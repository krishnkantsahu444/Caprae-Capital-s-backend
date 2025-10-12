"""
Enhanced company detail endpoint with normalized metadata.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from bson import ObjectId
from app.db_mongo import get_business_by_id, get_collection
from app.utils.normalization import normalize_business_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/{id}")
async def get_company_detail(id: str) -> Dict[str, Any]:
    """
    Get detailed company information by ID with fully normalized metadata.
    
    Returns complete business data including:
    - All core fields (name, location, rating, etc.)
    - Lead score and tier
    - Completeness flags
    - Enrichment fields needed
    - Email data (if enriched)
    
    **Example Response:**
    ```json
    {
        "id": "507f1f77bcf86cd799439011",
        "name": "Acme Restaurant",
        "category": "Restaurant",
        "location": "New York, NY",
        "rating": 4.5,
        "reviews": 234,
        "phone": "+1-212-555-0123",
        "website": "https://acme.com",
        "email": "contact@acme.com",
        "hours": "9am-9pm Mon-Fri",
        "services": ["Delivery", "Takeout"],
        "lead_score": {
            "total_score": 85.5,
            "tier": "HOT",
            "breakdown": {...},
            "missing_fields": [],
            "recommendations": []
        },
        "completeness_flags": {
            "has_phone": true,
            "has_website": true,
            "has_email": true,
            "has_hours": true
        },
        "enrichment_fields": []
    }
    ```
    """
    try:
        # Fetch business from database
        business = get_business_by_id(id)
        
        if not business:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Normalize response with all metadata
        normalized = normalize_business_response(business)
        
        return normalized
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company detail: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}/score-breakdown")
async def get_score_breakdown(id: str) -> Dict[str, Any]:
    """
    Get detailed lead score breakdown for a company.
    
    Returns just the lead scoring data with detailed breakdown.
    """
    try:
        business = get_business_by_id(id)
        
        if not business:
            raise HTTPException(status_code=404, detail="Company not found")
        
        lead_score = business.get("lead_score", {})
        
        if not lead_score or not lead_score.get("total_score"):
            # If not scored yet, return a message indicating score not calculated
            return {
                "company_id": id,
                "company_name": business.get("name", ""),
                "lead_score": {
                    "message": "Lead score not yet calculated. Implement lead scoring service to calculate scores."
                }
            }
        
        return {
            "company_id": id,
            "company_name": business.get("name", ""),
            "lead_score": lead_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching score breakdown: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
