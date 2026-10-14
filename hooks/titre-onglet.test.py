#!/usr/bin/env python3
"""Cas de test de titre-onglet.py. Sortie 0 si tous passent.

Se lance après toute modification du hook : `python3 hooks/titre-onglet.test.py`
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

_ICI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("titre_onglet", _ICI / "titre-onglet.py")
_titre = importlib.util.module_from_spec(_spec)
sys.modules["titre_onglet"] = _titre
_spec.loader.exec_module(_titre)

CWD = "/home/axia/mon-projet"


def lancer(entree: str) -> subprocess.CompletedProcess:
    """Lance titre-onglet.py en sous-processus avec entree sur stdin, sortie en octets."""
    return subprocess.run(
        [sys.executable, str(_ICI / "titre-onglet.py")],
        input=entree.encode("utf-8"), capture_output=True, timeout=30,
    )


def attendu(titre: str) -> str:
    """Rend la ligne JSON attendue pour titre."""
    return json.dumps({"terminalSequence": "\x1b]0;%s\x07" % titre})


def ecrire_transcript(dossier: str, lignes: list[dict]) -> str:
    """Écrit lignes en transcript JSONL dans dossier ; rend son chemin."""
    chemin = pathlib.Path(dossier) / "t.jsonl"
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        for ligne in lignes:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    return str(chemin)


def verifier_etats() -> list[str]:
    """Les quatre états : au travail, tâche de fond, rendu, attente."""
    defauts: list[str] = []
    cas = [
        ({"hook_event_name": "UserPromptSubmit", "cwd": CWD}, "⚙ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": [
            {"id": "a", "status": "completed"}, {"id": "b", "type": "shell", "status": "running"}]},
         "⏳ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": None}, "✅ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": [{"status": "completed"}]},
         "✅ mon-projet"),
        ({"hook_event_name": "Notification", "cwd": CWD, "notification_type": "permission_prompt"},
         "✋ mon-projet"),
    ]
    for charge, titre in cas:
        rendu = _titre.render(charge)
        if rendu != attendu(titre):
            defauts.append(f"{charge['hook_event_name']} : {rendu!r} au lieu de {attendu(titre)!r}")
    if _titre.render({"hook_event_name": "PreToolUse", "cwd": CWD}) != "":
        defauts.append("événement non géré rendu")
    for type_ in ("idle_prompt", "auth_success", None):
        charge = {"hook_event_name": "Notification", "cwd": CWD, "notification_type": type_}
        if _titre.render(charge) != "":
            defauts.append(f"Notification {type_!r} rendue")
    return defauts


def verifier_nom() -> list[str]:
    """Nom : customTitle > aiTitle > cwd, le dernier de chaque type l'emporte."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [
            {"type": "custom-title", "customTitle": "Renommée"},
            {"type": "ai-title", "aiTitle": "Ancien titre"},
            {"type": "custom-title", "customTitle": "Renommée 2"},
            {"type": "ai-title", "aiTitle": "Titre IA"},
        ])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
        if nom != "Renommée 2":
            defauts.append(f"customTitle non prioritaire : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [
            {"type": "ai-title", "aiTitle": "Ancien titre"},
            {"type": "ai-title", "aiTitle": "Titre IA"},
        ])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
        if nom != "Titre IA":
            defauts.append(f"dernier aiTitle non retenu : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [{"type": "user", "message": "rien"}])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD + "/"})
        if nom != "mon-projet":
            defauts.append(f"repli sur cwd : {nom!r}")
    return defauts


def verifier_transcript_absent() -> list[str]:
    """Transcript absent, dossier ou JSON illisible : repli sur cwd, sans erreur."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        illisible = pathlib.Path(d) / "casse.jsonl"
        illisible.write_bytes(b"\xff\xfe{pas du json custom-title ai-title\n\x00\x01")
        for chemin in (str(pathlib.Path(d) / "absent.jsonl"), d, str(illisible), None):
            nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
            if nom != "mon-projet":
                defauts.append(f"{chemin!r} : {nom!r}")
    return defauts


def verifier_gros_transcript() -> list[str]:
    """Transcript de plus de 100 Ko : le titre en fin est lu, celui du début ignoré."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        chemin = pathlib.Path(d) / "gros.jsonl"
        with open(chemin, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"type": "custom-title", "customTitle": "Trop loin"}) + "\n")
            neutre = json.dumps({"type": "user", "message": "x" * 200}) + "\n"
            for _ in range(300 * 1024 // len(neutre)):
                f.write(neutre)
            f.write(json.dumps({"type": "ai-title", "aiTitle": "En fin"}) + "\n")
        nom = _titre.session_name({"transcript_path": str(chemin), "cwd": CWD})
        if nom != "En fin":
            defauts.append(f"titre de fin non lu : {nom!r}")
    return defauts


def verifier_controle() -> list[str]:
    """Un titre portant ESC ou BEL ne sort pas tel quel dans la séquence."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [{"type": "custom-title", "customTitle": "a\x07b\x1b]0;c"}])
        rendu = json.loads(_titre.render({"hook_event_name": "Stop", "transcript_path": chemin}))
        if rendu["terminalSequence"] != "\x1b]0;✅ ab]0;c\x07":
            defauts.append(f"caractères de contrôle transmis : {rendu!r}")
    return defauts


def verifier_processus() -> list[str]:
    """Le script lancé rend le JSON exact sur stdout, exit 0, et rien sur entrée invalide."""
    defauts: list[str] = []
    cas = [
        ({"hook_event_name": "UserPromptSubmit", "cwd": CWD}, "⚙ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD,
          "background_tasks": [{"id": "b", "status": "running"}]}, "⏳ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": None}, "✅ mon-projet"),
        ({"hook_event_name": "Notification", "cwd": CWD, "notification_type": "permission_prompt"},
         "✋ mon-projet"),
    ]
    for charge, titre in cas:
        resultat = lancer(json.dumps(charge))
        if resultat.returncode != 0 or resultat.stdout.decode("utf-8") != attendu(titre):
            defauts.append(f"{titre} : exit {resultat.returncode}, {resultat.stdout!r}")
    for entree in ("pas du json", "", "[]", '{"hook_event_name": "Stop", "cwd": 3}'):
        resultat = lancer(entree)
        if resultat.returncode != 0 or resultat.stderr:
            defauts.append(f"entrée {entree!r} : exit {resultat.returncode}, {resultat.stderr!r}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("quatre états", verifier_etats),
                       ("nom custom > ai > cwd", verifier_nom),
                       ("transcript absent / illisible -> cwd", verifier_transcript_absent),
                       ("transcript > 100 Ko, titre en fin", verifier_gros_transcript),
                       ("caractères de contrôle retirés", verifier_controle),
                       ("sortie du processus", verifier_processus)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    raise SystemExit(main())
