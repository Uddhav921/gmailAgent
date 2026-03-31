"""
Auth Routes — Gmail OAuth 2.0 Flow
GET  /auth/login         → redirect to Google consent screen
GET  /auth/callback      → exchange code for tokens
GET  /auth/status        → check if authenticated
POST /auth/watch         → set up Gmail push notifications
DELETE /auth/watch       → stop Gmail push notifications
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services.gmail_service import (
    get_authorization_url,
    exchange_code_for_tokens,
    load_credentials,
    setup_gmail_watch,
    stop_gmail_watch,
)

router = APIRouter()


@router.get("/login")
def login():
    """Redirect user to Google OAuth consent screen."""
    auth_url, state = get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def oauth_callback(code: str, state: str = ""):
    """Handle OAuth callback from Google and store tokens."""
    try:
        token_data = exchange_code_for_tokens(code, state=state)
        return {
            "status": "authenticated",
            "message": "OAuth successful. Tokens saved.",
            "scopes": token_data.get("scopes", []),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get("/status")
def auth_status():
    """Check if the agent is currently authenticated."""
    creds = load_credentials()
    if creds and creds.valid:
        return {"authenticated": True, "expired": False}
    elif creds and creds.expired:
        return {"authenticated": False, "expired": True, "message": "Token expired, refresh needed"}
    return {"authenticated": False, "message": "No credentials found. Visit /auth/login"}


@router.post("/watch")
def start_watch():
    """Register Gmail push notifications via Pub/Sub."""
    result = setup_gmail_watch()
    if result:
        return {"status": "watch_started", "details": result}
    raise HTTPException(status_code=500, detail="Failed to set up Gmail watch")


@router.delete("/watch")
def end_watch():
    """Stop Gmail push notifications."""
    success = stop_gmail_watch()
    if success:
        return {"status": "watch_stopped"}
    raise HTTPException(status_code=500, detail="Failed to stop Gmail watch")
