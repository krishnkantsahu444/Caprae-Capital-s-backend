# app/routers/companies.py
"""
Company search and export endpoints.
Uses Motor (async MongoDB) for fast, non-blocking queries.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from app.schemas.company import (
    CompaniesListResponse,
    CompanyOut,
    MetaCategoriesResponse,
    MetaLocationsResponse
)
from app.db_motor import get_collection
from bson import ObjectId
import re
import urllib.parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


def _regex(val: str):
    """Build MongoDB regex pattern with case-insensitive search"""
    return {"$regex": re.escape(val), "$options": "i"}


@router.get("/", response_model=CompaniesListResponse)
async def list_companies(
    query: Optional[str] = Query(None, description="Search in business name or category"),
    location: Optional[str] = Query(None, description="Filter by location/address"),
    category: Optional[str] = Query(None, description="Filter by category"),
    rating_min: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    rating_max: Optional[float] = Query(None, ge=0, le=5, description="Maximum rating"),
    has_website: Optional[bool] = Query(None, description="Filter businesses with website"),
    has_phone: Optional[bool] = Query(None, description="Filter businesses with phone"),
    services: Optional[List[str]] = Query(None, description="Filter by services (e.g., Dine-in, Delivery)"),
    sort_by: Optional[str] = Query("created_at", description="Sort field (rating, review_count, created_at, business_name)"),
    order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    limit: int = Query(20, ge=1, le=200, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    List and search companies with advanced filtering and pagination.
    
    **Query Examples:**
    - Search for coffee shops: `?query=coffee`
    - Filter by location: `?location=Austin`
    - High-rated only: `?rating_min=4.5`
    - Has website: `?has_website=true`
    - Sort by rating: `?sort_by=rating&order=desc`
    - Pagination: `?limit=50&offset=100`
    """
    coll = get_collection()
    filters = {}
    
    # Text search in name or category
    if query:
        filters["$or"] = [
            {"business_name": _regex(query)},
            {"category": _regex(query)}
        ]
    
    # Location filter (searches in address field)
    if location:
        filters["address"] = _regex(location)
    
    # Category exact match (case-insensitive)
    if category:
        filters["category"] = _regex(category)
    
    # Rating range filter
    if rating_min is not None or rating_max is not None:
        rfilter = {}
        if rating_min is not None:
            rfilter["$gte"] = rating_min
        if rating_max is not None:
            rfilter["$lte"] = rating_max
        filters["rating"] = rfilter
    
    # Website filter
    if has_website is True:
        filters["website"] = {"$exists": True, "$ne": None, "$ne": ""}
    elif has_website is False:
        filters["$or"] = [
            {"website": {"$exists": False}},
            {"website": None},
            {"website": ""}
        ]
    
    # Phone filter
    if has_phone is True:
        filters["phone"] = {"$exists": True, "$ne": None, "$ne": ""}
    elif has_phone is False:
        filters["$or"] = [
            {"phone": {"$exists": False}},
            {"phone": None},
            {"phone": ""}
        ]
    
    # Services filter (array contains any of the specified services)
    if services:
        filters["services"] = {"$in": services}
    
    # Sort configuration (prevent injection)
    allowed_sorts = {"rating", "review_count", "created_at", "business_name"}
    if sort_by not in allowed_sorts:
        sort_by = "created_at"
    
    sort_dir = -1 if order == "desc" else 1
    
    try:
        # Get total count
        total = await coll.count_documents(filters)
        
        # Get paginated results
        cursor = coll.find(filters).sort(sort_by, sort_dir).skip(offset).limit(limit)
        results = []
        
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        
        logger.info(f"List companies: {len(results)} results, {total} total, filters={filters}")
        
        return {"total": total, "results": results}
    
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/{company_id}", response_model=CompanyOut)
async def get_company(company_id: str):
    """
    Get a single company by MongoDB ObjectId.
    
    **Example:** `/companies/650f5b2a2f1c7f9d4c8b4567`
    """
    coll = get_collection()
    
    # Validate ObjectId format
    try:
        oid = ObjectId(company_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid company ID format")
    
    try:
        doc = await coll.find_one({"_id": oid})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        
        logger.info(f"Get company: {company_id} -> {doc.get('business_name')}")
        
        return doc
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/meta/categories", response_model=MetaCategoriesResponse)
async def get_categories(limit: int = Query(100, ge=1, le=500, description="Max categories to return")):
    """
    Get list of distinct categories in the database.
    Useful for autocomplete/filter dropdowns in frontend.
    
    **Example:** `/companies/meta/categories?limit=50`
    """
    coll = get_collection()
    
    try:
        categories = await coll.distinct("category")
        
        # Filter out None/empty and limit
        categories = [c for c in categories if c][:limit]
        
        logger.info(f"Get categories: {len(categories)} categories")
        
        return {"categories": categories}
    
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/meta/locations", response_model=MetaLocationsResponse)
async def get_locations(limit: int = Query(100, ge=1, le=500, description="Max locations to return")):
    """
    Get list of distinct locations in the database.
    Useful for autocomplete/filter dropdowns in frontend.
    
    **Example:** `/companies/meta/locations?limit=50`
    """
    coll = get_collection()
    
    try:
        locations = await coll.distinct("location")
        
        # Filter out None/empty and limit
        locations = [loc for loc in locations if loc][:limit]
        
        logger.info(f"Get locations: {len(locations)} locations")
        
        return {"locations": locations}
    
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/export/csv")
async def export_csv(
    query: Optional[str] = Query(None, description="Search in business name or category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    category: Optional[str] = Query(None, description="Filter by category"),
    rating_min: Optional[float] = Query(None, ge=0, le=5),
    has_website: Optional[bool] = Query(None),
    limit: int = Query(1000, ge=1, le=20000, description="Max records to export"),
):
    """
    Export companies to CSV with filters.
    Streams results to avoid memory issues with large datasets.
    
    **Example:** `/companies/export/csv?query=coffee&location=Austin&limit=500`
    """
    coll = get_collection()
    filters = {}
    
    # Apply same filters as list endpoint
    if query:
        filters["$or"] = [
            {"business_name": _regex(query)},
            {"category": _regex(query)}
        ]
    
    if location:
        filters["address"] = _regex(location)
    
    if category:
        filters["category"] = _regex(category)
    
    if rating_min is not None:
        filters["rating"] = {"$gte": rating_min}
    
    if has_website is True:
        filters["website"] = {"$exists": True, "$ne": None, "$ne": ""}
    
    try:
        cursor = coll.find(filters).limit(limit)
        
        # Stream CSV rows
        async def csv_streamer():
            header_written = False
            headers = []
            
            async for doc in cursor:
                # Normalize document
                doc["_id"] = str(doc["_id"])
                
                # Write header once
                if not header_written:
                    headers = list(doc.keys())
                    yield ",".join(headers) + "\n"
                    header_written = True
                
                # Write data row
                row = []
                for h in headers:
                    v = doc.get(h, "")
                    
                    # Handle lists (join with pipe)
                    if isinstance(v, list):
                        v = "|".join(map(str, v))
                    
                    # Escape newlines and quotes for CSV
                    v = str(v).replace("\n", " ").replace("\r", " ")
                    row.append('"' + v.replace('"', '""') + '"')
                
                yield ",".join(row) + "\n"
        
        # Generate filename
        query_part = urllib.parse.quote_plus(query or "all")
        filename = f"companies_export_{query_part}.csv"
        
        logger.info(f"CSV export: filters={filters}, limit={limit}")
        
        return StreamingResponse(
            csv_streamer(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stats/summary")
async def get_stats():
    """
    Get database statistics: total companies, avg rating, categories, etc.
    
    **Example:** `/companies/stats/summary`
    """
    coll = get_collection()
    
    try:
        # Total count
        total_companies = await coll.count_documents({})
        
        # Companies with website
        with_website = await coll.count_documents({
            "website": {"$exists": True, "$ne": None, "$ne": ""}
        })
        
        # Companies with phone
        with_phone = await coll.count_documents({
            "phone": {"$exists": True, "$ne": None, "$ne": ""}
        })
        
        # Average rating (using aggregation)
        pipeline = [
            {"$match": {"rating": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": None,
                "avg_rating": {"$avg": "$rating"},
                "max_rating": {"$max": "$rating"},
                "min_rating": {"$min": "$rating"}
            }}
        ]
        rating_stats = await coll.aggregate(pipeline).to_list(1)
        
        # Count categories
        categories = await coll.distinct("category")
        
        # Count locations
        locations = await coll.distinct("location")
        
        stats = {
            "total_companies": total_companies,
            "with_website": with_website,
            "with_phone": with_phone,
            "website_percentage": round((with_website / total_companies * 100), 2) if total_companies > 0 else 0,
            "phone_percentage": round((with_phone / total_companies * 100), 2) if total_companies > 0 else 0,
            "avg_rating": round(rating_stats[0]["avg_rating"], 2) if rating_stats else None,
            "max_rating": rating_stats[0]["max_rating"] if rating_stats else None,
            "min_rating": rating_stats[0]["min_rating"] if rating_stats else None,
            "total_categories": len([c for c in categories if c]),
            "total_locations": len([loc for loc in locations if loc])
        }
        
        logger.info(f"Stats: {stats}")
        
        return stats
    
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Stats query failed: {str(e)}")
