"""Google Maps Crawlee Playwright spider with anti-bot measures and DB persistence."""
import asyncio
import logging
import random
from typing import Optional, List, Dict
from urllib.parse import quote_plus

from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from parsers import parse_card_html, parse_detail_page_html, normalize_phone
# MongoDB (primary) and SQLite (backup) imports
try:
    from db_mongo import save_business, business_exists, is_record_complete
except ImportError:
    from db import save_business, business_exists
    # Fallback for is_record_complete if not in legacy db.py
    def is_record_complete(business: Dict) -> bool:
        return bool(business.get("phone") and business.get("website"))
    print("Warning: MongoDB not available, using SQLite")

from utils.anti_bot import Rotation, load_lines, DEFAULT_USER_AGENTS
from utils.config import (
    PROXY_LIST_PATH,
    USER_AGENTS_PATH,
    HEADLESS,
    MAX_REQUESTS_PER_CRAWL,
    MIN_DELAY_MS,
    MAX_DELAY_MS,
    DETAIL_PAGE_TIMEOUT,
    MAX_DETAIL_ATTEMPTS,
    DETAIL_PAGE_DELAY_MS_MIN,
    DETAIL_PAGE_DELAY_MS_MAX,
    resolve_path,
)

logger = logging.getLogger(__name__)


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

    async def visit_detail_page_and_enrich(self, context_page: Page, business: Dict) -> bool:
        """
        Visit business detail page with retry logic, proxy rotation, and robust error handling.
        
        Args:
            context_page: Main page context (used to create new tab).
            business: Business dict to enrich (modified in-place).
        
        Returns:
            True if successfully enriched, False otherwise.
        """
        url = business.get("google_maps_url")
        if not url:
            logger.debug(f"No google_maps_url for {business.get('name')}, skipping detail visit")
            return False
        
        business_name = business.get("name", "Unknown")
        
        # Throttle before attempting detail visit
        delay_ms = self.rotation.random_delay_ms(DETAIL_PAGE_DELAY_MS_MIN, DETAIL_PAGE_DELAY_MS_MAX)
        logger.info(f"🕒 Waiting {delay_ms}ms before visiting detail page for: {business_name}")
        await context_page.wait_for_timeout(delay_ms)
        
        # Retry loop with proxy rotation
        for attempt in range(1, MAX_DETAIL_ATTEMPTS + 1):
            new_page = None
            try:
                logger.info(f"🔍 Attempt {attempt}/{MAX_DETAIL_ATTEMPTS} - Visiting detail page: {business_name}")
                
                # Create new tab for isolation
                new_page = await context_page.context.new_page()
                
                # Rotate user agent
                user_agent = self.rotation.next_user_agent()
                await new_page.set_user_agent(user_agent)
                logger.debug(f"Set user agent: {user_agent[:50]}...")
                
                # Navigate to detail page
                await new_page.goto(url, timeout=DETAIL_PAGE_TIMEOUT, wait_until="domcontentloaded")
                
                # Wait for detail page content with multiple selector fallbacks
                detail_selectors = [
                    "div.x3AX1-LfntMc-header-title",    # Detail page title
                    "h1.DUwDvf",                         # Business name header
                    "button[data-item-id*='authority']", # Website button
                    "div[role='main']",                  # Main content area
                    "div.m6QErb",                        # Info section
                ]
                
                # Try to wait for at least one selector
                selector_found = False
                for sel in detail_selectors:
                    try:
                        await new_page.wait_for_selector(sel, timeout=5000)
                        selector_found = True
                        logger.debug(f"Found selector: {sel}")
                        break
                    except PlaywrightTimeout:
                        continue
                
                if not selector_found:
                    logger.warning(f"⚠️  No expected selectors found on detail page for: {business_name}")
                
                # Check for blocking indicators
                if await self.check_for_blocking(new_page):
                    raise Exception("Detected CAPTCHA or blocking page")
                
                # Additional wait for dynamic content
                await new_page.wait_for_timeout(random.randint(1000, 2000))
                
                # Extract page content
                html = await new_page.content()
                detail_data = parse_detail_page_html(html)
                
                # Normalize phone numbers
                if detail_data.get("phone"):
                    phones = detail_data["phone"].split("|")
                    normalized_phones = [normalize_phone(p) for p in phones]
                    normalized_phones = [p for p in normalized_phones if p]  # Filter None
                    if normalized_phones:
                        detail_data["phone"] = "|".join(normalized_phones) if len(normalized_phones) > 1 else normalized_phones[0]
                
                # Merge enriched data into business dict
                business.update(detail_data)
                
                logger.info(f"✅ Successfully enriched: {business_name} | Website: {detail_data.get('website', 'N/A')} | Phone: {detail_data.get('phone', 'N/A')}")
                
                # Close tab and return success
                await new_page.close()
                return True
                
            except PlaywrightTimeout as e:
                logger.warning(f"⏱️  Timeout on attempt {attempt} for {business_name}: {str(e)[:100]}")
                
            except Exception as e:
                logger.warning(f"⚠️  Error on attempt {attempt} for {business_name}: {str(e)[:100]}")
            
            finally:
                # Ensure page is closed
                if new_page and not new_page.is_closed():
                    try:
                        await new_page.close()
                    except Exception:
                        pass
            
            # If not last attempt, rotate proxy and retry
            if attempt < MAX_DETAIL_ATTEMPTS:
                proxy = self.rotation.next_proxy()
                if proxy:
                    logger.info(f"🔄 Rotating proxy for retry: {proxy[:30]}...")
                
                # Exponential backoff before retry
                backoff_ms = min(2000 * attempt, 5000)
                logger.info(f"⏳ Backing off {backoff_ms}ms before retry...")
                await context_page.wait_for_timeout(backoff_ms)
        
        # All attempts failed
        logger.error(f"❌ Failed to enrich detail page after {MAX_DETAIL_ATTEMPTS} attempts: {business_name}")
        return False

    async def enrich_with_detail_page(self, page: Page, business: Dict):
        """
        Legacy wrapper for backward compatibility.
        Delegates to visit_detail_page_and_enrich.
        """
        await self.visit_detail_page_and_enrich(page, business)

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
            logger.warning("⚠️  Results selector not found, proceeding anyway")

        # Scroll to load more results
        await self.scroll_results_panel(page, max_scrolls=8)

        # Parse the page
        html = await page.content()
        businesses = parse_card_html(html)

        logger.info(f"📋 Found {len(businesses)} businesses on page")

        # Process each business
        for business in businesses:
            if self.results_count >= self.max_results:
                logger.info(f"🎯 Reached max results limit: {self.max_results}")
                break

            business_name = business.get("name", "Unknown")
            google_maps_url = business.get("google_maps_url")

            # Check if already exists in DB with complete data
            if google_maps_url and business_exists(google_maps_url):
                # Check if existing record is complete
                # If complete, skip detail visit; if incomplete, will update
                logger.info(f"⏭️  Skipping duplicate: {business_name}")
                continue
            
            # Check if record is already complete from search results
            if is_record_complete(business):
                logger.info(f"✨ Already complete from search results: {business_name} | Skipping detail visit")
            else:
                # Enrich with detail page if URL exists
                if google_maps_url:
                    enriched = await self.visit_detail_page_and_enrich(page, business)
                    if not enriched:
                        logger.warning(f"⚠️  Could not enrich {business_name}, saving partial data")
                else:
                    logger.info(f"ℹ️  No google_maps_url for {business_name}, skipping detail visit")

            # Save to database (upsert will handle updates)
            saved = save_business(business)
            if saved:
                self.results_count += 1
                completeness = "✅ Complete" if is_record_complete(business) else "⚠️  Partial"
                logger.info(f"💾 Saved ({self.results_count}/{self.max_results}): {business_name} | {completeness}")
            else:
                logger.debug(f"🔄 Updated existing: {business_name}")

            # Random delay between businesses
            delay_ms = self.rotation.random_delay_ms(MIN_DELAY_MS, MAX_DELAY_MS)
            await page.wait_for_timeout(delay_ms)

    async def handle_failed_request(self, context: PlaywrightCrawlingContext, error: Exception):
        """Handle failed requests with logging."""
        logger.error(f"❌ Request failed for {context.request.url}: {str(error)[:200]}")
        # Could implement retry logic with proxy rotation here if needed

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
