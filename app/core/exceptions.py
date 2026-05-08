class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ScrapeError(AppError):
    """Base exception for scraping errors."""


class RateLimitError(ScrapeError):
    """Source is rate-limiting our requests."""


class BlockedError(ScrapeError):
    """Source is blocking our scraper (IP ban, CAPTCHA, etc.)."""


class ParseError(ScrapeError):
    """HTML/JSON parsing failed for a source page."""
