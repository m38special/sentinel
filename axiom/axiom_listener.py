"""
AXIOM - UAI Listener
Receives token signals from SENTINEL via UAI and runs quant analysis
"""
import os
import json
import redis
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
UAI_CHANNEL = 'uai:events:token_signal'
UAI_RESPONSE_CHANNEL = 'uai:events:token_signal'  # AXIOM responds on same channel


def analyze_token(payload: dict) -> dict:
    """
    Run AXIOM's quant analysis on token signal
    Returns: risk score, recommendation, confidence
    """
    symbol = payload.get('symbol', 'UNKNOWN')
    market_cap = payload.get('market_cap', 0)
    risk_score = payload.get('risk_score', 50)
    risk_level = payload.get('risk_level', 'MEDIUM')
    
    # AXIOM's proprietary analysis
    # (Placeholder - replace with actual quant model)
    
    # Higher market cap = more stable = lower risk
    if market_cap > 1_000_000:
        adjustment = -10
    elif market_cap > 500_000:
        adjustment = -5
    else:
        adjustment = 5
    
    final_score = max(0, min(100, risk_score + adjustment))
    
    if final_score < 30:
        recommendation = 'STRONG_BUY'
        confidence = 0.85
    elif final_score < 50:
        recommendation = 'BUY'
        confidence = 0.70
    elif final_score < 70:
        recommendation = 'HOLD'
        confidence = 0.60
    else:
        recommendation = 'SELL'
        confidence = 0.75
    
    return {
        'symbol': symbol,
        'market_cap': market_cap,
        'axiom_score': final_score,
        'recommendation': recommendation,
        'confidence': confidence,
        'analyzed_at': datetime.utcnow().isoformat()
    }


def handle_token_signal(message: dict, redis_client):
    """Handle incoming token signal from SENTINEL"""
    payload = message.get('payload', {})
    symbol = payload.get('symbol', 'UNKNOWN')
    mint = payload.get('mint', '')
    from_agent = message.get('from', 'sentinel')
    msg_id = message.get('id', '')

    logger.info(f"AXIOM received signal: {symbol}")

    # Run analysis
    result = analyze_token(payload)

    logger.info(f"AXIOM analysis: {result['symbol']} -> {result['recommendation']} (conf: {result['confidence']})")

    # Send result back via UAI
    response = {
        'id': f"resp-{datetime.utcnow().timestamp()}",
        'from': 'axiom',
        'to': from_agent,  # Send back to sender
        'intent': 'analyze.market_signal.response',
        'priority': 'medium',
        'payload': {
            'original_msg_id': msg_id,
            'symbol': symbol,
            'mint': mint,
            'axiom_score': result['axiom_score'],
            'recommendation': result['recommendation'],
            'confidence': result['confidence'],
            'market_cap': result['market_cap'],
            'analyzed_at': result['analyzed_at'],
        },
        'reply_to': msg_id,
        'ts': datetime.utcnow().isoformat() + 'Z',
        'ttl': 300,
    }

    redis_client.publish(UAI_RESPONSE_CHANNEL, json.dumps(response))
    logger.info(f"AXIOM → UAI response sent for {symbol}")

    return result


def listen():
    """Listen for UAI token signals"""
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()

    pubsub.subscribe(UAI_CHANNEL)
    logger.info(f"AXIOM listening on {UAI_CHANNEL}")

    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data.get('intent') == 'analyze.market_signal':
                    handle_token_signal(data, redis_client)
            except Exception as e:
                logger.error(f"Error processing message: {e}")


if __name__ == '__main__':
    logger.info("AXIOM starting...")
    listen()
