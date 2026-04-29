#!/bin/bash

# Gmail Filter Agent - Gmail API Setup Script
# This script helps you set up Gmail API credentials for the agent

echo "🔧 Gmail Filter Agent - Gmail API Setup"
echo "========================================"
echo ""
echo "To use the Gmail Filter Agent, you need to set up Gmail API access:"
echo ""
echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Create a new project or select an existing one"
echo "3. Enable the Gmail API:"
echo "   - Go to 'APIs & Services' > 'Library'"
echo "   - Search for 'Gmail API' and enable it"
echo "4. Create OAuth 2.0 credentials:"
echo "   - Go to 'APIs & Services' > 'Credentials'"
echo "   - Click 'Create Credentials' > 'OAuth 2.0 Client IDs'"
echo "   - Choose 'Desktop application' as application type"
echo "   - Download the credentials JSON file"
echo "5. Save the downloaded file as 'credentials/credentials.json' in this directory"
echo ""
echo "Once you have the credentials.json file, run this script again to test the setup."
echo ""

# Check if credentials file exists
if [ -f "credentials/credentials.json" ]; then
    echo "✅ Found credentials.json file"
    echo ""
    echo "Testing Gmail API authentication..."

    # Test the credentials
    python3 -c "
import os
import sys
sys.path.append('scripts')

try:
    from gmail_filter_agent import authenticate_gmail
    print('🔐 Attempting Gmail authentication...')
    service = authenticate_gmail()
    if service:
        print('✅ Gmail API authentication successful!')
        print('📧 Gmail Filter Agent is ready to use!')
    else:
        print('❌ Gmail authentication failed')
        print('Please check your credentials.json file')
except Exception as e:
    print(f'❌ Error during authentication: {e}')
    print('Make sure credentials.json is valid and you have authorized the application')
"
else
    echo "❌ credentials.json not found in credentials/ directory"
    echo ""
    echo "Please follow the steps above to obtain your Gmail API credentials."
fi

echo ""
echo "For more information, see the SKILL.md file in this directory."