"""Google Maps Crawlee Playwright spider with anti-bot measures and DB persistence."""
import asyncio
from typing import Optional, List, Dict
from urllib.parse import quote_plus

from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from playwright.async_api import Page

from parsers import parse_card_html, parse_detail_page
# MongoDB (primary) and SQLite (backup) imports
try:
    from db_mongo import save_business, business_exists
except ImportError:
    from db import save_business, business_exists
    print("Warning: MongoDB not available, using SQLite")

from utils.anti_bot import Rotation, load_lines, DEFAULT_USER_AGENTS
from utils.config import (
    PROXY_LIST_PATH,
    USER_AGENTS_PATH,
    HEADLESS,
    MAX_REQUESTS_PER_CRAWL,
    MIN_DELAY_MS,
    MAX_DELAY_MS,
    resolve_path,
)


class GoogleMapsCrawlee:
    """Crawlee-based Google Maps scraper with Playwright."""

    def __init__(
        self,
        query: str,
        location: str,
        max_results: int = 20,
        headless: bool = HEADLESS,
        use_proxies: bool = True,
    ):
        self.query = query
        self.location = location
        self.max_results = max_results
        self.headless = headless
        self.use_proxies = use_proxies
        self.results_count = 0

        # Load proxies and user agents
        proxies = []
        if use_proxies:
            proxy_path = resolve_path(PROXY_LIST_PATH)
            proxies = load_lines(str(proxy_path))

        ua_path = resolve_path(USER_AGENTS_PATH)
        user_agents = load_lines(str(ua_path)) or DEFAULT_USER_AGENTS

        self.rotation = Rotation(proxies=proxies, user_agents=user_agents)

    def build_search_url(self) -> str:
        """Build Google Maps search URL from query and location."""
        search_term = f"{self.query} {self.location}"
        encoded = quote_plus(search_term)
        return f"https://www.google.com/maps/search/{encoded}"

    async def check_for_blocking(self, page: Page) -> bool:
        """Check if the page shows blocking/CAPTCHA."""
        content = await page.content()
        content_lower = content.lower()

        blocking_indicators = [
            "unusual traffic",
            "captcha",
            "sorry",
            "automated requests",
            "verify you're not a robot",
        ]

        for indicator in blocking_indicators:
            if indicator in content_lower:
                return True
        return False

    async def scroll_results_panel(self, page: Page, max_scrolls: int = 10):
        """Scroll the results panel to load lazy-loaded content."""
        # Try to find the scrollable results panel
        panel_selectors = [
            "div[role='feed']",  # Common results feed
            "div.m6QErb",  # Results container
            "div[aria-label*='Results']",
        ]

        panel = None
        for selector in panel_selectors:
            try:
                panel = await page.query_selector(selector)
                if panel:
                    break
            except Exception:
                continue

        if not panel:
            # Fallback: scroll the entire page
            for _ in range(max_scrolls):
                await page.keyboard.press("PageDown")
                await page.wait_for_timeout(self.rotation.random_delay_ms(500, 1000))
            return

        # Scroll within the panel
        for i in range(max_scrolls):
            try:
                await panel.evaluate("element => element.scrollBy(0, element.clientHeight)")
                await page.wait_for_timeout(self.rotation.random_delay_ms(500, 1000))

                # Check if we've reached the end
                scroll_height = await panel.evaluate("element => element.scrollHeight")
                scroll_top = await panel.evaluate("element => element.scrollTop")
                client_height = await panel.evaluate("element => element.clientHeight")

                if scroll_top + client_height >= scroll_height - 100:
                    break
            except Exception:
                break

    async def enrich_with_detail_page(self, page: Page, business: Dict):
        """Visit business detail page to extract website and additional info."""
        url = business.get("google_maps_url")
        if not url:
            return

        try:
            # Navigate to detail page
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.rotation.random_delay_ms(1000, 2000))

            # Parse detail page
            html = await page.content()
            detail_data = parse_detail_page(html)

            # Merge enriched data
            business.update(detail_data)

        except Exception as e:
            print(f"Error enriching business {business.get('name')}: {e}")

    async def handle_page(self, context: PlaywrightCrawlingContext):
        """Handle each page crawled by Crawlee."""
        page = context.page

        # Check for blocking
        if await self.check_for_blocking(page):
            raise Exception("Blocked by Google - CAPTCHA or unusual traffic detected")

        # Wait for results to load
        try:
            await page.wait_for_selector("div[role='feed'], div.Nv2PK, a.hfpxzc", timeout=10000)
        except Exception:
            print("Warning: Results selector not found, proceeding anyway")

        # Scroll to load more results
        await self.scroll_results_panel(page, max_scrolls=8)

        # Parse the page
        html = await page.content()
        businesses = parse_card_html(html)

        print(f"Found {len(businesses)} businesses on page")

        # Process each business
        for business in businesses:
            if self.results_count >= self.max_results:
                break

            # Check if already exists in DB
            if business.get("google_maps_url") and business_exists(business["google_maps_url"]):
                print(f"Skipping duplicate: {business.get('name')}")
                continue

            # Enrich with detail page if URL exists
            if business.get("google_maps_url"):
                await self.enrich_with_detail_page(page, business)

            # Save to database
            saved = save_business(business)
            if saved:
                self.results_count += 1
                print(f"Saved: {business.get('name')} ({self.results_count}/{self.max_results})")

            # Random delay between businesses
            await page.wait_for_timeout(self.rotation.random_delay_ms(MIN_DELAY_MS, MAX_DELAY_MS))

    async def handle_failed_request(self, context: PlaywrightCrawlingContext, error: Exception):
        """Handle failed requests."""
        print(f"Request failed for {context.request.url}: {error}")
        # Could implement retry logic with proxy rotation here

    async def run_async(self) -> Dict:
        """Run the crawler asynchronously and return results."""
        start_url = self.build_search_url()

        # Build launch options
        launch_options = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }

        # Add proxy if available
        proxy = self.rotation.next_proxy()
        if proxy:
            # Parse proxy format: http://host:port or host:port
            if "://" in proxy:
                launch_options["proxy"] = {"server": proxy}
            else:
                launch_options["proxy"] = {"server": f"http://{proxy}"}

        # Get user agent
        user_agent = self.rotation.next_user_agent()

        # Create crawler
        crawler = PlaywrightCrawler(
            request_handler=self.handle_page,
            request_handler_timeout_secs=120,
            max_requests_per_crawl=1,  # Only process the search page
            headless=self.headless,
            browser_type="chromium",
        )

        # Override default context options to add user agent
        if user_agent:
            crawler._playwright_crawler_options = crawler._playwright_crawler_options or {}
            crawler._playwright_crawler_options["browser_context_options"] = {
                "user_agent": user_agent,
            }

        # Run the crawler
        try:
            await crawler.run([start_url])
        except Exception as e:
            print(f"Crawler error: {e}")
            raise

        return {"results_count": self.results_count, "query": self.query, "location": self.location}

    def run(self) -> Dict:
        """Synchronous wrapper for run_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.run_async())


def run_crawl(query: str, location: str, max_results: int = 20, headless: bool = True) -> Dict:
    """
    Convenience function to run a Google Maps crawl.

    Args:
        query: Business type or keyword to search for.
        location: Geographic location or city.
        max_results: Maximum number of results to scrape.
        headless: Whether to run browser in headless mode.

    Returns:
        Dictionary with crawl statistics.
    """
    crawler = GoogleMapsCrawlee(
        query=query,
        location=location,
        max_results=max_results,
        headless=headless,
    )
    return crawler.run()
