---
name: audit-seo
description: Use when a public page changes — a landing page, any page outside the login, an SEO page ("on touche la landing", "une page publique") — or when a site is about to go public or changes shape (a new page type, a route rename, a switch to client-side rendering), or when the user says a page is slow, not indexed, not found on Google, or asks whether the SEO holds. Runs Lighthouse, then what it cannot see, ordered by what actually costs indexation rather than by best practice.
---

# Auditer le SEO d'un site

## 0. Ce que le projet déclare

Si le dépôt a `.claude/surcharges/audit-seo.md`, lis-le d'abord : il complète ce skill, et le
remplace là où ils se contredisent.

Les **constantes** vivent dans le `CLAUDE.md` du projet, § « Pages publiques » — pas dans la
surcharge :

| Constante | Sert à |
|---|---|
| les **pages publiques**, chacune avec **les fichiers qui la rendent** (motifs) | `/pr` compare ces motifs à `git diff --name-only` — un layout partagé déclare toutes les pages |
| la **commande qui sert le site localement**, au plus près de la production | le mode page |
| l'**adresse de production** | le mode mise en ligne |

## Deux modes

| Mode | Quand | Quel site | Ce que tu vérifies |
|---|---|---|---|
| **Page** | une page publique change — `/pr` le lance sur les pages touchées | **la branche**, servie localement | pour chaque URL : Lighthouse, puis les deux 🔴 ci-dessous |
| **Mise en ligne** | le site va devenir public, ou change de forme | l'adresse de production | tout : Lighthouse et les deux 🔴 sur les pages clés, puis 🟠 et 🟡 |

⛔ **Le mode page n'audite jamais la production** : elle sert encore l'ancienne version, et un
`noindex` que la branche ajoute y serait invisible.

⚠️ **Mais un site servi localement n'est pas la production** : un en-tête `noindex` activé hors
production, un canonical absolu vers l'hôte de production, un `robots.txt` de préproduction y
lèvent des 🔴 qui ne viennent pas de la branche. ⇒ En mode page, **on compare des sorties, pas des
constats** : sers la base de la même façon, dans un worktree, et lance **la même commande** sur la
base et sur la branche. Un 🔴 compte dès que **la sortie change** dans le sens qui coûte
l'indexation — même si la base levait déjà ce 🔴 : un canonical déjà absolu qui change de chemin,
une règle `Disallow` ajoutée à un `robots.txt` qui en avait déjà. Le canonical se compare **par
chemin**, pas par hôte.

Le mode page ne fait que ce qui se juge **sur une URL**. Ce qui demande de parcourir le site — le
🟠 — reste à la mise en ligne.

## 1. Lighthouse d'abord

Il score déjà la catégorie SEO — titre, meta description, liens explorables, `robots.txt` valide,
`hreflang`, canonical, taille de police, cibles tactiles — ainsi que la performance et
l'accessibilité. Lis son rapport, puis **passe à ce qu'il ne voit pas** : il juge une page à la fois.

```
lighthouse <url> --chrome-flags="--headless" --output json --output-path <dossier temporaire>/lighthouse.json --quiet
```

- ⚠️ **Un rapport écrit n'est pas un audit réussi.** Sur une page qui n'a pas chargé, la commande
  sort en erreur mais écrit quand même le JSON, scores à `null`. Lis le code de sortie et le champ
  `runtimeError` **avant** les scores ; une erreur se rend comme « Lighthouse n'a pas tourné », pas
  comme des scores.
- **L'URL ne se devine pas** : elle vient du projet (§ 0). Absente → demande-la.
- ⛔ **Le serveur de dev de l'utilisateur ne se touche pas.** Il te faut un serveur : lance le tien sur un
  autre port, et tue-le après.
- **Le rapport s'écrit hors du dépôt** — jamais dans l'arbre de travail.
- La ligne de commande absente → le MCP `chrome-devtools`, outil `lighthouse_audit`.

⇒ Ta valeur est ailleurs : **ce qui se joue à l'échelle du site, et ce qui empêche l'indexation
avant que le classement soit même une question.**

## L'ordre des constats, et il n'est pas négociable

La sévérité suit une seule question : **est-ce que ça coûte l'indexation aujourd'hui ?** Pas
« est-ce une bonne pratique ». Un audit dont tout est critique ne se traite pas.

### 🔴 La page n'est pas indexable — tout le reste est sans objet

| À vérifier | Comment |
|---|---|
| `robots.txt` n'interdit pas la route | `curl -s <site>/robots.txt` |
| pas de `<meta name="robots" content="noindex">` | `curl -s <url> \| grep -i noindex` |
| pas d'en-tête `X-Robots-Tag: noindex` | `curl -sI <url> \| grep -i x-robots` |
| le canonical pointe sur elle-même, pas ailleurs | `curl -s <url> \| grep -i canonical` |
| le code de réponse est 200 | `curl -s -o /dev/null -w '%{http_code}' <url>` |

⚠️ **Un `noindex` oublié en préproduction et poussé en production est le défaut SEO le plus
coûteux qui existe**, et le plus silencieux : le site fonctionne, il disparaît simplement.

### 🔴 Le contenu n'existe pas sans JavaScript

**Le point le plus important dès que le rendu se fait côté client** — Inertia, React, toute SPA : le HTML
servi peut être une coquille vide, le contenu n'arrivant qu'après l'exécution du script.

```
curl -s <url> | grep -c "<un fragment de texte visible sur la page>"
```

**0 → le contenu n'est pas dans la réponse.** Googlebot exécute le JavaScript, mais dans une
seconde vague, différée et moins fiable ; les autres robots — réseaux sociaux, moteurs
alternatifs, IA — souvent pas du tout.

⇒ Le constat se pose, pas le remède : basculer en rendu serveur est une décision d'architecture,
pas une correction d'audit.

### 🟠 Le site se parcourt mal

| | Comment |
|---|---|
| un `sitemap.xml` existe et ne liste que des 200 | `curl -s <site>/sitemap.xml` puis un code par URL |
| aucune page orpheline — toute route atteignable par un lien | suivre les `<a href>` depuis l'accueil |
| pas deux URL pour la même page — `/x` et `/x/`, avec et sans `www` | comparer les canonical |
| le contenu diffère d'une page à l'autre | comparer les titres et les 200 premiers mots |

⚠️ **Lighthouse ne voit aucun de ces quatre points** : ils demandent plusieurs pages.

### 🟡 Ce qui améliore sans débloquer

Données structurées `schema.org`, longueur des titres, `og:` pour le partage social,
`Core Web Vitals` (LCP, INP, CLS). Réels, mais **ils ne décident pas de la présence dans l'index**.

## ⛔ Ce qui est du folklore, et que tu ne signales pas

- **« Un seul `<h1>` par page »** — Google a dit publiquement que plusieurs ne posent pas de
  problème. La structure des titres compte pour la compréhension, pas pour une règle de comptage.
- **« La meta description est un facteur de classement »** — non. Elle joue sur le taux de clic.
- **Une densité de mots-clés cible** — abandonné depuis longtemps.
- **Un score Lighthouse de 100** — c'est un indicateur, pas un objectif. Un site à 78 bien indexé
  bat un site à 100 en `noindex`.

⚠️ **Signaler du folklore coûte la crédibilité de tout le rapport.** Un constat sans conséquence
nommée n'est pas un constat.

## Comment tu rends

Les constats, par ordre de coût, avec pour chacun **l'URL, la preuve, et ce que ça coûte**. Jamais
une liste de bonnes pratiques.

```
MODE:       page — <les URL> | mise en ligne
LIGHTHOUSE: performance <n> · SEO <n> · accessibilité <n> — par URL
INDEXABLE:  oui | non — <ce qui l'empêche>
SANS JS:    le contenu est dans la réponse | absent
🔴 <url> — <le constat> — preuve : <la commande et ce qu'elle rend>
🟠 …
🟡 …
HORS PORTÉE: <ce qui demande Search Console, des données de trafic, ou une décision d'archi>
```

⚠️ **Ce que tu ne peux pas savoir se dit.** L'indexation réelle, les requêtes qui amènent du
trafic, les liens entrants : rien de tout ça ne se lit depuis le dépôt ni depuis une page. Le taire
donnerait à l'audit une complétude qu'il n'a pas.

## Si le constat demande un navigateur

⚠️ **Aucun sous-agent ne porte l'outil `Skill`** : ce fichier est lu par le thread principal. Pour
faire constater un rendu à l'écran — un contenu qui n'apparaît qu'après exécution, un `hreflang`
qui change selon la langue du navigateur — passe par `qa`, **en lui donnant le critère** et le point
d'entrée, jamais ce fichier.
