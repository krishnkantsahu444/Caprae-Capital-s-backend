# 🚀 3-DAY CRITICAL PATH TO +10 POINTS

**Current:** 17/40 (42.5%) → **Target:** 27/40 (67.5%)  
**Timeline:** 3 days intensive work  
**Focus:** Maximum impact, minimum time

---

## DAY 1: Lead Scoring (+3 points) 🔥

### Morning (4 hours)
**Create Lead Scoring Engine**

```bash
# 1. Create file structure
mkdir -p app/domain/services
mkdir -p app/infrastructure/queue/tasks
mkdir -p app/presentation/api/v1/routes

# 2. Install dependencies
pip install python-dateutil
```

**File 1:** `app/domain/services/lead_scoring.py`
- Copy implementation from EVALUATION_CRITERIA_IMPLEMENTATION.md
- Test with sample lead data

**File 2:** Update MongoDB schema
```python
# Add to app/db_mongo.py

def update_business_score(business_id: str, score_data: dict):
    """Update business with lead score"""
    collection = get_collection()
    collection.update_one(
        {"_id": ObjectId(business_id)},
        {"$set": {
            "lead_score": score_data['total_score'],
            "lead_tier": score_data['tier'],
            "score_breakdown": score_data['breakdown'],
            "scored_at": score_data['scored_at']
        }}
    )

def search_businesses_by_tier(tier: str, limit: int = 100):
    """Search businesses by lead tier"""
    collection = get_collection()
    query = {"lead_tier": tier} if tier else {}
    return list(collection.find(query).sort("lead_score", -1).limit(limit))
```

### Afternoon (4 hours)
**Integrate Scoring into Scraping Pipeline**

**File 3:** `app/infrastructure/queue/tasks/scoring_tasks.py`
```python
from celery import shared_task
from app.domain.services.lead_scoring import LeadScoringService
from app.db_mongo import get_all_businesses, update_business_score, get_business_by_id

@shared_task(name="score_all_leads", bind=True)
def score_all_leads(self):
    """Background job to score all leads"""
    collection = get_collection()
    leads = collection.find({})
    scored_count = 0
    
    for lead in leads:
        try:
            score_data = LeadScoringService.calculate_score(lead)
            update_business_score(str(lead['_id']), score_data)
            scored_count += 1
        except Exception as e:
            print(f"Error scoring lead {lead.get('_id')}: {e}")
    
    return {'status': 'completed', 'leads_scored': scored_count}

@shared_task(name="score_single_lead")
def score_single_lead(lead_id: str):
    """Score a single lead after scraping"""
    lead = get_business_by_id(lead_id)
    if lead:
        score_data = LeadScoringService.calculate_score(lead)
        update_business_score(lead_id, score_data)
        return score_data
    return None
```

**File 4:** Update `app/crawlers/google_maps_crawlee.py`
```python
# After saving business, trigger scoring
from app.infrastructure.queue.tasks.scoring_tasks import score_single_lead

# In handle_page() method, after save_business(business):
if saved:
    # Trigger async scoring
    score_single_lead.delay(str(business_id))
```

**File 5:** `app/presentation/api/v1/routes/scoring.py`
```python
from fastapi import APIRouter, HTTPException
from app.domain.services.lead_scoring import LeadScoringService
from app.infrastructure.queue.tasks.scoring_tasks import score_all_leads
from app.db_mongo import get_business_by_id, search_businesses_by_tier

router = APIRouter(prefix="/scoring", tags=["Lead Scoring"])

@router.get("/companies/{company_id}/score-breakdown")
async def get_score_breakdown(company_id: str):
    """Get detailed score breakdown"""
    from bson import ObjectId
    lead = get_business_by_id(ObjectId(company_id))
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    score_data = LeadScoringService.calculate_score(lead)
    return score_data

@router.post("/admin/rescore-all")
async def trigger_rescoring():
    """Trigger background rescoring"""
    task = score_all_leads.delay()
    return {'status': 'queued', 'task_id': task.id}

@router.get("/companies/by-tier")
async def list_by_tier(tier: str = None, limit: int = 100):
    """List companies by tier"""
    leads = search_businesses_by_tier(tier, limit)
    return {'results': leads, 'count': len(leads), 'tier': tier}
```

**File 6:** Register routes in `app/main.py`
```python
from app.presentation.api.v1.routes import scoring

app.include_router(scoring.router, prefix="/api/v1")
```

### Test (evening)
```bash
# Run scorer on existing data
curl -X POST http://localhost:8000/api/v1/scoring/admin/rescore-all

# Check HOT leads
curl http://localhost:8000/api/v1/scoring/companies/by-tier?tier=HOT

# Get score breakdown
curl http://localhost:8000/api/v1/scoring/companies/{id}/score-breakdown
```

---

## DAY 2: Email Enrichment (+2 points) 🔥

### Morning (4 hours)
**Setup Hunter.io Integration**

```bash
# Install dependencies
pip install httpx aiohttp
```

**File 1:** `app/infrastructure/enrichment/hunter_client.py`
```python
import httpx
import os
from typing import List, Dict, Any, Optional

class HunterClient:
    """Hunter.io API client for email enrichment"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('HUNTER_API_KEY')
        self.base_url = "https://api.hunter.io/v2"
    
    async def find_emails(self, domain: str) -> List[Dict[str, Any]]:
        """Find emails for a domain"""
        if not self.api_key:
            return []
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/domain-search",
                    params={
                        "domain": domain,
                        "api_key": self.api_key,
                        "limit": 5
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                emails = data.get('data', {}).get('emails', [])
                
                return [
                    {
                        'email': email['value'],
                        'first_name': email.get('first_name'),
                        'last_name': email.get('last_name'),
                        'position': email.get('position'),
                        'confidence': email.get('confidence', 0),
                        'type': email.get('type'),  # personal/generic
                        'verified': email.get('verification', {}).get('status') == 'valid'
                    }
                    for email in emails
                ]
            except Exception as e:
                print(f"Error fetching emails from Hunter.io: {e}")
                return []
    
    async def verify_email(self, email: str) -> Dict[str, Any]:
        """Verify single email address"""
        if not self.api_key:
            return {'email': email, 'status': 'unknown'}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/email-verifier",
                    params={
                        "email": email,
                        "api_key": self.api_key
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return {'email': email, 'status': 'unknown'}
                
                data = response.json()
                verification = data.get('data', {})
                
                return {
                    'email': email,
                    'status': verification.get('status'),  # valid/invalid/accept_all/unknown
                    'score': verification.get('score', 0),
                    'smtp_check': verification.get('smtp_check'),
                    'disposable': verification.get('disposable', False),
                    'webmail': verification.get('webmail', False)
                }
            except Exception as e:
                print(f"Error verifying email: {e}")
                return {'email': email, 'status': 'error'}
    
    def extract_domain_from_website(self, website: str) -> Optional[str]:
        """Extract domain from website URL"""
        if not website:
            return None
        
        # Remove protocol
        domain = website.replace('http://', '').replace('https://', '')
        # Remove www
        domain = domain.replace('www.', '')
        # Remove path
        domain = domain.split('/')[0]
        # Remove port
        domain = domain.split(':')[0]
        
        return domain if domain else None
```

### Afternoon (4 hours)
**Create Enrichment Tasks**

**File 2:** `app/infrastructure/queue/tasks/enrichment_tasks.py`
```python
from celery import shared_task
from app.infrastructure.enrichment.hunter_client import HunterClient
from app.db_mongo import get_business_by_id, update_business_emails

@shared_task(name="enrich_emails", bind=True)
async def enrich_emails(self, business_id: str):
    """Enrich business with emails from Hunter.io"""
    from bson import ObjectId
    
    business = get_business_by_id(ObjectId(business_id))
    if not business:
        return {'status': 'error', 'message': 'Business not found'}
    
    website = business.get('website')
    if not website:
        return {'status': 'skipped', 'message': 'No website to enrich'}
    
    hunter = HunterClient()
    domain = hunter.extract_domain_from_website(website)
    
    if not domain:
        return {'status': 'error', 'message': 'Invalid domain'}
    
    # Find emails
    emails = await hunter.find_emails(domain)
    
    if not emails:
        return {'status': 'no_results', 'message': 'No emails found'}
    
    # Store emails in database
    update_business_emails(ObjectId(business_id), emails)
    
    return {
        'status': 'completed',
        'business_id': business_id,
        'emails_found': len(emails),
        'emails': emails
    }

@shared_task(name="enrich_all_emails", bind=True)
async def enrich_all_emails(self):
    """Batch enrichment for all businesses with websites"""
    from app.db_mongo import get_collection
    
    collection = get_collection()
    businesses = collection.find({
        'website': {'$exists': True, '$ne': None},
        'emails': {'$exists': False}  # Only enrich if no emails yet
    }).limit(100)
    
    enriched_count = 0
    for business in businesses:
        try:
            await enrich_emails(str(business['_id']))
            enriched_count += 1
        except Exception as e:
            print(f"Error enriching {business.get('_id')}: {e}")
    
    return {'status': 'completed', 'enriched': enriched_count}
```

**File 3:** Update `app/db_mongo.py`
```python
def update_business_emails(business_id, emails: list):
    """Update business with enriched emails"""
    from datetime import datetime
    
    collection = get_collection()
    collection.update_one(
        {"_id": business_id},
        {"$set": {
            "emails": emails,
            "email_enriched_at": datetime.utcnow()
        }}
    )
```

**File 4:** Create API endpoints
```python
# app/presentation/api/v1/routes/enrichment.py

from fastapi import APIRouter, HTTPException
from app.infrastructure.queue.tasks.enrichment_tasks import enrich_emails

router = APIRouter(prefix="/enrichment", tags=["Enrichment"])

@router.post("/companies/{company_id}/enrich-emails")
async def trigger_email_enrichment(company_id: str):
    """Trigger email enrichment for a company"""
    task = enrich_emails.delay(company_id)
    return {
        'status': 'queued',
        'task_id': task.id,
        'message': f'Email enrichment queued for {company_id}'
    }

@router.get("/companies/{company_id}/emails")
async def get_enriched_emails(company_id: str):
    """Get enriched emails for a company"""
    from bson import ObjectId
    from app.db_mongo import get_business_by_id
    
    business = get_business_by_id(ObjectId(company_id))
    if not business:
        raise HTTPException(404, "Company not found")
    
    return {
        'business_id': company_id,
        'business_name': business.get('name'),
        'website': business.get('website'),
        'emails': business.get('emails', []),
        'enriched_at': business.get('email_enriched_at')
    }
```

**File 5:** Add to `.env`
```bash
# Hunter.io API Key (sign up at hunter.io)
HUNTER_API_KEY=your_hunter_api_key_here
```

### Test
```bash
# Enrich single business
curl -X POST http://localhost:8000/api/v1/enrichment/companies/{id}/enrich-emails

# Get enriched emails
curl http://localhost:8000/api/v1/enrichment/companies/{id}/emails
```

---

## DAY 3: Webhooks + Documentation (+3.5 points) 🔥

### Morning (3 hours)
**Webhook System**

**File 1:** `app/infrastructure/webhooks/webhook_service.py`
```python
import httpx
import hmac
import hashlib
from typing import Dict, Any
from datetime import datetime

class WebhookService:
    """Service for delivering webhooks"""
    
    @staticmethod
    async def deliver(url: str, event: str, data: Dict[str, Any], secret: str = None):
        """Deliver webhook to URL"""
        payload = {
            'event': event,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        headers = {'Content-Type': 'application/json'}
        
        # Add HMAC signature if secret provided
        if secret:
            signature = WebhookService._generate_signature(payload, secret)
            headers['X-Webhook-Signature'] = signature
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                return {
                    'success': response.status_code == 200,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _generate_signature(payload: Dict, secret: str) -> str:
        """Generate HMAC signature for payload"""
        import json
        message = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature
```

**File 2:** `app/infrastructure/queue/tasks/webhook_tasks.py`
```python
from celery import shared_task
from app.infrastructure.webhooks.webhook_service import WebhookService

@shared_task(name="send_webhook", max_retries=3)
async def send_webhook(url: str, event: str, data: dict, secret: str = None):
    """Send webhook with retry logic"""
    result = await WebhookService.deliver(url, event, data, secret)
    
    if not result['success']:
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries))
    
    return result
```

**File 3:** Integrate webhooks into scraper
```python
# In google_maps_crawlee.py after scoring

from app.infrastructure.queue.tasks.webhook_tasks import send_webhook

# After lead is scored
if lead_tier == 'HOT':
    # Send webhook for HOT lead
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        send_webhook.delay(
            url=webhook_url,
            event='lead.hot_tier',
            data={
                'business_id': str(business_id),
                'business_name': business.get('name'),
                'lead_score': score_data['total_score'],
                'tier': 'HOT'
            }
        )
```

### Afternoon (5 hours)
**Documentation Sprint**

**File 1:** Update `README.md` with complete guide
**File 2:** Create `docs/API_DOCUMENTATION.md`
**File 3:** Create `docs/PRODUCT_STRATEGY.md`
**File 4:** Create `docs/ARCHITECTURE.md`
**File 5:** Record 5-minute video demo

---

## VERIFICATION CHECKLIST

### Day 1 Complete ✅
- [ ] Lead scoring engine working
- [ ] Scoring integrated into scraper
- [ ] API endpoints return scores
- [ ] HOT/WARM/COLD tiers assigned
- [ ] Background rescoring task works

### Day 2 Complete ✅
- [ ] Hunter.io API integrated
- [ ] Email enrichment working
- [ ] Emails stored in MongoDB
- [ ] API endpoints return enriched emails
- [ ] Batch enrichment task works

### Day 3 Complete ✅
- [ ] Webhooks deliver on HOT leads
- [ ] Retry logic working
- [ ] Complete API documentation
- [ ] Product strategy doc created
- [ ] Video demo recorded

---

## EXPECTED SCORE AFTER 3 DAYS

| Criteria | Before | After | Gain |
|----------|--------|-------|------|
| Business Use Case | 5/10 | **9/10** | +4 |
| Technicality | 8/10 | **9/10** | +1 |
| Other (Innovation) | 2/5 | **5/5** | +3 |
| **TOTAL** | **17/40** | **25/40** | **+8** |

**With full 7-day implementation: 27/40 achievable!**
