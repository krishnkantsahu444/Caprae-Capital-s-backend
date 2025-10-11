"""Robust HTML parsing utilities for Google Maps business cards."""
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional


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


def parse_detail_page(html: str) -> Dict:
    """
    Parse Google Maps business detail page to extract additional information.

    Args:
        html: Raw HTML content from business detail page.

    Returns:
        Dictionary with website, hours, and other enriched data.
    """
    soup = BeautifulSoup(html, "lxml")
    data = {}

    # Extract website
    website_selectors = [
        "a[data-item-id='authority']",  # Website link with data attribute
        "a[href^='http'][aria-label*='Website']",  # Website with aria-label
        "a.CsEnBe[href^='http']",  # Website link class
    ]
    for sel in website_selectors:
        web_el = soup.select_one(sel)
        if web_el and web_el.get('href'):
            href = web_el.get('href')
            # Filter out Google URLs
            if 'google.com' not in href:
                data['website'] = href
                break

    # Extract hours
    hours_el = soup.select_one("div[aria-label*='Hours']")
    if hours_el:
        data['hours'] = safe_text(hours_el)

    # Extract phone (more reliable on detail page)
    phone_selectors = [
        "button[data-item-id*='phone']",
        "a[href^='tel:']",
    ]
    for sel in phone_selectors:
        phone_el = soup.select_one(sel)
        if phone_el:
            phone_text = safe_text(phone_el)
            if phone_text:
                data['phone'] = phone_text
                break

    return data
