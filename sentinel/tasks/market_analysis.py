"""
Market Analysis & Simulation Script
SENTINEL Phase 8 | LiQUiD SOUND

Scans market data and simulates potential moves based on:
- Historical patterns
- Technical indicators
- Sentiment analysis
"""
import os
import json
import random
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_market_data():
    """Fetch current market data from Redis (populated by SENTINEL)"""
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    market_data = {
        "tokens": [],
        "sentiment": "neutral",
        "fear_greed_index": 50,
        "volume_24h": 0,
        "market_cap_change": 0
    }
    
    # Get recent tokens
    for key in r.keys("token:*"):
        token = r.hgetall(key)
        if token:
            market_data["tokens"].append(token)
    
    # Get market metrics
    market_data["fear_greed_index"] = int(r.get("market:fear_greed") or 50)
    market_data["sentiment"] = r.get("market:sentiment") or "neutral"
    
    return market_data


def analyze_historical_patterns(market_data: dict) -> dict:
    """Analyze historical patterns from stored data"""
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    patterns = {
        "bullish_signals": 0,
        "bearish_signals": 0,
        "sideways_signals": 0,
        "confidence": 0.0,
        "key_levels": []
    }
    
    # Analyze stored token data
    tokens = market_data.get("tokens", [])
    
    for token in tokens:
        # Check price momentum
        try:
            price_change = float(token.get("price_change_24h", 0) or 0)
            if price_change > 5:
                patterns["bullish_signals"] += 1
            elif price_change < -5:
                patterns["bearish_signals"] += 1
            else:
                patterns["sideways_signals"] += 1
        except (ValueError, TypeError):
            pass
    
    # Calculate confidence
    total = patterns["bullish_signals"] + patterns["bearish_signals"] + patterns["sideways_signals"]
    if total > 0:
        patterns["confidence"] = min(0.9, total / 10)  # Max 90% confidence
    
    return patterns


def simulate_market_moves(market_data: dict, patterns: dict, days: int = 1) -> dict:
    """Simulate potential market moves based on patterns and data"""
    
    scenarios = {
        "bullish": {"probability": 0.30, "impact": "+5-15%"},
        "bearish": {"probability": 0.25, "impact": "-3-10%"},
        "sideways": {"probability": 0.35, "impact": "-2%+2%"},
        "volatile": {"probability": 0.10, "impact": "-15%+20%"}
    }
    
    # Adjust probabilities based on patterns
    if patterns.get("bullish_signals", 0) > patterns.get("bearish_signals", 0):
        scenarios["bullish"]["probability"] += 0.15
        scenarios["bearish"]["probability"] -= 0.10
    elif patterns.get("bearish_signals", 0) > patterns.get("bullish_signals", 0):
        scenarios["bearish"]["probability"] += 0.15
        scenarios["bullish"]["probability"] -= 0.10
    
    # Fear/greed adjustment
    fear_greed = market_data.get("fear_greed_index", 50)
    if fear_greed > 70:  # Extreme greed
        scenarios["volatile"]["probability"] += 0.10
    elif fear_greed < 30:  # Extreme fear
        scenarios["bullish"]["probability"] += 0.10  # Potential bounce
    
    # Normalize probabilities
    total = sum(s["probability"] for s in scenarios.values())
    for s in scenarios.values():
        s["probability"] = round(s["probability"] / total, 2)
    
    # Generate simulation
    simulation = {
        "timestamp": datetime.utcnow().isoformat(),
        "analysis_period": f"{days} day(s)",
        "market_conditions": {
            "sentiment": market_data.get("sentiment", "neutral"),
            "fear_greed_index": fear_greed,
            "tokens_analyzed": len(market_data.get("tokens", []))
        },
        "patterns": patterns,
        "scenarios": scenarios,
        "recommendations": []
    }
    
    # Generate recommendations
    if scenarios["bullish"]["probability"] > 0.35:
        simulation["recommendations"].append({
            "action": "ACCUMULATE",
            "target": "quality_tokens",
            "reason": "Bullish patterns detected"
        })
    elif scenarios["bearish"]["probability"] > 0.35:
        simulation["recommendations"].append({
            "action": "REDUCE_EXPOSURE",
            "target": "volatile_tokens",
            "reason": "Bearish patterns detected"
        })
    else:
        simulation["recommendations"].append({
            "action": "HOLD",
            "target": "stable_positions",
            "reason": "Sideways/neutral market"
        })
    
    return simulation


def generate_market_report():
    """Generate full market analysis report"""
    log.info("Generating market analysis report...")
    
    # Get market data
    market_data = get_market_data()
    
    # Analyze patterns
    patterns = analyze_historical_patterns(market_data)
    
    # Simulate moves
    simulation = simulate_market_moves(market_data, patterns)
    
    # Store in Redis
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.set("market:simulation:latest", json.dumps(simulation))
    r.lpush("market:simulations:history", json.dumps(simulation))
    r.ltrim("market:simulations:history", 0, 99)  # Keep last 100
    
    log.info(f"Market simulation complete: {simulation['recommendations']}")
    
    return simulation


if __name__ == "__main__":
    report = generate_market_report()
    print(json.dumps(report, indent=2))
