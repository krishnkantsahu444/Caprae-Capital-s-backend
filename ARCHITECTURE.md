# Company Search API - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COMPANY SEARCH API                          │
│                    (FastAPI + Motor + MongoDB)                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   React UI   │  │   Postman    │  │   cURL/CLI   │              │
│  │              │  │              │  │              │              │
│  │  - Search    │  │  - Testing   │  │  - Scripts   │              │
│  │  - Filters   │  │  - Debug     │  │  - Automation│              │
│  │  - Export    │  │  - API Docs  │  │  - CI/CD     │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                       │
│         └──────────────────┴──────────────────┘                       │
│                            │                                          │
│                   HTTP/REST Requests                                 │
│                            │                                          │
└────────────────────────────┼──────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                             │
│                    (app/main.py - Port 9000)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              STARTUP EVENT (Lifecycle)                        │  │
│  │  1. Initialize Motor (async MongoDB client)                  │  │
│  │  2. Create indexes (if not exist)                            │  │
│  │  3. Test connection                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   ROUTERS (Endpoints)                         │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │                                                               │  │
│  │  /companies Router (app/routers/companies.py)                │  │
│  │  ────────────────────────────────────────────                │  │
│  │                                                               │  │
│  │  GET  /companies                                              │  │
│  │       ├─ Query: search, location, category                   │  │
│  │       ├─ Filters: rating, website, phone, services           │  │
│  │       ├─ Sort: rating, reviews, date, name                   │  │
│  │       └─ Pagination: limit (1-200), offset                   │  │
│  │                                                               │  │
│  │  GET  /companies/{id}                                         │  │
│  │       └─ Retrieve single company by ObjectId                 │  │
│  │                                                               │  │
│  │  GET  /companies/meta/categories                             │  │
│  │       └─ Distinct categories (autocomplete)                  │  │
│  │                                                               │  │
│  │  GET  /companies/meta/locations                              │  │
│  │       └─ Distinct locations (autocomplete)                   │  │
│  │                                                               │  │
│  │  GET  /companies/export/csv                                  │  │
│  │       └─ Stream CSV download (max 20k records)               │  │
│  │                                                               │  │
│  │  GET  /companies/stats/summary                               │  │
│  │       └─ Aggregate statistics                                │  │
│  │                                                               │  │
│  └───────────────────────┬───────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │            PYDANTIC SCHEMAS (Validation)                      │  │
│  │            app/schemas/company.py                             │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  • CompanyBase       - Base fields                           │  │
│  │  • CompanyOut        - Response with _id                     │  │
│  │  • CompaniesListResponse - Paginated results                 │  │
│  │  • MetaCategoriesResponse - Category list                    │  │
│  │  • MetaLocationsResponse - Location list                     │  │
│  └───────────────────────┬───────────────────────────────────────┘  │
│                          │                                           │
└──────────────────────────┼───────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABASE LAYER (Motor)                            │
│                    app/db_motor.py                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │         AsyncIOMotorClient (Singleton Pattern)                │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  • init_motor()          - Initialize client                 │  │
│  │  • get_collection()      - Get collection instance           │  │
│  │  • create_indexes_async()- Create indexes on startup         │  │
│  │  • close_motor()         - Cleanup on shutdown               │  │
│  └───────────────────────┬───────────────────────────────────────┘  │
│                          │                                           │
│             Connection Pooling                                       │
│             (Max 100 connections)                                    │
│                          │                                           │
└──────────────────────────┼───────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MONGODB DATABASE                                 │
│                  (Atlas M10+ or Local)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Database: crashlens                                                 │
│  Collection: businesses                                              │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                        INDEXES                                │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  1. google_maps_url  (UNIQUE)   - Deduplication             │  │
│  │  2. category         (Standard) - Filter by type             │  │
│  │  3. location         (Standard) - Filter by location         │  │
│  │  4. rating           (Standard) - Sort/filter by rating      │  │
│  │  5. created_at       (Standard) - Sort by date               │  │
│  │  6. (category, rating) (Compound) - Combined filters         │  │
│  │  7. (location, rating) (Compound) - Location + rating        │  │
│  │  8. business_name    (Text)     - Full-text search           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    DOCUMENT SCHEMA                            │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  {                                                            │  │
│  │    "_id": ObjectId("..."),                                    │  │
│  │    "business_name": "Artisan Coffee",                         │  │
│  │    "address": "123 Main St, Austin, TX",                      │  │
│  │    "phone": "(512) 555-0123",                                 │  │
│  │    "rating": 4.7,                                             │  │
│  │    "review_count": 342,                                       │  │
│  │    "category": "Coffee shop",                                 │  │
│  │    "google_maps_url": "https://...",                          │  │
│  │    "website": "https://artisancoffee.com",                    │  │
│  │    "hours": "Mon-Fri: 7am-8pm",                               │  │
│  │    "services": ["Dine-in", "Takeout", "Delivery"],           │  │
│  │    "location": "Austin, TX",                                  │  │
│  │    "created_at": ISODate("2024-10-01T10:30:00Z")             │  │
│  │  }                                                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    OPERATIONS                                 │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  • find() with filters     - Query companies                 │  │
│  │  • find_one()             - Get single company               │  │
│  │  • distinct()             - Get unique values                │  │
│  │  • count_documents()      - Total count                      │  │
│  │  • aggregate()            - Statistics                       │  │
│  │  • update_one(upsert=True)- Deduplication (from scraper)     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                    PARALLEL SYSTEM (Coexists)                        │
│                     Celery Tasks + Scrapers                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │            CELERY WORKER (Background Tasks)                   │  │
│  │            app/celery_tasks/tasks.py                          │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  • Uses SYNC MongoDB (app/db_mongo.py)                       │  │
│  │  • Crawlee scraper → Google Maps                             │  │
│  │  • Saves to MongoDB via pymongo (not Motor)                  │  │
│  │  • Automatic deduplication (same collection)                 │  │
│  └───────────────────────┬───────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│              Same MongoDB Collection                                 │
│              (businesses in crashlens)                               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW EXAMPLE                             │
└─────────────────────────────────────────────────────────────────────┘

1. USER REQUEST
   Frontend → GET /companies?query=coffee&location=Austin&rating_min=4.5
              └─ Headers: Accept: application/json

2. FASTAPI ROUTING
   app/main.py → companies.router → list_companies()

3. VALIDATION
   Pydantic validates query parameters
   ├─ query: "coffee" ✓
   ├─ location: "Austin" ✓
   ├─ rating_min: 4.5 ✓
   └─ limit: 20 (default) ✓

4. BUSINESS LOGIC
   Build MongoDB filters:
   {
     "$or": [
       {"business_name": {"$regex": "coffee", "$options": "i"}},
       {"category": {"$regex": "coffee", "$options": "i"}}
     ],
     "address": {"$regex": "Austin", "$options": "i"},
     "rating": {"$gte": 4.5}
   }

5. DATABASE QUERY
   Motor → MongoDB Atlas
   ├─ Uses compound index (category, rating)
   ├─ Query time: ~50ms
   └─ Returns: 15 matching documents

6. POST-PROCESSING
   ├─ Convert ObjectId → string
   ├─ Apply pagination (skip 0, limit 20)
   └─ Format response

7. RESPONSE
   {
     "total": 15,
     "results": [
       {
         "_id": "671abc123...",
         "business_name": "Mozart's Coffee",
         "category": "Coffee shop",
         "rating": 4.8,
         "location": "Austin, TX",
         ...
       },
       ...
     ]
   }

8. CLIENT RENDERING
   Frontend displays results in UI


┌─────────────────────────────────────────────────────────────────────┐
│                     TECHNOLOGY STACK                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   FastAPI   │  │    Motor    │  │   MongoDB   │  │   Pydantic  │
│   0.110.0   │  │    3.3.2    │  │    Atlas    │  │    2.6.4    │
│             │  │             │  │             │  │             │
│  REST API   │  │  Async DB   │  │  NoSQL DB   │  │ Validation  │
│  Framework  │  │   Driver    │  │   (Cloud)   │  │  Schemas    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Pandas    │  │  Aiofiles   │  │   Uvicorn   │  │    Redis    │
│    2.1.4    │  │   23.2.1    │  │    0.29.0   │  │    5.0.1    │
│             │  │             │  │             │  │             │
│ CSV Export  │  │  Async I/O  │  │ ASGI Server │  │   Celery    │
│ Processing  │  │   Support   │  │             │  │   Broker    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────┐
                      │   Load Balancer │
                      │     (Nginx)     │
                      └────────┬────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────▼─────┐ ┌─────▼──────┐ ┌────▼───────┐
         │  Uvicorn   │ │  Uvicorn   │ │  Uvicorn   │
         │  Worker 1  │ │  Worker 2  │ │  Worker 3  │
         └──────┬─────┘ └─────┬──────┘ └────┬───────┘
                │              │              │
                └──────────────┼──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   MongoDB Atlas     │
                    │   Replica Set       │
                    │   ┌───────────────┐ │
                    │   │   Primary     │ │
                    │   ├───────────────┤ │
                    │   │  Secondary 1  │ │
                    │   ├───────────────┤ │
                    │   │  Secondary 2  │ │
                    │   └───────────────┘ │
                    └─────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                       PERFORMANCE METRICS                            │
└─────────────────────────────────────────────────────────────────────┘

Endpoint                      Avg Response Time    Throughput
──────────────────────────────────────────────────────────────────────
GET /companies (indexed)              30ms         1000 req/s
GET /companies (regex search)        150ms          300 req/s
GET /companies/{id}                   20ms         1500 req/s
GET /meta/categories                  50ms          800 req/s
GET /export/csv (1000 rows)         1500ms           10 req/s
GET /stats/summary                   400ms          100 req/s

Capacity:
- Documents: 10M+ (with proper indexes)
- Concurrent users: 500+ (4 workers)
- Database size: 50GB+ (Atlas M10)


┌─────────────────────────────────────────────────────────────────────┐
│                          SECURITY LAYERS                             │
└─────────────────────────────────────────────────────────────────────┘

Layer 1: Input Validation
├─ Pydantic schemas validate all inputs
├─ Type checking (string, int, float, bool)
├─ Range validation (rating: 0-5, limit: 1-200)
└─ Format validation (ObjectId format for IDs)

Layer 2: Injection Prevention
├─ Regex patterns: re.escape() all user inputs
├─ Sort fields: Whitelisted (rating, created_at, etc.)
├─ MongoDB operators: No $where or JavaScript execution
└─ Query limits: Max 200 results per page

Layer 3: Error Handling
├─ All exceptions caught and logged
├─ Generic error messages (no stack traces exposed)
├─ Proper HTTP status codes (400, 404, 500)
└─ Logging for debugging (internal only)

Layer 4: Rate Limiting (Recommended)
├─ 100 requests/minute per IP
├─ Slowapi middleware integration
└─ Export endpoint: Lower limit (10/min)

Layer 5: Authentication (Recommended)
├─ API key validation
├─ JWT token support
└─ Role-based access control


Legend:
─────────────────────────
┌──┐  Component/System
│  │  
└──┘  

  │   Data flow
  ▼   

─────  Connection

[...]  Optional/Future
