"""
Analytics and aggregation API endpoints for lead insights.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.db_mongo import get_collection
from app.utils.normalization import normalize_business_response, normalize_business_list_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/top_leads")
async def get_top_leads(
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    tier: Optional[str] = Query(None, description="Filter by lead tier (HOT, WARM, COLD, LOW)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results")
) -> Dict[str, Any]:
    """
    Get top-rated leads per category/location sorted by lead score.
    
    **Query Examples:**
    - Top 10 overall: `/analytics/top_leads`
    - Top 10 restaurants: `/analytics/top_leads?category=Restaurant`
    - Top 10 in NYC: `/analytics/top_leads?location=New York`
    - Top 10 HOT leads: `/analytics/top_leads?tier=HOT`
    """
    collection = get_collection()
    
    # Build aggregation pipeline
    pipeline = []
    
    # Match stage for filters
    match_stage = {}
    if category:
        match_stage["category"] = {"$regex": category, "$options": "i"}
    if location:
        match_stage["location"] = {"$regex": location, "$options": "i"}
    if tier:
        match_stage["lead_score.tier"] = tier.upper()
    
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # Sort by lead score (descending)
    pipeline.append({"$sort": {"lead_score.total_score": -1}})
    
    # Limit results
    pipeline.append({"$limit": limit})
    
    try:
        top_leads = list(collection.aggregate(pipeline))
        normalized = normalize_business_list_response(top_leads)
        
        return {
            "count": len(normalized),
            "filters": {
                "category": category,
                "location": location,
                "tier": tier
            },
            "results": normalized
        }
    except Exception as e:
        logger.error(f"Error fetching top leads: {e}")
        raise HTTPException(500, f"Failed to fetch top leads: {str(e)}")


@router.get("/counts")
async def get_counts_per_category_location() -> Dict[str, Any]:
    """
    Get business counts grouped by category and location.
    
    **Returns:**
    ```json
    {
        "total_groups": 50,
        "results": [
            {"category": "Restaurant", "location": "New York, NY", "count": 25},
            {"category": "Cafe", "location": "Austin, TX", "count": 15}
        ]
    }
    ```
    """
    collection = get_collection()
    
    pipeline = [
        {
            "$group": {
                "_id": {
                    "category": "$category",
                    "location": "$location"
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]
    
    try:
        results = list(collection.aggregate(pipeline))
        
        formatted_results = [
            {
                "category": r["_id"].get("category", "Unknown"),
                "location": r["_id"].get("location", "Unknown"),
                "count": r["count"]
            }
            for r in results
        ]
        
        return {
            "total_groups": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"Error fetching counts: {e}")
        raise HTTPException(500, f"Failed to fetch counts: {str(e)}")


@router.get("/summary")
async def get_summary_statistics() -> Dict[str, Any]:
    """
    Get overall summary statistics including:
    - Average rating
    - Average lead score
    - Total leads
    - Complete leads (with phone)
    - Enrichment statistics
    
    **Returns:**
    ```json
    {
        "avg_rating": 4.2,
        "avg_lead_score": 65.3,
        "total_leads": 1000,
        "complete_leads": 850,
        "leads_with_phone": 900,
        "leads_with_website": 850,
        "leads_with_email": 300,
        "hot_leads": 150,
        "warm_leads": 400,
        "cold_leads": 300,
        "low_leads": 150
    }
    ```
    """
    collection = get_collection()
    
    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_rating": {"$avg": "$rating"},
                "avg_lead_score": {"$avg": "$lead_score.total_score"},
                "total_leads": {"$sum": 1},
                
                # Completeness counts
                "leads_with_phone": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$phone", None]},
                                {"$ne": ["$phone", ""]}
                            ]},
                            1,
                            0
                        ]
                    }
                },
                "leads_with_website": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$website", None]},
                                {"$ne": ["$website", ""]}
                            ]},
                            1,
                            0
                        ]
                    }
                },
                "leads_with_email": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$email", None]},
                                {"$ne": ["$email", ""]}
                            ]},
                            1,
                            0
                        ]
                    }
                },
                
                # Tier counts
                "hot_leads": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$lead_score.tier", "HOT"]},
                            1,
                            0
                        ]
                    }
                },
                "warm_leads": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$lead_score.tier", "WARM"]},
                            1,
                            0
                        ]
                    }
                },
                "cold_leads": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$lead_score.tier", "COLD"]},
                            1,
                            0
                        ]
                    }
                },
                "low_leads": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$lead_score.tier", "LOW"]},
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    
    try:
        result = list(collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            # Remove the _id field
            stats.pop("_id", None)
            
            # Round averages
            if stats.get("avg_rating"):
                stats["avg_rating"] = round(stats["avg_rating"], 2)
            if stats.get("avg_lead_score"):
                stats["avg_lead_score"] = round(stats["avg_lead_score"], 1)
            
            # Calculate completeness percentage
            total = stats.get("total_leads", 0)
            if total > 0:
                stats["completeness_rate"] = round(
                    (stats.get("leads_with_phone", 0) / total) * 100, 1
                )
                stats["enrichment_rate"] = round(
                    (stats.get("leads_with_email", 0) / total) * 100, 1
                )
            
            return stats
        else:
            return {
                "avg_rating": 0,
                "avg_lead_score": 0,
                "total_leads": 0,
                "complete_leads": 0,
                "leads_with_phone": 0,
                "leads_with_website": 0,
                "leads_with_email": 0,
                "hot_leads": 0,
                "warm_leads": 0,
                "cold_leads": 0,
                "low_leads": 0,
                "completeness_rate": 0,
                "enrichment_rate": 0
            }
    except Exception as e:
        logger.error(f"Error fetching summary statistics: {e}")
        raise HTTPException(500, f"Failed to fetch summary: {str(e)}")


@router.get("/tier_distribution")
async def get_tier_distribution(
    category: Optional[str] = Query(None, description="Filter by category"),
    location: Optional[str] = Query(None, description="Filter by location")
) -> Dict[str, Any]:
    """
    Get distribution of leads across tiers (HOT/WARM/COLD/LOW).
    
    **Query Examples:**
    - Overall distribution: `/analytics/tier_distribution`
    - For restaurants: `/analytics/tier_distribution?category=Restaurant`
    """
    collection = get_collection()
    
    # Build match stage
    match_stage = {}
    if category:
        match_stage["category"] = {"$regex": category, "$options": "i"}
    if location:
        match_stage["location"] = {"$regex": location, "$options": "i"}
    
    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    pipeline.append({
        "$group": {
            "_id": "$lead_score.tier",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$lead_score.total_score"}
        }
    })
    pipeline.append({"$sort": {"avg_score": -1}})
    
    try:
        results = list(collection.aggregate(pipeline))
        
        # Format results
        distribution = {}
        total = 0
        for r in results:
            tier = r["_id"] or "UNSCORED"
            count = r["count"]
            avg_score = round(r["avg_score"], 1) if r.get("avg_score") else 0
            
            distribution[tier] = {
                "count": count,
                "avg_score": avg_score
            }
            total += count
        
        # Calculate percentages
        for tier in distribution:
            distribution[tier]["percentage"] = round(
                (distribution[tier]["count"] / total) * 100, 1
            ) if total > 0 else 0
        
        return {
            "total_leads": total,
            "filters": {
                "category": category,
                "location": location
            },
            "distribution": distribution
        }
    except Exception as e:
        logger.error(f"Error fetching tier distribution: {e}")
        raise HTTPException(500, f"Failed to fetch tier distribution: {str(e)}")


@router.get("/completeness_stats")
async def get_completeness_statistics() -> Dict[str, Any]:
    """
    Get detailed statistics about data completeness.
    
    **Returns:**
    ```json
    {
        "total_leads": 1000,
        "fields": {
            "phone": {"present": 900, "missing": 100, "percentage": 90.0},
            "website": {"present": 850, "missing": 150, "percentage": 85.0},
            "email": {"present": 300, "missing": 700, "percentage": 30.0}
        }
    }
    ```
    """
    collection = get_collection()
    
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "phone_present": {
                    "$sum": {"$cond": [{"$and": [{"$ne": ["$phone", None]}, {"$ne": ["$phone", ""]}]}, 1, 0]}
                },
                "website_present": {
                    "$sum": {"$cond": [{"$and": [{"$ne": ["$website", None]}, {"$ne": ["$website", ""]}]}, 1, 0]}
                },
                "email_present": {
                    "$sum": {"$cond": [{"$and": [{"$ne": ["$email", None]}, {"$ne": ["$email", ""]}]}, 1, 0]}
                },
                "hours_present": {
                    "$sum": {"$cond": [{"$and": [{"$ne": ["$hours", None]}, {"$ne": ["$hours", ""]}]}, 1, 0]}
                },
                "rating_present": {
                    "$sum": {"$cond": [{"$gt": ["$rating", 0]}, 1, 0]}
                },
                "reviews_present": {
                    "$sum": {"$cond": [{"$gt": ["$reviews", 0]}, 1, 0]}
                }
            }
        }
    ]
    
    try:
        result = list(collection.aggregate(pipeline))
        
        if result:
            data = result[0]
            total = data.get("total", 0)
            
            fields = {}
            for field in ["phone", "website", "email", "hours", "rating", "reviews"]:
                present = data.get(f"{field}_present", 0)
                missing = total - present
                percentage = round((present / total) * 100, 1) if total > 0 else 0
                
                fields[field] = {
                    "present": present,
                    "missing": missing,
                    "percentage": percentage
                }
            
            return {
                "total_leads": total,
                "fields": fields
            }
        else:
            return {"total_leads": 0, "fields": {}}
    except Exception as e:
        logger.error(f"Error fetching completeness stats: {e}")
        raise HTTPException(500, f"Failed to fetch completeness stats: {str(e)}")
