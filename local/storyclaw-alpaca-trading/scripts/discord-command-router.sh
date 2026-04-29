#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.openclaw/skills/local/storyclaw-alpaca-trading"
CMD="${*:-}"
LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')

if [[ "$LOWER" == *"turn auton on"* ]]; then
  jq '.autonomous = true' "$BASE_DIR/config.monitor.json" > "$BASE_DIR/config.monitor.json.tmp" && mv "$BASE_DIR/config.monitor.json.tmp" "$BASE_DIR/config.monitor.json"
  echo "✅ Autonomous mode is now **ON**. I will trade every 5 minutes."
  exit 0
fi

if [[ "$LOWER" == *"turn auton off"* ]]; then
  jq '.autonomous = false' "$BASE_DIR/config.monitor.json" > "$BASE_DIR/config.monitor.json.tmp" && mv "$BASE_DIR/config.monitor.json.tmp" "$BASE_DIR/config.monitor.json"
  echo "⏸ Autonomous mode is now **OFF**. I will ask for permission before trading."
  exit 0
fi

if [[ "$LOWER" == *"cash"* || "$LOWER" == *"portfolio"* || "$LOWER" == *"positions"* || "$LOWER" == *"invested"* || "$LOWER" == *"have in"* ]]; then
  node "$BASE_DIR/scripts/portfolio-qa.js" "$CMD"
  exit 0
fi

node "$BASE_DIR/scripts/resolve-pending-alert.js" "$CMD"
