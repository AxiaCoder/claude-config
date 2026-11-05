---
name: regles-dev-tester
description: Preloaded into the `dev` and `tester` agents through their `skills:` field — the debug-output check on what they touched, and the turn budget that exploration eats. Do not invoke from the main session.
user-invocable: false
---

# Règles communes à `dev` et `tester`

## Aucun débogage dans ce que tu as touché

⛔ **Aucun débogage dans ce que tu as touché.** Ça ne se relit pas, ça se lance :

```
git diff -U0 | grep -nE '^\+.*(console\.(log|debug|warn)|debugger\b)'
```

Rien ne sort → c'est propre. Quelque chose sort → tu le retires. ⚠️ Le `^\+` compte : la commande
ne juge que **tes ajouts**, pas un `console.log` que le dépôt assume déjà.

## ⚠️ Ton budget de tours est fini, et c'est l'exploration qui le mange

**Les extraits du brief font foi.** Ce qu'il cite n'est pas à relire, ce qu'il donne pour établi
n'est pas à revérifier.

⛔ Ne rouvre pas un fichier que le brief cite.
⛔ Ne rouvre pas un fichier que tu viens d'écrire — tu le connais.
⛔ Ne pars pas confirmer une cause que le brief déclare trouvée.

⇒ **Il te manque vraiment quelque chose ?** Lis ce qui manque, rien d'autre. Et si le lot est plus
gros que ton budget, **rends ce que tu as fait en disant ce qui manquait** — c'est une réponse
valable, pas un échec.
