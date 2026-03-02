"""
CEO Dashboard Server
SENTINEL Phase 6 | LiQUiD SOUND
"""
import os
import json
import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template_string
import redis

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CEO Dashboard | LiQUiD SOUND</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
            padding: 24px 32px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 24px; font-weight: 700; color: #58a6ff; }
        .timestamp { color: #8b949e; font-size: 14px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .card-title { font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
        .card-icon { font-size: 20px; }
        
        .metric { font-size: 36px; font-weight: 700; color: #fff; }
        .metric-label { font-size: 13px; color: #8b949e; margin-top: 4px; }
        
        .alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; }
        .alert-critical { background: rgba(255,68,68,0.15); border-left: 3px solid #ff4444; }
        .alert-high { background: rgba(255,140,0,0.15); border-left: 3px solid #ff8c00; }
        .alert-medium { background: rgba(255,215,0,0.15); border-left: 3px solid #ffd700; }
        
        .feed-item {
            padding: 12px 0;
            border-bottom: 1px solid #30363d;
        }
        .feed-item:last-child { border-bottom: none; }
        .feed-title { font-weight: 600; color: #fff; margin-bottom: 4px; }
        .feed-time { font-size: 12px; color: #8b949e; }
        
        .btn {
            background: #238636;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover { background: #2ea043; }
        
        .status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
        .status-live { background: #00c853; }
        .status-offline { background: #ff4444; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏢 CEO Dashboard</div>
        <div>
            <span class="status status-live"></span>
            <span class="timestamp">Last updated: <span id="lastUpdate">--</span></span>
            <button class="btn" onclick="refresh()" style="margin-left: 16px;">↻ Refresh</button>
        </div>
    </div>
    
    <div class="container">
        <!-- Key Metrics -->
        <div class="grid" style="margin-bottom: 24px;">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🛡️ SENTINEL Alerts</span>
                </div>
                <div class="metric" id="alertCount">--</div>
                <div class="metric-label">Last 24 hours</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📈 High-Score Tokens</span>
                </div>
                <div class="metric" id="highScoreCount">--</div>
                <div class="metric-label">Detected today</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📝 Pending Approvals</span>
                </div>
                <div class="metric" id="pendingContent">--</div>
                <div class="metric-label">Awaiting review</div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⚠️ Risk Alerts</span>
                </div>
                <div class="metric" id="riskCount">--</div>
                <div class="metric-label">Active</div>
            </div>
        </div>
        
        <div class="grid">
            <!-- Risk Alerts -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🚨 Risk Alerts</span>
                    <span class="card-icon">⚠️</span>
                </div>
                <div id="riskAlerts">
                    <div style="color: #8b949e; text-align: center; padding: 20px;">Loading...</div>
                </div>
            </div>
            
            <!-- Market Updates -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📈 Market Updates</span>
                    <span class="card-icon">📊</span>
                </div>
                <div id="marketUpdates">
                    <div style="color: #8b949e; text-align: center; padding: 20px;">Loading...</div>
                </div>
            </div>
            
            <!-- Dashboard Feed -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📋 Recent Activity</span>
                    <span class="card-icon">📌</span>
                </div>
                <div id="dashboardFeed">
                    <div style="color: #8b949e; text-align: center; padding: 20px;">Loading...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        async function refresh() {
            try {
                const res = await fetch('/api/dashboard');
                const data = await res.json();
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                
                // Metrics
                document.getElementById('alertCount').textContent = data.sentinel?.alerts || 0;
                document.getElementById('highScoreCount').textContent = data.sentinel?.high_score_tokens || 0;
                document.getElementById('pendingContent').textContent = data.content?.pending_approvals || 0;
                document.getElementById('riskCount').textContent = data.risk?.count || 0;
                
                // Risk Alerts
                const riskHtml = (data.risk?.alerts || []).map(a => 
                    `<div class="alert alert-${a.severity || 'medium'}">
                        <strong>${a.title}</strong><br>
                        <small>${a.description || ''}</small>
                    </div>`
                ).join('') || '<div style="color: #8b949e;">No active risk alerts</div>';
                document.getElementById('riskAlerts').innerHTML = riskHtml;
                
                // Market Updates
                const marketHtml = (data.market?.updates || []).slice(0, 5).map(u => 
                    `<div class="feed-item">
                        <div class="feed-title">${u.title}</div>
                        <div class="feed-time">${new Date(u.ts).toLocaleString()}</div>
                    </div>`
                ).join('') || '<div style="color: #8b949e;">No market updates</div>';
                document.getElementById('marketUpdates').innerHTML = marketHtml;
                
                // Dashboard Feed
                const feedHtml = (data.dashboard || []).slice(0, 5).map(f => 
                    `<div class="feed-item">
                        <div class="feed-title">${f.title}</div>
                        <div class="feed-time">${f.type} • ${new Date(f.ts).toLocaleString()}</div>
                    </div>`
                ).join('') || '<div style="color: #8b949e;">No recent activity</div>';
                document.getElementById('dashboardFeed').innerHTML = feedHtml;
                
            } catch(e) {
                console.error(e);
            }
        }
        
        refresh();
        setInterval(refresh, 60000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/dashboard')
def dashboard_data():
    """Return dashboard data from Redis"""
    data = {
        "sentinel": {"alerts": 0, "high_score_tokens": 0},
        "risk": {"count": 0, "alerts": []},
        "market": {"count": 0, "updates": []},
        "content": {"pending_approvals": 0},
        "dashboard": []
    }
    
    try:
        # SENTINEL stats
        data["sentinel"]["alerts"] = int(r.get("sentinel:stats:alerts:today") or 0)
        data["sentinel"]["high_score_tokens"] = int(r.get("sentinel:stats:high_score:today") or 0)
        
        # Risk alerts
        risk_alerts = r.lrange("cfo:risk_alerts", 0, 9) or []
        data["risk"]["alerts"] = [json.loads(a) for a in risk_alerts]
        data["risk"]["count"] = len(risk_alerts)
        
        # Market updates
        market_updates = r.lrange("cfo:market_updates", 0, 9) or []
        data["market"]["updates"] = [json.loads(u) for u in market_updates]
        data["market"]["count"] = len(market_updates)
        
        # Content pending
        pending = r.keys("content:draft:*") or []
        data["content"]["pending_approvals"] = len(pending)
        
        # Dashboard feed
        feed = r.lrange("ceo:dashboard:feed", 0, 19) or []
        data["dashboard"] = [json.loads(f) for f in feed]
        
    except Exception as e:
        log.error(f"Failed to fetch dashboard data: {e}")
    
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
