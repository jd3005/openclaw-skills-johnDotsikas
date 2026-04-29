#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.agents/skills/storyclaw-alpaca-trading"
CMD="${*:-}"
LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')

if [[ "$LOWER" == *"cash"* || "$LOWER" == *"portfolio"* || "$LOWER" == *"positions"* || "$LOWER" == *"invested"* || "$LOWER" == *"have in"* ]]; then
  node "$BASE_DIR/scripts/portfolio-qa.js" "$CMD"
  exit 0
fi

node "$BASE_DIR/scripts/resolve-pending-alert.js" "$CMD"
