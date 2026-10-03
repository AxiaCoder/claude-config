#!/bin/bash
# Hook SessionStart — Charge le contexte git au démarrage
# Installation : ~/.claude/hooks/session-git-context.sh

# Seulement pour les repos git
if [ ! -d ".git" ]; then
  exit 0
fi

echo "📍 Branche : $(git branch --show-current)"
echo ""

echo "📝 Dernier commit :"
git log -1 --format="  %h — %s (%cr)"
echo ""

STATUS=$(git status --short)
if [ -n "$STATUS" ]; then
  echo "📂 Fichiers modifiés :"
  echo "$STATUS" | sed 's/^/  /'
  echo ""

  echo "📊 Diff en attente :"
  git diff --stat | sed 's/^/  /'
  STAGED=$(git diff --cached --stat)
  if [ -n "$STAGED" ]; then
    echo "  (staged) :"
    echo "$STAGED" | sed 's/^/  /'
  fi
else
  echo "📂 Working tree clean"
fi

exit 0