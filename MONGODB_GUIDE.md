# MongoDB Integration Guide

## Overview

This backend uses **MongoDB** as the primary database for storing Google Maps business leads. MongoDB provides:
- **Atomic upserts** for deduplication
- **Flexible schema** for varied business data
- **Fast indexed queries** for searching and filtering
- **Horizontal scalability** for production deployments

## Architecture

### Dual MongoDB Driver Setup

This project uses **two MongoDB drivers** for different use cases:

1. **pymongo** (sync) - Used by Celery background tasks
   - File: `app/db_mongo.py`
   - Thread-safe, blocking operations
   - Perfect for background scraping tasks

2. **motor** (async) - Used by FastAPI endpoints
   - File: `app/db_motor.py`
   - Non-blocking, high concurrency
   - Perfect for API request handling

Both drivers connect to the same MongoDB database and can coexist safely.

---

## Quick Start

### 1. Install MongoDB

**Option A: Local MongoDB**
```bash
# Windows (with Chocolatey)
choco install mongodb

# Mac
brew install mongodb-community

# Linux (Ubuntu)
sudo apt-get install mongodb

# Start MongoDB
mongod --dbpath ./data/db
```

**Option B: MongoDB Atlas (Cloud)**
1. Sign up at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get your connection string (looks like: `mongodb+srv://user:pass@cluster.mongodb.net/`)

### 2. Configure Environment

Edit `.env` file:
```bash
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/              # Local MongoDB
# OR
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/  # Atlas Cloud

MONGO_DB_NAME=crashlens                           # Database name
MONGO_COLLECTION=businesses                       # Collection name
```

**Security Note:** Never commit your real `.env` file! Use `.env.example` as a template.

### 3. Verify Connection

Run the test script to verify MongoDB is working:
```bash
python tests/test_mongodb.py
```

Expected output:
```
✅ Test 1 PASSED: Upsert and deduplication working correctly
✅ Test 2 PASSED: Record completeness check working correctly
✅ Test 3 PASSED: Bulk insert completed successfully
✅ Test 4 PASSED: Search functionality working correctly
✅ Test 5 PASSED: Pagination working correctly
✅ Test 6 PASSED: Indexes verified

🎉 ALL TESTS PASSED! MongoDB integration is working correctly.
```

---

## Database Schema

### Business Document Structure

```json
{
  "_id": "ObjectId('650f5b2a2f1c7f9d4c8b4567')",
  "name": "Joe's Coffee Shop",
  "google_maps_url": "https://maps.google.com/?cid=12345",
  "phone": "+15125551234",
  "website": "https://joescoffee.com",
  "category": "Coffee Shop",
  "location": "Austin, TX",
  "address": "123 Main St, Austin, TX 78701",
  "rating": 4.5,
  "review_count": 120,
  "hours": {
    "Monday": "8:00 AM - 6:00 PM",
    "Tuesday": "8:00 AM - 6:00 PM",
    "Wednesday": "8:00 AM - 6:00 PM",
    "Thursday": "8:00 AM - 6:00 PM",
    "Friday": "8:00 AM - 8:00 PM",
    "Saturday": "9:00 AM - 8:00 PM",
    "Sunday": "10:00 AM - 5:00 PM"
  },
  "services": ["Dine-in", "Takeout", "Delivery"],
  "description": "Cozy coffee shop with artisan brews...",
  "created_at": "2024-09-24T10:30:00Z"
}
```

### Required Fields
- `google_maps_url` - **Required** for deduplication (unique index)
- `name` - Business name

### Optional Fields
- `phone` - Phone number (normalized, e.g., "+15125551234")
- `website` - Website URL
- `category` - Business category
- `location` - City, state
- `address` - Full address
- `rating` - Rating (0.0 - 5.0)
- `review_count` - Number of reviews
- `hours` - Operating hours
- `services` - Array of services offered
- `description` - Business description

---

## MongoDB Indexes

### Automatically Created Indexes

The system creates the following indexes on startup:

1. **google_maps_url_unique** (Unique) - Deduplication
   ```javascript
   db.businesses.createIndex({"google_maps_url": 1}, {unique: true})
   ```

2. **phone_idx** - Search by phone
   ```javascript
   db.businesses.createIndex({"phone": 1}, {sparse: true})
   ```

3. **website_idx** - Filter by website presence
   ```javascript
   db.businesses.createIndex({"website": 1}, {sparse: true})
   ```

4. **category_idx** - Filter by category
   ```javascript
   db.businesses.createIndex({"category": 1})
   ```

5. **location_idx** - Filter by location
   ```javascript
   db.businesses.createIndex({"location": 1})
   ```

6. **rating_idx** - Sort/filter by rating
   ```javascript
   db.businesses.createIndex({"rating": 1})
   ```

7. **name_idx** - Search by name
   ```javascript
   db.businesses.createIndex({"name": 1})
   ```

8. **category_location_idx** - Compound query optimization
   ```javascript
   db.businesses.createIndex({"category": 1, "location": 1})
   ```

9. **quality_idx** - Filter complete records
   ```javascript
   db.businesses.createIndex({"phone": 1, "website": 1, "rating": 1}, {sparse: true})
   ```

10. **created_at_idx** - Sort by date
    ```javascript
    db.businesses.createIndex({"created_at": 1})
    ```

### Verify Indexes

```bash
# MongoDB Shell
mongo

use crashlens
db.businesses.getIndexes()
```

---

## API Endpoints

### 1. Search Businesses

**Endpoint:** `GET /companies/`

**Query Parameters:**
- `query` - Search in business name or category (case-insensitive)
- `location` - Filter by location/address
- `category` - Filter by category
- `rating_min` - Minimum rating (0-5)
- `rating_max` - Maximum rating (0-5)
- `has_website` - Filter businesses with website (true/false)
- `has_phone` - Filter businesses with phone (true/false)
- `services` - Filter by services (array)
- `sort_by` - Sort field: `rating`, `review_count`, `created_at`, `business_name`
- `order` - Sort order: `asc` or `desc`
- `limit` - Results per page (default: 20, max: 200)
- `offset` - Pagination offset (default: 0)

**Examples:**

```bash
# Search for coffee shops
curl "http://localhost:9000/companies/?query=coffee"

# Filter by location
curl "http://localhost:9000/companies/?location=Austin"

# High-rated businesses with phone numbers
curl "http://localhost:9000/companies/?rating_min=4.5&has_phone=true"

# Paginated results
curl "http://localhost:9000/companies/?limit=50&offset=100"

# Combined filters
curl "http://localhost:9000/companies/?query=restaurant&location=Austin&rating_min=4.0&has_website=true&sort_by=rating&order=desc"
```

**Response:**
```json
{
  "total": 150,
  "results": [
    {
      "_id": "650f5b2a2f1c7f9d4c8b4567",
      "name": "Joe's Coffee Shop",
      "google_maps_url": "https://maps.google.com/?cid=12345",
      "phone": "+15125551234",
      "website": "https://joescoffee.com",
      "category": "Coffee Shop",
      "location": "Austin, TX",
      "rating": 4.5,
      "review_count": 120
    }
  ]
}
```

### 2. Get Single Business

**Endpoint:** `GET /companies/{company_id}`

**Example:**
```bash
curl "http://localhost:9000/companies/650f5b2a2f1c7f9d4c8b4567"
```

### 3. Get Categories

**Endpoint:** `GET /companies/meta/categories`

Get list of all distinct categories in the database.

**Example:**
```bash
curl "http://localhost:9000/companies/meta/categories?limit=100"
```

**Response:**
```json
{
  "categories": ["Coffee Shop", "Bakery", "Auto Repair", "Pizza Restaurant", "IT Services"]
}
```

### 4. Get Locations

**Endpoint:** `GET /companies/meta/locations`

Get list of all distinct locations in the database.

**Example:**
```bash
curl "http://localhost:9000/companies/meta/locations?limit=100"
```

### 5. Export to CSV

**Endpoint:** `GET /companies/export/csv`

Export filtered results to CSV file.

**Example:**
```bash
curl "http://localhost:9000/companies/export/csv?location=Austin&has_phone=true" -o leads.csv
```

---

## Upsert Logic & Deduplication

### How It Works

The system uses **atomic upserts** to prevent duplicate entries:

```python
# In app/db_mongo.py
def save_business(business: Dict) -> bool:
    """
    Save business with atomic upsert.
    
    Key priority:
    1. google_maps_url (if present) - Primary key
    2. phone (if no URL) - Fallback key
    
    Returns:
        True if new record inserted
        False if existing record updated
    """
    # Determine unique key
    if business.get("google_maps_url"):
        unique_key = {"google_maps_url": business["google_maps_url"]}
    elif business.get("phone"):
        unique_key = {"phone": business["phone"]}
    else:
        return False  # Cannot save without unique identifier
    
    # Atomic upsert
    result = collection.update_one(
        unique_key,
        {
            "$set": business,
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )
    
    return result.upserted_id is not None
```

### Benefits

✅ **Atomic** - No race conditions even with concurrent tasks  
✅ **Idempotent** - Running scraper multiple times won't create duplicates  
✅ **Updates** - Re-scraping updates existing records with new data  
✅ **Fast** - Unique index makes lookups O(log n)

### Testing Deduplication

```python
# In tests/test_mongodb.py
business = {
    "name": "Test Business",
    "google_maps_url": "https://maps.google.com/?cid=12345",
    "phone": "+15125551234"
}

# First insert
result1 = upsert_business(business)
print(result1)  # True (new record)

# Duplicate insert
result2 = upsert_business(business)
print(result2)  # False (existing record, not inserted)

# Update existing
business["rating"] = 4.8
result3 = upsert_business(business)
print(result3)  # False (updated existing record)
```

---

## Usage in Code

### From Celery Tasks (Sync)

```python
from app.db_mongo import upsert_business, search_businesses

# Save a business from scraper
business_data = {
    "name": "Joe's Coffee",
    "google_maps_url": "https://maps.google.com/?cid=12345",
    "phone": "+15125551234",
    "website": "https://joescoffee.com",
    "category": "Coffee Shop",
    "location": "Austin, TX",
    "rating": 4.5
}

is_new = upsert_business(business_data)
if is_new:
    print("✅ New business inserted")
else:
    print("🔄 Existing business updated")

# Search businesses
results = search_businesses(
    location="Austin",
    has_phone=True,
    min_rating=4.0,
    limit=50
)
print(f"Found {len(results)} businesses")
```

### From FastAPI Endpoints (Async)

```python
from fastapi import APIRouter
from app.db_motor import get_collection

router = APIRouter()

@router.get("/custom-search")
async def custom_search():
    coll = get_collection()
    
    # Custom MongoDB query
    results = []
    cursor = coll.find({"rating": {"$gte": 4.5}}).limit(10)
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return {"results": results}
```

---

## Performance Tips

### 1. Use Indexes for Queries

Always filter on indexed fields for fast queries:
```python
# ✅ FAST - Uses indexes
search_businesses(category="Coffee Shop", location="Austin")

# ❌ SLOW - No index on description field
collection.find({"description": {"$regex": "coffee"}})
```

### 2. Limit Result Sets

Always use `limit` to avoid loading entire collection:
```python
# ✅ GOOD
search_businesses(location="Austin", limit=100)

# ❌ BAD - Could return millions of records
collection.find({})
```

### 3. Use Projection

Only select fields you need:
```python
# ✅ GOOD - Only get name and phone
collection.find({}, {"name": 1, "phone": 1, "_id": 0})

# ❌ BAD - Returns entire document
collection.find({})
```

### 4. Monitor Slow Queries

Enable MongoDB profiler to find slow queries:
```javascript
// In MongoDB shell
db.setProfilingLevel(1, {slowms: 100})  // Log queries > 100ms
db.system.profile.find().sort({ts: -1}).limit(10)
```

---

## Troubleshooting

### Connection Errors

**Error:** `ConnectionFailure: Failed to connect to MongoDB`

**Solutions:**
1. Check MongoDB is running: `mongod --dbpath ./data/db`
2. Verify `MONGO_URI` in `.env` is correct
3. Check firewall/network settings
4. For MongoDB Atlas, whitelist your IP address

### Duplicate Key Errors

**Error:** `DuplicateKeyError: E11000 duplicate key error`

**Solutions:**
1. This is handled automatically by upsert logic
2. If persistent, check for race conditions
3. Verify unique index exists: `db.businesses.getIndexes()`

### Slow Queries

**Error:** Queries taking >1 second

**Solutions:**
1. Check indexes exist: `db.businesses.getIndexes()`
2. Add indexes for your query fields
3. Use `.explain()` to see query plan
4. Limit result sets with `limit` parameter

### Out of Memory

**Error:** `MemoryError` or system slowdown

**Solutions:**
1. Always use pagination (`limit` and `offset`)
2. Don't load entire collection into memory
3. Use cursors for large result sets
4. Increase MongoDB cache size in config

---

## Production Deployment

### MongoDB Atlas (Recommended for Production)

1. **Create Cluster**
   - Sign up at https://www.mongodb.com/cloud/atlas
   - Create M10+ cluster for production (free tier for testing)

2. **Configure Security**
   - Enable authentication
   - Whitelist application server IPs
   - Use strong password

3. **Connection String**
   ```bash
   MONGO_URI=mongodb+srv://username:password@cluster0.mongodb.net/?retryWrites=true&w=majority
   ```

4. **Enable Monitoring**
   - Atlas has built-in monitoring
   - Set up alerts for high CPU, memory, or disk usage

### Self-Hosted MongoDB

1. **Install MongoDB**
   ```bash
   # Ubuntu
   sudo apt-get install mongodb-org
   
   # Configure
   sudo nano /etc/mongod.conf
   ```

2. **Enable Authentication**
   ```javascript
   // MongoDB shell
   use admin
   db.createUser({
     user: "adminuser",
     pwd: "strongpassword",
     roles: ["root"]
   })
   ```

3. **Configure Replica Set** (for high availability)
   ```yaml
   # /etc/mongod.conf
   replication:
     replSetName: "rs0"
   ```

4. **Backup Strategy**
   ```bash
   # Daily backups
   mongodump --uri="mongodb://localhost:27017/crashlens" --out=/backups/$(date +%Y%m%d)
   ```

---

## Sample MongoDB Queries

### Using MongoDB Shell

```javascript
// Connect
mongo mongodb://localhost:27017/crashlens

// Count all businesses
db.businesses.count()

// Find businesses in Austin
db.businesses.find({"location": /Austin/i}).limit(10)

// High-rated businesses with phone
db.businesses.find({
  "rating": {$gte: 4.5},
  "phone": {$exists: true, $ne: ""}
}).sort({"rating": -1})

// Find by category
db.businesses.find({"category": "Coffee Shop"})

// Get distinct categories
db.businesses.distinct("category")

// Count by category
db.businesses.aggregate([
  {$group: {_id: "$category", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

// Find recent businesses
db.businesses.find().sort({"created_at": -1}).limit(10)

// Delete test data
db.businesses.deleteMany({"name": /Test/i})
```

---

## Environment Variables Reference

```bash
# MongoDB Connection
MONGO_URI=mongodb://localhost:27017/              # MongoDB connection string
MONGO_DB_NAME=crashlens                           # Database name
MONGO_COLLECTION=businesses                       # Collection name

# Database Behavior
DB_UPSERT_ON_INSERT=true                         # Enable atomic upserts

# Legacy SQLite (optional)
DB_PATH=leads.db                                  # SQLite path (deprecated)
```

---

## Migration from SQLite

If you're migrating from SQLite to MongoDB:

### 1. Export SQLite Data

```python
import sqlite3
import json

conn = sqlite3.connect('leads.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM businesses")
rows = cursor.fetchall()

# Convert to list of dicts
columns = [desc[0] for desc in cursor.description]
businesses = [dict(zip(columns, row)) for row in rows]

# Save to JSON
with open('export.json', 'w') as f:
    json.dump(businesses, f, indent=2)

conn.close()
```

### 2. Import to MongoDB

```python
from app.db_mongo import upsert_business
import json

# Load exported data
with open('export.json', 'r') as f:
    businesses = json.load(f)

# Import to MongoDB
for business in businesses:
    upsert_business(business)
    print(f"Imported: {business.get('name')}")

print(f"✅ Migrated {len(businesses)} businesses to MongoDB")
```

---

## Additional Resources

- [MongoDB Documentation](https://docs.mongodb.com/)
- [PyMongo Tutorial](https://pymongo.readthedocs.io/en/stable/tutorial.html)
- [Motor (Async) Docs](https://motor.readthedocs.io/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [FastAPI + MongoDB Guide](https://www.mongodb.com/developer/languages/python/python-quickstart-fastapi/)

---

## Support

For issues or questions:
1. Check this documentation first
2. Run test script: `python tests/test_mongodb.py`
3. Check logs in `logs/` directory
4. Review MongoDB logs: `tail -f /var/log/mongodb/mongod.log`
5. Open an issue on GitHub

