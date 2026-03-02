# SENTINEL — Project State

> Last updated: 2026-03-01

---

## Phase 1: MVP WebSocket Listener
**Status: ✅ DONE**

- Real-time WebSocket connection to PumpPortal
- Token launch event listener
- Basic filtering + console output
- Foundation validated

---

## Phase 2: Production Infrastructure
**Status: ✅ COMPLETE (pending CIPHER v2 audit sign-off)**

### Wave 1 — Infrastructure Layer ✅
| Task | Owner | Status |
|------|-------|--------|
| `Dockerfile` | infra | ✅ DONE |
| `docker-compose.yml` (Redis + Celery + TimescaleDB) | infra | ✅ DONE |

### Wave 2 — Processing Layer ✅
| Task | Owner | Status |
|------|-------|--------|
| Celery tasks (token scoring, alert routing) | backend | ✅ DONE |
| TimescaleDB schema (hypertables, indexes) | backend | ✅ DONE |

### Wave 3 — Integration Layer ✅
| Task | Owner | Status |
|------|-------|--------|
| `sentinel_ph2.py` — PumpPortal WS → `score_and_route.delay()` | backend | ✅ DONE |
| Alert routing → Slack / Discord / Telegram | backend | ✅ DONE (Slack live, Discord/TG stubbed) |
| NOVA social score injection (Redis cache lookup) | backend | ✅ DONE |
| `.env.example` for Railway deploy | infra | ✅ DONE |

### Bug Fixes Applied
| Bug | File | Fix |
|-----|------|-----|
| `check_rug_indicators.run()` → plain function call | tasks/score_token.py | ✅ Fixed |
| `docker-compose.yml` referenced `sentinel.py` (not ph2) | docker-compose.yml | ✅ Fixed |
| `Dockerfile` CMD referenced `sentinel.py` | Dockerfile | ✅ Fixed |

---

## Infrastructure Targets
- **Redis:** interchange.proxy.rlwy.net:56657 (Railway)
- **Celery broker:** Redis (same instance)
- **TimescaleDB:** Docker (local dev) → Railway (prod)
- **Deployment:** Docker Compose → Railway

---

## Key Files
| File | Purpose |
|------|---------|
| `sentinel_ph2.py` | Wave 3 listener — WS → Celery dispatch |
| `tasks/__init__.py` | Celery app init + queue routing |
| `tasks/score_token.py` | Scoring pipeline (score_and_route task) |
| `tasks/risk_filter.py` | Rug indicator checks |
| `tasks/store_token.py` | TimescaleDB persistence |
| `tasks/alert_router.py` | Slack/Discord/Telegram routing |
| `tasks/nova_scan.py` | NOVA social scan (Celery Beat, every 15min) |
| `docker-compose.yml` | Full stack (sentinel + celery + redis + timescaledb) |
| `.env.example` | Env var template for Railway deploy |

---

## Next Steps
1. ✅ CIPHER v2 audit (in progress — subagent running)
2. Patch any new CIPHER findings
3. Push Phase 2 stack to https://github.com/m38special/sentinel
4. Deploy to Railway (replace MVP with Ph2 stack)
5. E2E smoke test: confirm tokens flow from WS → Celery → Slack
