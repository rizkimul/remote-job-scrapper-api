import hashlib

from selectolax.parser import HTMLParser

from app.schemas.normalized_job import NormalizedJob
from app.schemas.scraper import RawJobItem


def normalize_items(items: list[RawJobItem]) -> list[NormalizedJob]:
    """Transform raw scraper output into normalized pipeline items.

    Strips HTML from descriptions, normalizes tags, computes dedup hash.
    Pure function — no I/O, no side effects.

    Args:
        items: Raw items from a scraper.

    Returns:
        Normalized items ready for the deduplicate stage.
    """
    return [_normalize_one(item) for item in items]


def _normalize_one(item: RawJobItem) -> NormalizedJob:
    description = _strip_html(item.description)
    tags = _normalize_tags(item.tags)
    dedup_hash = _compute_dedup_hash(item.company, item.title, description)

    return NormalizedJob(
        title=item.title.strip(),
        company=item.company.strip(),
        description=description,
        tags=tags,
        salary_min=item.salary_min,
        salary_max=item.salary_max,
        currency=item.currency,
        posted_at=item.posted_at,
        source_url=item.source_url,
        source_name=item.source_name,
        dedup_hash=dedup_hash,
    )


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return HTMLParser(text).text(separator=" ", strip=True)


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        normalized = tag.lower().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _compute_dedup_hash(company: str, title: str, description: str) -> str:
    """SHA-256 of pipe-joined normalized (company, title, description[:200]).

    Using first 200 chars of description mirrors DedupKey model intent:
    minor description edits (typo fixes, added links) should not create duplicate jobs.
    """
    parts = "|".join([
        company.lower().strip(),
        title.lower().strip(),
        description[:200].lower().strip(),
    ])
    return hashlib.sha256(parts.encode()).hexdigest()
