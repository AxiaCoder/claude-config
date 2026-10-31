#!/usr/bin/env python3
"""Cas de test de garde-push.py, lancé en sous-processus. Sortie 0 si tous passent.

`python3 hooks/garde-push.test.py`
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

_HOOK = pathlib.Path(__file__).resolve().parent / "garde-push.py"

# Assemblées par morceaux : le garde actif de la session lit aussi la commande qui lance ce fichier.
NV = "--no-" + "verify"
HP = "core." + "hooksPath"
APM = "ALLOW_" + "PUSH_" + "MAIN"
GPM = "garde." + "pushMain"
APP = "ALLOW_" + "PUSH_" + "PERSONAL"
GPMQ = "GARDE_" + "PUBLIC_" + "MARQUEURS"
ACS = "ALLOW_" + "COMMIT_" + "SECRET"
PM = "push origin " + "ma" + "in"
SE = "sans-" + "externes"
SEP = "Sans" + "Externes"
GA = "gitleaks" + ":allow"
BA = "betterleaks" + ":allow"
GCG = "GIT_CONFIG_" + "GLOBAL"
GCS = "GIT_CONFIG_" + "SYSTEM"
GCN = "GIT_CONFIG_" + "NOSYSTEM"
GCC = "GIT_CONFIG_" + "COUNT"
GCK = "GIT_CONFIG_" + "KEY_"
GCV = "GIT_CONFIG_" + "VALUE_"
HO = "HO" + "ME"
XCH = "XDG_" + "CONFIG_" + "HOME"
GCP = "GIT_CONFIG_" + "PARAMETERS"

REFUS, PASSE = 2, 0
DELAI = 2.0

CAS: tuple[tuple[int, str], ...] = (
    # --- doivent être refusés ---
    (REFUS, f"git {PM} {NV}"),
    (REFUS, f"git push {NV}"),
    (REFUS, f"git push {NV} origin feat/x"),
    (REFUS, f"git -C repo push {NV.upper()}"),
    (REFUS, f"cd repo && git commit -m x && git push {NV}"),
    (REFUS, f"git push {NV[:-1]} origin feat/x"),
    (REFUS, f"git push {NV[:-2]}"),
    (REFUS, f"git push {NV[:-3]}"),
    (REFUS, f"git config --global {HP} /dev/null"),
    (REFUS, f"git config --global --unset {HP}"),
    (REFUS, f"git -c {HP}=/tmp/vide {PM}"),
    (REFUS, f"git config --global {HP.lower()} x"),
    (REFUS, f"GIT_CONFIG_KEY_0={HP} git push"),
    (REFUS, f"{APM}=1 git {PM}"),
    (REFUS, f"export {APM}=1"),
    (REFUS, f"$env:{APM} = '1'; git {PM}"),
    (REFUS, f"git config --local {GPM} off"),
    (REFUS, f"git config {GPM.upper()} off"),
    (REFUS, f"gh pr create --body 'voir {APM}'"),
    (REFUS, f"{APP}=1 git push origin feat/x"),
    (REFUS, f"export {APP}=1"),
    (REFUS, f"$env:{APP} = '1'; git push"),
    (REFUS, f"{APP.lower()}=1 git push"),
    (REFUS, f"{GPMQ}= git push origin feat/x"),
    (REFUS, f"export {GPMQ}=''"),
    (REFUS, f"unset {GPMQ}; git push"),
    (REFUS, f"env -u {GPMQ} git push"),
    (REFUS, f"Remove-Item Env:{GPMQ}; git push"),
    (REFUS, f"{GPMQ.lower()}=x git push"),
    (REFUS, f"{ACS}=1 git commit -m x"),
    (REFUS, f"export {ACS}=1"),
    (REFUS, f"$env:{ACS} = '1'; git commit -m x"),
    (REFUS, f"{ACS.lower()}=1 git commit -m x"),
    (REFUS, f"git commit {NV} -m x"),
    (REFUS, f"git commit {NV} -m 'pushed fix'"),
    (REFUS, f"git commit {NV[:-2]} -m x"),
    (REFUS, "git commit -n -m x"),
    (REFUS, "git commit -anm x"),
    (REFUS, "git commit -nm x"),
    (REFUS, "git -C repo commit -n -m x"),
    (REFUS, "git add . && git commit -an -m 'wip'"),
    (REFUS, f"git -c {HP}=/dev/null commit -m x"),
    (REFUS, f"touch ~/.claude/claude-config.{SE} && git commit -m x"),
    (REFUS, f"bash install.sh --{SE}"),
    (REFUS, f".\\install.ps1 -{SEP}"),
    (REFUS, f"New-Item $HOME/.claude/claude-config.{SE}"),
    (REFUS, f"echo > ~/.claude/claude-config.{SE.upper()}"),
    (REFUS, f"echo 'token = 1  # {GA}' >> config.py"),
    (REFUS, f"sed -i '' 's/$/ # {GA}/' config.py"),
    (REFUS, f"printf '%s\\n' '# {GA.upper()}' | tee -a config.py"),
    (REFUS, f"cat >> config.py <<'EOF'\nx = 1  # {BA}\nEOF"),
    (REFUS, f"git commit -m 'ajoute {GA}'"),
    # --- environnement de git : préfixe ---
    (REFUS, f"{GCG}=/dev/null git commit -m x"),
    (REFUS, f"{GCS}=/dev/null git push origin feat/x"),
    (REFUS, f"{GCN}=1 git commit -m x"),
    (REFUS, f"{GCC}=1 {GCK}0=core.editor {GCV}0=vim git commit -m x"),
    (REFUS, f"{GCV}0=/dev/null git push"),
    (REFUS, f"{HO}=/tmp git commit -m x"),
    (REFUS, f"{XCH}=/tmp git push origin feat/x"),
    (REFUS, f"{GCG.lower()}=/dev/null git commit -m x"),
    (REFUS, f"{HO.lower()}=/tmp git push"),
    (REFUS, f"cd repo && {HO}=/tmp git commit -m x"),
    # --- environnement de git : instruction séparée ---
    (REFUS, f"export {GCG}=/dev/null; git commit -m x"),
    (REFUS, f"export {HO}=/tmp && git push origin feat/x"),
    (REFUS, f"{GCG}=/dev/null; git commit -m x"),
    (REFUS, f"{XCH}=/tmp && git push"),
    (REFUS, f"unset {HO}; git commit -m x"),
    (REFUS, f"unset {XCH} && git push"),
    # --- environnement de git : PowerShell ---
    (REFUS, f"$env:{GCG} = 'NUL'; git commit -m x"),
    (REFUS, f"$env:{HO}='C:/tmp'; git push"),
    (REFUS, f"$env:{XCH.lower()} = 'C:/tmp'; git push"),
    (REFUS, f"Remove-Item Env:{HO}; git commit -m x"),
    (REFUS, f"Remove-Item Env:{GCS}; git push"),
    # --- environnement de git : env ---
    (REFUS, f"env {GCG}=/dev/null git commit -m x"),
    (REFUS, f"env {HO}=/tmp git push"),
    (REFUS, f"env -u {HO} git commit -m x"),
    (REFUS, f"env -u {XCH} git push"),
    (REFUS, "env -i git commit -m x"),
    (REFUS, "env -i PATH=/usr/bin git push origin feat/x"),
    (REFUS, "env --ignore-environment git commit -m x"),
    (REFUS, f"env -u{HO} git push"),
    (REFUS, f"{HO}= git commit -m x"),
    (REFUS, f"declare -x {HO}=/tmp; git commit -m x"),
    (REFUS, f"$env:{HO}=$null; git push"),
    # --- git désigné par son chemin ---
    (REFUS, "/usr/bin/git commit -n -m x"),
    (REFUS, '"C:/Program Files/Git/cmd/git.exe" commit -n -m x'),
    (REFUS, "git.exe commit -n -m x"),
    (REFUS, f"{HO}=/tmp /usr/bin/git push origin feat/x"),
    (REFUS, f"{GCG}=/dev/null git.exe commit -m x"),
    (REFUS, "GIT.EXE commit -n -m x"),
    (REFUS, "C:\\Git\\cmd\\git.exe commit -n -m x"),
    # --- environnement de git : formes détournées ---
    (REFUS, f"export -n {HO}; git commit -m x"),
    (REFUS, f"unset -v {HO}; git commit -m x"),
    (REFUS, f"unset FOO {HO}; git commit -m x"),
    (REFUS, f"env --unset={HO} git commit -m x"),
    (REFUS, "env - git commit -m x"),
    (REFUS, "env -iv git commit -m x"),
    (REFUS, f"{HO}+=x git commit -m x"),
    (REFUS, f"{GCG}+=x git commit -m x"),
    (REFUS, f"Set-Item Env:{HO} x; git push"),
    (REFUS, f"Remove-Item -Path Env:{HO}; git push"),
    (REFUS, f"rm env:{HO}; git push"),
    (REFUS, f"[Environment]::SetEnvironmentVariable('{HO}','x'); git push"),
    (REFUS, f"export {GCP}=x; git push"),
    (PASSE, f"cd $env:{HO}; git status"),
    (PASSE, "echo $env:USERPROFILE; git log"),
    (PASSE, "unset FOO; git status"),
    (PASSE, "env -u FOO git status"),
    # --- antislash d'échappement bash ---
    (REFUS, "git commit \\-n -m x"),
    (REFUS, "git commit -\\n -m x"),
    (REFUS, f"git commit \\{NV} -m x"),
    (REFUS, "git commit --no\\-" + "verify -m x"),
    (REFUS, "g\\it commit -n -m x"),
    (REFUS, "gi\\t commit -n -m x"),
    # --- environnement de git : options intercalées ---
    (REFUS, f"declare +x {HO}; git push"),
    (REFUS, f"typeset +x {HO}; git push"),
    (REFUS, f"local +x {HO}; git push"),
    (REFUS, f"env -v -u {HO} git push"),
    (REFUS, f"env -C . -u {HO} git push"),
    (REFUS, "env -C . -i git push"),
    (REFUS, "env --chdir=. -i git push"),
    (REFUS, f"Remove-Item Env:\\{HO}; git push"),
    (REFUS, f"Remove-Item Env:/{HO}; git push"),
    (PASSE, f"cd ${{env:{HO}}}; git status"),
    (PASSE, "git commit -i -m x"),
    (PASSE, "env FOO=1 git commit -i -m x"),
    (PASSE, "env -u FOO git commit -m x"),
    # --- environnement de git : passe 2 ---
    (REFUS, f"${{env:{HO}}} = 'x'; git push"),
    (REFUS, f"${{env:{GCG}}}='NUL'; git commit -m x"),
    (REFUS, f"env --unset FOO -u {HO} git push"),
    (REFUS, f"env --chdir . -u {HO} git push"),
    (REFUS, "env --chdir / -i git push"),
    (REFUS, f"env -vu {HO} git push"),
    (REFUS, "env -S x -i git push"),
    (REFUS, f"declare -g +x {HO}; git push"),
    (REFUS, f"typeset -r +x {HO}; git push"),
    (REFUS, f"export -n FOO {HO}; git push"),
    (PASSE, "env -u FOO -u BAR git status"),
    (PASSE, "env --chdir . git status"),
    (PASSE, "declare -g X=1; git status"),
    (PASSE, "env git commit -i -m x"),
    (PASSE, "env" + " -u" * 40 + " x"),
    (PASSE, "env" + " -u" * 40 + " git status"),
    # --- environnement de git : env par son nom ou une option abrégée ---
    (REFUS, "ENV -i git push"),
    (REFUS, "env.exe -i git push"),
    (REFUS, f"/usr/bin/env.exe -u {HO} git push"),
    (REFUS, f"Env -u {HO} git push"),
    (REFUS, f"env --u {HO} git push"),
    (REFUS, f"env --u={HO} git push"),
    (REFUS, "env --c / -i git push"),
    (REFUS, "env --s x -i git push"),
    (PASSE, "env --chdir=/ git status"),
    (PASSE, "ENV git status"),
    # --- noms recollés par le shell : guillemets accolés, antislash ---
    (REFUS, 'export "HO""ME=/tmp"; git push'),
    (REFUS, "export 'HO''ME=/tmp'; git push"),
    (REFUS, "HO\\ME=/tmp git push"),
    (REFUS, '"HO"ME=/tmp git push'),
    (REFUS, "'HO'ME=/tmp git push"),
    (REFUS, 'XDG_CONFIG_"HOME"=/tmp git push'),
    (REFUS, "GIT_CONFIG_\\COUNT=1 git push"),
    (REFUS, 'export GIT_CONFIG_"GLOBAL"=/x; git push'),
    (REFUS, "export GIT_CONFIG_'SYSTEM'=/x; git push"),
    (REFUS, 'git -c core."hooks"Path=/dev/null push'),
    (REFUS, "git -c 'core.hooks'Path=/dev/null push"),
    (REFUS, "git -c core.hooks\\Path=/dev/null push"),
    (REFUS, 'git config core.hook"s"Path /dev/null'),
    (REFUS, "ALLOW_" + "PUSH_" + '"MAIN"=1 git push'),
    (REFUS, "ALLOW_" + "PUSH_" + "MA\\IN=1 git push"),
    (REFUS, 'git -c garde."push"Main=true push'),
    (REFUS, "ALLOW_" + "PUSH_" + "'PERSONAL'=1 git push"),
    (REFUS, "GARDE_" + "PUBLIC_" + '"MARQUEURS"=/dev/null git push'),
    (REFUS, "ALLOW_" + "COMMIT_" + '"SECRET"=1 git commit -m x'),
    (REFUS, "bash install.sh --sans-" + '"externes"'),
    (REFUS, "echo '# gitleaks'" + "':allow' >> f.py"),
    (REFUS, 'git push --no-"verify"'),
    (REFUS, "git push --no-'verify'"),
    (REFUS, "git push --no-ver\\ify"),
    (PASSE, 'git commit -m "x" && echo garde\\ ok'),
    (PASSE, "git commit -m 'fix: core hooks' && git push"),
    (PASSE, 'export "HO""MEPAGE=x"; git status'),
    (PASSE, 'git push --no-"verbose"'),
    (PASSE, "git log --grep 'p''ush' -n 5"),
    (REFUS, "export HO''ME=/tmp; git push"),
    (REFUS, 'export HO""ME=/tmp; git push'),
    (REFUS, "git p\\ush " + NV),
    (REFUS, 'git pu""sh ' + NV),
    (REFUS, 'git p\\ush --no-"verify"'),
    (REFUS, f'{HO}=/tmp git push "'),
    (REFUS, 'export "HO""ME=/tmp"; git push; echo $\'it\\\'s\''),
    (REFUS, 'git -c core."hooks"Path=/dev/null push; echo $\'it\\\'s\''),
    (PASSE, 'git log --grep "push" --no-"verbose"'),
    (REFUS, 'git push --no-"verify"; echo $\'it\\\'s\''),
    (REFUS, "ALLOW_" + "PUSH_" + "MA\\IN=1 git push; echo $'it\\'s'"),
    (PASSE, "cd C:\\Users\\me\\HO\\ME; git status"),
    (PASSE, "Set-Location C:\\Users\\me; $env:PATH = 'C:\\Git\\cmd'; git status"),
    (PASSE, "git -C C:\\Users\\me\\repo push origin feat"),
    (PASSE, 'git commit -m "it\'s done" && git push'),
    (REFUS, "export $''HO''ME=/tmp; git push"),
    (REFUS, 'export $"HO"ME=/tmp; git push'),
    (REFUS, "declare $''HO''ME=/tmp; git push"),
    (REFUS, 'typeset -x $"HO"ME=/tmp; git push'),
    (REFUS, "git commit -\"n\" -m x; echo $'it\\'s'"),
    (REFUS, "git commit --no-\"verify\" -m x; echo $'it\\'s'"),
    (REFUS, "unset HO''ME; git push; echo $'it\\'s'"),
    (REFUS, "env -u HO''ME git push; echo $'it\\'s'"),
    (REFUS, "export -n HO''ME; git push; echo $'it\\'s'"),
    (REFUS, "declare +x HO''ME; git push; echo $'it\\'s'"),
    (REFUS, "HO\\\nME=/tmp git push"),
    (REFUS, "export HO\\\r\nME=/tmp; git push"),
    (REFUS, "unset HO\\\nME; git push"),
    (REFUS, "git -c core.hoo\\\nksPath=/dev/null push"),
    (REFUS, "git push --no-v\\\nerify"),
    (REFUS, "git commit -\\\nn -m x"),
    (REFUS, "ALLOW_" + "PUSH_" + "MA\\\nIN=1 git push"),
    (PASSE, "git status\ngit log -n 1"),
    (REFUS, "cd D:\\repo\\\r\ngit commit -n -m x"),
    (REFUS, "cd D:\\repo\\\ngit commit -n -m x"),
    # --- saut de ligne séparateur de commandes ---
    (PASSE, "git commit -m x\ngit log -n 1"),
    (PASSE, "git commit -m x\r\ngit log -n 1"),
    (PASSE, "git commit -m x\n\ngit log -n 1"),
    (REFUS, f"git commit -m x\ngit push {NV}"),
    (REFUS, f"git commit -m x\r\ngit push {NV}"),
    (REFUS, "git status\ngit commit -n -m x"),
    (REFUS, "git log -n 1\ngit commit -n -m x"),
    (REFUS, "git commit -m x \\\n -n"),
    (REFUS, "git commit -m x \\\r\n -n"),
    (REFUS, "C:\\Git\\cmd\\git.exe commit -m x \\\n -n"),
    (REFUS, "git commit -m 'a\nb' -n"),
    (REFUS, 'git commit -m "a\nb" -n'),
    (REFUS, "git commit -m 'a\r\nb' -n"),
    (REFUS, "git commit -m '\n' -n"),
    (REFUS, 'git commit -m "a\\"\nb" -n'),
    (REFUS, f"export {HO}=/tmp\ngit push"),
    (REFUS, f"{HO}=/tmp\ngit push"),
    (REFUS, f"unset {HO}\r\ngit push"),
    (REFUS, f"$env:{HO}='C:/tmp'\r\ngit push"),
    (REFUS, f"git status\n{GCG}=/dev/null git commit -m x"),
    (REFUS, "echo ok\ngit -c core.hooksPath=/dev/null push"),
    (PASSE, 'echo \\"\ngit commit -m x\ngit log -n 1'),
    (PASSE, "echo 'a\\'\ngit commit -m x\ngit log -n 1"),
    (PASSE, "echo \"it's\"\ngit commit -m x\ngit log -n 1"),
    (REFUS, "git commit -m x\\\n-n"),
    # --- commentaire shell clos par le saut de ligne ---
    (REFUS, "echo hi # c\ngit commit -n -m x"),
    (REFUS, "echo hi # c\r\ngit commit -n -m x"),
    (REFUS, "curl http://x/#frag\ngit commit -n -m x"),
    (REFUS, "echo a#b\ngit commit -n -m x"),
    (REFUS, "echo a#b\r\ngit commit -n -m x"),
    (REFUS, f"echo hi #c\n{HO}=/tmp git push"),
    (REFUS, "echo hi # c\nenv -i git push"),
    (REFUS, f"git status #\nunset {HO}; git push"),
    (REFUS, f"git status #\r\nunset {HO}; git push"),
    (REFUS, "git commit -m \"titre\n\ncorps\" -n # it's"),
    (REFUS, "git commit -m \"titre\r\n\r\ncorps\" -n # it's"),
    (REFUS, "echo $'\\''\ngit commit -m \"a\nb\" -n"),
    (REFUS, "git commit -m \"a\nb\" -n; echo $'it\\'s'"),
    # --- continuation PowerShell : backtick en fin de ligne ---
    (REFUS, "git commit -m x `\n-n"),
    (REFUS, "git commit -m x `\r\n-n"),
    (REFUS, f"git commit -m x `\n{NV}"),
    # --- doivent passer ---
    (PASSE, f"echo ${HO}"),
    (PASSE, f'cd "${HO}" && git status'),
    (PASSE, "ls ~ && git log"),
    (PASSE, f"{HO}=/tmp npm test"),
    (PASSE, f"{XCH}=/tmp nvim"),
    (PASSE, "env FOO=1 git status"),
    (PASSE, "/usr/bin/git status"),
    (PASSE, "git.exe log"),
    (PASSE, f"git commit -m '{HO} sweet home'"),
    (PASSE, "export GIT" + HO + "=x; git status"),
    (PASSE, "CLAUDE_" + HO + "=/tmp git status"),
    (PASSE, "echo gitleaks detect"),
    (PASSE, "git push"),
    (PASSE, f"git {PM}"),
    (PASSE, "git push -u origin feat/garde"),
    (PASSE, f"echo {NV}"),
    (PASSE, "git log -n 5"),
    (PASSE, "head -n 3 fichier"),
    (PASSE, "git commit -m \"voir -n\""),
    (PASSE, "git commit -m x && git log -n 1"),
    (PASSE, "git commit -am wip"),
    (PASSE, "git commit -mnote"),
    (PASSE, "git log --grep commit -n 5"),
    (PASSE, f"git commit -m 'voir {NV}'"),
    (PASSE, "git pushd"),
    (PASSE, "git push --no-verbose"),
    (PASSE, "git push --no-version-check"),
    (PASSE, "git config --global core.editor vim"),
    (PASSE, "ls hooks"),
    (PASSE, "bash install.sh"),
    (PASSE, ""),
)


def lancer(entree: bytes, delai: float = DELAI) -> int | str:
    """Lance le hook avec `entree` sur stdin ; rend son code de sortie, ou "timeout" au-delà de `delai` secondes."""
    try:
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=entree,
            capture_output=True,
            check=False,
            timeout=delai,
        ).returncode
    except subprocess.TimeoutExpired:
        return "timeout"


def evenement(commande: str) -> bytes:
    """Rend le JSON PreToolUse, encodé en UTF-8, d'un appel Bash portant `commande`."""
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": commande}}
    ).encode("utf-8")


def main() -> int:
    """Joue la table puis les entrées dégradées ; rend 0 si tout passe, 1 sinon."""
    echecs = 0
    cas = [(attendu, commande, evenement(commande)) for attendu, commande in CAS]
    cas += [
        (PASSE, "<json illisible>", b"{pas du json"),
        (PASSE, "<entree vide>", b""),
        (PASSE, "<sans tool_input>", b'{"tool_name": "Bash"}'),
        (PASSE, "<command non textuelle>", b'{"tool_input": {"command": 42}}'),
        (PASSE, "<tableau>", b"[]"),
        (REFUS, "<utf-8 accentué>", evenement(f"echo « é » && {APM}=1 git push")),
        (REFUS, "<octet non UTF-8>", b'{"tool_input": {"command": "\xff ' + APM.encode() + b'=1"}}'),
    ]
    for attendu, libelle, entree in cas:
        obtenu = lancer(entree)
        if obtenu != attendu:
            echecs += 1
            print(f"ECHEC  attendu {attendu}, obtenu {obtenu} : {libelle!r}")
    print(f"{len(cas) - echecs}/{len(cas)} cas passent")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
