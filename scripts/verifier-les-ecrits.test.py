#!/usr/bin/env python3
"""Cas de test des renvois de fichier et de commande, dans verifier-les-ecrits.py. Sortie 0 si tous passent.

Chaque cas de fichier balaye une racine temporaire, avec une racine `--aussi` qui porte un dossier
`.claude/`, et dit si le renvoi cité doit être signalé `FICHIER ABSENT` ou non. Chaque cas de
commande dit si un `/nom` cité doit être signalé `RENVOI MORT` ou non.

⚠️ Se lance après toute modification de `renvoi_verifiable`, des préfixes hors de portée ou de `FAUX_AMIS` :
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


CAS_COMMANDES: tuple[tuple[str, str], ...] = (
    # --- commande du harnais citée : un faux ami, jamais signalé ---
    ("PASSE", "mcp"),
    ("PASSE", "compact"),
    # --- commande ou skill présent dans la racine : pas signalé ---
    ("PASSE", "presente"),
    ("PASSE", "skill-present"),
    # --- témoin : une commande inconnue reste signalée ---
    ("SIGNALE", "commande-absente"),
)


def juger_commande(nom: str) -> str:
    """Balaye une racine dont un `.md` cite `/nom`, et rend SIGNALE ou PASSE."""
    with tempfile.TemporaryDirectory() as dossier:
        balayee = pathlib.Path(dossier) / "balayee"
        (balayee / "commands").mkdir(parents=True)
        (balayee / "commands" / "presente.md").write_text("x\n", encoding="utf-8")
        (balayee / "skills" / "skill-present").mkdir(parents=True)
        (balayee / "skills" / "skill-present" / "SKILL.md").write_text("x\n", encoding="utf-8")
        (balayee / "texte.md").write_text(f"Lance `/{nom}`.\n", encoding="utf-8")
        constats = _verifier.verifier([balayee], [])
    return "SIGNALE" if any(c.startswith("RENVOI MORT") and c.endswith(f"/{nom}") for c in constats) else "PASSE"


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
    joues = [(attendu, cible, juger(cible, versionne)) for attendu, cible, versionne in CAS]
    joues += [(attendu, f"/{nom}", juger_commande(nom)) for attendu, nom in CAS_COMMANDES]
    for attendu, cible, obtenu in joues:
        if obtenu != attendu:
            echecs.append((attendu, obtenu, cible))
        print(f"{'  ok ' if obtenu == attendu else 'ECHEC'} {obtenu:7} {cible}")

    print(f"\n{len(joues) - len(echecs)}/{len(joues)} cas conformes")
    for attendu, obtenu, cible in echecs:
        print(f"  attendu {attendu}, obtenu {obtenu} : {cible}")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
