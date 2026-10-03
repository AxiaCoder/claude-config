# Un dossier perso d'exemple

À copier **hors de ce dépôt** — par exemple dans votre dossier de notes —, à adapter, puis à
donner à l'installation :

```bash
cp -R exemple-perso ~/notes/claude-perso
bash install.sh --perso ~/notes/claude-perso
```

| Fichier | Ce qu'il porte ici |
|---|---|
| `settings.json` | une préférence d'interface et les adresses de télémétrie (`192.0.2.10` est une adresse de documentation, à remplacer) |
| `CLAUDE.md` | qui vous êtes, et où vivent vos fiches projet — le skill `cadrer-un-projet` écrit là où ce fichier le dit |

Chaque fichier est facultatif. On peut y ajouter `settings.macos.json` ou
`settings.windows.json` pour ce qui ne vaut que sur un OS. Le fonctionnement complet →
[README](../README.md#le-dossier-perso).

⚠️ Ce dossier-ci n'est jamais lu par l'installation : il ne sert que d'exemple.
