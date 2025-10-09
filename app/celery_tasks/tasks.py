from celery import Celery
import random
import time

from config import celery_config


app = Celery(
    "leadgen-scraper",
    broker=celery_config.broker_url,
    backend=celery_config.result_backend,
)
app.conf.update(
    task_serializer=celery_config.task_serializer,
    result_serializer=celery_config.result_serializer,
    accept_content=celery_config.accept_content,
    timezone=celery_config.timezone,
    enable_utc=celery_config.enable_utc,
)


@app.task(bind=True, max_retries=3)
def scrape_leads(self, query: str):
    try:
        time.sleep(random.randint(1, 3))  # simulate delay
        # mock result — later replaced by real scraper
        return [
            {"title": f"Company related to {query}", "url": f"https://example.com/{query}", "source": "mock"}
        ]
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
