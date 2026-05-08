import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScrapeRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ScrapeRun(Base, TimestampMixin):
    """One execution of a scraper for one source."""

    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id"), index=True
    )
    status: Mapped[ScrapeRunStatus] = mapped_column(
        SAEnum(ScrapeRunStatus, name="scraperunstatus"),
        default=ScrapeRunStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_stored: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    source: Mapped["Source"] = relationship(back_populates="scrape_runs")
    jobs: Mapped[list["Job"]] = relationship(back_populates="scrape_run")
