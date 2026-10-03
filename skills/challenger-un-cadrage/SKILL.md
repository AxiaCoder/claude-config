---
name: challenger-un-cadrage
description: Use right after something has been framed and before any code is written — a project sheet just filled, a plan just agreed, a spec just read — or when the user asks what is missing, what has been forgotten, or whether a framing holds. Looks for the holes that implementation would discover the hard way, and ranks them by what each would cost to find late. Do not use on existing code, on a diff, or on a decision small enough to change afterwards.
---

# Challenger un cadrage

**Tu cherches ce que l'implémentation découvrirait à ses frais.** Pas ce qui manque à un document —
ce qui manquera à celui qui construit.

⛔ **Tu ne réécris pas le cadrage.** Tu le troues. Refaire le travail à la place de celui qui l'a
fait lui retire le moyen d'apprendre où il s'est trompé.

## Le moment

| C'est le moment | Ce n'en est pas un |
|---|---|
| une fiche projet vient d'être remplie | du code existe déjà → `reviewer` |
| un plan vient d'être arrêté, rien n'est écrit | un diff → `reviewer` |
| L'utilisateur demande *« qu'est-ce qui manque ? »* | une décision qu'on pourra changer après sans rien perdre |

⚠️ **C'est la passe que personne ne demande sur son propre travail.** Elle vaut surtout quand elle
n'a pas été réclamée — donc propose-la, ne l'impose pas.

## La sévérité, et elle a un critère

> **Ce trou serait découvert quand, et à quel prix ?**

| | |
|---|---|
| 🔴 | découvert **en cours d'implémentation**, et il fait refaire ce qui est déjà écrit |
| 🟠 | découvert **à la première utilisation réelle** — un cas limite, un état d'erreur non prévu |
| 🟡 | tout le reste : ça se décide plus tard sans rien perdre |

⛔ **Pas de tri par nature.** « Ce n'est pas une bonne pratique » n'est pas une sévérité. Cinq
points qui coûtent valent mieux que cinquante qui se lisent — et un cadrage dont tout est critique
ne se traite pas.

## Les quatre familles, et ce qu'on y oublie

Ce ne sont pas des cases à cocher : ce sont les endroits où les trous se logent.

**Fonctionnel** — les parcours sont-ils tous décrits, ou seulement le principal ? **Que se passe-t-il
quand ça échoue** ? Qui a le droit de faire quoi ?

**Technique** — les contrats entre composants sont-ils définis, ou supposés ? De quoi ça dépend
qu'on ne contrôle pas ? Qu'est-ce qui casse si la charge double ?

**Usage** — les états vide, en chargement, en erreur sont-ils prévus, ou seulement l'état plein ?
⚠️ **L'état vide est le plus souvent oublié, et le premier que l'utilisateur voit.**

**Exploitation** — comment on sait que ça marche en production ? Comment on revient en arrière ?
Qu'est-ce qu'on regarde quand quelqu'un dit que c'est cassé ?

## Ce que tu rends

Par ordre de coût, et chaque point porte **ce qu'il coûterait d'être trouvé tard** — sans ça, ce
n'est pas un constat, c'est un avis.

```
🔴 <le trou> — découvert à <quel moment> — coûte <quoi>
🟠 …
🟡 …
SOLIDE: <ce qui est bien tenu, une ou deux lignes>
À TRANCHER: <les décisions qui restent, avec leurs options>
```

⚠️ **`SOLIDE` n'est pas de la politesse.** Un cadrage dont on ne dit que les trous se refait en
entier au lieu d'être corrigé.

⚠️ **`À TRANCHER` n'est pas une liste de problèmes** : ce sont les questions dont la réponse
appartient à l'utilisateur, avec les options entre lesquelles il choisit. Ne réponds pas à sa place.

## Après

Les décisions tranchées retournent dans la fiche projet — `## Décisions & notes`. Les tickets se
créent ensuite par `/new-ticket`, un à la fois.
