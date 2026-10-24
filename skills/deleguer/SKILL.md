---
name: deleguer
description: Use before launching any subagent (Agent/Task tool) — to write the brief, pick its shape, and size the launch. Carries the brief template (BUT, ÉTAT, LE DÉFAUT, LA RÉFÉRENCE, AC, RENDS, STOP), the caveman style, what CONTRAINTES must not repeat, one batch per launch, and the measurements behind the delegation rules in CLAUDE.md. Do not use to decide who writes or how many agents run at once — those rules stay in CLAUDE.md § Délégation aux sous-agents.
---

# Déléguer : le brief et le lancement

Les règles de choix (qui écrit, combien en même temps) sont dans `CLAUDE.md` § Délégation aux
sous-agents. Ici : comment rédiger le brief et pourquoi.

## Ce qui fait couper un agent

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

## Les briefs se rédigent en caveman

**Un brief de sous-agent n'est pas une lettre.** Fragments, impératifs, symboles — le style de
`CAVEMAN.md`, importé en fin de `CLAUDE.md`. Un brief de quatre-vingts lignes de prose coûte à
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

## Les mesures derrière les règles de choix

📌 **`Explore` plutôt que `general-purpose`** — mesuré sur 30 jours _(23/09/2026)_ : **95
lancements de `general-purpose` contre 10 d'`Explore`**, alors que la règle nomme déjà `Explore`
pour la recherche. Le fourre-tout coûte **7,2 M de tokens de cache relu par lancement contre
2,2 M** — plus de trois fois plus. La description de `general-purpose` promet d'aider *quand on
n'est pas sûr de trouver du premier coup* : c'est l'état d'esprit au moment de choisir, et ce qui
le fait gagner par défaut.

📌 **`dev` plutôt que la session principale** — mesuré du 24 au 28/09 : `dev` **0 lancement**, pour
80 éditions de code dans la session principale. La règle d'alors laissait le choix — *« un échange
où le contexte accumulé vaut plus que la parallélisation »* — et cette clause gagnait à chaque
fois. ⇒ **Le contexte se transmet dans le brief** : c'est ce que `ÉTAT:` existe pour porter.

## Combien d'agents : ce que la règle de `CLAUDE.md` ne dit pas

⚠️ **Le navigateur est un état partagé, même sans fichier commun.** Constaté le 12/10 : deux
agents de recherche d'offres dans le même Chrome, le premier clic du second est tombé dans
l'onglet que pilotait l'autre. ⇒ Chacun crée ses onglets et ne touche qu'à eux ; le découpage
suit **la charge de chaque source**, pas un agent par site — la même passe a montré une source
à 7 min contre quatre réunies à 4. **C'est pourquoi le plafond est de 2** pour un état partagé (§ Combien à la fois de `CLAUDE.md`) : l'extension donne un seul groupe
d'onglets à toute la session, donc l'isolement tient à la discipline de chaque agent, pas à un
mécanisme — chaque agent de plus est une collision possible de plus.

📌 **Pour les lecteurs, la limite est le coût, pas la collision** : chaque agent repart du contexte
injecté par le harnais (mesuré plus haut), et chaque rapport revient dans la conversation.
⇒ **Une recherche se découpe en autant d'agents qu'elle a de pistes vraiment indépendantes** —
c'est là que le parallélisme rend l'horloge. Ce qui ne se fait pas : découper une même piste en
morceaux pour remplir des agents.

⚠️ **Ne pas déléguer pour répéter du contexte que le parent a déjà.** Donner les questions et les
extraits, pas le dossier.

## La boucle `dev` ⇄ `qa`

Le brief porte le rang de passe — un agent neuf ne compte pas tout seul, c'est le parent qui tient
le compte. Au même écart constaté deux fois, `qa` rend `desaccord` : ce n'est plus un défaut,
c'est un critère qui ne tranche pas, et ça se règle avec l'utilisateur.
