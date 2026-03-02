#!/usr/bin/env python3
"""
AXIOM Scoring Engine v2.0
Enhanced with social velocity, liquidity depth, and holder metrics
"""
import os
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class SignalLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SKIP = "SKIP"


@dataclass
class TokenScore:
    symbol: str
    address: str
    total_score: float
    components: Dict[str, float]
    signal_level: SignalLevel
    risk_factors: List[str]
    timestamp: str


class AxiomScorerV2:
    """Enhanced scoring with v2.0 metrics"""
    
    # Weights for v2.0
    WEIGHTS = {
        "liquidity": 0.20,
        "holder_distribution": 0.15,
        "social_velocity": 0.20,
        "momentum": 0.15,
        "security": 0.15,
        "volume": 0.15,
    }
    
    # Thresholds
    MIN_LIQUIDITY = 5000  # USD
    MIN_HOLDERS = 50
    MAX_CONCENTRATION = 0.30  # Top 10 holders %
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def score_token(self, token_data: dict) -> TokenScore:
        """Calculate comprehensive token score"""
        
        components = {}
        
        # 1. Liquidity Score (0-100)
        liquidity = token_data.get("liquidity_usd", 0)
        components["liquidity"] = self._score_liquidity(liquidity)
        
        # 2. Holder Distribution (0-100)
        holders = token_data.get("holder_count", 0)
        top10_concentration = token_data.get("top10_concentration", 1.0)
        components["holder_distribution"] = self._score_holders(holders, top10_concentration)
        
        # 3. Social Velocity (NOVA signals)
        social_score = self._get_nova_signal(token_data.get("symbol"))
        components["social_velocity"] = social_score
        
        # 4. Momentum (price action)
        price_change = token_data.get("price_change_1h", 0)
        components["momentum"] = self._score_momentum(price_change)
        
        # 5. Security Score (rug pull indicators)
        components["security"] = self._score_security(token_data)
        
        # 6. Volume Score
        volume_24h = token_data.get("volume_24h", 0)
        components["volume"] = self._score_volume(volume_24h)
        
        # Calculate weighted total
        total_score = sum(
            components[k] * self.WEIGHTS[k] 
            for k in self.WEIGHTS
        )
        
        # Determine signal level
        signal_level = self._determine_signal(total_score, components)
        
        # Identify risk factors
        risk_factors = self._identify_risks(token_data, components)
        
        return TokenScore(
            symbol=token_data.get("symbol", "UNKNOWN"),
            address=token_data.get("address", ""),
            total_score=round(total_score, 2),
            components={k: round(v, 2) for k, v in components.items()},
            signal_level=signal_level,
            risk_factors=risk_factors,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _score_liquidity(self, liquidity: float) -> float:
        """Score liquidity depth"""
        if liquidity >= 100000:
            return 100
        elif liquidity >= 50000:
            return 80
        elif liquidity >= 25000:
            return 60
        elif liquidity >= 10000:
            return 40
        elif liquidity >= self.MIN_LIQUIDITY:
            return 20
        return 0
    
    def _score_holders(self, count: int, concentration: float) -> float:
        """Score holder distribution"""
        # Count score
        if count >= 1000:
            count_score = 50
        elif count >= 500:
            count_score = 40
        elif count >= 200:
            count_score = 30
        elif count >= self.MIN_HOLDERS:
            count_score = 20
        else:
            count_score = 0
        
        # Concentration score (lower = better)
        if concentration <= 0.1:
            conc_score = 50
        elif concentration <= 0.2:
            conc_score = 40
        elif concentration <= self.MAX_CONCENTRATION:
            conc_score = 30
        else:
            conc_score = 0
        
        return count_score + conc_score
    
    def _get_nova_signal(self, symbol: str) -> float:
        """Get social velocity from NOVA"""
        key = f"nova:signal:{symbol}"
        signal = self.redis.get(key)
        if signal:
            return float(signal) * 100  # Convert 0-1 to 0-100
        return 50  # Default neutral
    
    def _score_momentum(self, change: float) -> float:
        """Score price momentum"""
        if -5 <= change <= 10:
            return 100 - abs(change)
        elif -15 <= change <= 25:
            return 70
        return 30
    
    def _score_security(self, token_data: dict) -> float:
        """Score security indicators"""
        score = 100
        
        # Honeypot check
        if token_data.get("is_honeypot", False):
            return 0
        
        # Mint authority
        if token_data.get("mint_authority", "null") != "null":
            score -= 30
        
        # Freeze authority
        if token_data.get("freeze_authority", "null") != "null":
            score -= 20
        
        # Liquidity lock
        if not token_data.get("liquidity_locked", False):
            score -= 40
        
        return max(0, score)
    
    def _score_volume(self, volume: float) -> float:
        """Score trading volume"""
        if volume >= 1000000:
            return 100
        elif volume >= 500000:
            return 80
        elif volume >= 100000:
            return 60
        elif volume >= 50000:
            return 40
        elif volume >= 10000:
            return 20
        return 5
    
    def _determine_signal(self, total: float, components: dict) -> SignalLevel:
        """Determine signal level"""
        # Must pass security check
        if components.get("security", 100) < 50:
            return SignalLevel.SKIP
        
        if total >= 80:
            return SignalLevel.CRITICAL
        elif total >= 65:
            return SignalLevel.HIGH
        elif total >= 50:
            return SignalLevel.MEDIUM
        elif total >= 35:
            return SignalLevel.LOW
        return SignalLevel.SKIP
    
    def _identify_risks(self, token_data: dict, components: dict) -> List[str]:
        """Identify specific risk factors"""
        risks = []
        
        if components.get("liquidity", 100) < 30:
            risks.append("LOW_LIQUIDITY")
        
        if components.get("holder_distribution", 100) < 40:
            risks.append("CONCENTRATED_HOLDERS")
        
        if components.get("security", 100) < 70:
            risks.append("SECURITY_CONCERN")
        
        if components.get("volume", 100) < 20:
            risks.append("LOW_VOLUME")
        
        return risks
    
    def publish_signal(self, score: TokenScore):
        """Publish score to UAI"""
        msg = {
            "intent": "analyze.token_score",
            "symbol": score.symbol,
            "address": score.address,
            "score": score.total_score,
            "signal_level": score.signal_level.value,
            "components": score.components,
            "risk_factors": score.risk_factors,
            "timestamp": score.timestamp,
        }
        
        # Publish to UAI
        self.redis.publish("uai:events:token_signal", json.dumps(msg))
        
        # Cache for NOVA
        self.redis.setex(
            f"axiom:score:{score.symbol}",
            3600,  # 1hr TTL
            json.dumps({"score": score.total_score, "level": score.signal_level.value})
        )


# Backtest interface
def backtest_strategy(token_history: List[dict], returns: List[float]) -> dict:
    """
    Backtest scoring strategy using vectorbt-style analysis
    """
    import numpy as np
    
    if not returns:
        return {"error": "No returns data"}
    
    returns = np.array(returns)
    
    # Calculate metrics
    total_return = np.prod(1 + returns) - 1
    sharpe = returns.mean() / returns.std() * np.sqrt(365) if returns.std() > 0 else 0
    max_dd = (returns.cumsum() - np.maximum.accumulate(returns.cumsum())).min()
    
    return {
        "total_return": round(total_return * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "win_rate": round((returns > 0).mean() * 100, 2),
        "trades": len(returns),
    }


if __name__ == "__main__":
    # Test scorer
    scorer = AxiomScorerV2()
    
    test_token = {
        "symbol": "TEST",
        "address": "TesT123...",
        "liquidity_usd": 75000,
        "holder_count": 450,
        "top10_concentration": 0.15,
        "price_change_1h": 5.2,
        "volume_24h": 250000,
        "is_honeypot": False,
        "liquidity_locked": True,
        "mint_authority": "null",
        "freeze_authority": "null",
    }
    
    score = scorer.score_token(test_token)
    print(f"Token: {score.symbol}")
    print(f"Score: {score.total_score}")
    print(f"Signal: {score.signal_level.value}")
    print(f"Components: {score.components}")
    print(f"Risks: {score.risk_factors}")
