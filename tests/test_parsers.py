"""Unit tests for HTML parsing functions."""
import sys
import os
import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from parsers import (
    parse_card_html,
    parse_detail_page_html,
    normalize_phone,
    safe_text,
    parse_rating,
    parse_reviews,
)


# ==================== FIXTURES ====================

@pytest.fixture
def sample_card_html():
    """Sample HTML for a Google Maps business card."""
    return """
    <div class="Nv2PK">
        <div class="qBF1Pd">Artisan Coffee Roasters</div>
        <div class="W4Efsd">
            <span>Coffee shop</span>
        </div>
        <div class="W4Efsd">
            <span>123 Main St, Austin, TX 78701</span>
        </div>
        <div class="fontBodyMedium">
            <span class="MW4etd">4.7</span>
            <span class="UY7F9">(342)</span>
        </div>
        <a href="https://www.google.com/maps/place/data=xyz123">View</a>
    </div>
    """


@pytest.fixture
def sample_detail_page_html():
    """Sample HTML for a Google Maps detail page."""
    return """
    <html>
        <body>
            <div class="m6QErb">
                <h1 class="DUwDvf">Artisan Coffee Roasters</h1>
                
                <!-- Website link -->
                <a data-item-id="authority" href="https://artisancoffee.com">Website</a>
                
                <!-- Phone button -->
                <button data-item-id="phone:tel:+15125550123" aria-label="Phone: +1 512-555-0123">
                    Call
                </button>
                
                <!-- Hours -->
                <div aria-label="Hours: Monday to Friday 7am-8pm">
                    <table>
                        <tr><td>Monday</td><td>7:00 AM – 8:00 PM</td></tr>
                        <tr><td>Tuesday</td><td>7:00 AM – 8:00 PM</td></tr>
                    </table>
                </div>
                
                <!-- Category -->
                <button jsaction="category">Coffee shop</button>
                
                <!-- Services -->
                <div aria-label="Service options">
                    <span class="ZDu9vd" aria-label="Dine-in">Dine-in</span>
                    <span class="ZDu9vd" aria-label="Takeout">Takeout</span>
                    <span class="ZDu9vd" aria-label="Delivery">Delivery</span>
                </div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_card_with_url():
    """Sample card HTML with google_maps_url."""
    return """
    <a class="hfpxzc" href="https://www.google.com/maps/place/Artisan+Coffee/data=xyz">
        <div class="qBF1Pd">Blue Bottle Coffee</div>
        <span class="MW4etd">4.6</span>
    </a>
    """


# ==================== TESTS FOR normalize_phone ====================

def test_normalize_phone_valid():
    """Test normalizing a valid phone number."""
    result = normalize_phone("+1 (512) 555-0123")
    assert result == "+15125550123"


def test_normalize_phone_with_spaces_and_dashes():
    """Test normalizing phone with spaces and dashes."""
    result = normalize_phone("512-555-0123")
    assert result == "5125550123"


def test_normalize_phone_international():
    """Test normalizing international phone with leading 00."""
    result = normalize_phone("00441234567890")
    assert result == "+441234567890"


def test_normalize_phone_too_short():
    """Test that too-short numbers return None."""
    result = normalize_phone("12345")
    assert result is None


def test_normalize_phone_too_long():
    """Test that too-long numbers return None."""
    result = normalize_phone("1234567890123456")
    assert result is None


def test_normalize_phone_empty():
    """Test that empty string returns None."""
    result = normalize_phone("")
    assert result is None


def test_normalize_phone_none():
    """Test that None input returns None."""
    result = normalize_phone(None)
    assert result is None


def test_normalize_phone_with_letters():
    """Test normalizing phone with letters (should be removed)."""
    result = normalize_phone("1-800-FLOWERS")
    # After removing non-digits: "1800" - only 4 digits, should return None
    assert result is None


# ==================== TESTS FOR parse_card_html ====================

def test_parse_card_html_basic(sample_card_html):
    """Test parsing basic business card HTML."""
    results = parse_card_html(sample_card_html)
    
    assert len(results) == 1
    business = results[0]
    
    assert business["name"] == "Artisan Coffee Roasters"
    assert business["address"] == "123 Main St, Austin, TX 78701"
    assert business["category"] == "Coffee shop"
    assert business["rating"] == 4.7
    assert business["reviews"] == 342


def test_parse_card_html_with_url(sample_card_with_url):
    """Test parsing card with google_maps_url."""
    results = parse_card_html(sample_card_with_url)
    
    assert len(results) == 1
    business = results[0]
    
    assert business["name"] == "Blue Bottle Coffee"
    assert business["rating"] == 4.6
    assert business["google_maps_url"] is not None
    assert "maps/place" in business["google_maps_url"]


def test_parse_card_html_empty():
    """Test parsing empty HTML returns empty list."""
    results = parse_card_html("<html><body></body></html>")
    assert results == []


def test_parse_card_html_malformed():
    """Test parsing malformed HTML doesn't crash."""
    results = parse_card_html("<div><span>Incomplete")
    # Should not raise exception, may return empty or partial results
    assert isinstance(results, list)


# ==================== TESTS FOR parse_detail_page_html ====================

def test_parse_detail_page_html_complete(sample_detail_page_html):
    """Test parsing complete detail page HTML."""
    result = parse_detail_page_html(sample_detail_page_html)
    
    assert "website" in result
    assert result["website"] == "https://artisancoffee.com"
    
    assert "phone" in result
    # Phone should be normalized
    assert "+15125550123" in result["phone"]
    
    assert "hours" in result
    assert "Monday to Friday" in result["hours"] or "Monday" in result["hours"]
    
    assert "category" in result
    assert result["category"] == "Coffee shop"
    
    assert "services" in result
    assert isinstance(result["services"], list)
    assert "Dine-in" in result["services"]


def test_parse_detail_page_html_website_only():
    """Test parsing detail page with only website."""
    html = """
    <html><body>
        <a data-item-id="authority" href="https://example.com">Website</a>
    </body></html>
    """
    result = parse_detail_page_html(html)
    
    assert result["website"] == "https://example.com"


def test_parse_detail_page_html_phone_only():
    """Test parsing detail page with only phone."""
    html = """
    <html><body>
        <button data-item-id="phone:tel:+15551234567" aria-label="+1 555-123-4567">Call</button>
    </body></html>
    """
    result = parse_detail_page_html(html)
    
    assert "phone" in result
    assert "+15551234567" in result["phone"]


def test_parse_detail_page_html_filters_google_urls():
    """Test that Google URLs are filtered out from website field."""
    html = """
    <html><body>
        <a data-item-id="authority" href="https://google.com/business/123">Google</a>
        <a href="https://maps.google.com/place/123">Maps</a>
    </body></html>
    """
    result = parse_detail_page_html(html)
    
    # Should not extract Google URLs as website
    assert result.get("website") is None or "google.com" not in result["website"]


def test_parse_detail_page_html_multiple_phones():
    """Test parsing detail page with multiple phone numbers."""
    html = """
    <html><body>
        <button data-item-id="phone:tel:+15551111111" aria-label="+1 555-111-1111">Call 1</button>
        <button data-item-id="phone:tel:+15552222222" aria-label="+1 555-222-2222">Call 2</button>
    </body></html>
    """
    result = parse_detail_page_html(html)
    
    assert "phone" in result
    # Multiple phones should be joined with |
    assert "|" in result["phone"] or "+15551111111" in result["phone"]


def test_parse_detail_page_html_empty():
    """Test parsing empty detail page."""
    result = parse_detail_page_html("<html><body></body></html>")
    
    # Should return dict (possibly empty or with None values)
    assert isinstance(result, dict)


# ==================== TESTS FOR HELPER FUNCTIONS ====================

def test_safe_text_valid():
    """Test safe_text with valid element."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup("<div>Test Text</div>", "lxml")
    element = soup.find("div")
    
    assert safe_text(element) == "Test Text"


def test_safe_text_none():
    """Test safe_text with None element."""
    assert safe_text(None) is None


def test_safe_text_empty():
    """Test safe_text with empty element."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup("<div></div>", "lxml")
    element = soup.find("div")
    
    assert safe_text(element) is None


def test_parse_rating_valid():
    """Test parsing valid rating."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup("<span>4.5 stars</span>", "lxml")
    element = soup.find("span")
    
    assert parse_rating(element) == 4.5


def test_parse_rating_none():
    """Test parsing None rating."""
    assert parse_rating(None) is None


def test_parse_reviews_valid():
    """Test parsing valid review count."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup("<span>1,234 reviews</span>", "lxml")
    element = soup.find("span")
    
    assert parse_reviews(element) == 1234


def test_parse_reviews_none():
    """Test parsing None reviews."""
    assert parse_reviews(None) is None


# ==================== INTEGRATION-LIKE TESTS ====================

def test_parse_card_and_detail_page_integration(sample_card_html, sample_detail_page_html):
    """Test that card and detail page parsing work together."""
    # Parse card
    cards = parse_card_html(sample_card_html)
    assert len(cards) == 1
    
    card = cards[0]
    assert card["name"] == "Artisan Coffee Roasters"
    assert card["website"] is None  # Not available in card
    
    # Parse detail page
    detail = parse_detail_page_html(sample_detail_page_html)
    
    # Merge (simulate enrichment)
    card.update(detail)
    
    # Should now have website and phone
    assert card["website"] == "https://artisancoffee.com"
    assert card["phone"] is not None
    assert "512" in card["phone"] or "+1512" in card["phone"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
