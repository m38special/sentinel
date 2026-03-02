"""
Enhanced ML Pipeline
SENTINEL Phase 7 | LiQUiD SOUND
"""
import os
import json
import logging
from datetime import datetime, timedelta
import redis
from tasks import app

log = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_token_data():
    """Fetch token data from Redis"""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    tokens = []
    for key in r.keys("token:*"):
        data = r.hgetall(key)
        if data:
            tokens.append(data)
    return tokens


def analyze_token_features(tokens):
    """Extract ML features from tokens"""
    features = []
    for t in tokens:
        try:
            feature = {
                'liquidity_usd': float(t.get('liquidity_usd', 0) or 0),
                'holder_count': int(t.get('holder_count', 0) or 0),
                'volume_24h': float(t.get('volume_24h', 0) or 0),
                'price_change_1h': float(t.get('price_change_1h', 0) or 0),
                'price_change_24h': float(t.get('price_change_24h', 0) or 0),
                'social_score': int(t.get('social_score', 0) or 0),
                'momentum': float(t.get('momentum', 0) or 0),
            }
            features.append(feature)
        except:
            continue
    return features


def predict_signals():
    """Predict trading signals based on features"""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    tokens = get_token_data()
    features = analyze_token_features(tokens)
    
    predictions = []
    for i, (token, feature) in enumerate(zip(tokens, features)):
        # Simple rule-based scoring (replace with ML model)
        score = 0
        if feature['liquidity_usd'] > 10000: score += 20
        if feature['holder_count'] > 100: score += 15
        if feature['volume_24h'] > 50000: score += 15
        if feature['price_change_1h'] > 5: score += 20
        if feature['price_change_1h'] < -5: score += 10
        if feature['social_score'] > 50: score += 15
        if feature['momentum'] > 0.5: score += 15
        
        if score >= 85:
            signal = 'CRITICAL'
        elif score >= 70:
            signal = 'HIGH'
        elif score >= 50:
            signal = 'MEDIUM'
        else:
            signal = 'LOW'
        
        predictions.append({
            'token': token.get('symbol', token.get('mint', 'UNKNOWN')),
            'score': score,
            'signal': signal,
            'features': feature
        })
    
    # Store predictions
    r.set('ml:predictions:latest', json.dumps(predictions))
    return predictions


@app.task(name='tasks.ml_pipeline.run_predictions', bind=True, max_retries=2, queue='sentinel')
def run_predictions(self):
    """Generate token predictions"""
    predictions = predict_signals()
    return {'predictions': len(predictions), 'signals': [p['signal'] for p in predictions]}


@app.task(name='tasks.ml_pipeline.collect_and_predict', bind=True, max_retries=1, queue='sentinel')
def collect_and_predict(self):
    """Full ML pipeline: collect data + predict"""
    tokens = get_token_data()
    predictions = predict_signals()
    
    return {
        'tokens_collected': len(tokens),
        'predictions': len(predictions),
        'high_signals': len([p for p in predictions if p['signal'] in ['HIGH', 'CRITICAL']])
    }


# Schedule: Every 15 minutes
from celery.schedules import crontab

app.conf.beat_schedule = {
    **app.conf.beat_schedule,
    "ml-predictions-15min": {
        "task": "tasks.ml_pipeline.run_predictions",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "sentinel"},
    },
}


if __name__ == "__main__":
    result = predict_signals()
    print(json.dumps(result[:5], indent=2))
