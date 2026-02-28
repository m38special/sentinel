"""
tasks/security_alert.py — UAI Security Alert Publisher
SENTINEL Phase 4 | LiQUiD SOUND

Publishes security threat alerts to CIPHER via UAI channel.
CIPHER subscribes to uai:events:security_alert.
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
    """Get Redis client."""
    return redis_lib.from_url(REDIS_URL, decode_responses=True)


@app.task(
    name="tasks.security_alert.publish",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="sentinel",
)
def publish_security_alert(self, token_data: dict[str, Any], risk_flags: list):
    """
    Publish security threat alert to CIPHER via UAI.
    """
    r = get_redis()
    
    mint = token_data.get("mint", "")
    symbol = token_data.get("symbol", "???")
    
    message = {
        "id": f"sec-{datetime.now(timezone.utc).timestamp()}",
        "from": "sentinel",
        "to": "cipher",
        "intent": "security.threat_flag",
        "priority": "critical" if len(risk_flags) >= 3 else "high",
        "payload": {
            "symbol": symbol,
            "name": token_data.get("name", "Unknown"),
            "mint": mint,
            "risk_flags": risk_flags,
            "liquidity_sol": token_data.get("liquidity_sol", 0),
            "score": token_data.get("score", 0),
            "detected_at": token_data.get("detected_at"),
        },
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 300,
    }
    
    try:
        r.publish("uai:events:security_alert", json.dumps(message))
        log.warning(
            "security_alert_published",
            mint=mint,
            symbol=symbol,
            flags=len(risk_flags),
            priority=message["priority"],
        )
        return {"status": "published", "mint": mint, "flags": len(risk_flags)}
    except Exception as e:
        log.error("security_alert_failed", mint=mint, error=str(e))
        raise self.retry(exc=e)
