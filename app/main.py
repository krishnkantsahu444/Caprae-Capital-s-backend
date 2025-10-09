from typing import Any

import uvicorn
from fastapi import FastAPI

from config.celery_utils import create_celery
from routers import scraper


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    current_app = FastAPI(
        title="Lead Generation Backend",
        description="Async FastAPI service that delegates lead scraping to Celery workers backed by Redis.",
        version="1.0.0",
    )

    current_app.state.celery_app = create_celery()
    current_app.include_router(scraper.router)
    return current_app


app = create_app()
celery: Any = getattr(app.state, "celery_app")


if __name__ == "__main__":
    uvicorn.run("app.main:app", port=9000, reload=True)
