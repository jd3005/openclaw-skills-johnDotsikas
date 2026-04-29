#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.openclaw/skills/local/storyclaw-alpaca-trading"
STATE_DIR="$BASE_DIR/state"
STATE_FILE="$STATE_DIR/discord-reply-offset.txt"
SESSION_FILE=$(ls -t /home/john/.openclaw/agents/main/sessions/*.jsonl | head -n 1)
mkdir -p "$STATE_DIR"
LAST_TS="0"
if [[ -f "$STATE_FILE" ]]; then
  LAST_TS=$(cat "$STATE_FILE")
fi

if [[ -z "$SESSION_FILE" || ! -f "$SESSION_FILE" ]]; then
  exit 0
fi

PAYLOAD=$(python3 - <<'PY'
import json, glob, os
from pathlib import Path
sessions = glob.glob('/home/john/.openclaw/agents/main/sessions/*.jsonl')
if not sessions:
    exit(0)
session = Path(max(sessions, key=os.path.getmtime))
last_ts = int(Path('/home/john/.openclaw/skills/local/storyclaw-alpaca-trading/state/discord-reply-offset.txt').read_text().strip()) if Path('/home/john/.openclaw/skills/local/storyclaw-alpaca-trading/state/discord-reply-offset.txt').exists() else 0
best = None
for line in session.read_text().splitlines():
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('type') != 'message':
        continue
    msg = obj.get('message', {})
    if msg.get('role') != 'user':
        continue
    ts = obj.get('timestamp', '')
    txts = []
    for c in msg.get('content', []):
        if c.get('type') == 'text':
            txts.append(c.get('text', ''))
    text = '\n'.join(txts).strip()
    if 'Sender (untrusted metadata):' not in text:
        continue
    if '[Wed' not in text and 'Conversation info' not in text:
        continue
    # prefer newest user text entry after offset
    ms = int(obj.get('message', {}).get('timestamp', 0) or 0)
    if ms <= last_ts:
        continue
    best = {'ts': ms, 'text': text}
if best:
    print(json.dumps(best))
PY
)

if [[ -z "$PAYLOAD" ]]; then
  exit 0
fi

TEXT=$(PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json, os, re
payload = json.loads(os.environ['PAYLOAD'])
text = payload['text']
lines = [line.strip() for line in text.splitlines() if line.strip()]
content = lines[-1] if lines else ''
print(content)
PY
)

TS=$(PAYLOAD="$PAYLOAD" python3 - <<'PY'
import json, os
payload = json.loads(os.environ['PAYLOAD'])
print(payload['ts'])
PY
)

RESULT=$("$BASE_DIR/scripts/discord-command-router.sh" "$TEXT" 2>&1 || true)
if [[ "$RESULT" == "UNRECOGNIZED_REPLY" || "$RESULT" == "UNRECOGNIZED_PORTFOLIO_QUESTION" || "$RESULT" == NO_PENDING_* ]]; then
  printf '%s' "$TS" > "$STATE_FILE"
  exit 0
fi

printf '%s' "$TS" > "$STATE_FILE"
openclaw message send --channel discord --target user:1485786023609761904 --message "$RESULT"
