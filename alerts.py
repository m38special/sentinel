"""
Alert hooks for SENTINEL - Slack + Telegram
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


def send_slack_alert(message: str) -> bool:
    """F-04: Verify alert delivery - HTTP status AND ok field"""
    if not SLACK_WEBHOOK_URL:
        logger.debug("SLACK_WEBHOOK_URL not set")
        return False
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={'text': message, 'unfurl_links': False}, timeout=10)
        resp.raise_for_status()
        # F-04: Check Slack's {"ok": false} response
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
