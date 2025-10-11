# Company Search API Endpoints

Complete documentation for the company/business search API built with FastAPI and MongoDB (Motor).

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install motor pandas aiofiles

# Start FastAPI server
uvicorn app.main:app --reload --port 9000
```

### Base URL
```
http://localhost:9000
```

---

## 📋 Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies` | GET | List/search companies with filters & pagination |
| `/companies/{id}` | GET | Get single company by ID |
| `/companies/meta/categories` | GET | Get distinct categories (autocomplete) |
| `/companies/meta/locations` | GET | Get distinct locations (autocomplete) |
| `/companies/export/csv` | GET | Export companies to CSV |
| `/companies/stats/summary` | GET | Get database statistics |

---

## 📖 Detailed API Reference

### 1. List/Search Companies

**Endpoint:** `GET /companies`

**Description:** Advanced company search with filtering, sorting, and pagination.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | - | Search in business name or category |
| `location` | string | - | Filter by location/address (regex) |
| `category` | string | - | Filter by category (regex) |
| `rating_min` | float | - | Minimum rating (0-5) |
| `rating_max` | float | - | Maximum rating (0-5) |
| `has_website` | boolean | - | Filter businesses with/without website |
| `has_phone` | boolean | - | Filter businesses with/without phone |
| `services` | array[string] | - | Filter by services (e.g., Dine-in, Delivery) |
| `sort_by` | string | created_at | Sort field (rating, review_count, created_at, business_name) |
| `order` | string | desc | Sort order (asc or desc) |
| `limit` | integer | 20 | Results per page (1-200) |
| `offset` | integer | 0 | Pagination offset |

**Response Schema:**
```json
{
  "total": 1234,
  "results": [
    {
      "_id": "650f5b2a2f1c7f9d4c8b4567",
      "business_name": "Artisan Coffee Roasters",
      "address": "123 Main St, Austin, TX 78701",
      "phone": "(512) 555-0123",
      "rating": 4.7,
      "review_count": 342,
      "category": "Coffee shop",
      "google_maps_url": "https://www.google.com/maps/place/...",
      "website": "https://artisancoffee.com",
      "hours": "Mon-Fri: 7am-8pm",
      "services": ["Dine-in", "Takeout", "Delivery"],
      "location": "Austin, TX",
      "created_at": "2024-10-01T10:30:00Z"
    }
  ]
}
```

**Example Requests:**

```bash
# Search for coffee shops
curl "http://localhost:9000/companies?query=coffee&limit=10"

# Filter by location
curl "http://localhost:9000/companies?location=Austin&limit=20"

# High-rated businesses with website
curl "http://localhost:9000/companies?rating_min=4.5&has_website=true"

# Combination: coffee shops in Austin, sorted by rating
curl "http://localhost:9000/companies?query=coffee&location=Austin&sort_by=rating&order=desc"

# Pagination (page 3, 50 per page)
curl "http://localhost:9000/companies?limit=50&offset=100"

# Filter by multiple services
curl "http://localhost:9000/companies?services=Dine-in&services=Delivery"
```

**Status Codes:**
- `200` - Success
- `400` - Invalid parameters
- `500` - Server/database error

---

### 2. Get Single Company

**Endpoint:** `GET /companies/{company_id}`

**Description:** Retrieve full details of a single company by MongoDB ObjectId.

**Path Parameters:**
- `company_id` (string, required) - MongoDB ObjectId (24 hex characters)

**Example Request:**
```bash
curl "http://localhost:9000/companies/650f5b2a2f1c7f9d4c8b4567"
```

**Response Schema:**
```json
{
  "_id": "650f5b2a2f1c7f9d4c8b4567",
  "business_name": "Artisan Coffee Roasters",
  "address": "123 Main St, Austin, TX 78701",
  "phone": "(512) 555-0123",
  "rating": 4.7,
  "review_count": 342,
  "category": "Coffee shop",
  "google_maps_url": "https://www.google.com/maps/place/...",
  "website": "https://artisancoffee.com",
  "hours": "Mon-Fri: 7am-8pm, Sat-Sun: 8am-9pm",
  "services": ["Dine-in", "Takeout", "Delivery"],
  "location": "Austin, TX",
  "created_at": "2024-10-01T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid company ID format
- `404` - Company not found
- `500` - Server error

---

### 3. Get Categories (Autocomplete)

**Endpoint:** `GET /companies/meta/categories`

**Description:** Get list of distinct categories for dropdown/autocomplete UI.

**Query Parameters:**
- `limit` (integer, default: 100) - Max categories to return (1-500)

**Example Request:**
```bash
curl "http://localhost:9000/companies/meta/categories?limit=50"
```

**Response Schema:**
```json
{
  "categories": [
    "Coffee shop",
    "Restaurant",
    "Pizza restaurant",
    "Italian restaurant",
    "Mexican restaurant",
    "Bar & grill"
  ]
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

### 4. Get Locations (Autocomplete)

**Endpoint:** `GET /companies/meta/locations`

**Description:** Get list of distinct locations for dropdown/autocomplete UI.

**Query Parameters:**
- `limit` (integer, default: 100) - Max locations to return (1-500)

**Example Request:**
```bash
curl "http://localhost:9000/companies/meta/locations?limit=50"
```

**Response Schema:**
```json
{
  "locations": [
    "Austin, TX",
    "New York, NY",
    "San Francisco, CA",
    "Chicago, IL"
  ]
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

### 5. Export to CSV

**Endpoint:** `GET /companies/export/csv`

**Description:** Export companies to CSV file with same filtering as list endpoint. Streams results for memory efficiency.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | - | Search in business name or category |
| `location` | string | - | Filter by location |
| `category` | string | - | Filter by category |
| `rating_min` | float | - | Minimum rating (0-5) |
| `has_website` | boolean | - | Filter businesses with website |
| `limit` | integer | 1000 | Max records to export (1-20000) |

**Example Requests:**

```bash
# Export all coffee shops
curl -o coffee_shops.csv "http://localhost:9000/companies/export/csv?query=coffee&limit=500"

# Export high-rated Austin businesses
curl -o austin_top_rated.csv "http://localhost:9000/companies/export/csv?location=Austin&rating_min=4.5"

# Export businesses with websites
curl -o with_websites.csv "http://localhost:9000/companies/export/csv?has_website=true&limit=5000"
```

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename=companies_export_<query>.csv`
- Streaming response (no memory buffer)

**CSV Format:**
```csv
_id,business_name,address,phone,rating,review_count,category,google_maps_url,website,hours,services,location,created_at
"650f5b2a...",Artisan Coffee,"123 Main St","(512) 555-0123",4.7,342,"Coffee shop","https://...","https://...","Mon-Fri: 7am-8pm","Dine-in|Takeout|Delivery","Austin, TX","2024-10-01T10:30:00Z"
```

**Notes:**
- Lists (e.g., services) are joined with `|` separator
- Quotes and commas are properly escaped
- Large exports may take time (use reasonable limits)

**Status Codes:**
- `200` - Success (file download starts)
- `500` - Export failed

---

### 6. Database Statistics

**Endpoint:** `GET /companies/stats/summary`

**Description:** Get aggregate statistics about the database.

**Example Request:**
```bash
curl "http://localhost:9000/companies/stats/summary"
```

**Response Schema:**
```json
{
  "total_companies": 15234,
  "with_website": 8945,
  "with_phone": 12456,
  "website_percentage": 58.73,
  "phone_percentage": 81.77,
  "avg_rating": 4.23,
  "max_rating": 5.0,
  "min_rating": 1.5,
  "total_categories": 87,
  "total_locations": 342
}
```

**Status Codes:**
- `200` - Success
- `500` - Server error

---

## 🔐 Security & Rate Limiting

### Recommended Production Setup

1. **Rate Limiting** (use nginx or FastAPI middleware):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/")
@limiter.limit("100/minute")
async def list_companies(...):
    ...
```

2. **CORS** (restrict to your frontend domain):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

3. **API Authentication** (for export endpoint):
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@router.get("/export/csv")
async def export_csv(api_key: str = Depends(api_key_header)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(401, "Invalid API key")
    ...
```

---

## 🎨 Frontend Integration Examples

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function CompanySearch() {
  const [companies, setCompanies] = useState([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const searchCompanies = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        query: query,
        limit: 20,
        offset: 0,
        sort_by: 'rating',
        order: 'desc'
      });
      
      const response = await fetch(`http://localhost:9000/companies?${params}`);
      const data = await response.json();
      
      setCompanies(data.results);
      setTotal(data.total);
    } catch (error) {
      console.error('Search failed:', error);
    }
    setLoading(false);
  };

  return (
    <div>
      <input 
        type="text" 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search companies..."
      />
      <button onClick={searchCompanies}>Search</button>
      
      {loading && <p>Loading...</p>}
      
      <p>Found {total} companies</p>
      
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
