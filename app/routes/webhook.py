"""
Webhook Route — Gmail Push Notifications (via Google Pub/Sub)
POST /webhook/gmail  → receives Pub/Sub push messages when new Gmail messages arrive

How it works:
  1. Gmail watches the inbox via Pub/Sub (set up via /auth/watch)
  2. When a new email arrives, Google pushes a notification here
  3. We decode the Pub/Sub message → get email ID → fetch & process it
"""

import base64
import json
import logging
import hmac
import hashlib

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from app.services.gmail_service import get_email_by_id, get_email_thread, mark_as_read
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_new_email(history_id: str, email_address: str):
    """
    Background task: fetch and process the new email via the AI Orchestrator.
    """
    logger.info(f"Processing new email notification. History ID: {history_id}, User: {email_address}")

    from app.services.thread_analyzer import process_unread_emails_pipeline
    try:
        result = process_unread_emails_pipeline()
        logger.info(f"Pipeline executed via Webhook: {result}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")


@router.post("/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive Gmail Pub/Sub push notifications.
    Google sends a JSON body with a base64-encoded Pub/Sub message.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Pub/Sub format: { "message": { "data": "<base64>", "messageId": "..." }, "subscription": "..." }
    pubsub_message = body.get("message", {})
    if not pubsub_message:
        raise HTTPException(status_code=400, detail="No Pub/Sub message found")

    # Decode the base64-encoded data payload
    try:
        data_encoded = pubsub_message.get("data", "")
        data_decoded = base64.urlsafe_b64decode(data_encoded + "==").decode("utf-8")
        notification = json.loads(data_decoded)
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub message: {e}")
        raise HTTPException(status_code=400, detail="Failed to decode message data")

    history_id = notification.get("historyId", "")
    email_address = notification.get("emailAddress", "")

    logger.info(f"Gmail notification received — historyId: {history_id}, email: {email_address}")

    # Process in background so we return 200 immediately to Pub/Sub
    background_tasks.add_task(process_new_email, history_id, email_address)

    return {"status": "received"}
