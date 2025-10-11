# Lead Generation Backend with MongoDB

Complete FastAPI + Celery + Crawlee scraping platform with MongoDB persistence.

## Quick Start

See **QUICKSTART.md** for 5-minute setup guide.

## MongoDB Setup (NEW!)

### 1. Get MongoDB Connection String

**Option A: MongoDB Atlas (Recommended)**
- Sign up at https://www.mongodb.com/cloud/atlas
- Create M0 free cluster
- Create database user
- Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/`

**Option B: Local MongoDB**
```bash
# Install and start MongoDB
mongod --dbpath /data/db
# Connection string: mongodb://localhost:27017/
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env:
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB_NAME=crashlens
MONGO_COLLECTION=businesses
```

### 3. Test Connection

```bash
python -c "from app.db_mongo import get_client; get_client(); print('✅ MongoDB connected!')"
```

## Features

- ✅ **Crawlee Playwright scraper** with anti-bot measures
- ✅ **MongoDB persistence** with automatic deduplication
- ✅ **Proxy rotation** and user-agent randomization
- ✅ **FastAPI async endpoints**
- ✅ **Celery background jobs**
- ✅ **SQLite backup** (automatic fallback)

## Installation

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Running

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery
celery -A app.celery_tasks.tasks worker --loglevel=info

# Terminal 3: FastAPI
uvicorn app.main:app --reload --port 9000
```

## API Endpoints

### Scrape with Crawlee (MongoDB)

**POST** `/scrape/crawlee/async`
```json
{
  "query": "coffee shop",
  "location": "San Francisco",
  "max_results": 20,
  "headless": true
}
```

### Get Results from MongoDB

**GET** `/scrape/database/leads?limit=100&offset=0`

Returns paginated results from MongoDB with automatic deduplication.

## MongoDB Schema

```javascript
{
  _id: ObjectId,
  name: String,
  address: String,
  phone: String,
  website: String,
  rating: Number,
  reviews: Number,
  google_maps_url: String (unique),  // Deduplication key
  category: String,
  hours: String,
  created_at: ISODate
}
```

### Indexes (Automatic)

- `google_maps_url` (unique) — Deduplication
- `category` — Filtering
- `rating` — Sorting
- `created_at` — Time queries

## Testing MongoDB

### Run Test Scrape

```bash
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -H "Content-Type: application/json" \
  -d '{"query": "pizza", "location": "New York", "max_results": 5}'
```

### Query MongoDB

**Using MongoDB Compass (GUI):**
- Connect with your MONGO_URI
- Browse `crashlens` database → `businesses` collection

**Using mongosh (CLI):**
```bash
mongosh "your-connection-string"
use crashlens
db.businesses.countDocuments()
db.businesses.find().limit(5)
```

**Using Python:**
```python
from app.db_mongo import get_business_count, get_all_businesses
print(f"Total: {get_business_count()}")
businesses = get_all_businesses(limit=5)
```

### Verify Deduplication

Run same query twice and verify count doesn't double:

```bash
# First run
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -d '{"query": "pizza", "location": "NYC", "max_results": 5}'

# Check count: db.businesses.countDocuments()

# Second run (same query)
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -d '{"query": "pizza", "location": "NYC", "max_results": 5}'

# Count should be same or slightly higher (not doubled!)
```

## MongoDB Benefits

✅ **Scalability** — Handles millions of documents  
✅ **Flexible schema** — Add fields without migrations  
✅ **Performance** — Fast queries with indexes  
✅ **Cloud-native** — Atlas free tier + auto-backups  
✅ **Deduplication** — Automatic via unique index  
✅ **JSON-native** — Perfect for APIs

## Architecture

```
FastAPI → Celery → Crawlee → Playwright → Google Maps
                      ↓
                   Parser
                      ↓
                  MongoDB (upsert on google_maps_url)
```

## Troubleshooting

### "pymongo not found"
```bash
pip install pymongo dnspython
```

### "MongoDB connection failed"
- Check `MONGO_URI` in `.env`
- For Atlas: Whitelist your IP in Network Access
- For local: Ensure `mongod` is running

### "ServerSelectionTimeoutError"
- MongoDB not accessible
- Check firewall/network
- Verify connection string format

### "Duplicate key error"
✅ Normal! Means deduplication is working.

## Migration from SQLite

```python
# migration_script.py
from app.db import get_all_businesses as get_sqlite
from app.db_mongo import save_business

businesses = get_sqlite(limit=10000)
for b in businesses:
    save_business(b)
print(f"Migrated {len(businesses)} businesses")
```

## Production Checklist

- [ ] Use MongoDB Atlas M10+ tier
- [ ] Enable replica set (Atlas default)
- [ ] Configure backups (Atlas auto-backup)
- [ ] Add compound indexes for common queries
- [ ] Monitor with Atlas metrics
- [ ] Use connection string with `?retryWrites=true&w=majority`

## Documentation

- **QUICKSTART.md** — 5-minute setup guide
- **IMPLEMENTATION_SUMMARY.md** — Technical details
- **validate_setup.py** — Automated validation script

## API Docs

- http://localhost:9000/docs (Swagger)
- http://localhost:9000/redoc (ReDoc)

## Next Steps

- [ ] Add more data sources (LinkedIn, YC, etc.)
- [ ] Email enrichment service
- [ ] Custom enrichment scraper
- [ ] Export to CSV/Excel
- [ ] CRM integration
- [ ] Lead scoring ML model

---

**Full documentation:** See original README for comprehensive guide.
