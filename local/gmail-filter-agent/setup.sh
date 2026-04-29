#!/bin/bash
set -euo pipefail

echo "🚀 Gmail Filter Agent Setup"
echo "============================"

# Check if credentials directory exists
CREDENTIALS_DIR="$HOME/.credentials"
if [[ ! -d "$CREDENTIALS_DIR" ]]; then
    echo "Creating credentials directory: $CREDENTIALS_DIR"
    mkdir -p "$CREDENTIALS_DIR"
fi

# Check for Gmail credentials
GMAIL_CREDS="$CREDENTIALS_DIR/gmail_credentials.json"
if [[ ! -f "$GMAIL_CREDS" ]]; then
    echo ""
    echo "❌ Gmail credentials not found!"
    echo "Please:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create OAuth 2.0 credentials for Gmail API"
    echo "3. Download credentials.json"
    echo "4. Save as: $GMAIL_CREDS"
    echo ""
    echo "Press Enter when done..."
    read -r
fi

# Check environment variables
echo ""
echo "Checking Discord configuration..."

if [[ -n "${DISCORD_WEBHOOK_URL:-}" ]]; then
    echo "✅ DISCORD_WEBHOOK_URL is set"
elif [[ -n "${DISCORD_BOT_TOKEN:-}" && -n "${DISCORD_CHANNEL_ID:-}" ]]; then
    echo "✅ DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID are set"
else
    echo "❌ Discord not configured"
    echo "Choose one option:"
    echo "1) Webhook (easiest): export DISCORD_WEBHOOK_URL='your_webhook_url'"
    echo "2) Bot Token: export DISCORD_BOT_TOKEN='token' && export DISCORD_CHANNEL_ID='channel_id'"
fi

# Check OpenClaw availability
echo ""
echo "Checking OpenClaw status..."
if openclaw gateway status &>/dev/null; then
    echo "✅ OpenClaw gateway is running"
else
    echo "⚠️  OpenClaw gateway not running - start with 'openclaw gateway start'"
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Test the agent:"
echo "python3 scripts/gmail_filter_agent.py --test"
echo ""
echo "Run continuous monitoring:"
echo "python3 scripts/gmail_filter_agent.py --continuous"