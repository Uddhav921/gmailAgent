# 🤖 AI Email Agent

Autonomous email scheduling assistant that reads emails, detects intent via LLM, finds availability overlaps, and books Google Calendar meetings — with memory via Redis + Supermemory.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Email | Gmail API (OAuth 2.0) |
| LLM | Google Gemini API |
| Database | MongoDB Atlas (Motor async) |
| Cache | Redis (Upstash) |
| Memory | Supermemory API |
| Calendar | Google Calendar API |

---

## Project Structure

```
gmailAgent/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # MongoDB Motor connection
│   ├── routes/
│   │   ├── auth.py          # OAuth 2.0 login/callback
│   │   ├── webhook.py       # Gmail Pub/Sub push handler
│   │   └── admin.py         # Manual triggers & debug
│   ├── services/
│   │   ├── gmail_service.py # Email fetch, parse, send
│   │   ├── llm_service.py   # Intent detection + time extraction (Phase 3)
│   │   ├── scheduler.py     # Overlap detection + booking (Phase 4)
│   │   ├── calendar_service.py # Google Calendar API (Phase 4)
│   │   └── memory_service.py   # Redis + Supermemory (Phase 5)
│   ├── models/
│   │   ├── user.py          # User schema
│   │   ├── meeting.py       # Meeting schema
│   │   └── email_log.py     # Email processing log
│   └── utils/
│       ├── timezone.py      # UTC normalization (Phase 4)
│       └── reply_builder.py # Email reply templates (Phase 6)
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone & Install

```bash
git clone <repo-url>
cd gmailAgent
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Google Cloud Setup (Required First)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable: **Gmail API** + **Google Calendar API** + **Cloud Pub/Sub API**
4. Create **OAuth 2.0 Client ID** → Web Application
5. Set Authorized Redirect URI: `http://localhost:8000/auth/callback`
6. Download `credentials.json` *(do NOT commit this)*

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the Swagger UI.

---

## Authentication Flow

```
1. Visit http://localhost:8000/auth/login
2. Complete Google consent screen
3. Redirected back → tokens saved to token.json
4. Visit http://localhost:8000/auth/status to verify
5. POST /auth/watch to enable Gmail push notifications
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/auth/login` | Start OAuth flow |
| GET | `/auth/callback` | OAuth callback |
| GET | `/auth/status` | Check auth status |
| POST | `/auth/watch` | Enable Gmail push |
| POST | `/webhook/gmail` | Pub/Sub notification receiver |
| GET | `/admin/emails` | List unread emails |
| GET | `/admin/thread/{id}` | View email thread |
| POST | `/admin/process` | Manually trigger pipeline |
| POST | `/admin/send-test` | Send test email |

---

## Development Phases

- [x] **Phase 1** — Project scaffold, config, MongoDB
- [x] **Phase 2** — Gmail OAuth, fetch, parse, send, Pub/Sub
- [ ] **Phase 3** — LLM intent detection + time extraction
- [ ] **Phase 4** — Overlap scheduling + Google Calendar booking
- [ ] **Phase 5** — Redis cache + Supermemory preferences
- [ ] **Phase 6** — Reply builder + thread analyzer
- [ ] **Phase 7** — Advanced features (priority, clarification, override)

---

> ⚠️ All AI-generated emails include the disclaimer: *"This email was sent by an experimental AI assistant."*
