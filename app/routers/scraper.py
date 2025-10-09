from fastapi import APIRouter
from celery.result import AsyncResult
from celery_tasks.tasks import scrape_leads
from schemas.scraper import LeadRequest

router = APIRouter(prefix="/scrape", tags=["Scraper"])


@router.post("/async")
def start_scrape(req: LeadRequest):
    task = scrape_leads.delay(req.query)
    return {"task_id": task.id}


@router.get("/task/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id)
    if result.ready():
        return {"status": "completed", "result": result.result}
    return {"status": result.status}
