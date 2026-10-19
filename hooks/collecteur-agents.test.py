#!/usr/bin/env python3
"""Cas de test du dossier de config que lit collecteur-agents.py. Sortie 0 si tous passent.

`python3 hooks/collecteur-agents.test.py`
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

_ICI = pathlib.Path(__file__).resolve().parent

_SONDE = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("collecteur", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
urls, machine = m.config()
m.mettre_en_attente(["ligne-essai"])
print(json.dumps({"urls": urls, "machine": machine}))
"""

_REGLAGES = {
    "env": {
        "TELEMETRIE_ENDPOINTS": "http://essai:8428",
        "OTEL_RESOURCE_ATTRIBUTES": "machine=essai",
    }
}


def sonder(home: str, config_dir: str | None) -> tuple[int, str]:
    """Charge le collecteur sous HOME et CLAUDE_CONFIG_DIR donnés, lit sa config, met une ligne en attente.

    `config_dir` à None retire la variable de l'environnement. Rend le code de sortie et stdout.
    """
    env = {**os.environ, "HOME": home, "USERPROFILE": home}
    env.pop("CLAUDE_CONFIG_DIR", None)
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    fini = subprocess.run(
        [sys.executable, "-c", _SONDE, str(_ICI / "collecteur-agents.py")],
        capture_output=True, text=True, env=env, timeout=30,
    )
    return fini.returncode, fini.stdout + fini.stderr


def ecrire_reglages(dossier: pathlib.Path) -> None:
    """Écrit un settings.json minimal valide dans `dossier`."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "settings.json").write_text(json.dumps(_REGLAGES), encoding="utf-8")


def verifier_config_dir_defini() -> list[str]:
    """CLAUDE_CONFIG_DIR défini : réglages lus et file d'attente écrite dans ce dossier, ~/.claude intouché."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as dossier:
        ecrire_reglages(pathlib.Path(dossier))
        code, sortie = sonder(home, dossier)
        if code != 0 or '"machine": "essai"' not in sortie:
            defauts.append(f"réglages non lus depuis CLAUDE_CONFIG_DIR (sortie {code}) : {sortie.strip()[-300:]}")
        if not (pathlib.Path(dossier) / "telemetrie-agents" / "en-attente.jsonl").is_file():
            defauts.append("file d'attente absente de $CLAUDE_CONFIG_DIR/telemetrie-agents")
        if (pathlib.Path(home) / ".claude").exists():
            defauts.append("~/.claude créé alors que CLAUDE_CONFIG_DIR est défini")
    return defauts


def verifier_repli_maison() -> list[str]:
    """CLAUDE_CONFIG_DIR absent ou vide : réglages lus et file d'attente écrite dans ~/.claude."""
    defauts: list[str] = []
    for valeur in (None, ""):
        with tempfile.TemporaryDirectory() as home:
            claude = pathlib.Path(home) / ".claude"
            ecrire_reglages(claude)
            code, sortie = sonder(home, valeur)
            if code != 0 or '"machine": "essai"' not in sortie:
                defauts.append(f"CLAUDE_CONFIG_DIR={valeur!r} : réglages non lus depuis ~/.claude (sortie {code}) : {sortie.strip()[-300:]}")
            if not (claude / "telemetrie-agents" / "en-attente.jsonl").is_file():
                defauts.append(f"CLAUDE_CONFIG_DIR={valeur!r} : file d'attente absente de ~/.claude/telemetrie-agents")
    return defauts


def main() -> int:
    """Joue les cas et rend 1 si l'un d'eux échoue."""
    sys.stdout.reconfigure(encoding="utf-8")
    echec = False
    for libelle, verifier in (
        ("CLAUDE_CONFIG_DIR défini : réglages et file d'attente dans ce dossier", verifier_config_dir_defini),
        ("CLAUDE_CONFIG_DIR absent ou vide : réglages et file d'attente dans ~/.claude", verifier_repli_maison),
    ):
        defauts = verifier()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {libelle}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
