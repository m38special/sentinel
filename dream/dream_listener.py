"""
DREAM - UAI Listener
General purpose agent for creative/content tasks
"""
import os
import json
import redis
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
UAI_CHANNEL = 'uai:broadcast'


def handle_broadcast(message: dict):
    """Handle incoming broadcast messages"""
    payload = message.get('payload', {})
    logger.info(f"DREAM received broadcast: {payload}")
    
    # DREAM's creative processing
    intent = message.get('intent', '')
    
    if 'content' in intent or 'draft' in intent:
        logger.info("DREAM: Processing content request")
        # TODO: Generate content
    
    return {'status': 'received'}


def listen():
    """Listen for UAI broadcasts"""
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    pubsub.subscribe(UAI_CHANNEL)
    logger.info(f"DREAM listening on {UAI_CHANNEL}")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                handle_broadcast(data)
            except Exception as e:
                logger.error(f"Error: {e}")


if __name__ == '__main__':
    logger.info("DREAM starting...")
    listen()
