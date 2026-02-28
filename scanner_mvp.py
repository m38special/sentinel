"""
SENTINEL MVP — Pump.fun Token Scanner
Real-time WebSocket listener for new token events
"""
import asyncio
import json
import sqlite3
import logging
import os
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
NETWORK = 'solana'

# BUG-02: Lower threshold to catch new launches
MIN_MARKET_CAP = 0
HIGH_MARKET_CAP = 500_000
MEDIUM_MARKET_CAP = 50_000

# F-07: Validate DB path at startup
if DB_PATH == 'sentinel.db' or not DB_PATH.startswith('/app/'):
    logger.warning(f"DB_PATH={DB_PATH} - ensure volume mount is configured")


@dataclass
class TokenSignal:
    mint: str
    name: str
    symbol: str
    market_cap: float
    fdv: float
    holders: int
    volume_30m: float
    tx_buy: int
    tx_sell: int
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
                market_cap REAL,
                fdv REAL,
                holders INTEGER,
                volume_30m REAL,
                tx_buy INTEGER,
                tx_sell INTEGER,
                risk_score INTEGER,
                risk_level TEXT,
                signal_level TEXT,
                detected_at TEXT,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def insert_or_update(self, signal: TokenSignal) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                INSERT OR REPLACE INTO signals 
                (mint, name, symbol, market_cap, fdv, holders, volume_30m,
                 tx_buy, tx_sell, risk_score, risk_level, signal_level, detected_at, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (signal.mint, signal.name, signal.symbol, signal.market_cap,
                  signal.fdv, signal.holders, signal.volume_30m, signal.tx_buy,
                  signal.tx_sell, signal.risk_score, signal.risk_level,
                  signal.signal_level, signal.detected_at, 1 if signal.alert_sent else 0))
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
    
    def get_unalerted(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            'SELECT * FROM signals WHERE alert_sent = 0 AND signal_level IN ("HIGH", "MEDIUM")'
        )
        rows = cursor.fetchall()
        conn.close()
        return [TokenSignal(
            mint=r['mint'], name=r['name'], symbol=r['symbol'],
            market_cap=r['market_cap'], fdv=r['fdv'], holders=r['holders'],
            volume_30m=r['volume_30m'], tx_buy=r['tx_buy'], tx_sell=r['tx_sell'],
            risk_score=r['risk_score'], risk_level=r['risk_level'],
            signal_level=r['signal_level'], detected_at=r['detected_at'],
            alert_sent=bool(r['alert_sent'])
        ) for r in rows] if rows else []


def sanitize(s: str, max_len: int = 64) -> str:
    # NEW-04: Don't strip _ since validate_token() now allows it
    if not s:
        return 'Unknown'
    s = s.replace('*', '').replace('`', '').replace('[', '').replace(']', '')
    return s[:max_len].strip()


def validate_token(token: dict) -> bool:
    # REAL-05: Allow hyphens and underscores in symbols
    mint = token.get('mint', '')
    if not mint or len(mint) > 44:
        return False
    symbol = token.get('symbol', '')
    if not symbol or len(symbol) > 10:
        return False
    # Allow alphanumeric, hyphens, underscores
    if not symbol.replace('$', '').replace('-', '').replace('_', '').isalnum():
        return False
    name = token.get('name', '')
    if len(name) > 64:
        return False
    return True


def calculate_risk(token: dict) -> tuple[int, str]:
    score = 0
    holders = token.get('holder_count', 0) or 0
    if holders < 10: score += 30
    elif holders < 50: score += 20
    elif holders < 100: score += 10
    elif holders < 500: score += 5
    
    mc = token.get('usd_market_cap', 0) or 0
    fdv = token.get('usd_fdv', 0) or 0
    if mc > 0:
        ratio = fdv / mc
        if ratio > 10: score += 30
        elif ratio > 5: score += 20
        elif ratio > 2: score += 10
        elif ratio > 1: score += 5
    
    buy = token.get('tx_count_buy', 0) or 0
    sell = token.get('tx_count_sell', 0) or 0
    if sell > buy * 2: score += 20
    elif sell > buy: score += 10
    
    vol = token.get('volume_30m', 0) or 0
    if mc > 0 and vol > 0:
        turnover = vol / mc
        if turnover < 0.01: score += 20
        elif turnover < 0.05: score += 15
        elif turnover < 0.1: score += 10
        elif turnover < 0.2: score += 5
    
    if score >= 70: level = 'HIGH'
    elif score >= 40: level = 'MEDIUM'
    else: level = 'LOW'
    return min(score, 100), level


def determine_signal(market_cap: float, risk_level: str) -> str:
    if market_cap >= HIGH_MARKET_CAP:
        return 'HIGH'
    elif market_cap >= MEDIUM_MARKET_CAP:
        return 'MEDIUM' if risk_level != 'LOW' else 'LOW'
    return 'LOW'


def format_alert(signal: TokenSignal) -> str:
    emoji = '🚨' if signal.signal_level == 'HIGH' else '⚠️'
    name = sanitize(signal.name, 64)
    symbol = sanitize(signal.symbol, 10)
    mint = sanitize(signal.mint, 44)
    return f"""
{emoji} SENTINEL ALERT — {signal.signal_level} SIGNAL

Token: {name} (${symbol})
Mint: `{mint[:20]}...`
Market Cap: ${signal.market_cap:,.0f}
Risk: {signal.risk_level} ({signal.risk_score}/100)
Detected: {signal.detected_at}
    """.strip()


def send_alerts(db: SentinelDB):
    """NEW-01: Atomic alert - mark sent BEFORE sending to prevent duplicates"""
    import sqlite3
    
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Atomic: select and mark in one transaction
        cursor = conn.execute('''
            SELECT * FROM signals 
            WHERE alert_sent = 0 AND signal_level IN ('HIGH', 'MEDIUM')
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return
        
        # Mark as sent BEFORE alerting (prevents race condition)
        ids_to_mark = [r['id'] for r in rows]
        conn.execute(
            f'UPDATE signals SET alert_sent = 1 WHERE id IN ({",".join("?" * len(ids_to_mark))})',
            ids_to_mark
        )
        conn.commit()
        
        # Now send alerts (safe - duplicates won't be picked up)
        for r in rows:
            signal = TokenSignal(
                mint=r['mint'], name=r['name'], symbol=r['symbol'],
                market_cap=r['market_cap'], fdv=r['fdv'], holders=r['holders'],
                volume_30m=r['volume_30m'], tx_buy=r['tx_buy'], tx_sell=r['tx_sell'],
                risk_score=r['risk_score'], risk_level=r['risk_level'],
                signal_level=r['signal_level'], detected_at=r['detected_at'],
                alert_sent=True
            )
            message = format_alert(signal)
            send_slack_alert(message)
            send_telegram_alert(message)
            
    except Exception as e:
        logger.error(f"Alert error: {e}")
    finally:
        conn.close()


async def send_alerts_async(db: SentinelDB):
    """NEW-03: Use get_running_loop() instead of deprecated get_event_loop()"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_alerts, db)


async def listen_forever():
    """WebSocket listener for PumpPortal"""
    logger.info(f"Connecting to {PUMP_WS_URL}...")
    db = SentinelDB(DB_PATH)
    
    while True:
        try:
            # REAL-04: Add keepalive to prevent Railway dropping idle connections
            async with websockets.connect(PUMP_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                logger.info("Connected to PumpPortal WebSocket")
                
                # Subscribe to new token events
                # REAL-01: PumpPortal expects "keys": [] or no keys field for global subscription
                subscribe_msg = {
                    "method": "subscribeNewToken",
                    "keys": []
                }
                if PUMP_API_KEY:
                    subscribe_msg["apiKey"] = PUMP_API_KEY
                
                await ws.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to new token events on {NETWORK}")
                
                # Listen for messages
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        
                        # REAL-02: Only process actual newToken events, not broad 'data' messages
                        # Filter out ACKs, errors, pings
                        if data.get('method') == 'newToken' and 'data' in data:
                            token = data.get('data', {})
                            
                            if not validate_token(token):
                                continue
                            
                            mint = token.get('mint', '')
                            if not mint or not db.is_new_token(mint):
                                continue
                            
                            market_cap = token.get('usd_market_cap', 0) or 0
                            if market_cap < MIN_MARKET_CAP:
                                continue
                            
                            risk_score, risk_level = calculate_risk(token)
                            signal_level = determine_signal(market_cap, risk_level)
                            
                            signal = TokenSignal(
                                mint=mint,
                                name=token.get('name', 'Unknown'),
                                symbol=token.get('symbol', '???'),
                                market_cap=market_cap,
                                fdv=token.get('usd_fdv', 0) or 0,
                                holders=token.get('holder_count', 0) or 0,
                                volume_30m=token.get('volume_30m', 0) or 0,
                                tx_buy=token.get('tx_count_buy', 0) or 0,
                                tx_sell=token.get('tx_count_sell', 0) or 0,
                                risk_score=risk_score,
                                risk_level=risk_level,
                                signal_level=signal_level,
                                detected_at=datetime.now(timezone.utc).isoformat(),  # REAL-06
                            )
                            
                            db.insert_or_update(signal)
                            logger.info(f"📡 {signal.symbol}: {signal.signal_level}/{signal.risk_level}")
                            
                            # REAL-03: Don't block the listener - send alerts async
                            # NEW-02: Add done callback to catch exceptions
                            task = asyncio.create_task(send_alerts_async(db))
                            task.add_done_callback(lambda t: logger.error(f"Alert task failed: {t.exception()}") if t.exception() else None)
                            
                            # Send to AXIOM via UAI for quant analysis
                            try:
                                from sentinel_to_axiom import send_to_axiom
                                asyncio.create_task(asyncio.get_running_loop().run_in_executor(
                                    None, send_to_axiom, {
                                        'symbol': signal.symbol,
                                        'name': signal.name,
                                        'mint': signal.mint,
                                        'market_cap': signal.market_cap,
                                        'risk_score': signal.risk_score,
                                        'risk_level': signal.risk_level,
                                        'signal_level': signal.signal_level,
                                        'detected_at': signal.detected_at
                                    }
                                ))
                            except Exception as e:
                                logger.error(f"AXIOM send failed: {e}")
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON: {raw[:100]}")
                        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket closed: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == '__main__':
    # Health check server for Railway
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
