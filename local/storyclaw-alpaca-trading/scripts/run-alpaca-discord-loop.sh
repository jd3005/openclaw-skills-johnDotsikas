#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.openclaw/skills/local/storyclaw-alpaca-trading"
"$BASE_DIR/scripts/monitor-and-notify.sh" || true
"$BASE_DIR/scripts/check-discord-replies.sh" || true
