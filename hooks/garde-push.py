#!/usr/bin/env python3
"""Garde de push, côté Claude — hook PreToolUse sur Bash et PowerShell.

Le refus d'un push vers main appartient au hook git `git-hooks/pre-push`, celui d'un
secret indexé au hook git `git-hooks/pre-commit`. Ce hook-ci empêche seulement une commande
de l'agent de les désarmer : il refuse (sortie 2) une commande qui contient

- `--no-verify`, ou l'une de ses abréviations dès `--no-ver`, avec le mot `push` ;
- `--no-verify` (mêmes abréviations) ou `-n` comme option d'un `git commit` : `-n` seul ou
  groupé (`-anm`), avant toute lettre qui prend une valeur (`-mnote` est un message) ;
- `core.hooksPath` ;
- `ALLOW_PUSH_MAIN` ;
- `garde.pushMain` ;
- `ALLOW_PUSH_PERSONAL` ;
- `GARDE_PUBLIC_MARQUEURS` ;
- `ALLOW_COMMIT_SECRET`, le contournement du garde secrets du pre-commit ;
- `sans-externes` ou `SansExternes` : l'option d'installation sans externes et son mémo
  `~/.claude/claude-config.sans-externes`, qui désarment le garde secrets ;
- le marqueur d'exemption de gitleaks ou betterleaks (`…leaks:allow`), où qu'il soit dans
  la commande : l'exemption d'un faux positif reste à l'utilisateur ;
- une invocation de git, avec dans la même commande une affectation ou un retrait de
  `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_COUNT`,
  `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_KEY_<n>`, `GIT_CONFIG_VALUE_<n>`, `HOME` ou
  `XDG_CONFIG_HOME` (préfixe, `+=`, `export`, `export -n`, `unset`, `env -u`, `$env:`, le
  lecteur `Env:` de PowerShell, `SetEnvironmentVariable`), ou un `env -i` / `env -` : sans
  configuration globale, plus de `core.hooksPath`. Une commande lancée dans une chaîne
  (`sh -c '…'`, `eval`) ou un script sourcé n'est pas inspectée.

Git est reconnu nu ou par son chemin, `git.exe` compris. La comparaison ignore la casse. Tout le reste passe (sortie 0), y compris une entrée
illisible ou sans commande.

Cas de test : `python3 hooks/garde-push.test.py`
"""

from __future__ import annotations

import json
import re
import shlex
import sys

GARDE_PUSH = "le garde de push (hook git pre-push)"
GARDE_SECRETS = "le garde secrets (hook git pre-commit)"
GARDE_HOOKS = "les hooks git, garde de push et garde secrets compris"
EXEMPTION = "gitleaks:allow"

_MOTIFS_INTERDITS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"core\.hookspath", re.IGNORECASE), "core.hooksPath", GARDE_HOOKS),
    (re.compile(r"allow_push_main", re.IGNORECASE), "ALLOW_PUSH_MAIN", GARDE_PUSH),
    (re.compile(r"garde\.pushmain", re.IGNORECASE), "garde.pushMain", GARDE_PUSH),
    (re.compile(r"allow_push_personal", re.IGNORECASE), "ALLOW_PUSH_PERSONAL", GARDE_PUSH),
    (re.compile(r"garde_public_marqueurs", re.IGNORECASE), "GARDE_PUBLIC_MARQUEURS", GARDE_PUSH),
    (re.compile(r"allow_commit_secret", re.IGNORECASE), "ALLOW_COMMIT_SECRET", GARDE_SECRETS),
    (re.compile(r"sans-?externes", re.IGNORECASE), "sans-externes", GARDE_SECRETS),
    (re.compile(r"(?:git|better)leaks:allow", re.IGNORECASE), EXEMPTION, GARDE_SECRETS),
)
_NO_VERIFY = re.compile(r"--no-ver(?:i(?:fy?)?)?\b", re.IGNORECASE)
_MOT_PUSH = re.compile(r"\bpush\b", re.IGNORECASE)
_SEPARATEURS = frozenset({"&&", "||", ";", "|", "&", "(", ")", ";;", "|&"})
_OPTIONS_GIT_A_VALEUR = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_LETTRES_COMMIT_A_VALEUR = frozenset("mFcCtuS")
_OPTION_COURTE = re.compile(r"-[A-Za-z]+")
_NOMS_GIT = frozenset({"git", "git.exe"})
_VARIABLE_DE_CONFIG = (
    r"(?:GIT_CONFIG_(?:GLOBAL|SYSTEM|NOSYSTEM|COUNT|PARAMETERS|KEY_\d+|VALUE_\d+)"
    r"|XDG_CONFIG_HOME|HOME)"
)
_ENVIRONNEMENT_DE_GIT = re.compile(
    rf"(?<![\w$])(?:\$env:)?{_VARIABLE_DE_CONFIG}(?=\s*\+?=)"
    rf"|\b(?:unset|export\s+-n)(?:\s+[-\w]+)*?\s+{_VARIABLE_DE_CONFIG}\b"
    rf"|\benv\s+(?:-u\s*|--unset[=\s]\s*){_VARIABLE_DE_CONFIG}\b"
    r"|\benv\s+(?:-[a-z]*i[a-z]*|--ignore-environment|-)(?=\s)"
    rf"|(?<![\w$])Env:{_VARIABLE_DE_CONFIG}\b"
    rf"|SetEnvironmentVariable\(\s*['\"]{_VARIABLE_DE_CONFIG}['\"]",
    re.IGNORECASE,
)
_ANTISLASH_DE_CHEMIN = re.compile(r"\\(?=[\w.-])")


def _est_git(jeton: str) -> bool:
    """Vrai si `jeton` désigne l'exécutable git, nu ou par un chemin `/` ou `\\`, `git.exe` compris."""
    return re.split(r"[/\\]", jeton)[-1].lower() in _NOMS_GIT


def _jetons(commande: str) -> list[str]:
    """Découpe `commande` en mots shell, séparateurs isolés ; repli sur les espaces si les guillemets sont déséquilibrés.

    Un antislash suivi d'une lettre, d'un chiffre, `_`, `.` ou `-` devient `/` : un chemin
    Windows (`C:\\Git\\cmd\\git.exe`) garde ses séparateurs.
    """
    commande = _ANTISLASH_DE_CHEMIN.sub("/", commande)
    try:
        lexer = shlex.shlex(commande, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return commande.split()


def _options_de_commit(jetons: list[str]) -> list[str]:
    """Rend les mots qui suivent chaque `git [options] commit`, jusqu'au séparateur shell suivant."""
    options: list[str] = []
    i = 0
    while i < len(jetons):
        if not _est_git(jetons[i]):
            i += 1
            continue
        i += 1
        while i < len(jetons) and jetons[i].startswith("-"):
            i += 2 if jetons[i] in _OPTIONS_GIT_A_VALEUR else 1
        if i < len(jetons) and jetons[i] == "commit":
            i += 1
            while i < len(jetons) and jetons[i] not in _SEPARATEURS:
                options.append(jetons[i])
                i += 1
    return options


def _desarme_le_pre_commit(option: str) -> bool:
    """Vrai si `option` de `git commit` vaut `--no-verify` (ou abréviation) ou porte `-n`, seul ou groupé."""
    if _NO_VERIFY.fullmatch(option):
        return True
    if not _OPTION_COURTE.fullmatch(option):
        return False
    for lettre in option[1:]:
        if lettre == "n":
            return True
        if lettre in _LETTRES_COMMIT_A_VALEUR:
            return False
    return False


def motif_refuse(commande: str) -> tuple[str, str] | None:
    """Rend le réglage protégé que cite `commande` et le garde qu'il désarme, ou None si elle passe."""
    if _NO_VERIFY.search(commande) and _MOT_PUSH.search(commande):
        return "push --no-verify", GARDE_PUSH
    jetons = _jetons(commande)
    if any(_desarme_le_pre_commit(option) for option in _options_de_commit(jetons)):
        return "commit --no-verify / -n", GARDE_SECRETS
    for motif, nom, garde in _MOTIFS_INTERDITS:
        if motif.search(commande):
            return nom, garde
    environnement = _ENVIRONNEMENT_DE_GIT.search(commande)
    if environnement and any(_est_git(jeton) for jeton in jetons):
        return f"{environnement.group(0).strip()} devant git", GARDE_HOOKS
    return None


def commande_de(brut: str) -> str | None:
    """Extrait `tool_input.command` du JSON de l'événement ; None si absent ou illisible."""
    try:
        evenement = json.loads(brut)
    except ValueError:
        return None
    if not isinstance(evenement, dict):
        return None
    entree = evenement.get("tool_input")
    if not isinstance(entree, dict):
        return None
    commande = entree.get("command")
    return commande if isinstance(commande, str) else None


def main() -> int:
    """Lit l'événement sur stdin ; rend 2 avec un message sur stderr si la commande est refusée, 0 sinon."""
    commande = commande_de(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    if commande is None:
        return 0
    refus = motif_refuse(commande)
    if refus is None:
        return 0
    nom, garde = refus
    sys.stderr.reconfigure(encoding="utf-8")
    if nom == EXEMPTION:
        print(
            "garde-push : commande refusée, "
            "l'exemption gitleaks:allow est réservée à l'utilisateur (faux positif confirmé par lui). "
            'Pour chercher les exemptions existantes : rg "leaks:allow".',
            file=sys.stderr,
        )
        return 2
    if garde == GARDE_PUSH:
        consigne = "Le push vers main passe par une pull request. "
    elif garde == GARDE_SECRETS:
        consigne = "Un secret détecté se retire du commit, il ne se force pas. "
    else:
        consigne = ""
    print(
        f"garde-push : commande refusée, elle touche à « {nom} ». "
        f"Ce réglage désarme {garde} et reste réservé à l'utilisateur. "
        f"{consigne}"
        "Pour un texte qui cite ce réglage (corps de PR, commentaire), "
        "l'écrire dans un fichier avec l'outil d'écriture puis le passer par --body-file ou -F body=@.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
