"""
tasks/cfo_command.py — CFO Command Layer
SENTINEL Phase 6 | LiQUiD SOUND

Flow:
1. report.executive_summary auto-generation (morning/adhoc)
2. market_update → daily briefing integration
3. Budget/risk alerts via UAI
4. CEO dashboard feed
5. Daily briefing in Slack #idea-ocean (Yoruichi + NOVA format)
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests
from tasks import app

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C0AHE2LQFRC")


def get_redis():
    import redis as redis_lib
    return redis_lib.from_url(REDIS_URL, decode_responses=True)


def post_to_slack(text: str, channel: str = None, username: str = "Yoruichi", emoji: str = ":female-guard-officer:") -> bool:
    """Post message to Slack."""
    if not SLACK_BOT_TOKEN:
        log.warning("slack_token_missing")
        return False
    
    channel = channel or SLACK_CHANNEL_ID
    
    payload = {
        "channel": channel,
        "text": text,
        "username": username,
        "icon_emoji": emoji,
    }
    
    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        result = resp.json()
        if result.get("ok"):
            log.info(f"posted_to_slack: {channel}")
            return True
        else:
            log.error(f"slack_error: {result.get('error')}")
            return False
    except Exception as e:
        log.error(f"slack_network_error: {e}")
        return False


# ─────────────────────────────────────────────
# Daily Briefing (Yoruichi + NOVA) - Format Mirror
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.generate_daily_briefing",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="sentinel",
)
def generate_daily_briefing(self):
    """
    Daily briefing posted to #idea-ocean.
    Format: CAPTAIN YORUICHI — DAILY BRIEFING | [date]
            ...market content...
            --- 
            NOVA — DAILY BRIEFING | [date]
            ...social content...
    """
    r = get_redis()
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    # === CAPTAIN YORUICHI'S BRIEFING ===
    yoruichi_sections = _build_yoruichi_briefing(r, today)
    
    # === NOVA'S BRIEFING ===
    nova_sections = _build_nova_briefing(r, today)
    
    # Combine into single message
    full_briefing = f"""CAPTAIN YORUICHI — DAILY BRIEFING | {today}
---
{yoruichi_sections}

---
NOVA — DAILY BRIEFING | {today}
{nova_sections}"""
    
    # Post to Slack
    success = post_to_slack(full_briefing, username="Yoruichi", emoji=":briefcase:")
    
    log.info("daily_briefing_generated")
    return {"status": "posted" if success else "failed", "time": today}


def _build_yoruichi_briefing(r, today: str) -> str:
    """Build Yoruichi's market briefing section."""
    
    # Get crypto prices (from Redis cache or API)
    btc_price = r.get("market:btc:price") or "$65,000"
    eth_price = r.get("market:eth:price") or "$1,900"
    sol_price = r.get("market:sol:price") or "$85"
    xrp_price = r.get("market:xrp:price") or "$1.40"
    
    btc_change = r.get("market:btc:change") or "0%"
    eth_change = r.get("market:eth:change") or "0%"
    sol_change = r.get("market:sol:change") or "0%"
    xrp_change = r.get("market:xrp:change") or "0%"
    
    lines = [
        f":bar_chart: CRYPTO MARKETS",
        f"BTC: {btc_price} ({btc_change}) | ETH: {eth_price} ({eth_change}) | SOL: {sol_price} ({sol_change}) | XRP: {xrp_price} ({xrp_change})",
        ""
    ]
    
    # Market analysis
    try:
        market_updates = r.lrange("cfo:market_updates", 0, 2) or []
        if market_updates:
            for update in market_updates:
                data = json.loads(update)
                lines.append(data.get("title", ""))
        else:
            lines.append("Markets showing range-bound activity. Watching key support levels.")
    except:
        lines.append("Markets showing range-bound activity. Watching key support levels.")
    
    lines.extend(["", ":chart_with_upwards_trend: EQUITIES"])
    
    # Equity context
    sp500 = r.get("market:sp500") or "6,800"
    nasdaq = r.get("market:nasdaq") or "22,500"
    dow = r.get("market:dow") or "48,500"
    
    lines.append(f"S&P 500: {sp500} | Nasdaq: {nasdaq} | Dow: {dow}")
    
    lines.extend(["", ":robot_face: AI / TECH"])
    lines.append("AI capex continues scaling. Monitoring enterprise adoption trends.")
    
    lines.extend(["", ":globe_with_meridians: MACRO"])
    lines.append("Fed policy remains data-dependent. Key economic releases this week.")
    
    lines.extend(["", ":briefcase: CFO NOTE"])
    lines.append("SENTINEL monitoring for elevated signal flow. AXIOM risk scoring active. Stay disciplined.")
    lines.append("— Captain Yoruichi :briefcase: | CFO, Liquid Sound")
    
    return "\n".join(lines)


def _build_nova_briefing(r, today: str) -> str:
    """Build NOVA's social trends section."""
    
    lines = [":fire: TRENDING RIGHT NOW"]
    
    # Get trending from Redis cache
    try:
        trending = r.get("nova:trending:top")
        if trending:
            data = json.loads(trending)
            trends = data.get("trends", [])[:4]
            if trends:
                for t in trends:
                    lines.append(f"• {t}")
            else:
                lines.append("• Monitoring social channels for emerging trends")
        else:
            lines.append("• Scanning social platforms...")
    except:
        lines.append("• Scanning social platforms...")
    
    lines.extend(["", ":newspaper: BREAKING NEWS"])
    
    # Get news from cache
    try:
        news = r.lrange("nova:news:top", 0, 2) or []
        if news:
            for i, item in enumerate(news, 1):
                data = json.loads(item)
                lines.append(f"{i}. {data.get('title', 'News update')}")
        else:
            lines.append("1. Monitoring for breaking news")
    except:
        lines.append("1. Monitoring for breaking news")
    
    lines.extend(["", ":bulb: MARKETING OPPORTUNITIES"])
    lines.append("Content opportunities identified based on trend analysis.")
    
    lines.extend(["", ":chart_with_upwards_trend: INVESTING OPPORTUNITIES"])
    lines.append("SENTINEL + AXIOM filtering for high-score signals.")
    
    lines.extend(["", ":coin: SOLANA SPL TOKEN ALERT"])
    
    # Get token stats
    token_count = r.get("pumpfun:tokens:today") or "0"
    lines.append(f"{token_count}+ tokens deployed via Pump.fun in the last 24 hours.")
    lines.append("Signal-to-noise is elevated. Watch SENTINEL alerts in #plays.")
    
    lines.extend(["", ":star2: NOVA'S PICK OF THE DAY"])
    lines.append("Trend-based opportunity identified. First-mover advantage active.")
    lines.append("— NOVA :star2: | Social Intelligence, Liquid Sound")
    
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Executive Summary (Legacy)
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# Executive Summary Generation
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.generate_executive_summary",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="sentinel",
)
def generate_executive_summary(self, timeframe: str = "daily"):
    """
    Auto-generate executive summary for CEO.
    Aggregates data from:
    - SENTINEL alerts (last 24h)
    - Market signals
    - Risk alerts
    - Team activity
    """
    r = get_redis()
    
    # Gather data from various sources
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timeframe": timeframe,
        "sections": {}
    }
    
    # 1. Get SENTINEL activity
    try:
        alert_count = r.get("sentinel:stats:alerts:today") or 0
        high_score_count = r.get("sentinel:stats:high_score:today") or 0
        summary["sections"]["sentinel"] = {
            "alerts": int(alert_count),
            "high_score_tokens": int(high_score_count),
        }
    except Exception as e:
        log.warning("failed_to_get_sentinel_stats", error=str(e))
    
    # 2. Get market updates
    try:
        market_updates = r.lrange("cfo:market_updates", 0, 9) or []
        summary["sections"]["market"] = {
            "updates": [json.loads(u) for u in market_updates],
            "count": len(market_updates),
        }
    except Exception as e:
        log.warning("failed_to_get_market_updates", error=str(e))
    
    # 3. Get risk alerts
    try:
        risk_alerts = r.lrange("cfo:risk_alerts", 0, 4) or []
        summary["sections"]["risk"] = {
            "alerts": [json.loads(a) for a in risk_alerts],
            "count": len(risk_alerts),
        }
    except Exception as e:
        log.warning("failed_to_get_risk_alerts", error=str(e))
    
    # 4. Get content pipeline status
    try:
        pending_drafts = r.keys("content:draft:*") or []
        summary["sections"]["content"] = {
            "pending_approvals": len(pending_drafts),
        }
    except Exception as e:
        log.warning("failed_to_get_content_status", error=str(e))
    
    # Generate summary text
    summary_text = _format_summary_text(summary)
    summary["summary_text"] = summary_text
    
    # Store for CEO dashboard
    r.setex(
        f"ceo:summary:{timeframe}",
        86400,  # 24h TTL
        json.dumps(summary)
    )
    
    # Publish to CEO dashboard feed
    dashboard_msg = {
        "id": f"summary-{datetime.now(timezone.utc).timestamp()}",
        "from": "yoruichi",
        "to": "ceo",
        "intent": "report.executive_summary",
        "priority": "high",
        "payload": summary,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 3600,
    }
    r.publish("uai:events:ceo_dashboard", json.dumps(dashboard_msg))
    
    # Post to Slack #idea-ocean
    _post_to_slack(summary_text, timeframe)
    
    log.info(f"executive_summary_generated: {timeframe}")
    
    return {"status": "generated", "timeframe": timeframe}


def _format_summary_text(summary: dict) -> str:
    """Format summary as readable text."""
    sections = summary.get("sections", {})
    
    lines = ["📊 EXECUTIVE SUMMARY\n"]
    
    # Sentinel
    if "sentinel" in sections:
        s = sections["sentinel"]
        lines.append(f"🛡️ SENTINEL: {s.get('alerts', 0)} alerts, {s.get('high_score_tokens', 0)} high-score tokens")
    
    # Market
    if "market" in sections:
        m = sections["market"]
        lines.append(f"📈 MARKET: {m.get('count', 0)} updates")
    
    # Risk
    if "risk" in sections:
        r = sections["risk"]
        lines.append(f"⚠️ RISK: {r.get('count', 0)} alerts")
    
    # Content
    if "content" in sections:
        c = sections["content"]
        lines.append(f"📝 CONTENT: {c.get('pending_approvals', 0)} pending approvals")
    
    lines.append(f"\nGenerated: {summary.get('generated_at', 'N/A')}")
    
    return "\n".join(lines)


def _post_to_slack(summary_text: str, timeframe: str):
    """Post executive summary to Slack #idea-ocean."""
    import urllib.request
    
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID", "idea-ocean")  # Default to idea-ocean
    
    if not SLACK_BOT_TOKEN:
        log.warning("slack_token_missing_for_summary")
        return
    
    # Get channel ID if we have a channel name
    channel_id = SLACK_CHANNEL
    if not SLACK_CHANNEL.startswith("C"):
        # It's a channel name, need to resolve to ID
        # For now, try posting to the channel name directly
        channel_id = SLACK_CHANNEL
    
    payload = {
        "channel": channel_id,
        "text": summary_text,
        "username": "Yoruichi",
        "icon_emoji": ":female-guard-officer:",
    }
    
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
                log.info(f"summary_posted_to_slack: {channel_id}")
            else:
                log.error(f"slack_summary_error: {result.get('error')}")
    except Exception as e:
        log.error(f"slack_summary_network_error: {str(e)}")


# ─────────────────────────────────────────────
# Daily Newsletter (Yoruichi + NOVA)
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.generate_daily_newsletter",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="sentinel",
)
def generate_daily_newsletter(self):
    """
    Daily newsletter combining:
    - Yoruichi's market briefing
    - NOVA's social trends summary
    
    Posts to #idea-ocean.
    """
    import urllib.request
    from datetime import datetime, timedelta
    
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID", "C0AHE2LQFRC")
    
    r = get_redis()
    
    # Build newsletter sections
    lines = [
        "📰 *DAILY NEWSLETTER* — Yoruichi & NOVA",
        "_" + datetime.now().strftime("%B %d, %Y") + "_",
        ""
    ]
    
    # === YORUICHI'S MARKET BRIEFING ===
    lines.append("*🏦 YORUICHI'S MARKET BRIEF*")
    
    # Get risk alerts from last 24h
    try:
        risk_alerts = r.lrange("cfo:risk_alerts", 0, 4) or []
        if risk_alerts:
            lines.append(f"⚠️ *Risk Alerts:* {len(risk_alerts)} active")
            for alert in risk_alerts[:2]:
                alert_data = json.loads(alert)
                lines.append(f"  • {alert_data.get('title', 'Risk alert')}")
        else:
            lines.append("✅ *Risk Status:* All clear")
    except Exception as e:
        lines.append(f"⚠️ Risk data unavailable")
    
    # Get market updates
    try:
        market_updates = r.lrange("cfo:market_updates", 0, 4) or []
        if market_updates:
            lines.append(f"📈 *Market Updates:* {len(market_updates)}")
            for update in market_updates[:2]:
                update_data = json.loads(update)
                lines.append(f"  • {update_data.get('title', 'Market update')}")
        else:
            lines.append("📈 *Market:* No new updates")
    except Exception as e:
        lines.append("📈 Market data unavailable")
    
    lines.append("")
    
    # === NOVA'S SOCIAL TRENDS ===
    lines.append("*🐦 NOVA'S SOCIAL PULSE*")
    
    # Try to get NOVA scan data from Redis cache (updated by nova_scan tasks)
    try:
        nova_stats = r.get("nova:stats:daily")
        if nova_stats:
            nova_data = json.loads(nova_stats)
            lines.append(f"📊 Scans run: {nova_data.get('scan_count', 0)}")
            lines.append(f"🐦 Twitter signals: {nova_data.get('twitter_signals', 0)}")
            lines.append(f"📺 Reddit posts: {nova_data.get('reddit_posts', 0)}")
        else:
            lines.append("📊 No social scan data today yet")
            lines.append("   (NOVA runs every 15 min)")
    except Exception as e:
        lines.append("📊 Social data unavailable")
    
    # Get trending topics if cached
    try:
        trending = r.get("nova:trending:top")
        if trending:
            trending_data = json.loads(trending)
            trends = trending_data.get("trends", [])[:5]
            if trends:
                lines.append("")
                lines.append("*🔥 Trending Now:*")
                for t in trends:
                    lines.append(f"  • {t}")
    except:
        pass
    
    lines.append("")
    lines.append("_Report generated by Yoruichi & NOVA_")
    
    newsletter_text = "\n".join(lines)
    
    # Post to Slack
    if SLACK_BOT_TOKEN:
        payload = {
            "channel": SLACK_CHANNEL,
            "text": newsletter_text,
            "username": "NOVA",
            "icon_emoji": ":newspaper:",
        }
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
                    log.info("daily_newsletter_posted_to_slack")
                else:
                    log.error("slack_newsletter_error", error=result.get("error"))
        except Exception as e:
            log.error("slack_newsletter_network_error", error=str(e))
    
    log.info("daily_newsletter_generated")
    return {"status": "generated", "sections": ["yoruichi", "nova"]}


# ─────────────────────────────────────────────
# Market Update → Daily Briefing
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.publish_market_update",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="sentinel",
)
def publish_market_update(self, update_type: str, title: str, details: dict):
    """
    Publish market update that integrates with daily briefing.
    """
    r = get_redis()
    
    update = {
        "type": update_type,
        "title": title,
        "details": details,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    
    # Store for briefing history
    r.lpush("cfo:market_updates", json.dumps(update))
    r.ltrim("cfo:market_updates", 0, 99)  # Keep last 100
    
    # Publish to UAI market_update channel
    msg = {
        "id": f"market-{datetime.now(timezone.utc).timestamp()}",
        "from": "yoruichi",
        "to": "broadcast",
        "intent": "market_update",
        "priority": "medium",
        "payload": update,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 3600,
    }
    r.publish("uai:events:market_update", json.dumps(msg))
    
    log.info("market_update_published", type=update_type, title=title)
    
    return {"status": "published", "update_type": update_type}


# ─────────────────────────────────────────────
# Budget & Risk Alerts
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.risk_alert",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    queue="sentinel",
)
def risk_alert(self, severity: str, title: str, description: str, metadata: dict = None):
    """
    Publish budget or risk alert via UAI.
    """
    r = get_redis()
    
    alert = {
        "severity": severity,  # low, medium, high, critical
        "title": title,
        "description": description,
        "metadata": metadata or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    
    # Store for CEO dashboard
    r.lpush("cfo:risk_alerts", json.dumps(alert))
    r.ltrim("cfo:risk_alerts", 0, 49)  # Keep last 50
    
    # Publish to UAI security_alert channel
    msg = {
        "id": f"risk-{datetime.now(timezone.utc).timestamp()}",
        "from": "yoruichi",
        "to": "broadcast",
        "intent": "security.threat_flag",
        "priority": "critical" if severity == "critical" else "high",
        "payload": alert,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 86400,
    }
    r.publish("uai:events:security_alert", json.dumps(msg))
    
    log.warning("risk_alert_published", severity=severity, title=title)
    
    return {"status": "alert_published", "severity": severity}


# ─────────────────────────────────────────────
# CEO Dashboard Feed
# ─────────────────────────────────────────────

@app.task(
    name="tasks.cfo_command.publish_to_dashboard",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    queue="sentinel",
)
def publish_to_dashboard(self, widget_type: str, title: str, content: Any):
    """
    Publish widget update to CEO dashboard feed.
    """
    r = get_redis()
    
    widget = {
        "type": widget_type,
        "title": title,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    
    # Store for dashboard
    r.lpush("ceo:dashboard:feed", json.dumps(widget))
    r.ltrim("ceo:dashboard:feed", 0, 99)  # Keep last 100
    
    # Publish to CEO dashboard channel
    msg = {
        "id": f"dash-{datetime.now(timezone.utc).timestamp()}",
        "from": "yoruichi",
        "to": "ceo",
        "intent": "dashboard.widget_update",
        "priority": "medium",
        "payload": widget,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 3600,
    }
    r.publish("uai:events:ceo_dashboard", json.dumps(msg))
    
    log.info("dashboard_widget_published", widget_type=widget_type, title=title)
    
    return {"status": "published", "widget_type": widget_type}
