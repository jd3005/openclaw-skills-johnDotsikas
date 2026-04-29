#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/john/.openclaw/skills/local/storyclaw-alpaca-trading"
USER_ID="john"
export USER_ID
TARGET="user:1485786023609761904"
OPENCLAW="/home/john/.npm-global/bin/openclaw"
AUTONOMOUS=$(jq -r '.autonomous' "$BASE_DIR/config.monitor.json")

echo "STEP: buy-scan"
BUY_OUTPUT=$(timeout 60s env USER_ID="$USER_ID" node "$BASE_DIR/scripts/monitor.js" 2>&1 || true)
echo "STEP: sell-scan"
SELL_OUTPUT=$(timeout 45s env USER_ID="$USER_ID" node "$BASE_DIR/scripts/positions-watch.js" 2>/dev/null || echo '[]')

echo "STEP: build-message"
MESSAGE=""
AUTO_LOG=""

if [[ -n "$BUY_OUTPUT" && "$BUY_OUTPUT" != "No trade ideas right now." && "$BUY_OUTPUT" != *"timed out"* ]]; then
  # Extract all (Symbol, Amount, Price) sets from the output
  # Pattern: Paper trade idea: SYMBOL ... Suggested size: $AMOUNT ... Entry idea: around $PRICE
  IDEAS=$(echo "$BUY_OUTPUT" | awk '
    /Paper trade idea: / { sym=$NF }
    /Suggested size: \$/ { amt=substr($NF, 2) }
    /Entry idea: around \$/ { prc=substr($NF, 2); print sym","amt","prc }
  ')

  for IDEA in $IDEAS; do
    SYMBOL=$(echo "$IDEA" | cut -d',' -f1)
    AMOUNT=$(echo "$IDEA" | cut -d',' -f2)
    PRICE=$(echo "$IDEA" | cut -d',' -f3)

    if [[ -n "$SYMBOL" && -n "$AMOUNT" ]]; then
      if [[ "$AUTONOMOUS" == "true" ]]; then
        echo "STEP: auto-buy ($SYMBOL)"
        BUY_RES=$(node "$BASE_DIR/scripts/trading.js" buy-amount "$SYMBOL" "$AMOUNT" 2>&1 || true)
        if [[ "$BUY_RES" == *"Order submitted"* ]]; then
          AUTO_LOG+="✅ **Bought**: \$${AMOUNT} of ${SYMBOL} (Price: ${PRICE})\n"
        else
          if [[ "$BUY_RES" != *"already have"* ]]; then
            AUTO_LOG+="❌ **Failed ${SYMBOL}**: ${BUY_RES}\n"
          fi
        fi
      else
        # For manual mode, we just handle the first one for the pending system
        if [[ -z "$MESSAGE" ]]; then
          node "$BASE_DIR/scripts/save-pending-alert.js" "$SYMBOL" "$AMOUNT" "$PRICE" "70" >/dev/null 2>&1 || true
          MESSAGE+="📈 Paper trade alert\n\n$BUY_OUTPUT\n\nReply with 'place it' to execute."
        fi
      fi
    fi
  done
  
  if [[ "$AUTONOMOUS" == "true" ]]; then
    if [[ -n "$AUTO_LOG" ]]; then
      MESSAGE+="🤖 **Autonomous Mode Actions**\n\n"
    fi
  fi
fi

if [[ "$SELL_OUTPUT" != "[]" && -n "$SELL_OUTPUT" ]]; then
  # Handle multiple sells in autonomous mode
  if [[ "$AUTONOMOUS" == "true" ]]; then
    echo "STEP: auto-sell-loop"
    SYMBOLS=$(echo "$SELL_OUTPUT" | jq -r '.[].symbol')
    for S in $SYMBOLS; do
      QTY=$(echo "$SELL_OUTPUT" | jq -r ".[] | select(.symbol==\"$S\") | .qty")
      REASON=$(echo "$SELL_OUTPUT" | jq -r ".[] | select(.symbol==\"$S\") | .reason")
      echo "STEP: auto-sell ($S)"
      SELL_RES=$(node "$BASE_DIR/scripts/trading.js" sell "$S" "$QTY" 2>&1 || true)
      if [[ "$SELL_RES" == *"Order submitted"* ]]; then
        AUTO_LOG+="✅ **Sold**: ${S} (${QTY} units) - ${REASON}\n"
      else
        AUTO_LOG+="❌ **Failed to Sell ${S}**: ${SELL_RES}\n"
      fi
    done
  else
    # In manual mode, just handle the first one for the pending system
    FIRST_S=$(echo "$SELL_OUTPUT" | jq -r '.[0].symbol')
    FIRST_Q=$(echo "$SELL_OUTPUT" | jq -r '.[0].qty')
    node "$BASE_DIR/scripts/save-pending-sell.js" "$FIRST_S" "$FIRST_Q" >/dev/null 2>&1 || true
    
    SELL_TEXT=$(SELL_OUTPUT="$SELL_OUTPUT" python3 - <<'PY'
import json, os
items = json.loads(os.environ.get('SELL_OUTPUT', '[]'))
first = items[0]
print(f"📉 Sell idea: {first['symbol']}\nQty: {first['qty']}\nWhy: {first['reason']}\nP&L: {first['pnlPct']:.2f}%")
PY
)
    if [[ -n "$MESSAGE" ]]; then MESSAGE+="\n\n---\n\n"; fi
    MESSAGE+="$SELL_TEXT\nReply with 'sell it' to execute."
  fi
fi

if [[ -n "$AUTO_LOG" ]]; then
  MESSAGE+="$AUTO_LOG"
fi

if [[ -z "$MESSAGE" ]]; then
  echo "STEP: no-message"
  # Optional: only send "no ideas" once an hour instead of every 5 mins to reduce spam
  MINUTE=$(date +%M)
  if [[ "$MINUTE" == "00" || "$MINUTE" == "05" || "$AUTONOMOUS" != "true" ]]; then
    STATUS_PRE="📊 Alpaca monitor"
    if [[ "$AUTONOMOUS" == "true" ]]; then STATUS_PRE="🤖 Autonomous monitor"; fi
    MESSAGE="$STATUS_PRE: no active recommendations right now."
  else
    exit 0 # Silent exit for most 5-min intervals if nothing happened
  fi
fi

echo "STEP: send-discord"
"$OPENCLAW" message send --channel discord --target "$TARGET" --message "$MESSAGE"
