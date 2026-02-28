"""
tasks/risk_filter.py — Rug Indicator Checks
SENTINEL Phase 2 | LiQUiD SOUND

Returns a list of risk flags for a token.
Each flag reduces the composite score by 10 pts (in score_token.py).
"""
import logging
import structlog
from celery import shared_task
from tasks import app

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Risk Thresholds
# ─────────────────────────────────────────────
MIN_LIQUIDITY_SOL   = 5.0       # below this = low_liquidity flag
MIN_HOLDERS         = 10        # below this = low_holder_count flag
MAX_DEV_HOLD_PCT    = 50.0      # dev holds > 50% = dev_concentration flag
MAX_TOP10_HOLD_PCT  = 80.0      # top 10 wallets hold > 80% = whale_concentration
SOCIAL_REQUIRED     = True      # no social links = no_socials flag (configurable)


def check_rug_indicators(token_data: dict) -> list[str]:
    """
    Synchronous rug indicator check. Returns list of risk flag strings.
    Called from score_token (sync context) and as Celery task.

    Common flags:
      - low_liquidity        : < MIN_LIQUIDITY_SOL in bonding curve
      - low_holder_count     : < MIN_HOLDERS unique holders
      - dev_concentration    : dev wallet holds > MAX_DEV_HOLD_PCT %
      - whale_concentration  : top 10 wallets hold > MAX_TOP10_HOLD_PCT %
      - no_socials           : no Twitter/Telegram/website linked
      - frozen_metadata      : token metadata is frozen (common rug pattern)
      - mint_authority_active: mint authority not revoked (can print more)
      - copycat_name         : name matches known scam pattern
    """
    flags = []
    mint = token_data.get("mint", "")

    # Low liquidity
    liq = token_data.get("vSolInBondingCurve", 0) or token_data.get("liquidity_sol", 0) or 0
    if liq < MIN_LIQUIDITY_SOL:
        flags.append("low_liquidity")
        log.debug("flag_low_liquidity", mint=mint, liquidity_sol=liq)

    # Low holder count
    holders = token_data.get("holders", 0) or 0
    if holders < MIN_HOLDERS:
        flags.append("low_holder_count")

    # Dev concentration
    dev_pct = token_data.get("devHoldPercent", 0) or 0
    if dev_pct > MAX_DEV_HOLD_PCT:
        flags.append("dev_concentration")
        log.warning("flag_dev_concentration", mint=mint, dev_pct=dev_pct)

    # Whale concentration
    top10_pct = token_data.get("top10HoldPercent", 0) or 0
    if top10_pct > MAX_TOP10_HOLD_PCT:
        flags.append("whale_concentration")

    # No social links
    if SOCIAL_REQUIRED:
        twitter = token_data.get("twitter", "")
        telegram = token_data.get("telegram", "")
        website = token_data.get("website", "")
        if not any([twitter, telegram, website]):
            flags.append("no_socials")

    # Mint authority not revoked
    if token_data.get("mintAuthorityActive", False):
        flags.append("mint_authority_active")

    # Metadata frozen check
    if token_data.get("metadataFrozen", False):
        flags.append("frozen_metadata")

    # Copycat name detection (basic)
    name = (token_data.get("name", "") or "").lower()
    scam_patterns = ["official", "2.0", "v2", "real", "new", "legit"]
    if any(p in name for p in scam_patterns):
        flags.append("copycat_name")

    if flags:
        log.info("risk_flags_detected", mint=mint, flags=flags)

    return flags


# ─────────────────────────────────────────────
# Celery Task (for async pipeline use)
# ─────────────────────────────────────────────

@app.task(
    name="tasks.risk_filter.check_rug_indicators",
    queue="sentinel",
    max_retries=2,
)
def check_rug_indicators_task(token_data: dict) -> list[str]:
    """Async Celery wrapper for rug indicator check."""
    return check_rug_indicators(token_data)
