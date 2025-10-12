"""
Quick demo of the Email Enrichment System.
Run this to see the system in action!
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.enrichment import EmailFinder, EmailPatternGenerator, SMTPEmailValidator


async def demo_email_enrichment():
    """
    Demo: Find emails for a real business
    """
    print("=" * 70)
    print("📧 EMAIL ENRICHMENT SYSTEM DEMO")
    print("=" * 70)
    print()
    
    # Demo 1: Pattern Generation
    print("📦 DEMO 1: Email Pattern Generation")
    print("-" * 70)
    
    domain = "example.com"
    patterns = EmailPatternGenerator.generate_emails(
        domain=domain,
        first_name="John",
        last_name="Doe"
    )
    
    print(f"Generated {len(patterns)} email patterns for {domain}:")
    for i, (email, pattern) in enumerate(patterns[:10], 1):
        print(f"   {i}. {email:30} (pattern: {pattern})")
    print(f"   ... and {len(patterns) - 10} more patterns")
    print()
    
    # Demo 2: Domain Extraction
    print("🌐 DEMO 2: Domain Extraction from URLs")
    print("-" * 70)
    
    test_urls = [
        "https://www.google.com",
        "http://example.com/contact",
        "www.github.com",
        "microsoft.com"
    ]
    
    for url in test_urls:
        domain = EmailPatternGenerator.extract_domain_from_url(url)
        print(f"   {url:40} → {domain}")
    print()
    
    # Demo 3: MX Record Lookup
    print("🔍 DEMO 3: MX Record Validation")
    print("-" * 70)
    
    validator = SMTPEmailValidator()
    test_domains = ["google.com", "github.com", "example.com"]
    
    for domain in test_domains:
        mx_records = validator.get_mx_records(domain)
        if mx_records:
            print(f"   ✅ {domain:20} has {len(mx_records)} MX records")
            print(f"      Primary MX: {mx_records[0]}")
        else:
            print(f"   ❌ {domain:20} has no MX records")
    print()
    
    # Demo 4: Email Verification
    print("✉️  DEMO 4: SMTP Email Verification")
    print("-" * 70)
    
    test_emails = [
        "info@google.com",        # Valid format, real domain
        "notreal@thisdoesnotexist99999.com",  # Invalid domain
        "not-an-email",           # Invalid syntax
    ]
    
    for email in test_emails:
        result = validator.verify_email(email)
        status = "✅ VALID" if result['valid'] else "❌ INVALID"
        print(f"   {status} {email:40}")
        print(f"           MX Records: {result['mx_records']}")
        print(f"           Deliverable: {result['deliverable']}")
        if result['error']:
            print(f"           Error: {result['error']}")
    print()
    
    # Demo 5: Complete Email Finding
    print("🚀 DEMO 5: Complete Email Finding Workflow")
    print("-" * 70)
    print("Finding emails for: google.com")
    print("Methods: Contact scraping + Pattern generation + SMTP verification")
    print()
    
    finder = EmailFinder(max_patterns=10)
    
    result = await finder.find_emails(
        website="https://google.com",
        verify_smtp=False  # Skip SMTP for demo speed
    )
    
    print(f"Results:")
    print(f"   Domain: {result['domain']}")
    print(f"   Methods Used: {', '.join(result['methods_used'])}")
    print(f"   Emails Found: {len(result['emails_found'])}")
    print(f"   Verified Emails: {len(result['verified_emails'])}")
    
    if result['verified_emails']:
        print(f"\n   Top Emails:")
        for email in result['verified_emails'][:5]:
            confidence = result['confidence_scores'].get(email, 0)
            print(f"      • {email:35} (confidence: {confidence:.2f})")
    
    print()
    
    # Demo 6: Quick Find
    print("⚡ DEMO 6: Quick Find (One-Liner)")
    print("-" * 70)
    
    print("Quick finding emails for microsoft.com...")
    # Use async version since we're already in async context
    result = await finder.find_emails("microsoft.com", verify_smtp=False)
    emails = result['verified_emails']
    
    print(f"Found {len(emails)} emails:")
    for email in emails[:5]:
        print(f"   • {email}")
    
    print()
    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()
    print("💡 Key Features:")
    print("   • 20+ email pattern formats")
    print("   • SMTP verification (100% free)")
    print("   • Contact page scraping")
    print("   • MX record validation")
    print("   • Confidence scoring")
    print()
    print("💰 Total Cost: $0.00 (100% free & open source)")
    print()


if __name__ == "__main__":
    asyncio.run(demo_email_enrichment())
