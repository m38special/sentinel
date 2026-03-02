"""
CIPHER - UAI Listener
Receives security alerts from other agents
"""
import os
import json
import redis
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
UAI_CHANNEL = 'uai:events:security_alert'


def analyze_security(payload: dict) -> dict:
    """
    Run CIPHER's security analysis on alerts
    """
    alert_type = payload.get('type', 'unknown')
    severity = payload.get('severity', 'MEDIUM')
    
    # CIPHER's analysis logic
    if severity == 'CRITICAL':
        recommendation = 'IMMEDIATE_ACTION'
    elif severity == 'HIGH':
        recommendation = 'INVESTIGATE'
    else:
        recommendation = 'MONITOR'
    
    return {
        'alert_type': alert_type,
        'severity': severity,
        'recommendation': recommendation,
        'analyzed_at': datetime.utcnow().isoformat()
    }


def handle_security_alert(message: dict):
    """Handle incoming security alert"""
    payload = message.get('payload', {})
    logger.info(f"CIPHER received security alert: {payload}")
    
    result = analyze_security(payload)
    logger.info(f"CIPHER analysis: {result}")
    
    # TODO: Send to Slack/Telegram if critical
    
    return result


def listen():
    """Listen for UAI security alerts"""
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    pubsub.subscribe(UAI_CHANNEL)
    logger.info(f"CIPHER listening on {UAI_CHANNEL}")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data.get('intent', '').startswith('security.'):
                    handle_security_alert(data)
            except Exception as e:
                logger.error(f"Error: {e}")


if __name__ == '__main__':
    logger.info("CIPHER starting...")
    listen()
