#!/usr/bin/env python3
"""
Phase 7 ML Pipeline
Token Scoring Model Training
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import redis

# ML Libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, mean_squared_error
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("ML libraries not installed")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class TokenMLPipeline:
    """ML pipeline for token scoring"""
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.model = None
        self.feature_names = [
            "liquidity_usd",
            "holder_count",
            "top10_concentration",
            "volume_24h",
            "price_change_1h",
            "social_score",
            "momentum",
        ]
    
    def prepare_features(self, token_data: dict) -> np.ndarray:
        """Extract features from token data"""
        features = []
        for name in self.feature_names:
            features.append(token_data.get(name, 0))
        return np.array(features).reshape(1, -1)
    
    def train_signal_model(self, historical_data: List[dict]) -> Dict:
        """
        Train model to predict high-signal tokens
        """
        if not ML_AVAILABLE:
            return {"error": "ML libraries not available"}
        
        # Prepare data
        X = []
        y = []
        
        for record in historical_data:
            features = [record.get(f, 0) for f in self.feature_names]
            X.append(features)
            y.append(1 if record.get("signal_level") in ["HIGH", "CRITICAL"] else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        predictions = self.model.predict(X_test)
        report = classification_report(y_test, predictions, output_dict=True)
        
        # Save model
        self._save_model()
        
        return {
            "status": "trained",
            "accuracy": report["accuracy"],
            "precision": report["1"]["precision"] if "1" in report else 0,
            "recall": report["1"]["recall"] if "1" in report else 0,
        }
    
    def predict_signal(self, token_data: dict) -> Dict:
        """Predict signal level for token"""
        if not self.model:
            # Load existing model
            self._load_model()
        
        if not self.model:
            return {"error": "No model available"}
        
        features = self.prepare_features(token_data)
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0]
        
        return {
            "prediction": "HIGH" if prediction == 1 else "LOW",
            "confidence": float(max(probability)),
            "probabilities": {"low": float(probability[0]), "high": float(probability[1])},
        }
    
    def train_regression_model(self, historical_returns: List[dict]) -> Dict:
        """
        Train model to predict token returns
        """
        if not ML_AVAILABLE:
            return {"error": "ML libraries not available"}
        
        X = []
        y = []
        
        for record in historical_returns:
            features = [record.get(f, 0) for f in self.feature_names]
            X.append(features)
            y.append(record.get("return_24h", 0))
        
        X = np.array(X)
        y = np.array(y)
        
        # Train
        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Evaluate
        predictions = model.predict(X)
        mse = mean_squared_error(y, predictions)
        
        return {
            "status": "trained",
            "mse": float(mse),
            "rmse": float(np.sqrt(mse)),
        }
    
    def _save_model(self):
        """Save model to Redis"""
        if self.model:
            model_data = pickle.dumps(self.model)
            self.redis.set("ml:model:signal", model_data)
    
    def _load_model(self):
        """Load model from Redis"""
        model_data = self.redis.get("ml:model:signal")
        if model_data:
            self.model = pickle.loads(model_data)


class FeatureEngineering:
    """Feature engineering for ML"""
    
    @staticmethod
    def compute_social_velocity(social_data: List[dict]) -> float:
        """Compute social media velocity score"""
        if not social_data:
            return 0
        
        # Recent posts vs older posts
        now = datetime.utcnow()
        recent = sum(1 for s in social_data 
                    if (now - datetime.fromisoformat(s.get("timestamp", now))).days < 1)
        older = sum(1 for s in social_data 
                   if 1 <= (now - datetime.fromisoformat(s.get("timestamp", now))).days <= 7)
        
        if older == 0:
            return recent * 10
        
        return (recent / older) * 10
    
    @staticmethod
    def compute_holder_distribution(holder_data: List[dict]) -> Dict:
        """Analyze holder distribution"""
        if not holder_data:
            return {"gini": 1.0, "top10_pct": 1.0}
        
        amounts = sorted([h.get("balance", 0) for h in holder_data], reverse=True)
        total = sum(amounts)
        
        if total == 0:
            return {"gini": 1.0, "top10_pct": 1.0}
        
        top10 = sum(amounts[:10]) / total
        
        # Simple Gini
        n = len(amounts)
        gini = sum((2 * (i + 1) - n - 1) * amounts[i] for i in range(n)) / (n * total)
        
        return {"gini": abs(gini), "top10_pct": top10}
    
    @staticmethod
    def compute_liquidity_score(liquidity_history: List[float]) -> float:
        """Compute liquidity stability score"""
        if len(liquidity_history) < 2:
            return 50
        
        arr = np.array(liquidity_history)
        cv = arr.std() / arr.mean() if arr.mean() > 0 else 1
        
        # Lower coefficient of variation = higher score
        return max(0, min(100, 100 * (1 - cv)))


# A/B Testing Framework
class ABTestFramework:
    """A/B testing for strategy variations"""
    
    def __init__(self):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def create_experiment(self, name: str, variants: List[str]) -> str:
        """Create new A/B test"""
        exp_id = f"exp_{datetime.utcnow().timestamp()}"
        
        self.redis.hset(f"ab:{exp_id}", mapping={
            "name": name,
            "variants": json.dumps(variants),
            "created": datetime.utcnow().isoformat(),
        })
        
        return exp_id
    
    def get_variant(self, exp_id: str, user_id: str) -> str:
        """Get variant for user (deterministic)"""
        key = f"ab:{exp_id}:alloc:{user_id}"
        allocated = self.redis.get(key)
        
        if allocated:
            return allocated
        
        # Get variants
        variants = json.loads(self.redis.hget(f"ab:{exp_id}", "variants") or "[]")
        if not variants:
            return None
        
        # Deterministic allocation
        variant = variants[hash(user_id) % len(variants)]
        
        self.redis.setex(key, 86400 * 30, variant)
        
        return variant
    
    def record_conversion(self, exp_id: str, user_id: str, value: float = 1.0):
        """Record conversion"""
        variant = self.get_variant(exp_id, user_id)
        if variant:
            self.redis.zincrby(f"ab:{exp_id}:conversions", value, variant)
    
    def get_results(self, exp_id: str) -> Dict:
        """Get experiment results"""
        conversions = self.redis.zrange(f"ab:{exp_id}:conversions", 0, -1, withscores=True)
        
        return {
            "variants": {v: c for v, c in conversions},
        }


if __name__ == "__main__":
    if ML_AVAILABLE:
        pipeline = TokenMLPipeline()
        print("ML Pipeline ready")
    else:
        print("Install scikit-learn for ML features")
