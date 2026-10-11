#!/usr/bin/env python3
"""Cas de test de score_constraints.py. Sortie 0 si tous passent.

Se lance après toute modification du classement :
`python3 skills/avant-d-automatiser/scripts/score_constraints.test.py`
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_ICI = pathlib.Path(__file__).resolve().parent

FLUX_TRI = [
    {"name": "Tri du lundi (propose)", "throughput_sensitivity": 1, "wait_before": 0,
     "downstream_starvation": 1, "capacity_gap": 0, "annoyance": 0},
    {"name": "Validation humaine", "throughput_sensitivity": 3, "wait_before": 2,
     "downstream_starvation": 3, "capacity_gap": 2, "policy_gate": True, "annoyance": 1},
    {"name": "Appliquer les verdicts", "throughput_sensitivity": 1, "wait_before": 1,
     "downstream_starvation": 0, "capacity_gap": 0, "annoyance": 3},
]


def lancer(entree: str) -> tuple[int, dict]:
    """Lance score_constraints.py avec entree sur stdin ; rend le code de sortie et le JSON lu."""
    res = subprocess.run(
        [sys.executable, str(_ICI / "score_constraints.py")],
        input=entree.encode("utf-8"), capture_output=True, timeout=30,
    )
    return res.returncode, json.loads(res.stdout.decode("utf-8"))


def verifier_flux_tri() -> list[str]:
    """Flux de tri : goulot à la validation, l'étape agaçante classée piège."""
    defauts: list[str] = []
    code, sortie = lancer(json.dumps(FLUX_TRI))
    if code != 0:
        defauts.append(f"exit {code}")
    if sortie.get("verdict") != "constraint_found":
        defauts.append(f"verdict {sortie.get('verdict')}")
    if sortie.get("constraint") != "Validation humaine":
        defauts.append(f"goulot {sortie.get('constraint')}")
    roles = {s["name"]: s.get("role") for s in sortie.get("ranking", [])}
    if roles.get("Appliquer les verdicts") != "trap":
        defauts.append(f"rôle de « Appliquer les verdicts » : {roles.get('Appliquer les verdicts')}")
    return defauts


def verifier_verdicts() -> list[str]:
    """Données trop minces -> insufficient_data ; deux étapes à égalité -> ambiguous."""
    defauts: list[str] = []
    _, sortie = lancer(json.dumps([{"name": "a"}, {"name": "b"}]))
    if sortie.get("verdict") != "insufficient_data":
        defauts.append(f"données vides : {sortie.get('verdict')}")
    egal = {"throughput_sensitivity": 3, "wait_before": 2, "downstream_starvation": 2, "capacity_gap": 2}
    _, sortie = lancer(json.dumps([{"name": "a", **egal}, {"name": "b", **egal}]))
    if sortie.get("verdict") != "ambiguous":
        defauts.append(f"égalité : {sortie.get('verdict')}")
    return defauts


def verifier_invalide() -> list[str]:
    """Entrée qui n'est pas une liste JSON -> verdict error, exit 0."""
    defauts: list[str] = []
    for entree in ("{", "{}"):
        code, sortie = lancer(entree)
        if code != 0 or sortie.get("verdict") != "error":
            defauts.append(f"entrée {entree!r} : exit {code}, {sortie}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("flux de tri -> validation", verifier_flux_tri),
                       ("verdicts insufficient/ambiguous", verifier_verdicts),
                       ("entrée invalide -> error", verifier_invalide)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
