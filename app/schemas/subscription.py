import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SubscribeRequest(BaseModel):
    """Request body for POST /subscriptions."""

    email: str
    tags_filter: list[str] | None = Field(
        None, description="Only receive jobs matching ANY of these tags"
    )
    min_salary: int | None = Field(None, ge=0, description="Minimum salary filter")

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        v = v.lower().strip()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v


class SubscriptionResponse(BaseModel):
    """API response for a single subscription."""

    id: uuid.UUID
    email: str
    tags_filter: list[str] | None
    min_salary: int | None
    is_active: bool
    created_at: datetime


class DigestResult(BaseModel):
    """Returned by send_digest task."""

    subscriptions_processed: int
    emails_sent: int
