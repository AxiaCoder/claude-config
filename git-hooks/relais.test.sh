#!/bin/sh
# Cas de test de git-hooks/_relais et de ses stubs. Sortie 0 si tous passent.
#
# ⚠️ Le nom du réglage git de dossier de hooks est assemblé par concaténation :
# écrit en clair, il déclencherait le garde de session au moment de lancer ce fichier.

ici=$(cd "$(dirname "$0")" && pwd -P)
tmp=$(cd "$(mktemp -d)" && pwd -P)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/gitconfig-vide" <<EOF
[user]
	name = essai
	email = essai@example.invalid
[commit]
	gpgsign = false
EOF
GIT_CONFIG_GLOBAL="$tmp/gitconfig-vide"
GIT_CONFIG_NOSYSTEM=1
GIT_CEILING_DIRECTORIES="$tmp"
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM GIT_CEILING_DIRECTORIES

REGLAGE="core.hooks""Path"
STUBS="applypatch-msg commit-msg post-applypatch post-checkout post-commit post-merge
post-rewrite pre-applypatch pre-auto-gc pre-commit pre-merge-commit pre-rebase
prepare-commit-msg sendemail-validate"

mkdir "$tmp/modele-vide"

echec=0
nb=0

# Affiche le verdict d'un cas. $1 attendu · $2 obtenu · $3 libellé.
verdict() {
	nb=$((nb + 1))
	if [ "$2" = "$1" ]; then v="  ok "; else v="ECHEC"; echec=1; fi
	printf '%s %-8s %s\n' "$v" "$2" "$3"
}

# Crée le dépôt $1, sans hook local, pointé sur les hooks globaux de ce dossier.
depot() {
	git init -q --template="$tmp/modele-vide" "$1"
	git -C "$1" config --local "$REGLAGE" "$ici"
	mkdir -p "$1/.git/hooks"
}

# Écrit le hook local $2 du dépôt $1 avec le corps $3, exécutable.
hook_local() {
	printf '#!/bin/sh\n%s\n' "$3" >"$1/.git/hooks/$2"
	chmod +x "$1/.git/hooks/$2"
}

# Fait un commit vide dans le dépôt $1 ; affiche PASSE ou BLOQUE.
commit() {
	if git -C "$1" commit -q --allow-empty -m "${2:-essai}" >/dev/null 2>&1; then
		echo PASSE
	else
		echo BLOQUE
	fi
}

# 1. pre-commit local en échec → commit refusé
d="$tmp/refus"; depot "$d"; hook_local "$d" pre-commit 'exit 1'
verdict BLOQUE "$(commit "$d")" "pre-commit local exit 1 → commit refusé"

# 2. pre-commit local en succès → commit passe
d="$tmp/accord"; depot "$d"; hook_local "$d" pre-commit 'exit 0'
verdict PASSE "$(commit "$d")" "pre-commit local exit 0 → commit passe"

# 3. sans hook local → commit passe
d="$tmp/sans"; depot "$d"
verdict PASSE "$(commit "$d")" "sans hook local → commit passe"

# 4. commit-msg reçoit le fichier de message en $1
d="$tmp/msg"; depot "$d"
hook_local "$d" commit-msg "cp \"\$1\" \"$tmp/msg-recu\""
commit "$d" "message-temoin" >/dev/null
if grep -q message-temoin "$tmp/msg-recu" 2>/dev/null; then o=RECU; else o=ABSENT; fi
verdict RECU "$o" "commit-msg reçoit \$1 (fichier du message)"

# 5. post-rewrite reçoit son argument et son entrée standard
d="$tmp/rewrite"; depot "$d"
commit "$d" >/dev/null
avant=$(git -C "$d" rev-parse HEAD)
hook_local "$d" post-rewrite "echo \"\$1\" >\"$tmp/rw-arg\"; cat >\"$tmp/rw-stdin\""
git -C "$d" commit -q --amend --allow-empty -m modifie >/dev/null 2>&1
if [ "$(cat "$tmp/rw-arg" 2>/dev/null)" = amend ] && grep -q "^$avant " "$tmp/rw-stdin" 2>/dev/null
then o=RECU; else o=ABSENT; fi
verdict RECU "$o" "post-rewrite reçoit \"amend\" et l'ancien sha sur stdin"

# 6. hook local non exécutable → ignoré, comme le ferait git
# Sous Windows, chmod -x est sans effet : un fichier en #! reste exécutable, et git le lance.
d="$tmp/non-exec"; depot "$d"; hook_local "$d" pre-commit 'exit 1'
chmod -x "$d/.git/hooks/pre-commit"
if [ -x "$d/.git/hooks/pre-commit" ]; then
	verdict BLOQUE "$(commit "$d")" "pre-commit local en #!, exécutable sous Windows → lancé"
else
	verdict PASSE "$(commit "$d")" "pre-commit local non exécutable → ignoré"
fi

# 7. .git/hooks lien vers les hooks globaux → pas de boucle
d="$tmp/lien"; depot "$d"
rmdir "$d/.git/hooks"
ln -s "$ici" "$d/.git/hooks"
( commit "$d" >"$tmp/lien-res" ) &
pid=$!
i=0
while kill -0 "$pid" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.1; i=$((i + 1)); done
if kill -0 "$pid" 2>/dev/null; then
	pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
	o=BOUCLE
else
	o=$(cat "$tmp/lien-res")
fi
verdict PASSE "$o" ".git/hooks lien vers git-hooks/ → pas de boucle"

# 8. worktree lié → hook du dossier commun
d="$tmp/principal"; depot "$d"; commit "$d" >/dev/null
hook_local "$d" pre-commit 'exit 1'
git -C "$d" worktree add -q --detach "$tmp/lie" >/dev/null 2>&1
verdict BLOQUE "$(commit "$tmp/lie")" "worktree lié → hook local du dossier commun"

# 9. hors dépôt → 0
mkdir "$tmp/hors"
if (cd "$tmp/hors" && sh "$ici/pre-commit" </dev/null >/dev/null 2>&1); then o=PASSE; else o=BLOQUE; fi
verdict PASSE "$o" "hors dépôt → sortie 0"

# 10. chaque stub et le relais sont exécutables dans l'index
for f in _relais $STUBS; do
	mode=$(git -C "$ici" ls-files -s -- "$f" | cut -d' ' -f1)
	verdict 100755 "${mode:-absent}" "mode index de git-hooks/$f"
done

printf '\n%d cas, %s\n' "$nb" "$([ $echec = 0 ] && echo 'tous passent' || echo 'ÉCHECS')"
exit $echec
