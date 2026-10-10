#!/bin/sh
# Cas de test du garde données personnelles (git-hooks/_garde-public), appelé par
# git-hooks/pre-push. Sortie 0 si tous passent.
#
# gh est remplacé par un bouchon placé en tête du PATH : a/public est public, a/prive
# privé, tout autre dépôt fait échouer gh.

ici=$(cd "$(dirname "$0")" && pwd -P)
hook="$ici/pre-push"
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
XDG_CACHE_HOME="$tmp/cache"
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM GIT_CEILING_DIRECTORIES XDG_CACHE_HOME
unset ALLOW_PUSH_PERSONAL

mkdir "$tmp/bin"
cat >"$tmp/bin/gh" <<EOF
#!/bin/sh
echo "\$3" >>"$tmp/gh-appels"
case "\$3" in
a/public | a/cache) echo PUBLIC ;;
a/prive) echo PRIVATE ;;
*) exit 1 ;;
esac
EOF
chmod +x "$tmp/bin/gh"
PATH="$tmp/bin:$PATH"
export PATH

cat >"$tmp/marqueurs" <<'EOF'
# commentaire ignoré

Mot-Secret
serveur-[0-9]+
EOF
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs"
export GARDE_PUBLIC_MARQUEURS

Z=0000000000000000000000000000000000000000
M="ma""in"
PUBLIC="git@github.com:a/public.git"

git init -q --bare "$tmp/nu.git"
git init -q "$tmp/d"
cd "$tmp/d" || exit 1
git symbolic-ref HEAD "refs/heads/$M"
printf 'ligne propre\nancien mot-secret\n' >base.txt
git add base.txt
git commit -q -m init
git remote add origin "$tmp/nu.git"
git push -q origin "$M" 2>/dev/null
git fetch -q origin

echec=0
nb=0

# Affiche le verdict d'un cas. $1 attendu · $2 obtenu · $3 libellé.
verdict() {
	nb=$((nb + 1))
	if [ "$2" = "$1" ]; then v="  ok "; else v="ECHEC"; echec=1; fi
	printf '%s %-8s %s\n' "$v" "$2" "$3"
}

# Crée la branche $1 depuis main et y commite le fichier $2 au contenu $3, message $4.
branche() {
	git checkout -q -B "$1" "$M"
	printf '%s\n' "$3" >"$2"
	git add "$2"
	git commit -q -m "$4"
}

# Lance le pre-push pour la branche courante, nouvelle côté remote, vers l'URL $2.
# $1 attendu · $3 libellé. stderr dans $tmp/err.
essai() {
	sha=$(git rev-parse HEAD)
	ref=$(git symbolic-ref HEAD)
	if printf '%s %s %s %s\n' "$ref" "$sha" "$ref" "${4:-$Z}" | sh "$hook" origin "$2" >/dev/null 2>"$tmp/err"; then
		obtenu=PASSE
	else
		obtenu=BLOQUE
	fi
	verdict "$1" "$obtenu" "$3"
}

# Vérifie que stderr du dernier essai contient $1. $2 libellé.
stderr_contient() {
	if grep -q -e "$1" "$tmp/err"; then o=PRESENT; else o=ABSENT; fi
	verdict PRESENT "$o" "$2"
}

echo "— dépôt public —"
branche f1 ajout.txt "rien
contact serveur-42 ici" "ajout propre"
essai BLOQUE "$PUBLIC" "marqueur regex dans un fichier ajouté"
stderr_contient "ajout.txt:2" "  stderr : fichier:ligne"
stderr_contient "serveur-\[0-9\]+" "  stderr : marqueur"

branche f2 propre.txt "rien à signaler" "note sur MOT-SECRET"
essai BLOQUE "$PUBLIC" "marqueur dans un message de commit, casse ignorée"
stderr_contient "commit $(git rev-parse --short HEAD)" "  stderr : commit"

git checkout -q -B f3 "$M"
printf 'ligne propre\n' >base.txt
git commit -q -am "retrait"
essai PASSE "$PUBLIC" "ligne supprimée contenant le marqueur, déjà sur le remote"

branche f4 propre.txt "rien" "propre"
essai PASSE "$PUBLIC" "rien de marqué"

git push -q origin f4 2>/dev/null
avant=$(git rev-parse HEAD)
printf 'serveur-7\n' >>propre.txt
git commit -q -am "suite"
essai BLOQUE "$PUBLIC" "branche existante, marqueur dans le nouveau commit" "$avant"

git checkout -q f1
ALLOW_PUSH_PERSONAL=1
export ALLOW_PUSH_PERSONAL
essai PASSE "$PUBLIC" "ALLOW_PUSH_PERSONAL=1"
stderr_contient ALLOW_PUSH_PERSONAL "  stderr : contournement annoncé"
unset ALLOW_PUSH_PERSONAL

echo "— autres cas —"
essai PASSE "https://github.com/a/prive" "dépôt privé"
essai PASSE "nas:/volume1/x.git" "remote non GitHub"
essai PASSE "git@github.com:a/inconnu.git" "gh en erreur"
stderr_contient "inconnue" "  stderr : avertissement gh"

GARDE_PUBLIC_MARQUEURS="$tmp/absent"
essai PASSE "$PUBLIC" "fichier de marqueurs absent"
stderr_contient GARDE_PUBLIC_MARQUEURS "  stderr : avertissement marqueurs"
unset GARDE_PUBLIC_MARQUEURS
essai PASSE "$PUBLIC" "variable non définie"
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs"
export GARDE_PUBLIC_MARQUEURS

echo "— cache —"
: >"$tmp/gh-appels"
essai BLOQUE "https://github.com/a/cache.git" "1er push"
essai BLOQUE "git@github.com:a/cache" "2e push"
n=$(grep -c '^a/cache$' "$tmp/gh-appels")
verdict 1 "$n" "appels à gh pour a/cache"

touch -t 200001010000 "$XDG_CACHE_HOME/claude-config/garde-public/a_cache"
essai BLOQUE "https://github.com/a/cache/" "3e push, cache de plus de 24 h"
n=$(grep -c '^a/cache$' "$tmp/gh-appels")
verdict 2 "$n" "appels à gh pour a/cache après expiration"

echo "— plusieurs refs, tags, formes d'entrée —"

# Lance le pre-push vers l'URL $2 avec l'entrée $4 telle quelle. $1 attendu · $3 libellé.
essai_brut() {
	if printf '%s\n' "$4" | sh "$hook" origin "$2" >/dev/null 2>"$tmp/err"; then
		obtenu=PASSE
	else
		obtenu=BLOQUE
	fi
	verdict "$1" "$obtenu" "$3"
}

propre=$(git rev-parse f4~1)
marque=$(git rev-parse f1)
essai_brut BLOQUE "$PUBLIC" "deux refs, marqueur dans la seconde seulement" \
	"refs/heads/f4 $propre refs/heads/f4 $Z
refs/heads/f1 $marque refs/heads/f1 $Z"
stderr_contient "ajout.txt:2" "  stderr : lieu de la seconde ref"

essai_brut PASSE "$PUBLIC" "suppression d'une ref distante seule" \
	"(delete) $Z refs/heads/f1 $marque"

essai_brut PASSE "$PUBLIC" "suppression d'une ref puis ref propre" \
	"(delete) $Z refs/heads/f1 $marque
refs/heads/f4 $propre refs/heads/f4 $Z"

git tag t-leger f1
essai_brut BLOQUE "$PUBLIC" "tag léger sur un commit marqué" \
	"refs/tags/t-leger $marque refs/tags/t-leger $Z"

git tag -a t-annote -m "version" f1
essai_brut BLOQUE "$PUBLIC" "tag annoté sur un commit marqué" \
	"refs/tags/t-annote $(git rev-parse t-annote) refs/tags/t-annote $Z"

branche f5 plus.txt "++ serveur-9" "propre"
essai BLOQUE "$PUBLIC" "ligne ajoutée commençant par ++"
stderr_contient "plus.txt:1" "  stderr : ligne ++ bien située"

git checkout -q -B f6 "$M"
printf 'rien\r\nici Mot-Secret\r\n' >crlf.txt
git add crlf.txt
git commit -q -m "propre"
essai BLOQUE "ssh://git@github.com/a/public.git" "contenu en CRLF, URL ssh://"
stderr_contient "crlf.txt:2" "  stderr : ligne CRLF bien située"

printf 'serveur-[0-9]+\r\n' >"$tmp/marqueurs-crlf"
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs-crlf"
git checkout -q f1
essai BLOQUE "$PUBLIC" "fichier de marqueurs en CRLF"
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs"

git checkout -q --orphan f8
git rm -q -r --cached . >/dev/null
printf 'serveur-5\n' >orphelin.txt
git add orphelin.txt
git commit -q -m "orphelin Mot-Secret"
git clean -q -f
essai BLOQUE "$PUBLIC" "branche sans ancêtre commun"
stderr_contient "commit $(git rev-parse --short HEAD)" "  stderr : commit de la branche orpheline"
stderr_contient "orphelin.txt:1" "  stderr : fichier de la branche orpheline"

echo "— relais —"
crochet="$(git rev-parse --git-common-dir)/hooks/pre-push"
printf '#!/bin/sh\ntouch "%s"\n' "$tmp/relais-lance" >"$crochet"
chmod +x "$crochet"
essai BLOQUE "$PUBLIC" "refus du garde"
if [ -e "$tmp/relais-lance" ]; then o=LANCE; else o=NON_LANCE; fi
verdict NON_LANCE "$o" "  hook du dépôt non lancé après un refus"
git checkout -q -B f7 f4~1
essai PASSE "$PUBLIC" "push propre"
if [ -e "$tmp/relais-lance" ]; then o=LANCE; else o=NON_LANCE; fi
verdict LANCE "$o" "  hook du dépôt lancé après un passage"
rm -f "$crochet"

echo
if [ $echec -eq 0 ]; then echo "$nb cas, tous verts."; else echo "$nb cas, au moins un ECHEC."; fi
exit $echec
