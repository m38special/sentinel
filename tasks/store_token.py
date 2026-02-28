"""
tasks/store_token.py — TimescaleDB Persistence
SENTINEL Phase 2 | LiQUiD SOUND

Stores token events and alert records to TimescaleDB.
Uses SQLAlchemy with connection pooling.
"""
import os
import json
import logging
import structlog
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from tasks import app

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────
# DB Connection
# ─────────────────────────────────────────────
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv(
            "TIMESCALEDB_URL",
            "postgresql://sentinel:changeme_in_prod@localhost:5432/sentinel"
        )
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        log.info("db_engine_created", url=db_url.split("@")[-1])  # log host only
    return _engine


# ─────────────────────────────────────────────
# Celery Tasks
# ─────────────────────────────────────────────

@app.task(
    name="tasks.store_token.persist_to_timescaledb",
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    queue="sentinel",
)
def persist_to_timescaledb(self, token_data: dict[str, Any]):
    """
    Persist a scored token event to TimescaleDB.
    Safe to retry — uses INSERT (not upsert) for event log.
    """
    mint   = token_data.get("mint", "")
    symbol = token_data.get("symbol", "")

    try:
        engine = get_engine()

        insert_sql = text("""
            INSERT INTO token_events (
                time, mint, name, symbol, score,
                volume_sol, holders, market_cap_usd, liquidity_usd,
                social_score, risk_flags, source, raw_data
            ) VALUES (
                NOW(), :mint, :name, :symbol, :score,
                :volume_sol, :holders, :market_cap_usd, :liquidity_usd,
                :social_score, :risk_flags, :source, :raw_data
            )
        """)

        params = {
            "mint":           mint,
            "name":           token_data.get("name", ""),
            "symbol":         symbol,
            "score":          token_data.get("score", 0.0),
            "volume_sol":     token_data.get("volume", 0.0),
            "holders":        token_data.get("holders", 0),
            "market_cap_usd": token_data.get("marketCap", 0.0),
            "liquidity_usd":  token_data.get("liquidity_usd", 0.0),
            "social_score":   token_data.get("social_score", 0.0),
            "risk_flags":     token_data.get("risk_flags", []),
            "source":         token_data.get("source", "pumpportal"),
            "raw_data":       json.dumps({
                k: v for k, v in token_data.items()
                if k not in ("score_components",)  # exclude large nested dicts
            }),
        }

        with engine.connect() as conn:
            conn.execute(insert_sql, params)
            conn.commit()

        log.info("token_stored", mint=mint, symbol=symbol, score=params["score"])
        return {"status": "stored", "mint": mint}

    except Exception as exc:
        log.error("store_failed", mint=mint, error=str(exc))
        raise self.retry(exc=exc)


@app.task(
    name="tasks.store_token.record_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="sentinel",
)
def record_alert(self, token: dict[str, Any], score: float, channels: list[str]):
    """Record alert delivery to TimescaleDB."""
    mint   = token.get("mint", "")
    symbol = token.get("symbol", "")

    try:
        engine = get_engine()

        for channel in channels:
            insert_sql = text("""
                INSERT INTO alerts (
                    time, mint, symbol, alert_type, score,
                    channel, delivered_at
                ) VALUES (
                    NOW(), :mint, :symbol, :alert_type, :score,
                    :channel, NOW()
                )
            """)
            params = {
                "mint":       mint,
                "symbol":     symbol,
                "alert_type": "high_score",
                "score":      score,
                "channel":    channel,
            }
            with engine.connect() as conn:
                conn.execute(insert_sql, params)
                conn.commit()

        log.info("alert_recorded", mint=mint, channels=channels)
        return {"status": "recorded", "mint": mint, "channels": channels}

    except Exception as exc:
        log.error("record_alert_failed", mint=mint, error=str(exc))
        raise self.retry(exc=exc)
