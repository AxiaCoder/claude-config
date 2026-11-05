---
name: piloter-un-navigateur
description: Use before driving a browser to exercise a page — testing a flow by hand from the main session, or when the browser MCP server cannot be reached (`No matching deferred tools found`). Carries the single ToolSearch that loads the browser tools, how to recognise an unreachable server, and the two fallbacks — claude-in-chrome, then a Playwright script. Preloaded into the `qa` agent. Do not use to decide whether a change needs `qa` — that is `/pr`.
---

# Piloter un navigateur

Deux moments : **tester un parcours à la main** depuis la session principale, et **se rabattre**
quand le serveur MCP du navigateur ne répond pas.

## 1. Charger les outils

Tout en **un seul** `ToolSearch` — un appel par outil gaspille un aller-retour chacun :

```
select:mcp__chrome-devtools__new_page,mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__evaluate_script,mcp__chrome-devtools__take_snapshot,mcp__chrome-devtools__take_screenshot,mcp__chrome-devtools__click,mcp__chrome-devtools__fill,mcp__chrome-devtools__resize_page,mcp__chrome-devtools__list_console_messages
```

⚠️ **`No matching deferred tools found` ⇒ le serveur MCP n'est pas joignable d'ici.** Ne relance
pas de recherche : passe au repli. En session principale, demande d'abord à Axia de lancer `/mcp` — un
serveur encore en connexion se rattrape là.

## 2. Les replis, dans l'ordre

**`claude-in-chrome`, si tes outils l'ont** — la session principale l'a, `qa` non. Il agit dans le
Chrome d'Axia, avec ses sessions ouvertes. Charge d'abord le skill `claude-in-chrome`. ⚠️ Limite constatée le
26/10 : `resize_window` sans effet, rendu bloqué à 1920 px — un critère de largeur ne se mesure
pas par lui.

**Playwright**, par la recette du dépôt s'il en a une. Sinon, depuis la racine du dépôt :

```bash
node -e "require('@playwright/test')"
node -e "require('playwright')"
```

Sous pnpm, seul le paquet déclaré se résout, et c'est souvent `@playwright/test`. Un script Node
qui pilote Chromium rend les mêmes mesures ; le navigateur se télécharge dans le cache de
Playwright, le script s'écrit dans le dossier temporaire, jamais dans le dépôt.

## 3. Mesurer

`evaluate_script` — ou `page.evaluate` sous Playwright — rend un **chiffre** lu dans le DOM : un
compte, une largeur, une classe appliquée. C'est lui qui distingue un constat d'une impression.

⚠️ Ne déclenche jamais `alert`, `confirm` ni une boîte native : l'extension se fige. Lis la
console à la place.
