#!/usr/bin/env python3
"""
NOVA Zapier Webhook Connector
Sends generated content to Zapier for Instagram posting
"""
import os
import json
import requests
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
ZAPIER_WEBHOOK_URL = os.getenv("ZAPIER_WEBHOOK_URL", "")
INSTAGRAM_ACCOUNT = os.getenv("INSTAGRAM_ACCOUNT", "@888abundancefrequency")

# Secret for webhook verification
ZAPIER_SECRET = os.getenv("ZAPIER_SECRET", "")


class ZapierConnector:
    """Connect NOVA to Zapier for Instagram posting"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or ZAPIER_WEBHOOK_URL
        self.account = INSTAGRAM_ACCOUNT
    
    def send_content(self, content: dict, account: str = None) -> Dict:
        """
        Send content to Zapier webhook for posting
        
        Args:
            content: Dict with 'image', 'caption', 'hashtags', etc.
            account: Target Instagram account
        
        Returns:
            Response from Zapier
        """
        if not self.webhook_url:
            return {"success": False, "error": "No webhook URL configured"}
        
        account = account or self.account
        
        payload = {
            "account": account,
            "content": content.get("content", ""),
            "caption": content.get("caption", ""),
            "hashtags": content.get("hashtags", ""),
            "theme": content.get("theme", ""),
            "cta": content.get("cta", ""),
            "generated_at": datetime.utcnow().isoformat(),
            "source": "NOVA",
        }
        
        # Add image if available
        if content.get("image_url"):
            payload["image_url"] = content["image_url"]
        if content.get("image_base64"):
            payload["image_base64"] = content["image_base64"]
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "response": response.text,
                    "account": account,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response": response.text,
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Zapier webhook signature"""
        if not ZAPIER_SECRET:
            return True  # No secret configured
        
        expected = hmac.new(
            ZAPIER_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def queue_for_posting(self, content_batch: List[dict], account: str = None) -> Dict:
        """Queue multiple posts for posting"""
        results = []
        
        for content in content_batch:
            result = self.send_content(content, account)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "total": len(content_batch),
            "success": success_count,
            "failed": len(content_batch) - success_count,
            "results": results,
        }


class ContentFormatter:
    """Format content for Instagram"""
    
    @staticmethod
    def format_caption(content: str, hashtags: str = "", cta: str = "") -> str:
        """Format full Instagram caption"""
        parts = [content]
        
        if cta:
            parts.append(f"\n{cta}")
        
        if hashtags:
            parts.append(f"\n{hashtags}")
        
        return "".join(parts)
    
    @staticmethod
    def truncate_caption(caption: str, max_length: int = 2200) -> str:
        """Truncate caption if too long"""
        if len(caption) <= max_length:
            return caption
        
        # Leave room for hashtags
        return caption[:max_length - 50] + "..."


# Zapier Setup Instructions
ZAPIER_SETUP = """
=== ZAPIER SETUP INSTRUCTIONS ===

1. Create Zapier Account
   → https://zapier.com

2. Create New Zap
   → Trigger: Webhook (Catch Hook)
   → Action: Instagram Business (Create Photo Post)

3. Copy Webhook URL
   → Paste into ZAPIER_WEBHOOK_URL env var

4. Test Connection
   → Run: python nova_zapier_connector.py --test

=== ENVIRONMENT VARIABLES ===

export ZAPIER_WEBHOOK_URL="https://hooks.zapier.com/..."
export ZAPIER_SECRET="your_webhook_secret"
export INSTAGRAM_ACCOUNT="@your_account"
"""


def test_connection():
    """Test Zapier connection"""
    connector = ZapierConnector()
    
    test_content = {
        "content": "NOVA test post",
        "caption": "Test from NOVA Zapier connector",
        "hashtags": "#nova #test #liquidsound",
        "theme": "test",
    }
    
    result = connector.send_content(test_content)
    
    print("Zapier Connection Test")
    print(f"Webhook URL: {connector.webhook_url or 'NOT CONFIGURED'}")
    print(f"Result: {result}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_connection()
    elif len(sys.argv) > 1 and sys.argv[1] == "--setup":
        print(ZAPIER_SETUP)
    else:
        print("NOVA Zapier Connector Ready")
        print("Options:")
        print("  --test   Test Zapier connection")
        print("  --setup  Show Zapier setup instructions")
