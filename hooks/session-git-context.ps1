# Hook SessionStart — affiche l'etat git du depot au demarrage de la session.

if (-not (Test-Path '.git')) { exit 0 }

Write-Output "Branche : $(git branch --show-current)"
Write-Output ""
Write-Output "Dernier commit :"
git log -1 --format="  %h - %s (%cr)"
Write-Output ""

$status = git status --short
if ($status) {
  Write-Output "Fichiers modifies :"
  $status | ForEach-Object { "  $_" }
  Write-Output ""
  Write-Output "Diff en attente :"
  git diff --stat | ForEach-Object { "  $_" }
  $staged = git diff --cached --stat
  if ($staged) {
    Write-Output "  (staged) :"
    $staged | ForEach-Object { "  $_" }
  }
} else {
  Write-Output "Working tree clean"
}
exit 0
