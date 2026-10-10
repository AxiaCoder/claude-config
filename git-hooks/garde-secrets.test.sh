#!/bin/sh
# Cas de test du garde secrets (git-hooks/_garde-secrets), appelé par git-hooks/pre-commit.
# Sortie 0 si tous passent.
#
# HOME est un dossier jetable : son .claude/bin/betterleaks est un bouchon qui note ses
# arguments, trouve un secret (sortie 3) dans un indexé qui contient FAUX-SECRET, échoue
# (sortie 1) sur PLANTE, et passe sinon.
#
# Essai réel en fin de fichier, avec le betterleaks désigné par BETTERLEAKS_REEL (par
# défaut celui de ~/.claude/bin) : sauté, et dit, quand il est absent. Les faux secrets
# sont générés à l'exécution : ce fichier n'en contient aucun.
#
# ⚠️ Le nom du réglage git de dossier de hooks et celui du contournement sont assemblés par
# concaténation : écrits en clair, ils déclencheraient le garde de session.

ici=$(cd "$(dirname "$0")" && pwd -P)
reel=${BETTERLEAKS_REEL:-$HOME/.claude/bin/betterleaks}
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
HOME="$tmp/home"
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM GIT_CEILING_DIRECTORIES HOME

REGLAGE="core.hooks""Path"
CONTOURNEMENT="ALLOW_""COMMIT_""SECRET"
unset "$CONTOURNEMENT"
bouchon="$HOME/.claude/bin/betterleaks"
memo="$HOME/.claude/claude-config.sans-externes"

mkdir -p "$HOME/.claude/bin" "$tmp/modele-vide"
cat >"$tmp/bouchon" <<EOF
#!/bin/sh
printf '%s\n' "\$@" >"$tmp/args"
if git diff --cached | grep -q '^+.*FAUX-SECRET'; then
	echo "    a.txt:1  (regle-essai)"
	exit 3
fi
if git diff --cached | grep -q '^+.*PLANTE'; then
	echo "erreur interne"
	exit 1
fi
exit 0
EOF
chmod +x "$tmp/bouchon"

echec=0
nb=0

# Affiche le verdict d'un cas. $1 attendu · $2 obtenu · $3 libellé.
verdict() {
	nb=$((nb + 1))
	if [ "$2" = "$1" ]; then v="  ok "; else v="ECHEC"; echec=1; fi
	printf '%s %-8s %s\n' "$v" "$2" "$3"
}

# Pose le bouchon dans ~/.claude/bin.
poser() { cp "$tmp/bouchon" "$bouchon"; }

# Retire betterleaks de ~/.claude/bin.
retirer() { rm -f "$bouchon"; }

# Crée le dépôt $1, pointé sur les hooks globaux de ce dossier.
depot() {
	git init -q --template="$tmp/modele-vide" "$1"
	git -C "$1" config --local "$REGLAGE" "$ici"
	mkdir -p "$1/.git/hooks"
}

# Indexe a.txt au contenu $2 dans le dépôt $1 et tente le commit ; $3 attendu · $4 libellé.
# stderr dans $tmp/err.
essai() {
	printf '%s\nessai %s\n' "$2" "$nb" >"$1/a.txt"
	git -C "$1" add a.txt
	if git -C "$1" commit -q -m essai >/dev/null 2>"$tmp/err"; then o=PASSE; else o=BLOQUE; fi
	git -C "$1" reset -q 2>/dev/null
	verdict "$3" "$o" "$4"
}

# Vérifie que stderr du dernier essai contient $1. $2 libellé.
stderr_contient() {
	if grep -q -e "$1" "$tmp/err"; then o=PRESENT; else o=ABSENT; fi
	verdict PRESENT "$o" "$2"
}

# Vérifie que le bouchon a reçu l'argument $1 exactement. $2 attendu (PRESENT/ABSENT) · $3 libellé.
argument() {
	if grep -q -x -e "$1" "$tmp/args"; then o=PRESENT; else o=ABSENT; fi
	verdict "$2" "$o" "$3"
}

d="$tmp/d"
depot "$d"

echo "— logique, betterleaks bouchonné —"
poser
essai "$d" "rien à signaler" PASSE "indexé propre"
essai "$d" "x FAUX-SECRET" BLOQUE "secret trouvé"
stderr_contient "a.txt:1" "  stderr : fichier:ligne"
stderr_contient "regle-essai" "  stderr : règle"
stderr_contient "gitleaks:allow" "  stderr : comment exempter"
stderr_contient "$CONTOURNEMENT=1" "  stderr : contournement"

argument "--validation=false" PRESENT "commande : --validation=false"
argument "--validation" ABSENT "commande : pas de --validation nu"
argument "--validation=true" ABSENT "commande : pas de --validation=true"
argument "--redact" PRESENT "commande : --redact"
argument "--staged" PRESENT "commande : --staged"
argument "--pre-commit" PRESENT "commande : --pre-commit"
nb_validation=$(grep -c -e '^--validation' "$tmp/args")
verdict 1 "$nb_validation" "commande : un seul argument --validation…"

export "$CONTOURNEMENT=1"
essai "$d" "x FAUX-SECRET" PASSE "secret trouvé, contournement → passe"
unset "$CONTOURNEMENT"

essai "$d" "x PLANTE" BLOQUE "analyse en échec → bloqué"
stderr_contient "a échoué" "  stderr : échec signalé"

retirer
essai "$d" "rien à signaler" BLOQUE "betterleaks absent → bloqué"
stderr_contient "install.sh" "  stderr : relancer install.sh"
stderr_contient "install.ps1" "  stderr : relancer install.ps1"
stderr_contient "$CONTOURNEMENT=1" "  stderr : contournement"

export "$CONTOURNEMENT=1"
essai "$d" "rien à signaler" PASSE "betterleaks absent, contournement → passe"
unset "$CONTOURNEMENT"

: >"$memo"
essai "$d" "x FAUX-SECRET" PASSE "sans externes, betterleaks absent → passe"
stderr_contient "désactivé à l'installation" "  stderr : garde désactivé signalé"
rm -f "$memo"

if git -C "$d" commit -q --allow-empty -m vide >/dev/null 2>&1; then o=PASSE; else o=BLOQUE; fi
verdict PASSE "$o" "rien d'indexé, betterleaks absent → passe"

mkdir "$tmp/hors"
if (cd "$tmp/hors" && sh "$ici/pre-commit" </dev/null >/dev/null 2>&1); then o=PASSE; else o=BLOQUE; fi
verdict PASSE "$o" "hors dépôt → passe"

echo "— relais —"
poser
printf '#!/bin/sh\ntouch "%s"\n' "$tmp/relais-lance" >"$d/.git/hooks/pre-commit"
chmod +x "$d/.git/hooks/pre-commit"
essai "$d" "z FAUX-SECRET" BLOQUE "refus du garde"
if [ -e "$tmp/relais-lance" ]; then o=LANCE; else o=NON_LANCE; fi
verdict NON_LANCE "$o" "  hook du dépôt non lancé après un refus"
essai "$d" "rien à signaler" PASSE "indexé propre"
if [ -e "$tmp/relais-lance" ]; then o=LANCE; else o=NON_LANCE; fi
verdict LANCE "$o" "  hook du dépôt lancé après un passage"
rm -f "$d/.git/hooks/pre-commit"

echo "— essai réel —"
if [ -x "$reel" ]; then
	cp "$reel" "$bouchon"
	echo "  betterleaks $("$bouchon" version 2>/dev/null) ($reel)"
	r="$tmp/reel"
	depot "$r"
	jeton="ghp_$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 36)"
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton GitHub indexé → bloqué"
	sed 's/^/    | /' "$tmp/err"
	stderr_contient "a.txt:1" "  stderr : fichier:ligne"
	stderr_contient "github-pat" "  stderr : règle github-pat"
	if grep -q -e "$jeton" "$tmp/err"; then o=EN_CLAIR; else o=MASQUE; fi
	verdict MASQUE "$o" "  stderr : jeton masqué"
	essai "$r" "token = \"$jeton\" # gitleaks:allow" PASSE "même jeton, gitleaks:allow → passe"
	cle=$(openssl genrsa 2048 2>/dev/null)
	if [ -n "$cle" ]; then
		essai "$r" "$cle" BLOQUE "clé privée PEM générée → bloqué"
	fi
else
	echo "  sauté : $reel absent (bash install.sh, ou BETTERLEAKS_REEL=<chemin>)"
fi

echo
if [ $echec -eq 0 ]; then echo "$nb cas, tous verts."; else echo "$nb cas, au moins un ECHEC."; fi
exit $echec
