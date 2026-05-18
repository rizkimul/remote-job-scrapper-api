from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.digest_subscription import DigestSubscription
    from app.models.job import Job


class DigestSend(Base, TimestampMixin):
    """Idempotency log — one row per (subscriber, job) pair that was emailed.

    Unique constraint prevents resending the same job to the same subscriber.
    """

    __tablename__ = "digest_sends"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "job_id", name="uq_digest_send_subscription_job"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("digest_subscriptions.id"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    subscription: Mapped[DigestSubscription] = relationship(back_populates="sends")
    job: Mapped[Job] = relationship(back_populates="digest_sends")
