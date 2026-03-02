"""
Phase 7 - ML Model Training Tasks
SENTINEL | LiQUiD SOUND
"""
import os
import json
import logging
from datetime import datetime, timedelta
from celery import chain, group
from tasks import app

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@app.task(
    name="tasks.ml_pipeline.collect_training_data",
    bind=True,
    max_retries=2,
    queue="sentinel",
)
def collect_training_data(self, lookback_days: int = 30):
    """
    Collect historical token data for ML training.
    Gathers data from the last N days.
    """
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    training_data = []
    end_date = datetime.utcnow().date()
    
    for i in range(lookback_days):
        date = end_date - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        # Get tokens for this date
        keys = r.keys(f"token:*:{date_str}")
        
        for key in keys:
            token_data = r.hgetall(key)
            if token_data:
                training_data.append(token_data)
    
    # Store for training
    r.set("ml:training_data:pending", json.dumps(training_data))
    log.info(f"Collected {len(training_data)} samples for training")
    
    return {"samples": len(training_data), "date_range": f"{lookback_days} days"}


@app.task(
    name="tasks.ml_pipeline.train_signal_model",
    bind=True,
    max_retries=2,
    queue="sentinel",
)
def train_signal_model(self):
    """
    Train the token signal prediction model.
    Uses RandomForest to predict HIGH/CRITICAL signals.
    """
    import redis
    import numpy as np
    
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Check for training data
    data_json = r.get("ml:training_data:pending")
    if not data_json:
        return {"status": "no_data", "message": "No training data available"}
    
    training_data = json.loads(data_json)
    
    if len(training_data) < 100:
        return {"status": "insufficient_data", "samples": len(training_data)}
    
    # Features
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
            # Label: 1 for HIGH/CRITICAL, 0 otherwise
            label = 1 if record.get("signal_level") in ["HIGH", "CRITICAL"] else 0
            y.append(label)
        except (ValueError, TypeError):
            continue
    
    if len(X) < 50:
        return {"status": "insufficient_valid_data", "samples": len(X)}
    
    X = np.array(X)
    y = np.array(y)
    
    # Simple train/test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    # Save model info to Redis
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


@app.task(
    name="tasks.ml_pipeline.run_full_training_pipeline",
    bind=True,
    max_retries=1,
    queue="sentinel",
)
def run_full_training_pipeline(self, lookback_days: int = 30):
    """
    Full ML training pipeline:
    1. Collect training data
    2. Train model
    3. Save to model registry
    """
    # Chain: collect -> train
    result = chain(
        collect_training_data.s(lookback_days),
        train_signal_model.s()
    )()
    
    return {"status": "pipeline_started", "pipeline_id": result.id}


# Schedule: Run training weekly (Sunday 2am UTC)
from celery.schedules import crontab

app.conf.beat_schedule = {
    **app.conf.beat_schedule,
    "ml-training-weekly-sunday": {
        "task": "tasks.ml_pipeline.run_full_training_pipeline",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2am UTC
        "options": {"queue": "sentinel"},
    },
}
