"""
Timezone Utility — Phase 6 Helper
Provides UTC normalization helpers and common timezone lookups.
"""

import pytz
from datetime import datetime

# Common timezone aliases → pytz names
TIMEZONE_ALIASES: dict[str, str] = {
    "IST": "Asia/Kolkata",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "GMT": "UTC",
    "UTC": "UTC",
    "BST": "Europe/London",
    "CET": "Europe/Paris",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
}

DEFAULT_TIMEZONE_STR = "Asia/Kolkata"


def resolve_timezone(tz_str: str) -> pytz.BaseTzInfo:
    """
    Resolve a timezone string (abbreviation or full name) to a pytz timezone.
    Falls back to IST if the string is unrecognised.
    """
    if not tz_str:
        return pytz.timezone(DEFAULT_TIMEZONE_STR)

    # Try alias lookup first
    canonical = TIMEZONE_ALIASES.get(tz_str.upper())
    if canonical:
        return pytz.timezone(canonical)

    # Try pytz directly (e.g. "Asia/Kolkata")
    try:
        return pytz.timezone(tz_str)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.timezone(DEFAULT_TIMEZONE_STR)


def to_utc(dt: datetime, source_tz_str: str = "") -> datetime:
    """
    Convert a datetime to UTC.
    If dt is naive, assumes source_tz_str (or IST if empty).
    """
    tz = resolve_timezone(source_tz_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    return dt.astimezone(pytz.UTC)


def format_utc_iso(dt: datetime) -> str:
    """Return an ISO 8601 UTC string suitable for Google Calendar API."""
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def display_in_timezone(utc_dt: datetime, tz_str: str) -> str:
    """
    Convert a UTC datetime to a human-readable string in the target timezone.
    Example: '2026-04-02 14:00 IST'
    """
    tz = resolve_timezone(tz_str)
    local_dt = utc_dt.astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M %Z")
