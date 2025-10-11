# 🚀 Quick Setup Guide - Company Search API

Complete step-by-step guide to get the company search API running in 5 minutes.

---

## ✅ Prerequisites

- Python 3.8+
- MongoDB (Atlas or local)
- Redis (for Celery background tasks)
- Virtual environment activated

---

## 📦 Step 1: Install Dependencies

```bash
# Install all packages including Motor (async MongoDB)
pip install -r requirements.txt

# Verify installation
pip list | grep -E "motor|pandas|aiofiles"
```

**Expected output:**
```
aiofiles          23.2.1
motor             3.3.2
pandas            2.1.4
```

---

## 🔧 Step 2: Configure Environment

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your MongoDB credentials:**
   ```bash
   # MongoDB Atlas (Cloud)
   MONGO_URI=mongodb+srv://username:password@cluster0.mongodb.net/
   MONGO_DB_NAME=crashlens
   MONGO_COLLECTION=businesses

   # Or Local MongoDB
   MONGO_URI=mongodb://localhost:27017/
   MONGO_DB_NAME=crashlens
   MONGO_COLLECTION=businesses
   ```

3. **Test MongoDB connection:**
   ```bash
   python -c "from app.db_motor import init_motor; init_motor(); print('✅ Connected!')"
   ```

---

## 🗄️ Step 3: Create MongoDB Indexes

Run the index creation script:

```bash
python scripts/create_indexes.py
```

**Expected output:**
```
Connecting to MongoDB: mongodb+srv://...
Using database: crashlens
Using collection: businesses

Creating indexes...
1. Creating UNIQUE index on 'google_maps_url'...
   ✅ Created
2. Creating index on 'category'...
   ✅ Created
...
✅ Done!

Total documents: 0
```

**Note:** If you see "Total documents: 0", you'll need to run a scrape to populate data (Step 5).

---

## 🚀 Step 4: Start the Server

### Option A: Development Mode (with auto-reload)

```bash
uvicorn app.main:app --reload --port 9000
```

### Option B: Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4
```

**Expected startup logs:**
```
INFO:     Initializing Motor (async MongoDB) for FastAPI...
INFO:root:Initializing Motor client for MongoDB: mongodb+srv://...
INFO:root:Motor initialized: Database=crashlens, Collection=businesses
INFO:root:Created unique index on 'google_maps_url'
INFO:root:Created index on 'category'
INFO:root:Created index on 'location'
INFO:root:Created index on 'rating'
INFO:root:Created index on 'created_at'
INFO:root:Created compound index on 'category' and 'rating'
INFO:root:✅ All Motor indexes created successfully
INFO:     ✅ Motor initialized successfully
INFO:     Uvicorn running on http://127.0.0.1:9000 (Press CTRL+C to quit)
```

✅ **If you see these logs, the API is ready!**

---

## 🧪 Step 5: Test the API

### Quick Test (Terminal)

```bash
# Test basic list endpoint
curl "http://localhost:9000/companies?limit=5"
```

**Expected response:**
```json
{
  "total": 0,
  "results": []
}
```

**Note:** Empty results are normal if database is empty. Continue to populate data.

### Automated Test Script

```bash
python scripts/test_endpoints.py
```

**Expected output:**
```
============================================================
Company Search API - Endpoint Validation
============================================================
Base URL: http://localhost:9000

✅ PASS - List Companies (Basic)
   Status: 200, Keys: ['total', 'results']

✅ PASS - Get Categories
   Status: 200, Keys: ['categories']

...

SUMMARY: 10/10 tests passed (100.0%)
============================================================
✅ All tests passed! API is working correctly.
```

### Interactive Testing (Swagger UI)

Open in browser:
```
http://localhost:9000/docs
```

You'll see an interactive API documentation where you can test all endpoints directly.

---

## 📊 Step 6: Populate Database with Sample Data

### Start Required Services (in separate terminals)

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Celery Worker:**
```bash
celery -A app.celery_tasks.tasks worker --loglevel=info
```

**Terminal 3 - FastAPI Server:**
```bash
uvicorn app.main:app --reload --port 9000
```

### Run a Test Scrape

**Terminal 4 - Trigger Scrape:**
```bash
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee",
    "location": "Austin",
    "max_results": 10,
    "headless": true
  }'
```

**Expected response:**
```json
{
  "task_id": "abc123-def456-...",
  "status": "Task submitted successfully",
  "check_status_url": "/scrape/crawlee/task/abc123-def456-..."
}
```

### Check Scrape Status

```bash
curl "http://localhost:9000/scrape/crawlee/task/{task_id}"
```

### Verify Data in Database

```bash
# Check count
curl "http://localhost:9000/companies/stats/summary"

# List results
curl "http://localhost:9000/companies?limit=5"
```

**Expected response (after scrape completes):**
```json
{
  "total": 10,
  "results": [
    {
      "_id": "671234567890abcdef123456",
      "business_name": "Mozart's Coffee Roasters",
      "category": "Coffee shop",
      "rating": 4.6,
      "address": "3825 Lake Austin Blvd, Austin, TX",
      "phone": "(512) 477-2900",
      "website": "https://www.mozartscoffee.com",
      ...
    }
  ]
}
```

---

## 🎯 Step 7: Test All Endpoints

### 1. Basic List
```bash
curl "http://localhost:9000/companies?limit=10"
```

### 2. Search Coffee Shops
```bash
curl "http://localhost:9000/companies?query=coffee&limit=10"
```

### 3. Filter by Location
```bash
curl "http://localhost:9000/companies?location=Austin&limit=10"
```

### 4. High-Rated Only
```bash
curl "http://localhost:9000/companies?rating_min=4.5&limit=10"
```

### 5. Has Website
```bash
curl "http://localhost:9000/companies?has_website=true&limit=10"
```

### 6. Sort by Rating
```bash
curl "http://localhost:9000/companies?sort_by=rating&order=desc&limit=10"
```

### 7. Get Categories
```bash
curl "http://localhost:9000/companies/meta/categories"
```

### 8. Get Locations
```bash
curl "http://localhost:9000/companies/meta/locations"
```

### 9. Export to CSV
```bash
curl -o companies.csv "http://localhost:9000/companies/export/csv?limit=100"
```

### 10. Database Stats
```bash
curl "http://localhost:9000/companies/stats/summary"
```

---

## 🎨 Step 8: Import Postman Collection

1. Open Postman
2. Click **Import**
3. Select `postman_collection.json`
4. Collection "Company Search API" will appear with 14 pre-configured requests
5. Click any request and hit **Send** to test

---

## 📱 Step 9: Frontend Integration

### React Example

```jsx
import { useState, useEffect } from 'react';

function CompanyList() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:9000/companies?limit=20')
      .then(res => res.json())
      .then(data => {
        setCompanies(data.results);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Companies ({companies.length})</h1>
      {companies.map(c => (
        <div key={c._id}>
          <h3>{c.business_name}</h3>
          <p>{c.category} | ⭐ {c.rating}</p>
          <a href={c.website}>Visit Website</a>
        </div>
      ))}
    </div>
  );
}
```

### Vanilla JavaScript

```html
<!DOCTYPE html>
<html>
<head>
  <title>Company Search</title>
</head>
<body>
  <input id="search" type="text" placeholder="Search companies...">
  <div id="results"></div>

  <script>
    const searchInput = document.getElementById('search');
    const resultsDiv = document.getElementById('results');

    searchInput.addEventListener('input', async (e) => {
      const query = e.target.value;
      if (!query) return;

      const res = await fetch(`http://localhost:9000/companies?query=${query}&limit=10`);
      const data = await res.json();

      resultsDiv.innerHTML = data.results.map(c => `
        <div>
          <h3>${c.business_name}</h3>
          <p>${c.category} | ⭐ ${c.rating}</p>
        </div>
      `).join('');
    });
  </script>
</body>
</html>
```

---

## 🐛 Troubleshooting

### Issue: "Import 'motor' could not be resolved"
**Solution:**
```bash
pip install motor pandas aiofiles
```

### Issue: "Motor not initialized"
**Solution:**
```bash
# Check .env has correct MONGO_URI
cat .env | grep MONGO_URI

# Test connection manually
python -c "from pymongo import MongoClient; client = MongoClient('YOUR_MONGO_URI'); print(client.server_info())"
```

### Issue: Empty results `{"total": 0, "results": []}`
**Solution:**
1. Database is empty, run a scrape (see Step 6)
2. Or import sample data if available

### Issue: Server won't start
**Solution:**
```bash
# Check if port 9000 is already in use
netstat -ano | findstr :9000

# Kill the process or use different port
uvicorn app.main:app --reload --port 9001
```

### Issue: Celery worker not processing tasks
**Solution:**
```bash
# Make sure Redis is running
redis-cli ping  # Should return "PONG"

# Start Celery with verbose logging
celery -A app.celery_tasks.tasks worker --loglevel=debug
```

### Issue: CSV export fails
**Solution:**
- Reduce limit (max 20000)
- Check disk space
- Verify MongoDB connection

---

## 📚 Documentation

- **Full API Reference:** `API_ENDPOINTS.md`
- **Implementation Details:** `COMPANY_API_SUMMARY.md`
- **MongoDB Setup:** `README_MONGODB.md`
- **Swagger UI:** http://localhost:9000/docs
- **ReDoc:** http://localhost:9000/redoc

---

## ✅ Verification Checklist

Before deploying to production:

- [ ] Dependencies installed: `pip list | grep motor`
- [ ] MongoDB connection works
- [ ] Indexes created: `python scripts/create_indexes.py`
- [ ] Server starts without errors
- [ ] All endpoints return 200: `python scripts/test_endpoints.py`
- [ ] Database has sample data
- [ ] Postman collection works
- [ ] Frontend can connect
- [ ] CSV export works
- [ ] Rate limiting configured (production)
- [ ] CORS configured (production)
- [ ] Authentication added (production)

---

## 🚢 Production Deployment

### Recommended Stack:

**MongoDB:**
- Atlas M10+ tier ($60/mo)
- Auto-scaling enabled
- Automated backups

**Server:**
- Uvicorn with Gunicorn
- 4-8 workers
- Behind nginx reverse proxy

**Example Production Command:**
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:9000 \
  --access-logfile - \
  --error-logfile -
```

**Nginx Config:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🎉 Success!

If you've completed all steps, you now have:

✅ Production-ready company search API  
✅ 6 search endpoints with advanced filtering  
✅ CSV export with streaming  
✅ Metadata endpoints for autocomplete  
✅ Statistics endpoint for dashboards  
✅ MongoDB indexes for fast queries  
✅ Complete documentation and testing tools  

**Next steps:**
- Connect your frontend
- Add more data sources (Apollo.io, LinkedIn, etc.)
- Implement rate limiting
- Set up monitoring

---

**Need help?** Check the full documentation in `API_ENDPOINTS.md` or `COMPANY_API_SUMMARY.md`
