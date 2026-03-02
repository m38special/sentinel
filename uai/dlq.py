"""
UAI Phase 2 - Dead Letter Queue (DLQ)
Messages that fail ACK within TTL go here for Maxwell to triage
"""
import os
import json
import redis
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DLQ_KEY = 'uai:dlq'
ACK_KEY_PREFIX = 'uai:ack:'

# ACK states
ACK_STATES = ['queued', 'in_progress', 'done', 'failed', 'blocked']


class DeadLetterQueue:
    """Handle messages that timeout or fail"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.escalation_callback = None
    
    def set_escalation_callback(self, callback):
        """Set callback for when messages go to DLQ"""
        self.escalation_callback = callback
    
    def add_to_dlq(self, message: Dict[str, Any], reason: str = 'ttl_expired'):
        """Add a failed message to the DLQ"""
        dlq_entry = {
            'message': message,
            'reason': reason,
            'failed_at': datetime.utcnow().isoformat(),
            'retries': 0
        }
        
        self.redis.lpush(DLQ_KEY, json.dumps(dlq_entry))
        
        print(f"Message {message.get('id')} added to DLQ: {reason}")
        
        if self.escalation_callback:
            self.escalation_callback(dlq_entry)
        
        return dlq_entry
    
    def get_dlq(self, limit: int = 10) -> list:
        """Get messages from DLQ"""
        entries = self.redis.lrange(DLQ_KEY, 0, limit - 1)
        return [json.loads(e) for e in entries]
    
    def requeue(self, dlq_entry: Dict[str, Any]) -> bool:
        """Requeue a message from DLQ"""
        message = dlq_entry.get('message', {})
        message['retries'] = dlq_entry.get('retries', 0) + 1
        
        # Reset ACK status
        ack_key = f"{ACK_KEY_PREFIX}{message.get('id')}"
        self.redis.setex(ack_key, 300, json.dumps({
            'status': 'queued',
            'updated_at': datetime.utcnow().isoformat()
        }))
        
        # Remove from DLQ
        self.redis.lrem(DLQ_KEY, 1, json.dumps(dlq_entry))
        
        print(f"Message {message.get('id')} requeued (retry {message['retries']})")
        return True
    
    def ack_message(self, message_id: str, status: str):
        """Update ACK status for a message"""
        if status not in ACK_STATES:
            raise ValueError(f"Invalid ACK status: {status}")
        
        ack_key = f"{ACK_KEY_PREFIX}{message_id}"
        ack_data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Get TTL from message if available
        ttl = 300  # default
        self.redis.setex(ack_key, ttl, json.dumps(ack_data))
        
        return ack_data
    
    def check_acks(self, messages: list) -> list:
        """Check which messages have timed out and need DLQ"""
        timed_out = []
        
        for msg in messages:
            msg_id = msg.get('id')
            ttl = msg.get('ttl', 300)
            
            ack_key = f"{ACK_KEY_PREFIX}{msg_id}"
            ack_data = self.redis.get(ack_key)
            
            if not ack_data:
                # No ACK yet - might be queued
                continue
            
            ack = json.loads(ack_data)
            if ack.get('status') not in ['done', 'failed', 'blocked']:
                # Check if TTL expired (key still exists = not updated)
                if not self.redis.ttl(ack_key) > 0:
                    timed_out.append(msg)
        
        return timed_out


class ACKManager:
    """Manage ACK lifecycle for messages"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def init_ack(self, message_id: str, ttl: int = 300):
        """Initialize ACK for a message"""
        ack_key = f"{ACK_KEY_PREFIX}{message_id}"
        self.redis.setex(ack_key, ttl, json.dumps({
            'status': 'queued',
            'created_at': datetime.utcnow().isoformat()
        }))
    
    def update_ack(self, message_id: str, status: str, details: str = None):
        """Update ACK status"""
        if status not in ACK_STATES:
            raise ValueError(f"Invalid status: {status}")
        
        ack_key = f"{ACK_KEY_PREFIX}{message_id}"
        
        # Get current TTL remaining
        ttl = self.redis.ttl(ack_key)
        if ttl <= 0:
            ttl = 300
        
        self.redis.setex(ack_key, ttl, json.dumps({
            'status': status,
            'details': details,
            'updated_at': datetime.utcnow().isoformat()
        }))
    
    def get_ack(self, message_id: str) -> Optional[Dict]:
        """Get ACK status for a message"""
        ack_key = f"{ACK_KEY_PREFIX}{message_id}"
        data = self.redis.get(ack_key)
        return json.loads(data) if data else None
    
    def wait_for_ack(self, message_id: str, timeout: int = 30) -> Dict:
        """Wait for ACK with timeout"""
        start = time.time()
        
        while time.time() - start < timeout:
            ack = self.get_ack(message_id)
            if ack and ack.get('status') in ['done', 'failed', 'blocked']:
                return ack
            time.sleep(1)
        
        return {'status': 'timeout'}


if __name__ == '__main__':
    # Test DLQ
    dlq = DeadLetterQueue()
    
    # Add test message to DLQ
    test_msg = {
        'id': 'test-123',
        'from': 'sentinel',
        'to': 'axiom',
        'intent': 'analyze.market_signal',
        'ttl': 300
    }
    
    dlq.add_to_dlq(test_msg, 'ttl_expired')
    print("DLQ contents:", dlq.get_dlq())
