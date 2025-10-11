# 🚀 QUICK START: Full-Number Lead Scraping

**Goal:** Get the enhanced lead scraping system running in 15 minutes.

---

## Step 1: Install Dependencies (3 minutes)

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install all packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

**Verify:**
```bash
python -c "import crawlee, pymongo, motor; print('✅ All imports OK')"
```

---

## Step 2: Configure Environment (2 minutes)

```bash
# Copy example config
copy .env.example .env  # Windows
# cp .env.example .env  # Mac/Linux

# Edit .env file
notepad .env  # Windows
# nano .env  # Mac/Linux
```

**Required settings:**
```bash
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB_NAME=crashlens
MONGO_COLLECTION=businesses
```

**New settings (with defaults):**
```bash
DETAIL_PAGE_TIMEOUT=20000
MAX_DETAIL_ATTEMPTS=3
DETAIL_PAGE_DELAY_MS_MIN=1500
DETAIL_PAGE_DELAY_MS_MAX=3500
PHONE_NORMALIZE_REGEX=[^0-9+]
DB_UPSERT_ON_INSERT=true
```

---

## Step 3: Create MongoDB Indexes (1 minute)

```bash
cd app
python -c "from db_mongo import create_indexes; create_indexes()"
```

**Expected output:**
```
INFO - Created unique index on google_maps_url
INFO - Created index on category
INFO - Created index on rating
INFO - Created index on created_at
```

---

## Step 4: Run Unit Tests (2 minutes)

```bash
pytest tests/test_parsers.py -v
```

**Expected:**
```
======================== 30 passed in 2.45s ========================
```

If tests fail, check that imports work and paths are correct.

---

## Step 5: Run Integration Smoke Test (5 minutes - Optional)

**Note:** This makes real network requests and takes 30-60 seconds.

```bash
# Enable integration tests
set RUN_INTEGRATION=true  # Windows
# export RUN_INTEGRATION=true  # Mac/Linux

# Run smoke test
pytest tests/test_integration_smoke.py::test_smoke_scrape_end_to_end -v -s
```

**Expected:**
```
🔥 SMOKE TEST: Running minimal end-to-end scrape
📊 Initial DB count: 0
🚀 Starting crawl: coffee shop in Berkeley, CA
✅ Crawl completed! Results scraped: 3
✨ Complete records (phone + website): 2
✅ SMOKE TEST PASSED!
```

---

## Step 6: Start Services (2 minutes)

Open 3 terminals:

**Terminal 1: Redis**
```bash
redis-server
```

**Terminal 2: Celery Worker**
```bash
cd app
celery -A celery_tasks.tasks worker --loglevel=info
```

**Terminal 3: FastAPI Server**
```bash
cd app
uvicorn main:app --reload --port 9000
```

**Verify:** Visit http://localhost:9000/docs (should see Swagger UI)

---

## Step 7: Trigger a Test Scrape (2 minutes)

```bash
curl -X POST http://localhost:9000/scrape/crawlee/async ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"coffee shop\", \"location\": \"Austin, TX\", \"max_results\": 5}"
```

**Response:**
```json
{
  "task_id": "abc-123-xyz",
  "status": "pending"
}
```

**Watch Celery logs** (Terminal 2) for:
```
🔍 Attempt 1/3 - Visiting detail page: Blue Bottle Coffee
✅ Successfully enriched: Blue Bottle | Website: https://... | Phone: +1512...
💾 Saved (1/5): Blue Bottle Coffee | ✅ Complete
```

---

## Step 8: Verify Results (2 minutes)

### Option A: Using MongoDB Shell

```bash
mongosh "YOUR_MONGO_URI"
```

```javascript
use crashlens

// Count total businesses
db.businesses.count()

// Count complete records (phone + website)
db.businesses.find({
  "phone": {"$exists": true, "$ne": null},
  "website": {"$exists": true, "$ne": null}
}).count()

// View sample records
db.businesses.find({}, {name:1, phone:1, website:1}).limit(3).pretty()
```

### Option B: Using API

```bash
# Get statistics
curl "http://localhost:9000/companies/stats/summary"

# List complete records
curl "http://localhost:9000/companies?has_phone=true&has_website=true&limit=5"
```

**Expected:** At least 3-4 out of 5 businesses have phone + website.

---

## ✅ Success Checklist

After completing all steps:

- [ ] All dependencies installed (no import errors)
- [ ] `.env` configured with valid `MONGO_URI`
- [ ] MongoDB indexes created (4 indexes confirmed)
- [ ] Unit tests pass (30/30)
- [ ] Integration test passes (optional, if `RUN_INTEGRATION=true`)
- [ ] Redis running (`redis-cli ping` returns `PONG`)
- [ ] Celery worker running (no errors in logs)
- [ ] FastAPI server running (http://localhost:9000/docs accessible)
- [ ] Test scrape completed (5 businesses processed)
- [ ] Database has complete records (phone + website present)

---

## 🐛 Common Issues

### "Import 'motor' could not be resolved"
```bash
pip install motor pandas aiofiles
```

### "Timeout on detail page"
Increase timeout in `.env`:
```bash
DETAIL_PAGE_TIMEOUT=30000
MAX_DETAIL_ATTEMPTS=5
```

### "Detected CAPTCHA or blocking"
- Add proxies to `proxies.txt`
- Increase delays in `.env`:
  ```bash
  DETAIL_PAGE_DELAY_MS_MIN=3000
  DETAIL_PAGE_DELAY_MS_MAX=6000
  ```

### "Empty results in database"
- Check MongoDB connection: `mongosh "$MONGO_URI"`
- Verify Celery task completed: Check Terminal 2 logs
- Try different query (e.g., "restaurant" in "San Francisco")

### "Celery not processing tasks"
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Restart Celery with debug logs
celery -A celery_tasks.tasks worker --loglevel=debug
```

---

## 📚 Next Steps

After quick start works:

1. **Read Full Documentation:** `README.md`
2. **Run Verification Guide:** `VERIFICATION.md`
3. **Scale Up:** Increase `max_results` to 20-50
4. **Add Proxies:** Populate `proxies.txt` for production
5. **Monitor:** Watch Celery logs for success/failure patterns
6. **Tune Parameters:** Adjust timeouts and delays based on results

---

## 📞 Need Help?

- **Full Setup Guide:** `README.md`
- **Verification Steps:** `VERIFICATION.md`
- **Implementation Details:** `IMPLEMENTATION_COMPLETE.md`
- **API Reference:** `API_ENDPOINTS.md`
- **Troubleshooting:** `README.md` → Troubleshooting section

---

**Total Time:** 15 minutes  
**Status:** 🟢 Ready to scrape!  
**Next:** Scale up and monitor results

🚀 **Happy Scraping!** 🚀
