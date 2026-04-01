"""
Memory Service — Phase 5
Provides rate limiting and short-term caching to track email intents.
Uses Redis for cache storage, falls back to in-memory store if Redis is unavailable.
"""

import time
import logging
import json
import redis
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = 20  # Max emails processed per hour per user
RATE_LIMIT_WINDOW = 3600  # 1 hour

redis_client = None
if settings.redis_url:
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        # Attempt a ping to ensure connection works
        redis_client.ping()
        logger.info("✅ Redis connected successfully.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis ({e}). Falling back to in-memory cache.")
        redis_client = None

# Fallback In-Memory store
_intent_cache = {}
_rate_limits = {}


def cache_intent(email_id: str, intent: str, ttl: int = 3600):
    """Cache the determined intent of an email."""
    if redis_client:
        try:
            redis_client.setex(f"intent:{email_id}", ttl, intent)
            return
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
    
    _intent_cache[email_id] = intent


def get_cached_intent(email_id: str) -> str | None:
    """Retrieve a cached intent for faster processing."""
    if redis_client:
        try:
            return redis_client.get(f"intent:{email_id}")
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            
    return _intent_cache.get(email_id)


def check_rate_limit(user_email: str) -> bool:
    """
    Check if a user is sending too many emails to process.
    Returns True if safe to process, False if rate limited.
    """
    if redis_client:
        key = f"rate_limit:{user_email}"
        try:
            count = redis_client.get(key)
            if count is None:
                redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
                return True
            
            if int(count) >= RATE_LIMIT_MAX:
                logger.warning(f"Rate limit exceeded for user {user_email}.")
                return False
                
            redis_client.incr(key)
            return True
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall back to in-memory on error

    # In-memory fallback
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


# ─── Supermemory API Integration (Long-term Memory) ─────────────────────────
SUPERMEMORY_API_URL = "https://api.supermemory.ai/v1"


def save_user_preference(user_email: str, key: str, value: str) -> bool:
    """
    Save a user preference to Supermemory for persistent cross-session storage.
    Examples: preferred_timezone, preferred_hours, meeting_style, etc.
    
    Args:
        user_email: User's email address (unique identifier)
        key: Preference key (e.g., "preferred_timezone")
        value: Preference value (e.g., "Asia/Kolkata")
    
    Returns:
        True if saved successfully, False otherwise.
    """
    if not settings.supermemory_api_key:
        logger.debug("Supermemory API key not configured. Skipping preference save.")
        return False
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{SUPERMEMORY_API_URL}/memory/save",
                headers={"Authorization": f"Bearer {settings.supermemory_api_key}"},
                json={
                    "user_id": user_email,
                    "memory_type": "preference",
                    "key": key,
                    "value": value,
                },
                timeout=10,
            )
            if response.status_code in (200, 201):
                logger.debug(f"Saved preference {key}={value} for user {user_email}")
                return True
            else:
                logger.warning(f"Failed to save preference: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Supermemory save error: {e}")
        return False


def get_user_preference(user_email: str, key: str) -> str | None:
    """
    Retrieve a user preference from Supermemory.
    
    Args:
        user_email: User's email address
        key: Preference key to retrieve
    
    Returns:
        The preference value, or None if not found.
    """
    if not settings.supermemory_api_key:
        logger.debug("Supermemory API key not configured. Returning None.")
        return None
    
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{SUPERMEMORY_API_URL}/memory/get",
                headers={"Authorization": f"Bearer {settings.supermemory_api_key}"},
                params={
                    "user_id": user_email,
                    "memory_type": "preference",
                    "key": key,
                },
                timeout=10,
            )
            if response.status_code == 200:
                result = response.json()
                value = result.get("value")
                logger.debug(f"Retrieved preference {key}={value} for user {user_email}")
                return value
            else:
                logger.debug(f"Preference {key} not found for user {user_email}")
                return None
    except Exception as e:
        logger.error(f"Supermemory get error: {e}")
        return None


def log_meeting_to_memory(user_email: str, meeting_summary: dict) -> bool:
    """
    Log a successfully scheduled meeting to Supermemory for learning patterns.
    Can be used later for "smart suggestions" based on meeting history.
    
    Args:
        user_email: User's email address
        meeting_summary: dict with keys: date, time, duration, participants, subject
    
    Returns:
        True if logged successfully, False otherwise.
    """
    if not settings.supermemory_api_key:
        logger.debug("Supermemory API key not configured. Skipping meeting log.")
        return False
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{SUPERMEMORY_API_URL}/memory/save",
                headers={"Authorization": f"Bearer {settings.supermemory_api_key}"},
                json={
                    "user_id": user_email,
                    "memory_type": "meeting_history",
                    "data": json.dumps(meeting_summary),
                    "timestamp": time.time(),
                },
                timeout=10,
            )
            if response.status_code in (200, 201):
                logger.debug(f"Logged meeting to memory for user {user_email}")
                return True
            else:
                logger.warning(f"Failed to log meeting: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Supermemory meeting log error: {e}")
        return False


def get_user_meeting_history(user_email: str, limit: int = 10) -> list[dict] | None:
    """
    Retrieve past meetings from Supermemory for pattern analysis.
    Useful for smart suggestions and learning preferred meeting times.
    
    Args:
        user_email: User's email address
        limit: Maximum number of past meetings to retrieve
    
    Returns:
        List of meeting dicts, or None on error.
    """
    if not settings.supermemory_api_key:
        logger.debug("Supermemory API key not configured. Returning None.")
        return None
    
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{SUPERMEMORY_API_URL}/memory/query",
                headers={"Authorization": f"Bearer {settings.supermemory_api_key}"},
                params={
                    "user_id": user_email,
                    "memory_type": "meeting_history",
                    "limit": limit,
                },
                timeout=10,
            )
            if response.status_code == 200:
                result = response.json()
                meetings = result.get("data", [])
                logger.debug(f"Retrieved {len(meetings)} past meetings for user {user_email}")
                return meetings
            else:
                logger.debug(f"No meeting history found for user {user_email}")
                return None
    except Exception as e:
        logger.error(f"Supermemory history query error: {e}")
        return None
