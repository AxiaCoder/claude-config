---
description: Créer un ticket Jira au format commun — objectif, état actuel, critères testables, périmètre, hors-scope, vérification — validé par l'utilisateur avant création
---

Crée un ticket Jira.

## 0. La surcharge du projet

Si le dépôt a `.claude/surcharges/new-ticket.md`, lis-le d'abord : il complète cette commande, et la
remplace là où ils se contredisent.

## 1. Ce qu'il faut savoir

Demande ce qui manque, pas plus : l'objectif en une phrase, et le type — fonctionnalité, bug,
refactor, doc.

## 2. Le format

C'est celui du flux de capture d'Hermès : **un seul format de ticket partout**.

| Section | Contenu |
|---|---|
| Objectif | une phrase : le quoi et le pourquoi |
| État actuel | le comportement d'aujourd'hui, et où il vit |
| Critères d'acceptation | une liste, **chaque ligne testable** |
| Périmètre | fichiers ou modules concernés |
| Hors-scope | ce qu'on ne touche pas, explicitement |
| Vérification | comment prouver que c'est fait |

⚠️ **« État actuel » et « Périmètre » se lisent dans le code**, pas chez l'utilisateur : ne les lui demande
pas, et ne les invente pas. Le reste vient de la conversation.

**Le ticket dit quoi, pas comment.** S'il contient la solution, le travail a déjà été fait à la
main — sauf une contrainte que le code ne laisse pas deviner.

**Les conventions du dépôt n'y sont pas.** Elles vivent dans son `CLAUDE.md` ; recopiées dans chaque
ticket, elles divergent.

⚠️ **Un critère se teste, ou il ne sert à rien.** « Le cache s'invalide correctement » ne se teste
pas ; « un PUT sur le prix d'un produit invalide son entrée de cache dans les 5 s » se teste.

⚠️ **Le hors-scope est le frein.** Un agent qui part corriger un bug, croise du code laid à côté et
le refait produit un diff de 400 lignes. Une ligne « ne pas toucher au reste du module » coûte une
seconde.

⚠️ **Un ticket se prend, se termine et se vérifie seul**, une fois ses dépendances closes — une
sous-tâche aussi.

| | Exemple | Verdict |
|---|---|---|
| **dépendance** | B ne démarre qu'une fois A terminé — lien « bloqué par » | ✅ permis |
| **couplage** | « tant qu'on n'attaque pas A, on ne prend pas B » : les deux avancent ensemble | ⛔ un seul ticket, ou un découpage où chacun se livre seul |

Un ticket couplé n'est pas bloqué par l'autre, il en est une moitié : aucun des deux ne peut être
clos sans l'autre, et le premier qui part laisse le second sans état stable.

## 3. Validation

- Affiche le ticket complet, et attends la validation de l'utilisateur.
- Puis crée-le via le MCP Jira, dans le projet demandé.
- Une épique se crée directement dans le statut de départ du projet, jamais en brouillon.

## Le sprint

Le MCP Atlassian n'expose aucun outil de sprint : le sprint s'écrit par son **id numérique** dans
`customfield_10020`, qui refuse le nom.

⇒ **L'id se lit, il ne se calcule pas.** Une JQL qui demande le champ le rend en entier :

```
searchJiraIssuesUsingJql  jql: "project = <CLÉ> AND sprint is not EMPTY"
                          fields: ["customfield_10020"]
```

⚠️ **Ne jamais extrapoler la suite des ids** : un mauvais id s'écrit **sans erreur** — un sprint
inexistant ne lève rien en JQL, exactement comme un sprint vide.