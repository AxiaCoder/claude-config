---
name: auditer-un-depot
description: Use when the user says a codebase is getting messy, asks where the technical debt is, wonders what to clean before a big change, or comes back to a project left aside for a while. Sweeps exhaustively but reports ranked by what each finding costs today, never by best practice. Do not use on a diff or a pull request — that is `reviewer` — nor to chase one known bug.
---

# Auditer un dépôt

## Le moment

| C'est le moment | Ce n'en est pas un |
|---|---|
| *« ce code est devenu sale »*, *« où est la dette ? »* | un diff, une PR → `reviewer` |
| avant un gros changement, pour savoir ce qui gênera | un bug précis → `systematic-debugging` |
| un projet repris après des mois | une relecture de ce qu'on vient d'écrire |

⚠️ **Un audit est une campagne, pas un réflexe.** Il se termine par une liste de tickets, pas par
des corrections — corriger en route transforme un relevé en chantier, et on perd le relevé.

## ⛔ Exhaustif au balayage, hiérarchisé au rendu

Les deux à la fois, et ce n'est pas contradictoire :

- **Au balayage, aucun filtre.** Tu lis, tu ne supposes pas. Un audit qui n'a regardé qu'un tiers du
  dépôt ne dit rien de ce qu'il n'a pas vu — et il doit dire ce qu'il n'a pas vu.
- **Au rendu, un ordre strict.** Un audit dont tout est critique ne se traite pas, et personne ne le
  relit deux fois.

## La sévérité : ce que ça coûte aujourd'hui

⛔ **Pas « est-ce une bonne pratique ».** La question est le coût, maintenant.

| | |
|---|---|
| 🔴 | ça produit **déjà** un résultat faux, expose une donnée, ou bloque un travail en cours |
| 🟠 | ça coûte **à chaque fois qu'on passe dessus** — et on passe dessus |
| 🟡 | tout le reste, si bon soit-il |

⚠️ Le 🟠 est celui qui demande du jugement : une duplication dans un fichier qu'on ne rouvre jamais
est un 🟡 ; la même dans le fichier le plus édité du dépôt est un 🟠. **Regarde `git log` avant de
trancher** — la fréquence d'édition dit le coût mieux que la nature du défaut.

## Où la dette se loge

**Ce que le dépôt dit de lui-même, d'abord.** `CLAUDE.md`, ses conventions, ses décisions écrites.
⛔ Un écart à une convention du dépôt compte ; un écart à une convention que tu apportes, non.

**Ce qui se répète** — le même geste résolu de trois façons. Le vrai coût n'est pas la duplication,
c'est qu'une correction sur l'une laisse les deux autres.

**Ce qui ne sert plus** — code mort, imports inutiles, fichiers que rien n'importe. Cherche-le, ne
le devine pas : `git grep` sur le nom, pas un jugement à l'œil.

**Ce qui mentira bientôt** — un commentaire, une docstring, un écrit que le code contredit déjà.
C'est la dette la plus silencieuse : elle ne casse rien, elle trompe le prochain lecteur.

**Ce qui coûte à l'exécution** — une requête dans une boucle, un index absent, un rendu qui se
rejoue sans raison. ⚠️ **Mesure avant d'affirmer** : une affirmation de performance non mesurée est
une opinion.

**Ce qui n'est pas couvert** — mais par ce qui compte, pas par un pourcentage. ⛔ **Ne cite pas de
cible de couverture** : aucun seuil n'est déclaré dans la CI de ces dépôts, donc un chiffre inventé
ici se ferait contourner. Nomme les chemins critiques sans test, pas un taux.

## ⚠️ Et remets en cause tes propres motifs

Une grande partie de ce code a été écrite par un agent. **Si tu reconnais ta propre main, c'est un
signal, pas une garantie** — un motif produit trois fois par le même outil reste un motif à
questionner.

## Ce que tu rends

```
PÉRIMÈTRE: <ce qui a été lu>
NON LU: <ce qui ne l'a pas été, et pourquoi>
🔴 fichier.ts:24 — <le défaut> — coûte <quoi, aujourd'hui>
🟠 …
🟡 …
D'ABORD: <les trois choses à faire en premier, et pourquoi celles-là>
```

⚠️ **`NON LU` n'est pas un aveu, c'est la moitié du relevé.** Un audit qui ne dit pas ses angles
morts se lit comme complet.

⚠️ **`D'ABORD` se borne à trois.** Une liste de quinze actions classées par priorité est une liste
que personne n'attaque.

## Après

Les points retenus deviennent des tickets par `/new-ticket`, un à la fois. ⛔ Pas de lot : un ticket
de dette qui n'est pas près d'être pris vieillit avant d'être lu, et il faudra le réécrire.
