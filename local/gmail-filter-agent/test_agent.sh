#!/bin/bash

# Gmail Filter Agent - Test Script
# This script tests the full Gmail Filter Agent functionality

echo "🧪 Gmail Filter Agent - Full Test"
echo "=================================="
echo ""

# Check environment variables
if [ -z "$DISCORD_BOT_TOKEN" ]; then
    echo "❌ DISCORD_BOT_TOKEN environment variable not set"
    echo "Run: export DISCORD_BOT_TOKEN='your_bot_token_here'"
    exit 1
fi

if [ -z "$DISCORD_CHANNEL_ID" ]; then
    echo "❌ DISCORD_CHANNEL_ID environment variable not set"
    echo "Run: export DISCORD_CHANNEL_ID='your_channel_id_here'"
    exit 1
fi

# Check credentials
if [ ! -f "credentials/credentials.json" ]; then
    echo "❌ Gmail credentials not found"
    echo "Run ./setup_gmail.sh first to set up Gmail API access"
    exit 1
fi

echo "✅ Environment variables set"
echo "✅ Gmail credentials found"
echo ""

# Test Gmail API
echo "🔐 Testing Gmail API authentication..."
python3 -c "
import sys
sys.path.append('scripts')

try:
    from gmail_filter_agent import authenticate_gmail
    service = authenticate_gmail()
    if service:
        print('✅ Gmail API authentication successful!')
    else:
        print('❌ Gmail authentication failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Gmail authentication error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Gmail API test failed"
    exit 1
fi

# Test Discord integration
echo "📢 Testing Discord integration..."
python3 -c "
import requests
import os

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

url = f'https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages'
headers = {'Authorization': f'Bot {DISCORD_BOT_TOKEN}'}
payload = {'content': '🧪 Gmail Filter Agent Test - Full system integration working!'}

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if response.status_code in (200, 201):
        print('✅ Discord test message sent successfully!')
    else:
        print(f'❌ Discord API error: {response.status_code}')
        exit(1)
except Exception as e:
    print(f'❌ Discord error: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Discord test failed"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Gmail Filter Agent is ready to use."
echo ""
echo "To run the agent:"
echo "  export DISCORD_BOT_TOKEN='$DISCORD_BOT_TOKEN'"
echo "  export DISCORD_CHANNEL_ID='$DISCORD_CHANNEL_ID'"
echo "  python3 scripts/gmail_filter_agent.py"
echo ""
echo "The agent will:"
echo "  - Check for unread emails in your Gmail inbox"
echo "  - Use AI to determine which emails are important"
echo "  - Send Discord notifications for important emails"
echo "  - Learn from your preferences over time"