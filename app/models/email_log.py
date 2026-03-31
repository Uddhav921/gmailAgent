"""MongoDB Email Log Model (Pydantic)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmailLogModel(BaseModel):
    email_id: str
    thread_id: str
    sender: str
    recipients: list[str]
    subject: str
    detected_intent: Optional[str] = None     # scheduling | query | clarification | unknown
    extracted_slots: Optional[list] = None    # Raw parsed time slots
    action_taken: Optional[str] = None        # booked | replied | clarified | human_review
    meeting_id: Optional[str] = None          # If a meeting was booked
    reply_sent: bool = False
    reply_message_id: Optional[str] = None
    error: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
