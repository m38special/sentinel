"""
UAI Phase 2 - Agent Registration
Each agent declares capabilities on startup
"""
import os
import json
import yaml
import redis
from typing import Dict, List, Any
from datetime import datetime

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REGISTRY_KEY = 'uai:agents:registry'

# Load intents registry
def load_intents():
    with open('registry/intents.yaml', 'r') as f:
        return yaml.safe_load(f)

INTENTS = load_intents()

# Default agent registration format
DEFAULT_REGISTRATION = {
    'handles': [],  # intent prefixes e.g. ['analyze.*', 'risk.*']
    'broadcast_subscriptions': [],  # Redis channels
    'status': 'online',
    'registered_at': None,
    'last_heartbeat': None
}


class AgentRegistry:
    """Register agents and their capabilities"""
    
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def register(self, agent_id: str, handles: List[str], broadcast_subscriptions: List[str]):
        """Register an agent with its capabilities"""
        registration = {
            'handles': handles,
            'broadcast_subscriptions': broadcast_subscriptions,
            'status': 'online',
            'registered_at': datetime.utcnow().isoformat(),
            'last_heartbeat': datetime.utcnow().isoformat()
        }
        
        # Store in Redis hash
        self.redis.hset(REGISTRY_KEY, agent_id, json.dumps(registration))
        
        # Subscribe to broadcast channels
        pubsub = self.redis.pubsub()
        for channel in broadcast_subscriptions:
            pubsub.subscribe(channel)
        
        print(f"Agent {agent_id} registered: handles={handles}, subs={broadcast_subscriptions}")
        return registration
    
    def unregister(self, agent_id: str):
        """Unregister an agent"""
        self.redis.hdel(REGISTRY_KEY, agent_id)
        print(f"Agent {agent_id} unregistered")
    
    def heartbeat(self, agent_id: str):
        """Update agent heartbeat"""
        current = self.redis.hget(REGISTRY_KEY, agent_id)
        if current:
            reg = json.loads(current)
            reg['last_heartbeat'] = datetime.utcnow().isoformat()
            self.redis.hset(REGISTRY_KEY, agent_id, json.dumps(reg))
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent registration"""
        data = self.redis.hget(REGISTRY_KEY, agent_id)
        return json.loads(data) if data else None
    
    def get_all_agents(self) -> Dict[str, Dict]:
        """Get all registered agents"""
        all_agents = self.redis.hgetall(REGISTRY_KEY)
        return {k: json.loads(v) for k, v in all_agents.items()}
    
    def find_handler(self, intent: str) -> str:
        """Find which agent handles an intent"""
        prefix = intent.split('.')[0] + '.*'
        
        # Check intents registry
        for intent_prefix, config in INTENTS.get('intents', {}).items():
            if prefix == intent_prefix or intent.startswith(intent_prefix):
                return config.get('owner', 'maxwell')
        
        return 'maxwell'  # Default fallback


# Predefined agent registrations
AGENT_REGISTRATIONS = {
    'sentinel': {
        'handles': [],
        'broadcast_subscriptions': ['uai:broadcast', 'uai:events:market_update']
    },
    'axiom': {
        'handles': ['analyze.*', 'risk.*', 'backtest.*'],
        'broadcast_subscriptions': ['uai:events:token_signal', 'uai:events:market_update']
    },
    'cipher': {
        'handles': ['security.*'],
        'broadcast_subscriptions': ['uai:events:security_alert', 'uai:broadcast']
    },
    'nova': {
        'handles': ['social.*'],
        'broadcast_subscriptions': ['uai:events:token_signal', 'uai:events:market_update']
    },
    'urahara': {
        'handles': ['infra.*'],
        'broadcast_subscriptions': ['uai:broadcast', 'uai:events:security_alert']
    },
    'maxwell': {
        'handles': ['report.*'],
        'broadcast_subscriptions': ['uai:broadcast', 'uai:events:token_signal', 'uai:events:security_alert', 'uai:events:market_update']
    }
}


def register_all_agents():
    """Register all known agents"""
    registry = AgentRegistry()
    
    for agent_id, config in AGENT_REGISTRATIONS.items():
        registry.register(agent_id, config['handles'], config['broadcast_subscriptions'])
    
    print("\nRegistered agents:")
    for agent in registry.get_all_agents():
        print(f"  - {agent}")
    
    return registry


if __name__ == '__main__':
    register_all_agents()
