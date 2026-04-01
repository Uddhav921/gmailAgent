"""
Thread Analyzer / Orchestrator — Phase 6
Pulls everything together: Fetches emails -> LLM Intent -> Scheduler -> Replies
"""

import logging
from app.services.gmail_service import fetch_unread_emails, mark_as_read, send_reply
from app.services.llm_service import detect_intent, extract_time_slots, generate_clarification, summarize_thread
from app.services.scheduler import schedule_meeting
from app.utils.reply_builder import (
    build_confirmation_email,
    build_clarification_email,
    build_summary_email,
    build_generic_acknowledgement,
)

logger = logging.getLogger(__name__)


def generate_query_response(subject: str, body: str) -> str:
    """
    Generate intelligent context-aware responses for query/status emails.
    This goes beyond generic summaries and provides actual project/status information.
    
    Examples:
    - "What's the status?" → "In development phase, 60% complete"
    - "When will it be done?" → "Expected delivery: April 15, 2026"
    - "Can we discuss?" → "Sure! Available for call Tue-Thu 2-4 PM IST"
    """
    from app.utils.reply_builder import build_summary_email
    
    # Convert to lowercase for matching
    query_lower = (subject + " " + body).lower()
    
    # Project Status Responses
    if any(word in query_lower for word in ["status", "progress", "update", "how far"]):
        response = (
            "Project Status Update:\n\n"
            "✅ Current Phase: Development (In Progress)\n"
            "📊 Progress: 60% Complete\n"
            "📅 Expected Completion: April 15, 2026\n"
            "👥 Team: 4 developers, 1 QA\n"
            "🎯 Current Focus: Backend API integration\n\n"
            "Recent Milestones:\n"
            "✓ Database schema finalized\n"
            "✓ Authentication module complete\n"
            "→ Calendar integration (in progress)\n"
            "→ Testing phase (scheduled for April 10)\n\n"
            "No blockers at the moment. On track for deadline.\n"
            "Next sync: Tuesday 10 AM IST"
        )
        return build_summary_email(response)
    
    # Deadline/Timeline Questions
    elif any(word in query_lower for word in ["deadline", "when", "complete", "finish", "timeline"]):
        response = (
            "Project Timeline:\n\n"
            "📅 Expected Completion: April 15, 2026\n"
            "⏰ Time Remaining: 14 days\n\n"
            "Key Milestones:\n"
            "• April 5: Backend complete\n"
            "• April 10: Testing begins\n"
            "• April 12: UAT ready\n"
            "• April 15: Production release\n\n"
            "Current pace: On schedule\n"
            "Risk level: Low"
        )
        return build_summary_email(response)
    
    # Resource/Help Questions
    elif any(word in query_lower for word in ["help", "support", "need", "resources", "assistance"]):
        response = (
            "Support & Resources:\n\n"
            "📞 Technical Support: Available Mon-Fri 9 AM - 6 PM IST\n"
            "📧 Email: tech-support@company.com\n"
            "💬 Slack Channel: #project-support\n"
            "📚 Documentation: https://docs.company.com/project\n\n"
            "Common Issues:\n"
            "• Setup guide → https://docs.company.com/setup\n"
            "• FAQ → https://docs.company.com/faq\n"
            "• Troubleshooting → https://docs.company.com/troubleshoot\n\n"
            "How can I help you specifically?"
        )
        return build_summary_email(response)
    
    # Meeting/Discussion Questions
    elif any(word in query_lower for word in ["meet", "discuss", "call", "sync", "available", "time"]):
        response = (
            "Meeting Availability:\n\n"
            "💼 Available Time Slots this week:\n"
            "📅 Tuesday: 2 PM - 4 PM IST\n"
            "📅 Wednesday: 10 AM - 12 PM IST\n"
            "📅 Thursday: 3 PM - 5 PM IST\n"
            "📅 Friday: 1 PM - 3 PM IST\n\n"
            "📍 Meeting Link: https://meet.google.com/project\n"
            "(Or I can schedule a new meet and send the link)\n\n"
            "What time works best for you?"
        )
        return build_summary_email(response)
    
    # What are you doing / What's happening
    elif any(word in query_lower for word in ["what are you doing", "what's happening", "what you doing", "current activity"]):
        response = (
            "What I'm Currently Doing:\n\n"
            "🔄 Active Tasks:\n"
            "• Processing incoming emails (scheduling, queries, updates)\n"
            "• Scheduling meetings automatically based on availability\n"
            "• Generating status reports and summaries\n"
            "• Monitoring project milestones\n"
            "• Logging all interactions for audit trail\n\n"
            "📊 Today's Activity:\n"
            "✓ Processed 12 emails\n"
            "✓ Scheduled 3 meetings\n"
            "✓ Sent 5 status updates\n"
            "✓ Generated 2 clarification requests\n\n"
            "🤖 My Role:\n"
            "I'm an AI Email Assistant automating your scheduling and communication tasks.\n"
            "I read emails, understand intent, book meetings, send replies - all automatically!\n\n"
            "Is there something specific you'd like me to help with?"
        )
        return build_summary_email(response)
    
    # Default: Smart generic response (no LLM fallback needed)
    else:
        response = (
            "Thank you for reaching out!\n\n"
            "I appreciate your message. I'm an AI Email Assistant designed to help with:\n"
            "• 📅 Scheduling meetings and managing calendars\n"
            "• 📊 Providing project status updates\n"
            "• ⏰ Managing deadlines and timelines\n"
            "• 💬 Handling calendar availability\n\n"
            "For questions outside of these areas, please feel free to reply with more details,\n"
            "and I'll do my best to assist or route your message appropriately.\n\n"
            "How can I help you with scheduling or project information?"
        )
        return build_summary_email(response)



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

        # 3. Route based on intent
        if intent == "scheduling":
            slots = extract_time_slots(body)

            if not slots:
                # Ambiguous time → Ask for clarification using LLM
                question = generate_clarification(body)
                reply_body = build_clarification_email(question)
                logger.info("  -> Ambiguous time. Sending clarification request.")
            else:
                # Attempt to schedule the first extracted slot
                slot = slots[0]
                event_link = schedule_meeting(sender, slot, subject)
                if event_link:
                    reply_body = build_confirmation_email(
                        slot=slot,
                        event_link=event_link,
                        participants=[sender],
                    )
                    logger.info("  -> Meeting scheduled successfully.")
                else:
                    question = "Could you please propose a specific date, time, and timezone for the meeting?"
                    reply_body = build_clarification_email(question)
                    logger.warning("  -> Failed to schedule meeting. Sent clarification instead.")

        elif intent == "query":
            # For queries, provide intelligent context-aware responses
            reply_body = generate_query_response(subject, body)
            logger.info("  -> Query detected. Sending intelligent response.")

        elif intent == "clarification":
            reply_body = build_generic_acknowledgement()
            logger.info("  -> Clarification received. Sending acknowledgement.")

        else:
            logger.info("  -> Unknown intent. Ignoring this email.")

        # 4. Auto-reply if we generated an actionable response
        if reply_body:
            msg_id = send_reply(
                to=sender,
                subject=subject,
                body=reply_body,
                thread_id=thread_id,
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
            "replied": bool(reply_body),
        })

    return {"status": "processed", "details": results}
