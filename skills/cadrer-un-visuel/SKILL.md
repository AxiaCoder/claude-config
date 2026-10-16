---
name: cadrer-un-visuel
description: Use when a screen or interface is about to be built and no mockup is referenced — in the ticket or in the project sheet — or when the user asks to mock up, sketch or think through the design of such a screen. Load it BEFORE any mockup tool: it frames the screen in conversation, checks the user's design choices against a short set of UX principles and says so when one is off, settles where the mockup lives, and only then hands the drawing to the mockup tool. Typically raised by `cadrer-un-projet` or `start-ticket`, but also reached directly. Do not use for a pure back-end change, for a fix to a screen that already exists, when a mockup is already provided, nor to review a screen that is already built.
---

# Cadrer un visuel en conversation

Une interface construite sans maquette sort générique et se reprend par petites retouches. Ce
skill fixe l'écran **avant** le code, et dit quand un choix de design est mauvais — l'utilisateur
n'a pas toujours les bonnes pratiques UX, et exécuter sans rien dire ne les lui apprend pas.

## ⛔ Le moment

Une interface va s'écrire, et **aucune maquette n'est référencée** — ni dans le ticket, ni dans la
fiche projet. C'est ici, et nulle part ailleurs, que la question s'écrit : `cadrer-un-projet` et
`start-ticket` y renvoient.

**La question, une seule :** « Cet écran n'a pas de maquette. Maquette d'abord, ou premier jet
libre assumé ? »

| Réponse | Ce qui se passe |
|---|---|
| Maquette d'abord (ou l'utilisateur vient de la demander : la question est répondue) | le déroulé ci-dessous |
| Premier jet libre | une ligne dans le ticket s'il y en a un, sinon dans la fiche projet, puis le travail continue — c'est un choix légitime, pris en connaissance de cause |

⚠️ **Ne pas se déclencher sur un ticket sans interface**, ni sur le correctif d'un écran qui
existe : un cadrage visuel posé là est du bruit.

## Ce que tu ne produis pas

⛔ **Aucun document à part.** Les arbitrages vont dans `## Décisions & notes` de la fiche projet.
**Sans fiche**, le repli est celui de `cadrer-un-projet` (§ « Ce que tu ne produis pas ») : créer
`docs/PROJET.md` et la ligne du `CLAUDE.md` du dépôt qui le fait lire. La maquette, elle, vit là où
l'étape 5 l'a décidé.

## Le déroulé, une étape à la fois

⛔ **Pas un formulaire** : une question, la réponse, la suivante.

0. **Les reprises relevées.** Lis d'abord le bloc « Reprises relevées » de la fiche projet, s'il
   existe : c'est ce que ce projet a déjà payé.
1. **La charte minimale**, avant le premier écran : le ton, une couleur d'accent, une police, la
   densité. C'est ce qui évite le visuel générique. Si la fiche projet en porte une, lis-la au lieu
   de la redemander.
2. **L'écran** : son rôle, son action principale, ce que l'utilisateur doit comprendre en trois
   secondes.
3. **Le passage au socle** (ci-dessous) avant de dessiner.
4. **Les états** : vide, chargement, erreur, succès, désactivé.
5. **La maquette**, aux trois tailles : bureau, tablette, mobile. ⛔ **Avant de la produire, où
   vivra-t-elle ?** Un fichier dans le dépôt, un artefact, autre chose : si la fiche projet ou les
   consignes de l'utilisateur ne le disent pas, demande-le, et ne crée aucun fichier dans le dépôt
   sans cette réponse. Puis dessine avec l'outil de maquettes dont on dispose, sous ce cadrage. Sans
   outil, une description écrite de l'écran à ces trois tailles.
6. **L'enregistrement** dans la fiche projet : l'emplacement de la maquette (chemin ou lien), puis
   les arbitrages. Sans lui, la question revient au ticket suivant.

## Le socle de principes

Court, chaque principe avec sa raison. Il éclaire et il fait débattre : il n'interdit pas.

| Principe | Pourquoi |
|---|---|
| Une action principale par écran | sinon l'œil ne sait pas où aller |
| Hiérarchie par taille, graisse et contraste, deux ou trois niveaux de texte | la décoration ne remplace pas l'ordre |
| Contraste du texte ≥ 4,5:1 (3:1 pour les grands textes et les composants) | lisibilité et accessibilité (WCAG 2.2 AA) |
| Cibles tactiles ≥ 44 px | un doigt n'est pas un curseur |
| Tous les états traités, focus visible | l'écran vide ou en erreur est un écran comme un autre |
| Même geste, même composant ; échelle d'espacement et de typographie fixée | la cohérence vient de la contrainte, pas de l'œil |
| La couleur n'est jamais le seul signal | daltonisme, écrans délavés |
| Corps de texte ≥ 16 px, lignes d'environ 75 caractères au plus | confort de lecture |
| Bouton = verbe + objet ; une erreur dit quoi faire | l'utilisateur agit sans deviner |

## ⚠️ L'obligation de répondre

**Quand l'utilisateur propose un choix de design, compare-le au socle avant d'exécuter.** S'il s'en
écarte : dis-le, avec la raison et ce que ça coûte, puis laisse-le trancher. Son avis reste final ;
ce qui est interdit, c'est l'« ok » donné sans avoir fait la comparaison.

⛔ **Ne juge pas le beau.** Ce qui s'exige se vérifie : contraste, débordement, états, libellés,
tailles. Une impression de style n'est pas un défaut.

## Les interdits propres au projet

⛔ **Pas de liste d'interdits écrite d'avance** : elle se relève sur les reprises réelles. Chaque
retouche visuelle que l'utilisateur doit demander, y compris après le code, s'ajoute en une ligne
dans un bloc « Reprises relevées » sous `## Décisions & notes`. Ce bloc se lit à l'étape 0.

## ⚠️ Ce que ce cadrage ne remplace pas

Il ne remplace ni un designer ni la relecture d'un écran construit : il évite les erreurs connues
avant le code. Une question à laquelle l'utilisateur répond « je ne sais pas encore » reste ouverte
dans la fiche, marquée comme telle.
