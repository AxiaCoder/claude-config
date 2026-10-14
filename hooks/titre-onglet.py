#!/usr/bin/env python3
"""Hook Claude Code : le titre d'onglet du terminal dit l'etat de la session.

Lit sur stdin le JSON d'un evenement de hook et ecrit sur stdout
`{"terminalSequence": "<OSC 0 ; titre BEL>"}`, que le harnais envoie au terminal :

- `UserPromptSubmit` -> `⚙ <nom>` (au travail)
- `Stop` avec une tache de fond `running` -> `⏳ <nom>` (attend une commande en arriere-plan)
- `Stop` sinon -> `✅ <nom>` (a rendu la main)
- `Notification` de type `permission_prompt` ou `elicitation_dialog` -> `✋ <nom>`
  (attend l'utilisateur) ; tout autre type (`idle_prompt`...) ne change pas le titre

`<nom>` : dernier titre `/rename`, sinon dernier titre genere, lus dans la fin du transcript ;
a defaut le nom du dossier de travail. Demande `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, sans
quoi le titre natif de Claude Code ecrase celui-ci.

Sortie toujours 0 : un evenement inconnu ou une erreur ne rend rien.
"""

from __future__ import annotations

import json
import os
import re
import sys

TAIL_BYTES = 100 * 1024
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

ICON_WORKING = "⚙"
ICON_BACKGROUND = "⏳"
ICON_DONE = "✅"
WAITING_NOTIFICATIONS = frozenset({"permission_prompt", "elicitation_dialog"})
ICON_WAITING = "✋"


def read_tail(path, size=TAIL_BYTES):
    """Return the complete lines within the last size bytes of the file at path, decoded UTF-8."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        start = max(0, end - size)
        f.seek(start)
        data = f.read()
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if start > 0 else lines


def session_title(transcript_path):
    """Return the last customTitle, else the last aiTitle, of the transcript tail; "" if none or unreadable."""
    if not transcript_path:
        return ""
    try:
        lines = read_tail(transcript_path)
    except OSError:
        return ""
    ai_title = ""
    for line in reversed(lines):
        if "custom-title" not in line and "ai-title" not in line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "custom-title" and isinstance(entry.get("customTitle"), str) \
                and CONTROL_CHARS.sub("", entry["customTitle"]).strip():
            return entry["customTitle"]
        if not ai_title and entry.get("type") == "ai-title" and isinstance(entry.get("aiTitle"), str):
            ai_title = entry["aiTitle"]
    return ai_title


def session_name(payload):
    """Return the session name: transcript title, else basename of cwd, stripped of control characters."""
    name = session_title(payload.get("transcript_path"))
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
    icon = state_icon(payload)
    if icon is None:
        return ""
    name = session_name(payload)
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
