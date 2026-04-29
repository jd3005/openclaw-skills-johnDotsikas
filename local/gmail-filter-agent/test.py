#!/usr/bin/env python3
"""
Test script for Gmail Filter Agent
"""

import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from gmail_filter_agent import GmailFilterAgent

def test_ml_model():
    """Test the ML model with sample emails."""
    print("🧪 Testing ML Model...")

    agent = GmailFilterAgent()

    # Test emails
    test_emails = [
        "Urgent: Project deadline tomorrow",
        "Weekly newsletter from ACM",
        "Meeting invitation: Team standup",
        "Promotional offer: 50% off",
        "Security alert: Password changed",
        "Social media notification",
    ]

    print("\nEmail Importance Predictions:")
    print("-" * 50)

    for email_text in test_emails:
        importance, confidence = agent.predict_importance(email_text)
        status = "📧 IMPORTANT" if importance > 0.7 else "📝 NORMAL"
        print("2.2f"
    print("\n✅ ML Model test complete!")

def test_gmail_auth():
    """Test Gmail authentication."""
    print("\n🔐 Testing Gmail Authentication...")

    agent = GmailFilterAgent()

    if agent.authenticate_gmail():
        print("✅ Gmail authentication successful!")
        return True
    else:
        print("❌ Gmail authentication failed!")
        return False

def test_discord_auth():
    """Test OpenClaw Discord integration."""
    print("\n💬 Testing OpenClaw Discord Integration...")

    agent = GmailFilterAgent()

    if agent.authenticate_discord():
        print("✅ OpenClaw Discord integration available!")
        return True
    else:
        print("❌ OpenClaw Discord integration not available!")
        return False

def main():
    """Run all tests."""
    print("🚀 Gmail Filter Agent - Test Suite")
    print("=" * 40)

    # Test ML model
    test_ml_model()

    # Test authentications (optional)
    print("\nNote: Authentication tests require proper setup.")
    print("Run these manually after configuring credentials.")

    print("\n📋 Next Steps:")
    print("1. Run: bash setup.sh")
    print("2. Configure Gmail API credentials")
    print("3. Set DISCORD_CHANNEL_ID environment variable")
    print("4. Test: python3 scripts/gmail_filter_agent.py --test")

if __name__ == '__main__':
    main()