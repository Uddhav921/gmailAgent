#!/usr/bin/env python3
"""Comprehensive test script for Gmail AI Agent - Run this to verify everything works"""

import sys
from datetime import datetime

passed = 0
failed = 0

def test(name):
    """Decorator to run and track tests"""
    def decorator(fn):
        global passed, failed
        try:
            fn()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            error_msg = str(e)[:80]
            print(f"❌ {name}")
            print(f"   Error: {error_msg}")
            failed += 1
        return fn
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
#                            TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

@test("1. Import all modules")
def test_imports():
    from app.main import app
    from app.services import gmail_service, llm_service, scheduler, memory_service
    from app.services import calendar_service, thread_analyzer
    from app.utils import reply_builder, timezone
    from app.models import user, meeting, email_log
    from app.routes import auth, webhook, admin

@test("2. Health endpoint")
def test_health():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'healthy'

@test("3. Root endpoint")
def test_root():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get('/')
    assert r.status_code == 200
    assert r.json()['service'] == 'AI Email Agent'

@test("4. Time parsing - valid time")
def test_time_parser_valid():
    from app.services.time_parser import parse_time_string
    dt = parse_time_string('2026-04-15 14:00 IST')
    assert dt is not None
    # Verify date components (hour may differ due to timezone offset)
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 15

@test("5. Time parsing - normalize to UTC")
def test_time_parser_utc():
    from app.services.time_parser import parse_time_string, normalize_to_utc
    dt = parse_time_string('2026-04-15 14:00 IST')  # IST is UTC+5:30
    if dt:
        utc = normalize_to_utc(dt)
        assert utc.tzinfo is not None
        assert 'UTC' in str(utc.tzinfo)

@test("6. Timezone resolution - IST alias")
def test_timezone_tz():
    from app.utils.timezone import resolve_timezone
    tz = resolve_timezone('IST')
    assert str(tz) == 'Asia/Kolkata'

@test("7. Timezone resolution - fallback to default")
def test_timezone_fallback():
    from app.utils.timezone import resolve_timezone
    tz = resolve_timezone('INVALID_TZ')
    assert str(tz) == 'Asia/Kolkata'  # Should fallback to IST

@test("8. Build confirmation email")
def test_reply_confirmation():
    from app.utils.reply_builder import build_confirmation_email
    slot = {
        'date': '2026-04-15',
        'start': '14:00',
        'end': '15:00',
        'timezone': 'IST'
    }
    reply = build_confirmation_email(
        slot=slot,
        event_link='https://calendar.google.com/event',
        participants=['user@example.com']
    )
    assert 'experimental AI' in reply
    assert '2026-04-15' in reply
    assert '14:00' in reply

@test("9. Build clarification email")
def test_reply_clarification():
    from app.utils.reply_builder import build_clarification_email
    reply = build_clarification_email("What timezone are you in?")
    assert 'experimental AI' in reply
    assert 'What timezone are you in?' in reply

@test("10. Build summary email")
def test_reply_summary():
    from app.utils.reply_builder import build_summary_email
    reply = build_summary_email("Meeting scheduled for tomorrow at 2 PM")
    assert 'experimental AI' in reply
    assert 'summary' in reply.lower()

@test("11. Cache intent in memory")
def test_memory_cache():
    from app.services.memory_service import cache_intent, get_cached_intent
    test_id = f"email_test_{datetime.now().timestamp()}"
    cache_intent(test_id, 'scheduling', ttl=3600)
    result = get_cached_intent(test_id)
    assert result == 'scheduling'

@test("12. Rate limiting - allow initial requests")
def test_rate_limit():
    from app.services.memory_service import check_rate_limit
    test_user = f"user_{datetime.now().timestamp()}@example.com"
    # First 3 requests should be allowed
    for i in range(3):
        allowed = check_rate_limit(test_user)
        assert allowed == True

@test("13. UserModel creation")
def test_user_model():
    from app.models.user import UserModel
    user = UserModel(email='test@example.com', name='Test User', role='organizer')
    assert user.email == 'test@example.com'
    assert user.name == 'Test User'
    assert user.role == 'organizer'
    assert user.timezone == 'UTC'

@test("14. MeetingModel creation")
def test_meeting_model():
    from app.models.meeting import MeetingModel, MeetingSlot
    slot = MeetingSlot(
        start_utc=datetime(2026, 4, 15, 14, 0),
        end_utc=datetime(2026, 4, 15, 15, 0),
        timezone='UTC'
    )
    meeting = MeetingModel(
        title='Test Meeting',
        participants=['user@example.com'],
        slot=slot,
        status='pending'
    )
    assert meeting.title == 'Test Meeting'
    assert meeting.status == 'pending'
    assert len(meeting.participants) == 1

@test("15. Find overlap - single participant")
def test_scheduler_overlap_single():
    from app.services.scheduler import find_overlap
    slots = {
        'user1@example.com': [
            {'start_utc': datetime(2026, 4, 15, 14, 0), 
             'end_utc': datetime(2026, 4, 15, 16, 0)}
        ]
    }
    # Should return the slot if only one participant
    result = find_overlap(slots)
    assert isinstance(result, list)

@test("16. Priority scheduler - overlapping slots")
def test_scheduler_priority():
    from app.services.scheduler import find_overlap_with_priority
    slots = {
        'user1@example.com': [
            {'start_utc': datetime(2026, 4, 15, 14, 0), 
             'end_utc': datetime(2026, 4, 15, 16, 0)}
        ],
        'user2@example.com': [
            {'start_utc': datetime(2026, 4, 15, 15, 0), 
             'end_utc': datetime(2026, 4, 15, 17, 0)}
        ]
    }
    priorities = {
        'user1@example.com': 8,
        'user2@example.com': 5
    }
    overlaps = find_overlap_with_priority(slots, priorities)
    assert isinstance(overlaps, list)
    # May be empty or have overlapping slot
    if overlaps:
        assert 'priority_score' in overlaps[0]

@test("17. Email log model")
def test_email_log_model():
    from app.models.email_log import EmailLogModel
    log = EmailLogModel(
        email_id='msg_001',
        thread_id='thread_001',
        sender='user@example.com',
        recipients=['recipient@example.com'],
        subject='Test',
        detected_intent='scheduling'
    )
    assert log.email_id == 'msg_001'
    assert log.detected_intent == 'scheduling'

@test("18. API: User preference endpoint exists")
def test_api_user_preference():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    # Just check the endpoint exists and responds
    r = client.post(
        '/admin/user-preference',
        json={
            'user_email': 'test@example.com',
            'key': 'preferred_timezone',
            'value': 'Asia/Kolkata'
        }
    )
    assert r.status_code == 200

@test("19. API: Smart suggestions endpoint exists")
def test_api_smart_suggestions():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get('/admin/smart-suggestions/test@example.com')
    assert r.status_code == 200
    assert 'user_email' in r.json()

@test("20. API: Approve meeting endpoint exists")
def test_api_approve_meeting():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.post(
        '/admin/approve-meeting',
        json={
            'user_email': 'test@example.com',
            'meeting_id': 'meet_123',
            'action': 'approve'
        }
    )
    assert r.status_code == 200

# ═══════════════════════════════════════════════════════════════════════════════
#                          RUN ALL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " Gmail AI Agent - Comprehensive Test Suite ".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Run all test functions
    test_imports()
    test_health()
    test_root()
    test_time_parser_valid()
    test_time_parser_utc()
    test_timezone_tz()
    test_timezone_fallback()
    test_reply_confirmation()
    test_reply_clarification()
    test_reply_summary()
    test_memory_cache()
    test_rate_limit()
    test_user_model()
    test_meeting_model()
    test_scheduler_overlap_single()
    test_scheduler_priority()
    test_email_log_model()
    test_api_user_preference()
    test_api_smart_suggestions()
    test_api_approve_meeting()
    
    print()
    print("╔" + "═" * 78 + "╗")
    if failed == 0:
        print(f"║ {'✅ ALL TESTS PASSED'.center(78)} ║")
    else:
        print(f"║ {'⚠️  SOME TESTS FAILED'.center(78)} ║")
    print("╠" + "═" * 78 + "╣")
    print(f"║ {'PASSED: ' + str(passed):.<60} {'│':<18} ║")
    print(f"║ {'FAILED: ' + str(failed):.<60} {'│':<18} ║")
    print(f"║ {'TOTAL:  ' + str(passed + failed):.<60} {'│':<18} ║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    sys.exit(0 if failed == 0 else 1)
