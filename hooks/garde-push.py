#!/usr/bin/env python3
"""Garde de push, côté Claude — hook PreToolUse sur Bash et PowerShell.

Le refus d'un push vers main appartient au hook git `git-hooks/pre-push`. Ce hook-ci
empêche seulement une commande de l'agent de le désarmer : il refuse (sortie 2) une
commande qui contient

- `--no-verify`, ou l'une de ses abréviations dès `--no-ver`, avec le mot `push` ;
- `core.hooksPath` ;
- `ALLOW_PUSH_MAIN` ;
- `garde.pushMain` ;
- `ALLOW_PUSH_PERSONAL` ;
- `GARDE_PUBLIC_MARQUEURS` ;
- `ALLOW_COMMIT_SECRET`, le contournement du garde secrets du pre-commit.

La comparaison ignore la casse. Tout le reste passe (sortie 0), y compris une entrée
illisible ou sans commande.

Cas de test : `python3 hooks/garde-push.test.py`
"""

from __future__ import annotations

import json
import re
import sys

_MOTIFS_INTERDITS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"core\.hookspath", re.IGNORECASE), "core.hooksPath"),
    (re.compile(r"allow_push_main", re.IGNORECASE), "ALLOW_PUSH_MAIN"),
    (re.compile(r"garde\.pushmain", re.IGNORECASE), "garde.pushMain"),
    (re.compile(r"allow_push_personal", re.IGNORECASE), "ALLOW_PUSH_PERSONAL"),
    (re.compile(r"garde_public_marqueurs", re.IGNORECASE), "GARDE_PUBLIC_MARQUEURS"),
    (re.compile(r"allow_commit_secret", re.IGNORECASE), "ALLOW_COMMIT_SECRET"),
)
_NO_VERIFY = re.compile(r"--no-ver(?:i(?:fy?)?)?\b", re.IGNORECASE)
_MOT_PUSH = re.compile(r"\bpush\b", re.IGNORECASE)


def motif_refuse(commande: str) -> str | None:
    """Rend le nom du réglage protégé que cite `commande`, ou None si elle passe."""
    if _NO_VERIFY.search(commande) and _MOT_PUSH.search(commande):
        return "push --no-verify"
    for motif, nom in _MOTIFS_INTERDITS:
        if motif.search(commande):
            return nom
    return None


def commande_de(brut: str) -> str | None:
    """Extrait `tool_input.command` du JSON de l'événement ; None si absent ou illisible."""
    try:
        evenement = json.loads(brut)
    except ValueError:
        return None
    if not isinstance(evenement, dict):
        return None
    entree = evenement.get("tool_input")
    if not isinstance(entree, dict):
        return None
    commande = entree.get("command")
    return commande if isinstance(commande, str) else None


def main() -> int:
    """Lit l'événement sur stdin ; rend 2 avec un message sur stderr si la commande est refusée, 0 sinon."""
    commande = commande_de(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    if commande is None:
        return 0
    nom = motif_refuse(commande)
    if nom is None:
        return 0
    sys.stderr.reconfigure(encoding="utf-8")
    print(
        f"garde-push : commande refusée, elle touche à « {nom} ». "
        "Ce réglage désarme le garde de push et reste réservé à l'utilisateur. "
        "Le push vers main passe par une pull request. "
        "Pour un texte qui cite ce réglage (corps de PR, commentaire), "
        "l'écrire dans un fichier avec l'outil d'écriture puis le passer par --body-file ou -F body=@.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
