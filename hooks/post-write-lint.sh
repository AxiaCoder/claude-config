#!/bin/bash
# Hook PostToolUse — Lint automatique après chaque écriture
# Installation : ~/.claude/hooks/post-write-lint.sh

# Seulement pour les projets AdonisJS
if [ ! -f "adonisrc.ts" ]; then
  exit 0
fi

LINT_OUTPUT=$(pnpm lint --quiet 2>&1)
if [ $? -ne 0 ]; then
  echo "❌ Lint failed — corrige avant de continuer" >&2
  echo "$LINT_OUTPUT" >&2
  exit 2
fi

exit 0