# AXIOM Developer Documentation

## Free Tier API

Welcome to the AXIOM Analytics API! This documentation covers the free tier endpoints available to all registered developers.

---

## Quick Start

### 1. Get Your API Key

```bash
curl -X POST https://api.axiom.trade/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "name": "Your Name"}'
```

Response:
```json
{
  "success": true,
  "api_key": "ax_F_a1b2c3d4e5f6...",
  "tier": "free",
  "limits": {"requests_per_day": 100, "requests_per_second": 1}
}
```

### 2. Make Your First Request

```bash
curl https://api.axiom.trade/v1/whale-tracking \
  -H "X-API-Key: ax_F_your_api_key_here"
```

---

## API Endpoints

### Whale Tracking
**GET** `/v1/whale-tracking`

Get recent whale transaction activity.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| chain | string | all | `solana`, `ethereum`, `arbitrum`, `base`, `all` |
| min_volume_usd | number | 10000 | Minimum transaction volume |
| timeframe | string | 24h | `1h`, `6h`, `24h`, `7d` |
| limit | integer | 20 | Max 20 (free tier) |

**Example Response:**
```json
{
  "data": [
    {
      "tx_hash": "tx_abc123...",
      "wallet_address": "ABCdef...",
      "chain": "solana",
      "timestamp": "2026-02-28T20:00:00Z",
      "volume_usd": 50000,
      "tokens": ["SOL", "USDC"],
      "action": "buy",
      "profit_loss_estimated": 2500
    }
  ],
  "meta": {
    "total": 1,
    "tier": "free",
    "note": "Free tier: data delayed 1 hour"
  }
}
```

---

### Yield Signals
**GET** `/v1/yield-signals`

Get current DeFi yield opportunities with risk assessments.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| chain | string | all | Filter by blockchain |
| min_apy | number | 0 | Minimum APY percentage |
| risk_level | string | all | `low`, `medium`, `high`, `all` |
| limit | integer | 10 | Max 10 (free tier) |

**Example Response:**
```json
{
  "data": [
    {
      "pool_id": "pool_1",
      "protocol": "Raydium",
      "chain": "solana",
      "tokens": "SOL-USDC",
      "apy": 8.5,
      "apy_30d_avg": 7.2,
      "tvl_usd": 100000000,
      "risk_score": 25,
      "risk_factors": ["smart_contract"],
      "impermanent_loss_risk": "low"
    }
  ],
  "generated_at": "2026-02-28T21:00:00Z",
  "tier": "free"
}
```

---

### Market Sentiment
**GET** `/v1/sentiment`

Get aggregated market sentiment data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| asset | string | BTC | Asset symbol (BTC, SOL, ETH, etc.) |
| timeframe | string | 24h | Free tier restricted to 24h |

**Example Response:**
```json
{
  "asset": "SOL",
  "sentiment": {
    "score": 45,
    "label": "neutral",
    "confidence": 0.72
  },
  "sources": [
    {"source": "twitter", "score": 40, "volume": 15000, "trending": true},
    {"source": "reddit", "score": 55, "volume": 8000, "trending": false}
  ],
  "key_themes": ["yield_farming", "defi"],
  "tier": "free"
}
```

---

## Rate Limits

| Tier | Requests/Day | Requests/Second |
|------|---------------|-----------------|
| **Free** | 100 | 1 |
| Pro | 10,000 | 10 |
| Enterprise | Unlimited | Custom |

When rate limited, you'll receive:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded: daily_limit_exceeded"
  },
  "meta": {"retry_after": 3600}
}
```

---

## Check Your Usage

```bash
curl https://api.axiom.trade/v1/auth/usage \
  -H "X-API-Key: ax_F_your_key"
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `MISSING_API_KEY` | No API key provided |
| `INVALID_API_KEY` | API key not recognized |
| `RATE_LIMITED` | Daily or per-second limit exceeded |
| `INVALID_REQUEST` | Malformed request parameters |
| `EMAIL_EXISTS` | Email already registered |

---

## Upgrade to Pro

Need more requests or real-time data? Contact us to upgrade to Pro tier:

- **10,000 requests/day** (vs 100)
- **Real-time data** (vs 1h delayed)
- **All endpoints** including wallet profiles & webhooks
- **Priority support**

Email: `api@axiom.trade`

---

## Support

- **Email:** support@axiom.trade
- **Status:** [status.axiom.trade](https://status.axiom.trade)
- **Documentation:** [docs.axiom.trade](https://docs.axiom.trade)

---

*Last updated: 2026-02-28*
