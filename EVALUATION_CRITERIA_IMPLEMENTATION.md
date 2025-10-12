# 🎯 Backend Implementation Roadmap for Maximum Points

**Target Score:** 27/40 (67.5%) - Backend Only  
**Current Score:** 17/40 (42.5%)  
**Gap to Close:** +10 points  
**Timeline:** 7 days (with critical path: 3-4 days)

---

## 📊 Current Score Breakdown

| Criteria | Current | Target | Gap | Priority |
|----------|---------|--------|-----|----------|
| **Business Use Case** | 5/10 | 10/10 | **+5** | 🔥 CRITICAL |
| **UX/UI** | 2/10 | 2/10 | 0 | ⏭️ Skip (backend only) |
| **Technicality** | 8/10 | 10/10 | **+2** | 🔥 CRITICAL |
| **Design** | 0/5 | 0/5 | 0 | ⏭️ Skip (backend only) |
| **Other (Innovation)** | 2/5 | 5/5 | **+3** | 🔥 CRITICAL |
| **TOTAL** | **17/40** | **27/40** | **+10** | |

---

## 🚀 Critical Path Implementation (3-4 Days)

### Day 1-2: Business Use Case (+5 points)

#### ✅ Feature A: Lead Scoring Algorithm (2 days) 🔥
**Impact:** +3 points | **Priority:** HIGHEST

**Requirements:**
```python
# Multi-factor scoring (0-100 scale)
✅ Completeness Score (25%): phone + website + email
✅ Reputation Score (30%): rating × log(reviews)
✅ Engagement Potential (20%): multiple contact methods
✅ Data Freshness (15%): recency_days < 30
✅ Location Quality (10%): target_market_fit

# Priority Tiers
✅ HOT (80-100): Ready to contact immediately
✅ WARM (60-79): High quality, needs minor enrichment
✅ COLD (40-59): Partial data, needs significant enrichment
✅ LOW (0-39): Poor quality or incomplete

# Automatic Scoring
✅ Score on scrape completion (real-time)
✅ Background re-scoring job (daily via Celery Beat)
✅ Score update on data enrichment

# API Endpoints
GET /companies/{id}/score-breakdown
GET /companies/?tier=HOT&sort_by=score
POST /admin/rescore-all (trigger batch scoring)
```

**Implementation:**
```python
# app/domain/services/lead_scoring.py

from typing import Dict, Any
from datetime import datetime, timedelta
import math

class LeadScoringService:
    """
    Lead scoring engine based on multiple quality factors.
    Score range: 0-100
    """
    
    # Score weights (must sum to 1.0)
    WEIGHTS = {
        'completeness': 0.25,
        'reputation': 0.30,
        'engagement': 0.20,
        'freshness': 0.15,
        'location': 0.10,
    }
    
    # Tier thresholds
    TIERS = {
        'HOT': 80,
        'WARM': 60,
        'COLD': 40,
        'LOW': 0,
    }
    
    @staticmethod
    def calculate_score(lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive lead score.
        
        Returns:
            {
                'total_score': 85,
                'tier': 'HOT',
                'breakdown': {
                    'completeness': {'score': 100, 'weight': 0.25, 'contribution': 25},
                    'reputation': {'score': 95, 'weight': 0.30, 'contribution': 28.5},
                    ...
                },
                'missing_fields': ['email', 'hours'],
                'recommendations': ['Enrich email via Hunter.io']
            }
        """
        
        # Calculate component scores
        completeness = LeadScoringService._score_completeness(lead)
        reputation = LeadScoringService._score_reputation(lead)
        engagement = LeadScoringService._score_engagement(lead)
        freshness = LeadScoringService._score_freshness(lead)
        location = LeadScoringService._score_location(lead)
        
        # Calculate weighted total
        total_score = (
            completeness * LeadScoringService.WEIGHTS['completeness'] +
            reputation * LeadScoringService.WEIGHTS['reputation'] +
            engagement * LeadScoringService.WEIGHTS['engagement'] +
            freshness * LeadScoringService.WEIGHTS['freshness'] +
            location * LeadScoringService.WEIGHTS['location']
        )
        
        # Determine tier
        tier = LeadScoringService._get_tier(total_score)
        
        # Build breakdown
        breakdown = {
            'completeness': {
                'score': completeness,
                'weight': LeadScoringService.WEIGHTS['completeness'],
                'contribution': completeness * LeadScoringService.WEIGHTS['completeness']
            },
            'reputation': {
                'score': reputation,
                'weight': LeadScoringService.WEIGHTS['reputation'],
                'contribution': reputation * LeadScoringService.WEIGHTS['reputation']
            },
            'engagement': {
                'score': engagement,
                'weight': LeadScoringService.WEIGHTS['engagement'],
                'contribution': engagement * LeadScoringService.WEIGHTS['engagement']
            },
            'freshness': {
                'score': freshness,
                'weight': LeadScoringService.WEIGHTS['freshness'],
                'contribution': freshness * LeadScoringService.WEIGHTS['freshness']
            },
            'location': {
                'score': location,
                'weight': LeadScoringService.WEIGHTS['location'],
                'contribution': location * LeadScoringService.WEIGHTS['location']
            },
        }
        
        # Identify missing fields and recommendations
        missing_fields = []
        recommendations = []
        
        if not lead.get('phone'):
            missing_fields.append('phone')
            recommendations.append('Add phone number from detail page')
        if not lead.get('website'):
            missing_fields.append('website')
            recommendations.append('Add website from detail page')
        if not lead.get('email'):
            missing_fields.append('email')
            recommendations.append('Enrich email via Hunter.io')
        if not lead.get('rating') or lead.get('rating', 0) < 4.0:
            recommendations.append('Focus on leads with rating ≥ 4.0')
        if not lead.get('reviews') or lead.get('reviews', 0) < 10:
            recommendations.append('Target businesses with more reviews')
        
        return {
            'total_score': round(total_score, 1),
            'tier': tier,
            'breakdown': breakdown,
            'missing_fields': missing_fields,
            'recommendations': recommendations,
            'scored_at': datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def _score_completeness(lead: Dict) -> float:
        """Score based on data completeness (0-100)"""
        fields = ['phone', 'website', 'email', 'rating', 'reviews', 'address', 'category', 'hours']
        present = sum(1 for field in fields if lead.get(field))
        return (present / len(fields)) * 100
    
    @staticmethod
    def _score_reputation(lead: Dict) -> float:
        """Score based on rating and review count (0-100)"""
        rating = lead.get('rating', 0)
        reviews = lead.get('reviews', 0)
        
        if rating == 0:
            return 0
        
        # Rating component (0-5 scale → 0-70)
        rating_score = (rating / 5.0) * 70
        
        # Review volume component (logarithmic, 0-30)
        # 1 review = 10, 10 reviews = 20, 100 reviews = 30
        if reviews > 0:
            review_score = min(30, 10 + (math.log10(reviews) * 10))
        else:
            review_score = 0
        
        return rating_score + review_score
    
    @staticmethod
    def _score_engagement(lead: Dict) -> float:
        """Score based on contact methods available (0-100)"""
        contact_methods = []
        if lead.get('phone'):
            contact_methods.append('phone')
        if lead.get('website'):
            contact_methods.append('website')
        if lead.get('email'):
            contact_methods.append('email')
        if lead.get('social_media'):
            contact_methods.append('social')
        
        # 0 methods = 0, 1 = 40, 2 = 70, 3+ = 100
        method_count = len(contact_methods)
        if method_count == 0:
            return 0
        elif method_count == 1:
            return 40
        elif method_count == 2:
            return 70
        else:
            return 100
    
    @staticmethod
    def _score_freshness(lead: Dict) -> float:
        """Score based on data recency (0-100)"""
        created_at = lead.get('created_at')
        if not created_at:
            return 50  # Unknown, assume medium freshness
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        days_old = (datetime.utcnow() - created_at).days
        
        # <7 days = 100, 7-30 days = 80, 30-90 days = 50, >90 days = 20
        if days_old < 7:
            return 100
        elif days_old < 30:
            return 80
        elif days_old < 90:
            return 50
        else:
            return 20
    
    @staticmethod
    def _score_location(lead: Dict) -> float:
        """Score based on location quality (0-100)"""
        # For now, simple scoring. Can be enhanced with target market matching
        location = lead.get('location', '').lower()
        
        # Tier 1 markets (major cities)
        tier1 = ['new york', 'san francisco', 'los angeles', 'chicago', 'boston', 'seattle']
        # Tier 2 markets
        tier2 = ['miami', 'atlanta', 'denver', 'austin', 'portland']
        
        if any(city in location for city in tier1):
            return 100
        elif any(city in location for city in tier2):
            return 80
        elif location:
            return 60
        else:
            return 40
    
    @staticmethod
    def _get_tier(score: float) -> str:
        """Determine tier from score"""
        if score >= LeadScoringService.TIERS['HOT']:
            return 'HOT'
        elif score >= LeadScoringService.TIERS['WARM']:
            return 'WARM'
        elif score >= LeadScoringService.TIERS['COLD']:
            return 'COLD'
        else:
            return 'LOW'
```

**Files to Create:**
1. ✅ `app/domain/services/lead_scoring.py` - Scoring engine (above)
2. ✅ `app/infrastructure/queue/tasks/scoring_tasks.py` - Background scoring
3. ✅ `app/presentation/api/v1/routes/scoring.py` - Scoring endpoints
4. ✅ Update MongoDB schema: add `lead_score` field

**Celery Task:**
```python
# app/infrastructure/queue/tasks/scoring_tasks.py

from celery import shared_task
from app.domain.services.lead_scoring import LeadScoringService
from app.db_mongo import get_all_businesses, update_business_score

@shared_task(name="score_all_leads")
def score_all_leads():
    """Background job to score all leads"""
    leads = get_all_businesses(limit=10000)
    scored_count = 0
    
    for lead in leads:
        score_data = LeadScoringService.calculate_score(lead)
        update_business_score(lead['_id'], score_data)
        scored_count += 1
    
    return {
        'status': 'completed',
        'leads_scored': scored_count
    }

@shared_task(name="score_single_lead")
def score_single_lead(lead_id: str):
    """Score a single lead"""
    lead = get_business_by_id(lead_id)
    if lead:
        score_data = LeadScoringService.calculate_score(lead)
        update_business_score(lead_id, score_data)
        return score_data
    return None
```

**API Endpoints:**
```python
# app/presentation/api/v1/routes/scoring.py

from fastapi import APIRouter, HTTPException
from app.domain.services.lead_scoring import LeadScoringService
from app.infrastructure.queue.tasks.scoring_tasks import score_all_leads, score_single_lead

router = APIRouter(prefix="/scoring", tags=["Lead Scoring"])

@router.get("/companies/{company_id}/score-breakdown")
async def get_score_breakdown(company_id: str):
    """Get detailed score breakdown for a lead"""
    lead = get_business_by_id(company_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    score_data = LeadScoringService.calculate_score(lead)
    return score_data

@router.post("/admin/rescore-all")
async def trigger_rescoring():
    """Trigger background rescoring of all leads"""
    task = score_all_leads.delay()
    return {
        'status': 'queued',
        'task_id': task.id,
        'message': 'Rescoring job queued'
    }

@router.get("/companies")
async def list_by_tier(tier: str = None, limit: int = 100):
    """List companies filtered by tier"""
    # Query MongoDB with tier filter
    leads = search_businesses_by_tier(tier, limit)
    return {'results': leads, 'count': len(leads)}
```

---

#### ✅ Feature B: Email Enrichment Integration (2 days) 🔥
**Impact:** +2 points | **Priority:** HIGHEST

*[Implementation continues in next section...]*

