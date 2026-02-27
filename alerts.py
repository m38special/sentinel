"""
Alert hooks for SENTINEL - Slack + Telegram
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

# Slack bot token (xoxb-...) + channel ID
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN', '')
SLACK_CHANNEL_ID = os.getenv('SLACK_CHANNEL_ID', '')  # e.g., C0AHE2LQFRC for #idea-ocean
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


def send_slack_alert(message: str) -> bool:
    """Send Slack alert via bot API (not webhook)"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.debug("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not set")
        return False
    try:
        url = "https://slack.com/api/chat.postMessage"
        resp = requests.post(url, json={
            'channel': SLACK_CHANNEL_ID,
            'text': message,
            'unfurl_links': False
        }, headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if not body.get('ok'):
            logger.error(f"Slack API error: {body.get('error', 'unknown')}")
            return False
        return True
    except Exception as e:
        logger.error(f"Slack alert failed: {e}")
        return False


def send_telegram_alert(message: str) -> bool:
    """F-04, F-12: Verify delivery, scrub token from logs"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("TELEGRAM credentials not set")
        return False
    # F-12: Mask token before any logging
    safe_token = TELEGRAM_BOT_TOKEN[:8] + "..."
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if not body.get('ok'):
            logger.error(f"Telegram API error: {body.get('description', 'unknown')}")
            return False
        return True
    except Exception as e:
        # F-12: Don't log URL with token
        logger.error(f"Telegram alert failed (token masked {safe_token}): {type(e).__name__}")
        return False
