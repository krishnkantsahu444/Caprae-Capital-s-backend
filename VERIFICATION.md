# Verification Guide: Full Number Lead Scraping

This guide walks through verifying that the enhanced scraping system is working correctly and producing complete records with phone numbers and websites.

---

## ✅ Pre-Verification Checklist

Before running tests, ensure:

- [ ] `.env` file is configured with valid `MONGO_URI`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Playwright browsers installed: `playwright install chromium`
- [ ] Redis is running: `redis-cli ping` returns `PONG`
- [ ] MongoDB is accessible: `mongosh "$MONGO_URI"` connects successfully

---

## 🧪 Step 1: Run Unit Tests

Unit tests verify parsers and utilities without making network requests.

```bash
# Run all unit tests
pytest tests/test_parsers.py -v

# Expected output: All tests pass
```

### Expected Results

```
tests/test_parsers.py::test_normalize_phone_valid PASSED
tests/test_parsers.py::test_normalize_phone_with_spaces_and_dashes PASSED
tests/test_parsers.py::test_normalize_phone_international PASSED
tests/test_parsers.py::test_normalize_phone_too_short PASSED
tests/test_parsers.py::test_normalize_phone_too_long PASSED
tests/test_parsers.py::test_parse_card_html_basic PASSED
tests/test_parsers.py::test_parse_card_html_with_url PASSED
tests/test_parsers.py::test_parse_detail_page_html_complete PASSED
tests/test_parsers.py::test_parse_detail_page_html_website_only PASSED
tests/test_parsers.py::test_parse_detail_page_html_phone_only PASSED
tests/test_parsers.py::test_parse_detail_page_html_filters_google_urls PASSED
tests/test_parsers.py::test_parse_detail_page_html_multiple_phones PASSED
...
======================== 30 passed in 2.45s ========================
```

### Troubleshooting Unit Tests

**Import errors:**
```bash
# Ensure app directory is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/app"
# Windows: set PYTHONPATH=%PYTHONPATH%;%cd%\app
```

**BeautifulSoup errors:**
```bash
pip install beautifulsoup4 lxml
```

---

## 🌐 Step 2: Run Integration Smoke Test

Integration test performs a real scrape with minimal results to verify end-to-end functionality.

```bash
# Enable integration tests
export RUN_INTEGRATION=true  # Windows: set RUN_INTEGRATION=true

# Run smoke test (takes 30-60 seconds)
pytest tests/test_integration_smoke.py -v -s
```

### Expected Output

```
🔥 SMOKE TEST: Running minimal end-to-end scrape
================================================
📊 Initial DB count: 127
🚀 Starting crawl: coffee shop in Berkeley, CA
   Max results: 3
   Headless: False (for debugging)

[Crawlee logs showing detail page visits]

✅ Crawl completed!
   Results scraped: 3

📊 Final DB count: 130
   New records: 3

✨ Complete records (phone + website): 2

📋 Sample of saved records:
   1. Blue Bottle Coffee
      Phone: +15105559876
      Website: https://bluebottlecoffee.com
      Complete: ✅
   2. Peet's Coffee
      Phone: +15105551234
      Website: https://peets.com
      Complete: ✅
   3. Local Cafe
      Phone: +15105554321
      Website: N/A
      Complete: ⚠️

================================================
✅ SMOKE TEST PASSED!
================================================
```

### Success Criteria

- ✅ At least 1 new record saved to database
- ✅ At least 1 record has both phone AND website (complete record)
- ✅ Phone numbers are normalized (only digits and + character)
- ✅ No duplicate records created (upsert works)

### Troubleshooting Integration Test

**"Blocked by Google - CAPTCHA detected":**
- Add proxies to `proxies.txt`
- Increase delays: `DETAIL_PAGE_DELAY_MS_MIN=2000`, `MAX=5000`
- Rotate user agents more frequently

**"Timeout on detail page":**
- Increase timeout: `DETAIL_PAGE_TIMEOUT=30000`
- Check network connection
- Verify selectors in `parse_detail_page_html`

**"No records with phone + website":**
- Check logs for enrichment errors
- Verify selectors match current Google Maps HTML
- Try different query (e.g., popular businesses in major cities)

---

## 🗄️ Step 3: Verify Database Records

### 3.1 Check Total and Complete Counts

```bash
mongosh "$MONGO_URI"
```

```javascript
use crashlens

// Total businesses
db.businesses.count()
// Expected: Should increase after each scrape

// Businesses with phone AND website (COMPLETE)
db.businesses.find({
  "phone": {"$exists": true, "$ne": null},
  "website": {"$exists": true, "$ne": null}
}).count()
// Expected: At least 50% of total (ideally 80%+)

// Businesses with phone only
db.businesses.find({
  "phone": {"$exists": true, "$ne": null}
}).count()

// Businesses with website only
db.businesses.find({
  "website": {"$exists": true, "$ne": null}
}).count()
```

### 3.2 Inspect Sample Records

```javascript
// Get 5 complete records
db.businesses.find({
  "phone": {"$exists": true, "$ne": null},
  "website": {"$exists": true, "$ne": null}
}, {
  "name": 1,
  "phone": 1,
  "website": 1,
  "category": 1,
  "rating": 1,
  "hours": 1
}).limit(5).pretty()

// Expected output example:
{
  "_id": ObjectId("..."),
  "name": "Artisan Coffee Roasters",
  "phone": "+15125550123",
  "website": "https://artisancoffee.com",
  "category": "Coffee shop",
  "rating": 4.7,
  "hours": "Mon-Fri: 7am-8pm, Sat-Sun: 8am-9pm"
}
```

### 3.3 Verify Phone Normalization

```javascript
// Check for phones with invalid characters
db.businesses.find({
  "phone": {"$regex": /[^0-9+|]/}
}).count()
// Expected: 0 (no invalid characters)

// Sample phone numbers
db.businesses.find({
  "phone": {"$exists": true}
}, {
  "name": 1,
  "phone": 1
}).limit(10).pretty()

// All phones should look like:
// - "+15125550123" (international format)
// - "5125550123" (domestic format)
// - "+15125550123|+15125559999" (multiple phones)
```

### 3.4 Check for Duplicates

```javascript
// Find duplicate google_maps_urls
db.businesses.aggregate([
  {"$group": {
    "_id": "$google_maps_url",
    "count": {"$sum": 1},
    "names": {"$push": "$name"}
  }},
  {"$match": {"count": {"$gt": 1}}}
])
// Expected: Empty result (no duplicates)
```

### 3.5 Verify Indexes

```javascript
db.businesses.getIndexes()

// Expected indexes:
// 1. _id_ (default)
// 2. google_maps_url_unique (unique: true)
// 3. category_idx
// 4. rating_idx
// 5. created_at_idx
// 6. location_idx
// 7. (category, rating) compound
// 8. (location, rating) compound
```

---

## 📊 Step 4: Run a Small Production Scrape

Test with a realistic query to verify complete workflow.

### 4.1 Start Services

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A celery_tasks.tasks worker --loglevel=info

# Terminal 3: FastAPI server
uvicorn app.main:app --reload --port 9000
```

### 4.2 Trigger Scrape via API

```bash
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -H "Content-Type: application/json" \
  -d '{
    "query": "coffee shop",
    "location": "Austin, TX",
    "max_results": 10
  }'

# Response:
{
  "task_id": "abc-123-xyz",
  "status": "pending"
}
```

### 4.3 Monitor Celery Logs

Watch for these log messages in Celery terminal:

```
✅ Successfully enriched: Blue Bottle Coffee | Website: https://... | Phone: +1512...
💾 Saved (1/10): Blue Bottle Coffee | ✅ Complete
✅ Successfully enriched: Starbucks | Website: https://... | Phone: +1512...
💾 Saved (2/10): Starbucks | ✅ Complete
⚠️  Could not enrich Local Cafe, saving partial data
💾 Saved (3/10): Local Cafe | ⚠️  Partial
```

### 4.4 Check Task Status

```bash
curl http://localhost:9000/scrape/task/abc-123-xyz

# Response when complete:
{
  "task_id": "abc-123-xyz",
  "status": "SUCCESS",
  "result": {
    "results_count": 10,
    "query": "coffee shop",
    "location": "Austin, TX"
  }
}
```

### 4.5 Verify New Records in Database

```javascript
// Find records created in last 5 minutes
db.businesses.find({
  "created_at": {"$gte": new Date(Date.now() - 5*60*1000)}
}).count()
// Expected: 10 (or max_results from your scrape)

// Check completeness
db.businesses.find({
  "created_at": {"$gte": new Date(Date.now() - 5*60*1000)},
  "phone": {"$exists": true, "$ne": null},
  "website": {"$exists": true, "$ne": null}
}).count()
// Expected: At least 7-8 out of 10 (70-80% success rate for detail enrichment)
```

---

## 📈 Step 5: Verify API Endpoints

### 5.1 Search API

```bash
# Search for complete records
curl "http://localhost:9000/companies?has_phone=true&has_website=true&limit=5"

# Expected response:
{
  "total": 127,
  "results": [
    {
      "_id": "...",
      "business_name": "Artisan Coffee",
      "phone": "+15125550123",
      "website": "https://artisancoffee.com",
      "rating": 4.7,
      ...
    }
  ]
}
```

### 5.2 Statistics API

```bash
curl "http://localhost:9000/companies/stats/summary"

# Expected response:
{
  "total_companies": 150,
  "with_website": 120,
  "with_phone": 135,
  "website_percentage": 80.0,
  "phone_percentage": 90.0,
  "avg_rating": 4.23,
  ...
}
```

### 5.3 CSV Export

```bash
curl -o export.csv "http://localhost:9000/companies/export/csv?has_phone=true&has_website=true&limit=100"

# Verify CSV content
head export.csv
# Expected: Header row + 100 businesses with phone and website
```

---

## 🎯 Success Metrics

After completing all verification steps, your system should meet these benchmarks:

| Metric | Target | Acceptable | Action if Below |
|--------|--------|------------|-----------------|
| Unit tests pass rate | 100% | 100% | Fix failing tests |
| Integration test pass rate | 100% | 100% | Check network/DB connectivity |
| Records with phone | >90% | >70% | Review phone extraction selectors |
| Records with website | >80% | >60% | Review website extraction selectors |
| Complete records (phone + website) | >75% | >50% | Increase `MAX_DETAIL_ATTEMPTS`, add proxies |
| Phone normalization success | 100% | 100% | Fix `PHONE_NORMALIZE_REGEX` |
| Duplicate records | 0 | 0 | Verify unique index, fix upsert logic |
| Detail page timeout rate | <10% | <20% | Increase `DETAIL_PAGE_TIMEOUT` |
| CAPTCHA block rate | <5% | <15% | Add more proxies, increase delays |

---

## 🔍 Debugging Common Issues

### Issue: Low Complete Record Rate (<50%)

**Diagnosis:**
```bash
# Check detail visit attempts in logs
grep "Attempt" celery.log | wc -l
grep "Successfully enriched" celery.log | wc -l

# Calculate success rate: enriched / attempts * 100
```

**Fixes:**
1. Increase timeout: `DETAIL_PAGE_TIMEOUT=30000`
2. Increase retries: `MAX_DETAIL_ATTEMPTS=5`
3. Add proxies to `proxies.txt`
4. Verify selectors in `parse_detail_page_html` match current Google Maps HTML

### Issue: Phones Not Normalized

**Diagnosis:**
```javascript
db.businesses.find({
  "phone": {"$regex": /[\(\)\-\s]/}
}).limit(5).pretty()
```

**Fixes:**
1. Check `PHONE_NORMALIZE_REGEX` in `.env`
2. Verify `normalize_phone()` is called in `visit_detail_page_and_enrich`
3. Run unit tests: `pytest tests/test_parsers.py::test_normalize_phone_valid`

### Issue: Duplicate Records

**Diagnosis:**
```javascript
db.businesses.aggregate([
  {"$group": {"_id": "$google_maps_url", "count": {"$sum": 1}}},
  {"$match": {"count": {"$gt": 1}}}
])
```

**Fixes:**
1. Ensure unique index exists: `db.businesses.getIndexes()`
2. If missing: `python scripts/create_indexes.py`
3. Verify `save_business()` uses `upsert=True`
4. Check `DB_UPSERT_ON_INSERT=true` in `.env`

### Issue: High CAPTCHA Rate (>15%)

**Diagnosis:**
```bash
grep "Detected CAPTCHA" celery.log | wc -l
```

**Fixes:**
1. Add residential proxies to `proxies.txt` (datacenter proxies often blocked)
2. Increase delays:
   ```
   DETAIL_PAGE_DELAY_MS_MIN=3000
   DETAIL_PAGE_DELAY_MS_MAX=6000
   MIN_DELAY_MS=2000
   MAX_DELAY_MS=5000
   ```
3. Rotate user agents more frequently (add more to `user_agents.txt`)
4. Run scrapes during off-peak hours

---

## 📝 Verification Checklist

After completing all steps, confirm:

- [ ] All unit tests pass (30/30)
- [ ] Integration smoke test passes
- [ ] Database has records with phone + website (>50%)
- [ ] Phone numbers are normalized (no special characters)
- [ ] No duplicate records (unique index works)
- [ ] API endpoints return expected data
- [ ] CSV export works and contains complete records
- [ ] Celery tasks complete successfully
- [ ] Logs show successful detail page enrichment
- [ ] No critical errors in logs

---

## 🎉 Next Steps

Once verification is complete:

1. **Scale Up**: Increase `max_results` to 50-100 per scrape
2. **Schedule Scrapes**: Set up Celery Beat for periodic scraping
3. **Add Proxies**: Use proxy service (Bright Data, Oxylabs) for production
4. **Monitor**: Set up Prometheus + Grafana dashboards
5. **Optimize**: Review slow queries with MongoDB Atlas Performance Advisor
6. **Deploy**: Follow production deployment guide in `README.md`

---

## 📞 Support

If verification fails:
1. Check logs with `--loglevel=debug`
2. Review `README.md` troubleshooting section
3. Verify environment variables in `.env`
4. Test MongoDB connection: `mongosh "$MONGO_URI"`
5. Open a GitHub issue with logs and error messages

---

**Happy Scraping! 🚀**
