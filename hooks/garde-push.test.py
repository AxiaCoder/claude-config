#!/usr/bin/env python3
"""Cas de test de garde-push.py, lancé en sous-processus. Sortie 0 si tous passent.

`python3 hooks/garde-push.test.py`
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_HOOK = pathlib.Path(__file__).resolve().parent / "garde-push.py"

# Assemblées par morceaux : le garde actif de la session lit aussi la commande qui lance ce fichier.
NV = "--no-" + "verify"
HP = "core." + "hooksPath"
APM = "ALLOW_" + "PUSH_" + "MAIN"
GPM = "garde." + "pushMain"
APP = "ALLOW_" + "PUSH_" + "PERSONAL"
GPMQ = "GARDE_" + "PUBLIC_" + "MARQUEURS"
PM = "push origin " + "ma" + "in"

REFUS, PASSE = 2, 0

CAS: tuple[tuple[int, str], ...] = (
    # --- doivent être refusés ---
    (REFUS, f"git {PM} {NV}"),
    (REFUS, f"git push {NV}"),
    (REFUS, f"git push {NV} origin feat/x"),
    (REFUS, f"git -C repo push {NV.upper()}"),
    (REFUS, f"cd repo && git commit -m x && git push {NV}"),
    (REFUS, f"git push {NV[:-1]} origin feat/x"),
    (REFUS, f"git push {NV[:-2]}"),
    (REFUS, f"git push {NV[:-3]}"),
    (REFUS, f"git config --global {HP} /dev/null"),
    (REFUS, f"git config --global --unset {HP}"),
    (REFUS, f"git -c {HP}=/tmp/vide {PM}"),
    (REFUS, f"git config --global {HP.lower()} x"),
    (REFUS, f"GIT_CONFIG_KEY_0={HP} git push"),
    (REFUS, f"{APM}=1 git {PM}"),
    (REFUS, f"export {APM}=1"),
    (REFUS, f"$env:{APM} = '1'; git {PM}"),
    (REFUS, f"git config --local {GPM} off"),
    (REFUS, f"git config {GPM.upper()} off"),
    (REFUS, f"gh pr create --body 'voir {APM}'"),
    (REFUS, f"{APP}=1 git push origin feat/x"),
    (REFUS, f"export {APP}=1"),
    (REFUS, f"$env:{APP} = '1'; git push"),
    (REFUS, f"{APP.lower()}=1 git push"),
    (REFUS, f"{GPMQ}= git push origin feat/x"),
    (REFUS, f"export {GPMQ}=''"),
    (REFUS, f"unset {GPMQ}; git push"),
    (REFUS, f"env -u {GPMQ} git push"),
    (REFUS, f"Remove-Item Env:{GPMQ}; git push"),
    (REFUS, f"{GPMQ.lower()}=x git push"),
    # --- doivent passer ---
    (PASSE, "git push"),
    (PASSE, f"git {PM}"),
    (PASSE, "git push -u origin feat/garde"),
    (PASSE, f"git commit {NV} -m wip"),
    (PASSE, f"echo {NV}"),
    (PASSE, f"git commit {NV} -m 'pushed fix'"),
    (PASSE, "git pushd"),
    (PASSE, "git push --no-verbose"),
    (PASSE, "git push --no-version-check"),
    (PASSE, "git config --global core.editor vim"),
    (PASSE, "ls hooks"),
    (PASSE, ""),
)


def lancer(entree: bytes) -> int:
    """Lance le hook avec `entree` sur stdin et rend son code de sortie."""
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=entree, capture_output=True, check=False
    ).returncode


def evenement(commande: str) -> bytes:
    """Rend le JSON PreToolUse, encodé en UTF-8, d'un appel Bash portant `commande`."""
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": commande}}
    ).encode("utf-8")


def main() -> int:
    """Joue la table puis les entrées dégradées ; rend 0 si tout passe, 1 sinon."""
    echecs = 0
    cas = [(attendu, commande, evenement(commande)) for attendu, commande in CAS]
    cas += [
        (PASSE, "<json illisible>", b"{pas du json"),
        (PASSE, "<entree vide>", b""),
        (PASSE, "<sans tool_input>", b'{"tool_name": "Bash"}'),
        (PASSE, "<command non textuelle>", b'{"tool_input": {"command": 42}}'),
        (PASSE, "<tableau>", b"[]"),
        (REFUS, "<utf-8 accentué>", evenement(f"echo « é » && {APM}=1 git push")),
        (REFUS, "<octet non UTF-8>", b'{"tool_input": {"command": "\xff ' + APM.encode() + b'=1"}}'),
    ]
    for attendu, libelle, entree in cas:
        obtenu = lancer(entree)
        if obtenu != attendu:
            echecs += 1
            print(f"ECHEC  attendu {attendu}, obtenu {obtenu} : {libelle!r}")
    print(f"{len(cas) - echecs}/{len(cas)} cas passent")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
