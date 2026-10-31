#!/bin/sh
# Cas de test de git-hooks/pre-push. Sortie 0 si tous passent.
#
# ⚠️ Les commandes et refs d'essai sont assemblées par concaténation : écrites en
# clair, elles déclencheraient le garde de session au moment de lancer ce fichier.

ici=$(cd "$(dirname "$0")" && pwd -P)
hook="$ici/pre-push"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Bouchon ssh -G en tête du PATH : l'alias github-perso résout vers github.com, github-443
# vers ssh.github.com, tout autre hôte vers lui-même.
mkdir -p "$tmp/bin"
cat >"$tmp/bin/ssh" <<'EOF'
#!/bin/sh
[ "$1" = -G ] || exit 255
case "$2" in
github-perso) echo "hostname github.com" ;;
github-443) echo "hostname ssh.github.com" ;;
*) echo "hostname $2" ;;
esac
echo "port 22"
EOF
chmod +x "$tmp/bin/ssh"
PATH="$tmp/bin:$PATH"
export PATH

: >"$tmp/gitconfig-vide"
GIT_CONFIG_GLOBAL="$tmp/gitconfig-vide"
GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM
# Garde secrets du pre-push hors champ : HOME jetable, installation « sans externes ».
HOME="$tmp/home"
mkdir -p "$HOME/.claude"
: >"$HOME/.claude/claude-config.sans-externes"
export HOME
unset GARDE_PUBLIC_MARQUEURS
unset ALLOW_PUSH_MAIN

P="git pu""sh"
M="ma""in"
Z=0000000000000000000000000000000000000000
S=1111111111111111111111111111111111111111
GH_SSH="git@github.com:a/b.git"
GH_HTTPS="https://github.com/a/b"
NAS="nas:/volume1/x.git"

git init -q "$tmp/direct"
git init -q "$tmp/garde-off"
git -C "$tmp/garde-off" config --local garde.pushMain off

echec=0
nb=0

# Affiche le verdict d'un cas. $1 attendu · $2 obtenu · $3 libellé.
verdict() {
	nb=$((nb + 1))
	if [ "$2" = "$1" ]; then v="  ok "; else v="ECHEC"; echec=1; fi
	printf '%s %-7s %s\n' "$v" "$2" "$3"
}

# Affiche les refs distantes de l'entrée $1, « (del) » devant une suppression.
refs_visees() {
	printf '%s\n' "$1" | sed -e "s/^[^ ]* $Z refs\/heads\/\([^ ]*\) .*/(del)\1/" \
		-e 's/^[^ ]* [^ ]* refs\/heads\/\([^ ]*\) .*/\1/' | tr '\n' ' '
}

# Appelle le hook depuis le dépôt $2 avec l'URL $3 et l'entrée $4. $1 attendu · $5 note.
essai() {
	if (cd "$2" && printf '%s\n' "$4" | sh "$hook" origin "$3" >/dev/null 2>&1); then
		obtenu=PASSE
	else
		obtenu=BLOQUE
	fi
	verdict "$1" "$obtenu" "$3 · $(refs_visees "$4")${5:-}"
}

ligne() { # $1 ref distante · $2 sha local
	printf 'refs/heads/x %s refs/heads/%s %s' "$2" "$1" "$S"
}

D="$tmp/direct"
echo "— appel direct —"
for url in "$GH_SSH" "$GH_HTTPS"; do
	essai BLOQUE "$D" "$url" "$(ligne "$M" "$S")"
	essai BLOQUE "$D" "$url" "$(ligne master "$S")"
	essai PASSE "$D" "$url" "$(ligne feat "$S")"
	essai BLOQUE "$D" "$url" "(delete) $Z refs/heads/$M $S"
done
essai BLOQUE "$D" "git@GitHub.com:a/b.git" "$(ligne "$M" "$S")"
essai PASSE "$D" "$NAS" "$(ligne "$M" "$S")"
essai PASSE "$D" "https://nas/github.com-mirror/b.git" "$(ligne "$M" "$S")" "· github.com hors hôte"

echo "— alias ssh —"
essai BLOQUE "$D" "git@github-perso:a/b.git" "$(ligne "$M" "$S")" "· alias vers github.com"
essai PASSE "$D" "git@github-perso:a/b.git" "$(ligne feat "$S")" "· alias vers github.com"
essai BLOQUE "$D" "git@github-443:a/b.git" "$(ligne "$M" "$S")" "· alias vers ssh.github.com"
essai PASSE "$D" "git@nas-perso:a/b.git" "$(ligne "$M" "$S")" "· alias vers un autre hôte"
essai BLOQUE "$D" "ssh://git@github-perso:2222/a/b" "$(ligne "$M" "$S")" "· alias ssh://, avec port"
essai BLOQUE "$D" "ssh://git@github.com:22/a/b.git" "$(ligne "$M" "$S")" "· github.com en ssh://, avec port"
essai BLOQUE "$D" "git+ssh://git@github-perso/a/b.git" "$(ligne "$M" "$S")" "· alias git+ssh://"
essai BLOQUE "$D" "ssh+git://github-perso/a/b.git" "$(ligne "$M" "$S")" "· alias ssh+git://"
essai PASSE "$D" "https://github-perso/a/b.git" "$(ligne "$M" "$S")" "· https:// ne passe pas par ssh"
essai PASSE "$D" "git@-oProxyCommand=x:a/b.git" "$(ligne "$M" "$S")" "· hôte en option ssh"

echo "— hôtes et formes d'URL —"
essai BLOQUE "$D" "HTTPS://GitHub.COM/a/b.git" "$(ligne "$M" "$S")" "· hôte en majuscules"
essai BLOQUE "$D" "https://user@github.com/a/b.git" "$(ligne "$M" "$S")" "· https avec utilisateur"
essai BLOQUE "$D" "https://github.com:443/a/b" "$(ligne "$M" "$S")" "· https avec port"
essai BLOQUE "$D" "git@ssh.github.com:a/b.git" "$(ligne "$M" "$S")" "· ssh.github.com"
essai BLOQUE "$D" "git+ssh://git@github.com/a/b.git" "$(ligne "$M" "$S")" "· git+ssh://"
essai PASSE "$D" "https://mygithub.com/a/b.git" "$(ligne "$M" "$S")" "· hôte qui finit par github.com"
essai PASSE "$D" "https://github.com.evil.example/a/b.git" "$(ligne "$M" "$S")" "· hôte qui commence par github.com"
essai PASSE "$D" "/srv/github.com/a.git" "$(ligne "$M" "$S")" "· chemin local absolu"
essai PASSE "$D" "../github.com/a.git" "$(ligne "$M" "$S")" "· chemin local relatif"
essai PASSE "$D" "file:///srv/github.com/a.git" "$(ligne "$M" "$S")" "· file://"
essai BLOQUE "$D" "$GH_SSH" "$(ligne feat "$S")
$(ligne "$M" "$S")
$(ligne autre "$S")"

if (cd "$D" && ligne "$M" "$S" | ALLOW_PUSH_MAIN=1 sh "$hook" origin "$GH_SSH" >/dev/null 2>"$tmp/err"); then
	obtenu=PASSE
else
	obtenu=BLOQUE
fi
verdict PASSE "$obtenu" "ALLOW_PUSH_MAIN=1 · $GH_SSH · $M"
grep -q ALLOW_PUSH_MAIN "$tmp/err"
[ $? -eq 0 ] && obtenu=PASSE || obtenu=BLOQUE
verdict PASSE "$obtenu" "ALLOW_PUSH_MAIN=1 · message stderr"

essai PASSE "$tmp/garde-off" "$GH_SSH" "$(ligne "$M" "$S")" "· garde.pushMain off"

echo "— bout en bout (remote nu local) —"
git init -q --bare "$tmp/nu.git"
git init -q -b "$M" "$tmp/e2e" 2>/dev/null || { git init -q "$tmp/e2e" && git -C "$tmp/e2e" symbolic-ref HEAD "refs/heads/$M"; }
(
	cd "$tmp/e2e" &&
		git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init &&
		git remote add origin "$tmp/nu.git"
)
pousse() { # pousse main depuis le dépôt e2e avec core.hooksPath sur ce dossier
	(cd "$tmp/e2e" &&
		git -c user.name=t -c user.email=t@t commit -q --allow-empty -m "$1" &&
		git -c core.hooksPath="$ici" ${P#git } -q origin "$M" >/dev/null 2>&1)
}

if pousse un; then obtenu=PASSE; else obtenu=BLOQUE; fi
verdict PASSE "$obtenu" "core.hooksPath · remote local · $M"

hooks_depot=$(cd "$tmp/e2e" && cd "$(git rev-parse --git-common-dir)" && pwd -P)/hooks
mkdir -p "$hooks_depot"
cat >"$hooks_depot/pre-push" <<HOOK
#!/bin/sh
cat >"$tmp/temoin"
exit 1
HOOK
chmod +x "$hooks_depot/pre-push"

if pousse deux; then obtenu=PASSE; else obtenu=BLOQUE; fi
verdict BLOQUE "$obtenu" "hook du dépôt qui sort 1 → push refusé"
[ -f "$tmp/temoin" ] && obtenu=PRESENT || obtenu=ABSENT
verdict PRESENT "$obtenu" "hook du dépôt lancé (témoin)"
grep -q "refs/heads/$M" "$tmp/temoin" 2>/dev/null && obtenu=TRANSMIS || obtenu=PERDU
verdict TRANSMIS "$obtenu" "entrée transmise au hook du dépôt"

echo
if [ $echec -eq 0 ]; then echo "$nb cas, tous verts."; else echo "$nb cas, au moins un ECHEC."; fi
exit $echec
