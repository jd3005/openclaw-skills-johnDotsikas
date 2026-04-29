#!/usr/bin/env python3
"""
Gmail Filter Agent - Automatically filters important unread emails and sends Discord notifications.

This skill:
1. Connects to Gmail API to check unread emails
2. Uses AI to determine email importance
3. Sends important emails to Discord
4. Learns from user feedback to improve filtering
"""

import json
import os
import pickle
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Discord bot token and channel ID (for OpenClaw integration)
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID', '')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')  # Alternative: use webhook instead of bot token

# Gmail credentials path
CREDENTIALS_PATH = os.path.expanduser('~/.credentials/gmail_credentials.json')
TOKEN_PATH = os.path.expanduser('~/.credentials/gmail_token.pickle')

# ML model path
MODEL_PATH = os.path.expanduser('~/.credentials/gmail_filter_model.pickle')

# Email importance thresholds
IMPORTANCE_THRESHOLD = 0.7
MIN_CONFIDENCE = 0.6


class GmailFilterAgent:
    """AI-powered Gmail filtering agent that learns user preferences."""

    def __init__(self):
        self.service = None
        self.ml_model = None
        self.vectorizer = None
        self.load_ml_model()

    def authenticate_gmail(self) -> bool:
        """Authenticate with Gmail API."""
        creds = None

        # Load existing token if available
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)

        # Refresh or get new credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_PATH):
                    print("Error: Gmail credentials file not found. Please download from Google Cloud Console.")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            print(f"Gmail authentication failed: {e}")
            return False

    def authenticate_discord(self) -> bool:
        """Check if Discord is configured via webhook or bot token."""
        if DISCORD_WEBHOOK_URL:
            print("Discord webhook configured.")
            return True
        
        if DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID:
            print("Discord bot token configured.")
            return True

        print("Error: Neither DISCORD_WEBHOOK_URL nor (DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID) is configured.")
        return False

    def load_ml_model(self):
        """Load or create ML model for email importance classification."""
        try:
            if os.path.exists(MODEL_PATH):
                with open(MODEL_PATH, 'rb') as f:
                    self.ml_model = pickle.load(f)
                print("Loaded existing ML model.")
            else:
                # Create initial model with basic training data
                self.initialize_ml_model()
        except Exception as e:
            print(f"Error loading ML model: {e}")
            self.initialize_ml_model()

    def initialize_ml_model(self):
        """Initialize ML model with basic training examples."""
        # Basic training data - important vs unimportant emails
        training_emails = [
            # Important emails
            "Urgent: Project deadline approaching",
            "Meeting invitation: Team standup tomorrow",
            "Invoice payment due",
            "Job application response",
            "Security alert for your account",
            "Package delivery notification",
            "Doctor appointment confirmation",
            "Bank statement available",

            # Unimportant emails
            "Weekly newsletter",
            "Promotional offer",
            "Social media notification",
            "Spam advertisement",
            "Marketing email",
            "Unsubscribe reminder",
            "Daily digest",
        ]

        training_labels = [1] * 8 + [0] * 7  # 1=important, 0=unimportant

        # Create and train pipeline
        self.ml_model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
            ('classifier', MultinomialNB())
        ])

        self.ml_model.fit(training_emails, training_labels)

        # Save model
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.ml_model, f)

        print("Initialized new ML model with basic training data.")

    def extract_email_features(self, email_data: Dict) -> str:
        """Extract relevant features from email for ML classification."""
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        snippet = email_data.get('snippet', '')

        # Combine features for classification
        features = f"{subject} {sender} {snippet}"
        return features

    def predict_importance(self, email_features: str) -> Tuple[float, float]:
        """Predict if email is important using ML model."""
        try:
            # Get prediction probabilities
            probabilities = self.ml_model.predict_proba([email_features])[0]
            importance_prob = probabilities[1]  # Probability of being important
            confidence = max(probabilities)  # Confidence in prediction

            return importance_prob, confidence
        except Exception as e:
            print(f"Error predicting importance: {e}")
            return 0.5, 0.5  # Default to neutral

    def get_unread_emails(self, max_results: int = 50) -> List[Dict]:
        """Fetch unread emails from Gmail."""
        try:
            # Get unread messages
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From']
                ).execute()

                # Extract email data
                headers = msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                snippet = msg.get('snippet', '')

                email_data = {
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'snippet': snippet,
                    'timestamp': msg.get('internalDate', '')
                }

                emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    def filter_important_emails(self, emails: List[Dict]) -> List[Dict]:
        """Filter emails using ML model to find important ones."""
        important_emails = []

        for email in emails:
            features = self.extract_email_features(email)
            importance_prob, confidence = self.predict_importance(features)

            email['importance_score'] = importance_prob
            email['confidence'] = confidence

            # Consider email important if:
            # - Importance probability > threshold AND confidence > minimum
            if importance_prob > IMPORTANCE_THRESHOLD and confidence > MIN_CONFIDENCE:
                important_emails.append(email)
                print(f"✓ Important: {email['subject']} (score: {importance_prob:.2f})")
            else:
                print(f"✗ Unimportant: {email['subject']} (score: {importance_prob:.2f})")

        return important_emails

    def format_discord_message(self, email: Dict) -> str:
        """Format email data for Discord message."""
        subject = email['subject']
        sender = email['sender']
        snippet = email['snippet'][:200] + "..." if len(email['snippet']) > 200 else email['snippet']
        score = email.get('importance_score', 0)

        message = f"📧 **Important Email Detected**\n"
        message += f"**Subject:** {subject}\n"
        message += f"**From:** {sender}\n"
        message += f"**Preview:** {snippet}\n"
        message += f"**Importance Score:** {score:.2f}\n"
        message += f"**Link:** https://mail.google.com/mail/u/0/#inbox/{email['id']}"

        return message

    def send_discord_notification(self, email: Dict):
        """Send email notification to Discord via webhook or bot token."""
        try:
            message = self.format_discord_message(email)

            if DISCORD_WEBHOOK_URL:
                # Send via webhook (simplest method)
                payload = {"content": message}
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
                if response.status_code in (200, 204):
                    print(f"Sent notification via webhook for: {email['subject']}")
                else:
                    print(f"Failed to send via webhook: {response.status_code}")

            elif DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID:
                # Send via Discord REST API
                url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
                headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
                payload = {"content": message}
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                if response.status_code in (200, 201):
                    print(f"Sent notification via Discord API for: {email['subject']}")
                else:
                    error_msg = response.text if response.text else f"Status {response.status_code}"
                    print(f"Failed to send via Discord API: {error_msg}")

        except requests.exceptions.Timeout:
            print("Timeout sending notification")
        except Exception as e:
            print(f"Error sending notification: {e}")

    def update_ml_model(self, email_features: str, is_important: bool):
        """Update ML model with user feedback."""
        try:
            # Get current training data (this is simplified - in production you'd store historical data)
            label = 1 if is_important else 0

            # Partial fit the model (if supported)
            if hasattr(self.ml_model.named_steps['classifier'], 'partial_fit'):
                # Convert features and fit
                features_transformed = self.ml_model.named_steps['tfidf'].transform([email_features])
                self.ml_model.named_steps['classifier'].partial_fit(features_transformed, [label])

                # Save updated model
                with open(MODEL_PATH, 'wb') as f:
                    pickle.dump(self.ml_model, f)

                print(f"Updated ML model with feedback (important={is_important})")
            else:
                print("Model doesn't support online learning.")

        except Exception as e:
            print(f"Error updating ML model: {e}")

    def run_cycle(self):
        """Run one complete filtering cycle."""
        print(f"Starting Gmail filter cycle at {datetime.now()}")

        # Authenticate services
        if not self.authenticate_gmail():
            print("Gmail authentication failed.")
            return

        if not self.authenticate_discord():
            print("OpenClaw Discord integration not available.")
            return

        # Get unread emails
        emails = self.get_unread_emails()
        print(f"Found {len(emails)} unread emails.")

        if not emails:
            print("No unread emails to process.")
            return

        # Filter important emails
        important_emails = self.filter_important_emails(emails)

        # Send notifications
        for email in important_emails:
            self.send_discord_notification(email)

        print(f"Processed {len(emails)} emails, found {len(important_emails)} important ones.")

    def run_continuous(self, interval_minutes: int = 15):
        """Run continuous monitoring with specified interval."""
        print(f"Starting continuous Gmail monitoring (check every {interval_minutes} minutes)")

        # Run initial cycle
        self.run_cycle()

        # Schedule periodic checks
        while True:
            time.sleep(interval_minutes * 60)
            self.run_cycle()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Gmail Filter Agent')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=15,
                       help='Check interval in minutes (default: 15)')
    parser.add_argument('--test', action='store_true',
                       help='Run single test cycle')

    args = parser.parse_args()

    agent = GmailFilterAgent()

    if args.test:
        # Run single test cycle
        agent.run_cycle()
    elif args.continuous:
        agent.run_continuous(args.interval)
    else:
        print("Use --test for single run or --continuous for monitoring")
        print("\nRequired environment variables:")
        print("Option 1 - Webhook (easiest):")
        print("  export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print("\nOption 2 - Bot Token:")
        print("  export DISCORD_BOT_TOKEN='your_bot_token'")
        print("  export DISCORD_CHANNEL_ID='1486134987525722233'")
        print("\nSetup Gmail API:")
        print("1. Go to Google Cloud Console")
        print("2. Create OAuth 2.0 credentials")
        print("3. Download credentials.json to ~/.credentials/gmail_credentials.json")


if __name__ == '__main__':
    main()