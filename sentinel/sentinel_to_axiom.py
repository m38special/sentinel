"""
SENTINEL → AXIOM UAI Integration
Sends token signals to AXIOM via Redis pub/sub for quant analysis
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


def send_to_axiom(token_data: dict) -> bool:
    """
    Send token signal to AXIOM via UAI
    AXIOM subscribes to uai:events:token_signal
    """
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Build UAI message
    message = {
        'id': f"sig-{datetime.utcnow().timestamp()}",
        'from': 'sentinel',
        'to': 'axiom',
        'intent': 'analyze.market_signal',
        'priority': 'high' if token_data.get('signal_level') == 'HIGH' else 'medium',
        'payload': {
            'symbol': token_data.get('symbol'),
            'name': token_data.get('name'),
            'mint': token_data.get('mint'),
            'market_cap': token_data.get('market_cap'),
            'risk_score': token_data.get('risk_score'),
            'risk_level': token_data.get('risk_level'),
            'signal_level': token_data.get('signal_level'),
            'detected_at': token_data.get('detected_at')
        },
        'context_ref': None,
        'reply_to': None,
        'ts': datetime.utcnow().isoformat() + 'Z',
        'ttl': 300
    }
    
    try:
        redis_client.publish(UAI_CHANNEL, json.dumps(message))
        logger.info(f"Sent {token_data.get('symbol')} to AXIOM via UAI")
        return True
    except Exception as e:
        logger.error(f"Failed to send to AXIOM: {e}")
        return False


# Example: Integrate into scanner
# In scanner_mvp.py, after inserting a signal:
"""
from sentinel_to_axiom import send_to_axiom

# After db.insert_or_update(signal):
if signal.signal_level in ('HIGH', 'MEDIUM'):
    send_to_axiom({
        'symbol': signal.symbol,
        'name': signal.name,
        'mint': signal.mint,
        'market_cap': signal.market_cap,
        'risk_score': signal.risk_score,
        'risk_level': signal.risk_level,
        'signal_level': signal.signal_level,
        'detected_at': signal.detected_at
    })
"""


if __name__ == '__main__':
    # Test
    test_token = {
        'symbol': 'PEPE',
        'name': 'Pepe',
        'mint': 'EpXwC2n6C3m4...',
        'market_cap': 500000,
        'risk_score': 35,
        'risk_level': 'MEDIUM',
        'signal_level': 'MEDIUM',
        'detected_at': datetime.utcnow().isoformat()
    }
    
    send_to_axiom(test_token)
    print("Test message sent to AXIOM")
