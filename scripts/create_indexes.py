# scripts/create_indexes.py
"""
One-time script to create MongoDB indexes.
Run this after setting up MongoDB for the first time.

Usage:
    python scripts/create_indexes.py
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

def create_indexes():
    """Create all necessary indexes for the businesses collection"""
    print(f"Connecting to MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    coll = db[MONGO_COLLECTION]
    
    print(f"\nUsing database: {MONGO_DB_NAME}")
    print(f"Using collection: {MONGO_COLLECTION}")
    print("\nCreating indexes...")
    
    # Unique index on google_maps_url for deduplication
    print("1. Creating UNIQUE index on 'google_maps_url'...")
    coll.create_index([("google_maps_url", ASCENDING)], unique=True)
    print("   ✅ Created")
    
    # Standard indexes for filtering
    print("2. Creating index on 'category'...")
    coll.create_index([("category", ASCENDING)])
    print("   ✅ Created")
    
    print("3. Creating index on 'location'...")
    coll.create_index([("location", ASCENDING)])
    print("   ✅ Created")
    
    print("4. Creating index on 'rating'...")
    coll.create_index([("rating", DESCENDING)])
    print("   ✅ Created")
    
    print("5. Creating index on 'created_at'...")
    coll.create_index([("created_at", DESCENDING)])
    print("   ✅ Created")
    
    # Compound indexes for common query patterns
    print("6. Creating compound index on 'category' + 'rating'...")
    coll.create_index([("category", ASCENDING), ("rating", DESCENDING)])
    print("   ✅ Created")
    
    print("7. Creating compound index on 'location' + 'rating'...")
    coll.create_index([("location", ASCENDING), ("rating", DESCENDING)])
    print("   ✅ Created")
    
    # Text index for full-text search (optional)
    print("8. Creating text index on 'business_name' for full-text search...")
    try:
        coll.create_index([("business_name", "text")])
        print("   ✅ Created")
    except Exception as e:
        print(f"   ⚠️ Text index may already exist: {e}")
    
    # List all indexes
    print("\n" + "="*60)
    print("All indexes created successfully!")
    print("="*60)
    
    print("\nCurrent indexes on collection:")
    for idx in coll.list_indexes():
        print(f"  - {idx['name']}: {idx.get('key', {})}")
    
    # Show collection stats
    print("\n" + "="*60)
    print("Collection Statistics:")
    print("="*60)
    
    total_docs = coll.count_documents({})
    print(f"Total documents: {total_docs}")
    
    if total_docs > 0:
        # Count with website
        with_website = coll.count_documents({"website": {"$exists": True, "$ne": None, "$ne": ""}})
        print(f"Documents with website: {with_website} ({round(with_website/total_docs*100, 2)}%)")
        
        # Count with phone
        with_phone = coll.count_documents({"phone": {"$exists": True, "$ne": None, "$ne": ""}})
        print(f"Documents with phone: {with_phone} ({round(with_phone/total_docs*100, 2)}%)")
        
        # Categories
        categories = coll.distinct("category")
        print(f"Unique categories: {len([c for c in categories if c])}")
        
        # Locations
        locations = coll.distinct("location")
        print(f"Unique locations: {len([loc for loc in locations if loc])}")
    
    client.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        create_indexes()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. MongoDB is running")
        print("2. MONGO_URI is set correctly in .env")
        print("3. You have network access to MongoDB")
        sys.exit(1)
