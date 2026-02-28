"""
tasks/__init__.py — Celery App Init
SENTINEL Phase 2 | LiQUiD SOUND

Broker: Redis (Railway or local)
Queues:
  - sentinel  : token scoring pipeline
  - nova      : social scraping tasks
  - alerts    : notification delivery
"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Celery App
# ─────────────────────────────────────────────
app = Celery("sentinel")

app.conf.update(
    broker_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Queue routing
    task_queues={
        "sentinel": {"exchange": "sentinel", "routing_key": "sentinel"},
        "nova":     {"exchange": "nova",     "routing_key": "nova"},
        "alerts":   {"exchange": "alerts",   "routing_key": "alerts"},
    },
    task_default_queue="sentinel",
    task_routes={
        "tasks.score_token.*":  {"queue": "sentinel"},
        "tasks.risk_filter.*":  {"queue": "sentinel"},
        "tasks.store_token.*":  {"queue": "sentinel"},
        "tasks.alert_router.*": {"queue": "alerts"},
        "tasks.nova_scan.*":    {"queue": "nova"},
    },

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "nova-full-scan-every-15-min": {
            "task": "tasks.nova_scan.full_social_scan",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "nova"},
        },
        "sentinel-health-check-every-minute": {
            "task": "tasks.score_token.health_check",
            "schedule": 60.0,
            "options": {"queue": "sentinel"},
        },
    },
)

# Auto-discover tasks in this package
app.autodiscover_tasks(["tasks"])
