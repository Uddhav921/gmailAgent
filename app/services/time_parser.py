"""
Time Parsing Service — Phase 3
Handles translation of natural language time into UTC datetimes
using `dateparser` and timezone logic.
"""

import logging
from datetime import datetime
import dateparser
import pytz

logger = logging.getLogger(__name__)

# Fallback to IST if no timezone is provided
DEFAULT_TIMEZONE_STR = "Asia/Kolkata"
DEFAULT_TIMEZONE = pytz.timezone(DEFAULT_TIMEZONE_STR)


def parse_time_string(text: str) -> datetime | None:
    """
    Parse a natural language time string into an aware datetime object.
    Uses the default timezone (IST) if none is specified or inferred.
    """
    try:
        # dateparser returns a datetime object based on settings
        dt = dateparser.parse(
            text,
            settings={
                "TIMEZONE": DEFAULT_TIMEZONE_STR,
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )
        return dt
    except Exception as e:
        logger.error(f"Failed to parse time string '{text}': {e}")
        return None


def normalize_to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to strictly UTC timezone.
    If the datetime is naive, it assumes DEFAULT_TIMEZONE first.
    """
    if dt.tzinfo is None:
        # If naive, assume default timezone
        dt = DEFAULT_TIMEZONE.localize(dt)
        
    return dt.astimezone(pytz.UTC)
