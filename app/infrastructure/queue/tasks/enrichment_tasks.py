"""
Celery background tasks for email enrichment.
Runs email finding in background without blocking API.
"""

from celery import shared_task
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task(name="enrich_lead_email", bind=True, max_retries=3)
def enrich_lead_email_task(self, lead_id: str):
    """
    Enrich a single lead with email addresses in background.
    
    Workflow:
    1. Get lead from database
    2. Extract domain from website
    3. Run email enrichment (SMTP + scraping + WHOIS)
    4. Update database with enriched emails
    
    Args:
        lead_id: MongoDB ObjectId as string
    
    Returns:
        {
            'status': 'success',
            'lead_id': '...',
            'emails_found': 3,
            'verified_count': 2,
            'methods_used': ['smtp', 'scraping']
        }
    """
    try:
        logger.info(f"🚀 Starting email enrichment for lead: {lead_id}")
        
        # Import here to avoid circular imports
        from app.infrastructure.enrichment.email_finder import EmailEnrichmentService
        from app.infrastructure.enrichment.email_patterns import EmailPatternGenerator
        from app.db_mongo import get_business_by_id, update_business_emails
        
        # Get lead from database
        lead = get_business_by_id(lead_id)
        if not lead:
            logger.error(f"❌ Lead {lead_id} not found")
            return {'error': 'lead_not_found', 'lead_id': lead_id}
        
        website = lead.get('website')
        company_name = lead.get('name') or lead.get('business_name')
        
        if not website:
            logger.warning(f"⚠️ Lead {lead_id} has no website")
            return {'error': 'no_website', 'lead_id': lead_id}
        
        # Extract domain from website URL
        domain = EmailPatternGenerator.extract_domain_from_url(website)
        
        if not domain:
            logger.error(f"❌ Could not extract domain from {website}")
            return {'error': 'invalid_domain', 'website': website}
        
        logger.info(f"📧 Enriching emails for domain: {domain}")
        
        # Initialize enrichment service
        enricher = EmailEnrichmentService()
        
        # Run enrichment (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                enricher.enrich_emails(
                    domain=domain,
                    company_name=company_name
                )
            )
        finally:
            loop.close()
        
        # Update database with enriched emails
        if result['emails']:
            # Just pass the emails list directly
            update_business_emails(lead_id, result['emails'])
            
            logger.info(f"✅ Successfully enriched {len(result['emails'])} emails for lead {lead_id}")
            logger.info(f"   Verified: {result['verified_count']}/{result['total_found']}")
        else:
            logger.warning(f"⚠️ No emails found for lead {lead_id}")
        
        return {
            'status': 'success' if result['emails'] else 'no_emails_found',
            'lead_id': lead_id,
            'emails_found': len(result['emails']),
            'verified_count': result['verified_count'],
            'methods_used': result['methods_used'],
            'domain': domain
        }
    
    except Exception as e:
        logger.error(f"❌ Email enrichment failed for {lead_id}: {str(e)}")
        
        # Retry with exponential backoff: 60s, 120s, 240s
        retry_countdown = 60 * (2 ** self.request.retries)
        logger.info(f"⏰ Retrying in {retry_countdown}s (attempt {self.request.retries + 1}/3)")
        
        raise self.retry(exc=e, countdown=retry_countdown)


@shared_task(name="batch_enrich_emails")
def batch_enrich_emails_task(limit: int = 100):
    """
    Batch enrichment job for leads without emails.
    Run nightly or on-demand to enrich newly scraped leads.
    
    Args:
        limit: Max number of leads to enrich (default: 100)
    
    Returns:
        {
            'status': 'completed',
            'leads_queued': 50,
            'failures': 2
        }
    """
    logger.info(f"🔄 Starting batch email enrichment (limit={limit})")
    
    # Import here to avoid circular imports
    from app.db_mongo import get_database
    
    try:
        db = get_database()
        
        # Find leads with website but no enriched emails
        leads_cursor = db.businesses.find(
            {
                'website': {'$exists': True, '$ne': '', '$ne': None},
                '$or': [
                    {'emails': {'$exists': False}},
                    {'emails': {'$size': 0}}
                ]
            },
            limit=limit
        )
        
        leads = list(leads_cursor)
        logger.info(f"📊 Found {len(leads)} leads to enrich")
        
        queued_count = 0
        failed_count = 0
        
        for lead in leads:
            try:
                # Queue enrichment task for each lead
                # Type ignore: Celery's shared_task decorator adds .delay() method
                enrich_lead_email_task.delay(str(lead['_id']))  # type: ignore
                queued_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to queue enrichment for {lead['_id']}: {e}")
                failed_count += 1
        
        logger.info(f"✅ Batch enrichment complete: {queued_count} queued, {failed_count} failed")
        
        return {
            'status': 'completed',
            'total_found': len(leads),
            'leads_queued': queued_count,
            'failures': failed_count
        }
    
    except Exception as e:
        logger.error(f"❌ Batch enrichment failed: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
