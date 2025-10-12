"""
Main Email Finder - Orchestrates all email enrichment methods.
Combines pattern generation, SMTP verification, contact scraping, and WHOIS.
"""

import whois
import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from .email_patterns import EmailPatternGenerator
from .smtp_validator import SMTPEmailValidator
from .contact_scraper import ContactPageScraper

logger = logging.getLogger(__name__)

class EmailFinder:
    """
    Main orchestrator for email enrichment.
    
    Combines multiple free methods:
    1. Contact page scraping (finds existing emails)
    2. Pattern generation (guesses common formats)
    3. SMTP verification (validates emails)
    
    Usage:
        finder = EmailFinder()
        result = await finder.find_emails(
            website="https://acme.com",
            business_name="Acme Corp"
        )
    """
    
    def __init__(
        self,
        smtp_timeout: int = 10,
        scraper_timeout: int = 10,
        max_patterns: int = 20
    ):
        """
        Initialize email finder with all components.
        
        Args:
            smtp_timeout: Timeout for SMTP verification (seconds)
            scraper_timeout: Timeout for web scraping (seconds)
            max_patterns: Maximum patterns to try per domain
        """
        self.pattern_generator = EmailPatternGenerator()
        self.smtp_validator = SMTPEmailValidator(timeout=smtp_timeout)
        self.contact_scraper = ContactPageScraper(timeout=scraper_timeout)
        self.max_patterns = max_patterns
    
    async def find_emails(
        self,
        website: str,
        business_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        verify_smtp: bool = True
    ) -> Dict[str, Any]:
        """
        Find and verify email addresses for a business.
        
        Args:
            website: Business website URL (e.g., "https://acme.com")
            business_name: Business name (optional)
            first_name: Contact first name (optional, for pattern generation)
            last_name: Contact last name (optional, for pattern generation)
            verify_smtp: Whether to verify emails via SMTP (default: True)
        
        Returns:
            {
                'emails_found': ['info@acme.com', 'contact@acme.com'],
                'verified_emails': ['info@acme.com'],
                'methods_used': ['scraping', 'pattern_generation', 'smtp_verification'],
                'confidence_scores': {'info@acme.com': 0.95},
                'domain': 'acme.com',
                'success': True
            }
        """
        result = {
            'emails_found': [],
            'verified_emails': [],
            'methods_used': [],
            'confidence_scores': {},
            'domain': None,
            'success': False,
            'errors': []
        }
        
        try:
            # Step 1: Extract domain from website
            domain = self.pattern_generator.extract_domain_from_url(website)
            
            if not domain:
                result['errors'].append('Could not extract domain from website')
                return result
            
            result['domain'] = domain
            logger.info(f"Finding emails for domain: {domain}")
            
            # Step 2: Scrape contact pages for existing emails
            scraped_emails = []
            try:
                scraped_emails = await self.contact_scraper.scrape_emails(domain)
                if scraped_emails:
                    result['methods_used'].append('scraping')
                    result['emails_found'].extend(scraped_emails)
                    logger.info(f"Scraped {len(scraped_emails)} emails from {domain}")
                    
                    # High confidence for scraped emails
                    for email in scraped_emails:
                        result['confidence_scores'][email] = 0.95
            
            except Exception as e:
                logger.warning(f"Contact scraping failed for {domain}: {e}")
                result['errors'].append(f'Scraping error: {str(e)}')
            
            # Step 3: Generate email patterns
            generated_patterns = []
            try:
                patterns = self.pattern_generator.generate_emails(
                    domain=domain,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Limit number of patterns to try
                patterns = patterns[:self.max_patterns]
                generated_patterns = [email for email, pattern in patterns]
                
                if generated_patterns:
                    result['methods_used'].append('pattern_generation')
                    logger.info(f"Generated {len(generated_patterns)} email patterns")
            
            except Exception as e:
                logger.warning(f"Pattern generation failed for {domain}: {e}")
                result['errors'].append(f'Pattern generation error: {str(e)}')
            
            # Step 4: SMTP verification
            emails_to_verify = list(set(scraped_emails + generated_patterns))
            
            if verify_smtp and emails_to_verify:
                try:
                    result['methods_used'].append('smtp_verification')
                    
                    # Verify each email
                    for email in emails_to_verify:
                        verification = self.smtp_validator.verify_email(email)
                        
                        if verification['valid'] and verification['deliverable']:
                            if email not in result['verified_emails']:
                                result['verified_emails'].append(email)
                            
                            # Adjust confidence based on verification
                            if email in scraped_emails:
                                # Scraped + verified = very high confidence
                                result['confidence_scores'][email] = 0.98
                            else:
                                # Pattern + verified = high confidence
                                result['confidence_scores'][email] = 0.85
                        
                        elif email in scraped_emails:
                            # Scraped but couldn't verify - still medium confidence
                            if email not in result['verified_emails']:
                                result['verified_emails'].append(email)
                            result['confidence_scores'][email] = 0.70
                    
                    logger.info(f"Verified {len(result['verified_emails'])} emails via SMTP")
                
                except Exception as e:
                    logger.warning(f"SMTP verification failed: {e}")
                    result['errors'].append(f'SMTP verification error: {str(e)}')
                    
                    # If verification fails, use scraped emails anyway
                    result['verified_emails'] = scraped_emails
            else:
                # No SMTP verification - use all found emails
                result['verified_emails'] = scraped_emails
            
            # Step 5: Ensure unique emails
            result['emails_found'] = list(set(result['emails_found']))
            result['verified_emails'] = list(set(result['verified_emails']))
            
            # Step 6: Sort by confidence
            result['verified_emails'].sort(
                key=lambda e: result['confidence_scores'].get(e, 0),
                reverse=True
            )
            
            result['success'] = len(result['verified_emails']) > 0
            
            if result['success']:
                logger.info(f"✅ Successfully found {len(result['verified_emails'])} emails for {domain}")
            else:
                logger.info(f"❌ No emails found for {domain}")
            
            return result
        
        except Exception as e:
            logger.error(f"Email finding failed for {website}: {e}")
            result['errors'].append(f'Fatal error: {str(e)}')
            return result
    
    def find_emails_sync(
        self,
        website: str,
        business_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        verify_smtp: bool = True
    ) -> Dict[str, Any]:
        """
        Synchronous version of find_emails.
        Useful for non-async contexts.
        """
        return asyncio.run(
            self.find_emails(
                website=website,
                business_name=business_name,
                first_name=first_name,
                last_name=last_name,
                verify_smtp=verify_smtp
            )
        )
    
    def quick_find(self, website: str) -> List[str]:
        """
        Quick email finding - just returns list of emails.
        
        Args:
            website: Business website URL
        
        Returns:
            List of verified email addresses
        """
        result = self.find_emails_sync(website=website, verify_smtp=True)
        return result.get('verified_emails', [])
    
    def _get_whois_emails(self, domain: str) -> List[str]:
        """
        Extract emails from WHOIS domain records.
        
        Args:
            domain: Domain to lookup (e.g., "acme.com")
        
        Returns:
            List of email addresses from WHOIS records
        """
        try:
            logger.info(f"Looking up WHOIS data for {domain}")
            w = whois.whois(domain)
            emails = []
            
            # WHOIS data format varies by registrar
            if hasattr(w, 'emails'):
                if isinstance(w.emails, list):
                    emails.extend(w.emails)
                elif isinstance(w.emails, str):
                    emails.append(w.emails)
            
            # Also check registrant_email field
            if hasattr(w, 'registrant_email') and w.registrant_email:
                if isinstance(w.registrant_email, list):
                    emails.extend(w.registrant_email)
                elif isinstance(w.registrant_email, str):
                    emails.append(w.registrant_email)
            
            # Filter out privacy-protected/redacted emails
            filtered = [
                e.lower().strip() for e in emails
                if e and not any(keyword in e.lower() for keyword in [
                    'privacy', 'protected', 'redacted', 'proxy', 
                    'whoisguard', 'domains by proxy', 'data redacted'
                ])
            ]
            
            # Remove duplicates
            filtered = list(set(filtered))
            
            logger.info(f"Found {len(filtered)} WHOIS emails for {domain}")
            return filtered
        
        except Exception as e:
            logger.debug(f"WHOIS lookup failed for {domain}: {e}")
            return []


class EmailEnrichmentService:
    """
    Complete email enrichment service combining all methods.
    
    Methods:
    1. Pattern-based generation + SMTP verification
    2. Contact page scraping
    3. WHOIS domain lookup
    
    100% free - no paid APIs!
    """
    
    def __init__(self):
        self.pattern_gen = EmailPatternGenerator()
        self.smtp_validator = SMTPEmailValidator()
        self.contact_scraper = ContactPageScraper()
        self.email_finder = EmailFinder()
    
    async def enrich_emails(
        self,
        domain: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main enrichment workflow combining all methods.
        
        Workflow:
        1. Generate possible email patterns
        2. Verify each email via SMTP
        3. Scrape contact page for emails
        4. Check WHOIS for registrant email
        5. Deduplicate and score by confidence
        
        Args:
            domain: Company domain (e.g., "acme.com")
            first_name: Optional first name for pattern generation
            last_name: Optional last name for pattern generation
            company_name: Optional company name for context
        
        Returns:
            {
                'domain': 'acme.com',
                'company_name': 'Acme Corp',
                'emails': [
                    {
                        'email': 'john@acme.com',
                        'verified': True,
                        'confidence': 90,
                        'method': 'smtp_verified',
                        'pattern': '{first}@{domain}'
                    }
                ],
                'total_found': 3,
                'verified_count': 2,
                'enriched_at': '2025-10-12T06:00:00Z',
                'methods_used': ['smtp', 'scraping', 'whois']
            }
        """
        logger.info(f"Starting email enrichment for domain: {domain}")
        
        all_emails = []
        methods_used = set()
        
        # Method 1: Pattern-based generation + SMTP verification
        logger.info("Method 1: Pattern generation + SMTP verification")
        pattern_emails = self.pattern_gen.generate_emails(domain, first_name, last_name)
        
        # Limit to 15 patterns to avoid overwhelming SMTP servers
        for email, pattern in pattern_emails[:15]:
            verification = self.smtp_validator.verify_email(email)
            
            if verification['deliverable']:
                all_emails.append({
                    'email': email,
                    'verified': True,
                    'confidence': 90,
                    'method': 'smtp_verified',
                    'pattern': pattern,
                    'first_name': first_name,
                    'last_name': last_name
                })
                methods_used.add('smtp')
                logger.info(f"✅ Verified via SMTP: {email}")
        
        # Method 2: Contact page scraping
        logger.info("Method 2: Contact page scraping")
        try:
            scraped_emails = await self.contact_scraper.scrape_emails(domain)
            
            for email in scraped_emails:
                # Verify scraped emails via SMTP
                verification = self.smtp_validator.verify_email(email)
                
                all_emails.append({
                    'email': email,
                    'verified': verification['deliverable'],
                    'confidence': 95 if verification['deliverable'] else 70,
                    'method': 'scraped',
                    'pattern': 'found_on_website'
                })
                methods_used.add('scraping')
                logger.info(f"📄 Found on website: {email}")
        
        except Exception as e:
            logger.warning(f"Contact scraping failed: {e}")
        
        # Method 3: WHOIS lookup
        logger.info("Method 3: WHOIS email lookup")
        try:
            whois_emails = self.email_finder._get_whois_emails(domain)
            
            for email in whois_emails:
                # WHOIS emails may be outdated, so lower confidence
                all_emails.append({
                    'email': email,
                    'verified': False,
                    'confidence': 40,
                    'method': 'whois',
                    'pattern': 'domain_registration'
                })
                methods_used.add('whois')
                logger.info(f"🔍 Found in WHOIS: {email}")
        
        except Exception as e:
            logger.warning(f"WHOIS lookup failed: {e}")
        
        # Deduplicate by email address (keep highest confidence)
        unique_emails = {}
        for email_obj in all_emails:
            email_addr = email_obj['email']
            
            if email_addr not in unique_emails:
                unique_emails[email_addr] = email_obj
            else:
                # Keep version with higher confidence
                if email_obj['confidence'] > unique_emails[email_addr]['confidence']:
                    unique_emails[email_addr] = email_obj
        
        # Sort by confidence (highest first)
        final_emails = sorted(
            unique_emails.values(),
            key=lambda x: x['confidence'],
            reverse=True
        )
        
        logger.info(f"✅ Enrichment complete: Found {len(final_emails)} unique emails")
        
        return {
            'domain': domain,
            'company_name': company_name,
            'emails': final_emails,
            'total_found': len(final_emails),
            'verified_count': sum(1 for e in final_emails if e['verified']),
            'enriched_at': datetime.utcnow().isoformat(),
            'methods_used': list(methods_used)
        }
