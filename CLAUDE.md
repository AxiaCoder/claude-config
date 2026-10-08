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
- Avant toute implémentation : spec Markdown d'abord
- Pas d'options non demandées

⚠️ **Une question sans réponse se repose en entier, jamais par renvoi.** Un « ma question reste
ouverte » est un accusé de réception, pas une question : l'utilisateur ne peut pas y répondre sans
remonter le fil.

⇒ Elle se repose **dès qu'un rapport de sous-agent s'est intercalé** depuis qu'elle a été posée —
c'est ce qui la fait disparaître de l'écran. Une session en a perdu une comme ça, entre quatorze
rapports d'agents sur trente-quatre messages.

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

⇒ **Oui : un worktree hors du dépôt**, `git fetch` puis
`git worktree add --no-track -b <branche> <dossier> origin/<base>`.
⛔ Jamais `switch`, `stash` ni `checkout` dans l'arbre de l'autre : il est à elle.

⛔ **Sous Windows aussi, le worktree est permis — mais jamais de jonction ni de lien vers
`node_modules`** ou tout autre dossier du dépôt principal : sa suppression suit la jonction et
efface la cible. Les dépendances s'y installent depuis le lockfile. Vaut pour tout worktree, celui
de `tester` compris.

⚠️ **Après le merge, le worktree se retire avec sa branche locale** — `git worktree remove`, puis
`git branch -D` une fois la PR `MERGED` selon `gh pr view` : après un squash, `-d` refuse la branche
comme non fusionnée. Sinon il traîne : six trouvés le 29/09, dont aucun n'avait plus d'usage.

## Actions interdites sans permission explicite

**Ne jamais merger une PR sans le demander.**

Avant `gh pr merge` ou tout merge :
1. Demander : « Tu veux que je merge la PR ? »
2. Attendre un accord explicite
3. Seulement ensuite, exécuter

La règle tient même sur « finalise » ou « termine » : merger n'est pas implicite.

## Outillage

⛔ **Un contenu multi-ligne (guillemets, antislashs) ne passe jamais non protégé en ligne de
commande.** Avec Write : l'écrire dans un fichier, puis `git commit -F`, `--body-file`,
`--input <fichier>`. Sans Write : un heredoc **protégé**, délimiteur entre apostrophes (`<<'EOF'`),
dont le shell ne transforme aucun caractère. Interdits : le heredoc non protégé (`<<EOF`) et la
chaîne entre guillemets doubles, qui font interpréter `$`, les backticks et les antislashs.

⇒ **Le fichier écrit se contrôle avant de servir** : hors octet nul, aucun caractère de contrôle
autre que le saut de ligne, la tabulation et — sous Windows — le retour chariot. Rien ne doit
sortir de :

```bash
LC_ALL=C grep -na "$(printf '[\001-\010\013\014\016-\037\177]')" <fichier>
```

(Vérifiée avec le `grep` BSD, GNU et ugrep ; `grep -P` n'existe pas partout.)

## Délégation aux sous-agents

⚠️ **Ce qui fait couper un agent, c'est l'exploration, pas la tâche.** Mesuré sur une session de
vingt relances : **treize** ont dû commencer par un ⛔ *« n'explore pas »*, et les coupures sont
tombées en exploration, pas en écriture. Les agents relisaient ce que le brief citait déjà.

⇒ **C'est pour ça que le brief porte des extraits verbatim et non des chemins.** Un extrait qui
fait foi est un fichier que l'agent n'ouvre pas. ⛔ **Un chemin nu coûte deux fois** : au parent
qui l'écrit vite, puis à l'agent qui va lire — et une fois de plus s'il coupe en route.

⚠️ **Un lot par lancement.** Un brief qui porte « lot 1, lot 2, dernier lot » fait un lancement
long, et un lancement long coupe. Trois briefs courts à la suite coûtent moins que trois coupures
et leurs relances. Monter le budget de tours ne règle pas ça : passé de 25 à 40, les coupures sont
restées — 7 sur 19 allers-retours, puis 8 sur 18.

### Quand déléguer

⚖️ **Avant de nommer un agent, une question fermée : est-ce qu'il doit écrire un fichier ou lancer
une commande ?**

| Réponse | L'agent |
|---|---|
| **Non** — il lit, il cherche, il rend une conclusion | **`Explore`** |
| **Oui** | `general-purpose`, ou `dev` si c'est du code du dépôt |

⛔ **Pas de jugement à porter là-dessus** : ce n'est pas « la recherche est-elle assez large »,
c'est « l'agent a-t-il besoin d'écrire ». La description de `general-purpose` promet d'aider *quand
on n'est pas sûr de trouver du premier coup* — c'est exactement l'état d'esprit au moment de
choisir, et c'est ce qui le fait gagner par défaut.

📌 **Mesuré sur 30 jours** _(23/09/2026)_ : **95 lancements de `general-purpose` contre 10
d'`Explore`**, alors que la règle ci-dessous nomme déjà `Explore` pour la recherche. Et le
fourre-tout coûte **7,2 M de tokens de cache relu par lancement contre 2,2 M** — plus de trois fois
plus. Le rapport entre les deux se suit par la télémétrie, quand elle est configurée.

Déléguer quand la tâche le mérite, pas par principe :

- **Large ou parallélisable** — plusieurs fichiers indépendants, plusieurs pistes à explorer en même temps → `Explore` pour la recherche, `dev` pour l'écriture.
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

📌 **Mesuré du 24 au 28/09** : `dev` **0 lancement**, pour 80 éditions de code dans la session
principale. La règle d'alors laissait le choix — *« un échange où le contexte accumulé vaut plus
que la parallélisation »* — et cette clause gagnait à chaque fois. ⇒ **Le contexte se transmet dans
le brief** : c'est ce que `ÉTAT:` existe pour porter.

Le débogage — chercher la cause — reste dans la session principale. Le correctif qui suit obéit à
la question ci-dessus.

### Les briefs se rédigent en caveman

**Un brief de sous-agent n'est pas une lettre.** Fragments, impératifs, symboles — le style de
`CAVEMAN.md`, importé en fin de fichier. Un brief de quatre-vingts lignes de prose coûte à
l'entrée et n'instruit pas mieux qu'un de vingt.

Ce qui reste en prose : **les extraits verbatim**. Un chemin seul oblige le sous-agent à relire ce
que le parent a déjà lu.

```
Task(subagent_type="dev", prompt="
BUT: [une ligne]
ÉTAT: [le code tel qu'il est — extraits verbatim, pas des chemins nus]
LE DÉFAUT: [ce qui cloche, avec sa mesure]
LA RÉFÉRENCE: [le modèle à suivre, et où le lire]
FICHIERS: a.ts, b.ts
CONTRAINTES: [stack, conventions]
AC: [ce qui doit être vrai à la fin]
RENDS: [la décision laissée ouverte, et les chiffres que seul l'agent verra]
STOP: [quand s'arrêter]
")
```

⛔ **`CONTRAINTES:` ne porte jamais ce que le `CLAUDE.md` du dépôt dit déjà.** Le harnais l'injecte
dans le contexte de chaque sous-agent, avec le `CLAUDE.md` global, `CAVEMAN.md` et la mémoire
automatique — **46 684 caractères en médiane, avant que le brief commence** *(mesuré le 26/09 sur
303 lancements)*. Recopier `pnpm`, `JSDoc` ou une convention de commentaire le paie deux fois.

⇒ Ce qui reste légitime dans `CONTRAINTES:` est ce que le dépôt **ne dit pas** : une contrainte
propre à ce tour, une version imposée, un fichier à ne pas toucher.

⚠️ **`RENDS:` est le miroir de ce que le brief laisse ouvert.** Il apparaît quand une décision
revient à l'agent — un seuil, un nom, un choix parmi plusieurs — ou quand l'agent verra un chiffre
que le parent ne verra pas : un compte, une mesure, une mutation rouge ou verte.

⛔ **Un brief d'exécution pure n'en a pas.** Les valeurs sont données, rien n'est à choisir, rien
ne remonte. Sur trente briefs, douze en portaient — et ceux qui n'en avaient pas traitaient des
retours de review ou appliquaient des valeurs dictées.

⛔ **Jamais ce que la déclaration garantit déjà** : la branche, le vert du lint, le bloc de sortie
sont dus de toute façon. `RENDS:` ne demande que ce que personne d'autre ne peut savoir.

⇒ `dev` et `tester` portent une ligne `RENDS:` en miroir dans leur bloc de sortie. **Sans elle, la
question se répond en prose au milieu du résumé, et le parent la cherche.**

⚠️ **Un brief porte une de ces trois têtes, parfois deux — jamais les trois.** Un tour qui ouvre
un sujet pose un `ÉTAT`, un tour qui corrige le précédent pose `LE DÉFAUT`, un portage pose
`LA RÉFÉRENCE`.

Elles remplacent un champ `CONTEXTE:` qui **n'avait pas de condition d'arrêt** : on ne sait
jamais quand on en a mis assez, et c'est ce qui gonfle un brief. Les trois s'arrêtent seules —
l'état finit où finit la fonction citée, le défaut quand sa mesure est donnée, la référence au
chemin du modèle plus les fonctions à y lire.

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

⚠️ **La boucle `dev` ⇄ `qa` est bornée à deux passes**, puis elle remonte quoi qu'il arrive. Le
brief porte le rang de passe — un agent neuf ne compte pas tout seul, c'est le parent qui tient
le compte. Au même écart constaté deux fois, `qa` rend `desaccord` : ce n'est plus un défaut,
c'est un critère qui ne tranche pas, et ça se règle avec l'utilisateur.

Ce qui se plafonne, c'est ce qui tourne **en même temps** :

- **2 en vol** par défaut, et seulement sur des pistes qui ne partagent ni fichiers ni contexte ;
- **4 au maximum**, quand c'est demandé ou que le gain d'horloge est évident.

⚠️ **Un seul agent qui écrit à la fois.** L'arbre de travail est un état partagé que rien ne
verrouille : deux agents qui éditent en parallèle, ou un qui édite pendant qu'un autre relit, se
marchent dessus sans que rien ne le signale. Les lecteurs (`reviewer`, exploration) peuvent aller
à plusieurs.

⛔ **`qa` ne tourne pas pendant que `dev` écrit.** Il charge des pages et lance des commandes sur
l'arbre de travail : lancé en parallèle, il exerce un état à moitié écrit et son constat ne vaut
rien. Il part après le rendu du dev.

⚠️ **Interdire explicitement `checkout`, `switch` et `stash` à tout sous-agent**, et lui demander
de confirmer la branche en fin de course.

⚠️ **Ne pas déléguer pour répéter du contexte que le parent a déjà.** Donner les questions et les
extraits, pas le dossier.

⚠️ **Ne jamais recoller la sortie brute d'un sous-agent** comme réponse finale : elle se
synthétise.

Agents disponibles : `dev`, `reviewer`, `tester`, `qa`, `ci`. Tous en `model: opus`.

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
