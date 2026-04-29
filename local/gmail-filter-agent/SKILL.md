---
name: gmail-filter-agent
description: AI-powered Gmail filtering agent that learns user preferences and sends important email notifications to Discord.
---

# Gmail Filter Agent

An intelligent email filtering system that uses machine learning to identify important unread emails and sends notifications to Discord. The agent learns from user feedback to improve its filtering accuracy over time.

## Features

- 🤖 **AI-Powered Filtering**: Uses machine learning to classify email importance
- 📧 **Gmail Integration**: Connects to Gmail API to monitor unread emails
- 💬 **OpenClaw Discord Integration**: Sends important emails through your existing OpenClaw Discord bot
- 🧠 **Learning System**: Improves accuracy based on user feedback
- 🔄 **Continuous Monitoring**: Runs in background checking emails periodically

## Setup

### 1. Gmail API Setup

Run the automated setup script:

```bash
./setup_gmail.sh
```

This will guide you through:
1. Google Cloud Console setup
2. Gmail API enablement
3. OAuth credentials creation
4. Credentials file placement

### 2. Discord Configuration

Your Discord bot is already configured! The agent will use:

- **Bot Token**: `YOUR_DISCORD_BOT_TOKEN`
- **Channel ID**: `1486134987525722233`

### 3. Test the Setup

Run the test script to verify everything works:

```bash
./test_agent.sh
```

This will test both Gmail API and Discord integration.

### 4. Install Dependencies

```bash
cd workspace/skills/local/gmail-filter-agent
pip install -r requirements.txt
```

## Usage

### Quick Test

Run the comprehensive test script:

```bash
./test_agent.sh
```

This will verify Gmail API and Discord integration, then send a test notification.

### Single Cycle Test

```bash
export DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN"
export DISCORD_CHANNEL_ID="1486134987525722233"
python3 scripts/gmail_filter_agent.py --test
```

### Continuous Monitoring

```bash
export DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN"
export DISCORD_CHANNEL_ID="1486134987525722233"
python3 scripts/gmail_filter_agent.py --continuous --interval 10
```

## How It Works

### AI Classification

The agent uses a machine learning model trained on email features:
- **Subject line analysis**
- **Sender information**
- **Email snippet/content preview**
- **Historical user feedback**

### Importance Scoring

Emails are scored from 0-1 for importance:
- **> 0.7**: High importance (sent to Discord)
- **0.4-0.7**: Medium importance (logged but not notified)
- **< 0.4**: Low importance (filtered out)

### Learning System

The agent improves over time by:
- Tracking which emails you mark as important
- Updating the ML model with user feedback
- Adapting to your email patterns and preferences

## Configuration

### Thresholds (in script)

```python
IMPORTANCE_THRESHOLD = 0.7  # Minimum score for Discord notification
MIN_CONFIDENCE = 0.6        # Minimum confidence in prediction
```

### Email Check Frequency

Default: 15 minutes (configurable with --interval)

## Troubleshooting

### Gmail Authentication Issues

- Ensure `credentials.json` is in `~/.credentials/gmail_credentials.json`
- Delete `gmail_token.pickle` if authentication fails
- Check Gmail API is enabled in Google Cloud Console

### Discord Issues

- Verify OpenClaw is properly connected to Discord
- Ensure `DISCORD_CHANNEL_ID` is set correctly
- Check that OpenClaw has permission to send messages in the channel
- Test OpenClaw connectivity: `openclaw agent --help`

### ML Model Issues

- Delete `gmail_filter_model.pickle` to reset to basic model
- Model will retrain automatically with new data

## Security Notes

- Credentials are stored locally in `~/.credentials/`
- Bot token should be kept secure
- Gmail access is read-only
- No email content is stored permanently