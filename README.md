## Lead Generation Backend

This project exposes a lightweight FastAPI backend that triggers asynchronous Celery tasks to scrape or fetch lead data. The stack now includes production-ready scrapers for Apollo and Google Maps alongside a mock fallback for smoke testing.

### Features

- **Async scraping pipeline** powered by Celery and Redis
- **Apollo scraper** for B2B contacts and company enrichment
- **Google Maps scraper** with proxy rotation and anti-bot handling
- **Task tracking endpoints** to poll for status and retrieve results

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
celery -A app.celery_tasks.tasks worker --loglevel=info
```

### Run the FastAPI server:

```bash
uvicorn app.main:app --reload --port 9000
```

### API

- `POST /scrape/async` – launch the mock scraper for quick checks. Body: `{"query": "AI startups"}`
- `POST /scrape/apollo/async` – queue an Apollo scrape. Body: `{"query": "AI startups"}`
- `POST /scrape/google_maps/async` – queue a Google Maps scrape. Body: `{"query": "marketing agency", "location": "Austin, TX", "max_results": 40}`
- `GET /scrape/*/task/{task_id}` – poll task status for any of the above jobs

Visit `http://localhost:9000/docs` for interactive API docs.

### Configuration

- Apollo credentials can be supplied via the environment: `APOLLO_API_KEY`, `APOLLO_EMAIL`, `APOLLO_PASSWORD`, `APOLLO_SAVED_LIST_URL`, `APOLLO_BASE_URL`.
- Optional Google Maps proxy rotation: provide a JSON-serialisable list under the Celery task options or wire an environment variable before task submission.
- Both scrapers run headless by default; toggle by sending `"headless": false` in the request payload where supported.

### Next steps

- Store completed leads in a database or CRM
- Add enrichment pipelines and deduplication logic
- Extend the Google Maps scraper with richer structured data (hours, pricing, etc.)
