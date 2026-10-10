# claude-config

> 🇫🇷 Une configuration Claude Code de développeur solo, éprouvée au quotidien : des sous-agents
> qui se relaient (`dev` → `tester` → `reviewer`), des gardes qui empêchent les gestes
> irréversibles, et des règles de délégation **mesurées** plutôt que supposées. Windows et macOS,
> installée par liens, avec un dossier perso pour ce qui ne regarde que vous.
>
> 🇬🇧 A solo developer's Claude Code setup, used daily: subagents that hand off to each other
> (`dev` → `tester` → `reviewer`), guards against irreversible actions, and delegation rules that
> were **measured** rather than assumed. Windows and macOS, installed through links, with a
> personal folder for what is yours alone. *The content is written in French.*

## Ce que ça apporte

- **Une chaîne d'agents** — `dev` écrit, `tester` audite et prouve que ses tests tombent sans le
  changement, `reviewer` relit et poste sur la PR, `qa` exerce la fonctionnalité de l'extérieur,
  `ci` rejoue la CI en local avant un push.
- **Des règles de délégation** — `CLAUDE.md` dit quand déléguer et à qui (une question fermée :
  l'agent doit-il écrire ?), qui écrit le code (la session principale jusqu'à deux fichiers, `dev`
  au-delà), combien d'agents tournent à la fois, et ce qu'un brief porte : des extraits plutôt que
  des chemins, une condition d'arrêt, ce que l'agent doit rendre.
- **Des briefs courts** — le style *caveman* (`CAVEMAN.md`) pour tout ce qui va vers un sous-agent
  et en revient, avec ce qui ne se compresse jamais.
- **Des gardes** — `guardrail` coupe les boucles et les commandes destructrices ; un `pre-push`
  global refuse un push direct vers `main` d'un dépôt GitHub, et `garde-push` empêche l'agent de
  le désarmer.
- **Des skills de méthode** — cadrer un projet, challenger un cadrage, déboguer en quatre phases,
  traiter une review, vérifier avant d'annoncer, auditer un dépôt ou le SEO d'une page publique.
- **Des commandes** — `/pr`, `/pr-review`, `/start-ticket`, `/new-ticket`.
- **De la télémétrie** — l'OpenTelemetry natif de Claude Code, plus un collecteur qui rend aux
  sous-agents leur nom. Ce dépôt émet ; la pile qui reçoit et affiche est
  [**home-server-telemetry**](https://github.com/AxiaCoder/home-server-telemetry).

## Inspiration

Ce dépôt doit beaucoup à [**S.C.R.O.O.G.E.**](https://github.com/blegouge/S.C.R.O.O.G.E) —
*Smart Context Reducer & Optimized Observability Governance Engine* —, une pile de télémétrie et
d'optimisation pour IDE assistés par IA. Il en a tiré son inspiration, et une partie de sa pile.

## Démarrer

**Tout ce qui vient d'ailleurs** — installé par claude-config ou supposé présent, version,
source, empreinte, comment le retirer : [`DEPENDANCES.md`](./DEPENDANCES.md).

**Prérequis** : Claude Code, lancé au moins une fois (l'installation s'arrête si `~/.claude`
n'existe pas) ; `git` ; Python 3 (bibliothèque standard seulement). Sous Windows, en plus :
PowerShell 7 (`pwsh`) et Git for Windows, dont le `sh` fait tourner les hooks git.

1. **Cloner là où le dépôt restera.** L'installation lie `~/.claude` à ce dossier : le déplacer
   ensuite casse les liens, jusqu'à la prochaine installation.

   ```bash
   git clone https://github.com/AxiaCoder/claude-config.git ~/dev/claude-config
   cd ~/dev/claude-config
   ```

2. **Installer**, depuis le dossier du dépôt.

   ⚠️ L'installation **remplace** votre `~/.claude/CLAUDE.md` et votre `~/.claude/CAVEMAN.md`,
   et dans `~/.claude/settings.json` les clés que ce dépôt définit — `hooks`, `statusLine`,
   `permissions` : les permissions ajoutées à la main dans `~/.claude/settings.json` sont
   effacées à chaque passe. Les hooks d'autres outils (iTerm2…) sont gardés, ceux ajoutés à la
   main aussi ; seuls disparaissent ceux que le dépôt ou le dossier perso ne déclarent plus. À la première passe, ces trois fichiers sont d'abord copiés dans
   `~/.claude/config-backup-<date>/`. Ce qui doit rester se remet ensuite dans le dossier perso,
   vos permissions comprises : elles s'y **ajoutent** à celles du dépôt, sans en retirer
   aucune. `statusLine`, elle, remplace celle du dépôt.

   ```bash
   bash install.sh                                # macOS / Linux
   bash install.sh --perso ~/notes/claude-perso   # avec un dossier perso
   bash install.sh --dry-run                      # voir ce qui se passerait
   bash install.sh --sans-externes                # sans rien télécharger (garde secrets désactivé)
   ```

   L'installation télécharge **betterleaks**, à la version et au sha256 épinglés dans
   `git-hooks/betterleaks.version`, dans `~/.claude/bin/` — le garde secrets du `pre-commit`
   et du `pre-push` s'en sert. Un sha256 qui diffère ou un réseau absent : betterleaks n'est pas posé, le reste
   de l'installation continue, et la fin le signale. `--sans-externes` (`-SansExternes`) s'en
   passe et est mémorisé ; `--avec-externes` (`-AvecExternes`) le défait.

   ```powershell
   .\install.ps1                                  # Windows
   .\install.ps1 -Perso 'D:\notes\claude-perso'   # avec un dossier perso
   .\install.ps1 -WhatIfOnly                      # voir ce qui se passerait
   ```

3. **Vérifier** — les liens et les hooks, § [Maintenance](#maintenance).

L'installation est idempotente : la relancer après un `git pull` met le poste à jour.

## Le dossier perso

Tout ce qui ne regarde que vous — votre nom, vos adresses de télémétrie, vos préférences
d'interface, vos notes — vit **hors de ce dépôt**, dans un dossier perso que l'installation
reçoit par `--perso` (`-Perso` sous Windows). Elle le mémorise dans
`~/.claude/claude-config.perso` : les passes suivantes le reprennent seules, et supprimer ce
fichier revient à s'en passer. Sans dossier perso, on obtient une config générique complète.

Le dossier peut contenir, chacun facultatif :

| Fichier | Effet |
|---|---|
| `settings.json` | fusionné par-dessus les réglages du dépôt, sur les deux OS — `env` clé par clé, `hooks` et `permissions` ajoutés à ceux du dépôt, les autres clés — `statusLine` comprise — en bloc |
| `settings.macos.json` / `settings.windows.json` | fusionné ensuite, sur cet OS seulement |
| `CLAUDE.md` | inséré dans le `CLAUDE.md` rendu, à la place de `{{PERSO_CLAUDE_MD}}` |
| `CLAUDE.complet.md` | remplace tout le `CLAUDE.md` du dépôt, et fait ignorer le `CLAUDE.md` perso — pour une machine qui n'a que des sessions sans humain, un serveur ou une CI. ⚠️ Les règles du dépôt ne suivent plus : à recopier quand elles changent |

Dans ce `CLAUDE.md` comme dans `CLAUDE.complet.md`, `{{PERSO}}` est remplacé par le chemin du dossier perso, normalisé :
`{{PERSO}}/../notes/USER.md` devient le chemin absolu du `notes/USER.md` voisin.

➡️ Un exemple prêt à copier : [`exemple-perso/`](./exemple-perso/).

## Comment ça marche

`~/.claude` **reste un vrai dossier**. Seuls cinq dossiers y sont montés vers ce dépôt, par
jonction NTFS (Windows) ou lien symbolique (macOS) :

| Cible | Source |
|---|---|
| `~/.claude/agents` | `agents/` |
| `~/.claude/commands` | `commands/` |
| `~/.claude/skills` | `skills/` |
| `~/.claude/hooks` | `hooks/` |
| `~/.claude/git-hooks` | `git-hooks/` — déclaré en `core.hooksPath` global |

L'état d'exécution de Claude Code — `.credentials.json`, `history.jsonl`, `projects/`,
`sessions/`, `settings.local.json` — reste dans `~/.claude` et n'entre jamais dans un arbre de
travail git, où un `git clean -xdf` l'emporterait.

`CLAUDE.md`, `CAVEMAN.md` et `settings.json` ne sont pas liés mais **rendus** : ils portent des
chemins propres à la machine. Éditer `~/.claude/CLAUDE.md` ou `~/.claude/settings.json` à la
main ne sert donc à rien — la prochaine installation les écrase. La source est ici, ou dans le
dossier perso.

**`settings.json`** naît de quatre couches, chacune l'emportant sur la précédente, `env` fusionné
clé par clé :

1. `settings.base.json` — commun aux deux OS ;
2. `settings.macos.json` ou `settings.windows.json` — les commandes de hooks diffèrent (`.sh`
   contre `.ps1`, `python3` contre l'interpréteur trouvé sous Windows) ;
3. `<perso>/settings.json` ;
4. `<perso>/settings.<os>.json`.

`hooks` et `permissions` s'additionnent au lieu de se remplacer :

- `hooks` — par événement, les blocs des couches mis bout à bout dans l'ordre ; un bloc
  identique à un bloc déjà présent n'est pas ajouté une deuxième fois ;
- `permissions` — chaque liste (`allow`, `deny`, `ask`, `additionalDirectories`…) est l'union
  des couches, dans l'ordre de première apparition ; une valeur seule (`defaultMode`) revient à
  la dernière couche qui la pose.

La fusion repart du `settings.json` existant : les clés que Claude Code écrit lui-même et que ce
dépôt ne gère pas sont conservées. Sauf `hooks` et `permissions`, rebâtis à chaque passe à partir
des couches : un hook retiré du dépôt ou du dossier perso disparaît du fichier rendu. Des hooks
existants, ceux d'autres outils — iTerm2… — sont conservés, après ceux des couches. L'installation
mémorise les hooks qu'elle rend dans `~/.claude/claude-config.hooks.json` pour les reconnaître à
la passe suivante : est à nous un hook qui y figure, ou dont la commande désigne un fichier sous
`~/.claude/hooks` ou sous `hooks/` du dépôt ; tout autre est gardé.
⚠️ Un script à vous ne se range donc pas dans `~/.claude/hooks` : c'est un lien vers ce dépôt,
et son hook y serait pris pour un hook du dépôt, effacé s'il n'y est pas déclaré. Le ranger
ailleurs — dans le dossier perso, par exemple.
L'état d'avant la passe est copié en `settings.json.prev`.

| Marqueur | Remplacé par |
|---|---|
| `{{CLAUDE_HOME}}` | le chemin de `~/.claude` |
| `{{REPO}}` | le chemin de ce dépôt, ouvert à Claude Code par `permissions.additionalDirectories` |
| `{{PYTHON}}` | sous Windows : l'interpréteur trouvé par `py -3`, sinon `python` |
| `{{MODS}}` | chaque `mods/*/` qui porte un `.claude-plugin/plugin.json`, triés, joints par `;` (Windows) ou `:` (macOS). Sans mod, la clé qui le porte est retirée de `env` |
| `{{PERSO_CLAUDE_MD}}` | le `CLAUDE.md` du dossier perso, ou rien |
| `{{PERSO}}` | dans le `CLAUDE.md` ou le `CLAUDE.complet.md` perso : le chemin du dossier perso |

Un marqueur qui survit au rendu arrête l'installation avant d'écrire le fichier.

## Les hooks

### Hooks Claude Code

| Hook | Quand | Ce qu'il fait |
|---|---|---|
| `guardrail` | avant `Bash`, `Edit`, `MultiEdit`, `NotebookEdit`, `Write` — et `PowerShell` sous Windows | coupe les boucles (même appel répété) et les commandes destructrices passées par `Bash` — pas encore par l'outil PowerShell ; refuse qu'un agent ajoute une exemption de secret |
| `garde-push` | avant `Bash` — et `PowerShell` sous Windows | refuse une commande qui citerait de quoi désarmer le `pre-push` |
| `session-git-context` | au démarrage | affiche la branche, le dernier commit et l'état de l'arbre |
| `post-write-lint` | après `Write`, `Edit` | lance `pnpm lint` — sur un projet AdonisJS seulement |
| `collecteur-agents` | au démarrage, à la fin d'un sous-agent | pousse les métriques par sous-agent ; sans adresse configurée, il s'abstient sans faire échouer la session |
| `statusline` | en continu | modèle, dossier, branche, contexte, quotas |

La télémétrie demande une instance VictoriaMetrics et son adresse dans le dossier perso
(`TELEMETRIE_ENDPOINTS`, `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`) — VictoriaMetrics, Grafana et
les dashboards qui lisent ces métriques sont dans
[home-server-telemetry](https://github.com/AxiaCoder/home-server-telemetry). Déclarer un hook,
le vérifier, et ce dont chacun a besoin → [`HOOKS.md`](./HOOKS.md).

### Hooks git globaux

L'installation déclare `~/.claude/git-hooks` en `core.hooksPath` **global**. Git ne cumule
jamais deux dossiers de hooks : tant que ce réglage vaut, `.git/hooks/` de chaque dépôt n'est
plus lu. D'où le **relais** — chaque hook client de `git-hooks/` lance le hook du même nom
dans `.git/hooks/` du dépôt, s'il existe et est exécutable, avec les mêmes arguments et la
même entrée. Un `pre-commit` ou un `commit-msg` local continue donc de tourner.

| Hook | Ce qu'il fait |
|---|---|
| `pre-push` | refuse un push vers `main` ou `master` d'un remote GitHub, porteur d'un marqueur personnel vers un dépôt GitHub public, ou dont un commit porte un secret (garde secrets), puis relaie |
| `pre-commit` | refuse un commit dont l'indexé porte un secret (garde secrets), puis relaie |
| `applypatch-msg`, `pre-applypatch`, `post-applypatch`, `pre-merge-commit`, `prepare-commit-msg`, `commit-msg`, `post-commit`, `pre-rebase`, `post-checkout`, `post-merge`, `post-rewrite`, `pre-auto-gc`, `sendemail-validate` | relaient seulement (`git-hooks/_relais`) |

Ne sont **pas** relayés : `reference-transaction` et `post-index-change`, que git lance à
chaque mise à jour de ref ou d'index — un relais coûte une quinzaine de millisecondes par
appel ; `fsmonitor-watchman`, les hooks `p4-*` de `git p4` et les hooks serveur.

**Le garde de push.** Il ne vise que les remotes **GitHub** : vers un autre remote, le push
direct sur `main` passe. Pour le lever :

```bash
ALLOW_PUSH_MAIN=1 git push …                 # une fois
git config --local garde.pushMain off        # pour ce dépôt, durablement
git config --local --unset garde.pushMain    # le rétablir
```

Ces gestes sont réservés à l'utilisateur : le hook Claude `garde-push` refuse qu'un agent
lance une commande qui les cite, ou qui cite `core.hooksPath`. Il lit le texte de la
commande : un outil qui pose ce réglage sans le nommer (`npx husky init`) passe.

**Le garde données personnelles** (`git-hooks/_garde-public`, lancé par `pre-push`). Vers un
dépôt GitHub **public**, il refuse un push dont le contenu porte un marqueur personnel, et
liste pour chacun le marqueur, le `fichier:ligne` ou le commit, et un extrait.

- **Les marqueurs** vivent hors du dépôt, dans le fichier que désigne la variable
  d'environnement `GARDE_PUBLIC_MARQUEURS` — typiquement dans le dossier perso. Un motif par
  ligne, en expression régulière étendue (`grep -E`), **casse ignorée pour les lettres ASCII
  seulement** — la comparaison se fait octet par octet : un marqueur accentué s'écrit en motif
  tolérant, `[Éé]lise` ; lignes vides et lignes qui commencent par `#` ignorées. Un point vaut « n'importe quel caractère » :
  `192\.0\.2\.10` pour une adresse exacte. Vers un dépôt public, un motif que `grep -E` refuse
  **bloque** le push, avec le motif sur stderr : un garde qui l'ignorerait se croirait actif.
- **Ce qui est examiné**, pour chaque ref poussée : chaque commit qui part, un par un — ceux
  que le remote n'a pas encore ; pour une nouvelle branche, ceux qui suivent la merge-base avec
  la branche par défaut du remote. Dans chacun, les lignes **ajoutées**, fichiers binaires
  compris, et les **noms** des fichiers ajoutés ou renommés ; puis son message, son **auteur**
  et son **committer** (nom et e-mail) ; pour un tag annoté, son message et son tagger. Une ligne supprimée ne compte pas.
- **GitHub ou non** : l'hôte `github.com` ou `ssh.github.com`, ou un alias SSH
  (`git@github-perso:owner/repo`) que `ssh -G` résout vers l'un des deux — `ssh.github.com`
  est l'accès SSH par le port 443.
- **Public ou non** : l'API GitHub **sans authentification**
  (`https://api.github.com/repos/<owner/repo>`) — un dépôt public y est toujours visible,
  quel que soit le jeton de `gh`. 200 : public ; 404 : privé ou inexistant ; toute autre
  réponse : repli sur `gh repo view`. Seul « public » est gardé 24 h, dans
  `${XDG_CACHE_HOME:-~/.cache}/claude-config/garde-public/` ; un dépôt privé est re-vérifié à
  chaque push, et un dépôt passé public est examiné dès le push suivant.
- **Il bloque quand la visibilité reste inconnue** — API et `gh` en échec, hors réseau par
  exemple : un push vers GitHub sans réseau échouerait de toute façon.
- **Il laisse passer, avec une ligne sur stderr**, quand la variable est absente ou le fichier
  illisible : le garde n'a alors pas tourné.
- **Ce qu'il ne couvre pas** : le corps et le titre d'une PR ou d'une issue créées par `gh`,
  les commentaires, tout ce qui part sans `git push`.

```bash
ALLOW_PUSH_PERSONAL=1 git push …             # une fois, en connaissance de cause
```

Ce geste, comme vider ou retirer `GARDE_PUBLIC_MARQUEURS`, est réservé à l'utilisateur : le
hook Claude `garde-push` refuse une commande d'agent qui cite l'une ou l'autre variable.

**Le garde secrets** (`git-hooks/_garde-secrets`, lancé par `pre-commit` et par `pre-push`,
avant le relais). Il passe à betterleaks (`~/.claude/bin/betterleaks`, version épinglée — voir
[`DEPENDANCES.md`](./DEPENDANCES.md)) ce qui est indexé au `pre-commit`, et chaque commit qui
part au `pre-push`, vers tout remote. Il refuse si un secret s'y trouve, en listant
`fichier:ligne` et la règle — plus le commit au `pre-push` —, jamais le secret.

- **Pourquoi aussi au `pre-push`** : git crée des commits sans passer par le `pre-commit` —
  `rebase --continue` après un conflit ou un arrêt `edit`, `cherry-pick`, `commit-tree`,
  `commit --no-verify`. Le `pre-push` les rattrape avant qu'ils quittent la machine. Commits
  examinés par ref poussée : depuis ce que le remote a déjà ; nouvelle branche, depuis la
  merge-base avec la branche par défaut du remote, à défaut ceux que ce remote n'a pas — tout
  l'historique vers une URL sans nom de remote. Un merge est examiné sur ce que sa résolution
  ajoute (git ≥ 2.36 ; en deçà, les merges ne sont pas examinés et une ligne le signale). Un
  secret ajouté puis retiré est trouvé : il faut réécrire l'historique, un commit correctif ne
  suffit pas.

- **Aucun appel réseau** : la validation des secrets auprès des API est coupée
  (`--validation=false`).
- **Un faux positif s'exempte** par un commentaire `gitleaks:allow` sur la ligne. Ce
  commentaire est réservé à l'utilisateur : `guardrail.py` et `garde-push.py` refusent qu'un
  agent l'écrive.
- **Il bloque** quand betterleaks est absent, avec le geste pour le reposer — relancer
  l'installation — ou quand son analyse échoue.
- **Il laisse passer** hors dépôt, sans rien d'indexé ni de commit à pousser, et — avec une
  ligne sur stderr — quand l'installation a été faite avec `--sans-externes`.

```bash
ALLOW_COMMIT_SECRET=1 git commit …           # une fois, en connaissance de cause
ALLOW_COMMIT_SECRET=1 git push …             # idem, au pre-push
```

Ce contournement est réservé à l'utilisateur : le hook Claude `garde-push` refuse une commande
d'agent qui le cite.

**Un dépôt peut reprendre la main.** `core.hooksPath` suit la hiérarchie normale de git : une
valeur posée dans le dépôt (`git config --local core.hooksPath <dossier>`) remplace la
globale, et ni le relais ni le garde de push n'y jouent plus. C'est ce que fait **Husky**
(`.husky/`) : ses hooks tournent, le garde de push ne s'y applique pas. Le framework
`pre-commit` refuse de s'installer tant qu'un `core.hooksPath` est posé ; ses hooks
installés à la main dans `.git/hooks/` sont, eux, relayés.

⚠️ Ne pas lier **un seul** hook de `.git/hooks/` vers un stub de `git-hooks/` : le stub y
chercherait `_relais` à côté de lui, ne le trouverait pas, et ferait échouer le hook. Lier
le dossier `.git/hooks` entier fonctionne — le relais se reconnaît et s'arrête.

Si un autre dossier est déjà déclaré en `core.hooksPath` global, l'installation avertit et
n'y touche pas : le garde de push et le relais ne sont alors pas actifs.

## Adapter à un projet

Une commande ou un skill porte le cas général ; un projet le complète par un fichier
`.claude/surcharges/<nom>.md`, que la commande lit en premier. La surcharge complète la base,
et la remplace là où elles se contredisent. Le permanent d'un projet — coordonnées Jira, format
des branches — reste dans son `CLAUDE.md`.

Lisent une surcharge : `/start-ticket`, `/new-ticket`, `/pr-review`,
`verifier-avant-d-annoncer` et `audit-seo` — qui lit aussi les pages publiques que le
`CLAUDE.md` du projet déclare.

⛔ Un projet ne redéclare pas une commande ou un skill sous le même nom : à nom égal, la version
globale gagne et celle du projet est ignorée sans bruit.

## Maintenance

**Vérifier les liens.** Un lien cassé, ou remplacé par un vrai dossier, ne produit **aucune
erreur** : la configuration disparaît simplement. Au moindre doute :

```bash
ls -l ~/.claude | grep -E 'agents|commands|skills|hooks'      # macOS
git config --global --get core.hooksPath
```

```powershell
Get-Item ~\.claude\agents, ~\.claude\commands, ~\.claude\skills, ~\.claude\hooks,
  ~\.claude\git-hooks | Select-Object Name, LinkType, Target      # Windows : <JONCTION>
```

Un lien manque → relancer l'installation.

**Vérifier les hooks** après chaque fusion qui y touche → [`HOOKS.md`](./HOOKS.md), § La
vérification.

**Les tests** :

```bash
sh scripts/install.test.sh        # fusion des réglages, rendu de CLAUDE.md
sh git-hooks/relais.test.sh       # relais des hooks git
sh git-hooks/pre-push.test.sh     # garde de push
sh git-hooks/garde-public.test.sh # garde données personnelles
sh git-hooks/garde-secrets.test.sh # garde secrets ; essai réel avec ~/.claude/bin/betterleaks
python3 hooks/guardrail.test.py
python3 hooks/garde-push.test.py
python3 scripts/verifier-les-ecrits.py .   # renvois morts et notes en double dans les .md
```

**Désinstaller.**

1. Retirer les cinq liens — le lien seulement, jamais son contenu :
   `rm ~/.claude/{agents,commands,skills,hooks,git-hooks}` sous macOS ;
   `cmd /c rmdir %USERPROFILE%\.claude\agents` (et les quatre autres) sous Windows.
2. Retirer le dossier de hooks git : `git config --global --unset core.hooksPath`.
3. **Restaurer, ou retirer, les fichiers rendus.** La première installation a copié vos
   `CLAUDE.md`, `CAVEMAN.md` et `settings.json` d'origine dans le **plus ancien**
   `~/.claude/config-backup-<date>/` — avec les vrais dossiers qu'un lien a remplacés : les
   remettre en place. Un fichier absent de la sauvegarde n'existait pas avant : le supprimer.
   ⚠️ Ne pas garder le `settings.json` rendu : ses hooks pointeraient vers `~/.claude/hooks/`,
   qui n'existe plus, et échoueraient à chaque appel d'outil. `settings.json.prev` n'aide pas —
   il ne garde que l'état d'avant la dernière passe.
4. Supprimer `~/.claude/bin/betterleaks` (Windows : `betterleaks.exe`),
   `~/.claude/claude-config.sans-externes`,
   `~/.claude/claude-config.perso`, `~/.claude/claude-config.hooks.json`,
   `~/.claude/settings.json.prev`, puis les
   `~/.claude/config-backup-*` une fois leur contenu remis en place.

## Ce qui n'entre jamais dans le dépôt

Le `.gitignore` est un *deny-all* : rien n'est versionné sans figurer dans sa liste
d'exceptions. Cette forme est délibérée — elle protège des fichiers qui n'existent pas encore.

Ne jamais committer : `.claude.json` (il contient les jetons MCP en clair),
`.credentials.json`, `history.jsonl`, `settings.local.json`.

## Inventaire

| Dossier | Contenu |
|---|---|
| `agents/` | Sous-agents : `dev`, `tester`, `reviewer`, `qa`, `ci` |
| `commands/` | Commandes globales : `/pr`, `/pr-review`, `/start-ticket`, `/new-ticket` |
| `skills/` | Skills globaux |
| `hooks/` | Hooks Claude Code et statusline |
| `mods/` | Mods Claude Code : chaque sous-dossier qui a un `.claude-plugin/plugin.json` est chargé par l'installation, et porte sa propre règle. Retirer un mod = supprimer son dossier, puis relancer l'installation |
| `git-hooks/` | Hooks git globaux : garde de push, garde secrets et relais ; version épinglée de betterleaks |
| `scripts/` | Outils de maintenance et tests de l'installation |
| `exemple-perso/` | Un dossier perso d'exemple |

`CAVEMAN.md` définit le format de sortie que tous les agents reprennent, et `CLAUDE.md`
l'importe pour les briefs du parent — le supprimer laisserait chaque agent pointer vers
un fichier absent.

## Licence

[MIT](./LICENSE).
