"""
UAI Transport Layer v0.2 - Phase 2 Ready
Includes: Redis pub/sub, context store, agent registration, DLQ
"""
import os
import json
import uuid
import redis
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
UAI_CHANNEL = 'uai:events:token_signal'
BROADCAST_CHANNEL = 'uai:broadcast'
CONTEXT_PREFIX = 'uai:context:'
ACK_PREFIX = 'uai:ack:'
DLQ_KEY = 'uai:dlq'

# Priority levels
class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

# ACK statuses
class ACKStatus(Enum):
    QUEUED = 'queued'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'
    BLOCKED = 'blocked'
    FAILED = 'failed'


@dataclass
class UAIMessage:
    """Standardized UAI message schema v0.1"""
    id: str
    from_agent: str
    to: str
    intent: str
    priority: str
    payload: Dict[str, Any]
    context_ref: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: str = None
    ttl: int = 300
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + 'Z'
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'from': self.from_agent,
            'to': self.to,
            'intent': self.intent,
            'priority': self.priority,
            'payload': self.payload,
            'context_ref': self.context_ref,
            'reply_to': self.reply_to,
            'ts': self.timestamp,
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UAIMessage':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            from_agent=data.get('from', data.get('from_agent', 'unknown')),
            to=data.get('to', 'unknown'),
            intent=data.get('intent', 'unknown'),
            priority=data.get('priority', 'medium'),
            payload=data.get('payload', {}),
            context_ref=data.get('context_ref'),
            reply_to=data.get('reply_to'),
            timestamp=data.get('ts', data.get('timestamp')),
            ttl=data.get('ttl', 300)
        )


class UAITransport:
    """Redis-based transport for UAI with Phase 2 features"""
    
    def __init__(self, redis_url: str = REDIS_URL, agent_id: str = 'unknown'):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self.agent_id = agent_id
        self.handlers: Dict[str, Callable] = {}
        self.dlq_callback = None
    
    def set_dlq_callback(self, callback: Callable):
        """Set callback for DLQ escalation"""
        self.dlq_callback = callback
    
    def publish(self, message: UAIMessage) -> bool:
        """Publish a message to UAI channel"""
        try:
            # Initialize ACK
            ack_key = f"{ACK_PREFIX}{message.id}"
            self.redis.setex(ack_key, message.ttl, json.dumps({
                'status': 'queued',
                'created_at': datetime.utcnow().isoformat()
            }))
            
            # Determine channel
            if message.to == 'broadcast':
                channel = BROADCAST_CHANNEL
            elif message.intent.startswith('analyze.'):
                channel = 'uai:events:token_signal'
            elif message.intent.startswith('security.'):
                channel = 'uai:events:security_alert'
            elif message.intent.startswith('market.'):
                channel = 'uai:events:market_update'
            else:
                channel = UAI_CHANNEL
            
            data = json.dumps(message.to_dict())
            self.redis.publish(channel, data)
            logger.info(f"Published {message.id} to {channel}")
            return True
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False
    
    def subscribe(self, channels: list, handler: Callable[[UAIMessage], None]):
        """Subscribe to UAI channels"""
        for channel in channels:
            self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")
        self.handlers[handler.__name__] = handler
    
    def listen(self, blocking: bool = True):
        """Listen for messages"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    msg = UAIMessage.from_dict(data)
                    
                    # Check if message is for us
                    if msg.to == self.agent_id or msg.to == 'broadcast':
                        for handler in self.handlers.values():
                            handler(msg)
                    
                    # Update ACK to in_progress
                    self.update_ack(msg.id, ACKStatus.IN_PROGRESS.value)
                    
                except Exception as e:
                    logger.error(f"Message parse failed: {e}")
    
    def start_listener(self, channels: list, handler: Callable):
        """Start listener in background thread"""
        self.subscribe(channels, handler)
        thread = threading.Thread(target=self.listen, daemon=True)
        thread.start()
        logger.info(f"Background listener started for {self.agent_id}")
    
    def update_ack(self, message_id: str, status: str, details: str = None):
        """Update ACK status"""
        ack_key = f"{ACK_PREFIX}{message_id}"
        ttl = self.redis.ttl(ack_key)
        if ttl <= 0:
            ttl = 300
        
        self.redis.setex(ack_key, ttl, json.dumps({
            'status': status,
            'details': details,
            'updated_at': datetime.utcnow().isoformat()
        }))
        
        # If terminal state, check DLQ
        if status in ['done', 'failed', 'blocked']:
            if self.dlq_callback:
                self.dlq_callback(message_id, status)
    
    def set_context(self, key: str, value: Any, ttl: int = 86400):
        """Store context in Redis"""
        full_key = f"{CONTEXT_PREFIX}{key}"
        self.redis.setex(full_key, ttl, json.dumps(value))
    
    def get_context(self, key: str) -> Optional[Any]:
        """Retrieve context from Redis"""
        full_key = f"{CONTEXT_PREFIX}{key}"
        data = self.redis.get(full_key)
        return json.loads(data) if data else None
    
    def get_ack(self, message_id: str) -> Optional[Dict]:
        """Get ACK status"""
        ack_key = f"{ACK_PREFIX}{message_id}"
        data = self.redis.get(ack_key)
        return json.loads(data) if data else None


def create_message(
    from_agent: str,
    to: str,
    intent: str,
    payload: Dict[str, Any],
    priority: str = 'medium',
    context_ref: str = None,
    ttl: int = 300
) -> UAIMessage:
    """Helper to create a UAI message"""
    return UAIMessage(
        id=str(uuid.uuid4()),
        from_agent=from_agent,
        to=to,
        intent=intent,
        priority=priority,
        payload=payload,
        context_ref=context_ref,
        ttl=ttl
    )


# Example usage
if __name__ == '__main__':
    transport = UAITransport(agent_id='sentinel')
    
    # Example: Publish a token signal
    msg = create_message(
        from_agent='sentinel',
        to='axiom',
        intent='analyze.market_signal',
        payload={'symbol': 'PEPE', 'market_cap': 100000, 'risk': 'HIGH'},
        priority='high'
    )
    transport.publish(msg)
    
    print("UAI Transport v0.2 ready")
