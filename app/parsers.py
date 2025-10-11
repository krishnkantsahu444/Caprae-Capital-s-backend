"""Robust HTML parsing utilities for Google Maps business cards."""
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from utils.config import PHONE_NORMALIZE_REGEX


def normalize_phone(phone_str: Optional[str]) -> Optional[str]:
    """
    Normalize phone number by removing non-digit characters (except +).
    
    Args:
        phone_str: Raw phone number string.
    
    Returns:
        Normalized phone string, or None if invalid.
    """
    if not phone_str:
        return None
    
    # Remove all characters except digits and +
    normalized = re.sub(PHONE_NORMALIZE_REGEX, "", phone_str)
    
    # Replace leading 00 with +
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    
    # Validate length (between 6 and 15 digits is reasonable for international)
    if len(normalized) < 6 or len(normalized) > 15:
        return None
    
    return normalized


def safe_text(element) -> Optional[str]:
    """Safely extract text from a BeautifulSoup element."""
    if element is None:
        return None
    text = element.get_text(strip=True)
    return text if text else None


def parse_rating(element) -> Optional[float]:
    """Parse rating from an element."""
    if element is None:
        return None
    text = safe_text(element)
    if not text:
        return None
    # Extract first number that looks like a rating (e.g., "4.5" from "4.5 stars")
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_reviews(element) -> Optional[int]:
    """Parse review count from an element."""
    if element is None:
        return None
    text = safe_text(element)
    if not text:
        return None
    # Extract numbers and remove commas (e.g., "1,234 reviews" -> 1234)
    numbers = re.sub(r'[^\d]', '', text)
    if numbers:
        try:
            return int(numbers)
        except ValueError:
            return None
    return None


def parse_card_html(html: str) -> List[Dict]:
    """
    Parse Google Maps search results HTML and extract business cards.

    Args:
        html: Raw HTML content from Google Maps search results page.

    Returns:
        List of dictionaries containing business data.
    """
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Google Maps uses various selectors - try multiple patterns
    # These selectors may change over time and need to be updated
    card_selectors = [
        "div.Nv2PK",  # Common search result container
        "div[role='article']",  # Article role containers
        "div.section-result",  # Legacy selector
        "a.hfpxzc",  # Link container with business data
    ]

    cards = []
    for selector in card_selectors:
        found = soup.select(selector)
        if found:
            cards = found
            break

    for card in cards:
        # Extract business name
        name = None
        name_selectors = [
            "div.qBF1Pd",  # Primary name container
            "div.fontHeadlineSmall",  # Alternative name container
            "span.OSrXXb",  # Name span
            "[aria-label][role='link']",  # Linked name with aria-label
        ]
        for sel in name_selectors:
            name_el = card.select_one(sel)
            if name_el:
                name = safe_text(name_el)
                if name:
                    break

        # Extract address
        address = None
        address_selectors = [
            "div.W4Efsd:nth-of-type(2)",  # Common address container
            "span.W4Efsd",  # Address span
            "div.W4Efsd > span",  # Nested address
        ]
        for sel in address_selectors:
            addr_el = card.select_one(sel)
            if addr_el:
                address = safe_text(addr_el)
                if address:
                    break

        # Extract rating
        rating = None
        rating_selectors = [
            "span.MW4etd",  # Rating span
            "span[role='img'][aria-label*='stars']",  # Rating with aria-label
            "div.fontBodyMedium span",  # Rating in body text
        ]
        for sel in rating_selectors:
            rating_el = card.select_one(sel)
            if rating_el:
                rating = parse_rating(rating_el)
                if rating is not None:
                    break

        # Extract review count
        reviews = None
        review_selectors = [
            "span.UY7F9",  # Review count span
            "span[aria-label*='reviews']",  # Reviews with aria-label
            "span.fontBodyMedium span:nth-of-type(2)",  # Second span in rating group
        ]
        for sel in review_selectors:
            review_el = card.select_one(sel)
            if review_el:
                reviews = parse_reviews(review_el)
                if reviews is not None:
                    break

        # Extract phone number
        phone = None
        phone_selectors = [
            "span.UsdlK",  # Phone number span
            "[data-item-id*='phone']",  # Phone data attribute
        ]
        for sel in phone_selectors:
            phone_el = card.select_one(sel)
            if phone_el:
                phone = safe_text(phone_el)
                if phone:
                    break

        # Extract Google Maps URL
        google_maps_url = None
        link = card.find('a', href=re.compile(r'/maps/place/'))
        if link and link.get('href'):
            href = link.get('href')
            if href.startswith('http'):
                google_maps_url = href
            elif href.startswith('/'):
                google_maps_url = f"https://www.google.com{href}"

        # Extract category/type
        category = None
        category_selectors = [
            "span.W4Efsd:first-of-type",  # First W4Efsd usually contains category
            "div.W4Efsd > span:first-child",
        ]
        for sel in category_selectors:
            cat_el = card.select_one(sel)
            if cat_el:
                category = safe_text(cat_el)
                if category and category != address:  # Avoid using address as category
                    break

        # Only add results that have at least a name or URL
        if name or google_maps_url:
            results.append({
                "name": name,
                "address": address,
                "phone": phone,
                "website": None,  # Will be enriched in detail page
                "rating": rating,
                "reviews": reviews,
                "google_maps_url": google_maps_url,
                "category": category,
                "hours": None,  # Will be enriched in detail page
            })

    return results


def parse_detail_page_html(html: str) -> Dict:
    """
    Parse Google Maps business detail page to extract comprehensive information.
    Uses multiple fallback selectors for robustness against HTML changes.
    
    Args:
        html: Raw HTML content from business detail page.
    
    Returns:
        Dictionary with website, phone, hours, category, services, and other enriched data.
    """
    soup = BeautifulSoup(html, "lxml")
    data = {}
    
    # ==================== WEBSITE EXTRACTION ====================
    # Priority 1: Website button/link with data attribute
    website_selectors = [
        "a[data-item-id='authority']",                # Official website link
        "a[aria-label*='Website'][href^='http']",     # Website with aria-label
        "a[data-tooltip='Open website'][href^='http']",  # Tooltip-based
        "a.CsEnBe[href^='http']",                     # Website link class
        "button[data-item-id*='authority'] + a",      # Adjacent to website button
    ]
    
    for sel in website_selectors:
        try:
            web_el = soup.select_one(sel)
            if web_el and web_el.get('href'):
                href = web_el.get('href')
                # Filter out Google URLs and maps URLs
                if isinstance(href, str) and 'google.com' not in href and 'maps' not in href:
                    data['website'] = href
                    break
        except Exception:
            continue
    
    # Fallback: Look for any external HTTP link in business info section
    if not data.get('website'):
        try:
            info_section = soup.select_one("div.m6QErb, div[role='main']")
            if info_section:
                links = info_section.find_all('a', href=re.compile(r'^https?://(?!.*google\.com)(?!.*maps)'))
                if links:
                    data['website'] = links[0].get('href')
        except Exception:
            pass
    
    # ==================== PHONE EXTRACTION ====================
    # Priority 1: Phone button with data attribute
    phone_selectors = [
        "button[data-item-id*='phone']",              # Phone button
        "a[href^='tel:']",                             # Tel: link
        "button[data-tooltip*='phone' i]",            # Tooltip with "phone"
        "div[data-section-id='pn0'] button",          # Phone section button
        "span[data-tooltip*='Call']",                 # Call tooltip
    ]
    
    phones = []
    for sel in phone_selectors:
        try:
            phone_els = soup.select(sel)
            for phone_el in phone_els:
                # Try aria-label first (often contains full number)
                phone_text = phone_el.get('aria-label')
                if not phone_text:
                    phone_text = safe_text(phone_el)
                
                if phone_text:
                    normalized = normalize_phone(phone_text)
                    if normalized and normalized not in phones:
                        phones.append(normalized)
        except Exception:
            continue
    
    # Store phone(s) - join multiple with | separator
    if phones:
        data['phone'] = '|'.join(phones) if len(phones) > 1 else phones[0]
    
    # ==================== HOURS EXTRACTION ====================
    hours_selectors = [
        "div[aria-label*='Hours' i]",                 # Hours div with aria-label
        "table[aria-label*='Hours' i]",               # Hours table
        "div[data-section-id='oh'] div.t39EBf",      # Hours section
        "button[data-item-id='olh'] + div",           # Adjacent to hours button
    ]
    
    for sel in hours_selectors:
        try:
            hours_el = soup.select_one(sel)
            if hours_el:
                hours_text = safe_text(hours_el)
                if hours_text and len(hours_text) > 5:  # Reasonable length check
                    data['hours'] = hours_text
                    break
        except Exception:
            continue
    
    # ==================== CATEGORY EXTRACTION ====================
    # More reliable on detail page than search results
    category_selectors = [
        "button[jsaction*='category']",               # Category button
        "div.LBgpqf button",                          # Category in header
        "span[jstcache*='3']",                        # Category span (legacy)
        "button[data-tooltip*='Categories']",         # Categories tooltip
    ]
    
    for sel in category_selectors:
        try:
            cat_el = soup.select_one(sel)
            if cat_el:
                category = safe_text(cat_el)
                if category and len(category) > 2:
                    data['category'] = category
                    break
        except Exception:
            continue
    
    # ==================== SERVICES/AMENITIES EXTRACTION ====================
    services = []
    try:
        # Services are often in accessibility features or amenities sections
        service_sections = soup.select("div[aria-label*='Service options' i], div[aria-label*='Amenities' i]")
        for section in service_sections:
            service_els = section.select("span.ZDu9vd, div[role='img'][aria-label]")
            for svc in service_els:
                svc_text = svc.get('aria-label') or safe_text(svc)
                if svc_text and svc_text not in services:
                    services.append(svc_text)
    except Exception:
        pass
    
    if services:
        data['services'] = services  # Store as list
    
    # ==================== SOCIAL LINKS EXTRACTION ====================
    social_links = {}
    try:
        social_patterns = {
            'facebook': r'facebook\.com',
            'twitter': r'twitter\.com|x\.com',
            'instagram': r'instagram\.com',
            'linkedin': r'linkedin\.com',
        }
        
        for platform, pattern in social_patterns.items():
            link = soup.find('a', href=re.compile(pattern))
            if link and link.get('href'):
                social_links[platform] = link.get('href')
    except Exception:
        pass
    
    if social_links:
        data['social_links'] = social_links
    
    # ==================== ADDITIONAL METADATA ====================
    # Extract price level (if present)
    try:
        price_el = soup.select_one("span[aria-label*='Price' i]")
        if price_el:
            price_text = safe_text(price_el)
            if price_text:
                data['price_level'] = price_text
    except Exception:
        pass
    
    return data


def parse_detail_page(html: str) -> Dict:
    """
    Legacy wrapper for backward compatibility.
    Calls parse_detail_page_html with the same signature.
    """
    return parse_detail_page_html(html)
