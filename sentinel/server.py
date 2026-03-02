"""
SENTINEL CEO Dashboard - Simple Flask App
"""
import os
import json
import logging
import asyncio
from flask import Flask, jsonify, render_template_string, request

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CEO Dashboard | LiQUiD SOUND</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }
        h1 { color: #58a6ff; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 10px 0; }
        .metric { font-size: 32px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🏢 CEO Dashboard</h1>
    <div class="card">
        <div>🛡️ Alerts: <span id="alerts">--</span></div>
        <div>📈 High-Score: <span id="highscore">--</span></div>
        <div>📝 Pending: <span id="pending">--</span></div>
        <div>⚠️ Risk: <span id="risk">--</span></div>
    </div>
    <script>
        fetch('/api/dashboard').then(r=>r.json()).then(d=>{
            document.getElementById('alerts').textContent = d.sentinel?.alerts || 0;
            document.getElementById('highscore').textContent = d.sentinel?.high_score_tokens || 0;
            document.getElementById('pending').textContent = d.content?.pending_approvals || 0;
            document.getElementById('risk').textContent = d.risk?.count || 0;
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/dashboard')
def dashboard_data():
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        return jsonify({
            "sentinel": {"alerts": int(r.get("sentinel:stats:alerts:today") or 0), "high_score_tokens": int(r.get("sentinel:stats:high_score:today") or 0)},
            "risk": {"count": len(r.lrange("cfo:risk_alerts", 0, 9) or []), "alerts": []},
            "market": {"count": 0, "updates": []},
            "content": {"pending_approvals": len(r.keys("content:draft:*") or [])},
            "dashboard": []
        })
    except Exception as e:
        log.error(f"Error: {e}")
        return jsonify({"error": str(e)})

@app.route('/health')
def health():
    return "OK"

@app.route('/api/security/scan')
def security_scan():
    """Trigger security vulnerability scan"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("security_scanner", "/app/tasks/security_scanner.py")
        ss_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ss_module)
        result = ss_module.scan_codebase()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/memory/search')
def memory_search():
    """Search session memory for context"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400
    
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Search recent memory
        results = []
        memory_keys = r.keys("memory:*")
        
        for key in memory_keys[:100]:  # Limit search
            data = r.get(key)
            if data and query.lower() in data.lower():
                results.append({"key": key, "preview": data[:200]})
        
        return jsonify({"query": query, "results": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/memory/flush', methods=['POST'])
def memory_flush():
    """Flush old session memory"""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Get TTL for flush
        import time
        max_age_hours = int(request.args.get('hours', 24))
        
        # Find and delete old memory
        count = 0
        memory_keys = r.keys("memory:*")
        
        for key in memory_keys:
            ttl = r.ttl(key)
            if ttl == -1:  # No expiry set
                r.delete(key)
                count += 1
        
        return jsonify({"status": "flushed", "keys_removed": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/market/analyze')
def market_analyze():
    """Run market analysis and simulation"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("market_analysis", "/app/tasks/market_analysis.py")
        ma_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ma_module)
        result = ma_module.analyze_market()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/predictions')
def ml_predictions():
    """Get ML predictions"""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        predictions = r.get('ml:predictions:latest')
        if predictions:
            return jsonify(json.loads(predictions))
        return jsonify({"predictions": [], "message": "No predictions yet"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/train')
def ml_train():
    """Trigger ML training pipeline"""
    try:
        # Direct import to avoid circular imports
        import importlib.util
        spec = importlib.util.spec_from_file_location("ml_pipeline", "/app/tasks/ml_pipeline.py")
        ml_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ml_module)
        result = ml_module.run_full_training_pipeline(7)
        return jsonify({"status": "completed", "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import threading
    
    # Start WebSocket listener in background
    def run_sentinel():
        try:
            import sentinel_ph2
            log.info("Starting SENTINEL WebSocket listener...")
            asyncio.run(sentinel_ph2.main())
        except Exception as e:
            log.error(f"Sentinel error: {e}")
    
    sentinel_thread = threading.Thread(target=run_sentinel, daemon=True)
    sentinel_thread.start()
    log.info("SENTINEL listener started in background")
    
    # Run Flask dashboard
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
