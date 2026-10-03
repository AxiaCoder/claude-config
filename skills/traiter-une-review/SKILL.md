---
name: traiter-une-review
description: Use when a review pass has just landed on a pull request, or when resuming one — "traite la review", "la review a sorti quoi ?", "corrige les retours", or right after a `reviewer` agent hands back. Carries the pass cadence (the second pass is due, a third only on a reachable defect), the five handling rules, and the report to the user, written in terms of the defects found, not of the fixes. Do not use to conduct the review itself — that is `reviewer` / `/pr-review`.
---

# Traiter une passe de review

Ce skill couvre la **cadence** des passes — combien il en faut —, puis ce qui se passe une fois
une review postée : corriger, répondre, et rendre compte. Conduire la review elle-même est un autre
outil : `reviewer`, ou `/pr-review`.

⚠️ **Le livrable final n'est pas le code corrigé, c'est le compte rendu.** L'utilisateur lit le compte
rendu ; il ne lit ni le diff ni les fils GitHub. Un traitement parfait dont le compte rendu parle
des corrections est un traitement raté — voir §5, qui est la raison d'être de ce skill.

📌 **Ce qui est propre à un dépôt** — ticket à faire avancer, formateur à ne pas lancer, serveur à
ne pas tuer — vit dans son `CLAUDE.md`, pas ici.

---

## 0. Combien de passes

**La passe 1 part avec l'ouverture de la PR, sans question** — c'est `/pr` qui la lance, et qui
dit pourquoi. La permission qui compte est celle du **commit**, du **push** et de la **fusion**.

**Deux passes, puis la fusion.** La seconde part d'elle-même, dès que le traitement de la première
est poussé. Une troisième se lance seulement si la seconde **désigne un défaut atteignable** — et
c'est alors ce défaut qui la justifie, jamais la prudence.

⚠️ **Ne jamais proposer une passe de plus.** Quatre passes ont tourné sur une pull request de six
pixels, et **aucune des quatre n'a désigné un défaut atteignable**. Les quatre disaient aussi
« registre à jour : non », et à chaque fois sur un écrit **que cette pull request avait elle-même
produit**. Le reste était des durcissements, qui partent en ticket et ne retiennent rien.

⇒ **C'est ce qui rend la seconde passe due, et la troisième facultative.** La seconde relit ce que
le traitement de la première a écrit ; au-delà, une passe ne relit plus que sa propre trace —
chaque traitement réécrit, et chaque réécriture redonne à relire.

⚠️ **Et proposer moins de la même chose reste proposer la même chose.** « Une passe de vérification
des écrits, et tout durcissement part en ticket » est une passe de plus, déguisée en modération.

On rend compte **une fois par passe**, quand elle est tombée — pas au moment de la lancer. La forme
est en §5, et le total qu'elle prévoit se donne **sur la dernière passe**.

---

## 1. Lire la review, pas son résumé

```bash
gh api --paginate repos/<OWNER>/<REPO>/pulls/<PR>/comments \
  --jq '.[] | "── #\(.id)\(if .in_reply_to_id then " ↳ #\(.in_reply_to_id)" else "" end) \(.path):\(.line)\n\(.body)\n"'
gh api --paginate repos/<OWNER>/<REPO>/pulls/<PR>/reviews --jq '.[] | .body'
```

⚠️ **`--paginate` n'est pas un ornement : sans lui, `gh api` s'arrête à 30, en silence.** Rien dans
la sortie ne dit qu'il en manque. Une PR a porté **185** commentaires inline — on en aurait lu 30.

⚠️ **Et le cas le plus traître est la PR qui en porte exactement 30** : la sortie est alors complète
en apparence, tronquée en réalité, et rien ne distingue les deux.

⚠️ **Le résumé d'un agent de review comprime, et c'est dans ce qu'il comprime que se cache le
point le plus utile.** Un 🟡 qui a l'air d'une préférence de style est souvent une garantie que
rien ne tient. Lire le texte posté, en entier, avant de toucher à quoi que ce soit.

L'`id` sert au §4 : on répond au commentaire **de tête** d'un fil, celui qui n'a pas de `↳` —
l'API refuse une réponse à une réponse.

Relire aussi **ses propres réponses aux passes précédentes** : elles contiennent des affirmations,
et une correction peut les rendre fausses.

---

## 2. Les cinq règles

Elles empêchent une chaîne causale : une correction juste localement ouvre la suivante. Chacune
porte le **piège observé**.

### 1. Rayon d'action — *qu'est-ce que ce changement rend atteignable qui ne l'était pas ?*

Aller le vérifier, et l'écrire dans la réponse au reviewer. Le piège : répondre « rien » sans
avoir cherché. Un délai qu'on borne rend atteignable l'échec qu'il déclenche ; une garde ajoutée
d'un côté dit ce qui manque de l'autre ; un repli qui ferme un chemin déplace le seuil sur un autre.

### 2. Corriger la classe, pas l'instance

Un retour qui nomme un motif — lire-puis-écrire, une affirmation de doc, une garde manquante — se
traite sur **toutes** ses occurrences de la PR avant qu'on réponde.

⚠️ **Le reviewer nomme les occurrences qu'il a vues, pas toutes celles qui existent.** Une
suggestion citait deux niveaux à replier ; il y en avait trois. **Chercher par `grep`, ne pas se
fier à l'énumération du retour.**

⚠️ **Une review nomme un symptôme sur un chemin. Corriger la règle, pas la lecture.** Avant de
toucher au code : écrire la **règle** que le code devrait tenir, et vérifier qu'elle est vraie sur
**tous** les chemins. Un défaut corrigé côté *lecture* — un filtre de plus — a refermé un chemin et
laissé le même symptôme, mot pour mot, sur un autre.

| Signe qu'on corrige la **lecture** | Signe qu'on corrige la **règle** |
|---|---|
| la correction est un `where`, un `??`, une garde de plus | elle se dit en une phrase |
| on ne peut pas l'énoncer sans nommer un cas particulier | elle rend les cas disjoints |
| | une mutation qui l'enlève tue des tests |

### 3. Supprimer le mode de défaillance plutôt que le garder

Une instruction plutôt que deux gardées, un type marqué plutôt qu'une convention. Un type
restreint vaut mieux qu'un test : le test n'attrape que les cas auxquels on a pensé.

⚠️ **Se méfier de « ça ne peut pas arriver dans la configuration actuelle ».** C'est un
raisonnement, pas une garantie, et il vieillit sans prévenir. Faire que la branche **n'existe
pas** plutôt qu'elle soit inatteignable.

### 4. Les écrits se relisent dans les deux sens

Un écrit qui décrit le code — doc, registre de décisions, JSDoc, corps de PR — se relit quand la
correction le touche, **et quand elle touche le code qu'il décrit**, même sans le toucher lui. Un
écrit qui se contredit vaut moins qu'un écrit absent.

⚠️ **Le piège n'est pas d'oublier de relire, c'est de réécrire sans redériver.** Ce qu'un écrit
chiffre se redérive **du code**, jamais de la correction qui l'a signalé, ni du chiffre que le
reviewer propose.

⚠️ **Et relire l'écrit que la correction *contredit*, pas seulement celui qu'elle *modifie*.** Une
PR a ajouté un état à un écran ; l'écrit qui niait l'existence de cet état vivait ailleurs et n'a
été vu qu'à la troisième passe.

**Trois règles sur les chiffres** — à chaque fois, le nombre avait vraiment été mesuré, mais à côté
de ce que le code fait :

1. **Un chiffre se mesure avec le code qui l'établit**, jamais avec un script écrit pour
   l'occasion : ce sont deux implémentations de la même idée, donc elles divergent. Si un test
   sait calculer la grandeur, c'est lui qui donne le chiffre.
2. **Jamais une moyenne.** Elle dépend d'une convention qu'on oublie d'écrire à côté d'elle. Un
   maximum, un seuil, un compte exact ne bougent pas. ⚠️ Mais un maximum obtenu par
   échantillonnage est un minorant : resserrer le pas jusqu'à ce qu'il cesse de bouger.
3. **Un compte d'éléments de contenu n'est pas une propriété du mécanisme** : il bouge chaque fois
   que le contenu bouge. Ce qui mérite d'être écrit est ce qui ne bouge pas — « zéro avec la
   garde ». Quand un seuil dépend du contenu, **écrire la forme et non le nombre**.

⚠️ **Un chiffre consigné vieillit au premier commit suivant, y compris un commit qui ne le vise
pas.** Avant de citer un nombre déjà écrit, le remesurer sur le code tel qu'il est. Le piège est de
**citer une mesure juste faite sur un autre état du code**.

⚠️ **Y compris un chiffre que le reviewer vient de produire.** Une table de mesures reprise telle
quelle a été consignée comme propriété du mécanisme — « ça rebondit au lieu de converger » — alors
qu'elle était l'artefact d'un `break` cassé : le commentaire énonçait une loi qui décrivait un bug.

⚠️ **Vérifier ce que la source compte, pas seulement le nombre.** « La production double, +89 % »
venait d'une sortie qui imprime un stock de fin, pas une production — la vraie hausse était de
+9,5 %. Lire l'étiquette de la colonne.

⚠️ **Un argument qui tient sans chiffre ne prend pas de chiffre.** L'inventer pour faire poids,
c'est le rendre réfutable pour rien.

### 5. Examiner chaque suggestion

Le reviewer se trompe, et une suggestion reprise telle quelle introduit un défaut. Ce n'est pas
cette étape-là qu'il faut accélérer.

⚠️ **Et une suggestion juste en introduit un autre**, que cette règle-ci ne couvre pas : le défaut
naît alors de la **mise en œuvre**, pas de l'idée. Voir §3 bis.

⚠️ **Mais un refus s'argumente sur quelque chose de vérifié.** Un refus s'est appuyé sur une phrase
d'un écrit que la même PR venait de rendre fausse. Avant de refuser : relire la source citée.

---

## 2 bis. Ce qu'une review ne fera pas

Elle attrape très bien les écarts entre le code et ce qui l'accompagne. Elle ne questionne
**presque jamais le choix de conception lui-même** — elle vérifie que le choix est bien exécuté.

Trois passes ont trouvé six affirmations écrites fausses sur une PR, et aucune n'a demandé s'il
fallait vraiment poser **une ligne en base par élément** pour porter une propriété. C'est l'utilisateur
qui l'a fait tomber, en demandant ce que ça coûterait avec beaucoup plus d'éléments.

⇒ **Si un choix a un coût qui croît avec les données, le nommer et le soumettre avant de livrer.**
Chiffrer ce qu'il coûte **à la lecture**, pas seulement à l'écriture. Ne pas compter sur une passe
de review pour rouvrir un choix.

---

## 3. Muter les tests qu'on touche

**Un test vert ne prouve rien tant qu'on ne l'a pas vu tomber**, et une seule mutation ne le valide
pas : **celle qu'on essaie est celle qu'on avait en tête en l'écrivant**, donc il tombe par
construction. La question n'est pas « est-ce qu'il tombe ? » mais *« qu'est-ce qui peut casser la
propriété que son nom annonce ? »*, puis essayer chacune.

⚠️ **Relire le nom du test et vérifier que l'assertion dit exactement ça, ni moins.** Un test nommé
« déclaré dans le thème » assertait « présent quelque part dans le fichier ».

| Ce que le test affirme | Mutations à poser |
|---|---|
| une convention (arrondi, tri, ordre) | **toutes** les alternatives, pas seulement celle qu'on a rejetée |
| une valeur de réglage (mode, option, seuil) | chercher **où** elle change quelque chose, et asserter là |
| un seuil | la valeur juste en dessous **et** juste au-dessus |

⚠️ **Choisir des valeurs qui séparent les alternatives.** Un test « arrondit au plus proche » qui
essaie 36 h et 23 h 59 ne dit rien : ce sont exactement les deux points où `round` et `ceil`
coïncident.

⚠️ **Vérifier que la mutation a été appliquée.** Une ancre qui ne matche pas rend une suite verte
qui ne prouve rien, et se lit comme une mutation survivante.

⇒ La mutation la moins chère : **rejouer la suite contre la version de `main`** du fichier corrigé.
Les nouveaux cas doivent tomber, les anciens tenir.

---

## 3 bis. Un changement censé ne rien changer est celui qu'on ne vérifie pas

**Le critère ne tient pas à la nature du changement mais à la phrase qui le décrit.** Dès que cette
phrase est *« même comportement, meilleure forme »* — renommer, extraire, déplacer, réordonner,
remplacer par un équivalent —, rien dans l'intention ne pousse à regarder. Et la suite reste verte :
**elle l'était avant.**

⇒ Avant de committer une correction de cette forme : *quel test passerait au rouge si je me
trompais ?* Si la réponse est **aucun**, c'est le signal, pas la permission.

⇒ Deux contrôles, et le second suffit souvent : **poser la mutation** — défaire le changement, voir
si quelque chose tombe —, ou **comparer les deux sorties** sur une entrée que le changement
traverse.

⚠️ **Ça ne se rattrape pas en examinant mieux la suggestion du reviewer.** Une PR a perdu une
propriété en suivant un retour **juste** : le balayage remplacé parcourait aussi ce qu'il venait
d'ajouter, l'index qui l'a remplacé non.

---

## 4. Répondre, fil par fil

```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR>/comments/<COMMENT_ID>/replies \
  --method POST -F body=@<scratchpad>/reponse.md
```

Le fichier s'écrit **hors du dépôt**, par un chemin absolu : un chemin relatif le pose dans l'arbre
de travail, et le répertoire courant d'un agent ne tient pas d'un appel à l'autre.

Chaque réponse porte : **ce qui était juste dans le retour**, le sha de la correction, et **le
rayon d'action vérifié**. Un refus porte son argument et sa source.

Puis mettre à jour la **description de PR** si la correction la périme — c'est le cas dès qu'un
chiffre, un libellé ou un tableau y figure.

### Pièges d'outillage, tous payés

| Piège | Ce qu'il faut faire |
|---|---|
| zsh ne découpe pas les variables non quotées, et n'interprète pas `\n` entre guillemets | passer par un fichier, jamais par des arguments construits |
| une commande dont le texte cite `ALLOW_PUSH_MAIN`, `garde.pushMain`, `core.hooksPath`, ou `--no-verify` à côté du mot `push` — **corps de PR ou de commentaire passé en argument ou par heredoc compris** — est refusée par `garde-push` | écrire le fichier avec l'outil d'écriture, puis `--body-file` (`gh pr create`, `gh pr comment`) ou `-F body=@` (`gh api`) |
| un script d'édition qui échoue à mi-parcours écrit la moitié | `assert` sur chaque ancre, et relire le fichier après |
| une ancre qui tombe entre un bloc de doc et son symbole laisse le bloc orphelin — ni le lint, ni le typecheck, ni le `grep` ne le signalent | après l'insertion, relire ce qui précède l'ancre |
| éditer un hook actif : une erreur de syntaxe le casse pour la session, et il bloque les commandes suivantes | éditer une copie, `bash -n`, puis la mettre en place |
| un agent de review peut laisser l'arbre sur une autre branche | `git branch --show-current` avant de reprendre |

---

## 5. Terminer en énumérant ce que la review a trouvé

**C'est l'étape que ce skill existe pour garantir.** Elle se fait à la fin, dans le message à
l'utilisateur, et elle vient **avant** tout ce qui concerne les corrections.

### Ce qu'il faut écrire

Un bloc par retour, dans les mots du **problème**, jamais dans ceux du correctif :

```
**🟠 <ce que le code fait de faux>** — <le chemin qui y mène, et ce qu'il produit>.
```

⚠️ **Le piège est de raconter sa propre réponse.** « J'ai ajouté un test à deux villes » suppose
connu le défaut qu'on n'a pas énoncé. « Le regroupement n'était tenu par aucun test » se lit.

### Le squelette

1. **un bloc par retour**, sévérité en tête, le défaut énoncé ;
2. **les ✅** que la review a vérifiés — ils disent ce qui a été regardé et tient ;
3. **une ligne de corrections**, courte : sha + ce qui a changé ;
4. **les vérifications** : la commande lancée et ce qu'elle a rendu, le nombre de tests, les
   mutations posées ;
5. **ce qui reste ouvert**, et ce qui part en ticket.

Sur plusieurs passes, une section par passe, puis un total.

### À dire explicitement, sans le noyer

- un retour qui contredit une affirmation qu'on a soi-même écrite ;
- un test à soi qui passait pour de mauvaises raisons ;
- un chiffre à soi que la review a redérivé faux ;
- un refus de suggestion, avec son argument.

Ce sont les points que l'utilisateur ne peut pas retrouver ailleurs, et ceux qu'un compte rendu tourné
vers les corrections efface en premier.

---

## 6. Fusionner

**On fusionne quand plus aucun retour ne désigne un défaut atteignable dans le code tel qu'il
est.** Le reste part en tickets — **à une exception**, un écrit que *cette* pull request a
elle-même rendu faux, qui se corrige dedans. Un 📘 ne bloque donc jamais seul, sauf dans ce
cas-là.

⚠️ **Et quand l'attribution ne se tranche pas, on le dit.** Une attribution inventée envoie
corriger une dette qui n'est pas la sienne, ou laisse passer ce que la PR vient de casser.

⚠️ **Le périmètre d'une passe due ne se rétrécit pas aux fichiers de code.** Un diff qui ne touche
que des tests et des écrits se relit quand même : c'est ce que la catégorie 📘 existe pour
attraper. Seul un diff **purement mécanique** — un renommage, un déplacement sans réécriture — ne
mérite pas sa passe.

⛔ **Demander la permission avant de fusionner, PR par PR.** Une phrase conditionnelle (« on merge
si c'est bon ») est un mandat de vérifier, pas une permission d'avance : si la vérification échoue,
le dire et ne pas fusionner.
