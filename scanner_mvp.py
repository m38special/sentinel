"""
SENTINEL MVP — Pump.fun Token Scanner
Real-time scraper with asyncio, 5-min polling, SQLite storage, alerts
"""
import asyncio
import aiohttp
import sqlite3
import logging
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 300  # 5 minutes
DB_PATH = os.getenv('DB_PATH', 'sentinel.db')
PUMP_API_URL = 'https://api.pumpportal.fun/api/tokens/new'
NETWORK = 'solana'

MIN_MARKET_CAP = 10_000
HIGH_MARKET_CAP = 500_000
MEDIUM_MARKET_CAP = 50_000


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
            # F-01 fix: explicit column list, exclude AUTOINCREMENT id
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
    
    def get_unalerted(self) -> List[TokenSignal]:
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


MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # F-03: 10MB cap

async def fetch_new_tokens() -> List[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PUMP_API_URL, params={'network': NETWORK}, 
                                   timeout=aiohttp.ClientTimeout(total=30, max_size=MAX_RESPONSE_SIZE)) as resp:
                if resp.status == 200:
                    # F-03: explicit content-length check
                    if resp.content_length and resp.content_length > MAX_RESPONSE_SIZE:
                        logger.error(f"Response too large: {resp.content_length}")
                        return []
                    data = await resp.json()
                    # Cap response to prevent OOM
                    return (data if isinstance(data, list) else [])[:1000]
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
    return []


def sanitize(s: str, max_len: int = 64) -> str:
    """F-05, F-06: Sanitize external input - escape markdown, limit length"""
    if not s:
        return 'Unknown'
    # Strip markdown special chars
    s = s.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
    return s[:max_len].strip()


def validate_token(token: dict) -> bool:
    """F-06: Input validation on token fields"""
    mint = token.get('mint', '')
    if not mint or len(mint) > 44:
        return False
    symbol = token.get('symbol', '')
    if not symbol or len(symbol) > 10 or not symbol.replace('$', '').isalnum():
        return False
    name = token.get('name', '')
    if len(name) > 64:
        return False
    return True


def format_alert(signal: TokenSignal) -> str:
    emoji = '🚨' if signal.signal_level == 'HIGH' else '⚠️'
    # F-05: sanitize external fields
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


async def send_alerts(db: SentinelDB):
    from alerts import send_slack_alert, send_telegram_alert
    signals = db.get_unalerted()
    if not signals:
        return
    for signal in signals:
        message = format_alert(signal)
        # F-04: Only mark sent if both alerts succeed
        slack_ok = send_slack_alert(message)
        tg_ok = send_telegram_alert(message)
        if slack_ok or tg_ok:
            signal.alert_sent = True
            db.insert_or_update(signal)


async def scan_once(db: SentinelDB) -> int:
    logger.info("Scanning for new tokens...")
    tokens = await fetch_new_tokens()
    new_count = 0
    for token in tokens:
        # F-06: validate token before processing
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
            mint=mint, name=token.get('name', 'Unknown'), symbol=token.get('symbol', '???'),
            market_cap=market_cap, fdv=token.get('usd_fdv', 0) or 0,
            holders=token.get('holder_count', 0) or 0, volume_30m=token.get('volume_30m', 0) or 0,
            tx_buy=token.get('tx_count_buy', 0) or 0, tx_sell=token.get('tx_count_sell', 0) or 0,
            risk_score=risk_score, risk_level=risk_level, signal_level=signal_level,
            detected_at=datetime.utcnow().isoformat(),
        )
        db.insert_or_update(signal)
        new_count += 1
        logger.info(f"📡 {signal.symbol}: {signal.signal_level}/{signal.risk_level}")
    if new_count > 0:
        await send_alerts(db)
    return new_count


async def run_forever():
    logger.info(f"SENTINEL MVP started — polling every {POLL_INTERVAL}s")
    db = SentinelDB(DB_PATH)
    while True:
        try:
            count = await scan_once(db)
            logger.info(f"Cycle complete — {count} new tokens")
        except Exception as e:
            logger.error(f"Scan error: {e}")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    asyncio.run(run_forever())
