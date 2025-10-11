"""MongoDB database layer for lead persistence with deduplication."""
import logging
from typing import Dict, List, Optional
from pymongo import MongoClient, ASCENDING, errors
from pymongo.collection import Collection
from pymongo.database import Database
from utils.config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

logger = logging.getLogger(__name__)

# Global MongoDB client and collection
_client: Optional[MongoClient] = None
_db: Optional[Database] = None
_collection: Optional[Collection] = None


def get_client() -> MongoClient:
    """Get or create MongoDB client singleton."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
            )
            # Test connection
            _client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {MONGO_URI}")
        except errors.ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    return _client


def get_database() -> Database:
    """Get MongoDB database instance."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[MONGO_DB_NAME]
        logger.info(f"Using database: {MONGO_DB_NAME}")
    return _db


def get_collection() -> Collection:
    """Get MongoDB collection instance."""
    global _collection
    if _collection is None:
        db = get_database()
        _collection = db[MONGO_COLLECTION]
        logger.info(f"Using collection: {MONGO_COLLECTION}")
        # Ensure indexes are created
        create_indexes()
    return _collection


def create_indexes():
    """Create MongoDB indexes for performance and deduplication."""
    collection = get_collection()
    
    try:
        # Unique index on google_maps_url for deduplication
        collection.create_index(
            [("google_maps_url", ASCENDING)],
            unique=True,
            name="google_maps_url_unique"
        )
        logger.info("Created unique index on google_maps_url")
        
        # Index on category for filtering
        collection.create_index(
            [("category", ASCENDING)],
            name="category_idx"
        )
        logger.info("Created index on category")
        
        # Index on rating for sorting/filtering
        collection.create_index(
            [("rating", ASCENDING)],
            name="rating_idx"
        )
        logger.info("Created index on rating")
        
        # Compound index on location fields (if added later)
        # collection.create_index([("city", ASCENDING), ("state", ASCENDING)])
        
        # Index on created_at for time-based queries
        collection.create_index(
            [("created_at", ASCENDING)],
            name="created_at_idx"
        )
        logger.info("Created index on created_at")
        
    except errors.PyMongoError as e:
        logger.warning(f"Error creating indexes (may already exist): {e}")


def save_business(business: Dict) -> bool:
    """
    Save a business to MongoDB with deduplication.
    
    Uses upsert to handle duplicates gracefully - updates existing or inserts new.
    
    Args:
        business: Dictionary with business data. Must include 'google_maps_url' for deduplication.
    
    Returns:
        True if inserted (new), False if updated (duplicate).
    """
    collection = get_collection()
    
    if not business.get("google_maps_url"):
        logger.warning("Business missing google_maps_url, cannot save")
        return False
    
    try:
        # Add timestamp if not present
        if "created_at" not in business:
            from datetime import datetime
            business["created_at"] = datetime.utcnow()
        
        # Use update_one with upsert to handle duplicates
        result = collection.update_one(
            {"google_maps_url": business["google_maps_url"]},
            {"$set": business},
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"Inserted new business: {business.get('name')}")
            return True
        else:
            logger.info(f"Updated existing business: {business.get('name')}")
            return False
            
    except errors.DuplicateKeyError:
        logger.info(f"Duplicate business (ignored): {business.get('name')}")
        return False
    except errors.PyMongoError as e:
        logger.error(f"Error saving business: {e}")
        return False


def get_all_businesses(limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Retrieve businesses from MongoDB with pagination.
    
    Args:
        limit: Maximum number of results to return.
        offset: Number of results to skip.
    
    Returns:
        List of business dictionaries.
    """
    collection = get_collection()
    
    try:
        cursor = collection.find().sort("created_at", -1).skip(offset).limit(limit)
        businesses = list(cursor)
        
        # Convert ObjectId to string for JSON serialization
        for business in businesses:
            if "_id" in business:
                business["_id"] = str(business["_id"])
        
        logger.info(f"Retrieved {len(businesses)} businesses (offset={offset}, limit={limit})")
        return businesses
        
    except errors.PyMongoError as e:
        logger.error(f"Error retrieving businesses: {e}")
        return []


def get_business_count() -> int:
    """
    Get the total number of businesses in MongoDB.
    
    Returns:
        Total count of businesses.
    """
    collection = get_collection()
    
    try:
        count = collection.count_documents({})
        logger.info(f"Total businesses in database: {count}")
        return count
    except errors.PyMongoError as e:
        logger.error(f"Error counting businesses: {e}")
        return 0


def business_exists(google_maps_url: str) -> bool:
    """
    Check if a business with the given URL already exists.
    
    Args:
        google_maps_url: The Google Maps URL to check.
    
    Returns:
        True if exists, False otherwise.
    """
    collection = get_collection()
    
    try:
        exists = collection.find_one({"google_maps_url": google_maps_url}) is not None
        return exists
    except errors.PyMongoError as e:
        logger.error(f"Error checking business existence: {e}")
        return False


def get_businesses_by_category(category: str, limit: int = 100) -> List[Dict]:
    """
    Get businesses filtered by category.
    
    Args:
        category: Category to filter by.
        limit: Maximum number of results.
    
    Returns:
        List of business dictionaries.
    """
    collection = get_collection()
    
    try:
        cursor = collection.find({"category": category}).limit(limit)
        businesses = list(cursor)
        
        for business in businesses:
            if "_id" in business:
                business["_id"] = str(business["_id"])
        
        return businesses
    except errors.PyMongoError as e:
        logger.error(f"Error getting businesses by category: {e}")
        return []


def get_businesses_by_rating(min_rating: float, limit: int = 100) -> List[Dict]:
    """
    Get businesses with rating >= min_rating.
    
    Args:
        min_rating: Minimum rating threshold.
        limit: Maximum number of results.
    
    Returns:
        List of business dictionaries.
    """
    collection = get_collection()
    
    try:
        cursor = collection.find({"rating": {"$gte": min_rating}}).sort("rating", -1).limit(limit)
        businesses = list(cursor)
        
        for business in businesses:
            if "_id" in business:
                business["_id"] = str(business["_id"])
        
        return businesses
    except errors.PyMongoError as e:
        logger.error(f"Error getting businesses by rating: {e}")
        return []


def close_connection():
    """Close MongoDB connection (call on shutdown)."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


# Initialize connection and indexes on module import
try:
    create_indexes()
except Exception as e:
    logger.warning(f"Could not initialize MongoDB on import: {e}")
    logger.warning("MongoDB will be initialized on first use")
