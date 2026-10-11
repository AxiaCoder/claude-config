#!/usr/bin/env python3
"""Cas de test de choisir_la_forme.py. Sortie 0 si tous passent.

Se lance après toute modification de l'arbre de décision :
`python3 skills/avant-d-automatiser/scripts/choisir_la_forme.test.py`
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_ICI = pathlib.Path(__file__).resolve().parent

CAS_FORMES = [
    ("0 exploitation suffit", ["--exploitation-suffit", "--en-continu"], 0),
    ("1 événement", ["--evenement-declencheur"], 1),
    ("2 colle entre services", ["--colle-entre-services", "--evenement-declencheur"], 2),
    ("3 logique à tester", ["--logique-a-tester", "--evenement-declencheur"], 3),
    ("3 sans surveillance", ["--sans-surveillance"], 3),
    ("4 une étape d'IA", ["--jugement", "une-etape", "--sans-surveillance"], 4),
    ("5 jugement partout, à la main", ["--jugement", "chaque-etape", "--lance-par-l-utilisateur"], 5),
    ("5 une étape, à la main", ["--jugement", "une-etape", "--lance-par-l-utilisateur"], 5),
    ("6 agent autonome", ["--jugement", "chaque-etape", "--sans-surveillance"], 6),
    ("7 service permanent", ["--en-continu", "--jugement", "chaque-etape"], 7),
]


def lancer(*arguments: str) -> tuple[int, dict]:
    """Lance choisir_la_forme.py avec ces arguments ; rend le code de sortie et le JSON lu."""
    res = subprocess.run(
        [sys.executable, str(_ICI / "choisir_la_forme.py"), *arguments],
        capture_output=True, timeout=30,
    )
    return res.returncode, json.loads(res.stdout.decode("utf-8"))


def verifier_formes() -> list[str]:
    """Chaque forme 0-7 sort des faits qui la désignent, avec exit 0."""
    defauts: list[str] = []
    for nom, arguments, attendu in CAS_FORMES:
        code, sortie = lancer(*arguments)
        if code != 0 or sortie.get("forme") != attendu:
            defauts.append(f"{nom} : exit {code}, forme {sortie.get('forme')} au lieu de {attendu}")
    return defauts


def faits_json(arguments: list[str]) -> dict:
    """Traduit une liste de drapeaux en objet de faits pour --json."""
    faits: dict = {}
    i = 0
    while i < len(arguments):
        cle = arguments[i][2:].replace("-", "_")
        if cle == "jugement":
            faits[cle] = arguments[i + 1]
            i += 2
        else:
            faits[cle] = True
            i += 1
    return faits


def verifier_json() -> list[str]:
    """--json donne la même forme que les drapeaux, tirets ou soulignés."""
    defauts: list[str] = []
    _, sortie = lancer("--json", json.dumps({"jugement": "une-etape", "sans_surveillance": True}))
    if sortie.get("forme") != 4:
        defauts.append(f"--json une-etape : forme {sortie.get('forme')}")
    _, sortie = lancer("--json", json.dumps({"jugement": "une_etape", "sans_surveillance": True}))
    if sortie.get("forme") != 4:
        defauts.append(f"--json une_etape : forme {sortie.get('forme')}")
    return defauts


def verifier_parite() -> list[str]:
    """Chaque cas de CAS_FORMES rend la même décision par drapeaux et par --json."""
    defauts: list[str] = []
    for nom, arguments, _ in CAS_FORMES + [("contradictoires", ["--lance-par-l-utilisateur", "--sans-surveillance"], 3)]:
        _, par_drapeaux = lancer(*arguments)
        _, par_json = lancer("--json", json.dumps(faits_json(arguments)))
        if par_drapeaux != par_json:
            defauts.append(f"{nom} : drapeaux {par_drapeaux.get('forme')} / --json {par_json.get('forme')}")
    return defauts


def verifier_json_prime_sur_drapeaux() -> list[str]:
    """--json remplace les drapeaux au lieu de s'y ajouter."""
    defauts: list[str] = []
    _, sortie = lancer("--en-continu", "--json", json.dumps({"colle_entre_services": True}))
    if sortie.get("forme") != 2 or sortie.get("faits", {}).get("en_continu"):
        defauts.append(f"drapeau --en-continu pris en compte malgré --json : {sortie.get('forme')}")
    return defauts


def verifier_contradictions() -> list[str]:
    """Deux faits qui s'excluent : la forme reste décidée, et une remarque le signale."""
    defauts: list[str] = []
    for arguments, attendu in (
        (["--evenement-declencheur", "--lance-par-l-utilisateur"], 1),
        (["--lance-par-l-utilisateur", "--sans-surveillance"], 3),
        (["--lance-par-l-utilisateur", "--sans-surveillance", "--jugement", "chaque-etape"], 5),
        (["--lance-par-l-utilisateur", "--sans-surveillance", "--jugement", "une-etape"], 5),
    ):
        _, sortie = lancer(*arguments)
        notes = sortie.get("remarques", [])
        if sortie.get("forme") != attendu or not any("contradictoires" in n for n in notes):
            defauts.append(f"{arguments} : forme {sortie.get('forme')}, remarques {notes}")
    return defauts


def verifier_remarques() -> list[str]:
    """Les remarques de découpage, de déclenchement et d'agent apparaissent sur leur forme."""
    defauts: list[str] = []
    attentes = (
        (["--jugement", "une-etape"], 4, "Découper"),
        (["--logique-a-tester", "--evenement-declencheur"], 3, "événement"),
        (["--logique-a-tester", "--lance-par-l-utilisateur"], 3, "planifié"),
        (["--jugement", "chaque-etape", "--sans-surveillance"], 6, "forme plus basse"),
        (["--en-continu", "--jugement", "chaque-etape"], 7, "forme plus basse"),
    )
    for arguments, forme, fragment in attentes:
        _, sortie = lancer(*arguments)
        notes = sortie.get("remarques", [])
        if sortie.get("forme") != forme or not any(fragment in n for n in notes):
            defauts.append(f"{arguments} : forme {sortie.get('forme')}, remarques {notes}")
    _, sortie = lancer("--colle-entre-services")
    if sortie.get("remarques"):
        defauts.append(f"remarque inattendue sur la forme 2 : {sortie.get('remarques')}")
    return defauts


def verifier_modificateur() -> list[str]:
    """Le modificateur s'ajoute à une forme qui tourne, jamais à la forme 0."""
    defauts: list[str] = []
    _, sortie = lancer("--logique-a-tester", "--ne-doit-jamais-echouer-en-silence")
    if sortie.get("forme") != 3 or len(sortie.get("modificateurs", [])) != 1:
        defauts.append(f"modificateur absent sur la forme 3 : {sortie}")
    _, sortie = lancer("--logique-a-tester")
    if sortie.get("modificateurs"):
        defauts.append("modificateur présent sans le fait")
    _, sortie = lancer("--exploitation-suffit", "--ne-doit-jamais-echouer-en-silence")
    if sortie.get("forme") != 0 or sortie.get("modificateurs"):
        defauts.append(f"modificateur appliqué à la forme 0 : {sortie}")
    return defauts


def verifier_entrees_limites() -> list[str]:
    """Aucun fait -> pas de forme ; entrée invalide -> erreur JSON, exit 0."""
    defauts: list[str] = []
    code, sortie = lancer()
    if code != 0 or sortie.get("forme") is not None or sortie.get("nom") is not None:
        defauts.append(f"aucun fait : exit {code}, forme {sortie.get('forme')}")
    code, sortie = lancer("--json", "{}")
    if code != 0 or sortie.get("forme") is not None or sortie.get("faits", {}).get("jugement") != "aucun":
        defauts.append(f"--json vide : exit {code}, {sortie}")
    code, sortie = lancer("--ne-doit-jamais-echouer-en-silence")
    if sortie.get("forme") is not None or sortie.get("modificateurs"):
        defauts.append(f"modificateur appliqué sans forme : {sortie}")
    invalides = (
        ("--json", "[1]"), ("--json", "{"), ("--json", '"x"'), ("--json", "null"), ("--json", "0"),
        ("--json", '{"jugement": "parfois"}'), ("--json", '{"jugement": null}'),
        ("--jugement", "parfois"), ("--jugement", "UNE-ETAPE"),
    )
    for arguments in invalides:
        res = subprocess.run([sys.executable, str(_ICI / "choisir_la_forme.py"), *arguments],
                             capture_output=True, timeout=30)
        sortie = json.loads(res.stdout.decode("utf-8"))
        if res.returncode != 0 or "error" not in sortie or res.stderr or "Traceback" in res.stdout.decode():
            defauts.append(f"entrée invalide {arguments!r} : exit {res.returncode}, {sortie}")
    for brut in ("[1]", "null", '"x"'):
        _, sortie = lancer("--json", brut)
        if "JSON object" not in sortie.get("error", ""):
            defauts.append(f"--json {brut} : message {sortie.get('error')!r}")
    return defauts


def lancer_brut(*arguments: str) -> tuple[int, dict | None, str]:
    """Lance choisir_la_forme.py ; rend le code de sortie, le JSON de stdout (None s'il n'en est pas) et stderr."""
    res = subprocess.run(
        [sys.executable, str(_ICI / "choisir_la_forme.py"), *arguments],
        capture_output=True, timeout=30,
    )
    try:
        sortie = json.loads(res.stdout.decode("utf-8"))
    except ValueError:
        sortie = None
    return res.returncode, sortie, res.stderr.decode("utf-8")


def erreur_json(arguments: tuple[str, ...], fragment: str = "") -> str | None:
    """Rend un défaut si ces arguments ne donnent pas une erreur JSON, exit 0, contenant fragment."""
    code, sortie, _ = lancer_brut(*arguments)
    if code != 0 or not isinstance(sortie, dict) or "error" not in sortie or "forme" in sortie:
        return f"{arguments!r} : exit {code}, sortie {sortie}"
    if fragment and fragment not in sortie["error"]:
        return f"{arguments!r} : l'erreur ne nomme pas {fragment!r} : {sortie['error']!r}"
    return None


def verifier_faits_non_booleens() -> list[str]:
    """--json : un fait qui n'est pas true/false est refusé, jamais converti."""
    defauts: list[str] = []
    for valeur in ("non", "false", "true", 1, 0, None, [], {}):
        defaut = erreur_json(("--json", json.dumps({"en_continu": valeur})), "en_continu")
        if defaut:
            defauts.append(defaut)
    code, sortie, _ = lancer_brut("--json", json.dumps({"en_continu": False, "colle_entre_services": True}))
    if code != 0 or not sortie or sortie.get("forme") != 2:
        defauts.append(f"booléens stricts refusés : {sortie}")
    return defauts


def verifier_cles_json() -> list[str]:
    """--json : clé inconnue refusée et nommée ; clé à tirets lue comme sa forme à soulignés."""
    defauts: list[str] = []
    defaut = erreur_json(("--json", json.dumps({"inconnu": True})), "inconnu")
    if defaut:
        defauts.append(defaut)
    defaut = erreur_json(("--json", json.dumps({"en_continu": True, "sans_surveilance": True})), "sans_surveilance")
    if defaut:
        defauts.append(defaut)
    for faits, attendu in (({"en-continu": True}, 7),
                           ({"lance-par-l-utilisateur": True, "jugement": "une-etape"}, 5)):
        code, sortie, _ = lancer_brut("--json", json.dumps(faits))
        if code != 0 or not sortie or sortie.get("forme") != attendu:
            defauts.append(f"clé à tirets {faits} : forme {sortie and sortie.get('forme')} au lieu de {attendu}")
    return defauts


def verifier_drapeau_inconnu() -> list[str]:
    """Drapeau inconnu : erreur JSON sur stdout, exit 0, pas d'usage argparse."""
    defauts: list[str] = []
    for arguments in (("--nope",), ("--en-continu", "--sans-surveilance"), ("positionnel",)):
        defaut = erreur_json(arguments)
        if defaut:
            defauts.append(defaut)
    return defauts


def verifier_json_vide() -> list[str]:
    """--json '' est une erreur, pas un repli silencieux sur les drapeaux."""
    defauts: list[str] = []
    for arguments in (("--json", ""), ("--en-continu", "--json", "")):
        defaut = erreur_json(arguments)
        if defaut:
            defauts.append(defaut)
    return defauts


CAS_SANS_JUGEMENT = [
    ("événement + sans surveillance", ["--evenement-declencheur", "--sans-surveillance"], 1),
    ("colle + sans surveillance", ["--colle-entre-services", "--sans-surveillance"], 2),
    ("colle + logique à tester", ["--colle-entre-services", "--logique-a-tester"], 3),
    ("sans surveillance seul", ["--sans-surveillance"], 3),
    ("lancé à la main seul", ["--lance-par-l-utilisateur"], 3),
]


def verifier_sans_surveillance_ne_monte_pas() -> list[str]:
    """Sans jugement, sans_surveillance ne fait pas monter 1 ou 2 vers 3 ; drapeaux et --json concordent."""
    defauts: list[str] = []
    for nom, arguments, attendu in CAS_SANS_JUGEMENT:
        _, par_drapeaux = lancer(*arguments)
        _, par_json = lancer("--json", json.dumps(faits_json(arguments)))
        if par_drapeaux.get("forme") != attendu:
            defauts.append(f"{nom} (drapeaux) : forme {par_drapeaux.get('forme')} au lieu de {attendu}")
        if par_json.get("forme") != attendu:
            defauts.append(f"{nom} (--json) : forme {par_json.get('forme')} au lieu de {attendu}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("formes 0-7", verifier_formes),
                       ("--json", verifier_json),
                       ("sans surveillance ne fait pas monter 1-2", verifier_sans_surveillance_ne_monte_pas),
                       ("parité drapeaux / --json", verifier_parite),
                       ("--json prime sur les drapeaux", verifier_json_prime_sur_drapeaux),
                       ("faits contradictoires", verifier_contradictions),
                       ("remarques", verifier_remarques),
                       ("modificateur", verifier_modificateur),
                       ("entrées limites", verifier_entrees_limites),
                       ("--json : faits non booléens refusés", verifier_faits_non_booleens),
                       ("--json : clés inconnues ou à tirets", verifier_cles_json),
                       ("drapeau inconnu -> erreur JSON", verifier_drapeau_inconnu),
                       ("--json vide -> erreur", verifier_json_vide)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
