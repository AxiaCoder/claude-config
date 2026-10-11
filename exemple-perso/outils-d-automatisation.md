# Outils d'automatisation

Lu par le skill `avant-d-automatiser` une fois la forme choisie : parmi les outils de cette forme,
il retient le moins coûteux en effort **pour vous**, puis le moins cher à faire tourner. Désigné
par la variable `AVANT_D_AUTOMATISER_OUTILS` de `settings.json`.

Une ligne par couple forme × outil. Effort : `faible`, `moyen` ou `fort`. Un outil avec lequel
Claude n'a jamais livré de cas réel se note `non éprouvé` côté Claude : il compte comme `fort`.
Une forme sans ligne ici reste sans outil — le skill le dit, sans passer à une forme plus chère.

| Forme | Outil | Effort pour l'utilisateur | Effort pour Claude |
|---|---|---|---|
| 1 Réagir à un événement | Home Assistant (automatisation) | faible | moyen |
| 1 Réagir à un événement | Hook Claude Code | faible | faible |
| 2 Relier des services | n8n | moyen | moyen |
| 3 Script déterministe planifié | cron | faible | faible |
| 3 Script déterministe planifié | systemd timer | faible | faible |
| 3 Script déterministe planifié | GitHub Actions (planifié) | faible | faible |
| 4 Script avec une étape d'IA | Script Python appelant l'API d'un modèle, sous cron | faible | moyen |
| 5 Commande lancée à la main | Commande Claude Code | faible | faible |
| 6 Agent autonome | Claude Code en mode non interactif, sous cron | moyen | moyen |
| 7 Service permanent | Service systemd | moyen | moyen |
| 7 Service permanent | Conteneur Docker | moyen | non éprouvé |
