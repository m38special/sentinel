#!/usr/bin/env python3
"""
SENTINEL Health Dashboard
Real-time system monitoring
"""
import os
import json
import time
import redis
from datetime import datetime
from flask import Flask, jsonify, render_template_string

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Flask(__name__)

# Dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SENTINEL Health Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .logo { font-size: 24px; font-weight: bold; color: #58a6ff; }
        .status { padding: 5px 15px; border-radius: 20px; font-size: 14px; }
        .healthy { background: #238636; color: white; }
        .warning { background: #d29922; color: white; }
        .error { background: #da3633; color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; }
        .card h3 { margin: 0 0 15px 0; color: #8b949e; font-size: 14px; text-transform: uppercase; }
        .metric { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .metric-label { font-size: 12px; color: #8b949e; }
        .timestamp { color: #8b949e; font-size: 12px; margin-top: 10px; }
        .trend { font-size: 14px; }
        .up { color: #3fb950; }
        .down { color: #f85149; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SENTINEL</div>
        <div class="status healthy">ALL SYSTEMS OPERATIONAL</div>
    </div>
    <div class="grid">
        <div class="card">
            <h3>Tokens Scanned (24h)</h3>
            <div class="metric">{{ tokens_24h }}</div>
            <div class="metric-label">Total tokens processed</div>
        </div>
        <div class="card">
            <h3>High Score Signals</h3>
            <div class="metric">{{ high_signals }}</div>
            <div class="metric-label">Signals with score > 65</div>
        </div>
        <div class="card">
            <h3>Active Subscribers</h3>
            <div class="metric">{{ subscribers }}</div>
            <div class="metric-label">Signal subscribers</div>
        </div>
        <div class="card">
            <h3>API Requests (24h)</h3>
            <div class="metric">{{ api_requests }}</div>
            <div class="metric-label">Total API calls</div>
        </div>
        <div class="card">
            <h3>UAI Events</h3>
            <div class="metric">{{ uai_events }}</div>
            <div class="metric-label">Events processed</div>
        </div>
        <div class="card">
            <h3>Redis Memory</h3>
            <div class="metric">{{ redis_memory }}MB</div>
            <div class="metric-label">Used memory</div>
        </div>
    </div>
    <div class="timestamp">Last updated: {{ last_update }}</div>
</body>
</html>
"""

def get_metrics():
    """Get current system metrics"""
    r = redis.from_url(redis_url, decode_responses=True)
    
    metrics = {
        "tokens_24h": int(r.get("sentinel:stats:tokens:24h") or 0),
        "high_signals": int(r.get("sentinel:stats:high_score:24h") or 0),
        "subscribers": 0,  # Would count from subscriptions
        "api_requests": int(r.get("api:usage:total:24h") or 0),
        "uai_events": int(r.get("uai:events:count:24h") or 0),
        "redis_memory": 0,  # Would get from INFO
        "last_update": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    
    return metrics

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML, **get_metrics())

@app.route("/api/metrics")
def api_metrics():
    return jsonify(get_metrics())

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
