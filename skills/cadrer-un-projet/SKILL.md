---
name: cadrer-un-projet
description: Use when the user describes something to build that has no ticket and no code yet — a new project, or a feature they state before it exists. Runs three framing stages in conversation and lands the answers in the project sheet, never in a standalone document. Do not use for a question about existing code, for a ticket that already exists, or for a "what if we…" that is not going to be built.
---

# Cadrer un projet en conversation

## ⛔ Le moment, et surtout quand ce n'en est pas un

La discrimination est nette : **est-ce qu'il y a déjà un ticket, ou du code ?**

| C'est le moment | Ce n'en est pas un |
|---|---|
| un projet neuf, rien d'écrit | une question sur du code existant |
| une feature énoncée avant d'exister | un ticket Jira qui existe → `start-ticket` |
| *« j'aimerais faire un truc qui… »* | *« comment on ferait si… »* sans intention de le faire |

⚠️ **Se déclencher à tort coûte plus que de ne pas se déclencher.** Un cadrage lancé sur une
question ouverte transforme une réponse de trois lignes en interrogatoire.

## Ce que tu ne produis pas

⛔ **Aucun document.** Pas de brief, pas de PRD, pas de spec technique dans un fichier à part.

**La fiche projet** — son emplacement et son gabarit sont ceux que donne le `CLAUDE.md` de
l'utilisateur. Ses sections **couvrent déjà chaque chose que ce cadrage établit.** Un classeur
parallèle vieillit tout seul ; la fiche, non, parce qu'elle se relit à chaque démarrage de session.

⚠️ **Sans fiche déclarée, crée `docs/PROJET.md`** avec les sections du tableau ci-dessous, **et
ajoute au `CLAUDE.md` du dépôt la ligne qui le fait lire au démarrage.** Sans cette ligne, rien ne
le relit, et la fiche vieillit comme le classeur qu'elle remplace.

| Ce que l'étape établit | Où ça atterrit dans la fiche projet |
|---|---|
| le problème, la cible | `## Pourquoi ce projet existe` |
| ce que ça change si ça marche | `## Pourquoi ça compte` |
| le périmètre, inclus **et exclu** | `## Description` |
| l'objectif mesurable du moment | `## Milestone actuel` |
| les composants, la stack justifiée | `## Stack` |
| les arbitrages tranchés en route | `## Décisions & notes` |
| ce qui empêche d'avancer | `## Blockers` |

## Les trois étapes, en conversation

Tu poses les questions, tu écoutes, tu écris dans la fiche. ⛔ **Une étape à la fois** : poser les
quinze questions d'un coup produit un formulaire, pas un cadrage.

### 1 · Le problème, avant la solution

- **L'idée en une phrase.**
- **Quel problème, pour qui ?** Une idée dont on ne sait pas nommer le gêné n'est pas cadrée.
- **Pourquoi maintenant ?** Ce qui a changé pour que ça vaille le coup aujourd'hui.
- **Qu'est-ce qui existe déjà ?** Un outil, un bout de code, un autre de ses projets.
- ⛔ **Ce qui est hors périmètre.** C'est la question qu'on saute, et la seule qui borne le reste.

### 2 · À quoi on saura que c'est fait

- **Un objectif mesurable**, pas une intention. *« la page charge en moins d'une seconde »*, pas
  *« la page est rapide »*.
- **Le parcours principal**, en trois ou quatre étapes.
- **Ce qui doit être vrai pour que ce soit fini** — le critère d'acceptation, qui deviendra l'`AC`
  d'un brief de sous-agent.

### 3 · Ce que ça demande techniquement

- **Les composants** et ce qui circule entre eux.
- **La stack, justifiée** — pas la liste, la raison. Une techno sans justification écrite est une
  décision qui se rediscutera tous les trois mois.
- ⛔ **Les points de complexité**, nommés. C'est la partie que tout cadrage optimiste omet, et celle
  qui décide du délai.

## Après le cadrage

⇒ **Fais-le challenger.** Le skill `challenger-un-cadrage` cherche les trous d'un cadrage — c'est la passe adverse, et
c'est ce que personne ne pense à demander sur son propre travail.

⇒ Les tickets se créent ensuite par `/new-ticket`, un à la fois, à partir des critères d'acceptation
de l'étape 2. ⛔ Pas de découpage en lot : un ticket qui n'est pas près d'être pris vieillit avant
d'être lu.

## ⚠️ Ce que ce cadrage ne remplace pas

Il n'écrit ni code, ni ticket, ni décision à la place de l'utilisateur. **Une question à laquelle il
répond « je ne sais pas encore » reste ouverte dans la fiche**, marquée comme telle — la cacher
donnerait au cadrage une complétude qu'il n'a pas.
