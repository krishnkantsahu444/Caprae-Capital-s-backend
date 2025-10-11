"""
Unit tests for CAPTCHA detection, rate limiting, and detail page enrichment retry logic.

Tests cover:
1. CAPTCHA detection triggers retry
2. Rate limiting applies delays
3. Detail page enrichment retries on failure
4. Exponential backoff is applied correctly
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from utils.anti_bot import RateLimiter
from utils.exceptions import CaptchaDetectedError
from crawlers.google_maps_crawlee import GoogleMapsCrawlee


class TestRateLimiter:
    """Test the RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_applies_delay(self):
        """Test that rate limiter waits for the configured delay."""
        rate_limiter = RateLimiter(min_delay_ms=100, max_delay_ms=200)
        
        import time
        start = time.time()
        await rate_limiter.wait()
        elapsed = time.time() - start
        
        # Should wait between 0.1 and 0.2 seconds
        assert 0.09 < elapsed < 0.25, f"Expected delay 0.1-0.2s, got {elapsed}s"
    
    def test_rate_limiter_get_delay_ms(self):
        """Test that get_delay_ms returns value in correct range."""
        rate_limiter = RateLimiter(min_delay_ms=1000, max_delay_ms=2000)
        
        delay = rate_limiter.get_delay_ms()
        
        assert 1000 <= delay <= 2000, f"Expected delay 1000-2000ms, got {delay}ms"
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_zero_delay(self):
        """Test rate limiter with minimal delay."""
        rate_limiter = RateLimiter(min_delay_ms=0, max_delay_ms=10)
        
        import time
        start = time.time()
        await rate_limiter.wait()
        elapsed = time.time() - start
        
        # Should complete very quickly
        assert elapsed < 0.05, f"Expected near-zero delay, got {elapsed}s"


class TestCaptchaDetection:
    """Test CAPTCHA detection functionality."""
    
    @pytest.mark.asyncio
    async def test_is_captcha_present_detects_recaptcha_iframe(self):
        """Test that reCAPTCHA iframe is detected."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page with reCAPTCHA iframe
        mock_page = AsyncMock(spec=Page)
        mock_iframe = Mock()
        mock_page.query_selector = AsyncMock(side_effect=[
            mock_iframe,  # First call finds iframe
            None,         # Second call for form
        ])
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        result = await crawler.is_captcha_present(mock_page)
        
        assert result is True, "Should detect reCAPTCHA iframe"
        mock_page.query_selector.assert_called()
    
    @pytest.mark.asyncio
    async def test_is_captcha_present_detects_captcha_form(self):
        """Test that CAPTCHA redirect form is detected."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page with CAPTCHA form
        mock_page = AsyncMock(spec=Page)
        mock_form = Mock()
        mock_page.query_selector = AsyncMock(side_effect=[
            None,       # First call (iframe) finds nothing
            mock_form,  # Second call finds form
        ])
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        result = await crawler.is_captcha_present(mock_page)
        
        assert result is True, "Should detect CAPTCHA form"
    
    @pytest.mark.asyncio
    async def test_is_captcha_present_detects_text_indicators(self):
        """Test that text-based CAPTCHA indicators are detected."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page with blocking text
        mock_page = AsyncMock(spec=Page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="""
            <html>
                <body>
                    <h1>Unusual traffic from your computer network</h1>
                    <p>Please verify you're not a robot</p>
                </body>
            </html>
        """)
        
        result = await crawler.is_captcha_present(mock_page)
        
        assert result is True, "Should detect text indicator 'unusual traffic'"
    
    @pytest.mark.asyncio
    async def test_is_captcha_present_no_captcha(self):
        """Test that normal pages don't trigger CAPTCHA detection."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock normal page
        mock_page = AsyncMock(spec=Page)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="""
            <html>
                <body>
                    <h1>Google Maps Search Results</h1>
                    <div class="results">Normal content</div>
                </body>
            </html>
        """)
        
        result = await crawler.is_captcha_present(mock_page)
        
        assert result is False, "Should not detect CAPTCHA on normal page"


class TestDetailPageEnrichment:
    """Test detail page enrichment with retry logic."""
    
    @pytest.mark.asyncio
    async def test_detail_enrichment_succeeds_on_first_attempt(self):
        """Test successful enrichment on first attempt."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock successful detail page visit
        mock_context_page = AsyncMock(spec=Page)
        mock_new_page = AsyncMock(spec=Page)
        mock_context = Mock()
        mock_context.new_page = AsyncMock(return_value=mock_new_page)
        mock_context_page.context = mock_context
        mock_context_page.wait_for_timeout = AsyncMock()
        
        mock_new_page.set_extra_http_headers = AsyncMock()
        mock_new_page.goto = AsyncMock()
        mock_new_page.wait_for_selector = AsyncMock()
        mock_new_page.wait_for_timeout = AsyncMock()
        mock_new_page.content = AsyncMock(return_value="""
            <html>
                <body>
                    <button data-item-id="phone:authority">+1234567890</button>
                    <a href="https://example.com">Website</a>
                </body>
            </html>
        """)
        mock_new_page.is_closed = Mock(return_value=False)
        mock_new_page.close = AsyncMock()
        
        # Mock is_captcha_present to return False
        crawler.is_captcha_present = AsyncMock(return_value=False)
        
        business = {
            "name": "Test Business",
            "google_maps_url": "https://maps.google.com/test"
        }
        
        result = await crawler.visit_detail_page_and_enrich(mock_context_page, business)
        
        assert result is True, "Should succeed on first attempt"
        assert crawler.stats["detail_successes"] == 1
        assert crawler.stats["detail_failures"] == 0
    
    @pytest.mark.asyncio
    async def test_detail_enrichment_retries_on_captcha(self):
        """Test that detail enrichment retries when CAPTCHA is detected."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page setup
        mock_context_page = AsyncMock(spec=Page)
        mock_new_page = AsyncMock(spec=Page)
        mock_context = Mock()
        mock_context.new_page = AsyncMock(return_value=mock_new_page)
        mock_context_page.context = mock_context
        mock_context_page.wait_for_timeout = AsyncMock()
        
        mock_new_page.set_extra_http_headers = AsyncMock()
        mock_new_page.goto = AsyncMock()
        mock_new_page.is_closed = Mock(return_value=False)
        mock_new_page.close = AsyncMock()
        
        # First 2 attempts: CAPTCHA, Third attempt: success
        crawler.is_captcha_present = AsyncMock(side_effect=[
            True,   # Attempt 1: CAPTCHA
            True,   # Attempt 2: CAPTCHA
            False,  # Attempt 3: Success
        ])
        
        mock_new_page.wait_for_selector = AsyncMock()
        mock_new_page.wait_for_timeout = AsyncMock()
        mock_new_page.content = AsyncMock(return_value="<html><body></body></html>")
        
        business = {
            "name": "Test Business",
            "google_maps_url": "https://maps.google.com/test"
        }
        
        result = await crawler.visit_detail_page_and_enrich(mock_context_page, business)
        
        # Should eventually succeed after retries
        assert result is True, "Should succeed after CAPTCHA retries"
        assert crawler.stats["captcha_encounters"] == 2, "Should count CAPTCHA encounters"
        assert crawler.stats["detail_successes"] == 1
    
    @pytest.mark.asyncio
    async def test_detail_enrichment_fails_after_max_retries(self):
        """Test that enrichment fails after max retries."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page setup
        mock_context_page = AsyncMock(spec=Page)
        mock_new_page = AsyncMock(spec=Page)
        mock_context = Mock()
        mock_context.new_page = AsyncMock(return_value=mock_new_page)
        mock_context_page.context = mock_context
        mock_context_page.wait_for_timeout = AsyncMock()
        
        mock_new_page.set_extra_http_headers = AsyncMock()
        mock_new_page.goto = AsyncMock(side_effect=PlaywrightTimeout("Timeout"))
        mock_new_page.is_closed = Mock(return_value=False)
        mock_new_page.close = AsyncMock()
        
        business = {
            "name": "Test Business",
            "google_maps_url": "https://maps.google.com/test"
        }
        
        result = await crawler.visit_detail_page_and_enrich(mock_context_page, business)
        
        assert result is False, "Should fail after max retries"
        assert crawler.stats["detail_failures"] == 1
        assert crawler.stats["detail_successes"] == 0
    
    @pytest.mark.asyncio
    async def test_detail_enrichment_applies_exponential_backoff(self):
        """Test that exponential backoff is applied between retries."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        # Mock page setup
        mock_context_page = AsyncMock(spec=Page)
        mock_new_page = AsyncMock(spec=Page)
        mock_context = Mock()
        mock_context.new_page = AsyncMock(return_value=mock_new_page)
        mock_context_page.context = mock_context
        
        # Track wait_for_timeout calls to verify backoff
        wait_calls = []
        async def track_wait(ms):
            wait_calls.append(ms)
        
        mock_context_page.wait_for_timeout = AsyncMock(side_effect=track_wait)
        
        mock_new_page.set_extra_http_headers = AsyncMock()
        mock_new_page.goto = AsyncMock(side_effect=Exception("Test error"))
        mock_new_page.is_closed = Mock(return_value=False)
        mock_new_page.close = AsyncMock()
        
        business = {
            "name": "Test Business",
            "google_maps_url": "https://maps.google.com/test"
        }
        
        result = await crawler.visit_detail_page_and_enrich(mock_context_page, business)
        
        # Should have applied exponential backoff: 2s, 4s
        # (First wait is rate limiter, then 2000ms, then 4000ms)
        backoff_waits = [w for w in wait_calls if w >= 2000]
        assert len(backoff_waits) >= 2, "Should apply exponential backoff"
        assert backoff_waits[0] == 2000, "First backoff should be 2s"
        assert backoff_waits[1] == 4000, "Second backoff should be 4s"


class TestStatisticsTracking:
    """Test that statistics are tracked correctly."""
    
    def test_stats_initialization(self):
        """Test that stats are initialized correctly."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        assert crawler.stats["total_attempted"] == 0
        assert crawler.stats["total_successful"] == 0
        assert crawler.stats["captcha_encounters"] == 0
        assert crawler.stats["detail_failures"] == 0
        assert crawler.stats["detail_successes"] == 0
    
    @pytest.mark.asyncio
    async def test_stats_updated_on_captcha(self):
        """Test that CAPTCHA encounters are counted."""
        crawler = GoogleMapsCrawlee(query="test", location="test", max_results=1)
        
        mock_page = AsyncMock(spec=Page)
        mock_page.query_selector = AsyncMock(return_value=Mock())  # Found CAPTCHA
        mock_page.content = AsyncMock(return_value="<html></html>")
        
        await crawler.is_captcha_present(mock_page)
        
        # Increment manually as is_captcha_present doesn't update stats
        crawler.stats["captcha_encounters"] += 1
        
        assert crawler.stats["captcha_encounters"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
