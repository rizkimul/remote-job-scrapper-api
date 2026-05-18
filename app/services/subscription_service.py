import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.digest_subscription import DigestSubscription
from app.models.job import Job
from app.repositories.digest_send_repository import DigestSendRepository
from app.repositories.job_repository import JobRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import DigestResult, SubscriptionResponse

log = structlog.get_logger()

_DIGEST_WINDOW_HOURS = 25   # slightly more than 24h to avoid edge-case gaps
_DIGEST_MAX_JOBS = 50       # cap jobs per email to avoid huge emails


class SubscriptionService:
    """Handles subscribe/unsubscribe and daily digest email dispatch."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sub_repo = SubscriptionRepository(session)
        self._job_repo = JobRepository(session)
        self._send_repo = DigestSendRepository(session)

    async def subscribe(
        self,
        email: str,
        tags_filter: list[str] | None,
        min_salary: int | None,
    ) -> SubscriptionResponse:
        """Create or reactivate a digest subscription.

        Idempotent — calling with an existing email updates filters and reactivates.

        Args:
            email: Normalised subscriber email.
            tags_filter: Optional tag filter.
            min_salary: Optional minimum salary filter.

        Returns:
            SubscriptionResponse for the created/updated subscription.
        """
        sub = await self._sub_repo.create_or_reactivate(email, tags_filter, min_salary)
        await self._session.commit()
        return _map_subscription(sub)

    async def unsubscribe(self, email: str) -> bool:
        """Deactivate a subscription (soft delete).

        Args:
            email: Email address to unsubscribe.

        Returns:
            True if found and deactivated, False if not found.
        """
        found = await self._sub_repo.deactivate(email)
        if found:
            await self._session.commit()
        return found

    async def send_all_digests(self) -> DigestResult:
        """Send digest emails to all active subscribers.

        Called by the send_digest Celery task daily. For each subscriber:
        1. Fetch jobs from the last 25h matching their filters.
        2. Exclude jobs already sent (DigestSend idempotency log).
        3. If new jobs exist: build email, send, record sends.

        Returns:
            DigestResult with counts of processed subscriptions and emails sent.
        """
        subs = await self._sub_repo.get_all_active()
        emails_sent = 0

        for sub in subs:
            sent = await self._send_for_subscription(sub)
            emails_sent += sent

        log.info("digest_complete", subscriptions=len(subs), emails_sent=emails_sent)
        return DigestResult(subscriptions_processed=len(subs), emails_sent=emails_sent)

    async def _send_for_subscription(self, sub: DigestSubscription) -> int:
        since = datetime.now(tz=UTC) - timedelta(hours=_DIGEST_WINDOW_HOURS)

        candidate_jobs, _ = await self._job_repo.list_jobs(
            tags=sub.tags_filter,
            salary_min=sub.min_salary,
            since=since,
            page=1,
            page_size=_DIGEST_MAX_JOBS,
        )
        if not candidate_jobs:
            return 0

        sent_ids = await self._send_repo.get_sent_job_ids(sub.id)
        new_jobs = [j for j in candidate_jobs if j.id not in sent_ids]
        if not new_jobs:
            return 0

        plural = "s" if len(new_jobs) > 1 else ""
        subject = f"Daily Remote Job Digest — {len(new_jobs)} new job{plural}"
        body = _build_email_body(new_jobs)

        _send_email(to=sub.email, subject=subject, body=body)

        now = datetime.now(tz=UTC)
        await self._send_repo.record_sends(sub.id, [j.id for j in new_jobs], now)
        await self._session.commit()

        log.info("digest_sent", email=sub.email, jobs_count=len(new_jobs))
        return 1


def _map_subscription(sub: DigestSubscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        email=sub.email,
        tags_filter=sub.tags_filter,
        min_salary=sub.min_salary,
        is_active=sub.is_active,
        created_at=sub.created_at,
    )


def _build_email_body(jobs: list[Job]) -> str:
    lines = [
        "Here are the latest remote jobs matching your preferences:",
        "",
    ]
    for i, job in enumerate(jobs, start=1):
        salary = ""
        if job.salary_min and job.salary_max:
            salary = f"   Salary: ${job.salary_min:,}–${job.salary_max:,} {job.currency}\n"
        elif job.salary_min:
            salary = f"   Salary: ${job.salary_min:,}+ {job.currency}\n"

        tags = f"   Tags: {', '.join(job.tags)}\n" if job.tags else ""

        lines.append(
            f"{i}. {job.title} at {job.company}\n"
            f"{tags}"
            f"{salary}"
            f"   {job.source_url}"
        )
        lines.append("")

    lines.append("---")
    lines.append("Unsubscribe: DELETE /subscriptions/{your-email}")
    return "\n".join(lines)


def _send_email(to: str, subject: str, body: str) -> None:
    """Send email via SMTP. Logs and skips if smtp_host is not configured."""
    if not settings.smtp_host:
        log.info("email_skipped_no_smtp_configured", to=to, subject=subject)
        return

    msg = MIMEMultipart()
    msg["From"] = settings.digest_from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except smtplib.SMTPException as exc:
        log.error("email_send_failed", to=to, error=str(exc))
