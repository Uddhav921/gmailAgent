"""MongoDB User Model (Pydantic)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    email: str
    name: Optional[str] = None
    timezone: str = "UTC"
    preferred_hours_start: int = 9       # e.g. 9 AM
    preferred_hours_end: int = 18        # e.g. 6 PM
    calendar_id: str = "primary"
    supermemory_user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    preferred_hours_start: Optional[int] = None
    preferred_hours_end: Optional[int] = None
    calendar_id: Optional[str] = None
