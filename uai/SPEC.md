# Universal Agent Interface (UAI) — Spec v0.2

> **Status:** Phase 6 complete ✅  
> **Authors:** Captain Yoruichi (schema + routing) + Captain Urahara (transport + context store)  
> **Repo:** https://github.com/m38special/uai

---

## Overview

UAI is the shared communication protocol for all LiQUiD SOUND AI agents. It defines how agents discover each other, send tasks, share context, and confirm delivery — without manual relay.

---

## Architecture

```
┌─────────────┐    token_signal      ┌─────────────┐
│   SENTINEL  │ ──────────────────▶│    AXIOM    │
└─────────────┘                      └─────────────┘
       │                                    │
       │security_alert                      │
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│   CIPHER    │◀─────UAI───────────│    NOVA     │
└─────────────┘                      └─────────────┘
       │                                    │
       │                        social_signal│
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│   YORUICHI  │◀─content_review────│    CEO      │
└─────────────┘    ceo_dashboard     └─────────────┘
```

---

## Message Schema

See `schema/message.json` for full JSON Schema definition.

**Envelope fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | ✅ | Unique message ID |
| `from` | string | ✅ | Sending agent |
| `to` | string | ✅ | Receiving agent or `broadcast` |
| `intent` | string | ✅ | `namespace.action` (e.g., `analyze.risk_score`) |
| `priority` | string | ✅ | `critical / high / medium / low` |
| `payload` | object | ✅ | Intent-specific data |
| `context_ref` | UUID/null | ❌ | Parent task reference |
| `reply_to` | UUID/null | ❌ | Message this responds to |
| `ts` | ISO 8601 | ✅ | Creation timestamp |
| `ttl` | integer | ❌ | Seconds before DLQ escalation (default: 300) |

---

## Intent Routing

| Prefix | Owner | Examples |
|--------|-------|---------|
| `analyze.*` | AXIOM | `analyze.market_signal`, `analyze.risk_score` |
| `security.*` | CIPHER | `security.audit`, `security.threat_flag` |
| `social.*` | NOVA | `social.trend_report`, `social.sentiment` |
| `signal.*` | SENTINEL | `signal.new_token`, `signal.high_score` |
| `approve.*` | YORUICHI | `approve.content_draft`, `approve.trade_signal` |
| `report.*` | MAXWELL | `report.executive_summary`, `report.daily_brief` |
| `broadcast.*` | SYSTEM | `broadcast.approve`, `broadcast.reject`, `broadcast.emergency` |

---

## Redis Event Channels

| Channel | Publisher | Subscribers | Status |
|---------|-----------|-------------|--------|
| `uai:events:token_signal` | SENTINEL | AXIOM, NOVA, YORUICHI | ✅ Live |
| `uai:events:security_alert` | SENTINEL | CIPHER, YORUICHI, URAHARA | ✅ Live |
| `uai:events:social_signal` | NOVA | SENTINEL, AXIOM | ✅ Live |
| `uai:events:content_review` | SYSTEM | YORUICHI | ✅ Live |
| `uai:events:market_update` | YORUICHI | ALL | ✅ Live |
| `uai:events:ceo_dashboard` | YORUICHI | CEO | ✅ Live |
| `uai:broadcast` | ANY | ALL | ✅ Live |

---

## ACK Protocol

Every message triggers an ACK lifecycle on Redis:

```
uai:ack:{message_id}
  queued → in_progress → done | failed | blocked
```

- If no terminal state within `ttl` seconds → message moves to `uai:dlq`
- YORUICHI monitors DLQ and escalates or retries

---

## Agent Registration

Each agent declares capabilities on startup:

```yaml
agent: axiom
handles:
  - analyze.*
  - risk.*
  - backtest.*
broadcast_subscriptions:
  - uai:events:token_signal
  - uai:events:market_update
```

Gateway reads registration and updates routing table dynamically. No hardcoded routing.

---

## Phase Roadmap

| Phase | Owner | Status |
|-------|-------|--------|
| Phase 1 — Transport + Schema | YORUICHI + URAHARA | ✅ Done |
| Phase 2 — Gateway + Registration | URAHARA | ✅ Done |
| Phase 3 — SENTINEL → AXIOM Pilot | URAHARA | ✅ Done |
| Phase 4 — UAI Expansion (CIPHER + NOVA) | URAHARA | ✅ Done |
| Phase 5 — Content Approval Pipeline | URAHARA | ✅ LIVE |
| Phase 6 — CFO Command Layer | YORUICHI | ✅ Done |

---

## Active Monetization Projects (Priority)

### CIPHER — Security Services
- **Phase 1:** Smart Contract Audits ($2.5K–$15K)
- **Phase 2:** Threat Monitoring (Watch $500/mo → Fortress $4K/mo)
- **Phase 3:** Automated Vulnerability Scanning
- **Next:** Landing page + monitoring dashboard

### AXIOM — Quant Data Products
- **Phase 1:** Analytics API (Dev $99 → Pro $399 → Enterprise)
- **Phase 2:** Trading Signals (Scaler $149 → Institutional $2,499)
- **Phase 3:** Market Intelligence Reports ($99–$599/mo)
- **Next:** API deployment + client onboarding

### Kurotsuchi — Research Services
- **Phase 1:** Market Intelligence Reports ($500–$3K+)
- **Phase 2:** Trend Forecasting Retainers ($2.5K–$20K)
- **Phase 3:** Dataset/API Access ($200–$2.5K/mo)
- **Next:** MVP report + buyer validation
