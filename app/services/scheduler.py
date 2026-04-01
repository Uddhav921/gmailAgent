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

def find_overlap(slots_per_participant: dict) -> list[dict]:
    """
    Find common available time slots among multiple participants.
    Phase 7: Supports priority-based scheduling.
    
    Args:
        slots_per_participant: dict of {participant_email: [slots]}
            where each slot is {"start_utc": datetime, "end_utc": datetime}
    
    Returns:
        List of overlapping slots sorted by priority/value.
    """
    if not slots_per_participant:
        return []
    
    # Get all slots from all participants
    all_slots = []
    for email, slots in slots_per_participant.items():
        all_slots.extend([(s, email) for s in slots])
    
    if not all_slots:
        return []
    
    # Sort by start time
    all_slots.sort(key=lambda x: x[0].get("start_utc", datetime.min))
    
    # Simple overlap detection: find slots where intervals intersect
    overlaps = []
    for i, (slot1, email1) in enumerate(all_slots):
        start1 = slot1.get("start_utc")
        end1 = slot1.get("end_utc")
        
        if not start1 or not end1:
            continue
            
        overlap_found = True
        overlap_slot = slot1.copy()
        
        # Check if this slot overlaps with all other participants
        for j, (slot2, email2) in enumerate(all_slots[i+1:], start=i+1):
            start2 = slot2.get("start_utc")
            end2 = slot2.get("end_utc")
            
            if not start2 or not end2:
                continue
            
            # Check interval overlap
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            if overlap_start >= overlap_end:
                overlap_found = False
                break
            
            # Update the overlapping interval
            overlap_slot["start_utc"] = overlap_start
            overlap_slot["end_utc"] = overlap_end
        
        if overlap_found and overlap_slot not in overlaps:
            overlaps.append(overlap_slot)
    
    # TODO: Phase 7 - Sort by priority (priority users' slots ranked higher)
    return overlaps


def find_overlap_with_priority(slots_per_participant: dict, participant_priorities: dict = None) -> list[dict]:
    """
    Phase 7 Feature: Priority-Aware Scheduling
    Find overlapping slots but weight them by participant priority.
    High-priority users' time preferences are ranked higher.
    
    Args:
        slots_per_participant: dict of {participant_email: [slots]}
        participant_priorities: dict of {participant_email: priority_score (1-10)}
    
    Returns:
        Overlapping slots ranked by priority.
    """
    if not participant_priorities:
        participant_priorities = {}
    
    # Get base overlaps
    overlaps = find_overlap(slots_per_participant)
    
    if not overlaps:
        return []
    
    # Rank overlaps by priority
    ranked_overlaps = []
    for overlap in overlaps:
        # Calculate priority score for this overlap
        priority_score = sum(
            participant_priorities.get(email, 5)  # Default 5 if not specified
            for email in slots_per_participant.keys()
        ) / len(slots_per_participant)
        
        overlap["priority_score"] = priority_score
        ranked_overlaps.append(overlap)
    
    # Sort by priority score (highest first)
    ranked_overlaps.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    
    return ranked_overlaps

def check_for_duplicates(participants: list[str], slot: dict) -> bool:
    """
    Query database to check if a meeting is already booked at this time.
    (Placeholder for MongoDB integration)
    """
    # TODO: Check MongoDB meeting collection
    return False
