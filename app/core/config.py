from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = "changeme"

    database_url: str = "postgresql+asyncpg://scraper:scraper@postgres:5432/scraper_db"
    postgres_user: str = "scraper"
    postgres_password: str = "scraper"
    postgres_db: str = "scraper_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_url: str = "redis://redis:6379/0"

    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    scrape_delay_min: float = 2.0
    scrape_delay_max: float = 5.0
    scrape_user_agent: str = (
        "ScraperPipelineAPI/1.0 (+https://github.com/rizkimul/scraper-pipeline-api)"
    )

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    digest_from_email: str = ""


settings = Settings()
