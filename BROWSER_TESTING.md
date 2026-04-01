# 🌐 Browser Testing Guide — Gmail AI Agent

## **STEP 1: Start the Server**

Open PowerShell and run:

```powershell
cd "c:\Users\geeta\OneDrive\Desktop\All Projects\Hackethons\COEPHACK\gmailAgent"
python -m uvicorn app.main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**Keep this terminal open!** The server is now running locally.

---

## **STEP 2: Test URLs in Your Browser**

Open Google Chrome/Edge and visit these URLs:

### **Health Check (Quick Test)**
```
http://localhost:8000/health
```
**Expected Response:**
```json
{"status":"healthy"}
```
**What it means:** Server is running ✅

---

### **Root Endpoint (API Info)**
```
http://localhost:8000/
```
**Expected Response:**
```json
{
  "status": "ok",
  "service": "AI Email Agent",
  "version": "1.0.0"
}
```
**What it means:** App is loaded and ready ✅

---

## **STEP 3: Test Admin Features (Browser + PowerShell)**

### **View Unread Emails**
```
http://localhost:8000/admin/emails
```
**What you'll see:**
- If Gmail is connected: List of unread emails with sender, subject, snippet
- If Gmail is NOT connected: Error message (requires OAuth setup)

**Example Response (if Gmail configured):**
```json
{
  "count": 3,
  "emails": [
    {
      "id": "msg_001",
      "thread_id": "thread_001",
      "sender": "friend@example.com",
      "subject": "Let's schedule a meeting tomorrow at 2 PM",
      "snippet": "Can we schedule a meeting tomorrow at 2 PM?",
      "date": "2026-04-01"
    }
  ]
}
```

---

### **Manually Trigger Pipeline (Process Emails)**
```
http://localhost:8000/admin/process
```
**Click this URL or use:**
```powershell
curl -X POST http://localhost:8000/admin/process
```

**Expected Response:**
```json
{
  "triggered": true,
  "result": {
    "status": "processing",
    "emails_processed": 3
  }
}
```

**What it does:**
- Fetches unread emails
- Detects intent (scheduling/query/clarification)
- Extracts time slots
- Books calendar events
- Sends auto-replies
- Marks emails as read

**Check manually:**
- 📧 Open your Gmail inbox
- ✉️ Look for auto-reply emails from AI agent
- 📅 Check Google Calendar for new events

---

### **View Meeting History**
```
http://localhost:8000/admin/meeting-history/test@example.com
```

**Expected Response:**
```json
{
  "user_email": "test@example.com",
  "meeting_count": 0,
  "meetings": []
}
```

---

### **Get Smart Suggestions**
```
http://localhost:8000/admin/smart-suggestions/test@example.com
```

**Expected Response:**
```json
{
  "user_email": "test@example.com",
  "meeting_subject": null,
  "user_timezone": "UTC",
  "meeting_history_count": 0,
  "suggestions": []
}
```

---

## **STEP 4: Test Using PowerShell (curl commands)**

### **Save User Preference**
```powershell
curl -X POST http://localhost:8000/admin/user-preference `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "your_email@example.com",
    "key": "preferred_timezone",
    "value": "Asia/Kolkata"
  }'
```

**Expected Response:**
```json
{
  "operation": "save",
  "key": "preferred_timezone",
  "value": "Asia/Kolkata",
  "saved": true
}
```

---

### **Retrieve User Preference**
```powershell
curl -X POST http://localhost:8000/admin/user-preference `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "your_email@example.com",
    "key": "preferred_timezone"
  }'
```

**Expected Response:**
```json
{
  "operation": "retrieve",
  "key": "preferred_timezone",
  "value": "Asia/Kolkata",
  "found": true
}
```

---

### **Approve/Reject Meeting (Phase 7)**
```powershell
curl -X POST http://localhost:8000/admin/approve-meeting `
  -H "Content-Type: application/json" `
  -d '{
    "user_email": "your_email@example.com",
    "meeting_id": "meet_123",
    "action": "approve",
    "notes": "Looks good"
  }'
```

**Expected Response:**
```json
{
  "status": "updated",
  "meeting_id": "meet_123",
  "action": "approve",
  "notes": "Looks good"
}
```

---

### **Send Test Email**
```powershell
curl -X POST http://localhost:8000/admin/send-test `
  -H "Content-Type: application/json" `
  -d '{
    "to": "your_email@example.com",
    "subject": "Test from AI Agent",
    "body": "This is a test email from the AI scheduling agent.",
    "thread_id": "optional_thread_id"
  }'
```

**Expected Response:**
```json
{
  "sent": true,
  "message_id": "msg_abc123def456"
}
```

**Then check:** Your Gmail inbox for the test email ✅

---

## **STEP 5: Test Email Auto-Reply (Manual Testing)**

This is the **main feature** you need to test manually:

### **Setup:**

1. **Gmail Account:** Have 2 Gmail accounts ready
   - Account A: `your_gmail@gmail.com` (the agent's account - already authenticated with token.json)
   - Account B: `test_sender@gmail.com` (to send test emails)

2. **Agent Account Setup:**
   - Login to Account A in browser
   - Grant OAuth permissions (if not already done)
   - Gmail API enabled in Google Cloud Console

### **Test Scenario 1: Schedule Meeting (Simple)**

1. From Account B, send email to Account A with subject:
   ```
   Can we schedule a meeting tomorrow at 3 PM?
   ```

2. Wait 30 seconds, then trigger:
   ```powershell
   curl -X POST http://localhost:8000/admin/process
   ```

3. **Check these things manually:**
   - ✅ **Gmail (Account A):** Did you receive a reply email with:
     - "Meeting scheduled for tomorrow at 3 PM"
     - Google Calendar link
     - Google Meet link
     - AI disclaimer footer
   
   - ✅ **Google Calendar (Account A):** Did a new event appear?
     - Event name: "Can we schedule a meeting tomorrow at 3 PM?"
     - Time: Tomorrow at 3 PM
     - Attendees: test_sender@gmail.com (invited)
     - Meeting link: Google Meet auto-generated
   
   - ✅ **Gmail (Account A):** Is original email marked as read?

### **Test Scenario 2: Ambiguous Time (Requires Clarification)**

1. From Account B, send:
   ```
   Let's meet sometime next week?
   ```

2. Trigger:
   ```powershell
   curl -X POST http://localhost:8000/admin/process
   ```

3. **Check manually:**
   - ✅ **Gmail (Account A):** Did you get clarification email?
     ```
     "I noticed your email mentions scheduling, but I need more detail...
     Could you please specify the exact date, time, and timezone?"
     ```
   - ✅ No calendar event created (waiting for clarification)

### **Test Scenario 3: Query (Not Scheduling)**

1. From Account B, send:
   ```
   What's the status of the project?
   ```

2. Trigger:
   ```powershell
   curl -X POST http://localhost:8000/admin/process
   ```

3. **Check manually:**
   - ✅ **Gmail (Account A):** Did you get summary reply?
     ```
     "Here is a brief summary of the current status..."
     ```
   - ✅ No calendar event created

---

## **STEP 6: Check Logs for Debugging**

While server is running, watch the PowerShell output. You'll see:

```
INFO:     Processing email from friend@example.com
INFO:       -> Intent: scheduling
INFO:       -> Extracted Slots: [{'date': '2026-04-02', 'start': '15:00', 'timezone': 'UTC'}]
INFO:       -> Meeting scheduled successfully.
INFO:       -> Auto-replied with MSG ID: msg_abc123
INFO:       -> Email marked as read
```

**Key things to look for:**
- ✅ Intent detection working
- ✅ Time extraction working
- ✅ Calendar creation working
- ✅ Reply sending working
- ✅ Email mark-as-read working

If you see errors:
```
ERROR: No credentials found. Please authenticate via /auth/login
ERROR: Failed to schedule meeting: ...
ERROR: Unable to send reply: ...
```

---

## **QUICK TEST CHECKLIST**

Print this and check off as you test:

### **Part 1: Server Running**
- [ ] Server starts without errors
- [ ] http://localhost:8000/health returns 200 OK
- [ ] http://localhost:8000/ returns app info

### **Part 2: API Endpoints**
- [ ] /admin/emails shows your Gmail inbox (or appropriate error if not set up)
- [ ] /admin/process can be triggered
- [ ] /admin/user-preference saves and retrieves correctly
- [ ] /admin/smart-suggestions returns data

### **Part 3: Email Auto-Reply (MAIN TEST)**
- [ ] Send test email from another account
- [ ] Trigger /admin/process
- [ ] **Check Gmail:** Auto-reply received? ✅
- [ ] **Check Gmail:** Reply contains AI disclaimer? ✅
- [ ] **Check Gmail:** Original marked as read? ✅

### **Part 4: Calendar Booking**
- [ ] **Check Google Calendar:** New event created? ✅
- [ ] **Check event details:** Has attendees? ✅
- [ ] **Check event details:** Has Google Meet link? ✅
- [ ] **Check event attendees:** Got calendar invite? ✅

### **Part 5: Intent Detection**
- [ ] Scheduling emails → Auto-reply with calendar link ✅
- [ ] Ambiguous emails → Clarification request ✅
- [ ] Query emails → Summary reply ✅

---

## **API Endpoints Reference**

| Endpoint | Method | Test In Browser | Purpose |
|----------|--------|-----------------|---------|
| `/health` | GET | ✅ Yes | Health check |
| `/` | GET | ✅ Yes | API info |
| `/admin/emails` | GET | ✅ Yes | List Gmail emails |
| `/admin/process` | POST | ⚠️ URL, curl -X POST | Trigger pipeline |
| `/admin/user-preference` | POST | ✅ curl | Save/get preferences |
| `/admin/smart-suggestions/{email}` | GET | ✅ Yes | Get suggestions |
| `/admin/approve-meeting` | POST | ✅ curl | Approve meeting |
| `/admin/meeting-history/{email}` | GET | ✅ Yes | View history |
| `/admin/send-test` | POST | ✅ curl | Send test email |

---

## **EXPECTED BEHAVIOR**

### **When Email is Scheduling Intent:**
```
Email received: "Can we meet tomorrow at 2 PM?"
         ↓
Intent detected: "scheduling"
         ↓
Time extracted: 2026-04-02 14:00 UTC
         ↓
Calendar event created ✅
         ↓
Auto-reply sent ✅
  "Great news! I have automatically scheduled the meeting for you.
   📅 Date: 2026-04-02
   ⏰ Time: 14:00 – 15:00 UTC
   🔗 https://calendar.google.com/event
   This email was sent by an experimental AI assistant."
         ↓
Original email marked as read ✅
```

### **When Ambiguous:**
```
Email received: "Let's meet next week?"
         ↓
Intent detected: "scheduling"
         ↓
Time extraction: FAILED (ambiguous)
         ↓
Clarification email sent ✅
  "Thank you for reaching out! I need more detail...
   Could you please specify the exact date, time, and timezone?"
         ↓
NO calendar event created ⏸️
         ↓
Waiting for reply...
```

---

## **TROUBLESHOOTING**

### **"No credentials found"**
**Cause:** Gmail OAuth not set up  
**Fix:** 
```powershell
# Visit this URL to authenticate
http://localhost:8000/auth/login
```

### **"Supermemory API error"**
**Cause:** API key not configured  
**Fix:** This is OPTIONAL. App works without it.

### **"Redis connection refused"**
**Cause:** Redis server not running  
**Fix:** This is OPTIONAL. App uses in-memory cache as fallback.

### **"No emails to process"**
**Cause:** Inbox is empty  
**Fix:** Send test emails to your Gmail account

### **Email sent but no reply received**
**Check:**
1. Did /admin/process complete without errors?
2. Look at PowerShell output for error messages
3. Check email went to spam folder?
4. Is Gmail API enabled in Google Cloud Console?

---

## **SUCCESS INDICATORS**

You'll know everything is working when:

✅ GET `/health` → 200 OK  
✅ GET `/` → Returns app info  
✅ GET `/admin/emails` → Shows your emails  
✅ POST `/admin/process` → No errors  
✅ Send test email → Gets auto-reply within 30 seconds  
✅ Auto-reply has AI disclaimer  
✅ Google Calendar has new event with Meet link  
✅ Original email marked as read  

---

## **NEXT STEPS AFTER TESTING**

If everything passes manual testing:

1. ✅ You're ready for **production deployment**
2. Deploy to Railway/Render with environment variables
3. Set up Gmail Pub/Sub for real-time email processing
4. Monitor logs and gather feedback

---

**Happy Testing!** 🚀

For any issues, check:
- PowerShell output (server logs)
- Browser console (F12 → Network tab)
- Gmail spam folder
- Google Cloud Console (API quotas)
