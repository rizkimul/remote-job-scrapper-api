# Project: Scraper Pipeline API

## Purpose

A production-grade web scraping and data pipeline platform exposed as a REST API.
Built as a freelance portfolio project to showcase backend, async, and data
engineering skills. The author is a Python backend dev with 2 years of experience,
learning while building.

Domain: Aggregates remote developer job listings from multiple public job boards
(e.g., RemoteOK, We Work Remotely, Remotive) into a unified, deduplicated, queryable
API with daily digest emails.

## Tech Stack

- Python 3.12+
- FastAPI (async) — public API layer
- Playwright + httpx — scraping (Playwright for JS-heavy pages, httpx for static HTML)
- BeautifulSoup4 / selectolax — HTML parsing
- SQLAlchemy 2.0 (async) with asyncpg driver
- PostgreSQL 16 — primary store, with full-text search for job queries
- Alembic — migrations
- Redis 7 — cache + Celery broker + dedup bloom filter
- Celery + Celery Beat — scraping jobs scheduler and worker pool
- Pytest + pytest-asyncio + respx (HTTP mocking) — testing
- Docker + docker-compose
- structlog — structured logging
- Pydantic Settings — config

## Architecture

Layered architecture, strictly enforced:

app/
routers/ → HTTP layer, request/response only
services/ → business logic, orchestration
repositories/ → data access, all SQLAlchemy queries live here
models/ → SQLAlchemy ORM models
schemas/ → Pydantic DTOs (API contracts)
scrapers/ → one module per source site
base.py → abstract BaseScraper class
remoteok.py → concrete scraper
wwr.py → concrete scraper
remotive.py → concrete scraper
pipelines/ → ETL stages: extract → normalize → deduplicate → store
workers/ → Celery tasks (scrape_source, send_digest, cleanup_stale)
core/ → config, db, redis, logging, exceptions

Routers must NEVER import models or run queries directly.
Services must NEVER import SQLAlchemy session methods directly — go through repositories.
Scrapers must NEVER write to the DB directly — they return raw items to the pipeline.

## Domain Model (start here)

Core entities:

- Source: a job board we scrape (RemoteOK, WWR, Remotive)
- ScrapeRun: a single execution of a scraper, with status, started_at, ended_at, items_found
- Job: a normalized job listing (title, company, description, salary, tags, posted_at, source_url)
- DedupKey: hash of normalized (company + title + first 200 chars description) for cross-source dedup
- DigestSubscription: email + filters (tags, min_salary, etc.) for daily digest
- DigestSend: log of which jobs went to which subscriber (idempotency)

## Conventions

- All I/O is async. No sync DB calls.
- Type hints on every function signature. mypy strict mode.
- Docstrings on all public functions (Google style).
- Pydantic v2 syntax only.
- Use `Annotated[X, Depends(...)]` for FastAPI dependencies.
- Custom exceptions inherit from `app.core.exceptions.AppError`.
- Scrapers raise `ScrapeError` subclasses (RateLimitError, BlockedError, ParseError).
- Endpoints return Pydantic schemas, never ORM models.
- Use structlog with bound context (source, scrape_run_id) for every scrape log line.

## Scraping Discipline (IMPORTANT)

- Respect robots.txt — check before every new source.
- Set a clear, identifiable User-Agent that includes contact info or project URL.
- Implement polite delays (configurable per source, default 2-5s between requests).
- Cache responses for development (using respx fixtures or VCR).
- Always implement exponential backoff with jitter on retries.
- Never scrape sites that explicitly forbid it in ToS.
- Public job listings only. No scraping behind login walls.
- Document each source's scrape policy in `scrapers/<source>/README.md`.

## Git Workflow

- Conventional Commits required: feat/fix/refactor/test/docs/chore/perf/ci(scope): msg
- Feature branches off `develop`, off `main`
- After every small logical unit (model+migration, scraper+test, single endpoint, pipeline stage),
  STOP and tell me the exact commit command. Do not bundle features.

## Teaching Mode

- Before writing code, briefly explain WHY (1-3 sentences max).
- Flag idiomatic patterns I should learn (Strategy pattern for scrapers, Bloom filter for dedup,
  CQRS-lite for read vs write paths, etc.).
- When multiple approaches exist, give the trade-offs.
- Suggest concepts I should research independently.
- At the end of each feature, offer to quiz me with 3 questions to check understanding.

## Things to NEVER Do

- Never put business logic in routers.
- Never put SQL queries outside repositories.
- Never put scraping logic outside the scrapers/ folder.
- Never hardcode secrets — always Pydantic Settings + .env.
- Never write sync database code.
- Never skip writing tests for service-layer or pipeline logic.
- Never scrape without rate limiting and proper error handling.
- Never store raw HTML long-term — extract, normalize, then discard.
- Never generate huge code dumps — one logical unit at a time.

## Reference Commands

- Run app: `docker compose up`
- Run tests: `docker compose exec app pytest`
- Run a single scraper manually: `docker compose exec app python -m app.scrapers.remoteok`
- Trigger Celery scrape job: `docker compose exec app celery -A app.workers call scrape_source --args='["remoteok"]'`
- Make migration: `docker compose exec app alembic revision --autogenerate -m "msg"`
- Apply migration: `docker compose exec app alembic upgrade head`

## Build Order (track progress)

- [ ] 1. Project scaffold + Docker Compose (app, postgres, redis, celery worker, celery beat)
- [ ] 2. DB foundation: models for Source, ScrapeRun, Job, DedupKey, alembic setup
- [ ] 3. BaseScraper abstract class + first concrete scraper (RemoteOK)
- [ ] 4. Pipeline: extract → normalize → deduplicate → store
- [ ] 5. Celery integration: scheduled scrape job per source
- [ ] 6. Public API: GET /jobs with filters (tags, salary, search), pagination
- [ ] 7. Second + third scrapers (WWR, Remotive) — proves abstraction works
- [ ] 8. Digest subscriptions: subscribe endpoint + daily Celery task
- [ ] 9. Admin/stats endpoints: scrape success rate, items per source per day
- [ ] 10. Comprehensive tests (target 70%+ coverage)
- [ ] 11. GitHub Actions CI pipeline
- [ ] 12. Portfolio-quality README with Mermaid architecture diagram
