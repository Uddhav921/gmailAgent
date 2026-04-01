# Gmail AI Agent — Testing Guide

Run these commands in PowerShell from the project root directory.

---

## **STEP 0: Verify Environment**

```powershell
cd "c:\Users\geeta\OneDrive\Desktop\All Projects\Hackethons\COEPHACK\gmailAgent"
echo "Current directory:"
pwd
```

**Expected output**: Shows your project path

---

## **STEP 1: Run Unit Tests (Fastest)**

```powershell
# Run all tests in the tests/ folder
pytest tests/ -v

# Or individual test files:
pytest tests/test_time_parser.py -v
pytest tests/test_llm_intent.py -v  
pytest tests/test_pipeline.py -v
```

**Expected output**: Shows test results like:
```
tests/test_time_parser.py::test_parse_valid_time PASSED [ 20%]
tests/test_time_parser.py::test_parse_invalid_time PASSED [ 40%]
...
======================== 5 passed in 6.49s ========================
```

**If PASSED**: ✅ Unit tests working
**If FAILED**: ❌ Check error message, likely missing dependency

---

## **STEP 2: Import All Modules (30 seconds)**

```powershell
python -c "
from app.main import app
from app.services import gmail_service, llm_service, scheduler, memory_service, calendar_service, thread_analyzer
from app.utils import reply_builder, timezone
from app.models import user, meeting, email_log
print('✅ All modules imported successfully')
"
```

**Expected output**: 
```
✅ All modules imported successfully
```

**If error**: ❌ Shows which module failed to import

---

## **STEP 3: Test Individual Services (Copy-paste each)**

### **Test 3A: Health Check**
```powershell
python -c "
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get('/health')
print(f'Status Code: {response.status_code}')
print(f'Response: {response.json()}')
"
```

**Expected output**:
```
Status Code: 200
Response: {'status': 'healthy'}
```

---

### **Test 3B: Time Parser**
```powershell
python -c "
from app.services.time_parser import parse_time_string, normalize_to_utc
from datetime import datetime
import pytz

# Test 1: Parse time with timezone
print('Test 1: Parsing time...')
dt = parse_time_string('2026-04-15 14:00 IST')
print(f'  Parsed: {dt}')
print(f'  Type: {type(dt)}')

# Test 2: Normalize to UTC
print('\nTest 2: Normalizing to UTC...')
if dt:
    utc = normalize_to_utc(dt)
    print(f'  UTC: {utc}')
    print(f'  Timezone: {utc.tzinfo}')

print('\n✅ Time parser working')
"
```

**Expected output**:
```
Test 1: Parsing time...
  Parsed: 2026-04-15 14:00:00+05:30
  Type: <class 'datetime.datetime'>

Test 2: Normalizing to UTC...
  UTC: 2026-04-15 08:30:00+00:00
  Timezone: UTC

✅ Time parser working
```

---

### **Test 3C: Reply Builder**
```powershell
python -c "
from app.utils.reply_builder import (
    build_confirmation_email, 
    build_clarification_email,
    build_summary_email
)

# Test 1: Confirmation email
print('Test 1: Confirmation Email')
slot = {'date': '2026-04-15', 'start': '14:00', 'end': '15:00', 'timezone': 'IST'}
email = build_confirmation_email(slot, 'https://calendar.google.com/event', ['user@example.com'])
print(f'  Length: {len(email)} chars')
print(f'  Contains disclaimer: {\"experimental AI\" in email}')
print(f'  Preview: {email[:100]}...')

# Test 2: Clarification email
print('\nTest 2: Clarification Email')
email = build_clarification_email('What timezone are you in?')
print(f'  Length: {len(email)} chars')
print(f'  Preview: {email[:100]}...')

# Test 3: Summary email
print('\nTest 3: Summary Email')
email = build_summary_email('Meeting scheduled for tomorrow at 2 PM')
print(f'  Length: {len(email)} chars')
print(f'  Preview: {email[:100]}...')

print('\n✅ All reply builders working')
"
```

**Expected output**: Shows 3 different email templates

---

### **Test 3D: Memory Service (Redis)**
```powershell
python -c "
from app.services.memory_service import (
    cache_intent, 
    get_cached_intent,
    check_rate_limit
)

# Test 1: Cache intent
print('Test 1: Caching intent...')
cache_intent('email_001', 'scheduling', ttl=3600)
result = get_cached_intent('email_001')
print(f'  Cached intent: {result}')
print(f'  Match: {result == \"scheduling\"}')

# Test 2: Rate limiting
print('\nTest 2: Rate limit check...')
for i in range(3):
    allowed = check_rate_limit('user@example.com')
    print(f'  Request {i+1}: {\"✅ Allowed\" if allowed else \"❌ Blocked\"}')

print('\n✅ Memory service working')
"
```

**Expected output**:
```
Test 1: Caching intent...
  Cached intent: scheduling
  Match: True

Test 2: Rate limit check...
  Request 1: ✅ Allowed
  Request 2: ✅ Allowed
  Request 3: ✅ Allowed

✅ Memory service working
```

---

### **Test 3E: Timezone Utils**
```powershell
python -c "
from app.utils.timezone import resolve_timezone, TIMEZONE_ALIASES
import pytz

# Test 1: Resolve timezone by alias
print('Test 1: Timezone aliases')
for alias in ['IST', 'EST', 'PST', 'UTC']:
    tz = resolve_timezone(alias)
    print(f'  {alias} -> {tz}')

# Test 2: Resolve by full name
print('\nTest 2: Full timezone names')
tz = resolve_timezone('America/New_York')
print(f'  America/New_York -> {tz}')

# Test 3: Invalid timezone (fallback)
print('\nTest 3: Invalid timezone (should fallback to IST)')
tz = resolve_timezone('Invalid/Zone')
print(f'  Invalid/Zone -> {tz}')

print('\n✅ Timezone utils working')
"
```

**Expected output**: Shows timezone conversions

---

### **Test 3F: Scheduler (Priority Logic)**
```powershell
python -c "
from app.services.scheduler import find_overlap_with_priority
from datetime import datetime

# Test: Find overlapping time slots
print('Test: Finding overlapping time slots')
slots = {
    'user1@example.com': [
        {'start_utc': datetime(2026, 4, 15, 14, 0), 'end_utc': datetime(2026, 4, 15, 16, 0)}
    ],
    'user2@example.com': [
        {'start_utc': datetime(2026, 4, 15, 15, 0), 'end_utc': datetime(2026, 4, 15, 17, 0)}
    ]
}
priorities = {
    'user1@example.com': 8,
    'user2@example.com': 5
}

overlaps = find_overlap_with_priority(slots, priorities)
print(f'  Found {len(overlaps)} overlapping slot(s)')
for i, slot in enumerate(overlaps):
    print(f'  Slot {i+1}:')
    print(f'    Start: {slot.get(\"start_utc\")}')
    print(f'    End: {slot.get(\"end_utc\")}')
    print(f'    Priority Score: {slot.get(\"priority_score\")}')

print('\n✅ Scheduler working')
"
```

**Expected output**: Shows overlapping time slot from 15:00-16:00

---

## **STEP 4: Test API Endpoints**

### **Start the Server (in one terminal)**
```powershell
# Terminal 1: Start server
cd "c:\Users\geeta\OneDrive\Desktop\All Projects\Hackethons\COEPHACK\gmailAgent"
python -m uvicorn app.main:app --reload
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### **Test Endpoints (in another terminal)**
```powershell
# Terminal 2: Keep in project directory
cd "c:\Users\geeta\OneDrive\Desktop\All Projects\Hackethons\COEPHACK\gmailAgent"
```

---

### **Test 4A: Health Endpoint**
```powershell
curl http://localhost:8000/health
```

**Expected output**:
```json
{"status":"healthy"}
```

---

### **Test 4B: Root Endpoint**
```powershell
curl http://localhost:8000/
```

**Expected output**:
```json
{"status":"ok","service":"AI Email Agent","version":"1.0.0"}
```

---

### **Test 4C: Save User Preference**
```powershell
curl -X POST http://localhost:8000/admin/user-preference `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "test@example.com",
    "key": "preferred_timezone",
    "value": "Asia/Kolkata"
  }'
```

**Expected output**:
```json
{"operation":"save","key":"preferred_timezone","value":"Asia/Kolkata","saved":true}
```

---

### **Test 4D: Get User Preference**
```powershell
curl -X POST http://localhost:8000/admin/user-preference `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "test@example.com",
    "key": "preferred_timezone"
  }'
```

**Expected output**:
```json
{"operation":"retrieve","key":"preferred_timezone","value":"Asia/Kolkata","found":true}
```

---

### **Test 4E: Get Smart Suggestions**
```powershell
curl http://localhost:8000/admin/smart-suggestions/test@example.com
```

**Expected output**:
```json
{
  "user_email":"test@example.com",
  "meeting_subject":null,
  "user_timezone":"UTC",
  "meeting_history_count":0,
  "suggestions":[]
}
```

---

### **Test 4F: Approve Meeting (Phase 7)**
```powershell
curl -X POST http://localhost:8000/admin/approve-meeting `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "test@example.com",
    "meeting_id": "meet_123",
    "action": "approve",
    "notes": "Looks good"
  }'
```

**Expected output**:
```json
{"status":"updated","meeting_id":"meet_123","action":"approve","notes":"Looks good"}
```

---

### **Test 4G: List Emails (Requires Gmail Setup)**
```powershell
curl http://localhost:8000/admin/emails
```

**Expected output** (if Gmail authenticated):
```json
{"count":3,"emails":[{"id":"...", "sender":"...", "subject":"..."}]}
```

**If not authenticated**:
```json
{"detail":"No credentials found. Please authenticate via /auth/login"}
```

---

## **STEP 5: Comprehensive Test Script**

```powershell
# Save as test_all.py in project root
cat > test_all.py << 'EOF'
#!/usr/bin/env python3
"""Comprehensive test script for Gmail AI Agent"""

import sys
from datetime import datetime

passed = 0
failed = 0

def test(name):
    def decorator(fn):
        global passed, failed
        try:
            fn()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {str(e)[:100]}")
            failed += 1
        return fn
    return decorator

# ─── Tests ───────────────────────────────────────────────────────────

@test("1. Import all modules")
def test_imports():
    from app.main import app
    from app.services import gmail_service, llm_service, scheduler
    from app.utils import reply_builder, timezone

@test("2. Health check")
def test_health():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'healthy'

@test("3. Time parsing")
def test_time_parser():
    from app.services.time_parser import parse_time_string
    dt = parse_time_string('2026-04-15 14:00 IST')
    assert dt is not None
    assert dt.hour == 14

@test("4. Timezone resolution")
def test_timezone():
    from app.utils.timezone import resolve_timezone
    tz = resolve_timezone('IST')
    assert str(tz) == 'Asia/Kolkata'

@test("5. Reply builder")
def test_reply():
    from app.utils.reply_builder import build_confirmation_email
    slot = {'date': '2026-04-15', 'start': '14:00', 'end': '15:00', 'timezone': 'IST'}
    reply = build_confirmation_email(slot, 'https://example.com', ['user@example.com'])
    assert 'experimental AI' in reply
    assert '2026-04-15' in reply

@test("6. Memory caching")
def test_memory():
    from app.services.memory_service import cache_intent, get_cached_intent
    cache_intent('test_email_001', 'scheduling')
    result = get_cached_intent('test_email_001')
    assert result == 'scheduling'

@test("7. Rate limiting")
def test_rate_limit():
    from app.services.memory_service import check_rate_limit
    # Should allow up to RATE_LIMIT_MAX requests
    for i in range(3):
        allowed = check_rate_limit('testuser@example.com')
        assert allowed == True

@test("8. Priority scheduler")
def test_scheduler():
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
    overlaps = find_overlap_with_priority(slots)
    assert len(overlaps) > 0

@test("9. User model")
def test_user_model():
    from app.models.user import UserModel
    user = UserModel(email='test@example.com', name='Test User')
    assert user.email == 'test@example.com'
    assert user.timezone == 'UTC'

@test("10. Meeting model")
def test_meeting_model():
    from app.models.meeting import MeetingModel, MeetingSlot
    slot = MeetingSlot(
        start_utc=datetime.utcnow(),
        end_utc=datetime.utcnow(),
        timezone='UTC'
    )
    meeting = MeetingModel(
        title='Test Meeting',
        participants=['user@example.com'],
        slot=slot
    )
    assert meeting.status == 'pending'

# ─── Run Tests ────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("Gmail AI Agent - Comprehensive Test Suite")
    print("=" * 60)
    print()
    
    # Run all tests
    test_imports()
    test_health()
    test_time_parser()
    test_timezone()
    test_reply()
    test_memory()
    test_rate_limit()
    test_scheduler()
    test_user_model()
    test_meeting_model()
    
    print()
    print("=" * 60)
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
EOF

# Run it
python test_all.py
```

**Run it**:
```powershell
python test_all.py
```

**Expected output**:
```
============================================================
Gmail AI Agent - Comprehensive Test Suite
============================================================

✅ 1. Import all modules
✅ 2. Health check
✅ 3. Time parsing
✅ 4. Timezone resolution
✅ 5. Reply builder
✅ 6. Memory caching
✅ 7. Rate limiting
✅ 8. Priority scheduler
✅ 9. User model
✅ 10. Meeting model

============================================================
PASSED: 10
FAILED: 0
============================================================
```

---

## **QUICK REFERENCE: Test Order**

Run in this order:

1. **Unit Tests** → `pytest tests/ -v`
2. **Module Imports** → Use Step 2 command
3. **Service Tests** → Run Step 3A-F commands
4. **API Tests** → Start server (Step 4), then run endpoints
5. **Full Suite** → Run `test_all.py`

---

## **Troubleshooting**

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'app'` | Make sure you're in project root: `cd "c:\Users\geeta\OneDrive\Desktop\All Projects\Hackethons\COEPHACK\gmailAgent"` |
| `Connection refused` for Redis | Redis not running — app falls back to in-memory cache (OK for testing) |
| `Gmail API error` | Missing OAuth setup — only needed for `/admin/emails` endpoint |
| Pytest not found | Install: `pip install pytest` |
| `requirements.txt` issues | Run: `pip install -r requirements.txt` |

---

## **Success Criteria**

✅ **All tests pass** → Ready for deployment  
✅ **Health endpoints respond** → Server working  
✅ **Memory service works** → Caching functional  
✅ **Reply builder works** → Emails formatted correctly  
✅ **No import errors** → All dependencies installed  

Once all pass → You have a **production-ready MVP** 🚀
