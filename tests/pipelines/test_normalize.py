from datetime import UTC, datetime

from app.pipelines.normalize import (
    _compute_dedup_hash,
    _normalize_tags,
    _strip_html,
    normalize_items,
)
from app.schemas.scraper import RawJobItem

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_raw(**overrides) -> RawJobItem:
    defaults = dict(
        title="Senior Python Dev",
        company="Acme Corp",
        description="<p>Great job</p>",
        tags=["Python", "FastAPI", "remote"],
        salary_min=80000,
        salary_max=120000,
        currency="USD",
        posted_at=_NOW,
        source_url="https://remoteok.com/jobs/123",
        source_name="remoteok",
    )
    return RawJobItem(**{**defaults, **overrides})


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_empty_string():
    assert _strip_html("") == ""


def test_strip_html_plain_text_unchanged():
    assert _strip_html("no html here") == "no html here"


def test_normalize_tags_lowercased():
    assert _normalize_tags(["Python", "FASTAPI"]) == ["python", "fastapi"]


def test_normalize_tags_deduplicates():
    assert _normalize_tags(["python", "Python", "PYTHON"]) == ["python"]


def test_normalize_tags_strips_whitespace():
    assert _normalize_tags([" python ", "fastapi "]) == ["python", "fastapi"]


def test_normalize_tags_drops_empty():
    assert _normalize_tags(["python", "", "  "]) == ["python"]


def test_normalize_tags_preserves_order():
    result = _normalize_tags(["fastapi", "python", "async"])
    assert result == ["fastapi", "python", "async"]


def test_dedup_hash_is_deterministic():
    h1 = _compute_dedup_hash("Acme", "Dev", "description")
    h2 = _compute_dedup_hash("Acme", "Dev", "description")
    assert h1 == h2


def test_dedup_hash_is_64_chars():
    h = _compute_dedup_hash("Acme", "Dev", "description")
    assert len(h) == 64


def test_dedup_hash_differs_for_different_company():
    h1 = _compute_dedup_hash("Acme", "Dev", "desc")
    h2 = _compute_dedup_hash("Beta", "Dev", "desc")
    assert h1 != h2


def test_dedup_hash_case_insensitive():
    h1 = _compute_dedup_hash("ACME", "Senior Dev", "desc")
    h2 = _compute_dedup_hash("acme", "senior dev", "desc")
    assert h1 == h2


def test_dedup_hash_uses_only_first_200_chars_of_description():
    base = "x" * 200
    h1 = _compute_dedup_hash("Acme", "Dev", base + "different suffix")
    h2 = _compute_dedup_hash("Acme", "Dev", base + "another suffix")
    assert h1 == h2


def test_normalize_items_strips_html():
    items = [_make_raw(description="<p>Hello <b>world</b></p>")]
    result = normalize_items(items)
    assert result[0].description == "Hello world"


def test_normalize_items_normalizes_tags():
    items = [_make_raw(tags=["Python", "PYTHON", "fastapi"])]
    result = normalize_items(items)
    assert result[0].tags == ["python", "fastapi"]


def test_normalize_items_sets_dedup_hash():
    items = [_make_raw()]
    result = normalize_items(items)
    assert len(result[0].dedup_hash) == 64


def test_normalize_items_preserves_salary():
    items = [_make_raw(salary_min=80000, salary_max=120000)]
    result = normalize_items(items)
    assert result[0].salary_min == 80000
    assert result[0].salary_max == 120000


def test_normalize_items_handles_none_salary():
    items = [_make_raw(salary_min=None, salary_max=None)]
    result = normalize_items(items)
    assert result[0].salary_min is None
    assert result[0].salary_max is None


def test_normalize_items_returns_empty_for_empty_input():
    assert normalize_items([]) == []
