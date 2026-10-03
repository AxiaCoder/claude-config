---
description: Démarrer le travail sur un ticket — « on attaque X », « fais-moi le topo », « découpe ce ticket » : le topo, la branche, puis ce qui se soulève en route part dans le ticket
---

Démarre le travail sur un ticket.

## 0. La surcharge du projet

Si le dépôt a `.claude/surcharges/start-ticket.md`, lis-le d'abord : il complète cette commande, et
la remplace là où ils se contredisent.

## 1. Le ticket

Récupère-le via le MCP Jira — la clé est celle du projet courant, jamais un exemple codé ici.

## 2. Le topo, c'est la paraphrase du ticket

Quand l'utilisateur demande **le topo** : paraphraser le ticket, court. Le problème, où ça mord, ce qu'il y
a à faire. **Rien d'autre.**

⚠️ **Ne pas ajouter le raisonnement, ne pas lister ce qu'on ne fait pas, ne pas coller de blocs de
code** — et surtout pas de « avant / après » dont les deux moitiés sont identiques. *« Si je veux
savoir le code que tu vas écrire, je relis la PR. Si je te demande le topo sur le ticket, tu dois me
paraphraser le ticket. »*

⇒ **Ce qui mérite d'être dit en plus, c'est ce que le ticket ne dit pas** : une valeur qu'il oublie,
une référence devenue fausse, une contrainte découverte en lisant le code.

## 3. La branche

- Le nom **au format du dépôt** — lis-le dans `git branch -a` et dans le `CLAUDE.md` du dépôt, ne le
  devine pas.
- La base à jour **sans bouger de branche** : `git fetch`, puis la branche part de `origin/<base>`.
  Jamais `checkout <base>` puis `pull` : c'est une bascule.
- ⛔ **Une autre session dans ce dépôt ?** Le `CLAUDE.md` global dit comment le voir, et que la
  branche part alors dans un worktree hors du dépôt.
- Sinon, l'arbre doit être propre — s'il ne l'est pas, demande quoi faire —, puis
  `git switch --no-track -c <branche> origin/<base>`.
- ⚠️ **`--no-track` n'est pas un ornement** : sans lui, la branche suit `origin/<base>` : un `pull` tire
  la base, et un `git push` nu échoue — ou vise la base, selon `push.default`.

## 4. En route

**Ce qui se soulève en conversation part dans le ticket, dans le même mouvement** — sinon il
disparaît, et personne ne s'en aperçoit. Écris-le **avant** de passer à la suite, ou **dis
explicitement que tu ne le notes pas**. Et ne réponds jamais « c'est couvert » sans avoir relu le
ticket : effleurer n'est pas consigner.

**Découper, c'est créer de vraies sous-tâches, jamais des tickets frères** — la structure
fonctionnellement exacte l'emporte sur celle qui se visualise le mieux. Les sous-tâches suivent le
sprint de leur parent. Pour le sprint lui-même : `/new-ticket` § « Le sprint ».

**Une pull request porte une seule chose.** Une PR qui en porte six ne converge pas : chaque passe
de review modifie du code, donc fabrique la matière de la suivante.

## 5. Prêt

Affiche « Prêt à travailler sur <la clé du ticket> », et rappelle la suite : `/pr` quand c'est fait.