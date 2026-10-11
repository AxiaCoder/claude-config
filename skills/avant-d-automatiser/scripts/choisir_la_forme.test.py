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


def verifier_json() -> list[str]:
    """--json donne la même forme que les drapeaux, tirets ou soulignés."""
    defauts: list[str] = []
    _, sortie = lancer("--json", json.dumps({"jugement": "une-etape", "sans_surveillance": True}))
    if sortie.get("forme") != 4:
        defauts.append(f"--json une-etape : forme {sortie.get('forme')}")
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
    if code != 0 or sortie.get("forme") is not None:
        defauts.append(f"aucun fait : exit {code}, forme {sortie.get('forme')}")
    for arguments in (("--json", "[1]"), ("--json", "{"), ("--json", '{"jugement": "parfois"}')):
        code, sortie = lancer(*arguments)
        if code != 0 or "error" not in sortie:
            defauts.append(f"entrée invalide {arguments[1]!r} : exit {code}, {sortie}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("formes 0-7", verifier_formes),
                       ("--json", verifier_json),
                       ("modificateur", verifier_modificateur),
                       ("entrées limites", verifier_entrees_limites)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
