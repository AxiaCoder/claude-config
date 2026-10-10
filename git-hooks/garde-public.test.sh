#!/bin/sh
# Cas de test du garde données personnelles (git-hooks/_garde-public), appelé par
# git-hooks/pre-push. Sortie 0 si tous passent.
#
# curl, gh et ssh sont remplacés par des bouchons placés en tête du PATH.
# curl : a/public et a/cache répondent 200, a/prive 404, a/repli 500, tout autre dépôt
# échoue (réseau). gh : a/public, a/cache et a/repli sont publics, a/prive privé, tout
# autre dépôt échoue, et tout appel échoue quand GH_TOKEN vaut « x ». ssh -G : l'alias
# github-perso résout vers github.com, tout autre hôte vers lui-même.

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
[ "\${GH_TOKEN:-}" = x ] && exit 1
case "\$3" in
a/public | a/cache | a/repli) echo PUBLIC ;;
a/prive) echo PRIVATE ;;
*) exit 1 ;;
esac
EOF
cat >"$tmp/bin/curl" <<EOF
#!/bin/sh
for arg; do url=\$arg; done
depot=\${url#https://api.github.com/repos/}
echo "\$depot" >>"$tmp/curl-appels"
case "\$depot" in
a/public | a/cache) printf 200 ;;
a/prive) printf 404 ;;
a/repli) printf 500 ;;
*) printf 000; exit 7 ;;
esac
EOF
cat >"$tmp/bin/ssh" <<'EOF'
#!/bin/sh
[ "$1" = -G ] || exit 255
case "$2" in
github-perso) echo "hostname github.com" ;;
*) echo "hostname $2" ;;
esac
echo "port 22"
EOF
chmod +x "$tmp/bin/gh" "$tmp/bin/curl" "$tmp/bin/ssh"
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
essai BLOQUE "git@github.com:a/inconnu.git" "curl et gh en échec"
stderr_contient "inconnue" "  stderr : visibilité inconnue"
stderr_contient ALLOW_PUSH_PERSONAL "  stderr : contournement proposé"
ALLOW_PUSH_PERSONAL=1
export ALLOW_PUSH_PERSONAL
essai PASSE "git@github.com:a/inconnu.git" "curl et gh en échec, ALLOW_PUSH_PERSONAL=1"
unset ALLOW_PUSH_PERSONAL
rm -f "$XDG_CACHE_HOME/claude-config/garde-public/a_public"
GH_TOKEN=x
export GH_TOKEN
essai BLOQUE "$PUBLIC" "GH_TOKEN invalide, dépôt public"
unset GH_TOKEN
rm -f "$XDG_CACHE_HOME/claude-config/garde-public/a_public"
: >"$tmp/gh-appels"
essai BLOQUE "git@github.com:a/repli.git" "curl 500, repli sur gh : public"
n=$(grep -c '^a/repli$' "$tmp/gh-appels")
verdict 1 "$n" "  appels à gh pour a/repli"
: >"$tmp/gh-appels"
essai BLOQUE "https://github.com/a/public" "curl 200, sans appel à gh"
n=$(grep -c . "$tmp/gh-appels")
verdict 0 "$n" "  appels à gh"

GARDE_PUBLIC_MARQUEURS="$tmp/absent"
essai PASSE "$PUBLIC" "fichier de marqueurs absent"
stderr_contient GARDE_PUBLIC_MARQUEURS "  stderr : avertissement marqueurs"
unset GARDE_PUBLIC_MARQUEURS
essai PASSE "$PUBLIC" "variable non définie"
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs"
export GARDE_PUBLIC_MARQUEURS

echo "— cache —"
: >"$tmp/curl-appels"
essai BLOQUE "https://github.com/a/cache.git" "1er push"
essai BLOQUE "git@github.com:a/cache" "2e push"
n=$(grep -c '^a/cache$' "$tmp/curl-appels")
verdict 1 "$n" "appels à curl pour a/cache"

touch -t 200001010000 "$XDG_CACHE_HOME/claude-config/garde-public/a_cache"
essai BLOQUE "https://github.com/a/cache/" "3e push, cache de plus de 24 h"
n=$(grep -c '^a/cache$' "$tmp/curl-appels")
verdict 2 "$n" "appels à curl pour a/cache après expiration"

essai PASSE "https://github.com/a/prive" "privé, 1er push"
essai PASSE "https://github.com/a/prive" "privé, 2e push"
n=$(grep -c '^a/prive$' "$tmp/curl-appels")
verdict 2 "$n" "appels à curl pour a/prive : privé jamais gardé"

mkdir -p "$XDG_CACHE_HOME/claude-config/garde-public"
echo PRIVATE >"$XDG_CACHE_HOME/claude-config/garde-public/a_public"
essai BLOQUE "$PUBLIC" "ancien cache PRIVATE ignoré"
rm -f "$XDG_CACHE_HOME/claude-config/garde-public/a_public"

echo "— alias ssh —"
essai BLOQUE "git@github-perso:a/public.git" "alias ssh vers github.com"
stderr_contient "a/public" "  stderr : dépôt nommé"
essai BLOQUE "ssh://git@github-perso:2222/a/public" "alias ssh://, avec port"
essai BLOQUE "ssh://git@github.com:22/a/public.git" "github.com en ssh:// avec port"
essai PASSE "git@nas-perso:a/public.git" "alias ssh vers un autre hôte"

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

echo "— noms de fichiers, tags, identités, motifs —"
git checkout -q -B f9 "$M"
: >Mot-Secret.txt
git add Mot-Secret.txt
git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "marqueur dans le nom d'un fichier ajouté vide"
stderr_contient "nom de fichier" "  stderr : lieu nom de fichier"

git checkout -q -B f10 f4~1
git mv propre.txt serveur-3.txt
git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "marqueur dans le nom d'un fichier renommé"

git checkout -q -B f11 f4~1
printf 'serveur-4\n' >"café.txt"
git add "café.txt"
git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "fichier au nom accentué"
stderr_contient "· café.txt:1 ·" "  stderr : chemin sans guillemets ni échappement"

git tag -a t-message -m "version Mot-Secret" f4~1
essai_brut BLOQUE "$PUBLIC" "marqueur dans le message d'un tag annoté" \
	"refs/tags/t-message $(git rev-parse t-message) refs/tags/t-message $Z"
stderr_contient "tag t-message" "  stderr : lieu tag"

git checkout -q -B f12 f4~1
printf 'x\n' >auteur.txt
git add auteur.txt
GIT_AUTHOR_NAME="Mot-Secret" git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "marqueur dans le nom de l'auteur"
stderr_contient "auteur" "  stderr : lieu auteur"

git checkout -q -B f13 f4~1
printf 'x\n' >committer.txt
git add committer.txt
GIT_COMMITTER_EMAIL="serveur-1@example.invalid" git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "marqueur dans l'e-mail du committer"
stderr_contient "committer" "  stderr : lieu committer"

git checkout -q f6
essai BLOQUE "$PUBLIC" "contenu en CRLF"
if grep -q "$(printf '\r')" "$tmp/err"; then o=PRESENT; else o=ABSENT; fi
verdict ABSENT "$o" "  stderr : extrait sans \\r final"

echo "— chaque commit, octets, attributs, durée —"
git checkout -q -B f15 f4~1
printf 'ajout mot-secret\n' >retire.txt
git add retire.txt
git commit -q -m "propre"
git rm -q retire.txt
git commit -q -m "propre"
essai BLOQUE "$PUBLIC" "marqueur ajouté puis retiré par le commit suivant"
stderr_contient "commit $(git rev-parse --short HEAD~1) · retire.txt:1" "  stderr : commit et fichier:ligne"

git checkout -q -B f16 f4~1
printf 'caf\351 cr\350me\n' >a-latin1.txt
printf 'serveur-8\n' >b-marque.txt
git add a-latin1.txt b-marque.txt
git commit -q -m "propre"
LC_ALL=fr_FR.UTF-8
export LC_ALL
essai BLOQUE "$PUBLIC" "fichier Latin-1 avant le fichier marqué, LC_ALL=fr_FR.UTF-8"
unset LC_ALL

git checkout -q -B f17 f4~1
printf 'serveur-6\n' >attribut.txt
git add attribut.txt
git commit -q -m "propre"
attributs="$(git rev-parse --git-common-dir)/info/attributes"
mkdir -p "$(dirname "$attributs")"
printf '* -diff\n' >"$attributs"
essai BLOQUE "$PUBLIC" "« * -diff » dans info/attributes"
rm -f "$attributs"

base_perf=$(git rev-parse f4~1)
i=1
while [ $i -le 300 ]; do
	printf 'commit refs/heads/f18\ncommitter essai <essai@example.invalid> %d +0000\ndata <<FIN\nc%d\nFIN\n' $((1700000000 + i)) "$i"
	[ $i -eq 1 ] && printf 'from %s\n' "$base_perf"
	printf 'M 100644 inline p%d.txt\ndata <<FIN\nligne a\nligne b\nligne c\nFIN\n\n' "$i"
	i=$((i + 1))
done | git fast-import --quiet
debut=$(date +%s)
essai_brut PASSE "$PUBLIC" "300 commits propres" \
	"refs/heads/f18 $(git rev-parse f18) refs/heads/f18 $Z"
duree=$(($(date +%s) - debut))
echo "      (300 commits : ${duree} s)"
if [ $duree -lt 3 ]; then o=RAPIDE; else o=LENT; fi
verdict RAPIDE "$o" "  300 commits en moins de 3 s"

printf 'Mot-Secret\n(\n' >"$tmp/marqueurs-invalides"
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs-invalides"
git checkout -q -B f14 f4~1
essai BLOQUE "$PUBLIC" "motif invalide, contenu propre"
stderr_contient "invalide" "  stderr : motif invalide signalé"
ALLOW_PUSH_PERSONAL=1
export ALLOW_PUSH_PERSONAL
essai PASSE "$PUBLIC" "motif invalide, ALLOW_PUSH_PERSONAL=1"
unset ALLOW_PUSH_PERSONAL
GARDE_PUBLIC_MARQUEURS="$tmp/marqueurs"
git checkout -q f8

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
