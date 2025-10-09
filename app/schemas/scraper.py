from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class LeadRequest(BaseModel):
    """Request payload for starting a lead scraping task."""

    query: str = Field(..., description="Search query for the desired leads.")


class GoogleMapsLeadRequest(BaseModel):
    """Request body for launching a Google Maps scraping task."""

    query: str = Field(..., description="Business or keyword to search for.")
    location: str = Field(..., description="Geographic location or city to search within.")
    max_results: int = Field(25, ge=1, le=200, description="Maximum number of listings to return.")
    headless: bool = Field(True, description="Whether to run the browser in headless mode.")


class LeadResponse(BaseModel):
    """Structured lead returned by a scraping task."""

    business_name: Optional[str] = Field(None, description="Name of the company.")
    website: Optional[str] = Field(None, description="Company website URL.")
    industry: Optional[str] = Field(None, description="Industry or vertical of the company.")
    country: Optional[str] = Field(None, description="Country where the company is located.")
    first_name: Optional[str] = Field(None, description="Contact first name.")
    last_name: Optional[str] = Field(None, description="Contact last name.")
    job_title: Optional[str] = Field(None, description="Contact job title.")
    phone: Optional[str] = Field(None, description="Contact phone number.")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL for the contact.")
    email: Optional[str] = Field(None, description="Contact email address.")
    rating: Optional[float] = Field(None, description="Average Google rating.")
    review_count: Optional[int] = Field(None, description="Number of Google reviews.")
    service_options: Optional[List[str]] = Field(None, description="Service options listed in Google Maps.")
    address: Optional[str] = Field(None, description="Street address or area.")
    google_maps_url: Optional[str] = Field(None, description="Direct Google Maps URL for the listing.")
    source: Optional[str] = Field(None, description="Origin of the lead data (e.g., 'apollo', 'google_maps').")


TaskResultItem = Union[LeadResponse, Dict[str, Any]]


class TaskStatus(BaseModel):
    """Standard shape for Celery task status responses."""

    task_id: str = Field(..., description="Celery task identifier.")
    status: str = Field(..., description="Current status of the task.")
    result: Optional[List[TaskResultItem]] = Field(
        None,
        description="Optional task result when the task has completed.",
    )
