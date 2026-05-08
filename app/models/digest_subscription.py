import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DigestSubscription(Base, TimestampMixin):
    """User opt-in for daily job digest emails."""

    __tablename__ = "digest_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # RFC 5321 max email length is 254 chars
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    tags_filter: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    min_salary: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sends: Mapped[list["DigestSend"]] = relationship(back_populates="subscription")
