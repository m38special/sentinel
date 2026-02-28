"""
tasks/content_approval.py — Content Approval Pipeline
SENTINEL Phase 5 | LiQUiD SOUND

Flow:
1. Content draft created → report.content_draft intent
2. Sent to Yoruichi for approval
3. Yoruichi approves/rejects → broadcast.approve/reject
4. On ACK → NOVA auto-posts to socials
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import redis as redis_lib
from tasks import app

log = logging.get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APPROVAL_TTL = 3600  # 1 hour for approval timeout


def get_redis():
    return redis_lib.from_url(REDIS_URL, decode_responses=True)


@app.task(
    name="tasks.content_approval.create_draft",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="sentinel",
)
def create_content_draft(
    self,
    content_type: str,
    title: str,
    body: str,
    token_symbol: str = None,
    token_mint: str = None,
    metadata: dict = None
):
    """
    Create a content draft for Yoruichi approval.
    Publishes to uai:events:content_review channel.
    """
    r = get_redis()
    
    # Create draft ID
    draft_id = f"draft-{datetime.now(timezone.utc).timestamp()}"
    
    draft = {
        "id": draft_id,
        "type": content_type,
        "title": title,
        "body": body,
        "token_symbol": token_symbol,
        "token_mint": token_mint,
        "metadata": metadata or {},
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "system",
    }
    
    # Store in Redis with TTL
    r.setex(f"content:draft:{draft_id}", APPROVAL_TTL, json.dumps(draft))
    
    # Publish to Yoruichi for approval
    message = {
        "id": draft_id,
        "from": "system",
        "to": "yoruichi",
        "intent": "report.content_draft",
        "priority": "high",
        "payload": draft,
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": APPROVAL_TTL,
    }
    
    r.publish("uai:events:content_review", json.dumps(message))
    
    log.info(
        "content_draft_created",
        draft_id=draft_id,
        type=content_type,
        token_symbol=token_symbol,
    )
    
    return {"status": "draft_created", "draft_id": draft_id}


@app.task(
    name="tasks.content_approval.approve_content",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="sentinel",
)
def approve_content(self, draft_id: str, approver: str = "yoruichi", notes: str = ""):
    """
    Approve content draft. Triggers broadcast.approve and NOVA auto-post.
    """
    r = get_redis()
    
    # Get draft
    draft_data = r.get(f"content:draft:{draft_id}")
    if not draft_data:
        log.error("draft_not_found", draft_id=draft_id)
        return {"status": "error", "reason": "draft_not_found"}
    
    draft = json.loads(draft_data)
    draft["status"] = "approved"
    draft["approved_by"] = approver
    draft["approved_at"] = datetime.now(timezone.utc).isoformat()
    draft["notes"] = notes
    
    # Update in Redis
    r.setex(f"content:draft:{draft_id}", APPROVAL_TTL, json.dumps(draft))
    
    # Broadcast approval
    broadcast_msg = {
        "id": f"approval-{datetime.now(timezone.utc).timestamp()}",
        "from": approver,
        "to": "broadcast",
        "intent": "broadcast.approve",
        "priority": "medium",
        "payload": {
            "draft_id": draft_id,
            "content_type": draft.get("type"),
            "title": draft.get("title"),
            "token_symbol": draft.get("token_symbol"),
            "approved_by": approver,
            "notes": notes,
        },
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 300,
    }
    
    r.publish("uai:broadcast", json.dumps(broadcast_msg))
    
    # Trigger NOVA auto-post (async)
    from tasks.nova_scan import post_approved_content
    post_approved_content.delay(draft)
    
    log.info(
        "content_approved",
        draft_id=draft_id,
        approver=approver,
    )
    
    return {"status": "approved", "draft_id": draft_id}


@app.task(
    name="tasks.content_approval.reject_content",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="sentinel",
)
def reject_content(self, draft_id: str, approver: str = "yoruichi", reason: str = ""):
    """
    Reject content draft. Triggers broadcast.reject.
    """
    r = get_redis()
    
    # Get draft
    draft_data = r.get(f"content:draft:{draft_id}")
    if not draft_data:
        log.error("draft_not_found", draft_id=draft_id)
        return {"status": "error", "reason": "draft_not_found"}
    
    draft = json.loads(draft_data)
    draft["status"] = "rejected"
    draft["rejected_by"] = approver
    draft["rejected_at"] = datetime.now(timezone.utc).isoformat()
    draft["rejection_reason"] = reason
    
    # Update in Redis
    r.setex(f"content:draft:{draft_id}", APPROVAL_TTL, json.dumps(draft))
    
    # Broadcast rejection
    broadcast_msg = {
        "id": f"rejection-{datetime.now(timezone.utc).timestamp()}",
        "from": approver,
        "to": "broadcast",
        "intent": "broadcast.reject",
        "priority": "low",
        "payload": {
            "draft_id": draft_id,
            "content_type": draft.get("type"),
            "title": draft.get("title"),
            "rejected_by": approver,
            "reason": reason,
        },
        "ts": datetime.now(timezone.utc).isoformat(),
        "ttl": 300,
    }
    
    r.publish("uai:broadcast", json.dumps(broadcast_msg))
    
    log.info(
        "content_rejected",
        draft_id=draft_id,
        approver=approver,
        reason=reason,
    )
    
    return {"status": "rejected", "draft_id": draft_id}


@app.task(
    name="tasks.content_approval.get_draft_status",
    bind=True,
    max_retries=1,
    queue="sentinel",
)
def get_draft_status(self, draft_id: str):
    """Get current status of a content draft."""
    r = get_redis()
    
    draft_data = r.get(f"content:draft:{draft_id}")
    if not draft_data:
        return {"status": "not_found", "draft_id": draft_id}
    
    draft = json.loads(draft_data)
    return {"status": draft.get("status", "unknown"), "draft": draft}
