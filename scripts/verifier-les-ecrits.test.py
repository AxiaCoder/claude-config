#!/usr/bin/env python3
"""Cas de test des renvois de fichier, dans verifier-les-ecrits.py. Sortie 0 si tous passent.

Chaque cas balaye une racine temporaire, avec une racine `--aussi` qui porte un dossier
`.claude/`, et dit si le renvoi cité doit être signalé `FICHIER ABSENT` ou non.

⚠️ Se lance après toute modification de `renvoi_verifiable` ou des préfixes hors de portée :
`python3 scripts/verifier-les-ecrits.test.py`
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile

_ICI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("verifier_les_ecrits", _ICI / "verifier-les-ecrits.py")
_verifier = importlib.util.module_from_spec(_spec)
sys.modules["verifier_les_ecrits"] = _verifier
_spec.loader.exec_module(_verifier)

CAS: tuple[tuple[str, str, str], ...] = (
    # --- fichiers propres au projet de l'utilisateur : jamais cherchés dans un dépôt balayé ---
    ("PASSE", ".claude/surcharges/x.md", ""),
    ("PASSE", ".claude/surcharges/pr.md", ""),
    # --- sauf si le dépôt balayé versionne lui-même ses surcharges : une coquille se signale ---
    ("SIGNALE", ".claude/surcharges/pr-reveiw.md", "balayee"),
    ("PASSE", ".claude/surcharges/pr-review.md", "balayee"),
    # --- une racine `--aussi` qui versionne les siennes n'engage pas le dépôt balayé ---
    ("PASSE", ".claude/surcharges/x.md", "aussi"),
    # --- témoins : un vrai chemin absent reste signalé ---
    ("SIGNALE", "docs/absent.md", ""),
    ("SIGNALE", ".claude/absent.md", ""),
    ("SIGNALE", ".claude/surcharges-bis/x.md", ""),
    # --- un chemin présent n'est pas signalé ---
    ("PASSE", "docs/present.md", ""),
)


def juger(cible: str, versionne: str) -> str:
    """Balaye une racine dont un `.md` cite `cible`, et rend SIGNALE ou PASSE.

    `versionne` : `balayee` ou `aussi`, la racine qui porte son propre
    `.claude/surcharges/pr-review.md` ; vide, aucune.
    """
    with tempfile.TemporaryDirectory() as dossier:
        base = pathlib.Path(dossier)
        balayee = base / "balayee"
        aussi = base / "aussi"
        (balayee / "docs").mkdir(parents=True)
        (balayee / "docs" / "present.md").write_text("présent\n", encoding="utf-8")
        (aussi / ".claude").mkdir(parents=True)
        if versionne:
            surcharges = base / versionne / ".claude" / "surcharges"
            surcharges.mkdir(parents=True)
            (surcharges / "pr-review.md").write_text("x\n", encoding="utf-8")
        (balayee / "commande.md").write_text(f"Voir `{cible}`.\n", encoding="utf-8")
        constats = _verifier.verifier([balayee], [aussi])
    return "SIGNALE" if any(c.startswith("FICHIER ABSENT") and cible in c for c in constats) else "PASSE"


def main() -> int:
    """Joue tous les cas et rend 1 si l'un d'eux ne correspond pas à son attendu."""
    echecs: list[tuple[str, str, str]] = []
    for attendu, cible, versionne in CAS:
        obtenu = juger(cible, versionne)
        if obtenu != attendu:
            echecs.append((attendu, obtenu, cible))
        print(f"{'  ok ' if obtenu == attendu else 'ECHEC'} {obtenu:7} {cible}")

    print(f"\n{len(CAS) - len(echecs)}/{len(CAS)} cas conformes")
    for attendu, obtenu, cible in echecs:
        print(f"  attendu {attendu}, obtenu {obtenu} : {cible}")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
