#!/usr/bin/env python3
"""Status line de Claude Code : modele | dossier (branche) | contexte | 5h / 7d | PR.

Lit sur stdin le JSON que le harnais passe a la commande `statusLine`, ecrit une seule
ligne coloree ANSI sans retour final. Un champ absent omet son segment.

Sortie toujours 0 : un JSON invalide rend une ligne vide, jamais une trace.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[94m"


def g(o, *keys):
    """Return the nested value at keys, or None when any level is missing."""
    for k in keys:
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def level_color(pct):
    """Return the ANSI color for a usage percentage: green < 50, yellow < 80, red otherwise."""
    if pct < 50:
        return GREEN
    if pct < 80:
        return YELLOW
    return RED


def bar(pct, width=10):
    """Return a colored block bar for a usage percentage (0-100), followed by the bold value."""
    pct = max(0, min(100, pct))
    filled = round(pct / 100 * width)
    color = level_color(pct)
    return "%s%s%s%s%s %s%s%d%%%s" % (
        color, "█" * filled, DIM, "░" * (width - filled), RESET,
        BOLD, color, round(pct), RESET)


def git_branch(cwd):
    """Return the current git branch of cwd, or "" outside a repo or on any failure."""
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", cwd, "branch", "--show-current"],
                              capture_output=True, text=True, timeout=2).stdout.strip()
    except Exception:
        return ""


def render(d):
    """Return the status line for the parsed harness payload d; missing fields are omitted."""
    if not isinstance(d, dict):
        return ""
    parts = []
    m = g(d, "model", "display_name")
    if m:
        parts.append("\U0001F916 %s%s%s%s" % (BOLD, MAGENTA, m, RESET))

    cwd = g(d, "workspace", "current_dir") or d.get("cwd")
    if cwd:
        seg = "\U0001F4C1 %s%s%s" % (BLUE, os.path.basename(cwd.rstrip("/\\")) or cwd, RESET)
        br = git_branch(cwd)
        if br:
            seg += " \U0001F33F %s%s%s" % (CYAN, br, RESET)
        parts.append(seg)

    u = g(d, "context_window", "used_percentage")
    if u is not None:
        parts.append("\U0001F9E0 " + bar(u))

    for k, label in (("five_hour", "5h"), ("seven_day", "7d")):
        p = g(d, "rate_limits", k, "used_percentage")
        if p is not None:
            parts.append("⏳ %s%s%s " % (DIM, label, RESET) + bar(p, 6))

    n = g(d, "pr", "number")
    if n:
        ref = ("MR !" if g(d, "pr", "kind") == "mr" else "PR #") + str(n)
        parts.append("\U0001F500 %s%s%s%s" % (BOLD, YELLOW, ref, RESET))

    return ("  %s│%s  " % (DIM, RESET)).join(parts)


def main() -> int:
    """Read the payload from stdin, print the status line, and always return 0."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        d = json.loads(raw or "{}")
    except Exception:
        d = {}
    try:
        line = render(d)
    except Exception:
        line = ""
    print(line, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
