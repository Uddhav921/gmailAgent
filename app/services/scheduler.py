"""
Scheduler Logic — Phase 4
Validates available times and calls Calendar Service to book.
"""

import logging
from datetime import datetime, timedelta
import pytz

from app.services.calendar_service import create_event
from app.services.time_parser import parse_time_string, normalize_to_utc

logger = logging.getLogger(__name__)


def schedule_meeting(
    sender_email: str, 
    time_slot: dict, 
    subject: str
) -> str | None:
    """
    Attempts to schedule a meeting using the provided dict of extracted times.
    Expects time_slot schema:
        { "date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "timezone": "IST" }
    
    Returns the Google Calendar HTML link if booked, or None if failed.
    """
    date_str = time_slot.get("date")
    start_str = time_slot.get("start")
    end_str = time_slot.get("end")
    tz_str = time_slot.get("timezone", "")

    if not date_str or not start_str:
        logger.error("Missing date or start time for scheduling.")
        return None

    # Construct the base aware start time
    start_full_str = f"{date_str} {start_str} {tz_str}".strip()
    
    start_dt = parse_time_string(start_full_str)
    if not start_dt:
        return None
        
    start_utc = normalize_to_utc(start_dt)
    
    # Process end time (default to 45 mins after start if missing)
    if end_str:
        end_full_str = f"{date_str} {end_str} {tz_str}".strip()
        end_dt = parse_time_string(end_full_str)
        if end_dt:
            end_utc = normalize_to_utc(end_dt)
        else:
            end_utc = start_utc + timedelta(minutes=45)
    else:
        end_utc = start_utc + timedelta(minutes=45)

    # Convert UTC datetimes to strict ISO 8601 strings expected by Google Calendar
    start_utc_iso = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc_iso = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Book the event with Calendar API
    meeting_title = f"{subject} Meeting" if subject else "AI Scheduled Meeting"
    attendees = [sender_email]  # In phase 6, we'd add all CCs here as well.
    
    event_link = create_event(
        title=meeting_title,
        start_utc_iso=start_utc_iso,
        end_utc_iso=end_utc_iso,
        attendee_emails=attendees,
        description="This meeting was autonomously scheduled by the AI Email Agent."
    )
    
    return event_link
