from __future__ import annotations

import random
import time
from typing import List, Optional

from celery import Celery

from config.celery_utils import create_celery
from scrapers.google_maps_scraper import GoogleMapsScraper
from crawlers.google_maps_crawlee import run_crawl
# MongoDB (primary) and SQLite (backup) imports
try:
    from db_mongo import save_business, get_all_businesses, get_business_count
    USE_MONGODB = True
except ImportError:
    from db import save_business, get_all_businesses, get_business_count
    USE_MONGODB = False
    print("Warning: MongoDB not available, falling back to SQLite")

celery_app: Celery = create_celery()
app = celery_app  # backwards compatibility for `celery -A app.celery_tasks.tasks worker`


@celery_app.task(bind=True, name="scrape_leads", max_retries=3)
def scrape_leads(self, query: str) -> List[dict]:
    """Legacy mock task preserved for backwards compatibility."""
    try:
        time.sleep(random.uniform(0.5, 1.5))
        return [
            {
                "business_name": f"Mock company for {query}",
                "website": "https://example.com",
                "industry": "Mock Industry",
                "country": "N/A",
                "first_name": "Sample",
                "last_name": "Lead",
                "job_title": "Placeholder",
                "phone": None,
                "linkedin_url": "https://www.linkedin.com/in/sample",
                "email": "sample.lead@example.com",
            }
        ]
    except Exception as exc:  # pragma: no cover - retry path
        raise self.retry(exc=exc, countdown=5) from exc


@celery_app.task(
    bind=True,
    name="scrape_leads_from_google_maps",
    max_retries=3,
    soft_time_limit=900,
)
def scrape_leads_from_google_maps(
    self,
    query: str,
    location: str,
    options: Optional[dict] = None,
) -> List[dict]:
    """Scrape Google Maps for businesses that match a query and location."""

    options = options or {}
    max_results = int(options.get("max_results", 25))
    headless = bool(options.get("headless", True))
    proxies = options.get("proxies")

    try:
        with GoogleMapsScraper(proxies=proxies, headless=headless) as scraper:
            leads = scraper.scrape(query=query, location=location, max_results=max_results)
        return leads
    except Exception as exc:  # pragma: no cover - retry path
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(
    bind=True,
    name="scrape_leads_from_google_maps_crawlee",
    max_retries=3,
    soft_time_limit=900,
)
def scrape_leads_from_google_maps_crawlee(
    self,
    query: str,
    location: str,
    options: Optional[dict] = None,
) -> dict:
    """
    Scrape Google Maps using Crawlee (Playwright) with anti-bot measures and DB persistence.
    
    This is the production-ready scraper that saves directly to SQLite database.
    Results are retrieved separately from the database.
    """

    options = options or {}
    max_results = int(options.get("max_results", 20))
    headless = bool(options.get("headless", True))

    try:
        # Run the Crawlee scraper
        stats = run_crawl(
            query=query,
            location=location,
            max_results=max_results,
            headless=headless,
        )
        
        # Return statistics and a sample of results
        return {
            "status": "completed",
            "stats": stats,
            "message": f"Scraped {stats.get('results_count', 0)} businesses. Check database for full results.",
        }
    except Exception as exc:  # pragma: no cover - retry path
        raise self.retry(exc=exc, countdown=30) from exc
