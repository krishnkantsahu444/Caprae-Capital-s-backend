# MongoDB Quick Reference

**📖 For comprehensive MongoDB documentation, see [MONGODB_GUIDE.md](MONGODB_GUIDE.md)**

## Database Configuration

This backend uses **MongoDB** for storing business leads. Configuration in `.env`:

```bash
# MongoDB Settings
MONGO_URI=mongodb://localhost:27017/              # Or mongodb+srv://... for Atlas
MONGO_DB_NAME=crashlens                           # Database name
MONGO_COLLECTION=businesses                       # Collection name
```

## Quick Setup

### Local MongoDB
```bash
# Install and start MongoDB
mongod --dbpath ./data/db
```

### MongoDB Atlas (Cloud)
1. Create free cluster at https://www.mongodb.com/cloud/atlas
2. Get connection string
3. Update `MONGO_URI` in `.env`

## Test MongoDB Connection

```bash
python tests/test_mongodb.py
```

## API Search Examples

```bash
# Search for coffee shops in Austin
curl "http://localhost:9000/companies/?query=coffee&location=Austin"

# High-rated businesses with phone numbers
curl "http://localhost:9000/companies/?rating_min=4.5&has_phone=true"

# Export to CSV
curl "http://localhost:9000/companies/export/csv?location=Austin" -o leads.csv
```

## Key Features

✅ **Atomic Upserts** - No duplicate records  
✅ **10+ Indexes** - Fast queries on all fields  
✅ **Advanced Search** - Filter by name, location, category, rating, phone, website  
✅ **Pagination** - Handle large result sets efficiently  
✅ **Dual Drivers** - pymongo (Celery) + motor (FastAPI)  

## Common MongoDB Commands

```javascript
// MongoDB shell
mongo mongodb://localhost:27017/crashlens

// Count businesses
db.businesses.count()

// Find by category
db.businesses.find({"category": "Coffee Shop"})

// High-rated businesses
db.businesses.find({"rating": {$gte: 4.5}}).sort({"rating": -1})

// Get distinct categories
db.businesses.distinct("category")
```

## See Also

- **[MONGODB_GUIDE.md](MONGODB_GUIDE.md)** - Complete MongoDB documentation
- **[tests/test_mongodb.py](tests/test_mongodb.py)** - Test script with examples
- **[app/db_mongo.py](app/db_mongo.py)** - MongoDB implementation (sync)
- **[app/db_motor.py](app/db_motor.py)** - MongoDB implementation (async)
