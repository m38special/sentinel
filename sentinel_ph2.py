"""
SENTINEL Phase 2 — WebSocket Listener (Wave 3 Integration)
LiQUiD SOUND | CFO: Captain Yoruichi

Wires the Phase 1 PumpPortal WebSocket listener into the Phase 2
Celery task pipeline (score_and_route → store → alert_router).

Changes from MVP (scanner_mvp.py):
  - Drops inline SQLite + send_alerts — all processing via Celery
  - score_and_route.delay() dispatched immediately on valid token
  - Celery workers handle scoring, storage, and alert routing
  - Deduplication handled in Redis (alert_router)
  - Social score from NOVA injected if Redis cache present
  - Graceful shutdown on SIGTERM (Railway-compatible)
"""
import asyncio
import json
import logging
import os
import signal
import sys
import urllib.request
from datetime import datetime, timezone

import redis as redis_lib
import websockets

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("sentinel.ph2")

# ── Config ───────────────────────────────────────────────────────────────────
PUMP_WS_URL          = os.getenv("PUMP_WS_URL", "wss://pumpportal.fun/api/data")
PUMP_API_KEY         = os.getenv("PUMP_API_KEY", "")
REDIS_URL            = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MIN_MARKET_CAP_SOL   = float(os.getenv("MIN_MARKET_CAP_SOL", "0"))
MIN_VSOL_USD         = float(os.getenv("MIN_VSOL_USD", "0"))   # optional volume filter
SOL_USD_ESTIMATE     = float(os.getenv("SOL_USD_ESTIMATE", "150"))
RECONNECT_DELAY_S    = int(os.getenv("RECONNECT_DELAY_S", "5"))

# ── Redis + Celery app ───────────────────────────────────────────────────────
# Import Celery app for .delay() dispatch
# This runs in the listener process — tasks are dispatched to workers via broker
try:
    from tasks.score_token import score_and_route
    CELERY_AVAILABLE = True
    log.info("Celery task pipeline: ✅ connected")
except ImportError as e:
    CELERY_AVAILABLE = False
    log.warning(f"Celery not available ({e}) — running in LOG-ONLY mode")

# ── Redis (for NOVA social score cache lookup) ────────────────────────────────
_redis = None

def get_redis() -> redis_lib.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
            _redis.ping()
            log.info("Redis: ✅ connected")
        except Exception as e:
            log.warning(f"Redis not available ({e}) — social scores disabled")
            _redis = None
    return _redis


def get_nova_social_score(mint: str) -> float:
    """Pull NOVA social velocity score from Redis cache (0–100). Returns 0.0 if not found."""
    r = get_redis()
    if r is None:
        return 0.0
    try:
        val = r.get(f"nova:social:{mint}")
        return float(val) if val else 0.0
    except Exception:
        return 0.0


# ── UAI: Publish to AXIOM ───────────────────────────────────────────────────

def _publish_uai_signal(token_data: dict, social_score: float, score: float):
    """
    Publish token signal to AXIOM via UAI channel.
    AXIOM subscribes to uai:events:token_signal.
    """
    r = get_redis()
    if r is None:
        log.warning("UAI: Redis not available, skipping AXIOM signal")
        return

    mint = token_data.get("mint", "")
    symbol = token_data.get("symbol", "???")

    message = {
        "id": f"sig-{datetime.now(timezone.utc).timestamp()}",
        "from": "sentinel",
        "to": "axiom",
        "intent": "analyze.market_signal",
        "priority": "high" if score >= 85 else "medium",
        "payload": {
            "symbol": symbol,
            "name": token_data.get("name", "Unknown"),
            "mint": mint,
            "market_cap_sol": token_data.get("marketCapSol", 0),
            "liquidity_sol": token_data.get("liquidity_sol", 0),
            "social_score": social_score,
            "sentinel_score": score,
            "risk_flags": token_data.get("risk_flags", []),
            "detected_at": token_data.get("detected_at"),
        },
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 300,
    }

    try:
        r.publish("uai:events:token_signal", json.dumps(message))
        log.info(f"📡 UAI → AXIOM: {symbol} ({mint[:12]}...)")
    except Exception as e:
        log.error(f"UAI publish failed: {e}")


# ── Token Validation ─────────────────────────────────────────────────────────

def validate_token(token: dict) -> bool:
    """Accept only valid `create` events from PumpPortal."""
    if not isinstance(token, dict):
        return False
    if token.get("txType") != "create":
        return False
    mint = token.get("mint", "")
    if not mint or not (30 <= len(mint) <= 50):
        return False
    return True


def fetch_token_metadata(mint: str) -> dict:
    """Fetch name/symbol from pump.fun API — not in WS payload."""
    try:
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return {
                "name": data.get("name", "Unknown"),
                "symbol": data.get("symbol", "???"),
                "twitter": data.get("twitter", ""),
                "telegram": data.get("telegram", ""),
                "website": data.get("website", ""),
                "description": data.get("description", "")[:200],
            }
    except Exception as e:
        log.debug(f"Metadata fetch failed for {mint}: {e}")
        return {"name": "Unknown", "symbol": "???", "twitter": "", "telegram": "", "website": ""}


def sanitize(s: str, max_len: int = 64) -> str:
    if not s:
        return ""
    s = s.replace("*", "").replace("`", "").replace("[", "").replace("]", "")
    return s[:max_len].strip()


def build_token_payload(raw: dict, metadata: dict) -> dict:
    """Merge WS event + API metadata into a normalized payload for Celery."""
    mint = raw.get("mint", "")
    market_cap_sol = raw.get("marketCapSol", 0) or 0
    v_sol = raw.get("vSolInBondingCurve", 0) or 0
    v_tokens = raw.get("vTokensInBondingCurve", 0) or 0
    initial_buy = raw.get("initialBuy", 0) or 0

    return {
        # On-chain fields (from WS)
        "mint":                   mint,
        "bonding_curve_key":      raw.get("bondingCurveKey", ""),
        "trader_public_key":      raw.get("traderPublicKey", ""),
        "marketCapSol":           market_cap_sol,
        "vSolInBondingCurve":     v_sol,
        "vTokensInBondingCurve":  v_tokens,
        "initialBuy":             initial_buy,
        "token_age_seconds":      0,  # brand new on create event

        # Metadata (from API)
        "name":        sanitize(metadata.get("name", "Unknown"), 64),
        "symbol":      sanitize(metadata.get("symbol", "???"), 10),
        "twitter":     metadata.get("twitter", ""),
        "telegram":    metadata.get("telegram", ""),
        "website":     metadata.get("website", ""),
        "description": metadata.get("description", ""),

        # Derived
        "market_cap_usd":   market_cap_sol * SOL_USD_ESTIMATE,
        "liquidity_sol":    v_sol,
        "volume":           v_sol * SOL_USD_ESTIMATE,  # proxy for new tokens
        "holders":          0,  # not available at create time; enriched later
        "priceChangePercent": 0.0,

        # Timestamp
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "source":      "pumpportal_ws",
    }


# ── Dedup (Redis SET, 5 min TTL) ─────────────────────────────────────────────

SEEN_TTL = 300  # seconds

def is_seen(mint: str) -> bool:
    """
    Returns True if we already dispatched this mint in the last 5 min.
    Uses atomic SET NX EX to prevent TOCTOU race in parallel listeners.
    """
    r = get_redis()
    if r is None:
        return False  # can't dedup without Redis; allow through
    key = f"sentinel:seen:{mint}"
    # Atomic SET NX EX — only sets if key doesn't exist
    was_set = r.set(key, "1", ex=SEEN_TTL, nx=True)
    return not was_set  # True if we didn't set (already existed)


# ── Graceful Shutdown ─────────────────────────────────────────────────────────

_shutdown = False

def _handle_sigterm(*_):
    global _shutdown
    log.info("SIGTERM received — shutting down gracefully")
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


# ── Main Listener ─────────────────────────────────────────────────────────────

async def listen_forever():
    log.info(f"SENTINEL Ph2 — connecting to {PUMP_WS_URL}")

    while not _shutdown:
        try:
            async with websockets.connect(
                PUMP_WS_URL,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                log.info("✅ Connected to PumpPortal WebSocket")

                subscribe_msg = {"method": "subscribeNewToken"}
                if PUMP_API_KEY:
                    subscribe_msg["apiKey"] = PUMP_API_KEY
                await ws.send(json.dumps(subscribe_msg))
                log.info("📡 Subscribed to newToken events")

                async for raw_msg in ws:
                    if _shutdown:
                        break
                    try:
                        token = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        log.debug(f"Invalid JSON: {raw_msg[:80]}")
                        continue

                    if not validate_token(token):
                        continue

                    mint = token.get("mint", "")

                    # Redis dedup — skip if already dispatched
                    if is_seen(mint):
                        log.debug(f"Dedup skip: {mint[:12]}...")
                        continue

                    # Volume filter (optional)
                    v_sol = token.get("vSolInBondingCurve", 0) or 0
                    if MIN_VSOL_USD and (v_sol * SOL_USD_ESTIMATE) < MIN_VSOL_USD:
                        log.debug(f"Volume filter skip: {mint[:12]}... vSol={v_sol:.2f}")
                        continue

                    # Market cap filter
                    mc_sol = token.get("marketCapSol", 0) or 0
                    if mc_sol < MIN_MARKET_CAP_SOL:
                        log.debug(f"McapSol filter skip: {mint[:12]}... mcap={mc_sol:.2f}")
                        continue

                    # Fetch metadata async (non-blocking)
                    metadata = await asyncio.get_running_loop().run_in_executor(
                        None, fetch_token_metadata, mint
                    )

                    # Get NOVA social score from Redis cache
                    social_score = get_nova_social_score(mint)

                    # Build normalized payload
                    payload = build_token_payload(token, metadata)

                    log.info(
                        f"📡 {payload['symbol']} ({mint[:10]}...) "
                        f"mcap={mc_sol:.2f} SOL | social={social_score:.0f} "
                        f"| {'CELERY→' if CELERY_AVAILABLE else 'LOG-ONLY'}"
                    )

                    if CELERY_AVAILABLE:
                        # ── Wave 3: Dispatch to Celery pipeline ────────────────
                        task = score_and_route.delay(payload, social_score)
                        log.info(f"✅ Dispatched {mint[:12]}... → task_id={task.id}")

                        # ── Phase 3: UAI → AXIOM pilot ─────────────────────────
                        _publish_uai_signal(payload, social_score, score=0)
                    else:
                        # Fallback: just log (for local dev without Celery)
                        log.info(f"[LOG-ONLY] {payload['symbol']} payload={json.dumps(payload)[:200]}")

        except websockets.exceptions.ConnectionClosed as e:
            if _shutdown:
                break
            log.warning(f"WS closed: {e} — reconnecting in {RECONNECT_DELAY_S}s")
            await asyncio.sleep(RECONNECT_DELAY_S)
        except Exception as e:
            if _shutdown:
                break
            log.error(f"WS error: {type(e).__name__}: {e} — reconnecting in {RECONNECT_DELAY_S}s")
            await asyncio.sleep(RECONNECT_DELAY_S)

    log.info("SENTINEL Ph2 listener stopped.")


# ── Health Server ─────────────────────────────────────────────────────────────

def run_health_server(port: int = 8080):
    """Minimal HTTP health endpoint for Railway."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):
            pass  # suppress access logs

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    log.info(f"Health server: http://0.0.0.0:{port}/")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_health_server(int(os.getenv("PORT", "8080")))
    asyncio.run(listen_forever())
