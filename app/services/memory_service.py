"""
Memory Service — Phase 5
Provides rate limiting and short-term caching to track email intents.
Currently implements a basic in-memory dictionary fallback.
"""

import time
import logging

logger = logging.getLogger(__name__)

# Basic In-Memory store for Intent tracking and Rate Limiting
# { email_id: "intent" }
_intent_cache = {}

# { user_email: {"count": X, "reset_at": timestamp} }
_rate_limits = {}

RATE_LIMIT_MAX = 20  # Max emails processed per hour per user
RATE_LIMIT_WINDOW = 3600  # 1 hour


def cache_intent(email_id: str, intent: str):
    """Cache the determined intent of an email."""
    _intent_cache[email_id] = intent


def get_cached_intent(email_id: str) -> str | None:
    """Retrieve a cached intent for faster processing."""
    return _intent_cache.get(email_id)


def check_rate_limit(user_email: str) -> bool:
    """
    Check if a user is sending too many emails to process.
    Returns True if safe to process, False if rate limited.
    """
    now = time.time()
    
    if user_email not in _rate_limits:
        _rate_limits[user_email] = {"count": 1, "reset_at": now + RATE_LIMIT_WINDOW}
        return True
        
    user_state = _rate_limits[user_email]
    
    if now > user_state["reset_at"]:
        # Reset window
        user_state["count"] = 1
        user_state["reset_at"] = now + RATE_LIMIT_WINDOW
        return True
        
    if user_state["count"] >= RATE_LIMIT_MAX:
        logger.warning(f"Rate limit exceeded for user {user_email}.")
        return False
        
    user_state["count"] += 1
    return True
