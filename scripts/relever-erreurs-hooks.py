#!/usr/bin/env python3
"""Releve les erreurs de hook non bloquantes dans les transcriptions de Claude Code.

Une erreur non bloquante ne bloque rien, donc personne ne la lit : elle n'existe que dans les
transcriptions, sous le type `hook_non_blocking_error`. Ce script les regroupe par hook,
evenement, code de sortie et message, avec leur premiere et derniere occurrence.

    python3 scripts/relever-erreurs-hooks.py [--depuis AAAA-MM-JJ] [--transcriptions <dossier>]

Il dit aussi combien de sessions reelles la fenetre couvre : zero erreur sur deux sessions ne
vaut pas zero erreur sur cent. Les sessions lancees par un outil, dans un dossier temporaire,
sont ecartees et comptees a part.

Sortie 1 s'il y a au moins une erreur, 0 sinon.

⛔ L'absence d'un hook ne prouve pas qu'il ne tourne pas : le harnais n'ecrit un `hook_success`
que si le hook a ecrit quelque chose. Un garde qui laisse passer ne laisse aucune trace.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import re
import sys

# Des sessions ouvertes par un outil, pas par l'utilisateur : elles noieraient le compte.
AUTOMATIQUES = ("codenotch-usage",)

NOM_DE_SCRIPT = re.compile(r"[\w.-]+\.(?:sh|py|ps1)")
CHEMIN = re.compile(r"(?:/Users|/private|/var|[A-Z]:\\)\S*")
PREFIXE = "Failed with non-blocking status code:"


def erreurs_de(entree: object) -> list[dict]:
    """Rend les objets `hook_non_blocking_error` trouves a n'importe quelle profondeur."""
    trouvees = []
    if isinstance(entree, dict):
        if entree.get("type") == "hook_non_blocking_error":
            trouvees.append(entree)
        for valeur in entree.values():
            trouvees += erreurs_de(valeur)
    elif isinstance(entree, list):
        for valeur in entree:
            trouvees += erreurs_de(valeur)
    return trouvees


def nom_du_hook(commande: str) -> str:
    """Rend le nom du script qu'une commande de hook lance, ou son premier mot a defaut."""
    scripts = NOM_DE_SCRIPT.findall(commande)
    return scripts[-1] if scripts else (commande.split() or ["?"])[0]


def message_de(erreur: dict) -> str:
    """Rend la derniere ligne non vide de la sortie d'erreur, chemins et nombres masques."""
    texte = (erreur.get("stderr") or erreur.get("stdout") or "").replace(PREFIXE, "")
    lignes = [ligne.strip() for ligne in texte.splitlines() if ligne.strip()]
    if not lignes:
        return ""
    return re.sub(r"\d{3,}", "N", CHEMIN.sub("<chemin>", lignes[-1]))[:110]


def relever(dossier: pathlib.Path, depuis: datetime.datetime | None) -> tuple[dict, set, set]:
    """Parcourt les transcriptions posterieures a `depuis`, un instant avec fuseau, ou toutes.

    Rend les erreurs groupees — cle (evenement, hook, sortie, message), valeur
    [nombre, premiere, derniere] en heure locale —, les sessions reelles vues et les
    sessions automatiques. Une erreur recopiee par un fork ou une reprise compte une fois.
    """
    vues: dict[tuple, tuple[str, datetime.datetime, dict]] = {}
    sessions, automatiques = set(), set()

    for fichier in dossier.rglob("*.jsonl"):
        if depuis and fichier.stat().st_mtime < depuis.timestamp():
            continue
        with fichier.open(encoding="utf-8", errors="replace") as flux:
            for ligne in flux:
                try:
                    entree = json.loads(ligne)
                except json.JSONDecodeError:
                    continue
                session = entree.get("sessionId")
                try:
                    horodatage = datetime.datetime.fromisoformat(entree["timestamp"].replace("Z", "+00:00"))
                except (KeyError, TypeError, ValueError):
                    continue
                if not session or (depuis and horodatage < depuis):
                    continue
                sessions.add(session)
                if any(motif in entree.get("cwd", "") for motif in AUTOMATIQUES):
                    automatiques.add(session)
                if "hook_non_blocking_error" in ligne:
                    for erreur in erreurs_de(entree):
                        identite = (entree.get("uuid"), erreur.get("toolUseID"), erreur.get("command"))
                        vues.setdefault(identite, (session, horodatage, erreur))

    groupes: dict = collections.defaultdict(lambda: [0, "9999", "0000"])
    for session, horodatage, erreur in vues.values():
        if session in automatiques:
            continue
        cle = (
            erreur.get("hookEvent", "?"),
            nom_du_hook(erreur.get("command", "")),
            erreur.get("exitCode"),
            message_de(erreur),
        )
        heure = horodatage.astimezone().strftime("%Y-%m-%d %H:%M")
        groupe = groupes[cle]
        groupe[0] += 1
        groupe[1] = min(groupe[1], heure)
        groupe[2] = max(groupe[2], heure)

    return groupes, sessions - automatiques, automatiques


def main() -> int:
    """Affiche le releve, les erreurs les plus recentes d'abord."""
    sys.stdout.reconfigure(encoding="utf-8")
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument(
        "--depuis",
        type=datetime.datetime.fromisoformat,
        help="AAAA-MM-JJ ou AAAA-MM-JJTHH:MM, en heure locale ; tout par defaut",
    )
    parseur.add_argument(
        "--transcriptions",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".claude" / "projects",
    )
    arguments = parseur.parse_args()

    depuis = arguments.depuis.astimezone() if arguments.depuis else None
    groupes, reelles, automatiques = relever(arguments.transcriptions, depuis)

    fenetre = f"depuis {depuis:%Y-%m-%d %H:%M}" if depuis else "sur toutes les transcriptions"
    print(f"{len(reelles)} sessions reelles {fenetre} ({len(automatiques)} automatiques ecartees)")

    if not groupes:
        print("aucune erreur de hook")
        return 0

    for (evenement, hook, sortie, message), (nombre, premiere, derniere) in sorted(
        groupes.items(), key=lambda groupe: groupe[1][2], reverse=True
    ):
        print(f"{nombre:5}  {premiere} → {derniere}  {evenement:<13} {hook}  sortie={sortie}")
        print(f"       {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
