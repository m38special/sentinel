"""
tasks/score_token.py — Token Scoring Pipeline
SENTINEL Phase 2 | LiQUiD SOUND

Scores incoming token events 0–100 using:
  - On-chain signals (liquidity, volume, holders)
  - Social velocity (from NOVA)
  - Risk flags (rug indicators)
  - Timing signals (age, migration status)
"""
import structlog
from typing import Any

from tasks import app
from tasks.risk_filter import check_rug_indicators
from tasks.store_token import persist_to_timescaledb
from tasks.alert_router import route_alert

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Scoring Weights
# ─────────────────────────────────────────────
WEIGHTS = {
    "liquidity":     0.25,   # SOL in liquidity pool
    "volume":        0.20,   # recent trading volume
    "holders":       0.15,   # unique holder count
    "social":        0.20,   # NOVA social velocity score
    "momentum":      0.10,   # price momentum (if available)
    "age_penalty":   0.10,   # penalize tokens older than threshold
}

# Liquidity thresholds (SOL)
LIQ_TIERS = [
    (500,  100),   # > 500 SOL → max score
    (100,  80),
    (50,   60),
    (20,   40),
    (5,    20),
    (0,    5),
]

# Holder thresholds
HOLDER_TIERS = [
    (1000, 100),
    (500,  80),
    (200,  60),
    (100,  40),
    (50,   20),
    (0,    5),
]


def _tier_score(value: float, tiers: list[tuple]) -> float:
    """Map a value to a score using threshold tiers."""
    for threshold, score in tiers:
        if value >= threshold:
            return score
    return 0.0


def compute_score(token_data: dict, social_score: float = 0.0) -> dict:
    """
    Compute composite SENTINEL score for a token.

    Returns:
        {
            "score": float (0–100),
            "components": {component: sub_score},
            "risk_flags": [str],
        }
    """
    components = {}

    # Liquidity score
    liquidity_sol = token_data.get("vSolInBondingCurve", 0) or token_data.get("liquidity_sol", 0)
    components["liquidity"] = _tier_score(liquidity_sol, LIQ_TIERS)

    # Volume score — SOL-based tiers (FIND-14: USD proxy was always 100 for any token >6.67 SOL)
    VOLUME_TIERS = [(100, 100), (50, 80), (20, 60), (10, 40), (5, 20), (0, 10)]
    volume_sol = token_data.get("vSolInBondingCurve", 0) or token_data.get("volume_sol", 0) or 0
    components["volume"] = _tier_score(volume_sol, VOLUME_TIERS)

    # Holder score
    holders = token_data.get("holders", 0) or 0
    components["holders"] = _tier_score(holders, HOLDER_TIERS)

    # Social velocity (from NOVA)
    components["social"] = min(social_score, 100)

    # Momentum (price change %, if available)
    price_change = token_data.get("priceChangePercent", 0) or 0
    components["momentum"] = min(max(price_change, 0) / 100 * 100, 100)

    # Age penalty (newer = better for launch monitoring)
    # token_age_seconds: 0 = brand new (bonus), older = penalty
    age_s = token_data.get("token_age_seconds", 0) or 0
    if age_s < 300:       # < 5 min: full score
        components["age_penalty"] = 100
    elif age_s < 3600:    # < 1h: moderate
        components["age_penalty"] = 70
    elif age_s < 86400:   # < 1d: low
        components["age_penalty"] = 30
    else:
        components["age_penalty"] = 0

    # Weighted composite
    score = sum(
        components[k] * WEIGHTS[k]
        for k in WEIGHTS
        if k in components
    )

    # Risk flags from risk_filter (plain function — NOT a Celery task, call directly)
    risk_flags = check_rug_indicators(token_data)

    # Rug penalty: each flag reduces score by 10 pts
    rug_penalty = len(risk_flags) * 10
    final_score = max(0.0, min(100.0, score - rug_penalty))

    log.info(
        "token_scored",
        mint=token_data.get("mint", ""),
        symbol=token_data.get("symbol", ""),
        score=round(final_score, 2),
        components=components,
        risk_flags=risk_flags,
    )

    return {
        "score": round(final_score, 2),
        "components": {k: round(v, 2) for k, v in components.items()},
        "risk_flags": risk_flags,
    }


# ─────────────────────────────────────────────
# Celery Task
# ─────────────────────────────────────────────

@app.task(
    name="tasks.score_token.score_and_route",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="sentinel",
)
def score_and_route(self, token_data: dict[str, Any], social_score: float = 0.0):
    """
    Main pipeline task: score token → store → route alert if threshold met.
    Called directly from sentinel.py WebSocket listener.

    Args:
        token_data: Raw token event from PumpPortal
        social_score: NOVA social velocity score (0–100), default 0
    """
    try:
        mint = token_data.get("mint", "unknown")
        symbol = token_data.get("symbol", "")
        log.info("pipeline_start", mint=mint, symbol=symbol)

        # 1. Score
        result = compute_score(token_data, social_score)
        score = result["score"]
        risk_flags = result["risk_flags"]

        # 2. Enrich token_data with score
        enriched = {
            **token_data,
            "score": score,
            "social_score": social_score,
            "risk_flags": risk_flags,
            "score_components": result["components"],
        }

        # 3. Store to TimescaleDB (always)
        persist_to_timescaledb.delay(enriched)

        # 4. Route alert — threshold check happens inside route_alert
        # Let route_alert own all threshold logic (avoids split-brain)
        route_alert.delay(enriched, score)

        return {"mint": mint, "score": score, "status": "processed"}

    except (OSError, ConnectionError, TimeoutError) as exc:
        # Transient: network/DB blip — safe to retry
        log.warning("score_task_transient_error", mint=token_data.get("mint"), error=str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        # Non-transient: logic/data error — fail fast, no retry
        log.error("score_task_failed", mint=token_data.get("mint"), error=str(exc), exc_info=True)
        raise  # let Celery mark as FAILURE


@app.task(name="tasks.score_token.health_check", queue="sentinel")
def health_check():
    """Periodic health check — verifies worker is alive."""
    log.info("health_check", status="ok")
    return {"status": "ok"}
