"""
tasks/cfo_command.py — CFO Command Layer
SENTINEL Phase 6 | LiQUiD SOUND

Flow:
1. report.executive_summary auto-generation (morning/adhoc)
2. market_update → daily briefing integration
3. Budget/risk alerts via UAI
4. CEO dashboard feed
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import redis as redis_lib
from tasks import app

log = logging.get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis():
    return redis_lib.from_url(REDIS_URL, decode_responses=True)


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
    
    log.info("executive_summary_generated", timeframe=timeframe)
    
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
