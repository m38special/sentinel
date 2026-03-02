#!/usr/bin/env python3
"""
API Key Rotation System - CIPHER Security
Automated key rotation for enhanced security
"""
import os
import json
import hmac
import hashlib
import secrets
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class APIKeyRotation:
    """Automated API key rotation system"""
    
    # Key rotation settings
    ROTATION_DAYS = 30  # Rotate every 30 days
    OLD_KEY_GRACE_PERIOD = 7  # Old key works for 7 days after rotation
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def generate_key(self, user_id: str, key_type: str = "standard") -> Dict:
        """Generate new API key"""
        # Create key prefix based on type
        prefix = {
            "standard": "ls",
            "admin": "lsa",
            "webhook": "lsw",
        }.get(key_type, "ls")
        
        # Generate random part
        random_part = secrets.token_hex(16)
        api_key = f"{prefix}_{random_part}"
        
        # Hash for storage (never store raw keys)
        key_hash = self._hash_key(api_key)
        
        # Store key metadata
        key_data = {
            "user_id": user_id,
            "key_type": key_type,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=self.ROTATION_DAYS)).isoformat(),
            "rotation_required": True,
            "active": True,
            "key_hash": key_hash[:16],  # Store partial hash for reference
        }
        
        # Store in Redis
        self.redis.setex(
            f"apikey:meta:{key_hash[:16]}",
            self.ROTATION_DAYS * 86400,
            json.dumps(key_data)
        )
        
        # Map user to key
        self.redis.setex(
            f"apikey:user:{user_id}:current",
            self.ROTATION_DAYS * 86400,
            api_key
        )
        
        return {
            "api_key": api_key,
            "expires_at": key_data["expires_at"],
            "user_id": user_id,
        }
    
    def _hash_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_key(self, api_key: str) -> Dict:
        """Verify API key is valid"""
        key_hash = self._hash_key(api_key)[:16]
        
        # Check current key
        current_key_data = self.redis.get(f"apikey:meta:{key_hash}")
        
        if current_key_data:
            data = json.loads(current_key_data)
            if data.get("active"):
                return {"valid": True, "user_id": data.get("user_id"), "key_type": data.get("key_type")}
        
        # Check old keys (grace period)
        old_keys = self.redis.lrange(f"apikey:old:{key_hash}", 0, -1)
        for old_hash in old_keys:
            old_data = self.redis.get(f"apikey:meta:{old_hash}")
            if old_data:
                data = json.loads(old_data)
                if data.get("active"):
                    # Check grace period
                    created = datetime.fromisoformat(data.get("created_at"))
                    if (datetime.utcnow() - created).days <= self.OLD_KEY_GRACE_PERIOD:
                        return {"valid": True, "user_id": data.get("user_id"), "key_type": data.get("key_type"), "old_key": True}
        
        return {"valid": False}
    
    def rotate_key(self, user_id: str) -> Dict:
        """Rotate API key for user"""
        # Get current key
        current_key = self.redis.get(f"apikey:user:{user_id}:current")
        
        if current_key:
            # Move to old keys
            key_hash = self._hash_key(current_key)[:16]
            self.redis.lpush(f"apikey:old:{key_hash}", key_hash)
            self.redis.expire(f"apikey:old:{key_hash}", self.OLD_KEY_GRACE_PERIOD * 86400)
            
            # Deactivate old key
            key_data = self.redis.get(f"apikey:meta:{key_hash}")
            if key_data:
                data = json.loads(key_data)
                data["active"] = False
                self.redis.setex(
                    f"apikey:meta:{key_hash}",
                    self.OLD_KEY_GRACE_PERIOD * 86400,
                    json.dumps(data)
                )
        
        # Generate new key
        new_key_data = self.generate_key(user_id)
        
        return {
            "success": True,
            "new_api_key": new_key_data["api_key"],
            "expires_at": new_key_data["expires_at"],
        }
    
    def revoke_key(self, user_id: str, immediate: bool = True) -> Dict:
        """Revoke API key"""
        current_key = self.redis.get(f"apikey:user:{user_id}:current")
        
        if current_key:
            key_hash = self._hash_key(current_key)[:16]
            
            key_data = self.redis.get(f"apikey:meta:{key_hash}")
            if key_data:
                data = json.loads(key_data)
                data["active"] = False
                data["revoked_at"] = datetime.utcnow().isoformat()
                
                if immediate:
                    self.redis.delete(f"apikey:meta:{key_hash}")
                else:
                    self.redis.setex(
                        f"apikey:meta:{key_hash}",
                        86400,
                        json.dumps(data)
                    )
            
            self.redis.delete(f"apikey:user:{user_id}:current")
        
        return {"success": True}
    
    def get_key_info(self, user_id: str) -> Dict:
        """Get key information for user"""
        current_key = self.redis.get(f"apikey:user:{user_id}:current")
        
        if not current_key:
            return {"has_key": False}
        
        key_hash = self._hash_key(current_key)[:16]
        key_data = self.redis.get(f"apikey:meta:{key_hash}")
        
        if key_data:
            data = json.loads(key_data)
            return {
                "has_key": True,
                "key_type": data.get("key_type"),
                "created_at": data.get("created_at"),
                "expires_at": data.get("expires_at"),
                "active": data.get("active"),
            }
        
        return {"has_key": False}


class RateLimiter:
    """Rate limiting for API access"""
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> Dict:
        """Check if request is within rate limit"""
        key = f"ratelimit:{identifier}"
        
        current = self.redis.get(key)
        current = int(current) if current else 0
        
        if current >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": self.redis.ttl(key),
            }
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        pipe.execute()
        
        return {
            "allowed": True,
            "remaining": limit - current - 1,
            "reset_at": window_seconds,
        }


if __name__ == "__main__":
    rotation = APIKeyRotation()
    print("API Key Rotation Ready")
    print(f"Rotation period: {rotation.ROTATION_DAYS} days")
    print(f"Grace period: {rotation.OLD_KEY_GRACE_PERIOD} days")
