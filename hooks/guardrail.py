#!/usr/bin/env python3
"""Guardrail — Circuit breaker hook.

Detects and blocks:
- Infinite loops (same tool called repeatedly with same args)
- Destructive commands (rm -rf, DROP TABLE, etc.)
- Runaway subagents
- A write or edit that adds the gitleaks/betterleaks `:allow` exemption marker
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "hook-state"
STATE_FILE = STATE_DIR / "guardrail-state.json"

# Thresholds
MAX_IDENTICAL_CALLS = 3  # Block after 3 identical calls
MAX_TOOL_CALLS_PER_MINUTE = 50  # Rate limit
DESTRUCTIVE_PATTERNS = [
    r"DROP\s+DATABASE",
    r"DELETE\s+FROM\s+\w+\s*;",  # DELETE without WHERE
    r"git\s+push.*--force\s+origin\s+(main|master)",
    r"chmod\s+-R\s+777\s+/",
    r">\s*/etc/",  # Overwriting system files
]

# Recursive deletion is irreversible: no confirmation, no trash. So the default answer is
# to refuse and let a human decide; only what rebuilds itself on its own goes through.
DISPOSABLE_NAMES = frozenset(
    {
        "dist", "build", "out", "target", "node_modules", ".next", ".nuxt", ".turbo",
        ".svelte-kit", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
        ".ruff_cache", ".cache", "coverage", ".parcel-cache", ".gradle", ".tox", "tmp",
    }
)
TEMP_ROOTS = ("/tmp/", "/private/tmp/", "/var/tmp/", "/var/folders/")
# Le temp d'un utilisateur Windows, sous sa forme `C:/` comme sous celle de Git Bash (`/c/`).
_WINDOWS_TEMP_ROOT = re.compile(r"^(?:[a-z]:|/[a-z])/users/[^/]+/appdata/local/temp/", re.IGNORECASE)
# Les formes longues de GNU coreutils comptent autant que les courtes : `--recursive`
# et `--force` existent sur Linux, et `-\w+` ne peut pas les reconnaitre puisque `\w`
# n'admet pas le tiret. Sans elles le garde laissait passer une suppression de la racine.
_RM_RECURSIVE = re.compile(
    r"\brm(?:\s+--?[\w-]+)*\s+(?:-\w*[rR]\w*|--recursive)(?:\s+--?[\w-]+)*"
)
# Le seul `$` et la seule accolade admis dans une cible, lus sur le texte brut : tout
# autre `$` (quote `$'…'`, variable non gardée) ou accolade (expansion) fait refuser.
_GUARDED_VARIABLE = re.compile(r"(?<!\\)\$\{\w+:\?\}")
# Une assignation littérale qui ouvre la commande, suivie de `;` ou `&&` et des blancs
# qui précèdent la commande suivante. La valeur n'admet ni blanc ni joker : bash ne peut
# pas la découper en plusieurs cibles, citée ou non. Sans guillemets, elle n'admet pas
# non plus d'antislash : bash le retire, et en fin de valeur il échappe le séparateur, ce
# qui fait de l'assignation un simple préfixe d'environnement du `rm`. Seuls les blancs
# que bash reconnaît comme séparateurs sont admis autour.
_LEADING_ASSIGNMENT = re.compile(
    r"[ \t\n]*(?:export[ \t]+)?([A-Za-z]\w*)=(\"[\w./:\\-]+\"|'[\w./:\\-]+'|[\w./:-]+)"
    r"[ \t]*(?:;|&&)[ \t]*"
)
# Coupe la liste des cibles au premier separateur de commande.
_COMMAND_BREAK = re.compile(r"[;&|\n)]")
# Une redirection se RETIRE, elle ne tronque pas. Tronquer a la premiere flechette
# jetait l'operande quand la redirection le precede : une suppression dont l'erreur
# est redirigee avant la cible est du shell valide, et le garde n'y voyait alors plus
# aucune cible -- donc il laissait passer. Le `\d*` avale le descripteur de fichier,
# le `&?` la forme qui fusionne les deux flux.
_REDIRECTION = re.compile(r"\d*\s*(?:>>|>|<)\s*&?\s*\S+")
# Marqueur d'exemption ligne à ligne, reconnu par gitleaks et par betterleaks.
_SECRET_EXEMPTION = re.compile(r"(?:git|better)leaks:allow", re.IGNORECASE)
SECRET_EXEMPTION_REASON = (
    "l'exemption gitleaks:allow est réservée à l'utilisateur (faux positif confirmé par lui)"
)


def utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_state() -> dict:
    """Load guardrail state from disk."""
    try:
        if STATE_FILE.is_file():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {"call_history": [], "session_calls": {}}


def save_state(state: dict) -> None:
    """Persist guardrail state."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def hash_call(tool_name: str, tool_input: dict) -> str:
    """Create a hash of a tool call for deduplication."""
    content = json.dumps({"tool": tool_name, "input": tool_input}, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()[:12]


def check_destructive(command: str) -> str | None:
    """Check if command matches destructive patterns."""
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None


def _deletion_targets(command: str) -> list[tuple[str, int]]:
    """Return the operands of every recursive `rm` found in the command.

    Each operand comes with the offset of its `rm` in `command`. Line continuations
    (`\\` + newline) are expected joined by the caller, as bash does, so a newline only
    ends the operand list when it really ends the command.
    """
    targets: list[tuple[str, int]] = []
    for match in _RM_RECURSIVE.finditer(command):
        tail = _REDIRECTION.sub(" ", command[match.end():])
        tail = _COMMAND_BREAK.split(tail, maxsplit=1)[0]
        targets.extend(
            (token, match.start()) for token in tail.split() if not token.startswith("-")
        )
    return targets


def _shell_word(token: str) -> str:
    """Return the word bash hands to the command for this token, before any expansion.

    Quotes are removed wherever they sit in the token. A backslash outside single quotes
    escapes the next character and disappears; inside double quotes it does so only
    before `$`, a backtick, `"` or `\\`, and stays literal otherwise.
    """
    word: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(token):
        char = token[i]
        if quote == "'":
            if char == "'":
                quote = None
            else:
                word.append(char)
        elif char == "\\" and i + 1 < len(token):
            escaped = token[i + 1]
            if quote == '"' and escaped not in '$`"\\':
                word.append(char)
            else:
                word.append(escaped)
                i += 1
        elif char in "'\"" and quote in (None, char):
            quote = None if quote else char
        else:
            word.append(char)
        i += 1
    return "".join(word)


def _rebuilds_itself(target: str) -> bool:
    """Say whether deleting this path destroys anything that cannot be regenerated.

    The path is normalised as a POSIX path on every OS first, a backslash counting as a
    separator: `/tmp/../etc` starts with a temporary root but names
    a system directory, and comparing the raw prefix would let it through.
    """
    path = posixpath.normpath(target.replace("\\", "/")).rstrip("/")
    if not path or path in {".", ".."}:
        return False
    if any(path.startswith(root) for root in TEMP_ROOTS) or _WINDOWS_TEMP_ROOT.match(path):
        return True
    return path.rsplit("/", 1)[-1] in DISPOSABLE_NAMES


def _leading_assignment(command: str, rm_start: int) -> tuple[str, str] | None:
    """Return the `(name, value)` the command opens with, when its next command is the `rm`.

    None unless `command` starts with `name=<literal>` (or `export name=<literal>`),
    followed by `;` or `&&` and directly by the recursive `rm` found at `rm_start`.
    The name is a single letter or holds a lowercase letter, which no variable bash
    manages itself (`1`, `_`, `PWD`, `OLDPWD`, `RANDOM`, `UID`...) does.
    """
    match = _LEADING_ASSIGNMENT.match(command)
    if not match or match.end() != rm_start:
        return None
    name = match.group(1)
    if len(name) > 1 and name.isupper():
        return None
    return name, _shell_word(match.group(2))


def check_recursive_delete(command: str) -> str | None:
    """Refuse a recursive delete unless its target is known to rebuild itself.

    The previous rule matched a recursive delete followed by `/` or `~`, which is every
    absolute path -- so it stopped a build directory under /tmp as readily as the root
    itself, and let a relative target through entirely. This one reads the operand
    instead of the prefix, and its default is to refuse: a hole matters here, where a
    false positive only costs a round trip.
    """
    command = command.replace("\\\n", "")
    for target, position in _deletion_targets(command):
        operand = _shell_word(target)
        unguarded = _GUARDED_VARIABLE.sub("", target)
        if "{" in unguarded:
            return f"recursive delete on a brace expansion ({operand}) -- list the paths instead"
        # An unset variable is the classic way to delete the root: the path collapses to
        # nothing and the slash after it becomes the target. Bash only guarantees a value
        # with the `${VAR:?}` form -- `set -u` still lets an empty value through.
        if "$" in unguarded:
            return (
                f"recursive delete on an unguarded variable path ({operand}) -- "
                "use ${VAR:?} so the shell fails instead of expanding to nothing"
            )
        if _rebuilds_itself(operand):
            continue
        assignment = _leading_assignment(command, position)
        resolved = operand
        for name in set(re.findall(r"\$\{(\w+):\?\}", operand)):
            if assignment is None or assignment[0] != name:
                return (
                    f"recursive delete on a variable whose value is unknown here ({operand}) -- "
                    "open the command with d=<literal path, no blank nor wildcard>; then the rm "
                    "on ${d:?} -- a single-letter or lowercase name -- or write the path"
                )
            resolved = resolved.replace(f"${{{name}:?}}", assignment[1])
        if not _rebuilds_itself(resolved):
            return f"recursive delete on a path that does not rebuild itself ({resolved})"
    return None


def _count_exemptions(text: object) -> int:
    """Count the secret exemption markers in `text`; anything but a string counts 0."""
    return len(_SECRET_EXEMPTION.findall(text)) if isinstance(text, str) else 0


def _adds_exemption(old: object, new: object) -> bool:
    """Say whether `new` carries more secret exemption markers than `old`."""
    return _count_exemptions(new) > _count_exemptions(old)


def _read_text(path: object) -> str | None:
    """Return the UTF-8 content of the file at `path`, or None when it cannot be read."""
    if not isinstance(path, str) or not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _notebook_cell_source(tool_input: dict) -> str | None:
    """Return the source of the cell a NotebookEdit replaces, or None when unknown.

    An insert replaces nothing, so it yields None, as does an unreadable notebook or a
    missing cell id.
    """
    if tool_input.get("edit_mode") == "insert":
        return None
    raw = _read_text(tool_input.get("notebook_path"))
    cell_id = tool_input.get("cell_id")
    if raw is None or not cell_id:
        return None
    try:
        cells = json.loads(raw).get("cells", [])
    except (json.JSONDecodeError, AttributeError):
        return None
    for cell in cells if isinstance(cells, list) else []:
        if isinstance(cell, dict) and cell.get("id") == cell_id:
            source = cell.get("source", "")
            return "".join(source) if isinstance(source, list) else source
    return None


def check_secret_exemption(tool_name: str, tool_input: dict) -> str | None:
    """Return the refusal reason when a Write, Edit, MultiEdit or NotebookEdit adds an exemption marker.

    Markers are counted: the call passes when the new text holds no more of them than what
    it replaces -- `old_string` for an edit, the file on disk for a Write, the replaced cell
    for a NotebookEdit (0 when absent or unreadable). Any other tool, or a malformed input,
    passes.
    """
    if not isinstance(tool_input, dict):
        return None
    if tool_name == "Write":
        pairs = [(_read_text(tool_input.get("file_path")), tool_input.get("content"))]
    elif tool_name == "Edit":
        pairs = [(tool_input.get("old_string"), tool_input.get("new_string"))]
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        pairs = [
            (edit.get("old_string"), edit.get("new_string"))
            for edit in (edits if isinstance(edits, list) else [])
            if isinstance(edit, dict)
        ]
    elif tool_name == "NotebookEdit":
        pairs = [(_notebook_cell_source(tool_input), tool_input.get("new_source"))]
    else:
        return None
    if any(_adds_exemption(old, new) for old, new in pairs):
        return SECRET_EXEMPTION_REASON
    return None


def main() -> None:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        if not raw.strip():
            return
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    if not isinstance(data, dict):
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    if not tool_name:
        return

    state = load_state()
    call_hash = hash_call(tool_name, tool_input)
    now = utc_ts()

    # Initialize session tracking
    if session_id not in state["session_calls"]:
        state["session_calls"][session_id] = {"hashes": [], "last_ts": now}

    session_data = state["session_calls"][session_id]

    # Check for loop (identical consecutive calls)
    recent_hashes = session_data["hashes"][-10:]  # Last 10 calls
    consecutive_identical = 0
    for h in reversed(recent_hashes):
        if h == call_hash:
            consecutive_identical += 1
        else:
            break

    should_block = False
    block_reason = ""

    # Loop detection
    if consecutive_identical >= MAX_IDENTICAL_CALLS:
        should_block = True
        block_reason = f"Loop detected: {tool_name} called {consecutive_identical + 1}x with same args"

    # Destructive command detection (Bash only)
    if tool_name == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command", "")
        destructive_pattern = check_destructive(command)
        if destructive_pattern:
            should_block = True
            block_reason = f"Destructive command blocked: {destructive_pattern}"
        else:
            deletion = check_recursive_delete(command)
            if deletion:
                should_block = True
                block_reason = f"Destructive command blocked: {deletion}"

    exemption = check_secret_exemption(tool_name, tool_input)
    if exemption:
        should_block = True
        block_reason = exemption

    # Update state
    session_data["hashes"].append(call_hash)
    session_data["hashes"] = session_data["hashes"][-50:]  # Keep last 50
    session_data["last_ts"] = now
    save_state(state)

    if should_block:
        response = {
            "decision": "block",
            "reason": block_reason,
        }
        print(json.dumps(response))
        sys.stderr.reconfigure(encoding="utf-8")
        print(block_reason, file=sys.stderr)
        sys.exit(2)  # Exit code 2 = block


if __name__ == "__main__":
    main()
