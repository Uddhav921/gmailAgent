"""
Calendar Service — Phase 4
Wraps the Google Calendar API to fetch FreeBusy info and Book meetings.
"""

import logging
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.services.gmail_service import load_credentials

logger = logging.getLogger(__name__)


def get_calendar_service():
    """Returns an authenticated Calendar API client using the shared Gmail OAuth token."""
    creds = load_credentials()
    if not creds:
        raise ValueError("No credentials found. Please authenticate via /auth/login")
    return build("calendar", "v3", credentials=creds)


def create_event(
    title: str, 
    start_utc_iso: str, 
    end_utc_iso: str, 
    attendee_emails: list[str],
    description: str = ""
) -> Optional[str]:
    """
    Creates a Google Calendar event.
    Returns the HTML link to the booked event, or None on failure.
    """
    service = get_calendar_service()
    
    event_body = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_utc_iso,     # Must be formatted like "2023-10-27T12:00:00Z"
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_utc_iso,
            'timeZone': 'UTC',
        },
        'attendees': [{'email': email} for email in attendee_emails],
        'reminders': {
            'useDefault': True,
        },
        # Automatically generate Google Meet video conference
        'conferenceData': {
            'createRequest': {
                'requestId': f"req-{start_utc_iso}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    try:
        # conferenceDataVersion=1 is REQUIRED to auto-generate the Google Meet link
        event = service.events().insert(
            calendarId='primary', 
            body=event_body,
            sendUpdates='all', # Automatically sends standard Google Calendar invitations to attendees!
            conferenceDataVersion=1
        ).execute()
        
        logger.info(f"Event created: {event.get('htmlLink')}")
        return event.get('htmlLink')
    except HttpError as error:
        logger.error(f"An error occurred creating event: {error}")
        return None
