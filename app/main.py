from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    configure_logging()

    app = FastAPI(
        title="Scraper Pipeline API",
        description="Aggregates remote developer job listings from multiple job boards.",
        version="0.1.0",
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
