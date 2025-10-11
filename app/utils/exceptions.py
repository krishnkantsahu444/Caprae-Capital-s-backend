"""Custom exceptions for the lead generation system."""


class CaptchaDetectedError(Exception):
    """Raised when a CAPTCHA is detected during scraping."""
    pass


class RateLimitError(Exception):
    """Raised when rate limiting is triggered."""
    pass


class DetailPageEnrichmentError(Exception):
    """Raised when detail page enrichment fails after all retries."""
    pass
