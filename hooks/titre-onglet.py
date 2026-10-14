#!/usr/bin/env python3
"""Hook Claude Code : le titre d'onglet du terminal dit l'etat de la session.

Lit sur stdin le JSON d'un evenement de hook et ecrit sur stdout
`{"terminalSequence": "<OSC 0 ; titre BEL>"}`, que le harnais envoie au terminal :

- `UserPromptSubmit` -> `⚙ <nom>` (au travail)
- `Stop` avec une tache de fond `running` -> `⏳ <nom>` (attend une commande en arriere-plan)
- `Stop` sinon -> `✅ <nom>` (a rendu la main)
- `Notification` de type `permission_prompt` ou `elicitation_dialog` -> `✋ <nom>`
  (attend l'utilisateur) ; tout autre type (`idle_prompt`...) ne change pas le titre
- `PostToolUse` apres un `✋` -> `⚙ <nom>` (l'utilisateur a repondu, la session travaille) ;
  sans `✋` en cours, rien

`<nom>` : dernier titre `/rename` non vide de tout le transcript, sinon dernier titre genere non
vide ; a defaut le nom du dossier de travail.

Etat par session dans `<temp>/claude-titre-onglet/<session_id>.json` : chemin du transcript,
octet deja lu, derniers titres trouves, derniere icone ecrite. Le transcript n'est relu qu'a
partir de cet octet ; un chemin different ou un fichier plus court le fait relire depuis 0, un
etat illisible repart de zero. Demande `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, sans
quoi le titre natif de Claude Code ecrase celui-ci.

Sortie toujours 0 : un evenement inconnu ou une erreur ne rend rien.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
SESSION_ID_UNSAFE = re.compile(r"[^\w-]")
STATE_DIR = os.path.join(tempfile.gettempdir(), "claude-titre-onglet")
CHUNK_BYTES = 1024 * 1024

ICON_WORKING = "⚙"
ICON_BACKGROUND = "⏳"
ICON_DONE = "✅"
WAITING_NOTIFICATIONS = frozenset({"permission_prompt", "elicitation_dialog"})
ICON_WAITING = "✋"


def empty_state():
    """Return a fresh state: nothing read yet, no title, no icon."""
    return {"path": "", "offset": 0, "custom": "", "ai": "", "icon": ""}


def state_file(session_id):
    """Return the state file path for session_id, or None when the id is missing or has no safe character."""
    if not isinstance(session_id, str):
        return None
    safe = SESSION_ID_UNSAFE.sub("", session_id)
    return os.path.join(STATE_DIR, safe + ".json") if safe else None


def load_state(path):
    """Return the state stored at path, or a fresh state when path is None, missing or malformed."""
    if path is None:
        return empty_state()
    try:
        with open(path, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return empty_state()
    state = empty_state()
    if not isinstance(stored, dict):
        return state
    for key, default in state.items():
        value = stored.get(key)
        if isinstance(value, type(default)) and not isinstance(value, bool):
            state[key] = value
    if state["offset"] < 0:
        state["offset"] = 0
    return state


def save_state(path, state):
    """Write state to path atomically (temporary file then os.replace); no-op when path is None."""
    if path is None:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, path)


def is_blank(text):
    """Return True when text is empty once control characters and whitespace are removed."""
    return not CONTROL_CHARS.sub("", text).strip()


def scan_line(line, state):
    """Update state["custom"] or state["ai"] from one transcript line holding a non-blank title."""
    if b"custom-title" not in line and b"ai-title" not in line:
        return
    try:
        entry = json.loads(line.decode("utf-8", errors="replace"))
    except ValueError:
        return
    if not isinstance(entry, dict):
        return
    kind = entry.get("type")
    if kind == "custom-title":
        title = entry.get("customTitle")
        if isinstance(title, str) and not is_blank(title):
            state["custom"] = title
    elif kind == "ai-title":
        title = entry.get("aiTitle")
        if isinstance(title, str) and not is_blank(title):
            state["ai"] = title


def update_titles(transcript_path, state):
    """Read the transcript from state["offset"] to its last complete line and update state in place.

    Restarts from byte 0 when the path changed or the file is shorter than the stored offset.
    Raises OSError when the transcript cannot be read.
    """
    with open(transcript_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if state["path"] != transcript_path or size < state["offset"]:
            state.update(path=transcript_path, offset=0, custom="", ai="")
        f.seek(state["offset"])
        pending = b""
        while True:
            chunk = f.read(CHUNK_BYTES)
            if not chunk:
                break
            data = pending + chunk
            last = data.rfind(b"\n")
            if last < 0:
                pending = data
                continue
            for line in data[:last].split(b"\n"):
                scan_line(line, state)
            state["offset"] += last + 1
            pending = data[last + 1:]


def session_title(transcript_path, state=None):
    """Return the last non-blank customTitle, else the last non-blank aiTitle, of the whole transcript.

    state carries what earlier calls already read and is updated in place; "" if no title or unreadable.
    """
    if state is None:
        state = empty_state()
    if not transcript_path or not isinstance(transcript_path, str):
        return ""
    try:
        update_titles(transcript_path, state)
    except OSError:
        return ""
    return state["custom"] or state["ai"]


def session_name(payload, state=None):
    """Return the session name: transcript title, else basename of cwd, stripped of control characters.

    state, when given, is the session state updated in place by the transcript read.
    """
    name = session_title(payload.get("transcript_path"), state)
    if not CONTROL_CHARS.sub("", name).strip():
        cwd = payload.get("cwd") or ""
        name = os.path.basename(str(cwd).rstrip("/\\")) or str(cwd)
    return CONTROL_CHARS.sub("", name).strip()


def has_running_task(payload):
    """Return True when background_tasks holds at least one task whose status is "running"."""
    tasks = payload.get("background_tasks")
    if not isinstance(tasks, list):
        return False
    return any(isinstance(t, dict) and t.get("status") == "running" for t in tasks)


def state_icon(payload):
    """Return the icon for the hook event of payload, or None for an event this hook ignores."""
    event = payload.get("hook_event_name")
    if event == "UserPromptSubmit":
        return ICON_WORKING
    if event == "Stop":
        return ICON_BACKGROUND if has_running_task(payload) else ICON_DONE
    if event == "Notification":
        return ICON_WAITING if payload.get("notification_type") in WAITING_NOTIFICATIONS else None
    return None


def render(payload):
    """Return the JSON line to print for the parsed payload, or "" when nothing is to be written."""
    if not isinstance(payload, dict):
        return ""
    path = state_file(payload.get("session_id"))
    state = load_state(path)
    if payload.get("hook_event_name") == "PostToolUse":
        icon = ICON_WORKING if state["icon"] == ICON_WAITING else None
    else:
        icon = state_icon(payload)
    if icon is None:
        return ""
    name = session_name(payload, state)
    state["icon"] = icon
    save_state(path, state)
    title = "%s %s" % (icon, name) if name else icon
    return json.dumps({"terminalSequence": "\x1b]0;%s\x07" % title})


def main():
    """Read the hook payload from stdin and print the terminal title sequence; always exit 0."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        out = render(payload)
        if out:
            sys.stdout.write(out)
            sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
