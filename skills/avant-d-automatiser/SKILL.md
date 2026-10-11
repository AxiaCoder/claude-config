---
name: avant-d-automatiser
description: Use before proposing or building an automation — anything that runs without being called (cron, hook, worker, bot, loop, scheduled task, workflow, service) — or a new skill or command, and when asked "what should I automate", "is this worth building", "where is my bottleneck". Walks the Theory of Constraints over the flow, finds the bottleneck with a deterministic scorer, offers the no-build fix first, then picks the cheapest form and tool for one automation. Informs, never blocks — the user decides. Do not use to fix an existing automation, for a one-off script, or for a product feature — that is `cadrer-un-projet`.
---

# Avant d'automatiser

Une automatisation posée ailleurs que sur le goulot n'ajoute rien au débit : le système avance au
pas de son étape la plus lente. Ce skill trouve le goulot d'abord, puis pointe **une** automatisation
dessus — ou aucune. Porté de `the-goal` (glebis/claude-skills, MIT), d'après *Le But* de Goldratt.

⚠️ **Le garde informe, il ne bloque pas.** L'utilisateur tranche, y compris contre la fiche.

## Le vocabulaire

- **Débit** — le taux auquel le système produit ce pour quoi il existe : un nombre par période.
- **Inventaire** — le travail commencé et pas encore converti en débit : brouillons, files, en-cours.
  Un gros inventaire cache le goulot.
- **Dépense** — ce que coûte le système : heures, jetons, abonnements, attention. Une automatisation
  qui monte la dépense sans monter le débit est une perte, même si elle fait du bien.
- **Herbie** — le scout le plus lent de la troupe : accélérer les autres étire la file, la troupe
  marche toujours à son pas. Le goulot n'est presque jamais l'étape la plus agaçante : c'est celle
  devant laquelle le travail attend, dont l'aval a faim, et sans laquelle le débit ne monte pas.
- **Tambour-tampon-corde** — le goulot donne le rythme ; un tampon devant lui le garde toujours
  alimenté ; on ne lâche du travail neuf qu'au rythme qu'il absorbe.
- **Inertie** — continuer de polir l'ancien goulot une fois soulagé, par attachement à ce qu'on a
  construit. Le goulot se déplace : le suivre.

## Le déroulé

**Raccourci** — goulot déjà connu avec certitude → étapes 4 à 6 directement.

1. **But et débit.** Une phrase, et un **taux**. Sans taux → s'arrêter et le chercher avec
   l'utilisateur. « Gagner du temps » est refusé : baisser la dépense n'est pas monter le débit —
   sauf si la capacité libérée est elle-même le but déclaré.
2. **Flux et notes.** Claude **pré-remplit** le tableau des étapes, de l'intention au résultat, avec
   ce qu'il sait déjà, et le **montre en un seul message** pour correction — pas une question par
   étape. Notes de 0 à 3 :

   | Champ | Question |
   |---|---|
   | `throughput_sensitivity` | 2× plus rapide, le débit monterait-il ? **Décisif** : 0 disqualifie |
   | `wait_before` | du travail attend-il devant ? |
   | `downstream_starvation` | l'aval a-t-il faim à cause d'elle ? |
   | `capacity_gap` | demande au-delà de la capacité ? |
   | `policy_gate` | une règle ou une validation plutôt qu'un travail (oui/non) |
   | `annoyance` | à quel point elle **agace** — ne sert qu'à repérer le piège |
   | `necessary_condition` | doit être suffisante pour que ça marche, et l'est déjà (oui/non) |

   Inconnu → `null`, jamais une note inventée.
3. **Classement.** Depuis le dossier du skill, avec le Python de la machine (`python3`, ou `python`
   sous Windows) :
   ```bash
   echo '[{"name":"…","throughput_sensitivity":3,"wait_before":2,…}]' | python3 scripts/score_constraints.py
   ```
   Honorer le `verdict` : `insufficient_data` → compléter les notes ; `ambiguous` → resserrer le
   périmètre ou la fenêtre de temps ; `constraint_found` → suite. **Nommer à voix haute** chaque
   étape de rôle `trap` (agaçante mais pas liante) et `prerequisite` (à finir, puis ne plus y investir).
4. **Exploiter, puis subordonner.** D'abord le geste **sans construction** : protéger le temps du
   goulot, grouper, retirer un passage de main ou une validation, couper ce qui le consomme pour rien.
   Puis mettre le reste — automatisations existantes comprises — au service du goulot, quitte à
   ralentir ou ignorer les non-goulots. Souvent, ça suffit : forme 0.
5. **Forme.** Faits fermés → `choisir_la_forme.py` tranche (faits et ordre dans sa docstring) :
   ```bash
   python3 scripts/choisir_la_forme.py --jugement une-etape --sans-surveillance
   ```

   | # | Forme | Quand |
   |---|---|---|
   | 0 | Ne rien construire | l'exploitation suffit |
   | 1 | Réagir à un événement | un fait déclenche une action fixe |
   | 2 | Relier des services | colle entre services, sans jugement |
   | 3 | Script déterministe planifié | étapes fixes, logique à tester et versionner |
   | 4 | Script avec une étape d'IA | tout fixe sauf un jugement : classer, résumer, trier |
   | 5 | Commande lancée à la main | revient, demande du jugement, l'utilisateur la lance |
   | 6 | Agent autonome | jugement à chaque étape, sans personne |
   | 7 | Service permanent | tourne en continu |

   Du moins cher au plus cher, la première qui suffit. **L'IA seulement là où il faut juger** ; le
   reste déterministe, quitte à découper.
6. **Outil.** Claude lit le fichier désigné par la variable d'environnement
   `AVANT_D_AUTOMATISER_OUTILS` — une ligne par couple *Forme | Outil | Effort pour l'utilisateur |
   Effort pour Claude*. Parmi les outils de la forme retenue : le moins d'effort **pour
   l'utilisateur**, puis le moins cher à faire tourner — son temps est souvent le goulot. Un outil
   **non éprouvé** (Claude n'a jamais livré de cas réel avec) vaut effort fort.

   | Situation | Ligne « Outil » de la fiche |
   |---|---|
   | Variable absente | « non déclaré », puis une ligne : déclarer ses outils, modèle dans `exemple-perso/outils-d-automatisation.md` du dépôt de config |
   | Variable posée, fichier introuvable | « fichier introuvable : <chemin> » — une erreur de réglage, elle se dit |
   | Aucune ligne pour la forme | « aucun outil déclaré pour cette forme » |

   ⛔ **Jamais de bascule silencieuse vers une forme plus chère** faute d'outil. Sans fichier, le
   skill s'arrête à la forme : il ne bloque rien et ne demande rien.
7. **Prochain goulot.** Soulagé, le goulot se déplace : nommer où il ira, contre l'inertie.

## Les garde-fous

- **Jamais automatiser un non-goulot.** Si l'idée de l'utilisateur en vise un, le dire net et
  ramener au goulot.
- **Une seule automatisation**, pas une liste de cinq.
- **Exploiter et subordonner avant d'élever** : pas d'outillage quand un geste gratuit suffit.
- **Nommer les optimums locaux** quand on en voit : boîte vide, recherche plus rapide — de
  l'activité, pas du débit.

## La sortie

Une fiche d'une page, **dans la conversation** — le skill n'écrit aucun fichier :

- **But et débit** — la phrase et le taux.
- **Goulot** — l'étape, et ses preuves (verdict, notes décisives).
- **Exploitation** — le geste sans construction à tenter d'abord.
- **L'automatisation** — forme et outil, et en quoi elle sert le goulot. Ou « aucune ».
- **Ne pas automatiser** — les non-goulots tentants, nommés.
- **Prochain goulot** — où la contrainte ira ensuite.
