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

from app.services.gmail_service import (
    fetch_unread_emails,
    get_email_thread,
    send_reply,
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
