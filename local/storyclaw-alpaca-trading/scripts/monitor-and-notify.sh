#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.openclaw/skills/local/storyclaw-alpaca-trading"
USER_ID="john"
TARGET="user:1485786023609761904"
OPENCLAW="/home/john/.npm-global/bin/openclaw"

echo "STEP: buy-scan"
BUY_OUTPUT=$(timeout 45s env USER_ID="$USER_ID" node "$BASE_DIR/scripts/monitor.js" 2>&1 || true)
echo "STEP: sell-scan"
SELL_OUTPUT=$(timeout 45s env USER_ID="$USER_ID" node "$BASE_DIR/scripts/positions-watch.js" 2>/dev/null || echo '[]')

echo "STEP: build-message"
MESSAGE=""

if [[ -n "$BUY_OUTPUT" && "$BUY_OUTPUT" != "No trade ideas right now." && "$BUY_OUTPUT" != *"timed out"* ]]; then
  FIRST_SYMBOL=$(printf '%s\n' "$BUY_OUTPUT" | sed -n 's/^Paper trade idea: //p' | head -n1)
  FIRST_AMOUNT=$(printf '%s\n' "$BUY_OUTPUT" | sed -n 's/^Suggested size: \$//p' | head -n1)
  FIRST_PRICE=$(printf '%s\n' "$BUY_OUTPUT" | sed -n 's/^Entry idea: around \$//p' | head -n1)
  FIRST_SCORE=$(printf '%s\n' "$BUY_OUTPUT" | sed -n 's/^Confidence: .* (\([0-9][0-9]*\))$/\1/p' | head -n1)
  if [[ -n "$FIRST_SYMBOL" && -n "$FIRST_AMOUNT" ]]; then
    node "$BASE_DIR/scripts/save-pending-alert.js" "$FIRST_SYMBOL" "$FIRST_AMOUNT" "$FIRST_PRICE" "$FIRST_SCORE" >/dev/null 2>&1 || true
  fi
  MESSAGE+="📈 Paper trade alert\n\n$BUY_OUTPUT\n\nReply with one of these:\n- place it\n- don't place it\n- skip this one"
fi

if [[ "$SELL_OUTPUT" != "[]" && -n "$SELL_OUTPUT" ]]; then
  FIRST_SELL_SYMBOL=$(SELL_OUTPUT="$SELL_OUTPUT" python3 -c 'import json, os; items=json.loads(os.environ.get("SELL_OUTPUT", "[]")); print(items[0]["symbol"] if items else "")')
  FIRST_SELL_QTY=$(SELL_OUTPUT="$SELL_OUTPUT" python3 -c 'import json, os; items=json.loads(os.environ.get("SELL_OUTPUT", "[]")); print(items[0]["qty"] if items else "")')
  if [[ -n "$FIRST_SELL_SYMBOL" && -n "$FIRST_SELL_QTY" ]]; then
    node "$BASE_DIR/scripts/save-pending-sell.js" "$FIRST_SELL_SYMBOL" "$FIRST_SELL_QTY" >/dev/null 2>&1 || true
  fi
  SELL_TEXT=$(SELL_OUTPUT="$SELL_OUTPUT" python3 - <<'PY'
import json, os
items = json.loads(os.environ.get('SELL_OUTPUT', '[]'))
if not items:
    print('')
else:
    first = items[0]
    projected_giveback = max(first['pnlPct'] * 0.35, 2.0)
    print(
        "📉 Sell idea\n\n"
        f"Symbol: {first['symbol']}\n"
        f"Qty held: {first['qty']}\n"
        f"Why I want to sell: {first['reason']}\n"
        f"Current gain/loss: {first['pnlPct']:.2f}%\n"
        f"Projected reason to act: if momentum fades, you could give back roughly {projected_giveback:.2f}% of the move.\n"
        "Why sell it now: the setup looks stretched enough that protecting gains is reasonable.\n"
        "Manual vs auto: you can sell it yourself, or I can do it for you.\n\n"
        "Reply with one of these:\n"
        "- sell it\n"
        "- i'll do it manually\n"
        "- skip this one"
    )
PY
)
  if [[ -n "$SELL_TEXT" ]]; then
    if [[ -n "$MESSAGE" ]]; then
      MESSAGE+="\n\n---\n\n"
    fi
    MESSAGE+="$SELL_TEXT"
  fi
fi

if [[ -z "$MESSAGE" ]]; then
  echo "STEP: no-message"
  MESSAGE="📊 Alpaca monitor check complete — no buy or sell recommendations found right now."
fi

echo "STEP: send-discord"
"$OPENCLAW" message send --channel discord --target "$TARGET" --message "$MESSAGE"
