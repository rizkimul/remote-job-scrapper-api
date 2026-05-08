import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DedupKey(Base, TimestampMixin):
    """SHA256 hash of normalized (company + title + description[:200]).

    One-to-one with Job. Created atomically with the job to prevent duplicates.
    """

    __tablename__ = "dedup_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # SHA256 hex digest = 64 chars
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id"), unique=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id"), index=True
    )

    job: Mapped["Job"] = relationship(back_populates="dedup_key")
