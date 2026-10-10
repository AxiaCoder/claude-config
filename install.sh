#!/usr/bin/env bash
# Monte claude-config dans ~/.claude sur macOS ou Linux.
#
# Les cinq dossiers de configuration deviennent des liens symboliques vers ce
# repo, et git-hooks devient le dossier de hooks git global (core.hooksPath),
# sauf si un autre dossier y est déjà déclaré. CLAUDE.md, CAVEMAN.md et settings.json sont rendus : ils portent des
# chemins propres à la machine et ne peuvent pas être liés. Le script est
# idempotent.
#
# Le dossier perso, optionnel, porte ce qui est propre à l'utilisateur : ses
# settings.json et settings.macos.json s'ajoutent par-dessus ceux du dépôt, et
# son CLAUDE.md prend la place de {{PERSO_CLAUDE_MD}}, avec {{PERSO}} remplacé
# par le chemin du dossier. Son CLAUDE.complet.md, s'il en a un, remplace tout le
# CLAUDE.md du dépôt et fait ignorer son CLAUDE.md. Il
# est mémorisé dans ~/.claude/claude-config.perso : les passes suivantes le
# reprennent sans --perso.
#
# betterleaks, à la version et au sha256 de git-hooks/betterleaks.version, est
# téléchargé dans ~/.claude/bin pour le garde secrets du pre-commit. Inventaire des
# outils externes : DEPENDANCES.md. --sans-externes n'installe rien de ce qui se
# télécharge et désactive le garde secrets ; le choix est mémorisé dans
# ~/.claude/claude-config.sans-externes, --avec-externes le défait.
#
# Usage : bash install.sh [--perso <dossier>] [--sans-externes | --avec-externes] [--dry-run]

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="$HOME/.claude"
PERSO_MEMO="$CLAUDE_HOME/claude-config.perso"
EXTERNES_MEMO="$CLAUDE_HOME/claude-config.sans-externes"
EXTERNES=""
PERSO=""
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_HOME/config-backup-$STAMP"
LINKED_DIRS=(agents commands skills hooks git-hooks)

while [ $# -gt 0 ]; do
  case "$1" in
    --perso)   PERSO="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --sans-externes) EXTERNES=sans; shift ;;
    --avec-externes) EXTERNES=avec; shift ;;
    *) echo "Option inconnue : $1" >&2; exit 1 ;;
  esac
done

[ -d "$CLAUDE_HOME" ] || { echo "'$CLAUDE_HOME' n'existe pas." >&2; exit 1; }
PERSO_SOURCE="--perso"
if [ -z "$PERSO" ] && [ -f "$PERSO_MEMO" ]; then
  PERSO="$(cat "$PERSO_MEMO")"
  PERSO_SOURCE="le mémo $PERSO_MEMO — le supprimer pour s'en passer"
fi
if [ -n "$PERSO" ]; then
  [ -d "$PERSO" ] || { echo "Le dossier perso est introuvable à '$PERSO' (lu dans $PERSO_SOURCE). Relance avec --perso <dossier>." >&2; exit 1; }
  PERSO="$(cd "$PERSO" && pwd)"
fi

echo "claude-config -> $CLAUDE_HOME"
[ "$DRY_RUN" -eq 1 ] && echo "(simulation, rien ne sera écrit)"

run() { [ "$DRY_RUN" -eq 1 ] || "$@"; }

PREMIERE=1
[ -L "$CLAUDE_HOME/agents" ] && [ "$(readlink "$CLAUDE_HOME/agents")" = "$REPO/agents" ] && PREMIERE=0

# À la première passe, les fichiers que l'installation va réécrire sont ceux de
# l'utilisateur : ils partent dans la sauvegarde avant d'être remplacés.
if [ "$PREMIERE" -eq 1 ]; then
  for fichier in CLAUDE.md CAVEMAN.md settings.json; do
    if [ -e "$CLAUDE_HOME/$fichier" ]; then
      echo "  $fichier : existant, sauvegardé dans $(basename "$BACKUP_DIR")"
      run mkdir -p "$BACKUP_DIR"
      run cp "$CLAUDE_HOME/$fichier" "$BACKUP_DIR/$fichier"
    fi
  done
fi

for dir in "${LINKED_DIRS[@]}"; do
  target="$CLAUDE_HOME/$dir"
  source="$REPO/$dir"

  if [ -L "$target" ]; then
    if [ "$(readlink "$target")" = "$source" ]; then
      echo "  $dir : lien déjà en place"
      continue
    fi
    echo "  $dir : lien vers une autre cible, remplacement"
    run rm "$target"
  elif [ -e "$target" ]; then
    echo "  $dir : vrai dossier, sauvegarde dans $(basename "$BACKUP_DIR")"
    run mkdir -p "$BACKUP_DIR"
    run mv "$target" "$BACKUP_DIR/$dir"
  else
    echo "  $dir : absent, création du lien"
  fi

  run ln -s "$source" "$target"
done

if [ -n "$PERSO" ] && [ -f "$PERSO/CLAUDE.complet.md" ]; then
  echo "  CLAUDE.md : remplacé par le CLAUDE.complet.md du dossier perso"
  [ -f "$PERSO/CLAUDE.md" ] && echo "  CLAUDE.md : le CLAUDE.md du dossier perso est ignoré, CLAUDE.complet.md le remplace"
else
  echo "  CLAUDE.md : rendu, avec le CLAUDE.md du dossier perso s'il en a un"
fi
run python3 - "$REPO/CLAUDE.md" "$CLAUDE_HOME/CLAUDE.md" "$PERSO" <<'PY'
import os, pathlib, re, sys
src, dest, perso = sys.argv[1:4]
perso_md = pathlib.Path(perso) / "CLAUDE.md" if perso else None
perso_complet = pathlib.Path(perso) / "CLAUDE.complet.md" if perso else None

def resolve_perso(content):
    """Replace each {{PERSO}} marker and its path tail with the normalized absolute path under perso."""
    def resolve(m):
        tail = m.group("tail")
        path = os.path.normpath(perso + tail)
        return path + "/" if tail.endswith("/") else path
    return re.sub(r"\{\{PERSO\}\}(?P<tail>[\w./\[\]-]*)", resolve, content)

if perso_complet and perso_complet.exists():
    text = resolve_perso(perso_complet.read_text(encoding="utf-8"))
else:
    insert = ""
    if perso_md and perso_md.exists():
        insert = resolve_perso(perso_md.read_text(encoding="utf-8")) + "\n"
    text = re.sub(r"\{\{PERSO_CLAUDE_MD\}\}\r?\n(?:\r?\n)?", lambda m: insert,
                  pathlib.Path(src).read_text(encoding="utf-8"))
if "{{PERSO" in text:
    sys.exit("CLAUDE.md : un marqueur {{PERSO…}} survit au rendu, ~/.claude/CLAUDE.md n'est pas écrit.")
pathlib.Path(dest).write_text(text, encoding="utf-8")
PY

echo "  CAVEMAN.md : copie"
run cp "$REPO/CAVEMAN.md" "$CLAUDE_HOME/CAVEMAN.md"

# On repart des réglages en place pour ne pas perdre les clés écrites par le
# harness et que ce repo ne gère pas.
if [ -n "$PERSO" ]; then
  echo "  dossier perso : $PERSO"
  [ "$DRY_RUN" -eq 1 ] || printf '%s\n' "$PERSO" > "$PERSO_MEMO"
fi

echo "  settings.json : base + overlay macOS + dossier perso, fusionnés sur l'existant"
run python3 - "$CLAUDE_HOME" "$REPO" "$PERSO" <<'PY'
import json, os, pathlib, re, sys
home, repo = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
perso = [pathlib.Path(sys.argv[3]) / name for name in ("settings.json", "settings.macos.json")] if sys.argv[3] else []
target = home / "settings.json"
merged = {}
if target.exists():
    (home / "settings.json.prev").write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    merged = json.loads(target.read_text(encoding="utf-8"))
def add_unique(target_list, items):
    """Append to target_list each item it does not already hold, in order."""
    for item in items:
        if item not in target_list:
            target_list.append(item)


def mod_dirs():
    """Return the absolute paths of the <REPO>/mods/* folders holding a .claude-plugin/plugin.json, sorted."""
    mods = repo / "mods"
    if not mods.is_dir():
        return []
    return sorted(str(path) for path in mods.iterdir()
                  if (path / ".claude-plugin" / "plugin.json").is_file())


MODS = os.pathsep.join(mod_dirs())


# {{REPO}} : les dossiers de `~/.claude` sont des liens vers ce dépôt ; sans
# cette autorisation, une session ouverte ailleurs ne peut pas les suivre.
def render(text):
    """Replace the {{CLAUDE_HOME}}, {{REPO}} and {{MODS}} markers in a layer's raw JSON text, JSON-escaped.

    {{MODS}} becomes the mod folders joined by the platform's path-list separator, "" when there is none.
    """
    for marker, value in (("{{CLAUDE_HOME}}", home), ("{{REPO}}", repo), ("{{MODS}}", MODS)):
        text = text.replace(marker, json.dumps(str(value))[1:-1])
    return text


HOOKS_DIRS = {path for base in (home / "hooks", repo / "hooks")
              for path in (os.path.normpath(str(base)), os.path.realpath(str(base)))}
HOOKS_MEMO = home / "claude-config.hooks.json"


def hook_key(event, block, hook):
    """Return the canonical identity of a hook: its event, its block's matcher ("" when absent), its command."""
    matcher = block.get("matcher", "") if isinstance(block, dict) else ""
    command = hook.get("command", "") if isinstance(hook, dict) else ""
    return (str(event), str(matcher or ""), str(command))


def read_memo():
    """Return the hook keys rendered by the previous pass, or an empty set when the memo is absent or unreadable.

    An unreadable or malformed memo is reported on stderr and ignored.
    """
    if not HOOKS_MEMO.exists():
        return set()
    try:
        entries = json.loads(HOOKS_MEMO.read_text(encoding="utf-8"))
        return {(str(e["event"]), str(e["matcher"]), str(e["command"])) for e in entries}
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"  ATTENTION : {HOOKS_MEMO} illisible ({error}) : ignoré, seuls les hooks sous hooks/ sont reconnus comme les nôtres.", file=sys.stderr)
        return set()


def is_under_hooks_dir(hook):
    """Tell whether a hook's command, markers expanded, names a file under <CLAUDE_HOME>/hooks or <REPO>/hooks.

    Each absolute word or quoted string of the command is normalized, `\\` read as `/`.
    """
    command = str(hook.get("command", "")) if isinstance(hook, dict) else ""
    for marker, value in (("{{CLAUDE_HOME}}", home), ("{{REPO}}", repo)):
        command = command.replace(marker, str(value))
    for quoted, single, bare in re.findall(r'"([^"]*)"|\'([^\']*)\'|(\S+)', command):
        word = os.path.expanduser((quoted or single or bare).replace("\\", "/"))
        if not os.path.isabs(word):
            continue
        for path in (os.path.normpath(word), os.path.realpath(word)):
            if any(path.startswith(directory + os.sep) for directory in HOOKS_DIRS):
                return True
    return False


def foreign_blocks(event, blocks, memo):
    """Return the blocks of an event stripped of our hooks, blocks left empty dropped.

    Ours: a hook the previous pass rendered from the layers (memo), or one under a hooks dir.
    """
    kept = []
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        foreign = [hook for hook in block.get("hooks", [])
                   if hook_key(event, block, hook) not in memo and not is_under_hooks_dir(hook)]
        if foreign:
            kept.append({**block, "hooks": foreign})
    return kept


layers = [repo / "settings.base.json", repo / "settings.macos.json", *perso]
# hooks et permissions se rebâtissent à partir des couches : None tant
# qu'aucune couche ne les définit, et l'existant est alors conservé. Des hooks
# existants, seuls ceux d'autres outils sont repris, après ceux des couches.
hooks, permissions = None, None
for layer in layers:
    if not layer.exists():
        continue
    data = json.loads(render(layer.read_text(encoding="utf-8")))
    # env se fusionne clé par clé : un overlay ajoute une variable au socle,
    # il ne remplace pas le bloc entier.
    env = {**merged.get("env", {}), **data.pop("env", {})}
    layer_hooks = data.pop("hooks", None)
    if layer_hooks is not None:
        hooks = hooks if hooks is not None else {}
        for event, blocks in layer_hooks.items():
            add_unique(hooks.setdefault(event, []), blocks)
    layer_permissions = data.pop("permissions", None)
    if layer_permissions is not None:
        permissions = permissions if permissions is not None else {}
        for key, value in layer_permissions.items():
            if isinstance(value, list):
                if not isinstance(permissions.get(key), list):
                    permissions[key] = []
                add_unique(permissions[key], value)
            else:
                permissions[key] = value
    merged.update(data)
    if env:
        merged["env"] = env
# Un {{MODS}} rendu vide, aucun mod : la variable est retirée plutôt que posée vide.
if isinstance(merged.get("env"), dict) and merged["env"].get("CLAUDE_CODE_PLUGIN_DIRS") == "":
    del merged["env"]["CLAUDE_CODE_PLUGIN_DIRS"]
rendered = []
if hooks is not None:
    for event, blocks in hooks.items():
        for block in blocks if isinstance(blocks, list) else []:
            for hook in block.get("hooks", []) if isinstance(block, dict) else []:
                key = dict(zip(("event", "matcher", "command"), hook_key(event, block, hook)))
                if key not in rendered:
                    rendered.append(key)
    memo = read_memo()
    for event, blocks in (merged.get("hooks") or {}).items():
        foreign = foreign_blocks(event, blocks, memo)
        if foreign:
            add_unique(hooks.setdefault(event, []), foreign)
    merged["hooks"] = hooks
if permissions is not None:
    merged["permissions"] = permissions
text = json.dumps(merged, indent=2, ensure_ascii=False)
reste = re.search(r"\{\{[A-Z_]+\}\}", text)
if reste:
    sys.exit(f"settings.json : le marqueur {reste.group(0)} survit au rendu, ~/.claude/settings.json n'est pas écrit.")
target.write_text(text + "\n", encoding="utf-8")
if hooks is not None:
    HOOKS_MEMO.write_text(json.dumps(rendered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

hooks_path="$CLAUDE_HOME/git-hooks"
actuel="$(git config --global --get core.hooksPath || true)"
if [ -z "$actuel" ]; then
  echo "  git : core.hooksPath global -> $hooks_path"
  run git config --global core.hooksPath "$hooks_path"
elif [ "${actuel%/}" = "$hooks_path" ]; then
  echo "  git : core.hooksPath global déjà en place"
else
  echo "  ATTENTION : core.hooksPath global vaut déjà '$actuel' : laissé tel quel, le garde pre-push n'est pas actif." >&2
fi

# Pose dans ~/.claude/bin le betterleaks épinglé par git-hooks/betterleaks.version, s'il
# n'y est pas déjà à cette version. Rend 1, avec un message sur stderr, quand il n'a pas
# pu être posé : fichier de version absent, plateforme sans asset, téléchargement,
# sha256 ou extraction en échec. En simulation, annonce l'installation sans rien écrire.
installer_betterleaks() {
  local fichier="$REPO/git-hooks/betterleaks.version" bin="$CLAUDE_HOME/bin/betterleaks"
  local version os arch sha asset url dl obtenu
  if [ ! -f "$fichier" ]; then
    echo "  ATTENTION : betterleaks : $fichier absent, non installé." >&2
    return 1
  fi
  version="$(sed -n 's/^version=//p' "$fichier")"
  case "$(uname -s)" in Darwin) os=darwin ;; Linux) os=linux ;; *) os="" ;; esac
  case "$(uname -m)" in arm64 | aarch64) arch=arm64 ;; x86_64 | amd64) arch=x64 ;; *) arch="" ;; esac
  sha="$(sed -n "s/^${os}_${arch}=//p" "$fichier")"
  if [ -z "$version" ] || [ -z "$os" ] || [ -z "$arch" ] || [ -z "$sha" ]; then
    echo "  ATTENTION : betterleaks : aucun asset épinglé pour $(uname -s)/$(uname -m) dans $fichier, non installé." >&2
    return 1
  fi
  if [ -x "$bin" ] && [ "$("$bin" version 2>/dev/null)" = "$version" ]; then
    echo "  betterleaks : $version déjà en place"
    return 0
  fi
  asset="betterleaks_${version}_${os}_${arch}.tar.gz"
  url="https://github.com/betterleaks/betterleaks/releases/download/v${version}/${asset}"
  echo "  betterleaks : installation de $version ($asset) dans $CLAUDE_HOME/bin"
  [ "$DRY_RUN" -eq 1 ] && return 0
  dl="$(mktemp -d)" || return 1
  if ! curl -fsSL --max-time 120 -o "$dl/$asset" "$url"; then
    echo "  ATTENTION : betterleaks : téléchargement impossible ($url), non installé." >&2
    rm -rf "${dl:?}"
    return 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    obtenu="$(sha256sum "$dl/$asset" | cut -d' ' -f1)"
  else
    obtenu="$(shasum -a 256 "$dl/$asset" | cut -d' ' -f1)"
  fi
  if [ "$obtenu" != "$sha" ]; then
    echo "  ATTENTION : betterleaks : sha256 inattendu pour $asset (attendu $sha, obtenu $obtenu), non installé." >&2
    rm -rf "${dl:?}"
    return 1
  fi
  if ! { tar -xzf "$dl/$asset" -C "$dl" betterleaks && mkdir -p "$CLAUDE_HOME/bin" && mv -f "$dl/betterleaks" "$bin" && chmod +x "$bin"; }; then
    echo "  ATTENTION : betterleaks : extraction de $asset impossible, non installé." >&2
    rm -rf "${dl:?}"
    return 1
  fi
  rm -rf "${dl:?}"
}

case "$EXTERNES" in
  sans)
    echo "  externes : désactivés (--sans-externes), choix mémorisé dans $EXTERNES_MEMO"
    [ "$DRY_RUN" -eq 1 ] || : > "$EXTERNES_MEMO"
    SANS_EXTERNES=1 ;;
  avec)
    echo "  externes : réactivés (--avec-externes)"
    run rm -f "$EXTERNES_MEMO"
    SANS_EXTERNES=0 ;;
  *)
    SANS_EXTERNES=0
    if [ -f "$EXTERNES_MEMO" ]; then SANS_EXTERNES=1; fi ;;
esac

GARDE_SECRETS_INACTIF=0
if [ "$SANS_EXTERNES" -eq 1 ]; then
  echo "  betterleaks : non installé (sans externes ; --avec-externes pour revenir) : garde secrets désactivé"
  if [ -e "$CLAUDE_HOME/bin/betterleaks" ]; then
    echo "  betterleaks : $CLAUDE_HOME/bin/betterleaks reste en place, le retirer à la main (DEPENDANCES.md)"
  fi
else
  installer_betterleaks || GARDE_SECRETS_INACTIF=1
fi

echo
echo "Terminé. Vérifier les liens :"
echo "  ls -l ~/.claude | grep -E 'agents|commands|skills|hooks'"
echo "  git config --global --get core.hooksPath"
[ -d "$BACKUP_DIR" ] && echo "Sauvegarde : $BACKUP_DIR"
if [ "$GARDE_SECRETS_INACTIF" -eq 1 ]; then
  echo "ATTENTION : garde secrets inactif : betterleaks absent. les commits sont refusés tant qu'il manque : relancer install.sh, ou --sans-externes pour s'en passer." >&2
fi
exit 0
