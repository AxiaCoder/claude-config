---
description: Ouvre une pull request dont le corps dit le défaut, sa mesure et ce qui a été vérifié — le gabarit vient des PR déjà fusionnées ici, pas d'une convention importée
---

Ouvre une pull request depuis la branche courante.

## ⛔ D'abord, deux refus

⛔ **Pas sur `main`.** `git branch --show-current` d'abord ; sur `main`, on branche avant.
⛔ **Pas de merge.** Ouvrir et fusionner sont deux gestes, et le second demande l'accord de l'utilisateur —
même sur « finalise » ou « termine ».

## La porte avant d'ouvrir

Deux étapes, **dans cet ordre** : ce que la seconde vérifie doit contenir ce que la première ajoute.

**1 · Le code est vérifié par un autre que son auteur.** Une question fermée : **la branche
touche-t-elle un fichier de code**, au sens du `CLAUDE.md` global ?

| Réponse | Ce qui passe |
|---|---|
| **Non** — doc, réglages déclaratifs | rien |
| **Oui** | `tester`, en audit, sur `git diff <base>...HEAD` — `<base>` est la branche que la PR visera, `main` d'ordinaire |
| **Oui, et le changement s'exerce de l'extérieur** — une page, un endpoint, un parcours | `tester`, puis `qa` avec le critère d'acceptation et le point d'entrée |

**Et une seconde question fermée : la branche touche-t-elle une page publique ?** Le `CLAUDE.md`
du projet déclare, § « Pages publiques », chaque page avec les fichiers qui la rendent : compare ces
motifs à `git diff --name-only <base>...HEAD`. Une correspondance → le skill `audit-seo`, **mode
page**, sur les pages touchées. ⚠️ Sans déclaration, la question ne se pose pas : deviner ce qui est
public est justement le jugement qui ne part pas.

⛔ **Sans demander**, comme `reviewer` : c'est une vérification, pas une décision. **Les tests que
`tester` ajoute, c'est la session principale qui les commite** — lui n'a pas le droit.

⛔ **La PR ne s'ouvre pas** sur un test rouge qui désigne un vrai défaut, un `TOMBENT: non`, un
échec de `qa`, ou un 🔴 d'`audit-seo` — une page publique qui n'est plus indexable. L'auteur corrige,
puis l'étape 1 se rejoue — **deux fois au plus**, puis on remonte à l'utilisateur, comme la boucle
`dev` ⇄ `qa`.

⚠️ **`TOMBENT: non` ne bloque pas quand `tester` rend `COUVERTURE: sans objet`** — un diff qui ne
touche que des commentaires, ou n'ajoute que des tests qui figent l'existant : ses tests passent aussi
sur la base, c'est attendu. La condition est dans `agents/tester.md`, et c'est `tester` qui la
constate, jamais l'auteur du diff. Un refactor à comportement constant n'y entre pas : il bloque, et
remonte à l'utilisateur.

**2 · Ce que la CI du dépôt vérifie, rien d'autre.** Elle se lit dans `.github/workflows/`, elle ne
se devine pas : ⛔ ne lance pas un `build` qu'aucun workflow ne lance, et ne saute pas une
vérification qu'il lance. Le sous-agent `ci` fait exactement ça. Sur un dépôt sans workflow, lance
ce que son `CLAUDE.md` nomme.

## La langue suit le dépôt

Dans cet ordre, le premier qui répond tranche :

1. **Le `CLAUDE.md` du dépôt** fixe la langue des pull requests → celle-là.
2. **Les sujets des derniers commits écrits par un humain** (`git log --format=%s -8 origin/<base>`,
   sans les `Bump…` ni `Merge pull request…`) → leur langue majoritaire ; à égalité, celle du plus
   récent.
3. **Dépôt sans historique** → anglais.

⚠️ Qu'un dépôt soit public ne tranche rien : un dépôt public peut écrire en français. Passer un
dépôt à l'anglais est une décision, et elle s'écrit dans son `CLAUDE.md`.

## Le titre : un type que la machine lit, un constat que l'humain lit

```
<type>(<portée>): <le constat>
```

⚠️ **Le merge en squash fait du titre de la PR le sujet du commit** — c'est donc lui, et pas les
messages de la branche, qui entre dans l'historique et que les outils de versionnage liront.

**Le type décide de la montée de version** — `semantic-release`, `release-please`, `changesets` le
lisent tous de la même façon :

| Type | Ce qu'il monte | Pour quoi |
|---|---|---|
| `feat` | **mineur** | une capacité qui n'existait pas |
| `fix` | **patch** | un défaut atteignable corrigé |
| `feat!` ou un pied `BREAKING CHANGE:` | **majeur** | un appelant existant casse |
| `refactor` · `perf` · `test` · `docs` · `build` · `ci` · `chore` | rien, sauf configuration contraire | le reste |

⛔ **Le premier jeton est un type, pas un mot libre.** `scope(context):` ne se parse pas : un outil
cherche `fix`, il trouve `scope`, il ne reconnaît rien et ne monte aucune version.

**Et ce qui suit le préfixe reste un constat, pas une action.** Le titre dit ce qui est vrai : qui
relit l'historique dans six mois cherche le constat, pas le geste.

| ✅ | ⛔ |
|---|---|
| `fix(hooks): le contrôle ne vérifiait que le premier mot` | `fix(hooks): corrige le contrôle` |
| `fix(guardrail): les drapeaux longs passaient` | `fix: amélioration du garde` |
| `docs(optimisation): la preuve par l'absence d'un événement ne tenait pas` | `chore: update doc` |

⛔ **Pas de clé de ticket dans le titre.** Elle vit dans le corps, en lien vers le ticket.

## Le corps : quatre temps, dans cet ordre

**1 · Le défaut, avec sa mesure.** Pas la liste des fichiers — ce qui ne marchait pas, et le chiffre
qui le montre. ⛔ Un défaut sans mesure n'est qu'une opinion.

**2 · Ce que ça change.** Le geste, brièvement. Un tableau quand il y a un avant/après.

**3 · Ce que ça ne fait pas.** Ce qui est laissé de côté, et pourquoi. C'est la section qu'on oublie,
et celle qui évite le malentendu.

**4 · Ce qui a été vérifié.** La commande lancée et ce qu'elle a rendu. ⛔ Jamais « testé » tout
court.

⛔ **La vérification se relance après le changement, depuis l'état qui sera fusionné.** Mesurer que
le défaut existait ne dit rien du correctif.

⚠️ **Si la PR touche un `.md`**, lance le balayage. Il parcourt les `.md` et signale trois choses :
un renvoi vers une commande qui n'existe plus, un chemin de fichier qui n'existe pas, et une note
écrite deux fois dans le même fichier.

```
python3 scripts/verifier-les-ecrits.py . <les fiches concernées> --aussi <racines pour résoudre>
```

Les dossiers après `--aussi` ne sont pas balayés : ils servent à résoudre un chemin relatif à une
racine où le fichier qui le cite ne vit pas. Sortie 1 s'il trouve quelque chose.

⛔ **Pas de checklist.** Elle se coche sans être lue, et elle remplace la vérification par sa
promesse.

## La création

```
gh pr create --base <base> --head <branche> --title "<titre>" --body-file <fichier>
```

⚠️ **`--body-file`, jamais `--body "…"`.** Un corps passé en argument traverse le shell : les
backticks s'exécutent, les `$` s'étendent, le texte arrive mutilé.

⚠️ **Vérifie la base.** Une PR empilée sur une autre branche se fusionne **dans cette branche**, pas
dans `main`, et son contenu quitte alors tout historique vivant.

## Pour finir

- L'URL rendue par `gh`.
- **Puis la passe 1, sans reprendre la parole** : `reviewer`, avec le numéro de PR. Une review
  ne touche rien et ne pousse rien — demander « je lance la review ? » est un aller-retour pour
  une réponse qui est toujours oui.
- Quand elle tombe : skill `traiter-une-review`. Il porte la suite — la seconde passe, due, et le
  critère qui en autorise une troisième.
- Les lignes d'attribution que la session impose, si elle en impose.