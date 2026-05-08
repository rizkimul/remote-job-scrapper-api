import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """Normalized job listing. Cross-source unified schema."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_tags", "tags", postgresql_using="gin"),
        Index("ix_jobs_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_url: Mapped[str] = mapped_column(String(2000), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Populated by the store pipeline stage; queried with to_tsvector in repo layer
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    scrape_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scrape_runs.id"))

    source: Mapped["Source"] = relationship(back_populates="jobs")
    scrape_run: Mapped["ScrapeRun"] = relationship(back_populates="jobs")
    dedup_key: Mapped["DedupKey | None"] = relationship(
        back_populates="job", uselist=False
    )
    digest_sends: Mapped[list["DigestSend"]] = relationship(back_populates="job")
