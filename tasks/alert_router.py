"""
tasks/alert_router.py — Alert Routing
SENTINEL Phase 2 | LiQUiD SOUND

Routes high-score token alerts to notification channels.
Deduplication via Redis SET with TTL.

Routing thresholds (from .env):
  ALERT_THRESHOLD_SLACK=70    → Slack #sentinel-alerts
  ALERT_THRESHOLD_ALL=85      → Slack + Discord
  ALERT_THRESHOLD_URGENT=95   → All channels + Telegram urgent

Approval gate:
  score >= 85 → "Yoruichi approval gate" badge in Slack message
  Approval state tracked in Redis with 24h TTL
"""
import os
import json
import logging
import structlog
from datetime import datetime, timezone
from typing import Any

import redis as redis_client
from tasks import app

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
REDIS_URL           = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SLACK_BOT_TOKEN     = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_ALERT_CHANNEL = os.getenv("SLACK_ALERT_CHANNEL", "C0AHE2LQFRC")
DEDUP_TTL_SECONDS   = 300   # 5 min dedup window

THRESHOLD_SLACK     = float(os.getenv("ALERT_THRESHOLD_SLACK", "70"))
THRESHOLD_ALL       = float(os.getenv("ALERT_THRESHOLD_ALL_CHANNELS", "85"))
THRESHOLD_URGENT    = float(os.getenv("ALERT_THRESHOLD_URGENT", "95"))

# ─────────────────────────────────────────────
# Redis client (for dedup)
# ─────────────────────────────────────────────
_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = redis_client.from_url(REDIS_URL, decode_responses=True)
    return _redis


def is_duplicate(mint: str, score: float) -> bool:
    """Check if we already alerted on this token recently."""
    key = f"sentinel:alert:dedup:{mint}"
    r = get_redis()
    if r.exists(key):
        log.debug("alert_dedup_skip", mint=mint)
        return True
    r.setex(key, DEDUP_TTL_SECONDS, str(round(score, 2)))
    return False


# ─────────────────────────────────────────────
# Slack Formatting
# ─────────────────────────────────────────────

def _score_emoji(score: float) -> str:
    if score >= 90: return "🔴🔥"
    if score >= 80: return "🟠⚡"
    if score >= 70: return "🟡📡"
    return "⚪"


def _format_slack_message(token: dict, score: float) -> dict:
    """Format Slack block kit message for a SENTINEL alert."""
    symbol   = token.get("symbol", "???")
    name     = token.get("name", "Unknown")
    mint     = token.get("mint", "")
    liq_sol  = token.get("vSolInBondingCurve", 0) or token.get("liquidity_sol", 0) or 0
    holders  = token.get("holders", 0) or 0
    social   = token.get("social_score", 0) or 0
    flags    = token.get("risk_flags", [])
    twitter  = token.get("twitter", "")
    telegram = token.get("telegram", "")
    website  = token.get("website", "")

    emoji = _score_emoji(score)
    needs_gate = score >= THRESHOLD_ALL

    # Dexscreener link
    dex_url = f"https://dexscreener.com/solana/{mint}"
    pump_url = f"https://pump.fun/{mint}"

    socials_text = " | ".join(filter(None, [
        f"<{twitter}|Twitter>" if twitter else None,
        f"<{telegram}|Telegram>" if telegram else None,
        f"<{website}|Website>" if website else None,
    ])) or "_none_"

    flags_text = ", ".join(f"`{f}`" for f in flags) if flags else "_clean_"

    gate_block = []
    if needs_gate:
        gate_block = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Yoruichi approval gate* — score ≥ {THRESHOLD_ALL}. React ✅ to approve, ❌ to dismiss."
                }
            }
        ]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} SENTINEL ALERT: ${symbol}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Token:* {name} (`${symbol}`)"},
                {"type": "mrkdwn", "text": f"*Score:* `{score:.1f}/100`"},
                {"type": "mrkdwn", "text": f"*Liquidity:* {liq_sol:.1f} SOL"},
                {"type": "mrkdwn", "text": f"*Holders:* {holders}"},
                {"type": "mrkdwn", "text": f"*Social velocity:* {social:.0f}/100"},
                {"type": "mrkdwn", "text": f"*Risk flags:* {flags_text}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Socials:* {socials_text}"},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View on DexScreener"},
                "url": dex_url,
                "style": "primary"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Mint: `{mint[:20]}...`  |  <{pump_url}|Pump.fun>  |  {datetime.now(timezone.utc).strftime('%H:%M UTC')}"}
            ]
        },
        *gate_block,
    ]

    return {
        "channel": SLACK_ALERT_CHANNEL,
        "text": f"SENTINEL: ${symbol} scored {score:.0f}/100",
        "blocks": blocks,
    }


# ─────────────────────────────────────────────
# Delivery Functions
# ─────────────────────────────────────────────

def _send_slack(payload: dict) -> bool:
    """Send Slack message via Web API."""
    if not SLACK_BOT_TOKEN:
        log.warning("slack_token_missing")
        return False

    import urllib.request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                log.info("slack_alert_sent", channel=payload.get("channel"))
                return True
            else:
                log.error("slack_api_error", error=result.get("error"))
                return False
    except Exception as e:
        log.error("slack_send_failed", error=str(e))
        return False


# ─────────────────────────────────────────────
# Celery Task
# ─────────────────────────────────────────────

@app.task(
    name="tasks.alert_router.route_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="alerts",
)
def route_alert(self, token: dict[str, Any], score: float):
    """
    Route alert to appropriate channels based on score threshold.
    Deduplicates within DEDUP_TTL_SECONDS window.
    """
    mint   = token.get("mint", "unknown")
    symbol = token.get("symbol", "???")

    try:
        # Dedup check
        if is_duplicate(mint, score):
            return {"status": "deduped", "mint": mint}

        channels_hit = []

        # Slack (≥ 70)
        if score >= THRESHOLD_SLACK:
            payload = _format_slack_message(token, score)
            if _send_slack(payload):
                channels_hit.append("slack")

        # Future: Discord (≥ 85), Telegram (≥ 95)
        # if score >= THRESHOLD_ALL:
        #     _send_discord(token, score)
        #     channels_hit.append("discord")
        # if score >= THRESHOLD_URGENT:
        #     _send_telegram_urgent(token, score)
        #     channels_hit.append("telegram")

        # Store delivery record
        from tasks.store_token import record_alert
        record_alert.delay(token, score, channels_hit)

        log.info("alert_routed", mint=mint, symbol=symbol, score=score, channels=channels_hit)
        return {"status": "delivered", "mint": mint, "channels": channels_hit}

    except Exception as exc:
        log.error("alert_routing_failed", mint=mint, error=str(exc))
        raise self.retry(exc=exc)
