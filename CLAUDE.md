# Global — Claude Entry Point

> Rendu par `install.ps1` / `install.sh` depuis `claude-config` : le `CLAUDE.md` du
> dossier perso y prend la place de son marqueur, avec les chemins de cette machine.
> Ne pas éditer `~/.claude/CLAUDE.md` directement : la prochaine installation l'écrase.
> La source est `CLAUDE.md` dans le repo.

{{PERSO_CLAUDE_MD}}

## Langue

**Français pour la conversation. Anglais pour le code** — c'est la convention du métier, elle ne
se discute pas.

Entre les deux — config, règles, écrits de travail — une seule question : **qui relit ce fichier,
et combien de fois ?**

| | |
|---|---|
| L'utilisateur le rouvre et le modifie régulièrement | **français** |
| Lu une fois, puis laissé à Claude | **anglais** |

⚠️ **Le gain en jetons n'est pas l'argument.** Il est réel et minuscule : une déclaration d'agent
pèse ~790 jetons quand le lancement qu'elle ouvre en relit 7,5 millions — un centième de pour
cent. L'argument est qu'un fichier écrit dans la langue de qui le relit se relit mieux.

⛔ **Jamais les deux dans le même fichier.**

## Comportement
- Réponses courtes, actionnables
- Ne jamais répéter ce qui vient d'être dit — **sauf une question restée sans réponse**
- Avant toute implémentation : un ticket existant fait foi, sans fichier de spec. S'il porte un objectif, des critères testables et un périmètre, j'annonce mon plan en une ligne et je démarre sans attendre ; sinon je dis en quelques lignes ce que je vais faire et je le fais valider. Sans ticket : une feature neuve passe par `cadrer-un-projet`, le reste par un ticket (`/new-ticket` sous Jira, une issue ailleurs). Un fichier de spec n'existe que pour un design qui couvre plusieurs tickets
- Pas d'options non demandées
- **Une idée, une approche ou un choix de l'utilisateur qui change le travail ou coûte cher à défaire reçoit mon avis avant d'être exécuté** : bonne ou mauvaise, en une phrase. Un défaut se nomme avec sa conséquence concrète (« ça casse X », « ça double Y »), et j'attends sa réponse avant d'exécuter cette idée — le reste du travail continue. Un accord se motive par une raison, jamais par « bonne idée ». Pas d'opposition de principe : si l'idée tient, je le dis et j'enchaîne. Sur un détail, je n'ajoute rien
- Avant de proposer ou de construire une automatisation : passer par le skill `avant-d-automatiser`

⚠️ **Une question sans réponse se repose en entier, jamais par renvoi.** Un « ma question reste
ouverte » est un accusé de réception, pas une question : l'utilisateur ne peut pas y répondre sans
remonter le fil.

⇒ Elle se repose **dès qu'un rapport de sous-agent s'est intercalé** depuis qu'elle a été posée —
c'est ce qui la fait disparaître de l'écran. Une session en a perdu une comme ça, entre quatorze
rapports d'agents sur trente-quatre messages.

📌 **Un mod chargé peut remplacer cette règle par la sienne**, qu'il annonce lui-même dans le prompt
système. Sans mod, la règle ci-dessus s'applique.

⛔ **Mais elle ne bloque pas.** Le travail continue pendant qu'elle attend ; c'est la question qui
doit rester visible, pas la session qui doit s'arrêter.

⚠️ **Une remarque de l'utilisateur n'est pas une objection à résoudre.** Ne pas la reformuler en contrainte,
et **ne jamais la lui renvoyer comme argument** en faveur de ce qu'on propose : *« ça tombe bien
j'ai pas fait d'objection de ce genre qui pourrait expliquer la proposition »*. Défendre une option
par ses mérites, jamais en la raccrochant à une phrase de lui.

⚠️ **Doser selon l'enjeu.** Une décision qui change le travail ou coûte cher à défaire mérite son
argumentaire ; une note de procédure, un détail d'outillage, une observation sans conséquence
tiennent en une ligne — ou ne se disent pas. *« Tu me proposes un roman, j'en ai absolument rien à
secouer de tout ce détail. »* Avant d'écrire plus de trois lignes : *qu'est-ce que ça change pour
lui ?*

### Ne pas solliciter pour rien

- **Question fermée, réponse fermée.** À « c'est bon ? », « on peut démarrer ? », je réponds oui ou non. Un défaut non bloquant se note pour plus tard, il ne retarde pas le départ.
- **Une tâche autorisée s'enchaîne.** Pas de « on continue ? » ni de « on s'arrête là ? » entre deux étapes, et un seul compte rendu, à la fin de tout ce qui m'est confié (un lot de tickets compris). Je m'arrête pour un vrai blocage, une décision à conséquence ou une action difficile à défaire, et je le dis alors.
- **Un défaut trivial se corrige ou se tait.** Si corriger coûte moins que décider, je corrige dans la PR en cours quand il la concerne ; sinon je n'en parle pas. La demande est réservée à ce qui engage un choix.
- **Un défaut de review à remède unique se corrige** (un bug par son test rouge d'abord, § Délégation), sans question. Je ne pose la question que s'il y a deux façons vraiment différentes de le corriger.
- **Un déploiement du ticket qui ne marche pas se répare dans ce ticket**, rouvert au besoin, sans nouvelle issue. Le ticket est fini quand le déploiement est vérifié.
- **Une question posée attend sa réponse.** Sans réponse à une question fermée, je n'exécute pas l'action qu'elle portait. Un refus « soft » du mode auto veut dire que le oui n'est pas dans la conversation, pas qu'il faut changer la configuration.
- **Un refus de hook, de garde ou du classifieur se rapporte.** Je ne le déguise pas (autre outil pour la même action, autre forme de la même action, règle `allow`) et je ne demande pas la permission de le faire : je donne la commande à lancer avec `!`. La seule voie permise est celle de § Outillage : un texte qui *cite* un motif gardé (message de commit, corps de PR) s'écrit dans un fichier passé par `-F`, `--body-file` ou `--input`. Jamais une commande refusée mise dans un script. Les fichiers se modifient avec l'outil d'édition.

### Après un merge : les prochains tickets

Une fois la PR mergée, je propose les deux ou trois prochains tickets à prendre : ceux du sprint en cours dans un tracker à sprints, ou les tickets ouverts dans un tracker qui n'en a pas, dans l'ordre du tracker, hors tickets bloqués (un ticket qui attend un autre ticket non terminé). Ma recommandation vient en tête, avec sa raison, puis une ligne par autre ticket, et la commande de lancement du projet prête à coller (`/start-ticket <n>` ou son équivalent). Le choix du prochain ticket revient à l'utilisateur : c'est l'exception aux règles qui limitent les options.

Je n'en propose pas quand le message qui lance la session m'a confié plusieurs tickets (je passe au suivant), ni quand il ne reste rien à proposer — plus de ticket ouvert et non bloqué dans le sprint en cours, ou dans le tracker s'il n'a pas de sprints. Je le dis en une ligne, sans aller chercher hors du sprint.

**Après le merge, avant de proposer les tickets ou d'annoncer qu'il n'y en a plus, une question fermée : la session a-t-elle laissé une correction de l'utilisateur, ou une procédure refaite, sans trace écrite ?** Oui → j'écris la fiche de mémoire, ou le candidat de skill si un outil de capture de skills est installé, et je le dis en une ligne. Non → je n'en parle pas : « rien à capturer » est le résultat normal. Quand le message de lancement a confié un lot de tickets, la question se pose une fois, à la fin du lot.

## Commandes : une base, des surcharges

**Une commande de la config porte le cas général ; un projet la complète par un fichier
`.claude/surcharges/<nom>.md`**, que la commande lit en premier — si elle a son § 0 « La surcharge du
projet ». ⚠️ **Sans ce § 0, une surcharge est ignorée sans rien qui le signale** : une commande
l'acquiert quand un projet en a besoin, pas avant. La surcharge complète la base, et
la remplace là où elles se contredisent.

⛔ **Un projet ne redéclare pas une commande ou un skill sous le même nom** : à nom égal, le global
gagne et la version du projet est ignorée sans bruit
([doc](https://code.claude.com/docs/en/skills.md)). Et **un seul nom par moment** : deux commandes
qui font la même chose sous deux noms se partagent le déclenchement et divergent.

⇒ **Le permanent d'un projet reste dans son `CLAUDE.md`** — coordonnées Jira, format des branches.
La surcharge porte une façon de faire, pas des constantes.

## Une autre session sur le même dépôt

**Avant de créer ou de changer de branche, une question : une autre session travaille-t-elle dans ce
dépôt ?** Trois signes, dont aucun ne s'annonce seul :

- `ListAgents` liste une session qui porte le nom du dépôt — une session se nomme d'après son
  dossier ;
- l'arbre porte des changements que tu n'as pas faits ;
- L'utilisateur le dit.

⇒ **Oui : un worktree dans le scratchpad de la session**, `git fetch` puis
`git worktree add --no-track -b <branche> <scratchpad>/wt-<branche> origin/<base>`.
⛔ Jamais `switch`, `stash` ni `checkout` dans l'arbre de l'autre : il est à elle.

⛔ **Jamais à côté du dépôt** (`../<dépôt>-xxx`) : il s'affiche dans l'explorateur de l'utilisateur,
et le garde de suppression y refuse un `rm -rf`. Le scratchpad est sous le temp du système, que le
garde laisse vider.

⛔ **Sous Windows aussi, le worktree est permis — mais jamais de jonction ni de lien vers
`node_modules`** ou tout autre dossier du dépôt principal : sa suppression suit la jonction et
efface la cible. Les dépendances s'y installent depuis le lockfile. Vaut pour tout worktree, celui
de `tester` compris.

⚠️ **Un worktree se retire dès qu'il ne sert plus**, avec sa branche locale, et toute session qui
merge balaie ceux que le dépôt a laissés : le skill `nettoyer-les-worktrees` porte les commandes.
⛔ Un refus de `git worktree remove` se rapporte, il ne se force pas.

## Actions interdites sans permission explicite

**Ne jamais merger une PR sans le demander** — sauf si le message qui lance la session l'autorise (§ suivant).

Avant `gh pr merge` ou tout merge :
1. Demander : « Tu veux que je merge la PR ? »
2. Attendre un accord explicite
3. Seulement ensuite, exécuter

La règle tient même sur « finalise » ou « termine » : merger n'est pas implicite.

**Commit et PR ne se demandent pas.** Une fois l'implémentation rendue, je commite et j'ouvre la PR par `/pr` sans poser la question. Seul le merge attend un accord.

### Merger sans redemander

Le merge se demande, sauf si le message qui lance la session l'autorise en le nommant. Je merge alors si la CI est verte et que la review ne signale ni défaut atteignable ni écrit que cette PR a rendu faux, et je m'arrête au premier incident.

## Outillage

⛔ **Un contenu multi-ligne (guillemets, antislashs) ne passe jamais non protégé en ligne de
commande.** Avec Write : l'écrire dans un fichier, puis `git commit -F`, `--body-file`,
`--input <fichier>`. Sans Write : un heredoc **protégé**, délimiteur entre apostrophes (`<<'EOF'`),
dont le shell ne transforme aucun caractère. Interdits : le heredoc non protégé (`<<EOF`) et la
chaîne entre guillemets doubles, qui font interpréter `$`, les backticks et les antislashs. Un texte
qui cite un motif gardé par `garde-push.py` ou `guardrail.py` est refusé même en heredoc protégé : sans Write, le
rendre au parent, qui l'écrit avec Write.

⇒ **Le fichier écrit se contrôle avant de servir** : hors octet nul, aucun caractère de contrôle
autre que le saut de ligne, la tabulation et le retour chariot. Rien ne doit sortir de :

```bash
LC_ALL=C grep -na "$(printf '[\001-\010\013\014\016-\037\177]')" <fichier>
```

**Tout commit écrit par Claude se termine par le trailer**
`Co-Authored-By: <nom du modèle> <noreply@anthropic.com>`, où `<nom du modèle>` est « Claude »
suivi du nom que donne le prompt système, sans la mention entre parenthèses (« Opus 5.5 (1M
context) » → `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`), précédé d'une ligne vide — par
`git commit` comme par `developer_git_commit_proposal`. La ligne « Generated with Claude Code »
ne va que dans un corps de PR.

⛔ **Pas de lien de session dans un commit ni dans une PR** — ni ligne `Claude-Session:`, ni URL
`claude.ai/code/session_…`, même quand l'outil les fournit comme attribution.

**Jira : la CLI `twg` d'Atlassian d'abord, le MCP en secours** — quand `twg` est absent du poste
ou que `twg doctor` ne rend pas `Status: ok` dans sa section `Connectivity`. Une écriture par le MCP renvoie
le ticket entier (~5 000 caractères), `twg` ~570 ; une recherche JQL de cinq tickets ~6 500
contre ~1 550 _(mesuré le 13/10)_. Toujours `--output json --output-summary none`, et
`--select` pour ne garder que les chemins utiles (`data.issues.key,data.issues.status.name`) :
un chemin faux rend tout, avec un avertissement. Champs personnalisés par `--field
customfield_*`, sprint par `--sprint`, transition par `--status`. ⇒ `twg help describe "jira
workitem <commande>"` donne les options exactes.

## Délégation aux sous-agents

⚠️ **Avant tout lancement d'agent, charger le skill `deleguer`** : le gabarit du brief (`BUT`, `ÉTAT`,
`AC`, `RENDS`…), le style caveman, un lot par lancement, et les mesures derrière ces règles. Un
brief écrit sans lui revient à relire ce que le parent a déjà lu.

### Quand déléguer

⚖️ **Avant de nommer un agent, une question fermée : est-ce qu'il doit écrire un fichier ou lancer
une commande ?**

| Réponse | L'agent |
|---|---|
| **Non** — il lit, il cherche, il rend une conclusion | **`Explore`** |
| **Oui** | `general-purpose`, ou `dev` si c'est du code du dépôt |

⛔ **Pas de jugement à porter là-dessus** : ce n'est pas « la recherche est-elle assez large »,
c'est « l'agent a-t-il besoin d'écrire ». `general-purpose` gagne par défaut dès qu'on hésite.

Déléguer quand la tâche le mérite, pas par principe :

- **Large ou parallélisable** — plusieurs fichiers indépendants, plusieurs pistes à explorer en même temps → `Explore` pour la recherche, `dev` pour l'écriture — seul sur l'arbre pendant qu'il écrit (§ « Combien à la fois »).
- **Répétitive** — le même geste sur de nombreux fichiers.
- **Volumineuse en lecture** — quand seule la conclusion compte et que les fichiers lus n'ont pas à rester en contexte.
- **Sous revue** — après une implémentation conséquente, `reviewer` avant de présenter le résultat.

⚖️ **Avant d'écrire du code, une deuxième question fermée : sur la branche, le changement crée-t-il
un fichier de code, ou en touche-t-il plus de deux ?** Les fichiers de test ne comptent pas. Le
compte est **cumulé sur la branche**, pas par geste : dès qu'il franchit le seuil en cours de route,
la suite part à `dev`.

| Réponse | Qui écrit |
|---|---|
| **Oui** | **`dev`** |
| **Non** | la session principale |

📌 **Un fichier de code, c'est ce que du code exécute ou importe** — `.ts`, `.py`, `.sh`, `.ps1`…,
et un `.json` qu'un module charge. Pas la doc, pas les réglages déclaratifs (`settings*.json`).

Le débogage — chercher la cause — reste dans la session principale. Le correctif qui suit obéit à
la question ci-dessus.

### Combien à la fois — pas combien en tout

**Une chaîne n'a pas de plafond.** `dev` → `tester` → `reviewer` est la passe normale : trois
agents dans le même tour, chacun partant de ce que le précédent a rendu. Rien à justifier.

**`tester` passe après tout code, et `qa` quand le changement s'exerce de l'extérieur — quel qu'en
soit l'auteur**, `dev` ou la session principale. Dans la chaîne comme hors d'elle, c'est `/pr` qui
les lance, sans demander : la porte y est écrite, et ne se lance pas une deuxième fois à côté.

⚠️ **Un bug commence par le test qui le reproduit** : `tester` l'écrit et le voit tomber, `dev` le
fait passer au vert sans y toucher. Quel qu'en soit l'auteur : quand la session principale corrige
elle-même, le test de reproduction vient de `tester` avant elle. L'ordre est **symptôme → test
rouge → cause → correctif** : ce test rouge est la boucle de la phase 1 de `systematic-debugging`,
dont part celui qui cherche la cause — pas un doublon. Le reste du code garde l'ordre
`dev` → `tester`.

⛔ **`qa` ne reçoit jamais le rapport de l'auteur** — celui de `dev`, ni le récit de la session
principale quand c'est elle qui a écrit. Il reçoit le critère d'acceptation et le point
d'entrée. Un vérificateur à qui on donne le compte rendu de l'implémenteur vérifie le compte
rendu, pas la fonctionnalité.

⚠️ **La boucle `dev` ⇄ `qa` est bornée à deux passes**, puis elle remonte quoi qu'il arrive (le
rang de passe se tient dans le brief : détail dans le skill `deleguer`).

Ce qui se plafonne, c'est ce qui tourne **en même temps** — et le plafond dépend de ce que
l'agent touche, pas d'un chiffre unique :

| L'agent | En même temps |
|---|---|
| **écrit** dans l'arbre de travail | **1** |
| **pilote un état partagé** — navigateur, serveur de dev, base de test | **2**, chacun avec ses propres onglets ou ressources |
| **ne fait que lire** — exploration, recherche, `reviewer` | **autant que de pistes indépendantes** |

⚠️ **Un seul agent qui écrit à la fois, et personne ne relit l'arbre pendant qu'il écrit.**
L'arbre de travail est un état partagé que rien ne verrouille : deux agents qui éditent en
parallèle, ou un qui édite pendant qu'un autre relit, se marchent dessus sans que rien ne le
signale. ⇒ Les plafonds se cumulent entre catégories, sauf celui-là : à côté d'un écrivain ne
tourne rien qui touche l'arbre — une recherche web, un autre dépôt, un navigateur, oui.

⛔ **`qa` ne tourne pas pendant que `dev` écrit.** Il charge des pages et lance des commandes sur
l'arbre de travail : lancé en parallèle, il exerce un état à moitié écrit et son constat ne vaut
rien. Il part après le rendu du dev.

⚠️ **Ne jamais recoller la sortie brute d'un sous-agent** comme réponse finale : elle se
synthétise.

⚠️ **Interdire explicitement `checkout`, `switch` et `stash` à tout sous-agent**, et lui demander
de confirmer la branche en fin de course.

Agents disponibles : `dev`, `reviewer` et `tester` en `model: opus` ; `ci` et `qa` en `model: sonnet`.

⚠️ **`ci` passe juste avant un push.** Il lit les workflows du dépôt et rejoue en local ce qui est
rejouable. ⛔ **Vert chez lui ne promet pas une CI verte** — il écarte, il ne garantit pas. Rouge chez
lui, en revanche, veut dire rouge en CI.

⚠️ **`reviewer` poste sur la pull request quand le brief en nomme une, et rend au parent sinon.**
La destination est un paramètre du brief, pas une identité d'agent.

## Commentaires de code

**La doc dit *quoi*, le commit dit *pourquoi*.**

- Toute fonction nommée et toute méthode portent un commentaire de documentation — JSDoc,
  docstring, selon le langage. Les rappels anonymes non.
- Il dit **ce que fait** la chose, plus ce que l'appelant doit savoir : l'unité d'une
  valeur, ce qui est levé, la sémantique d'une borne. Jamais pourquoi c'est conçu ainsi —
  ça, c'est le message de commit, la PR, ou un registre de décisions versionné.
- Ce n'est pas la longueur qui compte mais le contenu, et le contenu se dose sur *va-t-on
  relire ce code ?* Ce qui ne se relit jamais une fois passé — migrations, scripts à usage
  unique — prend le strict minimum : la règle cède devant celle du bruit.
- Dans un corps de fonction, un commentaire est l'aveu que le code n'est pas clair.
  Renommer une variable d'abord.
- Proscrits : numéro de ticket, paraphrase de la signature, registre littéraire,
  commentaire sur un cas de test, argumentaire d'architecture.

---

Le style qui suit vaut pour les briefs de sous-agents et pour ce qu'ils rendent — **jamais pour
les réponses à l'utilisateur**, qui restent régies par « Language » et « Comportement ».

@CAVEMAN.md
