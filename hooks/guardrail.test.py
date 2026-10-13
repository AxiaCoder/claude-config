#!/usr/bin/env python3
"""Cas de test de `check_recursive_delete`, dans guardrail.py. Sortie 0 si tous passent.

Le garde refuse par défaut : un trou coûte ce qu'il a détruit, un faux positif coûte un
aller-retour. Les cas `PASSE` sont donc aussi importants que les `REFUS` — ils bornent le
faux positif, mais c'est un `REFUS` manqué qui est grave.

⚠️ Se lance après toute modification du motif ou de la liste des noms jetables :
`python3 hooks/guardrail.test.py`
"""

from __future__ import annotations

import importlib.util
import json
import ntpath
import os
import pathlib
import subprocess
import sys
import tempfile
import types

_ICI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("guardrail", _ICI / "guardrail.py")
_guardrail = importlib.util.module_from_spec(_spec)
sys.modules["guardrail"] = _guardrail
_spec.loader.exec_module(_guardrail)

CAS: tuple[tuple[str, str], ...] = (
    # --- doivent être refusés : la cible ne se reconstruit pas ---
    ("REFUS", "rm -rf /"),
    ("REFUS", "rm -rf ~"),
    ("REFUS", "rm -rf $HOME"),
    ("REFUS", "rm -rf /etc"),
    ("REFUS", "rm -rf ."),
    ("REFUS", "rm -rf .."),
    # --- traversée hors d'une racine temporaire : le chemin est normalisé avant d'être jugé ---
    ("REFUS", "rm -rf /tmp/../etc"),
    ("REFUS", "rm -rf node_modules/../.."),
    # --- quoting de bash : le garde juge le chemin que bash lira, pas le texte brut ---
    ("REFUS", r"rm -rf /tmp/\.\./etc"),
    ("REFUS", r"rm -rf C:/Users/moi/AppData/Local/Temp/\.\./\.\./\.\./Documents"),
    ("REFUS", "rm -rf /tmp/'..'/etc"),
    ("REFUS", 'rm -rf /tmp/".."/etc'),
    ("REFUS", """rm -rf "'"/../tmp/x"""),
    ("REFUS", r"rm -rf C:\Users\moi\AppData\Local\Temp\claude\x\scratchpad"),
    ("PASSE", r"rm -rf 'C:\Users\moi\AppData\Local\Temp\claude\x\scratchpad'"),
    ("PASSE", r'rm -rf "C:\Users\moi\AppData\Local\Temp\claude\x\scratchpad"'),
    ("REFUS", "rm -rf '/tmp/'..'/etc'"),
    ("REFUS", "rm -rf /tmp/''../etc"),
    ("REFUS", "rm -rf '/tmp/../etc"),
    ("REFUS", 'rm -rf "/etc'),
    ("REFUS", "rm -rf \\"),
    ("REFUS", r'rm -rf "/tmp/\$X"'),
    ("REFUS", "rm -rf '$'HOME"),
    ("REFUS", 'rm -rf "$"HOME'),
    ("REFUS", r"rm -rf \$HOME"),
    ("PASSE", "rm -rf \"/tmp/'..'/etc\""),
    ("PASSE", "rm -rf '/tmp/\"..\"/etc'"),
    ("PASSE", r'rm -rf "/tmp/\"..\"/etc"'),
    ("PASSE", r"rm -rf /tmp/\'..\'/etc"),
    ("PASSE", r'rm -rf "/tmp/\.\./etc"'),
    ("PASSE", r'rm -rf "/tmp/x\\"'),
    ("PASSE", r"rm -rf '/tmp/x\'"),
    # --- variantes de drapeaux, courtes et longues ---
    ("REFUS", "rm -fr /"),
    ("REFUS", "rm -Rf /"),
    ("REFUS", "rm -r -f /"),
    ("REFUS", "rm -rf --no-preserve-root /"),
    # ⚠️ Formes longues de GNU coreutils : absentes de BSD rm, donc invisibles sur macOS,
    # mais vivantes sur Linux — serveur, worker, intégration continue.
    ("REFUS", "rm --recursive --force /"),
    ("REFUS", "rm --force --recursive /"),
    ("REFUS", "rm --recursive /"),
    # --- globs ---
    ("REFUS", "rm -rf /*"),
    ("REFUS", "rm -rf *"),
    # --- plusieurs opérandes : un seul dangereux suffit à refuser ---
    ("REFUS", "rm -rf dist /etc"),
    ("REFUS", "rm -rf node_modules ~/Documents"),
    # --- enchaînements : le rm est jugé où qu'il soit dans la ligne ---
    ("REFUS", "cd / && rm -rf *"),
    ("REFUS", "sudo rm -rf /"),
    ("REFUS", "true; rm -rf /etc"),
    # --- variable non gardée : la façon classique de supprimer la racine ---
    ("REFUS", 'rm -rf "$DIR/"'),
    ("REFUS", "rm -rf ${DIR}/sous"),
    # --- doivent passer : la cible se reconstruit ---
    ("PASSE", "rm -rf /tmp/essai"),
    ("PASSE", "rm -rf C:/Users/moi/AppData/Local/Temp/claude/x/scratchpad/wt"),
    ("PASSE", 'rm -rf "/c/Users/moi/AppData/Local/Temp/claude/x/scratchpad/wt"'),
    # --- le temp Windows ne couvre que son propre contenu ---
    ("REFUS", "rm -rf C:/Users/moi/AppData/Local/Temp"),
    ("REFUS", "rm -rf C:/Users/moi/AppData/Local/Temp/../../Documents"),
    ("REFUS", "rm -rf C:/Users/moi/AppData/Local"),
    ("REFUS", "rm -rf C:/Windows/Temp/x"),
    ("PASSE", "rm -rf /private/tmp/claude-501/x/scratchpad"),
    ("PASSE", "rm -rf node_modules"),
    ("PASSE", "rm -rf ./dist"),
    ("PASSE", "rm -rf .venv"),
    ("PASSE", "rm -rf projet/build"),
    ("PASSE", 'rm -rf "${DIR:?}/dist"'),
    # --- hors périmètre : pas une suppression récursive ---
    ("PASSE", "rm fichier.txt"),
    ("PASSE", "rm -f fichier.txt"),
    ("PASSE", "grep -r motif /etc"),
    # --- une redirection n'est pas une cible ---
    ('PASSE', 'rm -rf /tmp/build 2>/dev/null'),
    ('PASSE', 'rm -rf node_modules > /dev/null'),
    ('PASSE', 'rm -rf dist 2>&1'),
    ('REFUS', 'rm -rf /etc/nginx 2>/dev/null'),
    ('REFUS', 'rm -rf . 2>/dev/null'),
    # ⚠️ La redirection AVANT l'opérande — forme shell valide, et le cas qu'une
    # troncature à la première flèchette laissait passer : elle jetait la cible avec la
    # redirection, il ne restait aucun opérande, et la branche « pas de refspec »
    # concluait que rien n'était visé. Trouvé en relecture le 2026-09-25.
    ('REFUS', 'rm -rf 2>/dev/null /etc'),
    ('REFUS', 'rm -rf > journal.txt /'),
    ('PASSE', 'rm -rf 2>/dev/null /tmp/essai'),
    # --- expansions que bash fait avant rm ---
    ("REFUS", "rm -rf /tmp/{..,}/etc"),
    ("REFUS", "rm -rf /tmp/{x/../..,y}/etc"),
    ("REFUS", "rm -rf /tmp/x/\\\n../../etc"),
    ("REFUS", "rm -rf \\\n/etc"),
    ("PASSE", "rm -rf /tmp/x/\\\nbuild"),
    ("PASSE", "rm -rf dist\nls"),
    ("REFUS", "rm -rf /tmp/$''{..,}/..${HOME:?}"),
    ("REFUS", "rm -rf /tmp/$\"\"{..,}/..${HOME:?}"),
    ("REFUS", "rm -rf /tmp/$'\\x2e\\x2e'/..${HOME:?}"),
    ("REFUS", "rm -rf \"${A:?}/${B}\""),
    ("REFUS", "rm -rf \"/tmp/${A:?}/${B}\""),
    ("PASSE", "rm -rf \"${A:?}/${B:?}/dist\""),
    ("PASSE", "rm -rf ${DIR:?}/build"),
    ("REFUS", "rm -rf /tmp/${USER:?/x}/../../home/u"),
    ("REFUS", "rm -rf /tmp/${USER:?/a/b}/../../../etc"),
    ("REFUS", "rm -rf \"/tmp/${USER:?\"}/x\"}/../../home/u\""),
    ("REFUS", "rm -rf /tmp/${USER:?\\}/x}/../../home/u"),
    ("REFUS", "rm -rf /tmp/${USER:?{a,b}}"),
    # --- variable assignée en littéral dans la même commande ---
    ("PASSE", 'S="C:/Users/moi/AppData/Local/Temp/x"; rm -rf "${S:?}/wt"'),
    ("PASSE", 'S=/c/Users/moi/AppData/Local/Temp/x && rm -rf "${S:?}"'),
    ("REFUS", 'export W="C:/Users/moi/AppData/Local/Temp/claude/s/scratchpad/wt"; git worktree list; rm -rf "${W:?}"'),
    ("PASSE", 'wt=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${wt:?}"'),
    ("PASSE", '  S=C:/Users/moi/AppData/Local/Temp/x && rm -rf "${S:?}/a"'),
    ("REFUS", 'DIR=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${DIR:?}/a"'),
    ("REFUS", 'echo; S=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", 'cat <<X\nHOME=C:/Users/moi/AppData/Local/Temp/x\nX\nrm -rf "${HOME:?}"'),
    ("REFUS", 'echo "x\nS=C:/Users/moi/AppData/Local/Temp/x"; rm -rf "${S:?}"'),
    ("REFUS", 'echo "x\nS=C:/Users/moi/AppData/Local/Temp/x; x"; rm -rf "${S:?}"'),
    ("REFUS", 'true #; S=C:/Users/moi/AppData/Local/Temp/x\nrm -rf "${S:?}"'),
    ("REFUS", '1=C:/Users/moi/AppData/Local/Temp/x; set -- /d/Documents/precious; rm -rf "${1:?}"'),
    ("REFUS", '_=C:/Users/moi/AppData/Local/Temp/x; ls /d/x; rm -rf "${_:?}"'),
    ("REFUS", 'OLDPWD=C:/Users/moi/AppData/Local/Temp/x; cd /d/Documents && cd /; rm -rf "${OLDPWD:?}"'),
    ("REFUS", 'RANDOM=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${RANDOM:?}"'),
    ("REFUS", 'UID=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${UID:?}"'),
    ("PASSE", 'S=/home/me/proj; rm -rf "${S:?}/dist"'),
    ("REFUS", 'S="D:/Documents/projet"; rm -rf "${S:?}/wt"'),
    ("REFUS", 'rm -rf "${S:?}/wt"'),
    ("REFUS", 'S=/tmp/x; S=/etc; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; S+=/../../etc; rm -rf "${S:?}"'),
    ("REFUS", 'S="$HOME/tmp"; rm -rf "${S:?}/x"'),
    ("REFUS", 'S=$(mktemp -d); rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; rm -rf "${S:?}/../../etc"'),
    ("REFUS", 'rm -rf "${S:?}"; S=/tmp/x'),
    ("PASSE", 'S="C:\\Users\\moi\\AppData\\Local\\Temp\\x"; rm -rf "${S:?}/wt"'),
    ("PASSE", "S='/tmp/x'; rm -rf \"${S:?}\""),
    ("REFUS", '(S=/tmp/x); rm -rf "${S:?}"'),
    ("REFUS", 'false || S=/tmp/x; rm -rf "${S:?}"'),
    ("REFUS", 'if true; then S=/tmp/x; fi; rm -rf "${S:?}"'),
    ("REFUS", 'while false; do S=/tmp/x; done; rm -rf "${S:?}"'),
    ("REFUS", 'case a in b) S=/tmp/x;; esac; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; for S in /etc; do rm -rf "${S:?}"; done'),
    ("REFUS", 'S=/tmp/x; read S; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; unset S; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; rm -rf "${S:?}" "${T:?}"'),
    ("REFUS", 'S=/tmp/x rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x & rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x | rm -rf "${S:?}"'),
    ("REFUS", 'false && S=/tmp/x; rm -rf "${S:?}"'),
    ("REFUS", '[ -d /nope ] && S=/tmp/x; rm -rf "${S:?}"'),
    ("REFUS", 'echo S=/tmp/x; rm -rf "${S:?}"'),
    ("REFUS", ': S=/tmp/x; rm -rf "${S:?}"'),
    ("REFUS", 'f() { S=/tmp/x; }; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; . ./evil.sh; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; source ./evil.sh; rm -rf "${S:?}"'),
    ("REFUS", 'S=/tmp/x; eval "$X"; rm -rf "${S:?}"'),
    ("REFUS", 'S="/tmp/x /d/Documents/precious"; rm -rf ${S:?}'),
    ("REFUS", "S='/d/Documents/precious /tmp/node_modules'; rm -rf ${S:?}"),
    ("REFUS", 'S="/tmp/x*"; rm -rf ${S:?}'),
    ("REFUS", '\x0bS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", '\x0cS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", '\x1cS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", '\xa0S=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", 'export\x0bS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", 'export\x0cS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", 'export\x1cS=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("REFUS", 'export\xa0S=C:/Users/moi/AppData/Local/Temp/x; rm -rf "${S:?}"'),
    ("PASSE", 'S=/tmp/x; rm -rf ${S:?}/wt'),
    ("PASSE", 'S="C:/Users/moi/AppData/Local/Temp/a-b_c.d"; rm -rf "${S:?}"'),
)


def verifier_boucle() -> list[str]:
    """Rejoue quatre appels identiques sous un HOME jetable et rend les défauts constatés.

    Attendu : les trois premiers passent (sortie 0), le quatrième est bloqué (sortie 2),
    l'état vit dans `~/.claude/hook-state/` et rien n'est écrit dans `token-telemetry/`.
    """
    defauts: list[str] = []
    charge = json.dumps({
        "session_id": "essai-boucle",
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/hosts"},
    })
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "HOME": home, "USERPROFILE": home}
        codes = [
            subprocess.run(
                [sys.executable, str(_ICI / "guardrail.py")],
                input=charge, capture_output=True, text=True, env=env, timeout=30,
            ).returncode
            for _ in range(4)
        ]
        if codes != [0, 0, 0, 2]:
            defauts.append(f"codes de sortie {codes}, attendu [0, 0, 0, 2]")
        claude = pathlib.Path(home) / ".claude"
        if not (claude / "hook-state" / "guardrail-state.json").is_file():
            defauts.append("pas d'état dans ~/.claude/hook-state/guardrail-state.json")
        if (claude / "token-telemetry").exists():
            defauts.append("~/.claude/token-telemetry/ créé")
    return defauts


CAS_WINDOWS: tuple[tuple[bool, str], ...] = (
    (True, "/tmp/build-x"),
    (True, "web/dist"),
    (False, "/etc"),
    (False, "/tmp/../etc"),
    (True, r"/tmp\build-x"),
    (False, r"/tmp/..\..\Users\me"),
    (False, r"/tmp\..\..\etc"),
)


def verifier_chemins_windows() -> list[str]:
    """Juge `_rebuilds_itself` avec `ntpath` à la place de `os.path`, et rend les écarts.

    Attendu : une racine temporaire et un nom jetable se reconstruisent toujours, même
    quand la normalisation de Windows change les `/` en `\\`.
    """
    defauts: list[str] = []
    os_reel = _guardrail.os
    _guardrail.os = types.SimpleNamespace(path=ntpath)
    try:
        for attendu, cible in CAS_WINDOWS:
            obtenu = _guardrail._rebuilds_itself(cible)
            if obtenu != attendu:
                defauts.append(f"{cible} : attendu {attendu}, obtenu {obtenu}")
    finally:
        _guardrail.os = os_reel
    return defauts


def verifier_entree_utf8() -> list[str]:
    """Envoie un appel Edit portant `⚠️` sous une entrée standard en cp1252, et rend les défauts.

    Attendu : sortie 0, sans trace d'exception — l'entrée du hook est de l'UTF-8 quel que
    soit l'encodage par défaut de la plateforme.
    """
    charge = json.dumps({
        "session_id": "essai-utf8",
        "tool_name": "Edit",
        "tool_input": {"file_path": "notes.md", "old_string": "a", "new_string": "⚠️ attention"},
    }, ensure_ascii=False).encode("utf-8")
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "HOME": home, "USERPROFILE": home, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        resultat = subprocess.run(
            [sys.executable, str(_ICI / "guardrail.py")],
            input=charge, capture_output=True, env=env, timeout=30,
        )
    defauts: list[str] = []
    if resultat.returncode != 0:
        defauts.append(f"code de sortie {resultat.returncode}, attendu 0")
    if b"Traceback" in resultat.stderr:
        derniere = resultat.stderr.decode("utf-8", "replace").strip().splitlines()[-1]
        defauts.append(f"exception : {derniere}")
    return defauts


# Assemblées par morceaux : le garde actif de la session lit aussi ce que l'agent écrit.
GA = "gitleaks" + ":allow"
BA = "betterleaks" + ":allow"
SECRET = 'token = "abc"  # '

CAS_EXEMPTION: tuple[tuple[str, str, dict], ...] = (
    ("REFUS", "Write", {"file_path": "a.py", "content": SECRET + GA}),
    ("REFUS", "Write", {"file_path": "a.py", "content": SECRET + GA.upper()}),
    ("REFUS", "Write", {"file_path": "a.py", "content": SECRET + BA}),
    ("REFUS", "Edit", {"file_path": "a.py", "old_string": 'token = "abc"', "new_string": SECRET + GA}),
    ("REFUS", "MultiEdit", {"file_path": "a.py", "edits": [
        {"old_string": "x = 1", "new_string": "x = 2"},
        {"old_string": 'token = "abc"', "new_string": SECRET + GA},
    ]}),
    ("REFUS", "NotebookEdit", {"notebook_path": "a.ipynb", "new_source": SECRET + GA}),
    ("PASSE", "Write", {"file_path": "a.py", "content": 'token = "abc"'}),
    ("PASSE", "Edit", {"file_path": "a.py", "old_string": SECRET + GA, "new_string": "x = 1\n" + SECRET + GA}),
    ("PASSE", "Edit", {"file_path": "a.py", "old_string": "x = 1", "new_string": "x = 2"}),
    ("PASSE", "Read", {"file_path": "a.py"}),
    ("REFUS", "Edit", {"file_path": "a.py", "old_string": f"A = 1 # {GA}\nB = 2",
                       "new_string": f"A = 1 # {GA}\nB = \"ghp_x\" # {GA}"}),
    ("PASSE", "Edit", {"file_path": "a.py", "old_string": f"A = 1 # {GA}\nB = 2",
                       "new_string": f"A = 1 # {GA}\nB = 3"}),
    ("REFUS", "MultiEdit", {"file_path": "a.py", "edits": [
        {"old_string": f"A = 1 # {GA}", "new_string": f"A = 1 # {GA}\nB = 2 # {BA}"},
    ]}),
)


def verifier_exemption_sur_disque() -> list[str]:
    """Juge un Write et un NotebookEdit contre le fichier existant, et rend les défauts.

    Attendu : conserver le nombre de marqueurs du fichier passe, en ajouter un est refusé.
    """
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as dossier:
        fichier = pathlib.Path(dossier) / "a.py"
        fichier.write_text(f"A = 1 # {GA}\n", encoding="utf-8")
        carnet = pathlib.Path(dossier) / "a.ipynb"
        carnet.write_text(json.dumps({"cells": [
            {"id": "c1", "cell_type": "code", "source": [f"A = 1 # {GA}\n"]},
        ]}), encoding="utf-8")
        cas = (
            ("PASSE", "Write", {"file_path": str(fichier), "content": f"A = 1 # {GA}\nB = 2\n"}),
            ("REFUS", "Write", {"file_path": str(fichier), "content": f"A = 1 # {GA}\nB = 2 # {GA}\n"}),
            ("PASSE", "NotebookEdit", {"notebook_path": str(carnet), "cell_id": "c1",
                                       "new_source": f"A = 1 # {GA}\nB = 2"}),
            ("REFUS", "NotebookEdit", {"notebook_path": str(carnet), "cell_id": "c1",
                                       "new_source": f"A = 1 # {GA}\nB = 2 # {GA}"}),
            ("REFUS", "NotebookEdit", {"notebook_path": str(carnet), "cell_id": "c1",
                                       "edit_mode": "insert", "new_source": f"A = 1 # {GA}"}),
        )
        for attendu, outil, entree in cas:
            obtenu = "REFUS" if _guardrail.check_secret_exemption(outil, entree) else "PASSE"
            if obtenu != attendu:
                defauts.append(f"{outil} {entree} : attendu {attendu}, obtenu {obtenu}")
    return defauts


def verifier_exemption() -> list[str]:
    """Juge `check_secret_exemption` sur la table, puis un Write exempté par le hook entier, et rend les défauts.

    Attendu : toute écriture qui ajoute l'exemption est refusée, une édition qui la conserve
    passe, et le hook entier sort en 2 avec le message sur stderr.
    """
    defauts: list[str] = []
    for attendu, outil, entree in CAS_EXEMPTION:
        obtenu = "REFUS" if _guardrail.check_secret_exemption(outil, entree) else "PASSE"
        if obtenu != attendu:
            defauts.append(f"{outil} {entree} : attendu {attendu}, obtenu {obtenu}")
    charge = json.dumps({
        "session_id": "essai-exemption",
        "tool_name": "Write",
        "tool_input": {"file_path": "a.py", "content": SECRET + GA},
    })
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "HOME": home, "USERPROFILE": home}
        resultat = subprocess.run(
            [sys.executable, str(_ICI / "guardrail.py")],
            input=charge.encode("utf-8"), capture_output=True, env=env, timeout=30,
        )
    if resultat.returncode != 2:
        defauts.append(f"hook entier : code {resultat.returncode}, attendu 2")
    if "réservée à l'utilisateur" not in resultat.stderr.decode("utf-8", "replace"):
        defauts.append("hook entier : le motif de refus manque sur stderr")
    return defauts


def main() -> int:
    """Joue tous les cas et rend 1 si l'un d'eux ne correspond pas à son attendu."""
    sys.stdout.reconfigure(encoding="utf-8")
    echecs: list[tuple[str, str, str]] = []
    for attendu, commande in CAS:
        obtenu = "REFUS" if _guardrail.check_recursive_delete(commande) else "PASSE"
        if obtenu != attendu:
            echecs.append((attendu, obtenu, commande))
        print(f"{'  ok ' if obtenu == attendu else 'ECHEC'} {obtenu:6} {commande}")

    print(f"\n{len(CAS) - len(echecs)}/{len(CAS)} cas conformes")
    for attendu, obtenu, commande in echecs:
        print(f"  attendu {attendu}, obtenu {obtenu} : {commande}")

    defauts_boucle = verifier_boucle()
    print(f"{'  ok ' if not defauts_boucle else 'ECHEC'} boucle : 4e appel identique bloqué, état dans hook-state")
    for defaut in defauts_boucle:
        print(f"  {defaut}")
    defauts_windows = verifier_chemins_windows()
    print(f"{'  ok ' if not defauts_windows else 'ECHEC'} chemins Windows : ntpath ne fait pas refuser un jetable")
    for defaut in defauts_windows:
        print(f"  {defaut}")

    defauts_utf8 = verifier_entree_utf8()
    print(f"{'  ok ' if not defauts_utf8 else 'ECHEC'} entrée UTF-8 : un appel portant ⚠️ ne fait pas tomber le hook en cp1252")
    for defaut in defauts_utf8:
        print(f"  {defaut}")

    defauts_exemption = verifier_exemption() + verifier_exemption_sur_disque()
    print(f"{'  ok ' if not defauts_exemption else 'ECHEC'} exemption gitleaks : refusée quand l'écriture l'ajoute")
    for defaut in defauts_exemption:
        print(f"  {defaut}")
    return 1 if echecs or defauts_boucle or defauts_windows or defauts_utf8 or defauts_exemption else 0


if __name__ == "__main__":
    raise SystemExit(main())
