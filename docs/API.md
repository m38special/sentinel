# Liquid Sound API Documentation

## Overview

Liquid Sound provides real-time token signals and market intelligence through a distributed agent system.

---

## Core Services

### SENTINEL - Token Detection

Real-time token monitoring via PumpPortal WebSocket.

```
WebSocket: wss://pumpportal.fun/api/tokens
```

**Event Types:**
- `tokenCreated` - New token deployed
- `trade` - Token traded
- `launch` - Token launched

### AXIOM - Quantitative Analysis

Token scoring and risk analysis.

**Endpoint:** `POST /api/v1/score`

```json
{
  "symbol": "TOKEN",
  "address": "...",
  "liquidity_usd": 50000,
  "holder_count": 250,
  "volume_24h": 100000
}
```

**Response:**
```json
{
  "score": 72.5,
  "signal_level": "HIGH",
  "components": {
    "liquidity": 60,
    "holder_distribution": 75,
    "social_velocity": 80,
    "momentum": 70,
    "security": 90,
    "volume": 60
  },
  "risk_factors": []
}
```

### NOVA - Social Intelligence

Trend detection and content generation.

**Endpoint:** `GET /api/v1/trends`

```json
{
  "trends": [
    {"topic": "iran", "velocity": 95},
    {"topic": "ai", "velocity": 88}
  ],
  "timestamp": "2026-03-02T00:00:00Z"
}
```

### CIPHER - Security

Contract analysis and threat detection.

**Endpoint:** `POST /api/v1/security/check`

```json
{
  "address": "..."
}
```

**Response:**
```json
{
  "is_safe": true,
  "threats": [],
  "honeypot_score": 0.05,
  "liquidity_locked": true
}
```

---

## Webhooks

Configure webhooks for real-time alerts:

```
POST /api/v1/webhooks
{
  "url": "https://your-server.com/webhook",
  "events": ["token_signal", "security_alert"],
  "secret": "whsec_..."
}
```

---

## Rate Limits

| Tier | Requests/day | Signals/day |
|------|-------------|-------------|
| Free | 100 | 5 |
| Starter | 1000 | 25 |
| Pro | 10000 | 100 |
| VIP | Unlimited | Unlimited |

---

## Authentication

All API requests require `Authorization` header:

```
Authorization: Bearer ls_<api_key>
```

---

## SDKs

### Python
```python
from liquid_sound import Sentinel, Axiom, Cipher

client = Sentinel(api_key="ls_...")
signals = client.get_signals()
```

### JavaScript
```javascript
const { Sentinel } = require('liquid-sound');
const client = new Sentinel({ apiKey: '...' });
const signals = await client.getSignals();
```

---

## Support

- Email: support@liquidsound.ai
- Telegram: @liquidSound
- Discord: discord.gg/liquidsound
