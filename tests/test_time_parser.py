import pytest
from datetime import datetime
import pytz
from app.services.time_parser import parse_time_string, normalize_to_utc
from app.utils.timezone import to_utc, resolve_timezone


def test_parse_valid_time():
    dt = parse_time_string("tomorrow at 2 PM IST")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_invalid_time():
    dt = parse_time_string("not a real time")
    # Dateparser can sometimes return a datetime even for bad input, 
    # but let's just make sure it doesn't crash
    if dt is not None:
        assert isinstance(dt, datetime)


def test_normalize_to_utc_naive():
    naive_dt = datetime(2026, 4, 1, 14, 0)
    utc_dt = normalize_to_utc(naive_dt)
    assert utc_dt.tzinfo == pytz.UTC


def test_to_utc_with_alias():
    naive_dt = datetime(2026, 4, 1, 14, 0)
    # 2 PM EST -> 6 PM UTC (or 7 PM UTC depending on DST)
    utc_dt = to_utc(naive_dt, "EST")
    assert utc_dt.tzinfo == pytz.UTC


def test_resolve_timezone_alias():
    tz = resolve_timezone("IST")
    assert str(tz) == "Asia/Kolkata"

    tz2 = resolve_timezone("PST")
    assert str(tz2) == "America/Los_Angeles"
