"""
SENTINEL CEO Dashboard - Simple Flask App
"""
import os
import json
import logging
from flask import Flask, jsonify, render_template_string

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
