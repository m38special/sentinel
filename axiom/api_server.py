"""
AXIOM Analytics API - Free Tier Mock Server
Phase 4: Developer Tier Free API Launch
"""
import os
import json
import uuid
import hashlib
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
API_KEYS_FILE = os.path.join(os.path.dirname(__file__), 'api_keys.json')
RATE_LIMITS = {
    'free': {'requests_per_day': 100, 'requests_per_second': 1},
    'pro': {'requests_per_day': 10000, 'requests_per_second': 10},
    'enterprise': {'requests_per_day': -1, 'requests_per_second': -1}
}

# In-memory rate limiting (reset daily)
rate_limit_store = {}


def load_api_keys():
    """Load API keys from storage"""
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_api_keys(keys):
    """Save API keys to storage"""
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)


def generate_api_key(tier='free'):
    """Generate a new API key"""
    raw_key = f"{tier}_{uuid.uuid4().hex}_{time.time()}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:32]
    return f"ax_{tier[0].upper()}_{key_hash}"


def validate_api_key(api_key):
    """Validate API key and return tier info"""
    keys = load_api_keys()
    
    for key, info in keys.items():
        if key == api_key:
            return {'valid': True, 'tier': info['tier'], 'name': info.get('name', 'Unnamed')}
    
    return {'valid': False, 'tier': None}


def rate_limit_check(api_key, tier):
    """Check rate limits for API key"""
    now = time.time()
    today = datetime.now().date().isoformat()
    
    key_limit_key = f"{api_key}:{today}"
    
    if api_key not in rate_limit_store:
        rate_limit_store[api_key] = {'daily': {}, 'secondly': {'count': 0, 'timestamp': now}}
    
    daily_data = rate_limit_store[api_key]['daily']
    second_data = rate_limit_store[api_key]['secondly']
    
    # Reset daily if new day
    if today not in daily_data:
        daily_data.clear()
        daily_data[today] = 0
    
    # Check daily limit
    limits = RATE_LIMITS.get(tier, RATE_LIMITS['free'])
    daily_limit = limits['requests_per_day']
    
    if daily_limit > 0 and daily_data[today] >= daily_limit:
        return False, 'daily_limit_exceeded'
    
    # Check secondly limit
    if now - second_data['timestamp'] < 1:
        second_data['count'] += 1
        if second_data['count'] > limits['requests_per_second']:
            return False, 'rate_limit_exceeded'
    else:
        second_data['count'] = 1
        second_data['timestamp'] = now
    
    # Increment counters
    daily_data[today] += 1
    
    return True, None


def require_api_key(f):
    """Decorator to require valid API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': {'code': 'MISSING_API_KEY', 'message': 'API key required'}}), 401
        
        validation = validate_api_key(api_key)
        
        if not validation['valid']:
            return jsonify({'error': {'code': 'INVALID_API_KEY', 'message': 'Invalid API key'}}), 401
        
        # Rate limit check
        allowed, error = rate_limit_check(api_key, validation['tier'])
        if not allowed:
            return jsonify({
                'error': {'code': 'RATE_LIMITED', 'message': f'Rate limit exceeded: {error}'},
                'meta': {'retry_after': 3600}
            }), 429
        
        g.api_key = api_key
        g.tier = validation['tier']
        
        return f(*args, **kwargs)
    return decorated


# ==================== FREE TIER ENDPOINTS ====================

@app.route('/v1/whale-tracking', methods=['GET'])
@require_api_key
def get_whale_tracking():
    """
    Get whale activity data (Free tier: delayed 1h, max 20 results)
    """
    chain = request.args.get('chain', 'all')
    min_volume = float(request.args.get('min_volume_usd', 10000))
    timeframe = request.args.get('timeframe', '24h')
    limit = min(int(request.args.get('limit', 20)), 20)  # Free tier cap
    
    # Mock data - in production, this would query real data with 1h delay
    mock_whales = [
        {
            'tx_hash': f"tx_{uuid.uuid4().hex[:16]}",
            'wallet_address': f"{'ABC' if i < 3 else 'DEF'}{uuid.uuid4().hex[:20]}...",
            'chain': 'solana' if i % 2 == 0 else 'ethereum',
            'timestamp': (datetime.utcnow() - timedelta(hours=1, minutes=i*10)).isoformat() + 'Z',
            'volume_usd': 50000 + (i * 10000),
            'tokens': ['SOL', 'USDC'] if i % 2 == 0 else ['ETH', 'USDT'],
            'action': 'buy' if i % 3 != 0 else 'sell',
            'profit_loss_estimated': (-5000 + i * 2000) if i % 3 != 0 else None
        }
        for i in range(limit)
    ]
    
    # Filter by chain if specified
    if chain != 'all':
        mock_whales = [w for w in mock_whales if w['chain'] == chain]
    
    return jsonify({
        'data': mock_whales,
        'meta': {
            'cursor': None,
            'has_more': False,
            'total': len(mock_whales),
            'tier': g.tier,
            'note': 'Free tier: data delayed 1 hour'
        }
    })


@app.route('/v1/yield-signals', methods=['GET'])
@require_api_key
def get_yield_signals():
    """
    Get yield optimization signals (Free tier: top 10 pools only)
    """
    chain = request.args.get('chain', 'all')
    min_apy = float(request.args.get('min_apy', 0))
    risk_level = request.args.get('risk_level', 'all')
    limit = min(int(request.args.get('limit', 10)), 10)  # Free tier cap
    
    # Mock yield data - top pools
    mock_pools = [
        {
            'pool_id': f"pool_{i+1}",
            'protocol': ['Raydium', 'Orca', 'Jupiter', 'Marinade', 'Solend'][i % 5],
            'chain': 'solana',
            'tokens': ['SOL-USDC', 'SOL-ETH', 'mSOL-SOL', 'stSOL-SOL', 'UST-USDC'][i % 5],
            'apy': 8.5 - (i * 0.5),
            'apy_30d_avg': 7.2 - (i * 0.3),
            'tvl_usd': 100000000 - (i * 10000000),
            'risk_score': 25 + (i * 5),
            'risk_factors': ['smart_contract', 'impermanent_loss'] if i > 5 else ['smart_contract'],
            'impermanent_loss_risk': 'low' if i < 3 else 'medium',
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        for i in range(limit)
    ]
    
    # Filter by APY
    mock_pools = [p for p in mock_pools if p['apy'] >= min_apy]
    
    return jsonify({
        'data': mock_pools,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'tier': g.tier,
        'note': 'Free tier: top 10 pools only'
    })


@app.route('/v1/sentiment', methods=['GET'])
@require_api_key
def get_sentiment():
    """
    Get market sentiment (Free tier: basic, 24h only)
    """
    asset = request.args.get('asset', 'BTC')
    timeframe = request.args.get('timeframe', '24h')
    
    # Free tier restricted to 24h only
    if timeframe != '24h':
        timeframe = '24h'
    
    # Mock sentiment data
    sentiment_score = 35 + (hash(asset) % 50)
    
    return jsonify({
        'asset': asset.upper(),
        'sentiment': {
            'score': sentiment_score,
            'label': 'neutral' if 30 < sentiment_score < 70 else ('fear' if sentiment_score < 30 else 'greed'),
            'confidence': 0.72
        },
        'sources': [
            {'source': 'twitter', 'score': sentiment_score - 5, 'volume': 15000 + (hash(asset) % 10000), 'trending': True},
            {'source': 'reddit', 'score': sentiment_score + 10, 'volume': 8000, 'trending': False},
            {'source': 'onchain', 'score': sentiment_score - 15, 'volume': 5000, 'trending': True}
        ],
        'key_themes': ['yield_farming', 'defi', 'layer2', 'staking'],
        'timeframe': timeframe,
        'tier': g.tier,
        'note': 'Free tier: 24h timeframe only'
    })


# ==================== AUTH ENDPOINTS ====================

@app.route('/v1/auth/register', methods=['POST'])
def register():
    """Register for free API key"""
    data = request.get_json() or {}
    
    email = data.get('email', '').strip()
    name = data.get('name', 'Developer')
    
    if not email or '@' not in email:
        return jsonify({'error': {'code': 'INVALID_EMAIL', 'message': 'Valid email required'}}), 400
    
    keys = load_api_keys()
    
    # Check if email already registered
    for key, info in keys.items():
        if info.get('email') == email:
            return jsonify({
                'error': {'code': 'EMAIL_EXISTS', 'message': 'Email already registered'},
                'api_key': key
            }), 409
    
    # Generate new free tier key
    api_key = generate_api_key('free')
    
    keys[api_key] = {
        'tier': 'free',
        'email': email,
        'name': name,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'requests_today': 0
    }
    
    save_api_keys(keys)
    
    logger.info(f"New free tier registration: {email} -> {api_key[:20]}...")
    
    return jsonify({
        'success': True,
        'api_key': api_key,
        'tier': 'free',
        'message': 'Welcome to AXIOM Free Tier!',
        'limits': RATE_LIMITS['free'],
        'endpoints': {
            'whale_tracking': '/v1/whale-tracking',
            'yield_signals': '/v1/yield-signals',
            'sentiment': '/v1/sentiment'
        }
    }), 201


@app.route('/v1/auth/usage', methods=['GET'])
@require_api_key
def get_usage():
    """Get current usage statistics"""
    today = datetime.now().date().isoformat()
    
    if g.api_key in rate_limit_store:
        daily = rate_limit_store[g.api_key]['daily']
        requests_today = daily.get(today, 0)
    else:
        requests_today = 0
    
    return jsonify({
        'api_key': g.api_key[:20] + '...',
        'tier': g.tier,
        'requests_today': requests_today,
        'limit': RATE_LIMITS[g.tier]['requests_per_day'],
        'remaining': max(0, RATE_LIMITS[g.tier]['requests_per_day'] - requests_today),
        'resets_at': f"{tomorrow().isoformat()}T00:00:00Z"
    })


def tomorrow():
    return datetime.now() + timedelta(days=1)


@app.route('/v1/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'axiom-api',
        'version': '1.0.0',
        'tier': 'free'
    })


@app.route('/', methods=['GET'])
def root():
    """API root with tier info"""
    return jsonify({
        'name': 'AXIOM Analytics API',
        'version': '1.0.0',
        'tiers': {
            'free': {
                'price': '$0/mo',
                'endpoints': 3,
                'limits': '100 req/day'
            },
            'pro': {
                'price': '$99/mo',
                'endpoints': 7,
                'limits': '10,000 req/day'
            }
        },
        'docs': '/docs',
        'register': '/v1/auth/register'
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting AXIOM Free Tier API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
