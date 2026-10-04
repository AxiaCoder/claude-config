#!/bin/sh
# Cas de test de la fusion de settings.json par install.sh. Sortie 0 si tous passent.
#
# Cas de test du rendu de CLAUDE.md, avec ou sans le CLAUDE.md ou le CLAUDE.complet.md du dossier perso.
#
# install.sh tourne sur une copie, avec un faux dépôt, un faux dossier perso et un HOME
# jetables : ni le vrai ~/.claude, ni le vrai dossier perso, ni la config git globale.

ici=$(cd "$(dirname "$0")" && pwd -P)
tmp=$(mktemp -d)
trap 'chmod -R u+w "$tmp" 2>/dev/null; rm -rf "$tmp"' EXIT

: >"$tmp/gitconfig-vide"
GIT_CONFIG_GLOBAL="$tmp/gitconfig-vide"
GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM

echec=0
nb=0

# Affiche le verdict d'un cas. $1 attendu · $2 obtenu · $3 libellé.
verdict() {
	nb=$((nb + 1))
	if [ "$2" = "$1" ]; then v="  ok "; else v="ECHEC"; echec=1; fi
	printf '%s %-24s %s\n' "$v" "$2" "$3"
}

# Monte un faux dépôt, un HOME vide et un dossier perso vide sous $tmp/$1.
monter() {
	racine="$tmp/$1"
	mkdir -p "$racine/repo" "$racine/home/.claude" "$racine/perso"
	cp "$ici/../install.sh" "$racine/repo/install.sh"
	printf '# avant\n\n{{PERSO_CLAUDE_MD}}\n\n# apres\n' >"$racine/repo/CLAUDE.md"
	: >"$racine/repo/CAVEMAN.md"
	cat >"$racine/repo/settings.base.json" <<'EOF'
{"model": "base", "effort": "base", "env": {"A": "base", "B": "base", "C": "base"}}
EOF
	cat >"$racine/repo/settings.macos.json" <<'EOF'
{"effort": "macos", "env": {"B": "macos", "C": "macos"}}
EOF
}

# Lance install.sh du montage $1, les arguments suivants lui étant passés. Sortie : son code retour.
installer() {
	m="$1"
	shift
	HOME="$tmp/$m/home" bash "$tmp/$m/repo/install.sh" "$@" >"$tmp/$m/sortie" 2>&1
}

# Affiche la valeur de settings.json du montage $1 au chemin $2 (« env.A », « model »).
lire() {
	python3 - "$tmp/$1/home/.claude/settings.json" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for k in sys.argv[2].split("."):
    d = d.get(k, "(absent)") if isinstance(d, dict) else "(absent)"
print(d)
PY
}

# Sans --perso ni mémo : l'install passe, base + macOS seuls.
monter sans-perso
installer sans-perso; verdict 0 "$?" "sans perso : install sans erreur"
verdict macos "$(lire sans-perso env.C)" "sans perso : macOS gagne sur base"
verdict "(absent)" "$(lire sans-perso env.D)" "sans perso : aucune variable perso"
verdict absent "$([ -f "$tmp/sans-perso/home/.claude/claude-config.perso" ] && echo present || echo absent)" "sans perso : aucun mémo écrit"

# Un --perso vide de couches : l'install passe, base + macOS seuls.
monter perso-vide
installer perso-vide --perso "$tmp/perso-vide/perso"; verdict 0 "$?" "perso vide : install sans erreur"
verdict macos "$(lire perso-vide env.C)" "perso vide : macOS gagne sur base"

# Les deux couches perso présentes.
monter avec-perso
cat >"$tmp/avec-perso/perso/settings.json" <<'EOF'
{"model": "perso", "env": {"C": "perso", "D": "perso"}}
EOF
cat >"$tmp/avec-perso/perso/settings.macos.json" <<'EOF'
{"env": {"D": "perso-macos", "E": "perso-macos"}}
EOF
installer avec-perso --perso "$tmp/avec-perso/perso"; verdict 0 "$?" "avec perso : install sans erreur"
verdict base "$(lire avec-perso env.A)" "env : clé de base gardée sous le perso"
verdict macos "$(lire avec-perso env.B)" "env : clé macOS gardée sous le perso"
verdict perso "$(lire avec-perso env.C)" "env : perso gagne sur macOS"
verdict perso-macos "$(lire avec-perso env.D)" "env : perso macOS gagne sur perso"
verdict perso-macos "$(lire avec-perso env.E)" "env : clé ajoutée par perso macOS"
verdict perso "$(lire avec-perso model)" "hors env : perso gagne sur base"
verdict macos "$(lire avec-perso effort)" "hors env : macOS gardé sans perso"

# Le --perso est mémorisé : une 2e passe sans --perso applique encore ses couches.
rm -f "$tmp/avec-perso/home/.claude/settings.json"
installer avec-perso; verdict 0 "$?" "perso mémorisé : 2e passe sans erreur"
verdict perso-macos "$(lire avec-perso env.D)" "perso mémorisé : couches perso appliquées"

# Seule la couche perso macOS présente : les autres sont sautées.
monter perso-macos-seul
cat >"$tmp/perso-macos-seul/perso/settings.macos.json" <<'EOF'
{"env": {"C": "perso-macos"}}
EOF
installer perso-macos-seul --perso "$tmp/perso-macos-seul/perso"; verdict 0 "$?" "perso macOS seul : install sans erreur"
verdict perso-macos "$(lire perso-macos-seul env.C)" "perso macOS seul : gagne sur macOS"

# Un --perso vers un dossier inexistant : refus, rien d'écrit.
monter perso-introuvable
installer perso-introuvable --perso "$tmp/perso-introuvable/nulle-part"
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "perso introuvable : install refusée"
verdict absent "$([ -f "$tmp/perso-introuvable/home/.claude/settings.json" ] && echo present || echo absent)" "perso introuvable : settings.json non écrit"
verdict nomme "$(grep -q 'dossier perso est introuvable' "$tmp/perso-introuvable/sortie" && echo nomme || echo muet)" "perso introuvable : le refus nomme le dossier perso"

# Un mémo vers un dossier disparu, sans --perso : refus qui nomme le mémo.
monter memo-perime
printf '%s\n' "$tmp/memo-perime/disparu" >"$tmp/memo-perime/home/.claude/claude-config.perso"
installer memo-perime
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "mémo périmé : install refusée"
verdict nomme "$(grep -q 'claude-config.perso' "$tmp/memo-perime/sortie" && echo nomme || echo muet)" "mémo périmé : le refus nomme le mémo"

# --dry-run n'écrit pas le mémo.
monter perso-dry-run
installer perso-dry-run --perso "$tmp/perso-dry-run/perso" --dry-run; verdict 0 "$?" "dry-run : install sans erreur"
verdict absent "$([ -f "$tmp/perso-dry-run/home/.claude/claude-config.perso" ] && echo present || echo absent)" "dry-run : mémo non écrit"

# Affiche le CLAUDE.md rendu du montage $1, fins de ligne rendues visibles en « | ».
rendu() {
	tr '\n' '|' <"$tmp/$1/home/.claude/CLAUDE.md"
}

# CLAUDE.md sans perso : le marqueur et sa ligne vide disparaissent, le reste est intact.
verdict '# avant||# apres|' "$(rendu sans-perso)" "CLAUDE.md sans perso : marqueur retiré"

# CLAUDE.md avec un perso qui n'en a pas : idem.
verdict '# avant||# apres|' "$(rendu perso-vide)" "CLAUDE.md perso sans CLAUDE.md : marqueur retiré"

# CLAUDE.md avec un perso qui en a un : inséré à la place du marqueur, {{PERSO}} résolu.
monter perso-md
printf '## perso\nvoir {{PERSO}}/../x/y.md\nhub {{PERSO}}/../\n' >"$tmp/perso-md/perso/CLAUDE.md"
installer perso-md --perso "$tmp/perso-md/perso"; verdict 0 "$?" "CLAUDE.md perso : install sans erreur"
perso_parent=$(cd "$tmp/perso-md" && pwd)
verdict "# avant||## perso|voir $perso_parent/x/y.md|hub $perso_parent/||# apres|" "$(rendu perso-md)" "CLAUDE.md perso : inséré, avant/après intacts"
verdict oui "$(grep -qxF "voir $perso_parent/x/y.md" "$tmp/perso-md/home/.claude/CLAUDE.md" && echo oui || echo non)" "{{PERSO}}/../x/y.md : chemin absolu normalisé"
verdict oui "$(grep -qxF "hub $perso_parent/" "$tmp/perso-md/home/.claude/CLAUDE.md" && echo oui || echo non)" "{{PERSO}}/../ : garde son / final"

# Marqueur suivi d'une seule fin de ligne, avec un perso qui a un CLAUDE.md : marqueur consommé, perso inséré.
monter marqueur-serre
printf '# avant\n{{PERSO_CLAUDE_MD}}\n# apres\n' >"$tmp/marqueur-serre/repo/CLAUDE.md"
printf '## perso serre\n' >"$tmp/marqueur-serre/perso/CLAUDE.md"
installer marqueur-serre --perso "$tmp/marqueur-serre/perso"; verdict 0 "$?" "marqueur serré : install sans erreur"
verdict absent "$(grep -qF '{{PERSO' "$tmp/marqueur-serre/home/.claude/CLAUDE.md" && echo present || echo absent)" "marqueur serré : marqueur absent du rendu"
verdict oui "$(grep -qxF '## perso serre' "$tmp/marqueur-serre/home/.claude/CLAUDE.md" && echo oui || echo non)" "marqueur serré : perso inséré"

# Marqueur suivi d'une seule fin de ligne, sans perso : marqueur consommé.
monter marqueur-serre-sans-perso
printf '# avant\n{{PERSO_CLAUDE_MD}}\n# apres\n' >"$tmp/marqueur-serre-sans-perso/repo/CLAUDE.md"
installer marqueur-serre-sans-perso; verdict 0 "$?" "marqueur serré sans perso : install sans erreur"
verdict absent "$(grep -qF '{{PERSO' "$tmp/marqueur-serre-sans-perso/home/.claude/CLAUDE.md" && echo present || echo absent)" "marqueur serré sans perso : marqueur absent"

# Un rendu qui garde un marqueur {{PERSO…}} : l'install échoue et nomme le marqueur.
monter marqueur-residuel
printf '## perso\nreste {{PERSO_CLAUDE_MD}}\n' >"$tmp/marqueur-residuel/perso/CLAUDE.md"
installer marqueur-residuel --perso "$tmp/marqueur-residuel/perso"
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "marqueur résiduel : install refusée"
verdict nomme "$(grep -q 'PERSO' "$tmp/marqueur-residuel/sortie" && echo nomme || echo muet)" "marqueur résiduel : le refus nomme le marqueur"

# Un perso avec CLAUDE.complet.md seul : il devient le CLAUDE.md rendu, {{PERSO}} résolu, celui du dépôt non lu.
monter complet-seul
printf '# complet\nvoir {{PERSO}}/../x\n' >"$tmp/complet-seul/perso/CLAUDE.complet.md"
installer complet-seul --perso "$tmp/complet-seul/perso"; verdict 0 "$?" "complet seul : install sans erreur"
complet_parent=$(cd "$tmp/complet-seul" && pwd)
verdict "# complet|voir $complet_parent/x|" "$(rendu complet-seul)" "complet seul : rendu = complet, {{PERSO}} résolu"
verdict absent "$(grep -qE '^# (avant|apres)$' "$tmp/complet-seul/home/.claude/CLAUDE.md" && echo present || echo absent)" "complet seul : CLAUDE.md du dépôt non lu"
verdict muet "$(grep -qF 'est ignoré' "$tmp/complet-seul/sortie" && echo annonce || echo muet)" "complet seul : aucun CLAUDE.md perso annoncé ignoré"

# CLAUDE.complet.md et CLAUDE.md dans le perso : le complet gagne, l'install annonce l'autre ignoré.
monter complet-et-md
printf '# complet gagne\n' >"$tmp/complet-et-md/perso/CLAUDE.complet.md"
printf '## perso ignore\n' >"$tmp/complet-et-md/perso/CLAUDE.md"
installer complet-et-md --perso "$tmp/complet-et-md/perso"; verdict 0 "$?" "complet + CLAUDE.md : install sans erreur"
verdict '# complet gagne|' "$(rendu complet-et-md)" "complet + CLAUDE.md : le complet gagne"
verdict annonce "$(grep -qF "CLAUDE.md : le CLAUDE.md du dossier perso est ignoré, CLAUDE.complet.md le remplace" "$tmp/complet-et-md/sortie" && echo annonce || echo muet)" "complet + CLAUDE.md : CLAUDE.md perso annoncé ignoré"

# Sans CLAUDE.complet.md, un perso avec CLAUDE.md : aucune annonce d'un CLAUDE.md ignoré.
verdict muet "$(grep -qF 'est ignoré' "$tmp/perso-md/sortie" && echo annonce || echo muet)" "CLAUDE.md perso sans complet : rien annoncé ignoré"

# Un CLAUDE.complet.md qui garde {{PERSO_CLAUDE_MD}} : refus, CLAUDE.md non écrit.
monter complet-marqueur
printf '# complet\n{{PERSO_CLAUDE_MD}}\n' >"$tmp/complet-marqueur/perso/CLAUDE.complet.md"
installer complet-marqueur --perso "$tmp/complet-marqueur/perso"
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "complet à marqueur : install refusée"
verdict absent "$([ -f "$tmp/complet-marqueur/home/.claude/CLAUDE.md" ] && echo present || echo absent)" "complet à marqueur : CLAUDE.md non écrit"

# --brain est retiré : refus.
monter option-brain
installer option-brain --brain "$tmp/option-brain/perso"
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "--brain : option refusée"

# Pose dans le HOME du montage $1 un CLAUDE.md, un CAVEMAN.md et un settings.json de l'utilisateur.
preexistants() {
	printf '# mon CLAUDE.md\n' >"$tmp/$1/home/.claude/CLAUDE.md"
	printf '# mon CAVEMAN.md\n' >"$tmp/$1/home/.claude/CAVEMAN.md"
	printf '{"model": "le mien"}\n' >"$tmp/$1/home/.claude/settings.json"
	mkdir -p "$tmp/$1/originaux"
	cp "$tmp/$1/home/.claude/CLAUDE.md" "$tmp/$1/home/.claude/CAVEMAN.md" "$tmp/$1/home/.claude/settings.json" "$tmp/$1/originaux/"
}

# Affiche le nombre de dossiers config-backup-* du HOME du montage $1.
sauvegardes() {
	find "$tmp/$1/home/.claude" -maxdepth 1 -name 'config-backup-*' -type d | wc -l | tr -d ' '
}

# 1re passe sur des fichiers de l'utilisateur : les trois sauvegardés à l'identique.
monter premiere-passe
preexistants premiere-passe
installer premiere-passe; verdict 0 "$?" "1re passe : install sans erreur"
verdict 1 "$(sauvegardes premiere-passe)" "1re passe : un dossier de sauvegarde"
for f in CLAUDE.md CAVEMAN.md settings.json; do
	verdict identique "$(cmp -s "$tmp/premiere-passe/originaux/$f" "$tmp/premiere-passe/home/.claude/config-backup-"*"/$f" && echo identique || echo differe)" "1re passe : $f sauvegardé à l'identique"
done

# 2e passe : les fichiers rendus ne sont plus ceux de l'utilisateur, aucune nouvelle sauvegarde.
for d in "$tmp/premiere-passe/home/.claude/config-backup-"*; do [ -d "$d" ] && mv "$d" "$tmp/premiere-passe/sauvegarde-1"; done
installer premiere-passe; verdict 0 "$?" "2e passe : install sans erreur"
verdict 0 "$(sauvegardes premiere-passe)" "2e passe : aucune sauvegarde"
verdict muet "$(grep -q 'existant, sauvegardé' "$tmp/premiere-passe/sortie" && echo annonce || echo muet)" "2e passe : aucune sauvegarde annoncée"

# 1re passe sur un HOME vierge : rien à sauvegarder, aucun dossier.
verdict 0 "$(sauvegardes sans-perso)" "HOME vierge : aucun dossier de sauvegarde"

# --dry-run sur des fichiers de l'utilisateur : rien copié, rien réécrit.
monter sauvegarde-dry-run
preexistants sauvegarde-dry-run
installer sauvegarde-dry-run --dry-run; verdict 0 "$?" "dry-run sauvegarde : install sans erreur"
verdict 0 "$(sauvegardes sauvegarde-dry-run)" "dry-run sauvegarde : aucun dossier"
verdict identique "$(cmp -s "$tmp/sauvegarde-dry-run/originaux/settings.json" "$tmp/sauvegarde-dry-run/home/.claude/settings.json" && echo identique || echo differe)" "dry-run sauvegarde : settings.json intact"

# Un overlay qui garde un marqueur inconnu : refus, settings.json de l'utilisateur intact.
monter marqueur-settings
preexistants marqueur-settings
cat >"$tmp/marqueur-settings/repo/settings.macos.json" <<'EOF'
{"env": {"C": "{{INCONNU}}"}}
EOF
installer marqueur-settings
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "marqueur settings : install refusée"
verdict identique "$(cmp -s "$tmp/marqueur-settings/originaux/settings.json" "$tmp/marqueur-settings/home/.claude/settings.json" && echo identique || echo differe)" "marqueur settings : settings.json non réécrit"
verdict nomme "$(grep -qF '{{INCONNU}}' "$tmp/marqueur-settings/sortie" && echo nomme || echo muet)" "marqueur settings : le refus nomme le marqueur"

# 1re passe interrompue dans la boucle des liens, puis relancée : le CLAUDE.md de l'utilisateur reste sauvegardé.
monter passe-interrompue
preexistants passe-interrompue
mkdir -p "$tmp/passe-interrompue/home/.claude/git-hooks"
chmod 555 "$tmp/passe-interrompue/home/.claude/git-hooks"
installer passe-interrompue
verdict refus "$([ "$?" -ne 0 ] && echo refus || echo accepte)" "passe interrompue : 1re passe en échec"
chmod 755 "$tmp/passe-interrompue/home/.claude/git-hooks"
installer passe-interrompue; verdict 0 "$?" "passe interrompue : relance sans erreur"
verdict sauvegarde "$(cat "$tmp/passe-interrompue/home/.claude/config-backup-"*/CLAUDE.md 2>/dev/null | grep -qxF '# mon CLAUDE.md' && echo sauvegarde || echo perdu)" "passe interrompue : CLAUDE.md de l'utilisateur sauvegardé"

# Affiche en JSON compact la valeur de settings.json du montage $1 au chemin $2 (« permissions.allow »).
lire_json() {
	python3 - "$tmp/$1/home/.claude/settings.json" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for k in sys.argv[2].split("."):
    d = d.get(k, "(absent)") if isinstance(d, dict) else "(absent)"
print(d if d == "(absent)" else json.dumps(d, separators=(",", ":"), ensure_ascii=False))
PY
}

# Affiche, séparées par des virgules, les commandes des hooks de l'événement $2 du montage $1, dans l'ordre.
commandes() {
	python3 - "$tmp/$1/home/.claude/settings.json" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
blocs = d.get("hooks", {}).get(sys.argv[2], [])
print(",".join(h["command"] for b in blocs for h in b.get("hooks", [])) or "(aucune)")
PY
}

# Pose dans le montage $1 un socle qui définit hooks et permissions, sans model.
socle_hooks() {
	cat >"$tmp/$1/repo/settings.base.json" <<'EOF'
{"effort": "base",
 "hooks": {"PreToolUse": [
   {"matcher": "Bash", "hooks": [{"type": "command", "command": "repo-garde"}]},
   {"matcher": "Edit", "hooks": [{"type": "command", "command": "commun"}]}]},
 "permissions": {"allow": ["Read", "Grep"], "additionalDirectories": ["/repo-dir"], "defaultMode": "default"}}
EOF
	printf '{"effort": "macos"}\n' >"$tmp/$1/repo/settings.macos.json"
}

# Pose dans le HOME du montage $1 un settings.json avec un model, un hook Notification et un allow X.
existant_hooks() {
	cat >"$tmp/$1/home/.claude/settings.json" <<'EOF'
{"model": "le mien",
 "hooks": {"Notification": [{"hooks": [{"type": "command", "command": "vieux"}]}]},
 "permissions": {"allow": ["X"]}}
EOF
}

# Le perso n'ajoute qu'un hook Stop : les hooks du dépôt restent.
monter hook-stop
socle_hooks hook-stop
printf '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "perso-stop"}]}]}}\n' >"$tmp/hook-stop/perso/settings.json"
installer hook-stop --perso "$tmp/hook-stop/perso"; verdict 0 "$?" "hook Stop perso : install sans erreur"
verdict repo-garde,commun "$(commandes hook-stop PreToolUse)" "hooks : ceux du dépôt gardés sous le perso"
verdict perso-stop "$(commandes hook-stop Stop)" "hooks : Stop ajouté par le perso"

# Le perso ajoute des blocs au même événement, dont un identique à celui du dépôt.
monter fusion
socle_hooks fusion
existant_hooks fusion
cat >"$tmp/fusion/perso/settings.json" <<'EOF'
{"hooks": {"PreToolUse": [
   {"matcher": "Write", "hooks": [{"type": "command", "command": "perso-garde"}]},
   {"matcher": "Edit", "hooks": [{"type": "command", "command": "commun"}]}]},
 "permissions": {"allow": ["Grep", "Bash(ls:*)"], "defaultMode": "acceptEdits"}}
EOF
installer fusion --perso "$tmp/fusion/perso"; verdict 0 "$?" "fusion : install sans erreur"
verdict repo-garde,commun,perso-garde "$(commandes fusion PreToolUse)" "hooks : dépôt puis perso, bloc identique une fois"
verdict '["Read","Grep","Bash(ls:*)"]' "$(lire_json fusion permissions.allow)" "permissions : allow en union sans doublon"
verdict '["/repo-dir"]' "$(lire_json fusion permissions.additionalDirectories)" "permissions : liste du dépôt gardée sous le perso"
verdict '"acceptEdits"' "$(lire_json fusion permissions.defaultMode)" "permissions : non-liste, le perso gagne"
verdict vieux "$(commandes fusion Notification)" "hooks : celui d'un autre outil, dans l'existant, gardé"
verdict absent "$(lire_json fusion permissions.allow | grep -qF '"X"' && echo present || echo absent)" "permissions : allow de l'existant retiré"
verdict '"le mien"' "$(lire_json fusion model)" "hors couches : model de l'existant gardé"

# 2e passe : settings.json identique octet pour octet.
cp "$tmp/fusion/home/.claude/settings.json" "$tmp/fusion/settings-passe-1.json"
installer fusion; verdict 0 "$?" "fusion 2e passe : install sans erreur"
verdict identique "$(cmp -s "$tmp/fusion/settings-passe-1.json" "$tmp/fusion/home/.claude/settings.json" && echo identique || echo differe)" "fusion 2e passe : settings.json identique"

# L'existant mêle des hooks d'autres outils et des hooks à nous (sous <CLAUDE_HOME>/hooks).
monter etrangers
socle_hooks etrangers
et_home="$tmp/etrangers/home/.claude"
cat >"$et_home/settings.json" <<EOF
{"hooks": {
   "PreToolUse": [
     {"matcher": "Edit", "hooks": [{"type": "command", "command": "commun"}]},
     {"matcher": "Bash", "hooks": [{"type": "command", "command": "tiers"}]},
     {"matcher": "Write", "hooks": [
       {"type": "command", "command": "tiers-mixte"},
       {"type": "command", "command": "$et_home/hooks/ancien.py"}]}],
   "Stop": [{"hooks": [{"type": "command", "command": "$et_home/hooks/ancien.py"}]}],
   "SessionStart": [{"hooks": [
     {"type": "command", "command": "python3 \"$et_home/hooks/demarrage.py\""},
     {"type": "command", "command": "{{CLAUDE_HOME}}/hooks/autre.py"}]}]}}
EOF
installer etrangers; verdict 0 "$?" "étrangers : install sans erreur"
verdict repo-garde,commun,tiers,tiers-mixte "$(commandes etrangers PreToolUse)" "hooks : étrangers après les couches, identique une fois"
verdict '[{"type":"command","command":"tiers-mixte"}]' "$(python3 -c 'import json,sys; print(json.dumps([b["hooks"] for b in json.load(open(sys.argv[1]))["hooks"]["PreToolUse"] if b.get("matcher") == "Write"][0], separators=(",", ":")))' "$et_home/settings.json" 2>&1)" "hooks : bloc mixte, seul l'étranger reste, matcher Write gardé"
verdict '(absent)' "$(lire_json etrangers hooks.Stop)" "hooks : celui à nous de l'existant retiré"
verdict '(absent)' "$(lire_json etrangers hooks.SessionStart)" "hooks : bloc de l'existant tout à nous retiré"
cp "$et_home/settings.json" "$tmp/etrangers/settings-passe-1.json"
installer etrangers; verdict 0 "$?" "étrangers 2e passe : install sans erreur"
verdict identique "$(cmp -s "$tmp/etrangers/settings-passe-1.json" "$et_home/settings.json" && echo identique || echo differe)" "étrangers 2e passe : settings.json identique"

# Aucune couche ne définit hooks ni permissions : ceux de l'existant restent.
monter sans-cle
existant_hooks sans-cle
installer sans-cle; verdict 0 "$?" "sans hooks ni permissions : install sans erreur"
verdict '["X"]' "$(lire_json sans-cle permissions.allow)" "permissions : existant gardé si aucune couche n'en a"
verdict vieux "$(commandes sans-cle Notification)" "hooks : existant gardé si aucune couche n'en a"

# Le perso recopie, chemins déjà développés, un bloc et un dossier que le dépôt porte à marqueur : une fois chacun.
monter marqueur-developpe
cat >"$tmp/marqueur-developpe/repo/settings.base.json" <<'EOF'
{"hooks": {"PreToolUse": [
   {"matcher": "Bash", "hooks": [{"type": "command", "command": "{{CLAUDE_HOME}}/hooks/guardrail.py"}]}]},
 "permissions": {"additionalDirectories": ["{{REPO}}"]}}
EOF
printf '{}\n' >"$tmp/marqueur-developpe/repo/settings.macos.json"
md_home="$tmp/marqueur-developpe/home/.claude"
md_repo="$tmp/marqueur-developpe/repo"
cat >"$tmp/marqueur-developpe/perso/settings.json" <<EOF
{"hooks": {"PreToolUse": [
   {"matcher": "Bash", "hooks": [{"type": "command", "command": "$md_home/hooks/guardrail.py"}]}]},
 "permissions": {"additionalDirectories": ["$md_repo"]}}
EOF
installer marqueur-developpe --perso "$tmp/marqueur-developpe/perso"; verdict 0 "$?" "marqueur développé : install sans erreur"
verdict "$md_home/hooks/guardrail.py" "$(commandes marqueur-developpe PreToolUse)" "hooks : bloc à marqueur et son rendu perso, une fois"
verdict "[\"$md_repo\"]" "$(lire_json marqueur-developpe permissions.additionalDirectories)" "permissions : {{REPO}} et son rendu perso, une fois"

# Un hook déclaré par le perso hors <CLAUDE_HOME>/hooks, puis retiré du perso : la passe suivante le retire.
monter perso-retire
socle_hooks perso-retire
printf '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "{{REPO}}/../perso/mine.sh"}]}]}}\n' >"$tmp/perso-retire/perso/settings.json"
installer perso-retire --perso "$tmp/perso-retire/perso"; verdict 0 "$?" "perso retiré : 1re passe sans erreur"
verdict "$tmp/perso-retire/repo/../perso/mine.sh" "$(commandes perso-retire Stop)" "perso retiré : hook Stop posé à la 1re passe"
printf '{}\n' >"$tmp/perso-retire/perso/settings.json"
installer perso-retire; verdict 0 "$?" "perso retiré : 2e passe sans erreur"
verdict "(aucune)" "$(commandes perso-retire Stop)" "hooks : celui que le perso ne déclare plus, retiré"

# L'existant porte un hook au chemin du dépôt (<repo>/hooks, cible du lien), qu'aucune couche ne déclare : retiré.
monter hook-depot
socle_hooks hook-depot
cat >"$tmp/hook-depot/home/.claude/settings.json" <<EOF
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "$tmp/hook-depot/repo/hooks/x.py"}]}]}}
EOF
installer hook-depot; verdict 0 "$?" "hook du dépôt : install sans erreur"
verdict "(aucune)" "$(commandes hook-depot Stop)" "hooks : celui au chemin réel du dépôt, retiré"

# Un hook d'un autre outil, posé à la main entre deux passes : conservé aux passes suivantes.
monter etranger-manuel
socle_hooks etranger-manuel
installer etranger-manuel; verdict 0 "$?" "étranger manuel : 1re passe sans erreur"
python3 - "$tmp/etranger-manuel/home/.claude/settings.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
d["hooks"].setdefault("Notification", []).append({"hooks": [{"type": "command", "command": "/opt/tiers/notifier.sh"}]})
json.dump(d, open(sys.argv[1], "w", encoding="utf-8"), indent=2)
PY
installer etranger-manuel; verdict 0 "$?" "étranger manuel : 2e passe sans erreur"
verdict /opt/tiers/notifier.sh "$(commandes etranger-manuel Notification)" "hooks : étranger posé à la main, gardé à la 2e passe"
installer etranger-manuel; verdict 0 "$?" "étranger manuel : 3e passe sans erreur"
verdict /opt/tiers/notifier.sh "$(commandes etranger-manuel Notification)" "hooks : étranger posé à la main, gardé à la 3e passe"

echo "$nb cas, $([ "$echec" -eq 0 ] && echo 'tous passent' || echo 'ECHEC')"
exit "$echec"
