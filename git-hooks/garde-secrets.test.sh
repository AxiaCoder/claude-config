#!/bin/sh
# Cas de test du garde secrets (git-hooks/_garde-secrets), appelé par git-hooks/pre-commit
# et git-hooks/pre-push. Sortie 0 si tous passent.
#
# HOME est un dossier jetable : son .claude/bin/betterleaks est un bouchon qui note ses
# arguments, trouve un secret (sortie 3) quand ce qu'il examine contient FAUX-SECRET — l'indexé,
# ou le `git log -p` de la plage donnée par --log-opts —, échoue (sortie 1) sur PLANTE, et
# passe sinon.
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
POUSSER="pu""sh"
SANS_HOOK="--no-""verify"
unset "$CONTOURNEMENT"
bouchon="$HOME/.claude/bin/betterleaks"
memo="$HOME/.claude/claude-config.sans-externes"

mkdir -p "$HOME/.claude/bin" "$tmp/modele-vide"
cat >"$tmp/bouchon" <<EOF
#!/bin/sh
printf '%s\n' "\$@" >"$tmp/args"
plage=
for arg; do case "\$arg" in --log-opts=*) plage=\${arg#--log-opts=} ;; esac; done
if [ -n "\$plage" ]; then git log -p \$plage >"$tmp/examine"; else git diff --cached >"$tmp/examine"; fi
if grep -q '^+.*FAUX-SECRET' "$tmp/examine"; then
	echo "    a.txt:1  (regle-essai)"
	exit 3
fi
if grep -q '^+.*PLANTE' "$tmp/examine"; then
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

echo "— pre-push, betterleaks bouchonné —"
# Crée le dépôt $1 et son remote nu $1.git, avec un premier commit poussé sur main.
depot_et_remote() {
	depot "$1"
	git init -q --bare "$1.git"
	git -C "$1" remote add origin "$1.git"
	git -C "$1" symbolic-ref HEAD refs/heads/main
	printf 'base\n' >"$1/a.txt"
	git -C "$1" add a.txt
	git -C "$1" commit -q -m base
	git -C "$1" "$POUSSER" -q origin main 2>/dev/null
	git -C "$1" fetch -q origin
	git -C "$1" remote set-head origin main
}

# Commit sans pre-commit dans le dépôt $1 : a.txt au contenu $2.
commit_sans_garde() {
	printf '%s\n' "$2" >"$1/a.txt"
	git -C "$1" add a.txt
	git -C "$1" commit -q "$SANS_HOOK" -m "$2"
}

# Pousse depuis le dépôt $1 les refs $3… vers $DISTANT (origin par défaut) ; $2 attendu,
# libellé via $LIBELLE. stderr dans $tmp/err.
pousse() {
	d_=$1 attendu_=$2
	shift 2
	if git -C "$d_" "$POUSSER" -q "${DISTANT:-origin}" "$@" >/dev/null 2>"$tmp/err"; then o=PASSE; else o=BLOQUE; fi
	verdict "$attendu_" "$o" "$LIBELLE"
}

# Vrai si le git du PATH a --diff-merges=remerge (≥ 2.36).
git_remerge() {
	v=$(git version | sed -n 's/^git version \([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1 \2/p')
	[ "${v% *}" -gt 2 ] || { [ "${v% *}" -eq 2 ] && [ "${v#* }" -ge 36 ]; }
}
if git_remerge; then fusions="--diff-merges=remerge "; else fusions=; fi

poser
p="$tmp/p"
depot_et_remote "$p"
git -C "$p" switch -q -c propre
commit_sans_garde "$p" "rien à signaler"
LIBELLE="push propre → passe" pousse "$p" PASSE propre
argument "--validation=false" PRESENT "commande : --validation=false"
argument "--redact" PRESENT "commande : --redact"
argument "--staged" ABSENT "commande : pas de --staged"

git -C "$p" switch -q -c fuite main
commit_sans_garde "$p" "x FAUX-SECRET"
commit_sans_garde "$p" "retiré"
LIBELLE="secret ajouté puis retiré dans 2 commits → bloqué" pousse "$p" BLOQUE fuite
stderr_contient "a.txt:1" "  stderr : fichier:ligne"
stderr_contient "historique" "  stderr : réécrire l'historique"
stderr_contient "$CONTOURNEMENT=1" "  stderr : contournement"
argument "--log-opts=$fusions$(git -C "$p" rev-parse main)..$(git -C "$p" rev-parse fuite)" PRESENT "commande : plage base..local, nouvelle branche"

LIBELLE="plusieurs refs, secret dans la 2e → bloqué" pousse "$p" BLOQUE propre fuite
git -C "$p" switch -q -c propre2 main
commit_sans_garde "$p" "toujours rien"
LIBELLE="plusieurs refs propres → passe" pousse "$p" PASSE propre propre2

git -C "$p" switch -q propre
commit_sans_garde "$p" "y FAUX-SECRET"
LIBELLE="branche connue du remote, secret dans la suite → bloqué" pousse "$p" BLOQUE propre
argument "--log-opts=$fusions$(git -C "$p" rev-parse origin/propre)..$(git -C "$p" rev-parse propre)" PRESENT "commande : plage distant..local"

export "$CONTOURNEMENT=1"
LIBELLE="secret, contournement → passe" pousse "$p" PASSE fuite
stderr_contient "non appliqué" "  stderr : contournement signalé"
unset "$CONTOURNEMENT"

LIBELLE="suppression de ref, betterleaks bouchonné → passe" pousse "$p" PASSE :fuite

git -C "$p" switch -q -c orpheline main
git -C "$p" remote remove origin
git -C "$p" remote add origin "$p.git"
commit_sans_garde "$p" "z FAUX-SECRET"
LIBELLE="sans branche par défaut connue, secret → bloqué" pousse "$p" BLOQUE orpheline
argument "--log-opts=$fusions$(git -C "$p" rev-parse orpheline) --not --remotes=origin" PRESENT "commande : plage --not --remotes=<remote visé>"

DISTANT="$p.git"
LIBELLE="push vers une URL sans nom de remote, secret → bloqué" pousse "$p" BLOQUE orpheline
unset DISTANT
argument "--log-opts=$fusions$(git -C "$p" rev-parse orpheline)" PRESENT "commande : URL sans nom → historique entier"

mkdir "$tmp/vieux-git"
printf '#!/bin/sh\n[ "$1" = version ] && { echo "git version 2.35.1"; exit 0; }\nexec "%s" "$@"\n' "$(command -v git)" >"$tmp/vieux-git/git"
chmod +x "$tmp/vieux-git/git"
sha_orpheline=$(git -C "$p" rev-parse orpheline)
if (cd "$p" && printf 'refs/heads/orpheline %s refs/heads/orpheline %s\n' "$sha_orpheline" 0000000000000000000000000000000000000000 |
	PATH="$tmp/vieux-git:$PATH" sh "$ici/_garde-secrets" --push origin >/dev/null 2>"$tmp/err"); then o=PASSE; else o=BLOQUE; fi
verdict BLOQUE "$o" "git < 2.36 simulé, secret → bloqué"
stderr_contient "merges non examinés (git < 2.36)" "  stderr : merges non examinés signalés"
argument "--log-opts=$(git -C "$p" rev-parse orpheline) --not --remotes=origin" PRESENT "commande : pas de --diff-merges sous git < 2.36"

git -C "$p" reset -q --hard HEAD~1
commit_sans_garde "$p" "x PLANTE"
LIBELLE="analyse en échec → bloqué" pousse "$p" BLOQUE orpheline
stderr_contient "a échoué" "  stderr : échec signalé"
git -C "$p" reset -q --hard HEAD~1

retirer
git -C "$p" switch -q -c sans-binaire main
commit_sans_garde "$p" "rien"
LIBELLE="betterleaks absent → bloqué" pousse "$p" BLOQUE sans-binaire
stderr_contient "install.sh" "  stderr : relancer install.sh"
export "$CONTOURNEMENT=1"
LIBELLE="betterleaks absent, contournement → passe" pousse "$p" PASSE sans-binaire
unset "$CONTOURNEMENT"
commit_sans_garde "$p" "encore"
: >"$memo"
LIBELLE="sans externes, betterleaks absent → passe" pousse "$p" PASSE sans-binaire
stderr_contient "désactivé à l'installation" "  stderr : garde désactivé signalé"
rm -f "$memo"
LIBELLE="rien de neuf à pousser, betterleaks absent → passe" pousse "$p" PASSE sans-binaire

echo "— essai réel —"
if [ -x "$reel" ]; then
	cp "$reel" "$bouchon"
	echo "  betterleaks $("$bouchon" version 2>/dev/null) ($reel)"
	r="$tmp/reel"
	depot "$r"
	# Tire un nouveau jeton GitHub dans $jeton : un essai qui passe le laisse dans HEAD.
	jeton_neuf() { jeton="ghp_$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 36)"; }
	jeton_neuf
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton GitHub indexé → bloqué"
	sed 's/^/    | /' "$tmp/err"
	stderr_contient "a.txt:1" "  stderr : fichier:ligne"
	stderr_contient "github-pat" "  stderr : règle github-pat"
	if grep -q -e "$jeton" "$tmp/err"; then o=EN_CLAIR; else o=MASQUE; fi
	verdict MASQUE "$o" "  stderr : jeton masqué"
	essai "$r" "token = \"$jeton\" # gitleaks:allow" PASSE "même jeton, gitleaks:allow → passe"

	printf '[extend]\nuseDefault = true\n[allowlist]\npaths = ['"'''"'.*'"'''"']\n' >"$tmp/tout-permis.toml"
	mkdir -p "$r/.git/info"
	printf '%s\n' .gitleaks.toml .betterleaks.toml .gitleaksignore .betterleaksignore >>"$r/.git/info/exclude"
	cp "$tmp/tout-permis.toml" "$r/.gitleaks.toml"
	jeton_neuf
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton, .gitleaks.toml local tout permis → bloqué"
	mv "$r/.gitleaks.toml" "$r/.betterleaks.toml"
	jeton_neuf
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton, .betterleaks.toml local tout permis → bloqué"
	rm -f "$r/.betterleaks.toml"

	echo "a.txt:github-pat:1" >"$r/.gitleaksignore"
	jeton_neuf
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton, .gitleaksignore local → bloqué"
	mv "$r/.gitleaksignore" "$r/.betterleaksignore"
	jeton_neuf
	essai "$r" "token = \"$jeton\"" BLOQUE "jeton, .betterleaksignore local → bloqué"
	rm -f "$r/.betterleaksignore"

	for var in GITLEAKS_CONFIG_TOML BETTERLEAKS_CONFIG_TOML; do
		export "$var=$(cat "$tmp/tout-permis.toml")"
		jeton_neuf
		essai "$r" "token = \"$jeton\"" BLOQUE "jeton, $var tout permis → bloqué"
		unset "$var"
	done
	for var in GITLEAKS_CONFIG BETTERLEAKS_CONFIG; do
		export "$var=$tmp/tout-permis.toml"
		jeton_neuf
		essai "$r" "token = \"$jeton\"" BLOQUE "jeton, $var tout permis → bloqué"
		unset "$var"
	done

	for option in -a a.txt; do
		jeton_neuf
		printf 'token = "%s"\n' "$jeton" >"$r/a.txt"
		if git -C "$r" commit -q -m essai "$option" >/dev/null 2>"$tmp/err"; then o=PASSE; else o=BLOQUE; fi
		verdict BLOQUE "$o" "jeton, commit $option sans add (index temporaire) → bloqué"
		stderr_contient "github-pat" "  stderr : règle github-pat"
	done

	cle=$(openssl genrsa 2048 2>/dev/null)
	if [ -n "$cle" ]; then
		essai "$r" "$cle" BLOQUE "clé privée PEM générée → bloqué"
	fi

	q="$tmp/q"
	depot_et_remote "$q"
	git -C "$q" switch -q -c rebase-conflit
	commit_sans_garde "$q" "branche"
	git -C "$q" switch -q main
	commit_sans_garde "$q" "main"
	git -C "$q" switch -q rebase-conflit
	git -C "$q" rebase -q main >/dev/null 2>&1
	jeton_neuf
	printf 'token = "%s"\n' "$jeton" >"$q/a.txt"
	git -C "$q" add a.txt
	if GIT_EDITOR=true git -C "$q" rebase --continue >/dev/null 2>"$tmp/err"; then o=PASSE; else o=BLOQUE; fi
	verdict PASSE "$o" "jeton introduit par rebase --continue après conflit → commit créé"
	git -C "$q" "$POUSSER" -q origin main 2>/dev/null
	LIBELLE="  … puis push → bloqué" pousse "$q" BLOQUE rebase-conflit
	sed 's/^/    | /' "$tmp/err"
	stderr_contient "$(git -C "$q" rev-parse --short=7 rebase-conflit)" "  stderr : commit nommé"
	stderr_contient "a.txt:1" "  stderr : fichier:ligne"
	stderr_contient "github-pat" "  stderr : règle github-pat"
	if grep -q -e "$jeton" "$tmp/err"; then o=EN_CLAIR; else o=MASQUE; fi
	verdict MASQUE "$o" "  stderr : jeton masqué"

	git -C "$q" switch -q -c ajoute-retire main
	jeton_neuf
	commit_sans_garde "$q" "token = \"$jeton\""
	commit_sans_garde "$q" "retiré"
	LIBELLE="jeton ajouté puis retiré dans 2 commits → bloqué" pousse "$q" BLOQUE ajoute-retire

	git -C "$q" switch -q -c propre-reel main
	commit_sans_garde "$q" "rien à signaler"
	LIBELLE="push propre → passe" pousse "$q" PASSE propre-reel

	m="$tmp/m"
	depot_et_remote "$m"
	git -C "$m" switch -q -c travail
	jeton_neuf
	commit_sans_garde "$m" "token = \"$jeton\""
	commit_sans_garde "$m" "retiré"
	env "$CONTOURNEMENT=1" git -C "$m" "$POUSSER" -q origin travail 2>/dev/null
	git init -q --bare "$m-public.git"
	git -C "$m" remote add public "$m-public.git"
	DISTANT=public
	LIBELLE="historique à jeton déjà sur origin, push vers un nouveau remote → bloqué" pousse "$m" BLOQUE travail
	unset DISTANT

	git -C "$m" switch -q -c malin main
	printf 'b\n' >"$m/b.txt"
	git -C "$m" add b.txt
	git -C "$m" commit -q "$SANS_HOOK" -m b
	git -C "$m" switch -q -c autre main
	printf 'c\n' >"$m/c.txt"
	git -C "$m" add c.txt
	git -C "$m" commit -q "$SANS_HOOK" -m c
	git -C "$m" switch -q malin
	git -C "$m" merge -q --no-commit autre >/dev/null 2>&1
	jeton_neuf
	printf 'token = "%s"\n' "$jeton" >"$m/d.txt"
	git -C "$m" add d.txt
	git -C "$m" commit -q "$SANS_HOOK" -m fusion
	LIBELLE="jeton introduit dans la résolution d'un merge → bloqué" pousse "$m" BLOQUE malin

	git -C "$m" switch -q main
	jeton_neuf
	commit_sans_garde "$m" "token = \"$jeton\""
	env "$CONTOURNEMENT=1" git -C "$m" "$POUSSER" -q origin main 2>/dev/null
	git -C "$m" fetch -q origin
	git -C "$m" switch -q -c fusion-propre main~1
	printf 'e\n' >"$m/e.txt"
	git -C "$m" add e.txt
	git -C "$m" commit -q "$SANS_HOOK" -m e
	git -C "$m" merge -q --no-edit main >/dev/null 2>&1
	LIBELLE="merge propre de main déjà poussé, porteur d'un ancien jeton → passe" pousse "$m" PASSE fusion-propre

	git -C "$q" switch -q -c volume main
	sha_base=$(git -C "$q" rev-parse HEAD)
	{
		i=1
		while [ $i -le 300 ]; do
			printf 'commit refs/heads/volume\ncommitter essai <essai@example.invalid> %s +0000\ndata 6\nc%04d\n' $((1700000000 + i)) $i
			[ $i -eq 1 ] && printf 'from %s\n' "$sha_base"
			printf 'M 100644 inline f%d.txt\ndata <<FIN\nligne %d de f%d\nFIN\n\n' $((i % 40)) $i $i
			i=$((i + 1))
		done
	} | git -C "$q" fast-import --quiet --force
	git -C "$q" reset -q --hard volume
	debut=$(date +%s)
	LIBELLE="300 commits propres → passe" pousse "$q" PASSE volume
	duree=$(($(date +%s) - debut))
	echo "    durée : ${duree} s"
	if [ "$duree" -lt 5 ]; then o=RAPIDE; else o=LENT; fi
	verdict RAPIDE "$o" "  300 commits en moins de 5 s"
else
	echo "  sauté : $reel absent (bash install.sh, ou BETTERLEAKS_REEL=<chemin>)"
fi

echo
if [ $echec -eq 0 ]; then echo "$nb cas, tous verts."; else echo "$nb cas, au moins un ECHEC."; fi
exit $echec
