from __future__ import annotations

from typing import Any, List

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException

from celery_tasks.tasks import (
    scrape_leads,
    scrape_leads_from_apollo,
    scrape_leads_from_google_maps,
)
from schemas.scraper import (
    GoogleMapsLeadRequest,
    LeadRequest,
    LeadResponse,
    TaskResultItem,
    TaskStatus,
)

router = APIRouter(prefix="/scrape", tags=["Scraper"])


@router.post("/async", response_model=TaskStatus)
def start_scrape(req: LeadRequest) -> TaskStatus:
    """Launch the generic mock scraping task."""

    task = scrape_leads.delay(req.query)
    return TaskStatus(task_id=task.id, status="PENDING", result=None)


@router.get("/task/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str) -> TaskStatus:
    """Inspect the state of the generic mock scraping task."""

    return _build_task_status(task_id)


@router.post("/apollo/async", response_model=TaskStatus)
def start_apollo_scrape(req: LeadRequest) -> TaskStatus:
    """Trigger an Apollo scraping workflow asynchronously."""

    task = scrape_leads_from_apollo.delay(req.query)
    return TaskStatus(task_id=task.id, status="PENDING", result=None)


@router.get("/apollo/task/{task_id}", response_model=TaskStatus)
def get_apollo_task_status(task_id: str) -> TaskStatus:
    """Return the status and result payload for an Apollo scraping task."""

    return _build_task_status(task_id)


@router.post("/google_maps/async", response_model=TaskStatus)
def start_google_maps_scrape(req: GoogleMapsLeadRequest) -> TaskStatus:
    """Trigger the Google Maps scraper asynchronously."""

    task = scrape_leads_from_google_maps.delay(
        req.query,
        req.location,
        {
            "max_results": req.max_results,
            "headless": req.headless,
        },
    )
    return TaskStatus(task_id=task.id, status="PENDING", result=None)


@router.get("/google_maps/task/{task_id}", response_model=TaskStatus)
def get_google_maps_task_status(task_id: str) -> TaskStatus:
    """Retrieve the status for a Google Maps scraping task."""

    return _build_task_status(task_id)


def _build_task_status(task_id: str) -> TaskStatus:
    result = AsyncResult(task_id)
    if result is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=404, detail="Task not found")

    payload = TaskStatus(task_id=task_id, status=result.status, result=None)
    if result.ready():
        payload.result = _normalise_result(result.result)
    return payload


def _normalise_result(raw: Any) -> List[TaskResultItem]:
    if raw is None:
        return []

    if not isinstance(raw, list):
        raw = [raw]

    normalised: List[TaskResultItem] = []
    for item in raw:
        if isinstance(item, LeadResponse):
            normalised.append(item)
        elif isinstance(item, dict):
            try:
                normalised.append(LeadResponse(**item))
            except Exception:  # pragma: no cover - keep raw dict on validation failure
                normalised.append(item)
        else:
            normalised.append(item)
    return normalised
