# app/schemas/company.py
"""
Pydantic schemas for company/business data.
Used by FastAPI for request/response validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class CompanyBase(BaseModel):
    """Base company fields (used for responses)"""
    business_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None
    google_maps_url: Optional[str] = None
    website: Optional[str] = None  # HttpUrl removed to avoid validation issues
    hours: Optional[str] = None
    services: Optional[List[str]] = None
    location: Optional[str] = None


class CompanyOut(CompanyBase):
    """Company response schema with MongoDB _id"""
    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "_id": "650f5b2a2f1c7f9d4c8b4567",
                "business_name": "Artisan Coffee Roasters",
                "address": "123 Main St, Austin, TX 78701",
                "phone": "(512) 555-0123",
                "rating": 4.7,
                "review_count": 342,
                "category": "Coffee shop",
                "google_maps_url": "https://www.google.com/maps/place/...",
                "website": "https://artisancoffee.com",
                "hours": "Mon-Fri: 7am-8pm, Sat-Sun: 8am-9pm",
                "services": ["Dine-in", "Takeout", "Delivery"],
                "location": "Austin, TX",
                "created_at": "2024-10-01T10:30:00Z"
            }
        }
    )


class CompaniesListResponse(BaseModel):
    """Paginated list of companies with total count"""
    total: int = Field(..., description="Total number of matching companies")
    results: List[CompanyOut] = Field(..., description="List of companies for current page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 1234,
                "results": [
                    {
                        "_id": "650f5b2a2f1c7f9d4c8b4567",
                        "business_name": "Artisan Coffee Roasters",
                        "category": "Coffee shop",
                        "rating": 4.7,
                        "location": "Austin, TX"
                    }
                ]
            }
        }
    )


class MetaCategoriesResponse(BaseModel):
    """List of distinct categories"""
    categories: List[str] = Field(..., description="Unique categories in database")


class MetaLocationsResponse(BaseModel):
    """List of distinct locations"""
    locations: List[str] = Field(..., description="Unique locations in database")
