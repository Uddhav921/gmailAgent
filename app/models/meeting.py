"""MongoDB Meeting Model (Pydantic)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MeetingSlot(BaseModel):
    start_utc: datetime
    end_utc: datetime
    timezone: str = "UTC"


class MeetingModel(BaseModel):
    title: str
    participants: list[str]           # List of email addresses
    slot: MeetingSlot
    calendar_event_id: Optional[str] = None
    calendar_event_link: Optional[str] = None
    status: str = "pending"          # pending | confirmed | cancelled
    trigger_email_id: str = ""       # Original email that triggered this
    trigger_thread_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    booked_at: Optional[datetime] = None
