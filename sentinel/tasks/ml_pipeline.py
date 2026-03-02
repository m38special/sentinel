"""
Phase 7 - ML Model Training Tasks
SENTINEL | LiQUiD SOUND
Standalone version - no celery tasks, direct execution
"""
import os
import json
import logging
from datetime import datetime, timedelta
import redis

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def collect_training_data(lookback_days: int = 30):
    """Collect historical token data for ML training."""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    training_data = []
    end_date = datetime.utcnow().date()
    
    for i in range(lookback_days):
        date = end_date - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        keys = r.keys(f"token:*:{date_str}")
        
        for key in keys:
            token_data = r.hgetall(key)
            if token_data:
                training_data.append(token_data)
    
    r.set("ml:training_data:pending", json.dumps(training_data))
    log.info(f"Collected {len(training_data)} samples for training")
    
    return {"samples": len(training_data), "date_range": f"{lookback_days} days"}


def train_signal_model():
    """Train the token signal prediction model."""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    data_json = r.get("ml:training_data:pending")
    if not data_json:
        return {"status": "no_data", "message": "No training data available"}
    
    training_data = json.loads(data_json)
    
    if len(training_data) < 100:
        return {"status": "insufficient_data", "samples": len(training_data)}
    
    feature_names = [
        "liquidity_usd", "holder_count", "top10_concentration",
        "volume_24h", "price_change_1h", "social_score", "momentum"
    ]
    
    X = []
    y = []
    
    for record in training_data:
        try:
            features = [float(record.get(f, 0) or 0) for f in feature_names]
            X.append(features)
            label = 1 if record.get("signal_level") in ["HIGH", "CRITICAL"] else 0
            y.append(label)
        except (ValueError, TypeError):
            continue
    
    if len(X) < 50:
        return {"status": "insufficient_valid_data", "samples": len(X)}
    
    try:
        import numpy as np
        X = np.array(X)
        y = np.array(y)
    except ImportError:
        return {"error": "numpy not installed"}
    
    # Split
    try:
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    except ImportError:
        return {"error": "sklearn not installed"}
    
    # Train
    try:
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
    except ImportError:
        return {"error": "sklearn not installed"}
    
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    model_info = {
        "trained_at": datetime.utcnow().isoformat(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_accuracy": float(train_score),
        "test_accuracy": float(test_score),
        "feature_names": feature_names
    }
    
    r.set("ml:model:signal:info", json.dumps(model_info))
    log.info(f"Model trained: train={train_score:.3f}, test={test_score:.3f}")
    
    return {"status": "trained", "train_accuracy": train_score, "test_accuracy": test_score}


def run_full_training_pipeline(lookback_days: int = 30):
    """Full ML training pipeline."""
    log.info("Starting ML training pipeline...")
    
    # Step 1: Collect data
    result1 = collect_training_data(lookback_days)
    if result1.get("samples", 0) < 50:
        return {"status": "insufficient_data", **result1}
    
    # Step 2: Train
    result2 = train_signal_model()
    
    return {"collection": result1, "training": result2}
