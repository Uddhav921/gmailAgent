"""
Gmail Service — Phase 2
Handles:
  - OAuth 2.0 token management (store/load/refresh)
  - Fetching unread emails via Gmail API
  - Parsing email body, sender, recipients, subject
  - Sending reply emails with AI disclaimer
  - Setting up Gmail Pub/Sub push notifications
"""

import os
import base64
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import html2text

from app.config import settings

logger = logging.getLogger(__name__)

# Gmail API scopes required
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

AI_DISCLAIMER = "\n\n---\nThis email was sent by an experimental AI assistant."

# ─── Token Management ────────────────────────────────────────────────────────

TOKEN_PATH = "token.json"

# In-memory store: state → Flow (preserves PKCE code_verifier between login & callback)
_flow_store: dict = {}


def create_oauth_flow() -> Flow:
    """Create an OAuth2 flow from client secrets."""
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    return flow


def get_authorization_url() -> tuple[str, str]:
    """Return OAuth authorization URL and state token."""
    flow = create_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        use_code_verifier=False,  # Disable PKCE for backend server
    )
    # Store flow for callback processing
    _flow_store[state] = flow
    logger.info(f"Created OAuth flow with state: {state}")
    return auth_url, state


def exchange_code_for_tokens(code: str, state: str = "") -> dict:
    """Exchange authorization code for access/refresh tokens."""
    # Retrieve the stored flow using the state parameter
    flow = _flow_store.pop(state, None) or create_oauth_flow()
    
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        # Persist token locally
        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f)
        logger.info("Token saved successfully")
        return token_data
    except Exception as e:
        logger.error(f"Token exchange failed: {str(e)}")
        raise


def load_credentials() -> Optional[Credentials]:
    """Load credentials from token file, refresh if expired."""
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH, "r") as f:
        token_data = json.load(f)
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", settings.google_client_id),
        client_secret=token_data.get("client_secret", settings.google_client_secret),
        scopes=token_data.get("scopes", SCOPES),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        token_data["token"] = creds.token
        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f)
    return creds


def get_gmail_service():
    """Return an authenticated Gmail API service client."""
    creds = load_credentials()
    if not creds:
        raise ValueError("No credentials found. Please authenticate via /auth/login")
    return build("gmail", "v1", credentials=creds)


# ─── Email Fetching ──────────────────────────────────────────────────────────

def fetch_unread_emails(max_results: int = 10) -> list[dict]:
    """
    Fetch unread emails from the Gmail inbox.
    Returns a list of parsed email dicts.
    """
    service = get_gmail_service()
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=["INBOX", "UNREAD"],
            maxResults=max_results,
        ).execute()
        messages = result.get("messages", [])
        emails = []
        for msg in messages:
            parsed = get_email_by_id(msg["id"])
            if parsed:
                emails.append(parsed)
        return emails
    except HttpError as e:
        logger.error(f"Failed to fetch emails: {e}")
        return []


def get_email_by_id(message_id: str) -> Optional[dict]:
    """Fetch a single email by ID and parse it."""
    service = get_gmail_service()
    try:
        msg = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()
        return parse_email_message(msg)
    except HttpError as e:
        logger.error(f"Failed to get email {message_id}: {e}")
        return None


def get_email_thread(thread_id: str) -> list[dict]:
    """
    Fetch all messages in a Gmail thread.
    Returns list of parsed email dicts in chronological order.
    """
    service = get_gmail_service()
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="full",
        ).execute()
        messages = thread.get("messages", [])
        return [parse_email_message(m) for m in messages]
    except HttpError as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        return []


# ─── Email Parsing ───────────────────────────────────────────────────────────

def parse_email_message(msg: dict) -> dict:
    """
    Parse a raw Gmail API message into a clean dict.
    Returns: {id, thread_id, subject, sender, recipients, body, date, labels}
    """
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

    body = _extract_body(msg.get("payload", {}))

    return {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "subject": headers.get("Subject", "(No Subject)"),
        "sender": headers.get("From", ""),
        "recipients": _parse_recipients(headers),
        "body": body,
        "date": headers.get("Date", ""),
        "labels": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text from email payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        html_content = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        converter = html2text.HTML2Text()
        converter.ignore_links = True
        return converter.handle(html_content).strip()

    # Multipart: recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        extracted = _extract_body(part)
        if extracted:
            return extracted
    return ""


def _parse_recipients(headers: dict) -> list[str]:
    """Extract all recipient emails from To, Cc, Bcc headers."""
    recipients = []
    for field in ["To", "Cc", "Bcc"]:
        value = headers.get(field, "")
        if value:
            # Handle comma-separated list
            for addr in value.split(","):
                addr = addr.strip()
                if addr:
                    recipients.append(addr)
    return recipients


# ─── Email Sending ───────────────────────────────────────────────────────────

def send_reply(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    cc: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Send an email reply via Gmail API.
    Automatically appends the AI disclaimer.
    Returns the sent message ID or None on failure.
    """
    service = get_gmail_service()

    # Get sender's email address
    profile = service.users().getProfile(userId="me").execute()
    sender_email = profile.get("emailAddress", "me")

    full_body = body + AI_DISCLAIMER

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    if cc:
        msg["Cc"] = ", ".join(cc)

    msg.attach(MIMEText(full_body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    send_payload = {"raw": raw}
    if thread_id:
        send_payload["threadId"] = thread_id

    try:
        sent = service.users().messages().send(
            userId="me",
            body=send_payload,
        ).execute()
        logger.info(f"Email sent. ID: {sent['id']}")
        return sent["id"]
    except HttpError as e:
        logger.error(f"Failed to send email: {e}")
        raise  # Re-raise so callers see the real error


# ─── Mark Email as Read ──────────────────────────────────────────────────────

def mark_as_read(message_id: str) -> bool:
    """Remove UNREAD label from a Gmail message."""
    service = get_gmail_service()
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True
    except HttpError as e:
        logger.error(f"Failed to mark message {message_id} as read: {e}")
        return False


# ─── Gmail Pub/Sub Setup ─────────────────────────────────────────────────────

def setup_gmail_watch() -> Optional[dict]:
    """
    Register Gmail push notifications via Google Pub/Sub.
    Must be called once (or re-called every 7 days to renew).
    Returns watch response with expiration timestamp.
    """
    service = get_gmail_service()
    try:
        watch_response = service.users().watch(
            userId="me",
            body={
                "topicName": settings.pubsub_topic,
                "labelIds": ["INBOX"],
                "labelFilterAction": "include",
            },
        ).execute()
        logger.info(f"Gmail watch set up: {watch_response}")
        return watch_response
    except HttpError as e:
        logger.error(f"Failed to set up Gmail watch: {e}")
        return None


def stop_gmail_watch() -> bool:
    """Stop Gmail push notifications."""
    service = get_gmail_service()
    try:
        service.users().stop(userId="me").execute()
        return True
    except HttpError as e:
        logger.error(f"Failed to stop Gmail watch: {e}")
        return False
