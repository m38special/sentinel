"""
Enhanced Market Analysis & Simulation Script
SENTINEL Phase 8 | LiQUiD SOUND
"""
import os
import json
import logging
from datetime import datetime, timedelta
from tasks import app

log = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_crypto_prices():
    """Fetch real-time crypto prices from CoinGecko"""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return {coin['symbol'].upper(): coin for coin in data}
    except Exception as e:
        log.warning(f"CoinGecko API error: {e}")
        return {}


def get_fear_greed():
    """Fetch Fear & Greed index"""
    try:
        import urllib.request
        url = "https://alternative.me/crypto/api/fear_and_greed/latest.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return int(data.get('data', {}).get('value', 50))
    except:
        return 50


def get_solana_data():
    """Fetch Solana-specific data"""
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/coins/solana?localization=false&tickers=false&community_data=false&developer_data=false"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return {
                'price': data.get('market_data', {}).get('current_price', {}).get('usd', 0),
                'change_24h': data.get('market_data', {}).get('price_change_percentage_24h', 0),
                'volume': data.get('market_data', {}).get('total_volume', 0),
                'market_cap': data.get('market_data', {}).get('market_cap', 0)
            }
    except Exception as e:
        log.warning(f"Solana API error: {e}")
        return {'price': 0, 'change_24h': 0, 'volume': 0, 'market_cap': 0}


def analyze_market():
    """Full market analysis with external data"""
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Fetch external data
    prices = get_crypto_prices()
    fear_greed = get_fear_greed()
    solana = get_solana_data()
    
    analysis = {
        'timestamp': datetime.utcnow().isoformat(),
        'fear_greed_index': fear_greed,
        'sentiment': 'neutral',
        'solana': solana,
        'top_coins': [],
        'recommendations': []
    }
    
    # Determine sentiment
    if fear_greed > 70:
        analysis['sentiment'] = 'extreme_greed'
    elif fear_greed > 60:
        analysis['sentiment'] = 'greed'
    elif fear_greed < 30:
        analysis['sentiment'] = 'extreme_fear'
    elif fear_greed < 40:
        analysis['sentiment'] = 'fear'
    
    # Get top coins
    if prices:
        analysis['top_coins'] = [
            {'symbol': s, 'price': p.get('current_price', 0), 'change': p.get('price_change_percentage_24h', 0)}
            for s, p in list(prices.items())[:10]
        ]
    
    # Generate recommendations
    if solana.get('change_24h', 0) > 5:
        analysis['recommendations'].append({'action': 'BULLISH', 'reason': 'SOL up >5%'})
    elif solana.get('change_24h', 0) < -5:
        analysis['recommendations'].append({'action': 'BEARISH', 'reason': 'SOL down >5%'})
    
    if fear_greed < 30:
        analysis['recommendations'].append({'action': 'ACCUMULATE', 'reason': 'Extreme fear - potential bottom'})
    elif fear_greed > 70:
        analysis['recommendations'].append({'action': 'TAKE_PROFIT', 'reason': 'Extreme greed - potential top'})
    
    # Store in Redis
    r.set('market:analysis:latest', json.dumps(analysis))
    r.lpush('market:analysis:history', json.dumps(analysis))
    r.ltrim('market:analysis:history', 0, 99)
    
    log.info(f"Market analysis complete: {analysis['sentiment']}, {len(analysis['recommendations'])} recommendations")
    return analysis


@app.task(name='tasks.market_analysis.run_analysis', bind=True, max_retries=2, queue='sentinel')
def run_market_analysis(self):
    """Celery task for scheduled market analysis"""
    return analyze_market()


# Schedule: Every hour
from celery.schedules import crontab

app.conf.beat_schedule = {
    **app.conf.beat_schedule,
    "market-analysis-hourly": {
        "task": "tasks.market_analysis.run_analysis",
        "schedule": crontab(minute=0),  # Every hour
        "options": {"queue": "sentinel"},
    },
}


if __name__ == "__main__":
    result = analyze_market()
    print(json.dumps(result, indent=2))
