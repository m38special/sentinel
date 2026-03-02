"""
Unit tests for AXIOM Scorer v2
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from axiom.axiom_scorer_v2 import AxiomScorerV2, SignalLevel


class TestAxiomScorerV2:
    """Test suite for AXIOM scoring engine"""
    
    @pytest.fixture
    def scorer(self):
        return AxiomScorerV2()
    
    @pytest.fixture
    def sample_token(self):
        return {
            "symbol": "TEST",
            "address": "Test123...",
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
    
    def test_score_token_returns_token_score(self, scorer, sample_token):
        """Test that score_token returns TokenScore object"""
        score = scorer.score_token(sample_token)
        assert score.symbol == "TEST"
        assert score.total_score > 0
    
    def test_liquidity_scoring(self, scorer):
        """Test liquidity scoring thresholds"""
        # High liquidity
        assert scorer._score_liquidity(100000) == 100
        # Medium liquidity
        assert scorer._score_liquidity(50000) == 80
        # Low liquidity
        assert scorer._score_liquidity(5000) == 0
    
    def test_holder_scoring(self, scorer):
        """Test holder distribution scoring"""
        # Good distribution
        score = scorer._score_holders(500, 0.15)
        assert score > 50
        # Poor distribution
        score = scorer._score_holders(10, 0.8)
        assert score < 30
    
    def test_security_blocks_honeypot(self, scorer, sample_token):
        """Test that honeypots are blocked"""
        sample_token["is_honeypot"] = True
        score = scorer.score_token(sample_token)
        assert score.signal_level == SignalLevel.SKIP
    
    def test_signal_level_thresholds(self, scorer, sample_token):
        """Test signal level thresholds"""
        # High score = CRITICAL
        sample_token["liquidity_usd"] = 200000
        sample_token["holder_count"] = 2000
        sample_token["volume_24h"] = 2000000
        score = scorer.score_token(sample_token)
        assert score.signal_level in [SignalLevel.CRITICAL, SignalLevel.HIGH]
    
    def test_risk_factors_identified(self, scorer, sample_token):
        """Test that risk factors are identified"""
        sample_token["liquidity_usd"] = 1000  # Low liquidity
        score = scorer.score_token(sample_token)
        assert "LOW_LIQUIDITY" in score.risk_factors


class TestSubscriptionManager:
    """Test suite for subscription manager"""
    
    def test_create_subscription_validates_input(self):
        """Test that create_subscription validates input"""
        # Would need to mock Redis
        pass
    
    def test_api_key_format(self):
        """Test API key generation format"""
        # Would need to mock Redis
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
