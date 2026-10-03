#!/usr/bin/env python3
"""Pousse dans VictoriaMetrics, par agent, ce que les metriques du harnais anonymisent.

Le harnais remplace le nom de tout agent defini par l'utilisateur par "custom" dans
ses metriques, mais il le passe en clair aux hooks. Ce collecteur lit donc le
hook SubagentStop, ouvre le transcript du sous-agent qui vient de finir, et
pousse ses tokens et sa duree sous le vrai nom de l'agent.

Deux modes :
  (defaut)       lit le JSON du hook sur stdin — SubagentStop ou SessionStart ;
  --rattrapage   relit tous les transcripts de sous-agents presents et repousse tout.

Sortie toujours 0 : ce collecteur ne fait jamais echouer une session.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

MAISON = pathlib.Path.home()
REGLAGES = MAISON / ".claude/settings.json"
PROJETS = MAISON / ".claude/projects"
FILE_ATTENTE = MAISON / ".claude/telemetrie-agents/en-attente.jsonl"
DELAI_ENVOI = 3
JOURS_GARDES = 30

TYPES = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_read_input_tokens": "cacheRead",
    "cache_creation_input_tokens": "cacheCreation",
}


def config() -> tuple[list[str], str]:
    """Rend les URL d'import a essayer dans l'ordre, et le nom de la machine.

    Les adresses viennent de TELEMETRIE_ENDPOINTS — une liste ordonnee, separee par
    des virgules — et a defaut de OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, celui du
    harnais. L'ordre compte : la premiere qui repond gagne.

    Leve RuntimeError si les adresses ou la machine manquent : inventer l'un ou
    l'autre produirait des series qui ne se recoupent avec rien dans les autres
    tableaux.
    """
    env = json.loads(REGLAGES.read_text(encoding="utf-8")).get("env", {})

    bases = [b.strip().rstrip("/") for b in env.get("TELEMETRIE_ENDPOINTS", "").split(",") if b.strip()]
    if not bases:
        point = env.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "")
        if not point:
            raise RuntimeError("ni TELEMETRIE_ENDPOINTS ni OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        bases = [point.split("/opentelemetry")[0].rstrip("/")]

    attributs = dict(
        p.split("=", 1)
        for p in env.get("OTEL_RESOURCE_ATTRIBUTES", "").split(",")
        if "=" in p
    )
    machine = attributs.get("machine")
    if not machine:
        raise RuntimeError("machine= absent de OTEL_RESOURCE_ATTRIBUTES")

    return [f"{b}/api/v1/import/prometheus" for b in bases], machine


def mesure(
    transcript: pathlib.Path, agent: str | None = None, lancement: str | None = None
) -> dict | None:
    """Rend les totaux d'un lancement de sous-agent, ou None s'il n'a rien consomme.

    `agent` et `lancement` viennent du hook quand ils sont fournis ; sinon ils sont
    lus dans le `.meta.json` voisin et dans le nom du fichier. Les horodatages sont en
    millisecondes depuis l'epoch.
    """
    if lancement is None:
        lancement = transcript.stem.removeprefix("agent-")
    if agent is None:
        meta = pathlib.Path(str(transcript).replace(".jsonl", ".meta.json"))
        if not meta.is_file():
            return None
        agent = json.loads(meta.read_text(encoding="utf-8")).get("agentType")
    if not agent:
        return None

    tokens: Counter[str] = Counter()
    modeles: Counter[str] = Counter()
    debut = fin = None

    with transcript.open(encoding="utf-8", errors="replace") as flux:
        for ligne in flux:
            try:
                enr = json.loads(ligne)
            except ValueError:
                continue

            horodatage = enr.get("timestamp")
            if horodatage:
                if debut is None:
                    debut = horodatage
                fin = horodatage

            message = enr.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            for brut, propre in TYPES.items():
                valeur = usage.get(brut)
                if isinstance(valeur, int):
                    tokens[propre] += valeur
            if message.get("model"):
                modeles[message["model"]] += 1

    if not tokens or debut is None:
        return None

    return {
        "agent": agent,
        "lancement": lancement,
        "modele": modeles.most_common(1)[0][0] if modeles else "inconnu",
        "tokens": dict(tokens),
        "debut_ms": epoch_ms(debut),
        "duree_s": round((epoch_ms(fin) - epoch_ms(debut)) / 1000, 1),
    }


def epoch_ms(horodatage: str) -> int:
    """Convertit un horodatage ISO en millisecondes depuis l'epoch, en UTC."""
    return int(
        datetime.fromisoformat(horodatage.replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .timestamp()
        * 1000
    )


def lignes(m: dict, machine: str) -> list[str]:
    """Rend les lignes au format d'exposition Prometheus pour un lancement.

    Chaque ligne porte l'horodatage du DEBUT du lancement, qui ne bouge jamais, et une
    etiquette `launch` propre au lancement. Les deux ensemble rendent le renvoi sans
    effet : VictoriaMetrics ne deduplique pas deux echantillons de meme horodatage, mais
    une serie par lancement se lit avec `last_over_time`, qui n'en garde qu'un.

    ⛔ Les panneaux doivent donc sommer `last_over_time(...)`, jamais `sum_over_time` :
    ce dernier additionnerait les renvois.
    """
    etiquettes = (
        f'agent="{echapper(m["agent"])}",model="{echapper(m["modele"])}",'
        f'machine="{echapper(machine)}",launch="{echapper(m["lancement"])}"'
    )
    sortie = [
        f'agent_tokens{{{etiquettes},type="{t}"}} {v} {m["debut_ms"]}'
        for t, v in sorted(m["tokens"].items())
    ]
    sortie.append(f'agent_duration_seconds{{{etiquettes}}} {m["duree_s"]} {m["debut_ms"]}')
    return sortie


def echapper(valeur: str) -> str:
    """Echappe une valeur d'etiquette Prometheus."""
    return valeur.replace("\\", "\\\\").replace('"', '\\"')


def pousser(corps: list[str], urls: list[str]) -> bool:
    """Essaie les adresses dans l'ordre et dit si l'une a accepte les lignes.

    L'ordre est celui des reglages : l'adresse du reseau local d'abord, celle du
    reseau prive virtuel ensuite. La premiere permet de mesurer sans qu'aucun outil
    tiers soit demarre ; la seconde couvre les sessions faites ailleurs.

    ⚠️ Chaque adresse doit ne resoudre que vers des hotes joignables. Les noms servis
    par la box portent aussi deux IPv6 publiques qui ne repondent pas, et un client
    qui les essaie dans l'ordre attend leurs expirations — 20 s mesurees.
    """
    donnees = ("\n".join(corps) + "\n").encode("utf-8")
    for url in urls:
        requete = urllib.request.Request(url, data=donnees, method="POST")
        try:
            with urllib.request.urlopen(requete, timeout=DELAI_ENVOI) as reponse:
                if 200 <= reponse.status < 300:
                    return True
        except (urllib.error.URLError, OSError, ValueError):
            continue
    return False


def mettre_en_attente(corps: list[str]) -> None:
    """Ajoute des lignes non envoyees a la file, pour un prochain passage."""
    FILE_ATTENTE.parent.mkdir(parents=True, exist_ok=True)
    with FILE_ATTENTE.open("a", encoding="utf-8") as flux:
        flux.write(json.dumps({"ts": time.time(), "lignes": corps}, ensure_ascii=False) + "\n")


def vider_la_file(urls: list[str]) -> tuple[int, int]:
    """Renvoie ce qui attend dans la file et rend (envoyees, restantes).

    Les entrees de plus de JOURS_GARDES jours sont jetees : au-dela, le transcript
    correspondant a ete purge et la mesure n'est plus comparable a rien.
    """
    if not FILE_ATTENTE.is_file():
        return 0, 0

    limite = time.time() - JOURS_GARDES * 86400
    envoyees = 0
    restantes: list[dict] = []

    for ligne in FILE_ATTENTE.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        try:
            entree = json.loads(ligne)
        except ValueError:
            continue
        if entree.get("ts", 0) < limite:
            continue
        if pousser(entree["lignes"], urls):
            envoyees += 1
        else:
            restantes.append(entree)

    if restantes:
        FILE_ATTENTE.write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in restantes),
            encoding="utf-8",
        )
    else:
        FILE_ATTENTE.unlink(missing_ok=True)

    return envoyees, len(restantes)


def traiter(m: dict, machine: str, urls: list[str]) -> str:
    """Pousse un lancement, ou le met en attente si le serveur ne repond pas."""
    corps = lignes(m, machine)
    if pousser(corps, urls):
        return "envoye"
    mettre_en_attente(corps)
    return "en attente"


def rattrapage(machine: str, urls: list[str]) -> None:
    """Repousse tous les lancements de sous-agents encore presents sur le disque."""
    envoyes = attente = ignores = 0
    for meta in PROJETS.glob("*/*/subagents/*.meta.json"):
        transcript = pathlib.Path(str(meta).replace(".meta.json", ".jsonl"))
        if not transcript.is_file():
            continue
        m = mesure(transcript)
        if m is None:
            ignores += 1
            continue
        if traiter(m, machine, urls) == "envoye":
            envoyes += 1
        else:
            attente += 1
    print(f"rattrapage : {envoyes} envoyes, {attente} en attente, {ignores} sans mesure")


def main() -> int:
    """Point d'entree : mode hook par defaut, --rattrapage sur demande."""
    try:
        urls, machine = config()
    except (OSError, ValueError, RuntimeError) as erreur:
        print(f"collecteur d'agents : {erreur}", file=sys.stderr)
        return 0

    envoyees, restantes = vider_la_file(urls)
    if envoyees or restantes:
        print(f"file d'attente : {envoyees} envoyees, {restantes} restantes")

    if "--rattrapage" in sys.argv:
        rattrapage(machine, urls)
        return 0

    charge = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not charge.strip():
        return 0
    try:
        hook = json.loads(charge)
    except ValueError:
        return 0

    chemin = hook.get("agent_transcript_path")
    if not chemin:
        return 0

    transcript = pathlib.Path(chemin)
    if not transcript.is_file():
        return 0

    m = mesure(transcript, hook.get("agent_type"), hook.get("agent_id"))
    if m is None:
        return 0

    etat = traiter(m, machine, urls)
    print(f"{m['agent']} : {sum(m['tokens'].values())} tokens, {m['duree_s']} s — {etat}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erreur:  # noqa: BLE001 - un collecteur ne casse jamais la session
        print(f"collecteur d'agents : {erreur}", file=sys.stderr)
        sys.exit(0)
