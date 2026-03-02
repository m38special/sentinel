#!/usr/bin/env python3
"""
ML Data Export Script
Exports training data from Redis for team sharing
"""
import os
import json
import redis

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

def export_ml_data():
    """Export all ML-related data from Redis"""
    data = {
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        "tokens_collected_total": r.get("ml:tokens:collected:total") or 0,
        "tokens_by_date": {},
        "outcomes": [],
        "ab_tests": []
    }
    
    # Get tokens collected by date
    for key in r.scan_iter("ml:tokens:collected:*"):
        if key != "ml:tokens:collected:total":
            date = key.split(":")[-1]
            data["tokens_by_date"][date] = r.get(key)
    
    # Get sample token data
    token_samples = []
    for key in r.scan_iter("ml:token:*"):
        tokens = r.lrange(key, 0, 9)  # Last 10
        for t in tokens:
            try:
                token_samples.append(json.loads(t))
            except:
                pass
        if len(token_samples) >= 50:
            break
    data["token_samples"] = token_samples[:50]
    
    # Get outcomes
    outcome_samples = []
    for key in r.scan_iter("ml:outcome:*"):
        outcomes = r.lrange(key, 0, 9)
        for o in outcomes:
            try:
                outcome_samples.append(json.loads(o))
            except:
                pass
    data["outcomes"] = outcome_samples[:50]
    
    # A/B test results
    for key in r.scan_iter("ab:*"):
        if key.endswith(":conversions"):
            exp_id = key.split(":")[1]
            data["ab_tests"].append({
                "experiment_id": exp_id,
                "conversions": r.zrange(key, 0, -1, withscores=True)
            })
    
    return data

if __name__ == "__main__":
    data = export_ml_data()
    print(json.dumps(data, indent=2))
