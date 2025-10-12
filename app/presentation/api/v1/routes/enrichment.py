"""
FastAPI endpoints for email enrichment.
Provides REST API to trigger and monitor email enrichment tasks.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["Email Enrichment"])


# Pydantic Models
class EnrichmentResponse(BaseModel):
    """Response model for enrichment trigger."""
    status: str = Field(..., description="Task status (queued, processing, completed)")
    task_id: str = Field(..., description="Celery task ID for tracking")
    message: str = Field(..., description="Human-readable status message")


class EnrichedEmail(BaseModel):
    """Model for enriched email data."""
    email: str = Field(..., description="Email address")
    verified: bool = Field(..., description="Whether email was verified via SMTP")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    method: str = Field(..., description="Discovery method (smtp_verified, scraped, whois)")
    pattern: Optional[str] = Field(None, description="Pattern used to generate email")


class EmailEnrichmentStatus(BaseModel):
    """Model for enrichment status response."""
    company_id: str
    has_emails: bool
    email_count: int
    emails: List[EnrichedEmail] = []
    enriched_at: Optional[str] = None
    methods_used: List[str] = []


# API Endpoints

@router.post("/companies/{company_id}/enrich-email", response_model=EnrichmentResponse)
async def trigger_email_enrichment(company_id: str):
    """
    Trigger email enrichment for a specific company.
    
    **Process:**
    1. Extract domain from company website
    2. Search for emails using:
       - SMTP pattern verification (20+ patterns)
       - Contact page scraping (/contact, /about, /team)
       - WHOIS domain lookup
    3. Verify email deliverability via SMTP
    4. Store enriched emails in database
    
    **Returns:** Task ID for status tracking
    
    **Example:**
    ```bash
    POST /enrichment/companies/507f1f77bcf86cd799439011/enrich-email
    ```
    
    **Response:**
    ```json
    {
      "status": "queued",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "message": "Email enrichment queued for company 507f..."
    }
    ```
    """
    # Import here to avoid circular imports
    from app.db_mongo import get_business_by_id
    from app.infrastructure.queue.tasks.enrichment_tasks import enrich_lead_email_task
    
    # Verify company exists
    company = get_business_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    # Check if company has a website
    if not company.get('website'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company has no website URL. Email enrichment requires a website."
        )
    
    # Queue enrichment task
    try:
        # Type ignore: Celery's shared_task decorator adds .delay() method
        task = enrich_lead_email_task.delay(company_id)  # type: ignore
        
        logger.info(f"✅ Queued email enrichment for company {company_id}, task_id: {task.id}")
        
        return EnrichmentResponse(
            status="queued",
            task_id=task.id,
            message=f"Email enrichment queued for company {company_id}"
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to queue enrichment for {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue enrichment task: {str(e)}"
        )


@router.get("/companies/{company_id}/emails", response_model=List[EnrichedEmail])
async def get_enriched_emails(company_id: str):
    """
    Get all enriched emails for a company.
    
    **Returns:** List of emails with metadata:
    - Email address
    - Verification status (SMTP verified)
    - Confidence score (0-100)
    - Discovery method (smtp_verified, scraped, whois)
    - Pattern used (if applicable)
    
    **Example:**
    ```bash
    GET /enrichment/companies/507f1f77bcf86cd799439011/emails
    ```
    
    **Response:**
    ```json
    [
      {
        "email": "contact@business.com",
        "verified": true,
        "confidence": 90,
        "method": "smtp_verified",
        "pattern": "contact@{domain}"
      },
      {
        "email": "info@business.com",
        "verified": true,
        "confidence": 95,
        "method": "scraped",
        "pattern": "found_on_website"
      }
    ]
    ```
    """
    from app.db_mongo import get_business_by_id
    
    company = get_business_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    emails = company.get('emails', [])
    
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enriched emails found. Trigger enrichment first using POST /enrichment/companies/{id}/enrich-email"
        )
    
    return emails


@router.get("/companies/{company_id}/status", response_model=EmailEnrichmentStatus)
async def get_enrichment_status(company_id: str):
    """
    Check email enrichment status for a company.
    
    **Returns:** Current enrichment status including:
    - Whether emails have been enriched
    - Number of emails found
    - All enriched emails with details
    - Enrichment timestamp
    - Methods used
    
    **Example:**
    ```bash
    GET /enrichment/companies/507f1f77bcf86cd799439011/status
    ```
    """
    from app.db_mongo import get_business_by_id
    
    company = get_business_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    emails = company.get('emails', [])
    
    return EmailEnrichmentStatus(
        company_id=company_id,
        has_emails=bool(emails),
        email_count=len(emails),
        emails=emails if emails else [],
        enriched_at=company.get('email_enriched_at'),
        methods_used=company.get('enrichment_methods', [])
    )


@router.post("/admin/batch-enrich", response_model=EnrichmentResponse)
async def trigger_batch_enrichment(limit: int = 100):
    """
    Trigger batch email enrichment for all leads without emails.
    
    **Admin endpoint** to enrich multiple leads at once.
    Processes leads that have a website but no enriched emails.
    
    **Args:**
    - `limit`: Maximum number of leads to enrich (default: 100, max: 1000)
    
    **Example:**
    ```bash
    POST /enrichment/admin/batch-enrich?limit=50
    ```
    
    **Response:**
    ```json
    {
      "status": "queued",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "message": "Batch enrichment queued for up to 50 leads"
    }
    ```
    """
    from app.infrastructure.queue.tasks.enrichment_tasks import batch_enrich_emails_task
    
    # Validate limit
    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000. Please use smaller batches."
        )
    
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be at least 1"
        )
    
    # Queue batch enrichment task
    try:
        # Type ignore: Celery's shared_task decorator adds .delay() method
        task = batch_enrich_emails_task.delay(limit)  # type: ignore
        
        logger.info(f"✅ Queued batch enrichment for up to {limit} leads, task_id: {task.id}")
        
        return EnrichmentResponse(
            status="queued",
            task_id=task.id,
            message=f"Batch enrichment queued for up to {limit} leads"
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to queue batch enrichment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue batch enrichment: {str(e)}"
        )


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Check status of an enrichment task.
    
    **Returns:**
    ```json
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "SUCCESS",
      "result": {
        "status": "success",
        "lead_id": "507f...",
        "emails_found": 3,
        "verified_count": 2,
        "methods_used": ["smtp", "scraping"]
      }
    }
    ```
    
    **Possible statuses:**
    - `PENDING`: Task is waiting to be executed
    - `STARTED`: Task is currently running
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed
    - `RETRY`: Task is being retried
    
    **Example:**
    ```bash
    GET /enrichment/task/550e8400-e29b-41d4-a716-446655440000/status
    ```
    """
    try:
        from celery.result import AsyncResult
        
        task = AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task.state,
            'result': task.result if task.ready() else None
        }
        
        # Add traceback if task failed
        if task.failed():
            response['error'] = str(task.info) if task.info else 'Unknown error'
            response['traceback'] = str(task.traceback) if task.traceback else None
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task status: {str(e)}"
        )
