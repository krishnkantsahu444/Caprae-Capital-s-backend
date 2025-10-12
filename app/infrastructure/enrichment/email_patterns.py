"""
Email pattern generation module.
Generates common email formats for businesses.
"""

from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class EmailPatternGenerator:
    """
    Generate possible email addresses using common business patterns.
    
    Example patterns:
    - john.doe@company.com
    - john@company.com
    - jdoe@company.com
    - info@company.com
    """
    
    # 20+ common email patterns
    PATTERNS = [
        # Personal email formats
        "{first}.{last}@{domain}",
        "{first}{last}@{domain}",
        "{first}_{last}@{domain}",
        "{first}-{last}@{domain}",
        "{first}@{domain}",
        "{last}@{domain}",
        "{f}{last}@{domain}",
        "{first}{l}@{domain}",
        "{f}.{last}@{domain}",
        "{first}.{l}@{domain}",
        "{last}.{first}@{domain}",
        
        # Generic/role-based emails
        "info@{domain}",
        "contact@{domain}",
        "hello@{domain}",
        "sales@{domain}",
        "support@{domain}",
        "admin@{domain}",
        "office@{domain}",
        "inquiry@{domain}",
        "service@{domain}",
        "customerservice@{domain}",
    ]
    
    @staticmethod
    def generate_emails(
        domain: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Generate possible email addresses for a domain.
        
        Args:
            domain: Company domain (e.g., "acme.com")
            first_name: First name (optional)
            last_name: Last name (optional)
        
        Returns:
            List of (email, pattern) tuples
            Example: [("john.doe@acme.com", "{first}.{last}@{domain}")]
        """
        emails = []
        
        # If no names provided, only generate generic emails
        if not first_name or not last_name:
            for pattern in EmailPatternGenerator.PATTERNS:
                if '{first}' not in pattern and '{last}' not in pattern and '{f}' not in pattern and '{l}' not in pattern:
                    try:
                        email = pattern.format(domain=domain)
                        emails.append((email, pattern))
                    except KeyError:
                        continue
            return emails
        
        # Normalize names
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f = first[0] if first else ''
        l = last[0] if last else ''
        
        # Generate all pattern variations
        for pattern in EmailPatternGenerator.PATTERNS:
            try:
                email = pattern.format(
                    first=first,
                    last=last,
                    f=f,
                    l=l,
                    domain=domain
                )
                emails.append((email, pattern))
            except KeyError:
                # Pattern requires variables we don't have
                continue
        
        return emails
    
    @staticmethod
    def extract_domain_from_url(url: str) -> Optional[str]:
        """
        Extract clean domain from website URL.
        
        Examples:
            "https://www.acme.com" -> "acme.com"
            "http://acme.com/about" -> "acme.com"
            "acme.com" -> "acme.com"
        """
        if not url:
            return None
        
        try:
            from urllib.parse import urlparse
            
            # Handle URLs without scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            
            # Remove www. prefix
            domain = domain.replace('www.', '')
            
            # Remove trailing slash and path
            domain = domain.split('/')[0]
            
            return domain if domain else None
        
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {e}")
            return None
