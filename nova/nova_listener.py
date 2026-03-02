"""
NOVA - UAI Listener
Receives market signals and token alerts for social content
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


def analyze_social_opportunity(payload: dict) -> dict:
    """
    Analyze if this token is worth creating social content about
    """
    signal_level = payload.get('signal_level', 'LOW')
    market_cap = payload.get('market_cap', 0)
    
    # NOVA's content criteria
    if signal_level == 'HIGH' and market_cap > 100000:
        content_recommendation = 'CREATE_POST'
        urgency = 'HIGH'
    elif signal_level == 'MEDIUM' and market_cap > 50000:
        content_recommendation = 'CONSIDER'
        urgency = 'MEDIUM'
    else:
        content_recommendation = 'SKIP'
        urgency = 'LOW'
    
    return {
        'symbol': payload.get('symbol'),
        'signal_level': signal_level,
        'market_cap': market_cap,
        'content_recommendation': content_recommendation,
        'urgency': urgency,
        'analyzed_at': datetime.utcnow().isoformat()
    }


def handle_token_signal(message: dict):
    """Handle incoming token signal for social content"""
    payload = message.get('payload', {})
    logger.info(f"NOVA received token signal: {payload.get('symbol')}")
    
    result = analyze_social_opportunity(payload)
    logger.info(f"NOVA content analysis: {result}")
    
    # TODO: If CREATE_POST, draft content and queue for approval
    
    return result


def listen():
    """Listen for UAI token signals"""
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    pubsub.subscribe(UAI_CHANNEL)
    logger.info(f"NOVA listening on {UAI_CHANNEL}")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data.get('intent', '').startswith('analyze.'):
                    handle_token_signal(data)
            except Exception as e:
                logger.error(f"Error: {e}")


if __name__ == '__main__':
    logger.info("NOVA starting...")
    listen()
