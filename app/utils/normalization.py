"""
Helper functions for MongoDB schema normalization and completeness flags.
"""
from typing import Dict, Any, List
from datetime import datetime


def add_completeness_flags(business: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add completeness flags to a business document.
    
    Args:
        business: Business document from MongoDB
        
    Returns:
        Updated business document with completeness_flags field
    """
    flags = {
        "has_phone": bool(business.get("phone")),
        "has_website": bool(business.get("website")),
        "has_email": bool(business.get("email")),
        "has_hours": bool(business.get("hours")),
        "has_rating": bool(business.get("rating")),
        "has_reviews": bool(business.get("reviews")),
        "has_services": bool(business.get("services")),
    }
    
    business["completeness_flags"] = flags
    return business


def calculate_enrichment_fields(business: Dict[str, Any]) -> List[str]:
    """
    Determine which fields need enrichment.
    
    Args:
        business: Business document from MongoDB
        
    Returns:
        List of field names that are missing and can be enriched
    """
    enrichment_needed = []
    
    if not business.get("email"):
        enrichment_needed.append("email")
    
    if not business.get("phone"):
        enrichment_needed.append("phone")
    
    if not business.get("website"):
        enrichment_needed.append("website")
    
    if not business.get("hours"):
        enrichment_needed.append("hours")
    
    if not business.get("services"):
        enrichment_needed.append("services")
    
    return enrichment_needed


def normalize_business_response(business: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a business document for API responses.
    Ensures all expected fields exist with default values.
    
    Args:
        business: Raw business document from MongoDB
        
    Returns:
        Normalized business document with all fields present
    """
    # Convert ObjectId to string
    business_id = str(business["_id"]) if "_id" in business else None
    
    # Build normalized response
    normalized = {
        "id": business_id,
        "name": business.get("name", ""),
        "business_name": business.get("business_name", business.get("name", "")),
        "category": business.get("category", ""),
        "location": business.get("location", ""),
        "address": business.get("address", business.get("location", "")),
        "rating": business.get("rating", 0.0),
        "reviews": business.get("reviews", 0),
        "phone": business.get("phone"),
        "website": business.get("website"),
        "email": business.get("email"),
        "emails": business.get("emails", []),
        "hours": business.get("hours"),
        "services": business.get("services", []),
        "google_maps_url": business.get("google_maps_url"),
        "created_at": business.get("created_at"),
        "updated_at": business.get("updated_at"),
        "scraped_at": business.get("scraped_at"),
        
        # Lead scoring data
        "lead_score": business.get("lead_score", {
            "total_score": 0,
            "tier": "LOW",
            "breakdown": {},
            "missing_fields": [],
            "recommendations": [],
            "scored_at": None
        }),
        
        # Completeness flags
        "completeness_flags": business.get("completeness_flags", {
            "has_phone": bool(business.get("phone")),
            "has_website": bool(business.get("website")),
            "has_email": bool(business.get("email")),
            "has_hours": bool(business.get("hours")),
            "has_rating": bool(business.get("rating")),
            "has_reviews": bool(business.get("reviews")),
            "has_services": bool(business.get("services")),
        }),
        
        # Enrichment fields
        "enrichment_fields": business.get("enrichment_fields", 
            calculate_enrichment_fields(business)
        ),
    }
    
    return normalized


def normalize_business_list_response(businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize a list of business documents for API responses.
    
    Args:
        businesses: List of raw business documents from MongoDB
        
    Returns:
        List of normalized business documents
    """
    return [normalize_business_response(b) for b in businesses]
