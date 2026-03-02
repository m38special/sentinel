"""
Rukia - Live Trading Bot
LiQUiD SOUND

Real-time pricing from CoinGecko API
"""
import os
import json
import logging
import urllib.request
from datetime import datetime

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Trading pairs to track
TRACKED_PAIRS = [
    'solana', 'bonk', 'wif', 'jupiter', 'raydium', 
    'orca', 'msol', 'stsol', 'usd-coin', 'tether'
]

COINGECKO_API = "https://api.coingecko.com/api/v3"


def get_prices():
    """Fetch live prices from CoinGecko"""
    try:
        ids = ','.join(TRACKED_PAIRS)
        url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&sparkline=false"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Rukia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return {coin['symbol'].upper(): coin for coin in data}
    except Exception as e:
        log.error(f"CoinGecko API error: {e}")
        return {}


def get_solana_price():
    """Get Solana-specific data"""
    try:
        url = f"{COINGECKO_API}/coins/solana?localization=false&tickers=false&community_data=false&developer_data=false"
        req = urllib.request.Request(url, headers={'User-Agent': 'Rukia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return {
                'price': data.get('market_data', {}).get('current_price', {}).get('usd', 0),
                'change_24h': data.get('market_data', {}).get('price_change_percentage_24h', 0),
                'volume': data.get('market_data', {}).get('total_volume', 0),
                'market_cap': data.get('market_data', {}).get('market_cap', 0),
                'high_24h': data.get('market_data', {}).get('high_24h', {}).get('usd', 0),
                'low_24h': data.get('market_data', {}).get('low_24h', {}).get('usd', 0),
            }
    except Exception as e:
        log.error(f"Solana API error: {e}")
        return {}


def update_trading_data():
    """Update all trading data in Redis"""
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Get prices
    prices = get_prices()
    solana = get_solana_price()
    
    # Store current prices
    r.set('rukia:prices:latest', json.dumps(prices))
    r.set('rukia:solana', json.dumps(solana))
    
    # Store history
    r.lpush('rukia:prices:history', json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'prices': {s: p.get('current_price', 0) for s, p in prices.items()},
        'solana': solana
    }))
    r.ltrim('rukia:prices:history', 0, 288)  # Keep 24 hours (5 min intervals)
    
    log.info(f"Updated trading data: {len(prices)} coins, SOL: ${solana.get('price', 0):.2f}")
    
    return {
        'prices_count': len(prices),
        'solana_price': solana.get('price', 0),
        'solana_change_24h': solana.get('change_24h', 0)
    }


def get_signals():
    """Generate trading signals based on price action"""
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    solana = json.loads(r.get('rukia:solana') or '{}')
    prices = json.loads(r.get('rukia:prices:latest') or '{}')
    
    signals = []
    
    # SOL signals
    if solana:
        change = solana.get('change_24h', 0)
        if change > 5:
            signals.append({'token': 'SOL', 'signal': 'BULLISH', 'reason': f'+{change:.1f}% today'})
        elif change < -5:
            signals.append({'token': 'SOL', 'signal': 'BUY', 'reason': f'Oversold {change:.1f}%'})
    
    # Other tokens
    for symbol, data in prices.items():
        change = data.get('price_change_percentage_24h', 0)
        if change > 10:
            signals.append({'token': symbol, 'signal': 'BULLISH', 'reason': f'+{change:.1f}%'})
        elif change < -10:
            signals.append({'token': symbol, 'signal': 'BUY', 'reason': f'Oversold {change:.1f}%'})
    
    return signals


if __name__ == "__main__":
    result = update_trading_data()
    print(json.dumps(result, indent=2))
    signals = get_signals()
    print(f"\nSignals: {signals}")
