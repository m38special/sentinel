# UAI & SENTINEL System Blueprint

> Last updated: March 2, 2026
> Version: 2.1

---

## Integrated Libraries (v2.1)

| Library | Purpose | Status |
|---------|---------|--------|
| **ccxt** | Multi-exchange API (100+ exchanges) | INTEGRATED |
| **ChatTTS** | Voice alerts (TTS) | INTEGRATED |
| **pumpportal** | Pump.fun token detection | ACTIVE |

---

## Overview

The **Universal Agent Interface (UAI)** is a message bus and event routing layer that connects autonomous agents (SENTINEL, NOVA, AXIOM, CIPHER, Yoruichi) with infrastructure services (Redis, TimescaleDB, Celery, Slack).

**SENTINEL** is the real-time token detection system that listens to PumpPortal WebSockets, scores tokens, and routes alerts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SENTINEL PHASE 5                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  PumpPortal │───▶│ sentinel_ph2 │───▶│  Celery Pipeline      │  │
│  │  WebSocket  │    │  Listener    │    │  (score→store→alert) │  │
│  └──────────────┘    └──────────────┘    └──────────┬────────────┘  │
│                                                    │               │
│                         ┌──────────────────────────▼───────────┐   │
│                         │         Redis (UAI Event Bus)         │   │
│                         │  - uai:events:token_signal           │   │
│                         │  - uai:events:security_alert         │   │
│                         │  - uai:events:social_signal         │   │
│                         │  - uai:events:market_update         │   │
│                         │  - uai:events:ceo_dashboard          │   │
│                         └─────────────────────┬─────────────────┘   │
│                                               │                    │
│         ┌──────────────────────────────────────┼────────────────┐    │
│         │              AGENTS                 │                │    │
│         ├─────────────┬─────────────┬──────────┼────────┬───────┤    │
│         ▼             ▼             ▼         ▼        ▼       ▼    │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐ ┌──────┐ ┌────┐  │
│    │  AXIOM  │  │  CIPHER │  │  NOVA  │  │YORUICHI│ │ URAH │ │    │  │
│    │ (Quant) │  │ (Sec)   │  │(Social)│  │ (CFO) │ │(CTO) │ │    │  │
│    └─────────┘  └─────────┘  └─────────┘  └───────┘ └──────┘ └────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    TimescaleDB (Storage)                       │  │
│  │  - token_events (mint, score, volume, holders, market_cap)    │  │
│  │  - alerts (mint, alert_type, channel, delivered_at)          │  │
│  │  - nova_scans (platform, scan_type, results_count)            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. SENTINEL (Token Detection)

**File:** `sentinel/sentinel_ph2.py`

- Connects to PumpPortal WebSocket (`wss://pumpportal.fun/api/tokens`)
- Listens for new token creations
- Emits `token_new` events to Celery queue

**Celery Tasks:**
| Task | Queue | Description |
|------|-------|-------------|
| `score_token` | sentinel | Scores token (risk, social, momentum) |
| `store_token` | sentinel | Persists to TimescaleDB |
| `alert_router` | alerts | Routes to Slack/Telegram |
| `risk_filter` | sentinel | Checks rug pull indicators |

### 2. UAI (Event Bus)

**Redis Channels:**
- `uai:events:token_signal` — New token with score
- `uai:events:security_alert` — Security threat detected
- `uai:events:social_signal` — NOVA social velocity alert
- `uai:events:market_update` — Market briefing
- `uai:events:ceo_dashboard` — CEO dashboard feed

**Intent Registry (v0.2):**
- `token.signal` — Token detected, scored
- `security.threat` — Security alert
- `social.velocity` — High social velocity
- `report.executive_summary` — Daily summary
- `report.content_draft` — Content for approval
- `broadcast.approve` / `broadcast.reject` — Content decision

### 3. Agents

| Agent | Role | Subscriptions |
|-------|------|---------------|
| **AXIOM** | Quantitative Analyst | `token_signal` → scores feedback |
| **CIPHER** | Cybersecurity | `security_alert` → threat analysis |
| **NOVA** | Social Media | `social_signal` → content generation |
| **Yoruichi** | CFO | `ceo_dashboard`, `market_update` |
| **Urahara** | CTO | Infrastructure oversight |

### 4. Daily Reports (Celery Beat)

| Time (CT) | Task | Output |
|-----------|------|--------|
| 7:00 AM | `generate_executive_summary` | #idea-ocean |
| 8:00 AM | `generate_daily_newsletter` | #idea-ocean (Yoruichi + NOVA) |
| Every 15 min | `nova_scan.full_social_scan` | DB + social signals |
| Every 1 min | `score_token.health_check` | System health |

---

## Phase History

### Phase 1 — MVP
- Pump.fun scraper (5-min polling)
- SQLite storage
- Basic Telegram/Slack alerts

### Phase 2 — Infrastructure
- Docker containerization
- Redis caching
- Celery task pipeline
- TimescaleDB for time-series

### Phase 3 — Wave 3 Integration
- WebSocket listener (sentinel_ph2.py)
- Score → Store → Alert pipeline
- Bug fixes

### Phase 4 — UAI Expansion
- AXIOM feedback loop
- CIPHER security alerts
- NOVA social signals
- Intent registry v0.2

### Phase 5 — Content Approval (Current)
- `report.content_draft` intent
- Yoruichi approval gate
- `broadcast.approve/reject`
- NOVA auto-post on ACK

---

## Configuration

### Environment Variables

```
# Redis
REDIS_URL=redis://redis:6379/0

# TimescaleDB
DATABASE_URL=postgresql://sentinel:changeme@timescaledb:5432/sentinel

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0AHE2LQFRC

# PumpPortal
PUMPPORTAL_WS_URL=wss://pumpportal.fun/api/tokens

# Groq (AI)
GROQ_API_KEY=gsk_...
```

### Docker Services

```yaml
services:
  sentinel-listener:  # WebSocket listener
  celery-worker:      # Task processor
  celery-beat:       # Scheduler
  redis:             # Broker + cache
  timescale:         # Time-series DB
```

---

## Future Roadmap (v2.1+)

### Week 1-2 Priorities
- [x] v2.1 deploy + ccxt integration
- [x] Daily briefing pipeline live
- [ ] AXIOM Scoring v2.0 (in progress)
- [ ] CIPHER Forta integration (in progress)

### Week 3-4
- [ ] CIPHER Forta deployment
- [ ] Horizontal scaling (Celery workers)
- [ ] Multi-region deployment planning

### Ongoing
- [ ] NOVA content ops (@888 3x/week)
- [ ] @liquidinsights launch
- [ ] Yoruichi revenue diversification
- [ ] AXIOM backtesting pipeline (vectorbt)
- [ ] Phase 7 ML model training

---

*Blueprint maintained by Captain Urahara (CTO)*
