#!/usr/bin/env python3
"""
SENTINEL Signal Subscription System
Revenue Framework for Liquid Sound
"""
import os
import json
import hashlib
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Tier(Enum):
    FREE = "free"
    STARTER = "starter"     # $29/mo
    PRO = "pro"             # $99/mo
    VIP = "vip"             # $299/mo


@dataclass
class Subscription:
    user_id: str
    tier: Tier
    start_date: datetime
    end_date: datetime
    signals_received: int
    active: bool


class SubscriptionManager:
    """Manage signal subscriptions and API access"""
    
    # Pricing
    PRICING = {
        Tier.FREE: {"price": 0, "signals_per_day": 5, "channels": ["telegram"]},
        Tier.STARTER: {"price": 29, "signals_per_day": 25, "channels": ["telegram", "webhook"]},
        Tier.PRO: {"price": 99, "signals_per_day": 100, "channels": ["telegram", "webhook", "discord"]},
        Tier.VIP: {"price": 299, "signals_per_day": -1, "channels": ["all"], "priority": True},
    }
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def create_subscription(self, user_id: str, tier: str) -> Dict:
        """Create new subscription"""
        # Input validation
        if not user_id or not isinstance(user_id, str) or len(user_id) > 100:
            return {"error": "Invalid user_id"}
        
        if not tier or tier.upper() not in [t.name for t in Tier]:
            return {"error": "Invalid tier"}
        tier_enum = Tier[tier.upper()]
        
        sub = {
            "user_id": user_id,
            "tier": tier_enum.value,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "signals_received": 0,
            "active": True,
            "api_key": self._generate_api_key(user_id),
        }
        
        # Store in Redis
        key = f"subscription:{user_id}"
        self.redis.setex(key, 86400 * 30, json.dumps(sub))
        
        return sub
    
    def _generate_api_key(self, user_id: str) -> str:
        """Generate unique API key"""
        raw = f"{user_id}:{datetime.utcnow().isoformat()}:liquid"
        return "ls_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
    
    def check_access(self, api_key: str, signal_type: str) -> Dict:
        """Check if user has access to signal"""
        # Find user by API key
        # In production: scan keys or use hash lookup
        
        # For now: check against known keys
        key = f"apikey:{api_key}"
        sub_data = self.redis.get(key)
        
        if not sub_data:
            return {"access": False, "reason": "Invalid API key"}
        
        sub = json.loads(sub_data)
        
        if not sub.get("active"):
            return {"access": False, "reason": "Subscription inactive"}
        
        # Check tier limits
        tier = Tier[sub["tier"].upper()]
        daily_limit = self.PRICING[tier]["signals_per_day"]
        
        # Check daily usage
        today_key = f"usage:{sub['user_id']}:{datetime.utcnow().date()}"
        today_count = int(self.redis.get(today_key) or 0)
        
        if daily_limit > 0 and today_count >= daily_limit:
            return {"access": False, "reason": "Daily limit reached", "upgrade": True}
        
        return {
            "access": True, 
            "tier": tier.value,
            "remaining": daily_limit - today_count - 1 if daily_limit > 0 else "unlimited"
        }
    
    def deliver_signal(self, api_key: str, signal: Dict) -> bool:
        """Deliver signal to subscriber"""
        access = self.check_access(api_key, "token_signal")
        
        if not access["access"]:
            return False
        
        # Increment usage
        user_id = self._get_user_from_key(api_key)
        if user_id:
            today_key = f"usage:{user_id}:{datetime.utcnow().date()}"
            self.redis.incr(today_key)
            
            # Store signal history
            signal_key = f"signals:{user_id}"
            self.redis.lpush(signal_key, json.dumps(signal))
            self.redis.ltrim(signal_key, 0, 999)  # Keep last 1000
        
        return True
    
    def _get_user_from_key(self, api_key: str) -> Optional[str]:
        """Get user ID from API key"""
        key = f"apikey:{api_key}"
        sub_data = self.redis.get(key)
        if sub_data:
            return json.loads(sub_data).get("user_id")
        return None


class PaymentProcessor:
    """Handle payments via Stripe/LN"""
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    async def create_checkout(self, user_id: str, tier: str) -> Dict:
        """Create Stripe checkout session"""
        # In production: integrate Stripe
        # For now: return structure
        
        return {
            "checkout_url": f"https://checkout.stripe.com/{user_id}/{tier}",
            "session_id": f"cs_{user_id}_{datetime.utcnow().timestamp()}",
            "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        }
    
    async def verify_payment(self, session_id: str) -> bool:
        """Verify payment completed"""
        # In production: verify with Stripe
        return True


# API Usage Tracking
def track_usage(user_id: str, endpoint: str):
    """Track API usage for billing"""
    r = redis.from_url(redis_url, decode_responses=True)
    
    # Daily
    daily_key = f"api:usage:{user_id}:{datetime.utcnow().date()}"
    r.incr(daily_key)
    r.expire(daily_key, 86400 * 2)
    
    # Monthly
    month_key = f"api:usage:{user_id}:{datetime.utcnow().strftime('%Y-%m')}"
    r.incr(month_key)


if __name__ == "__main__":
    mgr = SubscriptionManager()
    
    # Test create subscription
    sub = mgr.create_subscription("user123", "starter")
    print(f"Created subscription: {sub['tier']}")
    print(f"API Key: {sub['api_key']}")
    
    # Test access check
    access = mgr.check_access(sub['api_key'], "token_signal")
    print(f"Access: {access}")
