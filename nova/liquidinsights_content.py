#!/usr/bin/env python3
"""
Content Generator for @liquidinsights
NOVA - Market Education & Intelligence
"""
import os
import json
import random
from datetime import datetime

# Theme: Market education, crypto intelligence, DeFi insights

MARKET_THEMES = [
    "crypto market analysis",
    "defi education",
    "solana ecosystem",
    "tokenomics 101",
    "market sentiment",
    " whale movements",
    "liquidity pools",
    "yield farming",
    "nft market",
    "web3 trends",
]

def generate_insight(topic: str) -> str:
    """Generate market insight caption"""
    
    templates = [
        f"Quick {topic} breakdown:\n\nHere's what you need to know:\n\n1. The market is [condition]\n2. [key insight]\n3. What to watch:\n\nSave this for later\n\n#crypto #{topic.replace(' ','')} #investing #web3",
        f"{topic.upper()} 101\n\nMost people don't understand this. Here's the truth:\n\n[key insight]\n\nBookmark this. You'll need it.\n\n#crypto #education #{topic.replace(' ','')} #defi",
        f"The {topic} landscape is shifting.\n\nHere's what's actually happening:\n\n[insight]\n\nDon't get left behind.\n\n#crypto #{topic.replace(' ','')} #market",
    ]
    
    return random.choice(templates)

def generate_market_update() -> str:
    """Generate daily market update"""
    
    crypto_updates = [
        "BTC showing resilience at support levels",
        "SOL volatility increasing - watch for breakout",
        "DeFi TVL holding strong despite market conditions",
        "New token launches picking up on pump.fun",
        "Whale activity detected in SOL pools",
    ]
    
    insights = [
        "Smart money is accumulating.",
        "The correction is creating opportunities.",
        "Liquidity is shifting to new narratives.",
        "Don't chase - prepare.",
        "The next move is being built right now.",
    ]
    
    return f"""MARKET PULSE | {datetime.now().strftime('%B %d')}

CRYPTO
{random.choice(crypto_updates)}

{random.choice(insights)}

#crypto #solana #trading"""

def generate_content_batch(count: int = 5) -> list:
    """Generate batch of content"""
    content = []
    
    for i in range(count):
        theme = random.choice(MARKET_THEMES)
        content.append({
            "id": f"liquid-{datetime.now().strftime('%Y%m%d')}-{i+1}",
            "platform": "instagram",
            "account": "@liquidinsights",
            "type": random.choice(["insight", "market_update", "educational"]),
            "theme": theme,
            "content": generate_insight(theme),
            "generated_at": datetime.now().isoformat(),
            "status": "draft",
            "generated_by": "NOVA"
        })
    
    return content

def get_hashtags(topic: str) -> str:
    base = "#crypto #investing #web3 #trading"
    topic_tag = "#" + topic.replace(" ", "")
    return f"{base} {topic_tag}"

if __name__ == "__main__":
    print("Generating @liquidinsights content...\n")
    
    # Market update
    print("=== MARKET PULSE ===")
    print(generate_market_update())
    print("\n=== CONTENT BATCH ===")
    
    content = generate_content_batch(3)
    for post in content:
        print(f"\n--- {post['id']} ---")
        print(post['content'][:200] + "...")
