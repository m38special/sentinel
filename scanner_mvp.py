"""
SENTINEL MVP — Pump.fun Token Scanner (CIPHER-FIXED)
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

# CHANGE 1: SOL-denominated thresholds
MIN_MARKET_CAP_SOL = float(os.getenv('MIN_MARKET_CAP_SOL', '0'))
HIGH_MARKET_CAP_SOL = float(os.getenv('HIGH_MARKET_CAP_SOL', '100'))
MEDIUM_MARKET_CAP_SOL = float(os.getenv('MEDIUM_MARKET_CAP_SOL', '10'))
SOL_USD_ESTIMATE = 150.0

# BUG-09: Ensure DB directory exists
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


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
    if not s:
        return 'Unknown'
    # BUG-07: Truncate instead of rejecting
    s = s.replace('*', '').replace('`', '').replace('[', '').replace(']', '')
    return s[:max_len].strip()


def validate_token(token: dict) -> bool:
    # CHANGE 2: Filter by txType == 'create'
    mint = token.get('mint', '')
    if not mint or len(mint) < 30 or len(mint) > 50:
        return False
    if token.get('txType') != 'create':
        return False
    return True


# CHANGE 4: Fetch name/symbol from pump.fun API
def fetch_token_metadata(mint: str) -> dict:
    import urllib.request
    try:
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return {'name': data.get('name', 'Unknown'), 'symbol': data.get('symbol', '???')}
    except Exception as e:
        logger.debug(f"Metadata fetch failed for {mint}: {e}")
        return {'name': 'Unknown', 'symbol': '???'}


def calculate_risk(token: dict) -> tuple[int, str]:
    """BUG-13: Adapted for creation-time fields"""
    score = 0
    
    # Use available fields: mint, symbol, name, marketCapSol, solAmount, vSolInBondingCurve
    market_cap_sol = token.get('marketCapSol', 0) or 0
    
    # BUG-02: These fields don't exist in creation event - estimate risk from SOL amount
    sol_in_curve = token.get('vSolInBondingCurve', 0) or 0
    
    # Higher SOL in bonding curve = more early interest = lower risk
    if sol_in_curve > 50:
        score += 20
    elif sol_in_curve > 20:
        score += 10
    elif sol_in_curve > 5:
        score += 5
    
    # New token with low market cap = higher risk
    if market_cap_sol < 5:
        score += 40
    elif market_cap_sol < 15:
        score += 25
    elif market_cap_sol < 30:
        score += 15
    
    if score >= 70: level = 'HIGH'
    elif score >= 40: level = 'MEDIUM'
    else: level = 'LOW'
    return min(score, 100), level


def determine_signal(market_cap_sol: float, risk_level: str) -> str:
    """BUG-14: Use SOL-denominated thresholds"""
    if market_cap_sol >= HIGH_SIGNAL_SOL:
        return 'HIGH'
    elif market_cap_sol >= MEDIUM_SIGNAL_SOL:
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
Market Cap: {signal.market_cap:.2f} SOL
Risk: {signal.risk_level} ({signal.risk_score}/100)
Detected: {signal.detected_at}
    """.strip()


def send_alerts(db: SentinelDB):
    """BUG-04, BUG-05: Fixed - atomic alert"""
    import sqlite3
    
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
            conn.close()
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
    """BUG-04: Properly defined async wrapper"""
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
            async with websockets.connect(PUMP_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                logger.info("Connected to PumpPortal WebSocket")
                
                # BUG-10: Fixed subscription message
                subscribe_msg = {"method": "subscribeNewToken"}
                if PUMP_API_KEY:
                    subscribe_msg["apiKey"] = PUMP_API_KEY
                
                await ws.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to new token events on {NETWORK}")
                
                # Listen for messages
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        
                        # BUG-01: Check for txType == 'create' in flat JSON
                        # PumpPortal sends flat JSON with txType field
                        if data.get('txType') == 'create':
                            token = data  # Flat structure
                        elif data.get('method') == 'newToken' and 'data' in data:
                            token = data.get('data', {})
                        else:
                            continue
                        
                        if not validate_token(token):
                            continue
                        
                        mint = token.get('mint', '')
                        if not mint or not db.is_new_token(mint):
                            continue
                        
                        # BUG-02: Use correct field names
                        market_cap_sol = token.get('marketCapSol', 0) or 0
                        if market_cap_sol < MIN_MARKET_CAP_SOL:
                            continue
                        
                        risk_score, risk_level = calculate_risk(token)
                        signal_level = determine_signal(market_cap_sol, risk_level)
                        
                        # CHANGE 3: name/symbol not in WS — fetch from pump.fun API
                        metadata = await asyncio.get_running_loop().run_in_executor(
                            None, fetch_token_metadata, mint
                        )
                        
                        signal = TokenSignal(
                            mint=mint,
                            name=metadata.get('name', 'Unknown'),
                            symbol=metadata.get('symbol', '???'),
                            market_cap=market_cap_sol,
                            fdv=0,  # Not available in creation event
                            holders=0,  # Not available
                            volume_30m=0,  # Not available
                            tx_buy=0,
                            tx_sell=0,
                            risk_score=risk_score,
                            risk_level=risk_level,
                            signal_level=signal_level,
                            detected_at=datetime.now(timezone.utc).isoformat(),
                        )
                        
                        db.insert_or_update(signal)
                        logger.info(f"📡 {signal.symbol}: {signal.signal_level}/{signal.risk_level}")
                        
                        # BUG-04, BUG-05: Properly call async alerts
                        task = asyncio.create_task(send_alerts_async(db))
                        task.add_done_callback(lambda t: logger.error(f"Alert task failed: {t.exception()}") if t.exception() else None)
                        
                        # Send to AXIOM via UAI
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
    
    logger.info("SENTINEL started — WebSocket mode (CIPHER-FIXED)")
    asyncio.run(listen_forever())
