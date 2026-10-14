#!/usr/bin/env python3
"""Cas de test de titre-onglet.py. Sortie 0 si tous passent.

Se lance après toute modification du hook : `python3 hooks/titre-onglet.test.py`
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

_ICI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("titre_onglet", _ICI / "titre-onglet.py")
_titre = importlib.util.module_from_spec(_spec)
sys.modules["titre_onglet"] = _titre
_spec.loader.exec_module(_titre)

CWD = "/home/axia/mon-projet"
_TEMP_TEST = tempfile.mkdtemp(prefix="titre-onglet-test-")
_titre.STATE_DIR = os.path.join(_TEMP_TEST, "claude-titre-onglet")
_ENV_TEST = dict(os.environ, TMP=_TEMP_TEST, TEMP=_TEMP_TEST, TMPDIR=_TEMP_TEST)


def lancer(entree: str) -> subprocess.CompletedProcess:
    """Lance titre-onglet.py en sous-processus avec entree sur stdin, état dans le temp de test."""
    return subprocess.run(
        [sys.executable, str(_ICI / "titre-onglet.py")],
        input=entree.encode("utf-8"), capture_output=True, timeout=30, env=_ENV_TEST,
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


def ecrire_neutre(f, octets: int) -> None:
    """Écrit dans f des lignes sans titre totalisant au moins octets."""
    neutre = (json.dumps({"type": "user", "message": "x" * 2000}) + "\n").encode("utf-8")
    f.write(neutre * (octets // len(neutre) + 1))


def ligne(entree: dict) -> bytes:
    """Rend entree en ligne JSONL encodée."""
    return (json.dumps(entree) + "\n").encode("utf-8")


def verifier_gros_transcript() -> list[str]:
    """Titre à plus de 5 Mo de la fin, customTitle ancien face à des aiTitle récents."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        chemin = pathlib.Path(d) / "gros.jsonl"
        with open(chemin, "wb") as f:
            f.write(ligne({"type": "ai-title", "aiTitle": "Lointain"}))
            ecrire_neutre(f, 5 * 1024 * 1024 + 1)
        nom = _titre.session_name({"transcript_path": str(chemin), "cwd": CWD})
        if nom != "Lointain":
            defauts.append(f"titre à > 5 Mo non lu : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = pathlib.Path(d) / "gros.jsonl"
        with open(chemin, "wb") as f:
            f.write(ligne({"type": "custom-title", "customTitle": "Renommée"}))
            ecrire_neutre(f, 2 * 1024 * 1024)
            for i in range(3):
                f.write(ligne({"type": "ai-title", "aiTitle": f"IA {i}"}))
        nom = _titre.session_name({"transcript_path": str(chemin), "cwd": CWD})
        if nom != "Renommée":
            defauts.append(f"customTitle ancien battu par aiTitle récent : {nom!r}")
    return defauts


def verifier_lecture_incrementale() -> list[str]:
    """2e appel : seul le neuf est lu ; ligne incomplète attendue ; tronqué ou autre chemin : relu de 0."""
    defauts: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        chemin = pathlib.Path(d) / "t.jsonl"
        premiere = ligne({"type": "ai-title", "aiTitle": "Premier"})
        chemin.write_bytes(premiere)
        etat = _titre.empty_state()
        if _titre.session_title(str(chemin), etat) != "Premier" or etat["offset"] != len(premiere):
            defauts.append(f"1er appel : {etat!r}")
        remplacant = json.dumps({"type": "custom-title", "customTitle": "Relu"})
        remplacant = (remplacant.ljust(len(premiere) - 1) + "\n").encode("utf-8")
        with open(chemin, "r+b") as f:
            f.write(remplacant)
            f.seek(0, os.SEEK_END)
            f.write(ligne({"type": "ai-title", "aiTitle": "Neuf"}))
            f.write(b'{"type": "ai-title", "aiTitle": "Incompl')
        titre = _titre.session_title(str(chemin), etat)
        if titre != "Neuf":
            defauts.append(f"2e appel : {titre!r} au lieu de 'Neuf'")
        with open(chemin, "ab") as f:
            f.write(b'et"}\n')
        titre = _titre.session_title(str(chemin), etat)
        if titre != "Incomplet":
            defauts.append(f"ligne complétée non lue : {titre!r}")
        chemin.write_bytes(ligne({"type": "ai-title", "aiTitle": "Court"}))
        titre = _titre.session_title(str(chemin), etat)
        if titre != "Court":
            defauts.append(f"fichier tronqué non relu de 0 : {titre!r}")
        autre = pathlib.Path(d) / "autre.jsonl"
        autre.write_bytes(ligne({"type": "custom-title", "customTitle": "Autre"})
                          + ligne({"type": "user", "message": "x" * 500}))
        titre = _titre.session_title(str(autre), etat)
        if titre != "Autre":
            defauts.append(f"autre chemin non relu de 0 : {titre!r}")
    return defauts


def verifier_retour_au_travail() -> list[str]:
    """✋ puis PostToolUse -> ⚙ ; PostToolUse sans ✋ -> rien ; état corrompu -> pas d'exception."""
    defauts: list[str] = []
    attente = {"hook_event_name": "Notification", "cwd": CWD, "session_id": "s-1",
               "notification_type": "permission_prompt"}
    outil = {"hook_event_name": "PostToolUse", "cwd": CWD, "session_id": "s-1"}
    if _titre.render(attente) != attendu("✋ mon-projet"):
        defauts.append("✋ non posé")
    if _titre.render(outil) != attendu("⚙ mon-projet"):
        defauts.append("PostToolUse après ✋ : pas de ⚙")
    if _titre.render(outil) != "":
        defauts.append("2e PostToolUse rendu")
    if _titre.render(dict(outil, session_id="s-2")) != "":
        defauts.append("PostToolUse sans ✋ préalable rendu")
    etat = _titre.state_file("s-3")
    os.makedirs(os.path.dirname(etat), exist_ok=True)
    for contenu in ("{pas du json", "[1, 2]", '{"icon": 3, "offset": "x", "path": null}'):
        with open(etat, "w", encoding="utf-8") as f:
            f.write(contenu)
        try:
            if _titre.render(dict(outil, session_id="s-3")) != "":
                defauts.append(f"état {contenu!r} : PostToolUse rendu")
            if _titre.render({"hook_event_name": "Stop", "cwd": CWD, "session_id": "s-3"}) \
                    != attendu("✅ mon-projet"):
                defauts.append(f"état {contenu!r} : Stop faux")
        except Exception as erreur:
            defauts.append(f"état {contenu!r} : {erreur!r}")
    if _titre.state_file("../..") is not None or not _titre.state_file("a/../b").endswith("ab.json"):
        defauts.append("session_id non filtré")
    for charge, titre in ((dict(attente, session_id="p-1"), "✋ mon-projet"),
                          (dict(outil, session_id="p-1"), "⚙ mon-projet")):
        resultat = lancer(json.dumps(charge))
        if resultat.returncode != 0 or resultat.stdout.decode("utf-8") != attendu(titre):
            defauts.append(f"processus {titre} : exit {resultat.returncode}, {resultat.stdout!r}")
    if not os.path.exists(os.path.join(_TEMP_TEST, "claude-titre-onglet", "p-1.json")):
        defauts.append("état du processus hors du temp de test")
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


def verifier_cas_limites() -> list[str]:
    """Bornes de la spec : elicitation, background_tasks absent ou mal typé, titres vides, nom vide."""
    defauts: list[str] = []
    cas = [
        ({"hook_event_name": "Notification", "cwd": CWD, "notification_type": "elicitation_dialog"},
         "✋ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD}, "✅ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": {"status": "running"}},
         "✅ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": ["running", None]},
         "✅ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": CWD, "background_tasks": []}, "✅ mon-projet"),
        ({"hook_event_name": "Stop", "cwd": "/home/axia/a\x1b\x07b\x9b"}, "✅ ab"),
        ({"hook_event_name": "Stop"}, "✅"),
        ({"hook_event_name": "UserPromptSubmit", "cwd": ""}, "⚙"),
    ]
    for charge, titre in cas:
        rendu = _titre.render(charge)
        if rendu != attendu(titre):
            defauts.append(f"{charge!r} : {rendu!r} au lieu de {attendu(titre)!r}")
    if _titre.render({"cwd": CWD}) != "":
        defauts.append("charge sans hook_event_name rendue")

    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [
            {"type": "custom-title", "customTitle": "Renommée"},
            {"type": "ai-title", "aiTitle": "Titre IA"},
            {"type": "custom-title", "customTitle": "   "},
            {"type": "custom-title", "customTitle": ""},
        ])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
        if nom != "Renommée":
            defauts.append(f"customTitle vide retenu : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [
            {"type": "ai-title", "aiTitle": "Titre IA"},
            {"type": "custom-title", "customTitle": ""},
            {"type": "custom-title", "customTitle": 42},
        ])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
        if nom != "Titre IA":
            defauts.append(f"customTitle vide ou non textuel masque aiTitle : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = ecrire_transcript(d, [{"type": "ai-title", "aiTitle": "\x1b\x07  "}])
        nom = _titre.session_name({"transcript_path": chemin, "cwd": CWD})
        if nom != "mon-projet":
            defauts.append(f"titre fait de contrôles seuls : {nom!r}")
    with tempfile.TemporaryDirectory() as d:
        chemin = pathlib.Path(d) / "melange.jsonl"
        chemin.write_text(
            '["custom-title"]\n'
            '{"type": "custom-title", "customTitle": "Valide"}\n'
            '{"type": "custom-title", tronqué\n'
            '"ai-title"\n',
            encoding="utf-8")
        nom = _titre.session_name({"transcript_path": str(chemin), "cwd": CWD})
        if nom != "Valide":
            defauts.append(f"ligne invalide après le titre : {nom!r}")
    return defauts


def verifier_processus_silencieux() -> list[str]:
    """Entrée invalide ou événement ignoré : exit 0, stdout et stderr vides."""
    defauts: list[str] = []
    entrees = [b"pas du json", b"", b"[]", b"null", b"\xff\xfe\x00",
               json.dumps({"hook_event_name": "PreToolUse", "cwd": CWD}).encode("utf-8"),
               json.dumps({"hook_event_name": "Notification", "cwd": CWD,
                           "notification_type": "idle_prompt"}).encode("utf-8")]
    for entree in entrees:
        resultat = subprocess.run([sys.executable, str(_ICI / "titre-onglet.py")],
                                  input=entree, capture_output=True, timeout=30, env=_ENV_TEST)
        if resultat.returncode != 0 or resultat.stdout or resultat.stderr:
            defauts.append(f"entrée {entree!r} : exit {resultat.returncode}, "
                           f"{resultat.stdout!r}, {resultat.stderr!r}")
    return defauts


def main() -> int:
    """Joue toutes les vérifications et rend 1 si l'une d'elles relève un défaut."""
    echec = False
    for nom, verif in (("quatre états", verifier_etats),
                       ("nom custom > ai > cwd", verifier_nom),
                       ("transcript absent / illisible -> cwd", verifier_transcript_absent),
                       ("titre lointain, customTitle ancien", verifier_gros_transcript),
                       ("lecture incrémentale", verifier_lecture_incrementale),
                       ("attente puis outil -> au travail", verifier_retour_au_travail),
                       ("caractères de contrôle retirés", verifier_controle),
                       ("sortie du processus", verifier_processus),
                       ("cas limites de la spec", verifier_cas_limites),
                       ("processus muet sur entrée invalide", verifier_processus_silencieux)):
        defauts = verif()
        echec = echec or bool(defauts)
        print(f"{'  ok ' if not defauts else 'ECHEC'} {nom}")
        for defaut in defauts:
            print(f"  {defaut}")
    return 1 if echec else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(_TEMP_TEST, ignore_errors=True)
