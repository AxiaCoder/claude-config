---
name: nettoyer-les-worktrees
description: Use right after merging a pull request, and whenever a worktree you created is no longer needed — to remove it with its local branch, and to sweep the repository for worktrees left behind by other sessions or the other machine. Carries the removal commands, the rule that a refused removal is reported and never forced, and the sweep to run after every merge. Do not use to decide whether to create a worktree — that rule stays in CLAUDE.md § Une autre session sur le même dépôt.
---

# Nettoyer les worktrees

⚠️ **Un worktree se retire dès qu'il ne sert plus** — par la session qui l'a créé, avec sa branche
locale : `git worktree remove --force <dossier>`, puis `git branch -D` une fois la PR `MERGED` selon
`gh pr view` (après un squash, `-d` refuse la branche comme non fusionnée). Sinon il traîne : six
trouvés le 29/09, dont aucun n'avait plus d'usage.

⇒ **Toute session qui merge balaie le dépôt**, pas seulement sa PR : pour chaque entrée de
`git worktree list` hors de l'arbre principal, `gh pr view <branche>` ; `MERGED` ou `CLOSED` → elle
la retire **sans `--force`**, puis sa branche locale. ⛔ Un refus de `git worktree remove` se
rapporte, il ne se force pas : ce worktree porte des changements non commités, peut-être ceux d'une
session encore active. C'est ce qui rattrape le worktree d'une PR mergée depuis une autre
session ou l'autre machine. 📌 Une session ne voit que les worktrees de sa machine : celui du Windows
mergé depuis le Mac part au prochain merge sur le Windows, dans ce dépôt.
