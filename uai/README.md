# Universal Agent Interface (UAI)

## Overview
A shared protocol for all LiQUiD SOUND AI agents to communicate, delegate tasks, and collaborate natively.

## Architecture
```
┌─────────────┐    Redis pub/sub     ┌─────────────┐
│   SENTINEL  │ ──token_signal────▶│    AXIOM    │
└─────────────┘                      └─────────────┘
       │                                    │
       │security_alert                      │
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│   CIPHER    │◀──────UAI──────────│    NOVA     │
└─────────────┘                      └─────────────┘
       │                                    │
       │                       social_signal│
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│   YORUICHI  │◀──content_review────│    CEO      │
└─────────────┘     ceo_dashboard    └─────────────┘
```

## Transport Layer
- **Context Store:** Redis
- **Transport:** Redis pub/sub + OpenClaw sessions

## Message Schema
```python
{
    "id": "uuid",
    "from": "agent_id",
    "to": "agent_id|broadcast",
    "intent": "namespace.action",
    "priority": "critical|high|medium|low",
    "payload": {...},
    "context_ref": "uuid|null",
    "reply_to": "uuid|null",
    "ts": "ISO 8601",
    "ttl": 300
}
```

## ACK Protocol
- `queued` - task received
- `in_progress` - task being worked
- `done` - task completed
- `blocked` - task stuck
- `failed` - task failed

## Intent Routing

| Prefix | Owner | Examples |
|--------|-------|---------|
| `analyze.*` | AXIOM | market_signal, risk_score |
| `security.*` | CIPHER | threat_flag, audit |
| `social.*` | NOVA | sentiment, trend_report |
| `signal.*` | SENTINEL | new_token, high_score |
| `approve.*` | YORUICHI | content_draft, trade_signal |
| `report.*` | MAXWELL | executive_summary, daily_brief |
| `broadcast.*` | SYSTEM | approve, reject, emergency |

## UAI Event Channels

| Channel | Publisher | Subscribers | Status |
|---------|-----------|-------------|--------|
| `uai:events:token_signal` | SENTINEL | AXIOM, NOVA, YORUICHI | ✅ Live |
| `uai:events:security_alert` | SENTINEL | CIPHER, YORUICHI, URAHARA | ✅ Live |
| `uai:events:social_signal` | NOVA | SENTINEL, AXIOM | ✅ Live |
| `uai:events:content_review` | SYSTEM | YORUICHI | ✅ Live |
| `uai:events:market_update` | YORUICHI | ALL | ✅ Live |
| `uai:events:ceo_dashboard` | YORUICHI | CEO | ✅ Live |
| `uai:broadcast` | ANY | ALL | ✅ Live |

## Phase Status

### Phase 1 — Transport + Schema
- [x] Transport layer (Redis) ✅
- [x] Message schema ✅
- [x] Routing logic ✅

### Phase 2 — Gateway + Registration
- [x] Agent registration ✅
- [x] Dead letter queue ✅
- [x] ACK protocol ✅
- [x] Gateway integration ✅

### Phase 3 — SENTINEL → AXIOM Pilot
- [x] SENTINEL publishes token signals ✅
- [x] AXIOM responds via UAI ✅
- [x] Feedback loop ✅

### Phase 4 — UAI Expansion
- [x] CIPHER security alerts ✅
- [x] NOVA social signals ✅
- [x] Intent registry v0.2 ✅

### Phase 5 — Content Approval Pipeline
- [x] report.content_draft intent ✅
- [x] YORUICHI approval gate ✅
- [x] broadcast.approve/reject ✅
- [x] NOVA auto-post on ACK ✅

### Phase 6 — CFO Command Layer
- [x] report.executive_summary auto-generation ✅
- [x] market_update → daily briefing ✅
- [x] Budget/risk alerts via UAI ✅
- [x] CEO dashboard feed ✅

---

## Active Monetization Projects

| Project | Lead | Status |
|---------|------|--------|
| Security Services (Audits + Monitoring) | CIPHER | Phase 1: Landing page + dashboard |
| Quant Data Products (API + Signals) | AXIOM | Phase 1: API deployment |
| Research Services (Reports + Forecasting) | Kurotsuchi | Phase 1: MVP report |

## Usage
```python
from transport import UAITransport, create_message

transport = UAITransport()

# Publish
msg = create_message('sentinel', 'axiom', 'analyze.market_signal', {'symbol': 'PEPE'}, priority='high')
transport.publish(msg)

# Store context
transport.set_context('market:btc', {'price': 65000})
```
