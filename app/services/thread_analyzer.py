"""
Thread Analyzer / Orchestrator — Phase 6
Pulls everything together: Fetches emails -> LLM Intent -> Scheduler -> Replies
"""

import logging
from app.services.gmail_service import fetch_unread_emails, mark_as_read, send_reply
from app.services.llm_service import detect_intent, extract_time_slots, generate_clarification
from app.services.scheduler import schedule_meeting

logger = logging.getLogger(__name__)


def process_unread_emails_pipeline():
    """
    The main orchestration loop triggered by the Webhook or Admin endpoint.
    It reads the inbox, determines AI actions, schedules events if needed,
    and sends automatic replies before archiving the email state.
    """
    logger.info("Starting email processing pipeline...")
    
    # 1. Fetch unread emails
    emails = fetch_unread_emails(max_results=5)
    if not emails:
        logger.info("No unread emails to process.")
        return {"status": "no_emails"}

    results = []
    
    for email in emails:
        sender = email.get("sender")
        subject = email.get("subject")
        body = email.get("body", "")
        email_id = email.get("id")
        thread_id = email.get("thread_id")
        
        logger.info(f"Processing email {email_id} from {sender}")
        
        # 2. Detect Intent via Gemini
        intent = detect_intent(body)
        logger.info(f"  -> Intent: {intent}")
        
        reply_body = None
        
        # 3. Handle specific intents
        if intent == "scheduling":
            slots = extract_time_slots(body)
            
            if not slots:
                # Ambiguous time -> Ask for clarification using LLM
                reply_body = generate_clarification(body)
                logger.info("  -> Ambiguous time. Generated clarification.")
            else:
                # Attempt to schedule the first extracted slot
                event_link = schedule_meeting(sender, slots[0], subject)
                if event_link:
                    reply_body = f"Perfect! I have mapped this out and automatically scheduled a meeting for us. You can view or modify the Google Calendar event here: {event_link}"
                    logger.info("  -> Meeting scheduled successfully.")
                else:
                    reply_body = "I tried to schedule the meeting, but the extracted time seemed invalid or is in the past. Could you please propose another time format?"
                    logger.warning("  -> Failed to schedule meeting.")
                    
        elif intent == "query":
            reply_body = "This is an automated AI reply. I have recognized your question regarding status, and my human operator will get back to you shortly!"
            logger.info("  -> Query detected. Sending default acknowledgment.")
            
        elif intent == "clarification":
            reply_body = "Thank you for the clarification. I am updating your preferences."
            logger.info("  -> Clarification received.")
            
        else:
            logger.info("  -> Unknown intent. Ignoring this email.")
            
        # 4. Auto-reply if we generated an actionable response
        if reply_body:
            msg_id = send_reply(
                to=sender,
                subject=subject,
                body=reply_body,
                thread_id=thread_id
            )
            logger.info(f"  -> Auto-replied with MSG ID: {msg_id}")
            
        # 5. Mark as read so we don't process it a second time
        try:
           mark_as_read(email_id)
        except Exception as e:
           logger.error(f"Failed to mark as read: {e}")
        
        results.append({
            "email_id": email_id,
            "intent": intent,
            "replied": bool(reply_body)
        })

    return {"status": "processed", "details": results}
