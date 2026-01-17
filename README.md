# Caprae Capital — Lead Generation Backend

> **Note**: This project was developed as part of the **Full Stack Developer Interview Pre-Work** for Caprae Capital Partners. The challenge was to analyze [SaaSQuatch Leads](https://www.saasquatchleads.com/) and create an enhanced lead generation tool within a 5-hour timeframe that demonstrates business understanding, technical sophistication, and user-centric design.

## About This Project

This backend system was built in response to Caprae Capital's AI-Readiness Pre-Screening Challenge, which evaluates candidates on:

- **Business Use Case Understanding** — Demonstrating clear understanding of the lead generation process and identifying high-impact data points for sales outreach
- **Technical Sophistication** — Efficient data extraction, reliable performance at scale, data quality improvements (deduplication, enrichment, validation)
- **UX/UI Design** — User-friendly interface with seamless navigation and minimal learning curve
- **Innovation** — Creative solutions that deliver high-impact results efficiently

### Challenge Overview

The task was to enhance a lead generation scraping tool by developing one or two impactful features within 5 hours. This implementation focused on creating a production-ready backend with:

- Asynchronous scraping pipeline for scalability
- Anti-bot measures for reliable data collection
- MongoDB integration for data persistence and deduplication
- RESTful API for easy integration with existing workflows
- Comprehensive data normalization and enrichment capabilities

## System Overview

A production-ready backend for Google Maps lead generation and enrichment. It provides a FastAPI HTTP API that schedules asynchronous scraping jobs (Crawlee / Playwright or a mock scraper) via Celery, stores results in MongoDB (Motor), and includes utilities for anti-bot handling, deduplication, and phone normalization.

### Key Capabilities

- Queue and track scraping jobs via HTTP API
- Production-ready Google Maps scraper (Crawlee / Playwright) and a mock scraper for tests
- Asynchronous pipeline with Celery + Redis and async MongoDB client (Motor)
- Anti-bot features: proxy rotation, user-agent rotation, delay/randomization, CAPTCHA detection hooks
- Data normalization and deduplication (atomic upserts)
- Full-number leads with complete contact information (phone + website)
- Comprehensive API with filtering, export (CSV), and statistics

### Tech Stack

- **Python** (3.11+ recommended)
- **FastAPI** (HTTP API)
- **Celery** (background tasks) + **Redis** (broker)
- **Playwright / Crawlee** for scraping
- **MongoDB (Motor)** for async persistence

---

## Table of Contents

- [About This Project](#about-this-project)
- [Quick Start](#quick-start-windows)
- [Configuration](#configuration-important-variables)
- [Running a Scrape](#running-a-scrape-examples)
- [API Reference](#api-reference-and-implementation)
- [Testing](#testing)
- [Project Layout](#project-layout-high-level)
- [Contributing](#contributing)

---

## Quick Start (Windows)

1) Create and activate a virtualenv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # PowerShell
```

2) Install dependencies

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

3) Create environment file

```powershell
copy .env.example .env
# Edit .env to provide MONGO_URI, MONGO_DB_NAME, and any proxy/user-agent paths
```

4) Start Redis (example using Docker)

```powershell
docker run -d --name redis -p 6379:6379 redis:latest
```

5) Start Celery worker and FastAPI

```powershell
# From repo root
celery -A app.celery_tasks.tasks worker --loglevel=info
# In another terminal
uvicorn app.main:app --reload --port 9000
```

Open the interactive API docs at http://localhost:9000/docs

---

## Configuration (Important Variables)

Edit `.env` (copied from `.env.example`) to set:

- `MONGO_URI` — MongoDB connection string (default: `mongodb://localhost:27017/`)
- `MONGO_DB_NAME` — DB name
- `MONGO_COLLECTION` — collection for leads (default: `businesses`)
- `REDIS_URL` — Redis broker URL (e.g. `redis://localhost:6379/0`)
- `PROXY_LIST_PATH` — optional path to `proxies.txt`
- `USER_AGENTS_PATH` — optional path to `user_agents.txt`
- `HEADLESS` — run browsers headless (true/false)
- Various scraper tuning variables: timeouts, delays, max per session (see config files)

---

## Running a Scrape (Examples)

- Mock scraper (fast, useful for smoke tests)

```bash
POST http://localhost:9000/scrape/async
Body: {"query":"AI startups"}
```

- Crawlee / Google Maps scraper (queues a Celery job)

```bash
POST http://localhost:9000/scrape/google_maps/async
Body: {"query":"marketing agency","location":"Austin, TX","max_results":40}
```

Poll job status:

```bash
GET /scrape/*/task/{task_id}
```

---

## API Reference and Implementation

- FastAPI app entry: app/main.py
- Celery tasks: app/celery_tasks/tasks.py
- Scrapers: app/scrapers and app/crawlers
- Helpers and utilities: app/utils

---

## Testing

- Unit tests (fast, no network):

```powershell
pytest tests/test_parsers.py -v
```

- Run full tests (including integration/smoke): ensure Redis and MongoDB are available and then run:

```powershell
pytest tests/ -v -s
```

---

## Project Layout (High Level)

- `app/` — application package
  - `main.py` — FastAPI app
  - `celery_tasks/` — Celery task definitions
  - `scrapers/`, `crawlers/` — scraping implementations
  - `db_*.py` — MongoDB helpers (sync/async)
  - `presentation/` — API routers
  - `schemas/` — pydantic schemas
  - `utils/` — anti-bot, normalization, config helpers
- `scripts/` — helper scripts (create_indexes, test_endpoints)
- `tests/` — unit and integration tests

---

## Helpful Files

- `requirements.txt` — Python dependencies
- `proxies.txt.example` — proxy list format
- `user_agents.txt` — user-agent list used by scrapers

---

## Features Developed for the Challenge

### 1. Asynchronous Scraping Architecture
- **Why**: Scalability and performance are critical for lead generation tools handling high volumes
- **Implementation**: Celery + Redis for background job processing, allowing multiple concurrent scraping tasks
- **Business Impact**: Users can queue multiple searches without blocking, dramatically improving throughput

### 2. Anti-Bot Protection Suite
- **Why**: Reliable data collection requires evading detection and rate limiting
- **Implementation**: 
  - Proxy rotation from configurable proxy pool
  - User-agent randomization
  - Random delays between requests
  - CAPTCHA detection hooks
- **Business Impact**: Higher success rates and more consistent data collection

### 3. MongoDB Integration with Deduplication
- **Why**: Lead quality depends on data accuracy and avoiding duplicates
- **Implementation**: 
  - Atomic upserts to prevent duplicate records
  - Phone number normalization for better matching
  - Structured data storage with indexing for fast queries
- **Business Impact**: Clean, deduplicated lead databases ready for CRM import

### 4. Full-Number Leads Feature
- **Why**: Contact information completeness directly impacts sales conversion rates
- **Implementation**: Detail page scraping to extract complete phone numbers and websites
- **Business Impact**: Higher-quality leads with verified contact information

### 5. RESTful API with Task Tracking
- **Why**: Easy integration with existing sales workflows and CRM systems
- **Implementation**: 
  - FastAPI endpoints for job submission and status polling
  - CSV export for bulk data operations
  - Statistics endpoints for monitoring scraping performance
- **Business Impact**: Seamless integration into existing tech stacks, minimal training required

---

## Notes and Recommendations

- For local development, Docker is the easiest way to run Redis and MongoDB.
- Use the mock scraper for rapid iteration without consuming scraping resources.
- When running Crawlee/Playwright in production, configure a proxy pool and follow local laws and site terms-of-service.

---

## About Caprae Capital

[Caprae Capital Partners](https://capraecapital.com) is a private equity firm dedicated to transforming businesses through strategic initiatives, with a focus on AI-readiness and operational excellence. Unlike traditional PE firms that rely heavily on financial engineering, Caprae emphasizes post-acquisition value creation through SaaS (Software as a Service) and MaaS (M&A as a Service) models.

This project demonstrates practical AI solutions for lead generation—a critical component of Caprae's vision to help businesses improve decision-making, streamline operations, and create lasting value.

**Relevant Links**:
- [SaaSQuatch Leads](https://www.saasquatchleads.com/) — Reference application
- [Caprae Substack](https://capraecapital.substack.com/) — Company insights and thought leadership
- [Recruitment Information](https://capraecapital.com/careers)

---

## Contributing

Pull requests are welcome. Please run the test suite and keep changes focused. Add a short description in PRs explaining behavior changes.

---

## License

See [LICENSE.txt](LICENSE.txt) for licensing information.

---

## Contact & Acknowledgments

**Project Author**: Developed as interview pre-work for Caprae Capital Partners  
**Challenge Duration**: 5 hours (core features)  
**Submission Contact**: recruiting@capraecapital.com

Special thanks to the Caprae Capital team for providing a challenging and real-world problem that showcases the intersection of business strategy and technical implementation.

---

**Last Updated**: January 18, 2026
# Caprae Capital Backend - Lead Generation System# Lead Generation Backend## Lead Generation Backend



Production-ready Google Maps lead generation system with Crawlee, FastAPI, Celery, and MongoDB.



## 🚀 FeaturesThis project exposes a lightweight FastAPI backend that triggers asynchronous Celery tasks to scrape or fetch lead data. The stack includes **two production-ready Google Maps scrapers**:This project exposes a lightweight FastAPI backend that triggers asynchronous Celery tasks to scrape or fetch lead data. The stack includes a production-ready Google Maps scraper alongside a mock fallback for smoke testing.



- **Full-Number Leads**: Robust detail page scraping for complete contact information (phone + website)

- **Anti-Bot Protection**: Proxy rotation, user agent rotation, CAPTCHA detection, retry logic

- **Async Architecture**: FastAPI + Celery for background jobs, Motor for async MongoDB1. **Selenium-based scraper** (legacy) — for basic scraping needs### Features

- **Deduplication**: Atomic upserts prevent duplicate records

- **Phone Normalization**: Automatic cleaning and validation of phone numbers2. **Crawlee (Playwright) scraper** (recommended) — production-ready with advanced anti-bot measures, proxy rotation, and SQLite persistence

- **Comprehensive API**: REST endpoints for search, filtering, export (CSV), and statistics

- **Async scraping pipeline** powered by Celery and Redis

---

---- **Google Maps scraper** with proxy rotation and anti-bot handling

## 📋 Table of Contents

- **Task tracking endpoints** to poll for status and retrieve results

- [Quick Start](#quick-start)

- [Environment Configuration](#environment-configuration)## Features

- [Testing](#testing)

- [Database Verification](#database-verification)### Requirements

- [API Endpoints](#api-endpoints)

- [Architecture](#architecture)- **Async scraping pipeline** powered by Celery and Redis

- [Troubleshooting](#troubleshooting)

- **Crawlee-based Google Maps scraper** with:- Python 3.9+

---

  - Playwright browser automation (more reliable than Selenium)- Redis running locally (`redis://localhost:6379`)

## 🏁 Quick Start

  - Proxy rotation and user-agent randomization- Dependencies from `requirements.txt`

### 1. Install Dependencies

  - Anti-bot detection and retry logic

```bash

# Create virtual environment  - SQLite database persistence with automatic deduplicationInstall dependencies:

python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate  - Structured data extraction (name, address, phone, website, rating, reviews, etc.)



# Install packages- **Task tracking endpoints** to poll for status and retrieve results```bash

pip install -r requirements.txt

- **Database API** to query scraped leadspip install -r requirements.txt

# Install Playwright browsers

playwright install chromium```

```

---

### 2. Configure Environment

### Run the stack

```bash

# Copy example config## Requirements

cp .env.example .env

Make sure Redis is running locally (for example via `redis-server` or Docker).

# Edit .env with your settings

nano .env- **Python 3.11+** (Python 3.9+ may work but 3.11+ recommended)

```

- **Redis** running locally (`redis://localhost:6379`)Start a Celery worker:

**Required settings:**

```bash- **Playwright browsers** (installed automatically, see setup below)

MONGO_URI=mongodb+srv://user:password@cluster0.mongodb.net/

MONGO_DB_NAME=crashlens```bash

MONGO_COLLECTION=businesses

```---celery -A app.celery_tasks.tasks worker --loglevel=info



### 3. Start Services```



```bash## Installation

# Terminal 1: Start Redis (required for Celery)

redis-server### Run the FastAPI server:



# Terminal 2: Start Celery worker### 1. Install Python dependencies

celery -A celery_tasks.tasks worker --loglevel=info

```bash

# Terminal 3: Start FastAPI server

uvicorn app.main:app --reload --port 9000```bashuvicorn app.main:app --reload --port 9000

```

pip install -r requirements.txt```

### 4. Run a Scrape

```

```bash

# Via API### API

curl -X POST http://localhost:9000/scrape/crawlee/async \

  -H "Content-Type: application/json" \### 2. Install Playwright browsers

  -d '{

    "query": "coffee shop",- `POST /scrape/async` – launch the mock scraper for quick checks. Body: `{"query": "AI startups"}`

    "location": "Austin, TX",

    "max_results": 5This step is **critical** for the Crawlee scraper to work:- `POST /scrape/google_maps/async` – queue a Google Maps scrape. Body: `{"query": "marketing agency", "location": "Austin, TX", "max_results": 40}`

  }'

```- `GET /scrape/*/task/{task_id}` – poll task status for any of the above jobs



---```bash



## ⚙️ Environment Configurationpython -m playwright installVisit `http://localhost:9000/docs` for interactive API docs.



### Core Settings```



| Variable | Default | Description |### Configuration

|----------|---------|-------------|

| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |This downloads Chromium, Firefox, and WebKit browsers. For production, you may only need Chromium:

| `MONGO_DB_NAME` | `crashlens` | Database name |

| `MONGO_COLLECTION` | `businesses` | Collection name |- Optional Google Maps proxy rotation: provide a JSON-serialisable list under the Celery task options or wire an environment variable before task submission.

| `HEADLESS` | `true` | Run browser in headless mode |

| `MAX_PER_SESSION` | `50` | Max results per crawl session |```bash- The scraper runs headless by default; toggle by sending `"headless": false` in the request payload.



### Detail Page Scraping (NEW)python -m playwright install chromium



| Variable | Default | Description |```### Next steps

|----------|---------|-------------|

| `DETAIL_PAGE_TIMEOUT` | `20000` | Timeout for detail page load (ms) |

| `MAX_DETAIL_ATTEMPTS` | `3` | Retry attempts for detail page |

| `DETAIL_PAGE_DELAY_MS_MIN` | `1500` | Min delay before detail visit (ms) |### 3. Configure environment variables- Store completed leads in a database or CRM

| `DETAIL_PAGE_DELAY_MS_MAX` | `3500` | Max delay before detail visit (ms) |

- Add enrichment pipelines and deduplication logic

### Phone Normalization

Copy the example environment file:- Extend the Google Maps scraper with richer structured data (hours, pricing, etc.)

| Variable | Default | Description |

|----------|---------|-------------|

| `PHONE_NORMALIZE_REGEX` | `[^0-9+]` | Characters to remove from phones |```bash

cp .env.example .env

### Database Behavior```



| Variable | Default | Description |Edit `.env` to configure:

|----------|---------|-------------|

| `DB_UPSERT_ON_INSERT` | `true` | Enable atomic upsert behavior |- `DB_PATH` — SQLite database path (default: `leads.db`)

- `PROXY_LIST_PATH` — Path to proxy list file (default: `proxies.txt`)

### Anti-Bot Configuration- `USER_AGENTS_PATH` — Path to user agents file (default: `user_agents.txt`)

- `HEADLESS` — Run browser in headless mode (default: `true`)

| Variable | Default | Description |- `MAX_REQUESTS_PER_CRAWL` — Max pages to crawl per session (default: `20`)

|----------|---------|-------------|- `MIN_DELAY_MS` / `MAX_DELAY_MS` — Random delay range between requests (default: 1000-3500ms)

| `PROXY_LIST_PATH` | `proxies.txt` | Path to proxy list file |

| `USER_AGENTS_PATH` | `user_agents.txt` | Path to user agents file |### 4. Set up proxies (optional but recommended for production)

| `MIN_DELAY_MS` | `1000` | Min delay between businesses (ms) |

| `MAX_DELAY_MS` | `3500` | Max delay between businesses (ms) |Create a `proxies.txt` file with one proxy per line:



---```

http://proxy1.example.com:8080

## 🧪 Testinghttp://proxy2.example.com:8080

192.168.1.100:3128

### Unit Tests (Fast)```



Test parsers and utilities without network requests:See `proxies.txt.example` for the format.



```bash### 5. Start Redis

# Run all unit tests

pytest tests/test_parsers.py -vMake sure Redis is running locally:



# Run specific test```bash

pytest tests/test_parsers.py::test_normalize_phone_valid -vredis-server

```

# Run with coverage

pytest tests/test_parsers.py --cov=app.parsers --cov-report=htmlOr use Docker:

```

```bash

**Expected output:**docker run -d -p 6379:6379 redis:latest

``````

tests/test_parsers.py::test_normalize_phone_valid PASSED

tests/test_parsers.py::test_parse_card_html_basic PASSED---

tests/test_parsers.py::test_parse_detail_page_html_complete PASSED

...## Running the Stack

======================== 30 passed in 2.45s ========================

```### 1. Start Celery worker



### Integration Tests (Slow)```bash

celery -A app.celery_tasks.tasks worker --loglevel=info

End-to-end smoke test with real scraping:```



```bash### 2. Start FastAPI server

# Enable integration tests

export RUN_INTEGRATION=true  # On Windows: set RUN_INTEGRATION=true```bash

uvicorn app.main:app --reload --port 9000

# Run smoke test (takes 30-60 seconds)```

pytest tests/test_integration_smoke.py -v -s

### 3. Access the API

# Run all tests including integration

pytest tests/ -v -s- **API Docs**: http://localhost:9000/docs

```- **ReDoc**: http://localhost:9000/redoc



**Expected output:**---

```

🔥 SMOKE TEST: Running minimal end-to-end scrape## API Endpoints

📊 Initial DB count: 127

🚀 Starting crawl: coffee shop in Berkeley, CA### Scraping Endpoints

✅ Crawl completed! Results scraped: 3

📊 Final DB count: 130 (New records: 3)#### 1. Mock Scraper (for testing)

✨ Complete records (phone + website): 2

✅ SMOKE TEST PASSED!**POST** `/scrape/async`

```

```json

### Test Coverage{

  "query": "AI startups"

```bash}

# Generate coverage report```

pytest tests/ --cov=app --cov-report=html --cov-report=term

Returns a mock lead immediately.

# View HTML report

open htmlcov/index.html  # On Windows: start htmlcov/index.html#### 2. Legacy Selenium Scraper

```

**POST** `/scrape/google_maps/async`

---

```json

## 🗄️ Database Verification{

  "query": "marketing agency",

### Check Data Completeness  "location": "Austin, TX",

  "max_results": 40,

```bash  "headless": true

# Using mongosh}

mongosh "$MONGO_URI"```



use crashlensReturns task ID. Results are returned in the task status response.



# Count total businesses#### 3. Crawlee Scraper (Recommended for Production)

db.businesses.count()

**POST** `/scrape/crawlee/async`

# Count businesses with phone AND website

db.businesses.find({```json

  "phone": {"$exists": true, "$ne": null},{

  "website": {"$exists": true, "$ne": null}  "query": "coffee shop",

}).count()  "location": "San Francisco, CA",

  "max_results": 20,

# Count businesses with phone only  "headless": true

db.businesses.find({}

  "phone": {"$exists": true, "$ne": null}```

}).count()

**Returns:**

# Count businesses with website only- Task ID to track progress

db.businesses.find({- Results are saved to SQLite database automatically

  "website": {"$exists": true, "$ne": null}- Use `/scrape/database/leads` to retrieve results

}).count()

**Advantages:**

# Sample complete records- ✅ Playwright (more stable than Selenium)

db.businesses.find({- ✅ Advanced anti-bot measures (proxy rotation, UA randomization, random delays)

  "phone": {"$exists": true, "$ne": null},- ✅ Database persistence with deduplication

  "website": {"$exists": true, "$ne": null}- ✅ Enrichment: visits detail pages to extract website, hours, etc.

}, {

  "name": 1,### Task Status Endpoints

  "phone": 1,

  "website": 1,**GET** `/scrape/task/{task_id}` — Check status of any scraping task

  "category": 1

}).limit(5).pretty()**GET** `/scrape/crawlee/task/{task_id}` — Check status of Crawlee scraping task



# Check for duplicates (by google_maps_url)**Returns:**

db.businesses.aggregate([

  {"$group": {```json

    "_id": "$google_maps_url",{

    "count": {"$sum": 1}  "task_id": "abc123",

  }},  "status": "SUCCESS",

  {"$match": {"count": {"$gt": 1}}}  "result": {

])    "status": "completed",

    "stats": {

# Verify indexes      "results_count": 18,

db.businesses.getIndexes()      "query": "coffee shop",

```      "location": "San Francisco, CA"

    },

### Using Python    "message": "Scraped 18 businesses. Check database for full results."

  }

```python}

from app.db_mongo import get_collection, is_record_complete```



collection = get_collection()### Database Endpoints



# Total count**GET** `/scrape/database/leads?limit=100&offset=0`

total = collection.count_documents({})

print(f"Total businesses: {total}")Retrieve all leads from the SQLite database with pagination.



# Complete records**Returns:**

complete = collection.count_documents({

    "phone": {"$exists": True, "$ne": None},```json

    "website": {"$exists": True, "$ne": None}{

})  "total": 150,

print(f"Complete records: {complete} ({complete/total*100:.1f}%)")  "limit": 100,

  "offset": 0,

# Sample records  "results": [

for record in collection.find().limit(5):    {

    complete_flag = "✅" if is_record_complete(record) else "⚠️"      "id": 1,

    print(f"{complete_flag} {record.get('name')}: "      "name": "Blue Bottle Coffee",

          f"phone={record.get('phone', 'N/A')[:15]}, "      "address": "66 Mint St, San Francisco, CA 94103",

          f"website={record.get('website', 'N/A')[:30]}")      "phone": "(415) 495-3394",

```      "website": "https://bluebottlecoffee.com",

      "rating": 4.5,

### Verify Phone Normalization      "reviews": 1234,

      "google_maps_url": "https://www.google.com/maps/place/...",

```bash      "category": "Coffee shop",

# Check for invalid characters in phone numbers      "hours": "Mon-Fri: 7am-7pm, Sat-Sun: 8am-6pm",

db.businesses.find({      "created_at": "2025-10-12 10:30:00"

  "phone": {"$regex": /[^0-9+|]/}    }

}).count()  ]

}

# Should return 0 if normalization is working```

```

---

---

## Configuration

## 📡 API Endpoints

### Proxy Rotation

Full API documentation: See `API_ENDPOINTS.md`

The Crawlee scraper automatically rotates proxies from `proxies.txt` in round-robin fashion. This is **highly recommended** for production to avoid IP bans.

### Company Search

### User Agent Rotation

```bash

# List companies with filtersUser agents are rotated from `user_agents.txt`. A default list of common user agents is provided.

GET /companies?query=coffee&location=Austin&rating_min=4.5&has_website=true&limit=20

### Anti-Bot Measures

# Get single company

GET /companies/{company_id}The Crawlee scraper includes:



# Export to CSV- **Random delays** between requests (1-3.5 seconds by default)

GET /companies/export/csv?query=restaurant&limit=1000- **Proxy rotation** to distribute requests across multiple IPs

- **User-agent randomization** to appear as different browsers

# Get statistics- **Headless mode** (can be disabled for debugging)

GET /companies/stats/summary- **CAPTCHA detection** — automatically detects and reports blocking

```- **Scroll simulation** to load lazy-loaded content

- **Detail page enrichment** — visits business detail pages to extract website and hours

### Metadata

### Database Schema

```bash

# Get categories for autocompleteThe SQLite database (`leads.db`) has the following schema:

GET /companies/meta/categories

```sql

# Get locations for autocompleteCREATE TABLE businesses (

GET /companies/meta/locations    id INTEGER PRIMARY KEY,

```    name TEXT,

    address TEXT,

### Scraping    phone TEXT,

    website TEXT,

```bash    rating REAL,

# Trigger async scrape (Celery)    reviews INTEGER,

POST /scrape/crawlee/async    google_maps_url TEXT UNIQUE,  -- Used for deduplication

Content-Type: application/json    category TEXT,

{    hours TEXT,

  "query": "restaurant",    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

  "location": "San Francisco",);

  "max_results": 20```

}

**Deduplication:** The `google_maps_url` field is unique, so duplicate businesses are automatically skipped.

# Check task status

GET /scrape/task/{task_id}---

```

## Testing

### Interactive Docs

### Run a small test scrape

- Swagger UI: http://localhost:9000/docs

- ReDoc: http://localhost:9000/redoc```bash

# Start Redis and Celery worker first, then use the API

---curl -X POST http://localhost:9000/scrape/crawlee/async \

  -H "Content-Type: application/json" \

## 🏗️ Architecture  -d '{"query": "pizza", "location": "New York", "max_results": 5, "headless": true}'

```

```

┌──────────────────────────────────────────────────────────────┐### Check the database

│                         CLIENT                               │

│  (React Frontend / Postman / cURL / Python Client)          │```bash

└────────────────────────┬─────────────────────────────────────┘sqlite3 leads.db "SELECT COUNT(*) FROM businesses;"

                         │sqlite3 leads.db "SELECT name, address, website FROM businesses LIMIT 5;"

                         │ HTTP REST API```

                         ▼

┌──────────────────────────────────────────────────────────────┐---

│                      FASTAPI SERVER                          │

│  ┌───────────────────────────────────────────────────────┐  │## Architecture

│  │  Routers:                                             │  │

│  │  - /companies (Motor - async MongoDB)                │  │### Tech Stack

│  │  - /scrape (Celery task dispatch)                    │  │

│  └───────────────────────────────────────────────────────┘  │- **FastAPI** — Modern async web framework

└────────────┬─────────────────────────────────┬───────────────┘- **Celery** — Distributed task queue for async job execution

             │                                 │- **Redis** — Message broker and result backend

             │ Motor (async)                   │ Celery Tasks- **Crawlee** — High-level web scraping framework (Python port)

             ▼                                 ▼- **Playwright** — Browser automation (more reliable than Selenium)

┌─────────────────────────┐      ┌───────────────────────────┐- **BeautifulSoup** — HTML parsing

│   MONGODB ATLAS         │      │   CELERY WORKERS          │- **SQLite** — Lightweight database for lead storage

│  Collection: businesses │◄─────┤  - Crawlee scraper        │- **Pydantic** — Data validation and serialization

│  Indexes: 8             │      │  - pymongo (sync)         │

│  Upsert: google_maps_url│      │  - Proxy rotation         │### Workflow

└─────────────────────────┘      │  - Detail page visits     │

                                 └───────────┬───────────────┘1. **User** sends POST request to `/scrape/crawlee/async`

                                             │2. **FastAPI** validates request and enqueues Celery task

                                             │ Redis Queue3. **Celery worker** picks up task and runs Crawlee scraper

                                             ▼4. **Crawlee** launches Playwright browser, navigates to Google Maps, scrolls results, parses HTML

                                 ┌───────────────────────────┐5. **Parser** extracts business cards using BeautifulSoup

                                 │    REDIS (Broker)         │6. **Enrichment** visits detail pages to get website and hours

                                 │  - Task queue             │7. **Database** saves businesses with automatic deduplication

                                 │  - Results backend        │8. **Task completes** and returns statistics

                                 └───────────────────────────┘9. **User** queries `/scrape/database/leads` to retrieve results

```

---

### Data Flow for Detail Page Enrichment

## Production Deployment

```

1. Parse search results → Extract basic card info### Environment Setup

2. Check if record complete → Skip detail if phone + website present

3. Check DB for duplicates → Skip if URL already exists with complete data- Use Python 3.11+ with a production WSGI server (Gunicorn + Uvicorn workers)

4. Visit detail page:- Run Celery workers with concurrency tuned to your hardware

   a. Wait random delay (anti-bot)- Use Redis Cluster or Sentinel for high availability

   b. Open new tab (isolation)- Set up proxy pool with residential or datacenter proxies

   c. Rotate user agent- Use Docker/Kubernetes for containerized deployment

   d. Navigate with timeout

   e. Wait for content selectors### Scaling Tips

   f. Check for CAPTCHA

   g. Extract: website, phone(s), hours, category, services- **Horizontal scaling:** Run multiple Celery workers across multiple machines

   h. Normalize phone(s)- **Proxy pool:** Use a large pool of rotating proxies to avoid bans

   i. Retry up to MAX_DETAIL_ATTEMPTS on failure- **Rate limiting:** Add delays between requests (already implemented)

5. Merge enriched data into business dict- **Database:** Migrate from SQLite to PostgreSQL for production scale

6. Atomic upsert to MongoDB:- **Monitoring:** Add Flower for Celery monitoring, Sentry for error tracking

   - Key: google_maps_url (or phone as fallback)- **Caching:** Use Redis for caching frequently accessed data

   - $set: all fields

   - $setOnInsert: created_at### Anti-Ban Best Practices

7. Log result with completeness status

```1. **Always use proxies** in production (residential proxies preferred)

2. **Randomize user agents** (already implemented)

---3. **Add random delays** (1-5 seconds between requests)

4. **Limit concurrent requests** (1-3 concurrent browsers per proxy)

## 🐛 Troubleshooting5. **Rotate proxies frequently** (every 20-50 requests)

6. **Monitor for CAPTCHAs** and rotate immediately if detected

### "Import 'motor' could not be resolved"7. **Use headless: false** for debugging, headless: true for production



```bash---

pip install motor pandas aiofiles

```## Troubleshooting



### "Motor not initialized"### "Import 'crawlee' could not be resolved"



Check MongoDB connection:Run `pip install crawlee[playwright]` and `python -m playwright install`.

```bash

# Test connection### "Playwright browsers not found"

mongosh "$MONGO_URI"

Run `python -m playwright install chromium`.

# Check .env file

cat .env | grep MONGO_URI### "Blocked by Google / CAPTCHA detected"

```

- Add more proxies to `proxies.txt`

### Empty Results- Increase delays in `.env` (`MIN_DELAY_MS` / `MAX_DELAY_MS`)

- Reduce `MAX_REQUESTS_PER_CRAWL`

```bash- Try residential proxies instead of datacenter proxies

# Check database has data

python -c "from app.db_mongo import get_business_count; print(get_business_count())"### "Database locked" error



# If empty, run a scrape firstSQLite has limited concurrency. For production, migrate to PostgreSQL or MySQL.

curl -X POST http://localhost:9000/scrape/crawlee/async \

  -H "Content-Type: application/json" \### No results in database

  -d '{"query": "coffee", "location": "Austin", "max_results": 5}'

```- Check Celery worker logs for errors

- Verify Google Maps selectors are still valid (they change frequently)

### Detail Page Enrichment Not Working- Run with `headless: false` to see what the browser is doing

- Check for anti-bot detection in logs

Check logs for errors:

```bash---

# Look for these log messages

✅ Successfully enriched: <business_name>## Next Steps

⚠️  Failed to enrich detail page after 3 attempts

```- [ ] Migrate from SQLite to PostgreSQL for production scale

- [ ] Add email enrichment service (Hunter.io, Apollo.io, etc.)

Common causes:- [ ] Build custom company enrichment scraper

- Google CAPTCHA detected (try proxy rotation)- [ ] Add webhook notifications for task completion

- Timeout too short (increase `DETAIL_PAGE_TIMEOUT`)- [ ] Implement job queuing dashboard (Flower or custom UI)

- Selectors changed (update `parse_detail_page_html`)- [ ] Add export to CSV/Excel functionality

- [ ] Integrate with CRM (Salesforce, HubSpot, etc.)

### Phone Numbers Not Normalized- [ ] Add machine learning for lead scoring

- [ ] Build two-stage pipeline: Google Maps → Custom enrichment

Verify `PHONE_NORMALIZE_REGEX` in `.env`:

```bash---

PHONE_NORMALIZE_REGEX=[^0-9+]

```## License



Test normalization:MIT License

```python

from app.parsers import normalize_phone## Contributing

print(normalize_phone("+1 (512) 555-0123"))  # Should output: +15125550123

```Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.


### Duplicate Records

Check unique index exists:
```bash
mongosh "$MONGO_URI"
use crashlens
db.businesses.getIndexes()
# Should see index on google_maps_url with unique: true
```

If missing:
```bash
python scripts/create_indexes.py
```

### Celery Tasks Not Processing

```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Check Celery worker is running
celery -A celery_tasks.tasks inspect active

# Restart worker with debug logs
celery -A celery_tasks.tasks worker --loglevel=debug
```

### Playwright Browser Errors

```bash
# Reinstall browsers
playwright install chromium

# Check browser launch
python -c "from playwright.sync_api import sync_playwright; \
  with sync_playwright() as p: p.chromium.launch()"
```

---

## 📚 Additional Documentation

- **API Reference**: `API_ENDPOINTS.md`
- **MongoDB Setup**: `README_MONGODB.md`
- **Quick Start Guide**: `QUICKSTART_COMPANY_API.md`
- **Architecture Details**: `ARCHITECTURE.md`
- **Implementation Summary**: `COMPANY_API_SUMMARY.md`

---

## 🔒 Production Deployment

### Security Checklist

- [ ] Add rate limiting (e.g., slowapi)
- [ ] Configure CORS with specific origins
- [ ] Add API authentication (API key or JWT)
- [ ] Use environment variables for secrets (never commit `.env`)
- [ ] Enable HTTPS/TLS
- [ ] Set up MongoDB Atlas IP whitelist
- [ ] Review MongoDB user permissions

### Performance Tuning

- [ ] Upgrade MongoDB Atlas to M10+ tier
- [ ] Enable auto-scaling and read replicas
- [ ] Add Redis cluster for Celery at scale
- [ ] Use Gunicorn with multiple workers:
  ```bash
  gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:9000
  ```
- [ ] Configure nginx reverse proxy
- [ ] Set up monitoring (Prometheus + Grafana)

### Monitoring

- MongoDB Atlas: Enable Performance Advisor and profiling
- Celery: Use Flower for task monitoring
  ```bash
  celery -A celery_tasks.tasks flower --port=5555
  ```
- FastAPI: Add Prometheus metrics endpoint
- Logs: Centralize with ELK stack or CloudWatch

---

## 📝 License

See `LICENSE.txt`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `pytest tests/ -v`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

---

## 📞 Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation in `/docs`
- Review logs with `--loglevel=debug`

---

**Built with ❤️ using FastAPI, Crawlee, Celery, Motor, and MongoDB**
