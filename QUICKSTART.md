# Quick Start Guide — Crawlee Google Maps Scraper

## 🚀 Get Running in 5 Minutes

### Step 1: Install Dependencies (2 min)

```bash
# Navigate to project directory
cd "C:\Users\LawLight\OneDrive\Desktop\Caprae-Capital-s-backend"

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers (CRITICAL - downloads ~300MB)
python -m playwright install chromium
```

### Step 2: Start Redis (1 min)

```bash
# Option A: Windows native (if installed)
redis-server

# Option B: Docker (recommended)
docker run -d -p 6379:6379 redis:latest

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### Step 3: Start Celery Worker (1 min)

Open a **new terminal** and run:

```bash
cd "C:\Users\LawLight\OneDrive\Desktop\Caprae-Capital-s-backend"
celery -A app.celery_tasks.tasks worker --loglevel=info
```

Keep this terminal open. You should see:
```
[tasks]
  . scrape_leads
  . scrape_leads_from_google_maps
  . scrape_leads_from_google_maps_crawlee
```

### Step 4: Start FastAPI Server (1 min)

Open **another new terminal** and run:

```bash
cd "C:\Users\LawLight\OneDrive\Desktop\Caprae-Capital-s-backend"
uvicorn app.main:app --reload --port 9000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:9000
```

---

## ✅ Test the Scraper (2 min)

### Option A: Web UI (Easiest)

1. Open browser: http://localhost:9000/docs
2. Expand **POST** `/scrape/crawlee/async`
3. Click "Try it out"
4. Use this test payload:

```json
{
  "query": "pizza",
  "location": "New York",
  "max_results": 5,
  "headless": true
}
```

5. Click "Execute"
6. Copy the `task_id` from the response
7. Expand **GET** `/scrape/crawlee/task/{task_id}`
8. Paste your task_id and click "Execute"
9. Wait 30-60 seconds, then check again until status is "SUCCESS"

### Option B: Command Line

```bash
# Start the scrape
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -H "Content-Type: application/json" \
  -d '{"query": "pizza", "location": "New York", "max_results": 5, "headless": true}'

# Copy the task_id from response, then check status:
curl http://localhost:9000/scrape/crawlee/task/{TASK_ID}

# Query the database
curl http://localhost:9000/scrape/database/leads?limit=10
```

### Option C: Check Database Directly

```bash
# Open database
sqlite3 leads.db

# Count businesses
SELECT COUNT(*) FROM businesses;

# View results
SELECT name, address, website FROM businesses LIMIT 5;

# Exit
.quit
```

---

## 🔍 What to Expect

### First Run (Without Proxies)
- ✅ Should scrape 3-5 results successfully
- ⚠️ May get blocked after ~10 requests (Google rate limiting)
- ✅ Database should have entries with name, address, phone
- ⚠️ Some websites might be missing (detail pages may fail)

### With Proxies (Production)
- ✅ Should scrape 20-50+ results without blocking
- ✅ More reliable detail page visits (website extraction)
- ✅ Can run multiple concurrent jobs

---

## ⚙️ Configuration (Optional)

### Add Proxies (Recommended for Production)

1. Create `proxies.txt` in project root:

```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
192.168.1.100:3128
```

2. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

3. Edit `.env` to configure behavior:

```bash
# Database
DB_PATH=leads.db

# Proxies (comment out if not using)
PROXY_LIST_PATH=proxies.txt
USER_AGENTS_PATH=user_agents.txt

# Crawler behavior
HEADLESS=true
MAX_PER_SESSION=50
MAX_REQUESTS_PER_CRAWL=20

# Delays (milliseconds) - increase to avoid blocking
MIN_DELAY_MS=1500
MAX_DELAY_MS=4000
```

---

## 🐛 Troubleshooting

### "Import 'crawlee' could not be resolved"

```bash
pip install crawlee[playwright]
python -m playwright install chromium
```

### "Connection refused to localhost:6379"

Redis is not running. Start it:

```bash
redis-server
# or
docker run -d -p 6379:6379 redis:latest
```

### "Task stays in PENDING status"

Celery worker is not running. Check the Celery terminal for errors.

### "Blocked by Google / CAPTCHA detected"

- Add proxies to `proxies.txt`
- Increase delays in `.env` (MIN_DELAY_MS=2000, MAX_DELAY_MS=5000)
- Reduce max_results (try 5-10 instead of 20+)

### "No results in database"

- Check Celery worker logs for errors
- Try with `headless: false` to see browser
- Google Maps selectors may have changed (check parser.py)

### "Database locked"

SQLite has limited concurrency. Only run 1-2 concurrent tasks. For production, migrate to PostgreSQL.

---

## 📊 View Celery Worker Logs

In the Celery terminal, you should see:

```
[2025-10-12 10:30:00,123: INFO/MainProcess] Task scrape_leads_from_google_maps_crawlee[abc123] received
[2025-10-12 10:30:02,456: INFO/ForkPoolWorker-1] Found 18 businesses on page
[2025-10-12 10:30:03,789: INFO/ForkPoolWorker-1] Saved: Blue Bottle Coffee (1/5)
[2025-10-12 10:30:05,012: INFO/ForkPoolWorker-1] Saved: Stumptown Coffee (2/5)
...
[2025-10-12 10:30:45,678: INFO/ForkPoolWorker-1] Task scrape_leads_from_google_maps_crawlee[abc123] succeeded
```

---

## 🎯 Next Steps

### For Testing
1. ✅ Run small test scrapes (5-10 results)
2. ✅ Verify database entries are correct
3. ✅ Check that websites are being extracted
4. ✅ Test deduplication (run same query twice)

### For Production
1. 🔧 Add production proxies to `proxies.txt`
2. 🔧 Increase `max_results` to 20-50
3. 🔧 Monitor Celery logs for blocking
4. 🔧 Migrate to PostgreSQL if scaling beyond 1000s of leads
5. 🔧 Set up Flower for Celery monitoring: `pip install flower && celery -A app.celery_tasks.tasks flower`

---

## 📚 Learn More

- **Full Documentation:** See `README.md`
- **Implementation Details:** See `IMPLEMENTATION_SUMMARY.md`
- **API Docs:** http://localhost:9000/docs
- **Celery Monitoring:** Install Flower (`pip install flower`) then run `celery -A app.celery_tasks.tasks flower`

---

## ✅ Success Checklist

- [ ] Redis is running (`redis-cli ping` returns PONG)
- [ ] Celery worker is running (terminal shows worker started)
- [ ] FastAPI server is running (http://localhost:9000/docs loads)
- [ ] Playwright browsers installed (`python -m playwright install chromium`)
- [ ] Test scrape completed successfully
- [ ] Database has entries (`sqlite3 leads.db "SELECT COUNT(*) FROM businesses;"`)
- [ ] Can query results via API (`GET /scrape/database/leads`)

**If all checkboxes are ✅, you're ready for production!** 🎉

---

## 💡 Pro Tips

1. **Start small:** Use `max_results: 5` for testing, then scale up
2. **Monitor logs:** Keep Celery terminal visible to catch errors early
3. **Test deduplication:** Run same query twice, verify no duplicates in DB
4. **Use proxies:** Even for testing, helps avoid blocks
5. **Headless false:** Set `headless: false` to debug scraping issues
6. **Database backup:** Backup `leads.db` regularly (`cp leads.db leads.db.backup`)
7. **Rate limiting:** Don't run too many concurrent jobs (max 2-3 without good proxies)

---

**Happy scraping! 🚀**
