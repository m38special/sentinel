"""
UAI Phase 2 - Gateway Integration
Intercepts uai:* Redis channels and routes to the correct agent session
"""
import os
import json
import yaml
import redis
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
UAI_CHANNELS = [
    'uai:events:token_signal',
    'uai:events:security_alert', 
    'uai:events:social_signal',
    'uai:events:content_review',
    'uai:events:market_update',
    'uai:events:ceo_dashboard',
    'uai:broadcast'
]

# Load intents registry
def load_intents():
    with open('registry/intents.yaml', 'r') as f:
        return yaml.safe_load(f)

INTENTS = load_intents()


class UAIGateway:
    """
    Gateway that routes UAI messages to the correct agent.
    Reads agent registrations from Redis and routes messages accordingly.
    """
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self.agent_sessions = {}  # agent_id -> session_key mapping
        self.routing_table = self._build_routing_table()
    
    def _build_routing_table(self) -> Dict[str, str]:
        """Build routing table from intents registry"""
        table = {}
        
        for intent_prefix, config in INTENTS.get('intents', {}).items():
            owner = config.get('owner', 'maxwell')
            table[intent_prefix] = owner
        
        logger.info(f"Routing table: {table}")
        return table
    
    def find_handler(self, intent: str) -> str:
        """Find which agent handles an intent"""
        prefix = intent.split('.')[0] + '.'
        
        # Check exact match first
        if prefix in self.routing_table:
            return self.routing_table[prefix]
        
        # Check partial match
        for intent_prefix, owner in self.routing_table.items():
            if intent.startswith(intent_prefix.replace('.*', '')):
                return owner
        
        return 'maxwell'  # Default fallback
    
    def register_agent_session(self, agent_id: str, session_key: str):
        """Register an agent's OpenClaw session for routing"""
        self.agent_sessions[agent_id] = session_key
        logger.info(f"Registered agent session: {agent_id} -> {session_key}")
    
    def route_message(self, message: Dict) -> str:
        """Route a message to the correct agent"""
        intent = message.get('intent', '')
        to = message.get('to', '')
        
        # If explicit 'to' field, use that
        if to and to != 'broadcast':
            return to
        
        # Otherwise, find handler by intent
        return self.find_handler(intent)
    
    def start_listening(self):
        """Start listening to UAI channels"""
        for channel in UAI_CHANNELS:
            self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")
        
        logger.info("UAI Gateway listening for messages...")
        
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    target_agent = self.route_message(data)
                    
                    logger.info(f"Routing message {data.get('id')} to {target_agent}")
                    
                    # Store message for pickup
                    queue_key = f"uai:queue:{target_agent}"
                    self.redis.lpush(queue_key, json.dumps(data))
                    
                    # If agent has session, could trigger notification here
                    # For now, agents poll their queue
                    
                except Exception as e:
                    logger.error(f"Route error: {e}")
    
    def get_queue(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get pending messages for an agent"""
        queue_key = f"uai:queue:{agent_id}"
        messages = self.redis.lrange(queue_key, 0, limit - 1)
        return [json.loads(m) for m in messages]
    
    def ack_message(self, agent_id: str, message_id: str, status: str):
        """Acknowledge a message"""
        # Update ACK status
        ack_key = f"uai:ack:{message_id}"
        self.redis.setex(ack_key, 300, json.dumps({
            'status': status,
            'agent': agent_id,
            'updated_at': datetime.utcnow().isoformat()
        }))
        
        # Remove from queue
        queue_key = f"uai:queue:{agent_id}"
        # Note: In production, would need to remove specific message
        logger.info(f"Message {message_id} acknowledged by {agent_id}: {status}")


class UAIClient:
    """
    Client for agents to receive and respond to UAI messages.
    Agents use this to participate in the UAI network.
    """
    
    def __init__(self, agent_id: str, redis_url: str = REDIS_URL):
        self.agent_id = agent_id
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
    
    def subscribe(self, channels: List[str]):
        """Subscribe to UAI channels"""
        for channel in channels:
            self.pubsub.subscribe(channel)
    
    def get_messages(self, limit: int = 10) -> List[Dict]:
        """Get pending messages from queue"""
        queue_key = f"uai:queue:{self.agent_id}"
        messages = self.redis.lrange(queue_key, 0, limit - 1)
        return [json.loads(m) for m in messages]
    
    def send_response(self, original_message: Dict, payload: Dict, intent: str = None):
        """Send a response to a message"""
        response = {
            'id': f"resp-{datetime.utcnow().timestamp()}",
            'from': self.agent_id,
            'to': original_message.get('from'),
            'intent': intent or f"response.{original_message.get('intent', 'unknown')}",
            'priority': 'medium',
            'payload': payload,
            'reply_to': original_message.get('id'),
            'ts': datetime.utcnow().isoformat() + 'Z',
            'ttl': 300
        }
        
        # Publish to appropriate channel
        channel = 'uai:events:token_signal'  # Default
        self.redis.publish(channel, json.dumps(response))
        
        # Ack the original
        ack_key = f"uai:ack:{original_message.get('id')}"
        self.redis.setex(ack_key, 300, json.dumps({
            'status': 'done',
            'agent': self.agent_id,
            'updated_at': datetime.utcnow().isoformat()
        }))
        
        return response


# Example: AXIOM receiving SENTINEL signals
async def axiom_example():
    """Example: AXIOM receiving token signals from SENTINEL"""
    client = UAIClient('axiom')
    
    # Subscribe to token signals
    client.subscribe(['uai:events:token_signal'])
    
    print("AXIOM listening for token signals...")
    
    for message in client.pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            print(f"Received: {data}")
            
            # Process the signal (run quant model)
            if data.get('intent') == 'analyze.market_signal':
                payload = data.get('payload', {})
                symbol = payload.get('symbol')
                market_cap = payload.get('market_cap')
                
                # Run risk model...
                result = {'symbol': symbol, 'score': 0.85, 'recommendation': 'BUY'}
                
                # Send response
                client.send_response(data, result)
                print(f"Sent analysis: {result}")


if __name__ == '__main__':
    # Test gateway
    gateway = UAIGateway()
    print("Routing table:", gateway.routing_table)
    
    # Test client
    client = UAIClient('axiom')
    print("AXIOM queue:", client.get_messages())
