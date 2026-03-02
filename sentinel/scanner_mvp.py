"""
SENTINEL MVP — Pump.fun Token Scanner
Real-time WebSocket listener for new token events

FIX-01: PumpPortal sends FLAT JSON with txType="create", not {"method":"newToken","data":{}}
FIX-02: Market cap field is marketCapSol (SOL), not usd_market_cap
FIX-03: name/symbol NOT in WS payload — fetched from pump.fun API
FIX-04: MIN_MARKET_CAP lowered to 0 SOL (catch all new launches)
FIX-05: validate_token updated for actual field names
"""
import asyncio
import json
import sqlite3
import logging
import os
import urllib.request
import websockets
from datetime import datetime, timezone
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', '/app/data/sentinel.db')
PUMP_WS_URL = os.getenv('PUMP_WS_URL', 'wss://pumpportal.fun/api/data')
PUMP_API_KEY = os.getenv('PUMP_API_KEY', '')

# Filter thresholds (CEO updated Feb 28)
MIN_MARKET_CAP_SOL = float(os.getenv('MIN_MARKET_CAP_SOL', '56'))   # ~$4750 at current SOL price
MIN_VOLUME_USD = float(os.getenv('MIN_VOLUME_USD', '5900'))        # Filter dead coins
MIN_BUYS = int(os.getenv('MIN_BUYS', '10'))                       # Filter bot/dev bought coins

# Get live SOL price from CoinGecko (fallback to estimate)
def get_sol_price() -> float:
    """Fetch live SOL/USD price from CoinGecko."""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("solana", {}).get("usd", 85.0)
    except Exception:
        return 85.0  # Fallback

SOL_USD_ESTIMATE = get_sol_price()

if not DB_PATH.startswith('/app/'):
    logger.warning(f"DB_PATH={DB_PATH} - ensure volume mount is configured")


@dataclass
class TokenSignal:
    mint: str
    name: str
    symbol: str
    market_cap_sol: float
    initial_buy: float
    bonding_curve_key: str
    trader_public_key: str
    v_sol_in_bonding_curve: float
    v_tokens_in_bonding_curve: float
    risk_score: int
    risk_level: str
    signal_level: str
    detected_at: str
    alert_sent: bool = False


class SentinelDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mint TEXT UNIQUE NOT NULL,
                name TEXT,
                symbol TEXT,
                market_cap_sol REAL,
                initial_buy REAL,
                bonding_curve_key TEXT,
                trader_public_key TEXT,
                v_sol_in_bonding_curve REAL,
                v_tokens_in_bonding_curve REAL,
                risk_score INTEGER,
                risk_level TEXT,
                signal_level TEXT,
                detected_at TEXT,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def insert_or_update(self, signal: 'TokenSignal') -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                INSERT OR REPLACE INTO signals
                (mint, name, symbol, market_cap_sol, initial_buy, bonding_curve_key,
                 trader_public_key, v_sol_in_bonding_curve, v_tokens_in_bonding_curve,
                 risk_score, risk_level, signal_level, detected_at, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.mint, signal.name, signal.symbol,
                signal.market_cap_sol, signal.initial_buy, signal.bonding_curve_key,
                signal.trader_public_key, signal.v_sol_in_bonding_curve,
                signal.v_tokens_in_bonding_curve, signal.risk_score, signal.risk_level,
                signal.signal_level, signal.detected_at, 1 if signal.alert_sent else 0
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DB insert failed: {e}")
            return False
        finally:
            conn.close()

    def is_new_token(self, mint: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT 1 FROM signals WHERE mint = ?', (mint,))
        exists = cursor.fetchone() is not None
        conn.close()
        return not exists


def fetch_token_metadata(mint: str) -> dict:
    """Fetch name/symbol from pump.fun API since WS payload doesn't include them."""
    try:
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return {
                'name': data.get('name', 'Unknown'),
                'symbol': data.get('symbol', '???'),
            }
    except Exception as e:
        logger.debug(f"Metadata fetch failed for {mint}: {e}")
        return {'name': 'Unknown', 'symbol': '???'}


def sanitize(s: str, max_len: int = 64) -> str:
    if not s:
        return 'Unknown'
    s = s.replace('*', '').replace('`', '').replace('[', '').replace(']', '')
    return s[:max_len].strip()


def validate_token(token: dict) -> bool:
    """FIX-05: Validate against actual PumpPortal field names."""
    mint = token.get('mint', '')
    if not mint or len(mint) < 30 or len(mint) > 50:
        return False
    # Must be a create event
    if token.get('txType') != 'create':
        return False
    return True


def calculate_risk(token: dict) -> tuple:
    """Risk scoring based on available PumpPortal fields (SOL-based)."""
    score = 0

    # Initial buy size — large initial buy = potential pump & dump
    initial_buy = token.get('initialBuy', 0) or 0
    v_tokens = token.get('vTokensInBondingCurve', 1) or 1
    if v_tokens > 0:
        buy_ratio = initial_buy / (initial_buy + v_tokens)
        if buy_ratio > 0.3: score += 30
        elif buy_ratio > 0.15: score += 20
        elif buy_ratio > 0.05: score += 10

    # SOL in bonding curve — very low = very early / risky
    v_sol = token.get('vSolInBondingCurve', 0) or 0
    if v_sol < 1: score += 20
    elif v_sol < 5: score += 10
    elif v_sol < 20: score += 5

    # Market cap in SOL
    mc_sol = token.get('marketCapSol', 0) or 0
    if mc_sol < 1: score += 20
    elif mc_sol < 5: score += 15
    elif mc_sol < 20: score += 10

    if score >= 60: level = 'HIGH'
    elif score >= 35: level = 'MEDIUM'
    else: level = 'LOW'
    return min(score, 100), level


def determine_signal(market_cap_sol: float, risk_level: str) -> str:
    if market_cap_sol >= HIGH_MARKET_CAP_SOL:
        return 'HIGH'
    elif market_cap_sol >= MEDIUM_MARKET_CAP_SOL:
        return 'MEDIUM' if risk_level != 'LOW' else 'LOW'
    # Even tiny mcap tokens get logged — let alerts filter by level
    return 'LOW'


def format_alert(signal: 'TokenSignal') -> str:
    emoji = '🚨' if signal.signal_level == 'HIGH' else '⚠️'
    name = sanitize(signal.name, 64)
    symbol = sanitize(signal.symbol, 10)
    mc_usd = signal.market_cap_sol * SOL_USD_ESTIMATE
    return f"""{emoji} SENTINEL ALERT — {signal.signal_level} SIGNAL

Token: {name} (${symbol})
Mint: `{signal.mint[:20]}...`
Market Cap: {signal.market_cap_sol:.2f} SOL (~${mc_usd:,.0f})
Initial Buy: {signal.initial_buy:,.0f} tokens
Risk: {signal.risk_level} ({signal.risk_score}/100)
Detected: {signal.detected_at}
Pump.fun: https://pump.fun/{signal.mint}""".strip()


def send_alerts(db: SentinelDB):
    """Atomic alert — mark sent BEFORE sending to prevent duplicates."""
    from alerts import send_slack_alert  # Slack-only

    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute('''
            SELECT * FROM signals
            WHERE alert_sent = 0 AND signal_level IN ('HIGH', 'MEDIUM')
            LIMIT 10
        ''')
        rows = cursor.fetchall()

        if not rows:
            return

        ids_to_mark = [r['id'] for r in rows]
        conn.execute(
            f'UPDATE signals SET alert_sent = 1 WHERE id IN ({",".join("?" * len(ids_to_mark))})',
            ids_to_mark
        )
        conn.commit()

        for r in rows:
            signal = TokenSignal(
                mint=r['mint'], name=r['name'], symbol=r['symbol'],
                market_cap_sol=r['market_cap_sol'], initial_buy=r['initial_buy'],
                bonding_curve_key=r['bonding_curve_key'],
                trader_public_key=r['trader_public_key'],
                v_sol_in_bonding_curve=r['v_sol_in_bonding_curve'],
                v_tokens_in_bonding_curve=r['v_tokens_in_bonding_curve'],
                risk_score=r['risk_score'], risk_level=r['risk_level'],
                signal_level=r['signal_level'], detected_at=r['detected_at'],
                alert_sent=True
            )
            message = format_alert(signal)
            send_slack_alert(message)
            # send_telegram_alert(message)  # Disabled - Slack-only

    except Exception as e:
        logger.error(f"Alert error: {e}")
    finally:
        conn.close()


async def send_alerts_async(db: SentinelDB):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_alerts, db)


async def listen_forever():
    """WebSocket listener for PumpPortal."""
    logger.info(f"Connecting to {PUMP_WS_URL}...")
    db = SentinelDB(DB_PATH)

    while True:
        try:
            async with websockets.connect(PUMP_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                logger.info("Connected to PumpPortal WebSocket")

                # FIX-01: PumpPortal subscribe format — no "keys" field needed
                subscribe_msg = {"method": "subscribeNewToken"}
                if PUMP_API_KEY:
                    subscribe_msg["apiKey"] = PUMP_API_KEY

                await ws.send(json.dumps(subscribe_msg))
                logger.info("Subscribed to new token events")

                async for raw in ws:
                    try:
                        # FIX-01: PumpPortal sends FLAT JSON — no method/data wrapper
                        # Example: {"txType":"create","mint":"...","marketCapSol":31.3,...}
                        token = json.loads(raw)

                        if not isinstance(token, dict):
                            continue

                        if not validate_token(token):
                            continue

                        mint = token.get('mint', '')
                        if not db.is_new_token(mint):
                            continue

                        # FIX-02: Market cap is in SOL, not USD
                        market_cap_sol = token.get('marketCapSol', 0) or 0
                        if market_cap_sol < MIN_MARKET_CAP_SOL:
                            continue

                        # Volume filter using initialBuy (actual first-trade amount) as proxy
                        # FIND-16: vSolInBondingCurve was used before, always <$5k → filtered everything
                        initial_buy_sol = token.get('initialBuy', 0) or 0
                        volume_usd_est = initial_buy_sol * SOL_USD_ESTIMATE
                        if MIN_VOLUME_USD > 0 and volume_usd_est < MIN_VOLUME_USD:
                            logger.debug(f"Token filtered: initial buy ${volume_usd_est:,.0f} < ${MIN_VOLUME_USD:,.0f} min")
                            continue

                        # MIN_BUYS filter: Requires tracking trades over time
                        # For now, this is a placeholder - would need historical trade count
                        # Could be implemented via TimescaleDB query or Redis tracking

                        risk_score, risk_level = calculate_risk(token)
                        signal_level = determine_signal(market_cap_sol, risk_level)

                        # FIX-03: name/symbol not in WS payload — fetch from API
                        metadata = await asyncio.get_running_loop().run_in_executor(
                            None, fetch_token_metadata, mint
                        )

                        signal = TokenSignal(
                            mint=mint,
                            name=metadata.get('name', 'Unknown'),
                            symbol=metadata.get('symbol', '???'),
                            market_cap_sol=market_cap_sol,
                            initial_buy=token.get('initialBuy', 0) or 0,
                            bonding_curve_key=token.get('bondingCurveKey', ''),
                            trader_public_key=token.get('traderPublicKey', ''),
                            v_sol_in_bonding_curve=token.get('vSolInBondingCurve', 0) or 0,
                            v_tokens_in_bonding_curve=token.get('vTokensInBondingCurve', 0) or 0,
                            risk_score=risk_score,
                            risk_level=risk_level,
                            signal_level=signal_level,
                            detected_at=datetime.now(timezone.utc).isoformat(),
                        )

                        db.insert_or_update(signal)
                        logger.info(
                            f"📡 {signal.symbol} ({signal.mint[:8]}...): "
                            f"{signal.signal_level}/{signal.risk_level} | "
                            f"{market_cap_sol:.2f} SOL"
                        )

                        # Send alerts async (non-blocking)
                        task = asyncio.create_task(send_alerts_async(db))
                        task.add_done_callback(
                            lambda t: logger.error(f"Alert task failed: {t.exception()}")
                            if t.exception() else None
                        )

                        # Send to AXIOM via UAI
                        try:
                            from sentinel_to_axiom import send_to_axiom
                            await asyncio.get_running_loop().run_in_executor(
                                None, send_to_axiom, {
                                    'symbol': signal.symbol,
                                    'name': signal.name,
                                    'mint': signal.mint,
                                    'market_cap_sol': signal.market_cap_sol,
                                    'market_cap_usd': signal.market_cap_sol * SOL_USD_ESTIMATE,
                                    'risk_score': signal.risk_score,
                                    'risk_level': signal.risk_level,
                                    'signal_level': signal.signal_level,
                                    'detected_at': signal.detected_at,
                                }
                            )
                        except Exception as e:
                            logger.error(f"AXIOM send failed: {e}")

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON: {raw[:100]}")
                    except Exception as e:
                        logger.error(f"Message processing error: {e}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket closed: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == '__main__':
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

        def log_message(self, format, *args):
            pass

    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    logger.info("SENTINEL started — WebSocket mode")
    asyncio.run(listen_forever())
