"""
Scrape contact pages for email addresses.
Uses regex to find emails in HTML content.
"""

import httpx
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Set, Optional

logger = logging.getLogger(__name__)

class ContactPageScraper:
    """
    Scrape website contact pages for email addresses.
    Completely free - just HTTP requests + regex.
    """
    
    # Regex pattern to match email addresses
    EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Common contact page URLs
    CONTACT_URLS = [
        "/contact",
        "/contact-us",
        "/about",
        "/about-us",
        "/team",
        "/",  # Homepage
    ]
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    async def scrape_emails(self, domain: str) -> List[str]:
        """
        Scrape all email addresses from a domain's contact pages.
        
        Args:
            domain: Domain to scrape (e.g., "acme.com")
        
        Returns:
            List of unique email addresses found
        """
        emails_found = set()
        
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ) as client:
            for path in self.CONTACT_URLS:
                try:
                    # Build URL
                    url = f"https://{domain}{path}"
                    
                    # Fetch page
                    response = await client.get(url)
                    
                    if response.status_code != 200:
                        continue
                    
                    # Parse HTML
                    html = response.text
                    
                    # Extract emails using regex
                    found = re.findall(self.EMAIL_REGEX, html)
                    
                    # Filter valid emails
                    for email in found:
                        # Skip image files
                        if any(ext in email.lower() for ext in ['.png', '.jpg', '.gif', '.svg', '.webp', '.jpeg']):
                            continue
                        
                        # Only include emails from this domain or common business emails
                        email_domain = email.split('@')[1].lower()
                        target_domain = domain.lower()
                        
                        if email_domain == target_domain or target_domain in email_domain:
                            emails_found.add(email.lower())
                    
                    if found:
                        logger.info(f"Found {len(found)} potential emails on {url}")
                
                except httpx.TimeoutException:
                    logger.debug(f"Timeout scraping {url}")
                    continue
                except Exception as e:
                    logger.debug(f"Failed to scrape {url}: {e}")
                    continue
        
        return list(emails_found)
    
    def extract_from_html(self, html: str, domain: str) -> List[str]:
        """
        Extract emails from raw HTML content.
        Useful if you already have the HTML.
        
        Args:
            html: HTML content to parse
            domain: Target domain to filter emails
        
        Returns:
            List of unique email addresses
        """
        emails = []
        
        # Find emails with regex
        found = re.findall(self.EMAIL_REGEX, html)
        
        for email in found:
            # Skip images
            if any(ext in email.lower() for ext in ['.png', '.jpg', '.gif', '.svg', '.webp', '.jpeg']):
                continue
            
            # Only emails from target domain
            email_domain = email.split('@')[1].lower()
            target_domain = domain.lower()
            
            if email_domain == target_domain or target_domain in email_domain:
                emails.append(email.lower())
        
        return list(set(emails))
    
    def scrape_emails_sync(self, domain: str) -> List[str]:
        """
        Synchronous version of scrape_emails.
        Useful for non-async contexts.
        
        Args:
            domain: Domain to scrape (e.g., "acme.com")
        
        Returns:
            List of unique email addresses found
        """
        emails_found = set()
        
        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ) as client:
            for path in self.CONTACT_URLS:
                try:
                    # Build URL
                    url = f"https://{domain}{path}"
                    
                    # Fetch page
                    response = client.get(url)
                    
                    if response.status_code != 200:
                        continue
                    
                    # Parse HTML
                    html = response.text
                    
                    # Extract emails using regex
                    found = re.findall(self.EMAIL_REGEX, html)
                    
                    # Filter valid emails
                    for email in found:
                        # Skip image files
                        if any(ext in email.lower() for ext in ['.png', '.jpg', '.gif', '.svg', '.webp', '.jpeg']):
                            continue
                        
                        # Only include emails from this domain
                        email_domain = email.split('@')[1].lower()
                        target_domain = domain.lower()
                        
                        if email_domain == target_domain or target_domain in email_domain:
                            emails_found.add(email.lower())
                    
                    if found:
                        logger.info(f"Found {len(found)} potential emails on {url}")
                
                except httpx.TimeoutException:
                    logger.debug(f"Timeout scraping {url}")
                    continue
                except Exception as e:
                    logger.debug(f"Failed to scrape {url}: {e}")
                    continue
        
        return list(emails_found)
