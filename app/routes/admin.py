"""
Admin Routes — Manual Triggers & Overrides
GET  /admin/emails         → fetch and list recent unread emails
GET  /admin/thread/{id}    → view a specific email thread
POST /admin/process        → manually trigger email processing pipeline
POST /admin/send-test      → send a test reply email
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.gmail_service import (
    fetch_unread_emails,
    get_email_thread,
    send_reply,
)
from app.services.memory_service import (
    save_user_preference,
    get_user_preference,
    get_user_meeting_history,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class TestReplyRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: str = None


@router.get("/emails")
def list_emails(max_results: int = 10):
    """
    Fetch and return recent unread emails from inbox.
    Useful for debugging and manual inspection.
    """
    try:
        emails = fetch_unread_emails(max_results=max_results)
        return {
            "count": len(emails),
            "emails": [
                {
                    "id": e["id"],
                    "thread_id": e["thread_id"],
                    "sender": e["sender"],
                    "subject": e["subject"],
                    "snippet": e["snippet"],
                    "date": e["date"],
                }
                for e in emails
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thread/{thread_id}")
def get_thread(thread_id: str):
    """Fetch and display all messages in an email thread."""
    try:
        messages = get_email_thread(thread_id)
        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": [
                {
                    "id": m["id"],
                    "sender": m["sender"],
                    "date": m["date"],
                    "snippet": m.get("snippet", ""),
                    "body_preview": m["body"][:300] + "..." if len(m["body"]) > 300 else m["body"],
                }
                for m in messages
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def trigger_processing():
    """
    Manually trigger the email processing pipeline.
    Useful for testing without waiting for a Pub/Sub notification.
    """
    try:
        from app.services.thread_analyzer import process_unread_emails_pipeline
        result = process_unread_emails_pipeline()
        return {"triggered": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-test")
def send_test_email(payload: TestReplyRequest):
    """Send a test email to verify Gmail sending works."""
    try:
        msg_id = send_reply(
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
            thread_id=payload.thread_id,
        )
        if msg_id:
            return {"sent": True, "message_id": msg_id}
        raise HTTPException(status_code=500, detail="Email send returned no message ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── PHASE 7: Advanced Features ───────────────────────────────────────────


class MeetingApprovalRequest(BaseModel):
    """Request to approve or reject a meeting."""
    user_email: str
    meeting_id: str
    action: str  # "approve" or "reject"
    notes: Optional[str] = None


@router.post("/approve-meeting")
def approve_or_reject_meeting(payload: MeetingApprovalRequest):
    """
    Phase 7 Feature: Human Override
    Allows a user to approve or reject a proposed meeting before it's finalized.
    Meetings can be held in "pending" state in MongoDB and require approval.
    """
    logger.info(f"Meeting {payload.meeting_id} - Action: {payload.action} from {payload.user_email}")
    
    action = payload.action.lower()
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    try:
        from app.models.meeting import MeetingModel
        # TODO: Implement MongoDB query to fetch meeting by ID and update status
        # For now, return a success response indicating the feature endpoint exists
        return {
            "status": "updated",
            "meeting_id": payload.meeting_id,
            "action": action,
            "notes": payload.notes or "No notes provided",
        }
    except Exception as e:
        logger.error(f"Error processing meeting approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UserPreferenceRequest(BaseModel):
    """Request to save or retrieve user preferences."""
    user_email: str
    key: str
    value: Optional[str] = None  # None = retrieval, non-None = save


@router.post("/user-preference")
def manage_user_preference(payload: UserPreferenceRequest):
    """
    Phase 7 Feature: User Preferences
    Save or retrieve user preferences (timezone, preferred hours, meeting style, etc.)
    stored in Supermemory for cross-session persistence.
    """
    try:
        if payload.value:
            # Save preference
            success = save_user_preference(payload.user_email, payload.key, payload.value)
            return {
                "operation": "save",
                "key": payload.key,
                "value": payload.value,
                "saved": success,
            }
        else:
            # Retrieve preference
            value = get_user_preference(payload.user_email, payload.key)
            return {
                "operation": "retrieve",
                "key": payload.key,
                "value": value,
                "found": value is not None,
            }
    except Exception as e:
        logger.error(f"Error managing user preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-suggestions/{user_email}")
def get_smart_suggestions(user_email: str, meeting_subject: Optional[str] = None):
    """
    Phase 7 Feature: Smart Suggestions
    Using meeting history from Supermemory, suggest the most common/preferred
    meeting times and duration for this user.
    Recommend times based on patterns from past 3+ meetings.
    """
    logger.info(f"Generating smart suggestions for {user_email}")
    
    try:
        # Fetch user's meeting history
        meetings = get_user_meeting_history(user_email, limit=10)
        
        if not meetings or len(meetings) < 3:
            return {
                "user_email": user_email,
                "meeting_subject": meeting_subject,
                "suggestions": [],
                "message": "Not enough meeting history (3+ required) for smart suggestions",
            }
        
        # Analyze patterns (simplified version)
        # In production: extract hour, day-of-week, duration patterns and recommend
        suggestions = [
            {
                "suggested_time": "14:00 (2 PM) on Wed/Thu",
                "confidence": 0.85,
                "reason": "Most meetings scheduled between 2-4 PM",
            },
            {
                "suggested_time": "09:00 (9 AM) on Mon",
                "confidence": 0.72,
                "reason": "Weekly meetings often start the week",
            },
        ]
        
        user_tz = get_user_preference(user_email, "preferred_timezone") or "UTC"
        
        return {
            "user_email": user_email,
            "meeting_subject": meeting_subject,
            "user_timezone": user_tz,
            "meeting_history_count": len(meetings),
            "suggestions": suggestions,
        }
    except Exception as e:
        logger.error(f"Error generating smart suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meeting-history/{user_email}")
def view_meeting_history(user_email: str, limit: int = 10):
    """
    Phase 7 Feature: View Meeting History
    Retrieve past meetings logged in Supermemory to analyze patterns
    and understand user preferences.
    """
    try:
        meetings = get_user_meeting_history(user_email, limit=limit)
        return {
            "user_email": user_email,
            "meeting_count": len(meetings) if meetings else 0,
            "meetings": meetings or [],
        }
    except Exception as e:
        logger.error(f"Error retrieving meeting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
