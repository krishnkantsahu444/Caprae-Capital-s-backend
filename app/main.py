from typing import Any

import uvicorn
from fastapi import FastAPI

from config.celery_utils import create_celery
from routers import scraper, companies
from db_motor import init_motor, create_indexes_async, close_motor
import logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    current_app = FastAPI(
        title="Lead Generation Backend",
        description="Async FastAPI service that delegates lead scraping to Celery workers backed by Redis.",
        version="1.0.0",
    )

    current_app.state.celery_app = create_celery()
    
    # Include routers
    current_app.include_router(scraper.router)
    current_app.include_router(companies.router)
    
    return current_app


app = create_app()
celery: Any = getattr(app.state, "celery_app")


@app.on_event("startup")
async def startup_event():
    """Initialize Motor (async MongoDB) and create indexes on startup"""
    try:
        logger.info("Initializing Motor (async MongoDB) for FastAPI...")
        init_motor()
        await create_indexes_async()
        logger.info("✅ Motor initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Motor: {e}")
        logger.warning("Company search endpoints may not work without MongoDB")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Motor connection on shutdown"""
    try:
        await close_motor()
        logger.info("Motor connection closed")
    except Exception as e:
        logger.error(f"Error closing Motor: {e}")


if __name__ == "__main__":
    uvicorn.run("app.main:app", port=9000, reload=True)
