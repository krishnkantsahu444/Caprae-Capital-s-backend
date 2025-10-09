## Lead Generation Backend

This project exposes a lightweight FastAPI backend that triggers asynchronous Celery tasks to scrape or fetch lead data. The current implementation returns mock leads and can be extended with real scrapers later.

### Features

- **Async scraping pipeline** powered by Celery and Redis
- **Task tracking endpoints** to poll for status and retrieve results
- **Mock lead responses** to enable quick integration testing before adding real scrapers

### Requirements

- Python 3.9+
- Redis running locally (`redis://localhost:6379`)
- Dependencies from `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run the stack

Make sure Redis is running locally (for example via `redis-server` or Docker).

Start a Celery worker:

```bash
celery -A celery_tasks.tasks worker --loglevel=info
```

### Run the FastAPI server:

```bash
uvicorn main:app --reload --port 9000
```

### API

- `POST /scrape/async` – start a lead scraping task. Example body: `{"query": "AI startups in India"}`
- `GET /scrape/task/{task_id}` – check task progress and fetch the result when ready

Visit `http://localhost:9000/docs` for interactive API docs.

### Next steps

- Swap the mock implementation in `celery_tasks/tasks.py` with a real scraper
- Store completed leads in a database or CRM
- Add enrichment pipelines and deduplication logic
