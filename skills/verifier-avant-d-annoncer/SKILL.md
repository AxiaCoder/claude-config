---
name: verifier-avant-d-annoncer
description: Use before announcing that something works — before saying a quality gate passed, before presenting interface work, before starting a dev server, and when a symptom the user describes does not reproduce. Carries what has been announced wrongly before and what would have caught it — a green suite that proves nothing about the screen, a hollow test, a probe answered by someone else's server, an unlisted state, the wrong account. Reads the project's `.claude/surcharges/verifier-avant-d-annoncer.md` first. Do not use to handle a review — that is `traiter-une-review`.
---

# Vérifier avant d'annoncer

Chaque section dit **ce qui a été annoncé à tort**, puis ce qui l'aurait attrapé.

## 0. La surcharge du projet

Si le dépôt a `.claude/surcharges/verifier-avant-d-annoncer.md`, lis-le d'abord : il complète ce
skill — ports, comptes, générateurs, fichiers à ne pas formater —, et le remplace là où ils se
contredisent.

---

## 1. Le serveur de dev — celui de l'utilisateur ne se tue jamais

⛔ **L'utilisateur garde son serveur de dev en permanence.** Il ne s'arrête ni ne se relance.

Pour ce que le serveur recharge à chaud, le sien suffit et aucun serveur n'est à lancer. **Un serveur
à moi, quand ce qu'on vérifie ne se recharge pas à chaud** — la surcharge du projet dit quoi.

**Un port à moi, tiré au hasard** — jamais un numéro en dur : deux agents en parallèle, ou un serveur
mal tué, et le port fixe rend un `EADDRINUSE` pendant que la sonde interroge le serveur du voisin.

```bash
PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("",0));print(s.getsockname()[1])')
```

⚠️ **Tuer par le port, jamais par le motif de commande.** Un `pkill -f "<serveur>"` emporte le sien.

```bash
lsof -nP -iTCP:$PORT -sTCP:LISTEN -t   # le PID qui écoute, et lui seul
ps -o lstart=,command= -p <PID>        # vérifier que c'est bien le mien avant d'y toucher
```

⚠️ **`lsof -ti:$PORT` rend aussi les clients connectés** — le navigateur ouvert pour regarder
l'écran : tuer sa liste, c'est tuer le navigateur.

⚠️ **Un serveur à rechargement peut relancer son enfant** : tuer le seul PID du port ne suffit pas,
remonter au parent.

⚠️ **Tuer le mien à la fin.** Des sous-agents en ont laissé six qui squattaient un port — l'un
depuis quatre jours.

### Une sonde doit dire **quel** serveur répond

Un `302` prouve qu'**un** serveur répond sur ce port, pas que c'est le mien. Une journée de captures
a été prise ainsi, pendant que le log du mien alignait `started` **une** fois contre `EADDRINUSE`
**trente-cinq**.

```bash
lsof -nP -iTCP:$PORT -sTCP:LISTEN            # doit rendre mon PID, et lui seul
grep -c EADDRINUSE mon-serveur.log || true   # doit rendre 0
```

⚠️ **Un `EADDRINUSE` dans le log invalide tout ce qu'on a regardé ensuite**, et il n'apparaît nulle
part ailleurs : ni dans la sonde, ni à l'écran, ni dans le code de retour.

⚠️ **`grep -c` rend `0` et un code de retour 1 quand il ne trouve rien** : sous `set -e` ou dans une
chaîne `&&`, le cas nominal arrête tout. D'où le `|| true`.

### Avant de croire l'écran, comparer les âges

```bash
ps -o lstart= -p $(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t)   # démarrage du serveur
date -r <fichier modifié>                                  # dernière écriture, macOS et Linux
```

Serveur plus vieux que le fichier, et ce fichier n'est pas rechargé à chaud ⇒ **ce qu'on regarde est
périmé**.

---

## 2. Une suite verte ne prouve pas qu'une page s'affiche

Une suite qui s'arrête à la réponse du serveur prouve que **le serveur répond**, jamais que la page
**rend**. Une PR est partie en review sur la foi de 322 tests verts, avec une page qui ne s'affichait
pas.

⇒ **Avant de présenter un travail d'interface : ouvrir l'écran touché.**

⚠️ **Un écran derrière une connexion : demander à l'utilisateur de se connecter avant de
commencer**, pas en butant dessus — sans session, la vérification se rabat en silence sur une
relecture de code. **Aucun mot de passe n'est saisi par l'agent**, à une exception près : un compte
de développement ou de test que le projet documente, à trois conditions cumulées :

- **l'écran visé n'est jamais la production** — local, dev ou preview seulement ;
- **l'absence du compte en production se vérifie dans le code** (seeders, fixtures, scripts de
  déploiement), ⛔ **jamais en essayant de se connecter à la production** : ce serait l'acte même
  que la règle interdit ;
- **vérification impossible** (code des seeders absent, base partagée entre environnements) →
  pas de saisie, on demande à l'utilisateur.

⛔ **Jamais « vérifié à l'écran » pour un état qu'on n'a pas ouvert** — voir § 4.

### Ni qu'un artefact se régénère

Lint, typecheck et tests ne chargent pas les scripts de génération : un module que seul un
générateur importe n'est exercé par aucun d'eux. ⇒ Quand une PR touche ce qu'un générateur importe,
le relancer, puis `git diff --exit-code HEAD -- <artefacts>`.

⚠️ **Comparer à `HEAD`, pas à l'index** : l'index rendrait propre un artefact qu'on aurait indexé
sans le vouloir.

### Ni qu'aucun outil n'est passé derrière

Un formateur lancé sur un dossier qu'il n'a jamais formaté réécrit tout, et le lint reste vert.
⇒ **`git diff --numstat` avant d'annoncer** : un compte très supérieur à ce qu'on a écrit veut dire
qu'un outil est passé derrière.

---

## 3. Un test vert peut être creux

**Avant de committer un test, le faire échouer.** Un test vert sur un montage qui ne peut pas
produire le cas visé est pire qu'aucun test : il éteint la question.

⚠️ **Une seule mutation ne valide rien** — c'est celle qu'on avait en tête en l'écrivant, elle tombe
par construction. La question est **« qu'est-ce qui peut casser la propriété que son nom
annonce ? »**, puis essayer chacune.

⚠️ **Relire le nom du test et vérifier que l'assertion dit exactement ça, ni moins.** Une spec
nommée « déclaré dans le thème » assertait « présent quelque part dans le fichier ».

| Ce que la spec affirme | Mutations à poser |
|---|---|
| une convention (arrondi, tri, ordre) | **toutes** les alternatives, pas seulement celle qu'on a rejetée |
| une valeur de réglage (mode, option, seuil) | chercher **où** elle change quelque chose, et asserter là |
| une classe de style lue comme du texte | déplacer, échanger, préfixer d'une variante, passer par un style en ligne |
| un seuil | la valeur juste en dessous **et** juste au-dessus |

⚠️ **Choisir des valeurs qui séparent les alternatives.** « Arrondit au plus proche » testé sur
36 h et 23 h 59 ne dit rien : ce sont les deux points où `round` et `ceil` coïncident.

⚠️ **Vérifier que la mutation a été appliquée.** Une ancre qui ne matche pas rend une suite verte
qui se lit comme une mutation survivante : tout script d'édition vérifie que l'ancre apparaît
exactement une fois, et on relit le fichier après.

---

## 4. Énumérer les états avant de toucher une ligne qui en gouverne plusieurs

Une expression conditionnelle, une classe partagée, une garde : **écrire la table des cas avant
l'édition**, et relever la valeur obtenue pour chacun après.

Sur un anneau de focus — *ni choisie ni focalisée · focalisée · choisie · choisie **et**
focalisée* —, deux commits de correction ont introduit un défaut bloquant : lint vert, typecheck
vert, et « vérifié à l'écran » annoncé sur le seul état qu'on venait de changer.

**Un état absent de la table est un état qu'on ne vérifiera pas.**

---

## 5. Quand un symptôme ne se reproduit pas, vérifier le contexte avant le mécanisme

**Quel compte, quel serveur, quelle branche** — pas le mécanisme.

L'utilisateur regarde souvent avec son propre compte, créé à la main, qui n'existe sur aucun clone. Quatre
tours de diagnostic ont été passés sur le compte de dev : rien n'était cassé, et les trois faits
donnés dès son premier message étaient justes.

⇒ **Demander, ou lire la base.** Une sonde avec ma propre session ne prouve rien sur la sienne :
poser d'abord les deux ou trois requêtes qui décrivent *son* état.

---

## 6. Un résultat vert ne vaut que sur l'arbre attendu

**Avant d'annoncer une porte franchie, `git status` doit montrer les fichiers attendus modifiés.** Un
`git stash` glissé dans une commande d'exploration vide l'arbre : le lint, le build et la suite qui
suivent tournent alors sur `HEAD` — verts, et sans rapport avec le travail.
