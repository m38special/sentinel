"""
tasks/nova_scan.py — NOVA Social Scan Tasks
SENTINEL Phase 2 | LiQUiD SOUND

Periodic Celery tasks that trigger NOVA social scans
and store results to TimescaleDB.
Beat schedule: every 15 minutes (configured in tasks/__init__.py)
"""
import structlog
import json
from pathlib import Path

# Resolve nova_scraper relative to this file (works in dev + Docker)
_nova_scraper_path = Path(__file__).resolve().parent.parent
if str(_nova_scraper_path) not in sys.path:
    sys.path.insert(0, str(_nova_scraper_path))

from tasks import app

log = structlog.get_logger(__name__)


@app.task(
    name="tasks.nova_scan.full_social_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="nova",
    time_limit=300,      # 5 min hard timeout
    soft_time_limit=240, # 4 min soft timeout
)
def full_social_scan(self):
    """
    Periodic full NOVA social scan — Twitter + Reddit + TikTok.
    Scheduled every 15 minutes via Celery Beat.
    Results stored to nova_scans table.
    """
    import asyncio
    try:
        from nova_scraper import NOVAScraper
        nova = NOVAScraper(headless=True)

        log.info("nova_full_scan_start")
        result = asyncio.run(nova.full_scan())  # FIND-10: requires prefork pool (not gevent/eventlet)

        # Store to TimescaleDB
        _store_nova_scan(result, "full", [])

        # Extract high-velocity signals and log them
        twitter_crypto = result.get("nova_scan", {}).get("twitter", {}).get("crypto_trends", [])
        reddit_top = result.get("nova_scan", {}).get("reddit", {}).get("top_posts", [])[:5]

        log.info(
            "nova_full_scan_complete",
            twitter_crypto_count=len(twitter_crypto),
            reddit_top_count=len(reddit_top),
            duration=result.get("scan_duration_s"),
        )
        return {
            "status": "complete",
            "twitter_signals": len(twitter_crypto),
            "reddit_posts": len(reddit_top),
            "duration_s": result.get("scan_duration_s"),
        }

    except Exception as exc:
        log.error("nova_scan_failed", error=str(exc))
        raise self.retry(exc=exc)


@app.task(
    name="tasks.nova_scan.targeted_token_scan",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="nova",
    time_limit=120,
)
def targeted_token_scan(self, token_name: str, token_symbol: str) -> dict:
    """
    Targeted social velocity scan for a specific token.
    Called from score_and_route when a new token is detected.
    Returns social score (0–100) for inclusion in composite score.
    """
    import asyncio
    try:
        from nova_scraper import sentinel_social_check
        result = asyncio.run(sentinel_social_check(token_name, token_symbol))  # FIND-10: prefork pool required

        # Store scan record
        _store_nova_scan(
            result.get("detail", {}),
            "targeted",
            [token_name, token_symbol, f"${token_symbol}"],
        )

        log.info(
            "nova_targeted_scan_complete",
            symbol=token_symbol,
            social_score=result.get("social_score"),
            mentions=result.get("mentions"),
        )
        return result

    except Exception as exc:
        log.error("nova_targeted_scan_failed", symbol=token_symbol, error=str(exc))
        raise self.retry(exc=exc)


def _store_nova_scan(result: dict, scan_type: str, keywords: list):
    """Store NOVA scan results to TimescaleDB. Reuses engine from store_token."""
    try:
        from tasks.store_token import get_engine
        from sqlalchemy import text
        import json as _json

        engine = get_engine()

        platform = result.get("nova_scan", {})
        total = sum(
            len(v.get("crypto_trends", []) or v.get("top_posts", []) or v.get("all_trends", []))
            for v in platform.values()
            if isinstance(v, dict)
        )

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO nova_scans (time, platform, scan_type, keywords, results_count, scan_duration_s, raw_data)
                    VALUES (NOW(), :platform, :scan_type, :keywords, :results_count, :duration, :raw_data)
                """),
                {
                    "platform": ",".join(platform.keys()) if platform else scan_type,
                    "scan_type": scan_type,
                    "keywords": keywords,
                    "results_count": total,
                    "duration": result.get("scan_duration_s", 0),
                    "raw_data": (lambda j: j if len(j) <= 10000 else _json.dumps(
                        {"_truncated": True, "scan_type": scan_type, "duration": result.get("scan_duration_s")}
                    ))(_json.dumps(result)),  # FIND-12: safe truncation (no mid-JSON cuts)
                }
            )
            conn.commit()
    except Exception as e:
        log.warning("nova_scan_store_failed", error=str(e))  # non-fatal
