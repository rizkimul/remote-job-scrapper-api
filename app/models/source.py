import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Source(Base, TimestampMixin):
    """A job board we scrape. Seed data — not user-created."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_interval_hours: Mapped[int] = mapped_column(Integer, default=24)

    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="source")
    jobs: Mapped[list["Job"]] = relationship(back_populates="source")
