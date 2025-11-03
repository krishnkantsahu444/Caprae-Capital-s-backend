# API Endpoints Reference (Frontend)

This document lists all frontend-callable REST endpoints in the repository, what they are used for, the inputs they accept (path/query/body), and the output shapes they return.

Note: API route prefixes may include `/api/v1` depending on how `app.main` registers routers. Check `app/main.py`.

---

## 1) Email Enrichment

### POST /api/v1/enrichment/companies/{company_id}/enrich-email
- Purpose: Queue asynchronous email enrichment for a company (SMTP + scraping + WHOIS)
- Input:
  - Path parameter: `company_id` (string)
  - No body required
- Output (200):
```json
{
  "status": "queued",
  "task_id": "<celery-task-id>",
  "message": "Email enrichment queued for company <company_id>"
}
```
- Errors:
  - 404 if company not found
  - 400 if company has no website
  - 500 if queuing fails


### GET /api/v1/enrichment/companies/{company_id}/emails
- Purpose: Retrieve enriched emails for a company
- Input:
  - Path parameter: `company_id` (string)
- Output (200):
```json
[
  {
    "email": "contact@company.com",
    "verified": true,
    "confidence": 90,
    "method": "smtp_verified",
    "pattern": "contact@{domain}"
  },
  {
    "email": "info@company.com",
    "verified": true,
    "confidence": 95,
    "method": "scraped",
    "pattern": "found_on_website"
  }
]
```
- Errors:
  - 404 if company not found or no enriched emails


### GET /api/v1/enrichment/companies/{company_id}/status
- Purpose: Get enrichment status summary for a company
- Input:
  - Path parameter: `company_id` (string)
- Output (200):
```json
{
  "company_id": "<id>",
  "has_emails": true,
  "email_count": 2,
  "emails": [ ... ],
  "enriched_at": "2025-10-12T01:19:24Z",
  "methods_used": ["smtp", "scraping", "whois"]
}
```


### POST /api/v1/enrichment/admin/batch-enrich?limit={n}
- Purpose: Queue batch enrichment for leads missing emails (admin)
- Input:
  - Query parameter: `limit` (int, default 100)
- Output (200):
```json
{ "status": "queued", "task_id": "<celery-id>", "message": "Batch enrichment queued for up to <limit> leads" }
```
- Errors:
  - 400 if limit invalid
  - 500 on queue failure


### GET /api/v1/enrichment/task/{task_id}/status
- Purpose: Check Celery task status and result
- Input:
  - Path parameter: `task_id` (string)
- Output (200):
```json
{
  "task_id": "<task_id>",
  "status": "PENDING|STARTED|SUCCESS|FAILURE|RETRY",
  "result": { ... }  // present if task finished
}
```

---

## 2) Companies / Leads

### GET /api/v1/companies
- Purpose: Search / list businesses
- Input (query params): (all optional)
  - `query` (text)
  - `location` (text)
  - `category` (text)
  - `has_phone` (bool)
  - `has_website` (bool)
  - `has_email` (bool)
  - `sort_by` (e.g., score, rating, created_at)
  - `order` (asc|desc)
  - `limit` (int), `skip` (int)
- Output (200):
```json
{ "total": 123, "results": [ { "_id":"..", "name":"..", "website":"..", "phone":"..", "lead_score":{...}, "completeness_flags":{...} }, ... ] }
```


### GET /api/v1/companies/{id}
- Purpose: Get normalized company details
- Input:
  - Path param `id` (ObjectId string)
- Output (200):
```json
{
  "_id": "...",
  "name": "Acme Corp",
  "website": "https://acme.com",
  "phone": "+1-555-1234",
  "emails": [ ... ],
  "lead_score": { "total_score": 85, "tier": "HOT", "breakdown": {...} },
  "completeness_flags": { "has_phone": true, "has_email": true },
  "email_enriched_at": "2025-10-12T01:19:24Z",
}
```


### GET /api/v1/companies/{id}/score-breakdown
- Purpose: Get the score breakdown for a single company
- Input: path param `id`
- Output:
```json
{ "total_score": 85, "tier": "HOT", "breakdown": { "completeness": 40, "reputation": 25, ... }, "missing_fields": ["hours"], "recommendations": ["Add phone number"] }
```


### GET /api/v1/companies/meta/categories
- Purpose: Get list of categories
- Output: `['Restaurant','Plumber', ...]`

### GET /api/v1/companies/meta/locations
- Purpose: Get list of locations
- Output: `['New York, NY','Miami, FL', ...]`


### GET /api/v1/companies/export/csv?{filters}
- Purpose: Export filtered businesses as CSV
- Input: same filters as search
- Output: CSV file stream (Content-Type: text/csv)

---

## 3) Analytics

### GET /api/v1/analytics/top_leads?category={}&location={}&limit={}
- Purpose: Return top leads by lead_score
- Input: `category`, `location`, `limit`
- Output: list of lead objects sorted by score

### GET /api/v1/analytics/counts
- Purpose: Counts grouped by category+location
- Output: `[ { category, location, count }, ... ]`

### GET /api/v1/analytics/summary
- Purpose: Overall aggregates (avg rating, avg lead score, totals)
- Output: `{ avg_rating: num, avg_lead_score: num, total_leads: num, complete_leads: num }

---

## 4) Lead Scoring (if present)

### GET /api/v1/scoring/companies/{company_id}/score-breakdown
- Purpose: Return score breakdown (similar to companies/{id}/score-breakdown)

### POST /api/v1/scoring/admin/rescore-all
- Purpose: Trigger background rescore job (Celery)
- Output: { status: 'queued', task_id }

---

## 5) Scraping / Crawl

### POST /api/v1/scrape/crawlee
- Purpose: Trigger crawlee scraping job (Google Maps)
- Input: body: { query, location, max_results, headless, proxies }
- Output: { status: 'queued', task_id }

### GET /api/v1/scrape/crawlee/task/{task_id}
- Purpose: Get scrape job status and stats
- Output: { task_id, status, stats: { total_attempted, success, captcha_encounters } }

---

## 6) Admin

### POST /api/v1/admin/deduplicate
- Purpose: Trigger deduplication job
- Input: {threshold, batch_size}
- Output: {status: 'queued', task_id}

### GET /api/v1/admin/duplicate-report
- Purpose: Get last dedupe report
- Output: { merged_count, duplicates_found, report_url }

---

## 7) Misc

### GET /health or GET /api/v1/health
- Purpose: Liveness
- Output: `{ status: 'ok' }`

### GET /version
- Purpose: App version
- Output: `{ version: '1.0.0', commit: '...' }`

---

## Usage Notes for Frontend
- Trigger enrichment via POST, then poll `/enrichment/task/{task_id}/status` until `SUCCESS` and then GET `/companies/{id}/emails`.
- Use `/companies` for search and `/companies/{id}` for details.
- Dashboards: use `/analytics/*` endpoints.

---

If you want, I can now:
- generate example fetch() calls for these endpoints, or
- create an OpenAPI snippet with the request/response schemas.
Which would you like next?

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Rating</th>
            <th>Phone</th>
            <th>Website</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => (
            <tr key={company._id}>
              <td>{company.business_name}</td>
              <td>{company.category}</td>
              <td>{company.rating}</td>
              <td>{company.phone}</td>
              <td>
                {company.website && (
                  <a href={company.website} target="_blank">Visit</a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CompanySearch;
```

### Category Autocomplete

```jsx
function CategoryFilter() {
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetch('http://localhost:9000/companies/meta/categories')
      .then(res => res.json())
      .then(data => setCategories(data.categories));
  }, []);

  return (
    <select>
      <option value="">All Categories</option>
      {categories.map(cat => (
        <option key={cat} value={cat}>{cat}</option>
      ))}
    </select>
  );
}
```

### Export Button

```jsx
function ExportButton({ filters }) {
  const handleExport = () => {
    const params = new URLSearchParams(filters);
    window.open(`http://localhost:9000/companies/export/csv?${params}`, '_blank');
  };

  return <button onClick={handleExport}>Export to CSV</button>;
}
```

---

## 🧪 Testing with cURL

### Complete Test Suite

```bash
# 1. Basic search
curl "http://localhost:9000/companies?query=pizza&limit=5"

# 2. Location filter
curl "http://localhost:9000/companies?location=New%20York&limit=10"

# 3. High-rated only
curl "http://localhost:9000/companies?rating_min=4.5&limit=10"

# 4. Has website
curl "http://localhost:9000/companies?has_website=true&limit=10"

# 5. Sort by rating
curl "http://localhost:9000/companies?sort_by=rating&order=desc&limit=10"

# 6. Pagination
curl "http://localhost:9000/companies?limit=20&offset=40"

# 7. Get single company (replace with real ID)
curl "http://localhost:9000/companies/650f5b2a2f1c7f9d4c8b4567"

# 8. Get categories
curl "http://localhost:9000/companies/meta/categories"

# 9. Get locations
curl "http://localhost:9000/companies/meta/locations"

# 10. Export CSV
curl -o export.csv "http://localhost:9000/companies/export/csv?query=restaurant&limit=100"

# 11. Get stats
curl "http://localhost:9000/companies/stats/summary"
```

---

## 🔧 Performance Tuning

### MongoDB Indexes

Indexes are created automatically on startup. For manual creation:

```bash
python scripts/create_indexes.py
```

**Indexes Created:**
- `google_maps_url` (unique) - Deduplication
- `category` - Filter by category
- `location` - Filter by location
- `rating` - Sort/filter by rating
- `created_at` - Sort by creation date
- `(category, rating)` - Compound index for common queries
- `(location, rating)` - Compound index for location + rating
- `business_name` (text) - Full-text search

### Query Optimization Tips

1. **Use indexes**: Always filter on indexed fields when possible
2. **Limit results**: Don't fetch more than needed (max 200 per page)
3. **Avoid regex on large datasets**: Use exact matches or text indexes
4. **Compound indexes**: Use multiple filters that match compound indexes
5. **Projection**: If you only need specific fields, add projection (future enhancement)

### MongoDB Atlas Auto-Scaling

For production, use MongoDB Atlas M10+ with:
- Auto-scaling enabled
- Read replicas for high traffic
- Performance advisor for slow queries

---

## 🐛 Troubleshooting

### "Motor not initialized"
```bash
# Make sure MongoDB connection string is set
echo $MONGO_URI

# Check if Motor initializes on startup (watch logs)
uvicorn app.main:app --reload --port 9000
```

### Empty results
```bash
# Check database has data
python -c "from app.db_mongo import get_business_count; print(get_business_count())"

# Run a scrape to populate data
curl -X POST http://localhost:9000/scrape/crawlee/async \
  -H "Content-Type: application/json" \
  -d '{"query": "coffee", "location": "Austin", "max_results": 10}'
```

### Slow queries
```bash
# Check indexes exist
python scripts/create_indexes.py

# Use explain in MongoDB shell
mongosh
use crashlens
db.businesses.find({category: "Coffee shop"}).explain("executionStats")
```

### CSV export timeout
- Reduce `limit` parameter (max 20000)
- Add pagination: export in chunks of 1000-5000
- Consider background job for very large exports

---

## 📝 API Response Examples

### Successful List Response
```json
{
  "total": 342,
  "results": [
    {
      "_id": "650f5b2a2f1c7f9d4c8b4567",
      "business_name": "Blue Bottle Coffee",
      "address": "456 Mission St, San Francisco, CA 94105",
      "phone": "(415) 555-0199",
      "rating": 4.6,
      "review_count": 892,
      "category": "Coffee shop",
      "google_maps_url": "https://www.google.com/maps/place/...",
      "website": "https://bluebottlecoffee.com",
      "hours": "Mon-Sun: 7am-7pm",
      "services": ["Dine-in", "Takeout"],
      "location": "San Francisco, CA",
      "created_at": "2024-09-15T14:22:00Z"
    }
  ]
}
```

### Error Response (400)
```json
{
  "detail": "Invalid company ID format"
}
```

### Error Response (404)
```json
{
  "detail": "Company not found"
}
```

### Error Response (500)
```json
{
  "detail": "Database query failed: connection timeout"
}
```

---

## 🚀 Next Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run index creation:**
   ```bash
   python scripts/create_indexes.py
   ```

3. **Start server:**
   ```bash
   uvicorn app.main:app --reload --port 9000
   ```

4. **Test endpoints:**
   ```bash
   curl "http://localhost:9000/companies?limit=5"
   ```

5. **View interactive docs:**
   ```
   http://localhost:9000/docs
   ```

---

## 📚 Additional Resources

- **Swagger UI:** http://localhost:9000/docs
- **ReDoc:** http://localhost:9000/redoc
- **MongoDB Integration Guide:** `README_MONGODB.md`
- **Setup Guide:** `MONGODB_INTEGRATION_SUMMARY.md`

---

**Built with ❤️ using FastAPI, Motor, and MongoDB**
