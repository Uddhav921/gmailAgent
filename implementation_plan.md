# AI Email Agent — Implementation Plan

Autonomous scheduling assistant that reads emails, detects intent via LLM, finds availability overlaps, and books Google Calendar meetings automatically with persistent memory via Redis + Supermemory.

---

## Tech Stack Decision

| Layer | Choice | Reason |
|---|---|---|
| **Backend** | Python (FastAPI) | Best ecosystem for ML/NLP; async support |
| **Email Ingestion** | Gmail API (OAuth 2.0) | More reliable than raw IMAP; webhook support |
| **LLM** | Google Gemini API (or Ollama/Mistral local) | Fast, capable, free tier available |
| **NLP / Time Parsing** | `dateparser` + spaCy | Pure Python, no Duckling server needed |
| **Calendar** | Google Calendar API | Direct integration with Gmail OAuth |
| **Short-term Memory** | Redis (Upstash) | Rate limiting + intent cache |
| **Long-term Memory** | Supermemory API | Cross-session user preferences |
| **Database** | MongoDB Atlas | Users, meetings, email logs |
| **Email Sending** | Gmail API (send) | Same OAuth token; no SMTP config |
| **Deployment** | Railway / Render | Free tier, easy environment variables |

---

## Project Structure

```
gmailAgent/
├── app/
│   ├── main.py                  # FastAPI entrypoint
│   ├── config.py                # Env variables / settings
│   ├── routes/
│   │   ├── webhook.py           # Gmail push notification handler
│   │   └── admin.py             # Manual trigger / override endpoints
│   ├── services/
│   │   ├── gmail_service.py     # Fetch, parse, send emails
│   │   ├── llm_service.py       # Intent detection + summarization
│   │   ├── time_parser.py       # Natural language → UTC time slots
│   │   ├── scheduler.py         # Overlap detection + meeting booking
│   │   ├── calendar_service.py  # Google Calendar API wrapper
│   │   ├── memory_service.py    # Redis + Supermemory abstraction
│   │   └── thread_analyzer.py   # Thread summarization logic
│   ├── models/
│   │   ├── user.py              # MongoDB user schema
│   │   ├── meeting.py           # Meeting record schema
│   │   └── email_log.py         # Email log schema
│   └── utils/
│       ├── timezone.py          # UTC normalization helpers
│       └── reply_builder.py     # Format outgoing email replies
├── tests/
│   ├── test_time_parser.py
│   ├── test_scheduler.py
│   └── test_llm_intent.py
├── .env                         # API keys (never commit)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Proposed Changes — Phase by Phase

### Phase 1 — Project Scaffold & Auth Setup

#### [NEW] `app/main.py`
FastAPI app with CORS, router registration, MongoDB startup connection.

#### [NEW] `app/config.py`
Load all env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MONGO_URI`, `REDIS_URL`, `SUPERMEMORY_API_KEY`, `GEMINI_API_KEY`.

#### [NEW] `requirements.txt`
```
fastapi uvicorn motor pymongo python-dotenv
google-auth google-auth-oauthlib google-api-python-client
redis supermemory dateparser spacy
```

#### [NEW] `.env` (template, not committed)
```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GEMINI_API_KEY=
MONGO_URI=
REDIS_URL=
SUPERMEMORY_API_KEY=
```

---

### Phase 2 — Gmail Integration (Ingestion Layer)

#### [NEW] `app/services/gmail_service.py`
- OAuth 2.0 token exchange and refresh
- `fetch_unread_emails()` — list messages from inbox
- `get_email_thread(thread_id)` — fetch full thread JSON
- `parse_email_body(message)` — extract plain text, sender, subject, recipients
- `send_reply(to, subject, body, thread_id)` — send email with disclaimer footer

#### [NEW] `app/routes/webhook.py`
- POST `/webhook/gmail` — receive Gmail push notifications (via Google Pub/Sub)
- Trigger email processing pipeline on new message

> **Setup needed:** Enable Gmail API + Google Calendar API in Google Cloud Console. Create OAuth 2.0 credentials. Set up Pub/Sub topic for push notifications.

---

### Phase 3 — AI / NLP Layer (Intelligence)

#### [NEW] `app/services/llm_service.py`
- `detect_intent(email_text) → "scheduling" | "query" | "clarification" | "unknown"`
  - Uses Gemini API with a structured prompt
- `extract_time_slots(email_text) → list[dict]`
  - Prompt asks LLM to return JSON: `[{"date": "2026-04-01", "start": "14:00", "end": "16:00", "timezone": "IST"}]`
- `summarize_thread(thread_messages) → str`
  - Condense email chain into 2–3 sentences for status query replies
- `generate_clarification(email_text) → str`
  - Generate a polite clarification question when time is ambiguous

#### [NEW] `app/services/time_parser.py`
- `parse_times(text) → list[UTC datetime ranges]`
  - Uses `dateparser` + spaCy as fallback to LLM extraction
- `normalize_to_utc(slot, source_timezone) → slot`

---

### Phase 4 — Scheduler (Overlap + Booking)

#### [NEW] `app/services/scheduler.py`
- `find_overlap(slots_per_participant: dict) → list[slot]`
  - Set intersection logic on UTC time ranges
- `book_meeting(participants, slot, subject) → event_id`
  - Calls `calendar_service.create_event()`
- `check_for_duplicates(participants, slot) → bool`
  - Query MongoDB to prevent double-booking

#### [NEW] `app/services/calendar_service.py`
- `create_event(title, start_utc, end_utc, attendees) → event_link`
  - Uses Google Calendar API with user's OAuth token
- `get_free_busy(user_email, time_min, time_max) → busy_slots`
  - Optionally query Calendar free/busy API for real availability

---

### Phase 5 — Memory Layer (Redis + Supermemory)

#### [NEW] `app/services/memory_service.py`
- **Redis** functions:
  - `cache_intent(email_id, intent, ttl=3600)`
  - `get_cached_intent(email_id) → intent | None`
  - `check_rate_limit(user_email) → bool`
- **Supermemory** functions:
  - `save_user_preference(user_email, key, value)`
  - `get_user_preference(user_email, key) → value`
  - `log_meeting_to_memory(user_email, meeting_summary)`
  - Examples: preferred hours, timezone, meeting history

#### [NEW] `app/models/user.py`, `meeting.py`, `email_log.py`
- MongoDB document schemas using Pydantic

---

### Phase 6 — Reply Builder & Thread Analyzer

#### [NEW] `app/utils/reply_builder.py`
- `build_confirmation_email(slot, event_link, participants) → str`
- `build_clarification_email(question) → str`
- `build_summary_email(summary) → str`
- **All replies append:** `"\n\n---\nThis email was sent by an experimental AI assistant."`

#### [NEW] `app/services/thread_analyzer.py`
- `analyze_thread(messages) → {intent, slots, participants, summary}`
  - Orchestrates the full pipeline: filter noise → detect intent → extract times → route to scheduler or summarizer

---

### Phase 7 — Advanced Features (Post-MVP)

| Feature | Implementation |
|---|---|
| **Priority Scheduling** | Add `role` field to user model; sort participants by priority when resolving conflicts |
| **Smart Suggestions** | After 3+ meetings, ask Supermemory for preferred time patterns → pre-fill suggestions |
| **Human Override** | Add `POST /admin/approve/{meeting_id}` endpoint; hold meetings in "pending" state |
| **Multi-timezone UI** | Show proposed time in sender's TZ + each recipient's TZ in the reply email |
| **Clarification Loop** | If LLM returns `"clarification"`, send email, store state in Redis, resolve on reply |

---

## Verification Plan

### Automated Tests
```bash
# Run all tests
pytest tests/ -v

# Specific unit tests
pytest tests/test_time_parser.py    # UTC normalization, edge cases
pytest tests/test_scheduler.py     # Overlap detection correctness
pytest tests/test_llm_intent.py    # Mock LLM responses, intent routing
```

### Integration Tests
1. **Gmail Ingestion** — Send a test email to the agent's Gmail account → verify it's fetched and parsed
2. **Intent Detection** — Test emails: "Let's meet Thursday 3–5 PM" → `scheduling`; "What's the status?" → `query`
3. **Overlap Logic** — Feed 3 participants with overlapping/non-overlapping slots → verify correct output
4. **Calendar Booking** — Verify a real test event is created in Google Calendar
5. **Memory Persistence** — Save user preference via Supermemory → restart server → verify it's retrieved
6. **Reply Format** — Verify all sent emails contain the AI disclaimer

### Manual Verification
- Deploy to Railway, trigger via real Gmail push notification
- End-to-end: Send "Can we schedule a call tomorrow 4–6 PM?" → verify calendar invite + confirmation email received

---

## Implementation Order (Recommended)

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
Scaffold   Gmail     LLM/NLP   Schedule   Memory    Replies   Advanced
  ✦ Get OAuth working first — everything depends on it
  ✦ Build + test each service in isolation before integration
  ✦ Use mock LLM responses during scheduler development to move faster
```

> [!IMPORTANT]
> **Start here:** Create a Google Cloud project, enable Gmail API + Calendar API, and download your `credentials.json` before writing any code. OAuth setup is the most common blocker.

> [!WARNING]
> Never commit `.env` or `credentials.json` to GitHub. Add both to `.gitignore` immediately in Phase 1.
