"""
AI Email Agent — Configuration
Loads all environment variables via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ─── Google OAuth ────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # ─── Gemini LLM ──────────────────────────────────────────────
    gemini_api_key: str = ""

    # ─── MongoDB ─────────────────────────────────────────────────
    mongo_uri: str = "mongodb://localhost:27017/gmailAgent"

    # ─── Redis ───────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"

    # ─── Supermemory ─────────────────────────────────────────────
    supermemory_api_key: str = ""

    # ─── App ─────────────────────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # ─── Gmail Pub/Sub ───────────────────────────────────────────
    pubsub_topic: str = ""
    gmail_webhook_secret: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


settings = get_settings()
