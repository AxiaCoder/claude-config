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
# Usage : bash install.sh [--perso <dossier>] [--dry-run]

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="$HOME/.claude"
PERSO_MEMO="$CLAUDE_HOME/claude-config.perso"
PERSO=""
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_HOME/config-backup-$STAMP"
LINKED_DIRS=(agents commands skills hooks git-hooks)

while [ $# -gt 0 ]; do
  case "$1" in
    --perso)   PERSO="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
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
import json, pathlib, re, sys
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


# {{REPO}} : les dossiers de `~/.claude` sont des liens vers ce dépôt ; sans
# cette autorisation, une session ouverte ailleurs ne peut pas les suivre.
def render(text):
    """Replace the {{CLAUDE_HOME}} and {{REPO}} markers in a layer's raw JSON text, JSON-escaped."""
    for marker, value in (("{{CLAUDE_HOME}}", home), ("{{REPO}}", repo)):
        text = text.replace(marker, json.dumps(str(value))[1:-1])
    return text


layers = [repo / "settings.base.json", repo / "settings.macos.json", *perso]
# hooks et permissions se rebâtissent à partir des couches seules : None tant
# qu'aucune couche ne les définit, et l'existant est alors conservé.
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
if hooks is not None:
    merged["hooks"] = hooks
if permissions is not None:
    merged["permissions"] = permissions
text = json.dumps(merged, indent=2, ensure_ascii=False)
reste = re.search(r"\{\{[A-Z_]+\}\}", text)
if reste:
    sys.exit(f"settings.json : le marqueur {reste.group(0)} survit au rendu, ~/.claude/settings.json n'est pas écrit.")
target.write_text(text + "\n", encoding="utf-8")
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

echo
echo "Terminé. Vérifier les liens :"
echo "  ls -l ~/.claude | grep -E 'agents|commands|skills|hooks'"
echo "  git config --global --get core.hooksPath"
[ -d "$BACKUP_DIR" ] && echo "Sauvegarde : $BACKUP_DIR"
exit 0
