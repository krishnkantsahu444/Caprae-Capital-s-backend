"""MongoDB database layer for lead persistence with deduplication."""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, errors
from pymongo.collection import Collection
from pymongo.database import Database
from utils.config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION, DB_UPSERT_ON_INSERT

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
        
        # Non-unique index on phone for searching by phone
        collection.create_index(
            [("phone", ASCENDING)],
            name="phone_idx",
            sparse=True  # Only index documents that have a phone field
        )
        logger.info("Created index on phone")
        
        # Index on website for filtering businesses with websites
        collection.create_index(
            [("website", ASCENDING)],
            name="website_idx",
            sparse=True  # Only index documents that have a website field
        )
        logger.info("Created index on website")
        
        # Index on category for filtering
        collection.create_index(
            [("category", ASCENDING)],
            name="category_idx"
        )
        logger.info("Created index on category")
        
        # Index on location for filtering/searching by location
        collection.create_index(
            [("location", ASCENDING)],
            name="location_idx"
        )
        logger.info("Created index on location")
        
        # Index on rating for sorting/filtering
        collection.create_index(
            [("rating", ASCENDING)],
            name="rating_idx"
        )
        logger.info("Created index on rating")
        
        # Index on name for text searching (case-insensitive)
        collection.create_index(
            [("name", ASCENDING)],
            name="name_idx"
        )
        logger.info("Created index on name")
        
        # Compound index for common query patterns: category + location
        collection.create_index(
            [("category", ASCENDING), ("location", ASCENDING)],
            name="category_location_idx"
        )
        logger.info("Created compound index on category + location")
        
        # Compound index for quality filtering: has phone + has website + rating
        collection.create_index(
            [("phone", ASCENDING), ("website", ASCENDING), ("rating", ASCENDING)],
            name="quality_idx",
            sparse=True
        )
        logger.info("Created compound index for quality filtering")
        
        # Index on created_at for time-based queries
        collection.create_index(
            [("created_at", ASCENDING)],
            name="created_at_idx"
        )
        logger.info("Created index on created_at")
        
        # NEW INDEXES FOR FEATURE F: Data Quality & Search Optimization
        
        # Index on lead_score.total_score for sorting by score
        collection.create_index(
            [("lead_score.total_score", ASCENDING)],
            name="lead_score_idx",
            sparse=True
        )
        logger.info("Created index on lead_score.total_score")
        
        # Index on lead_score.tier for filtering by tier (HOT/WARM/COLD/LOW)
        collection.create_index(
            [("lead_score.tier", ASCENDING)],
            name="lead_tier_idx",
            sparse=True
        )
        logger.info("Created index on lead_score.tier")
        
        # Compound index for analytics: category + location + lead score
        collection.create_index(
            [("category", ASCENDING), ("location", ASCENDING), ("lead_score.total_score", ASCENDING)],
            name="category_location_score_idx"
        )
        logger.info("Created compound index on category + location + lead_score")
        
        # Index on completeness_flags.has_phone for filtering complete leads
        collection.create_index(
            [("completeness_flags.has_phone", ASCENDING)],
            name="has_phone_flag_idx",
            sparse=True
        )
        logger.info("Created index on completeness_flags.has_phone")
        
        # Index on completeness_flags.has_email for enrichment tracking
        collection.create_index(
            [("completeness_flags.has_email", ASCENDING)],
            name="has_email_flag_idx",
            sparse=True
        )
        logger.info("Created index on completeness_flags.has_email")
        
    except errors.PyMongoError as e:
        logger.warning(f"Error creating indexes (may already exist): {e}")


def is_record_complete(business: Dict) -> bool:
    """
    Check if a business record has complete data (phone and website).
    
    Args:
        business: Dictionary with business data.
    
    Returns:
        True if both phone and website are present and non-empty, False otherwise.
    """
    phone = business.get("phone")
    website = business.get("website")
    
    # Check phone is present and looks valid (at least 6 characters)
    has_valid_phone = bool(phone and isinstance(phone, str) and len(phone) >= 6)
    
    # Check website is present and looks valid (starts with http)
    has_valid_website = bool(website and isinstance(website, str) and website.startswith("http"))
    
    return has_valid_phone and has_valid_website


def save_business(business: Dict) -> bool:
    """
    Save a business to MongoDB with atomic upsert for deduplication.
    
    Uses update_one with upsert=True to atomically handle duplicates.
    Key priority: google_maps_url > phone (if no URL).
    Sets created_at only on insert, always updates scraped fields.
    
    Args:
        business: Dictionary with business data.
    
    Returns:
        True if inserted (new), False if updated (duplicate) or error.
    """
    collection = get_collection()
    
    # Determine unique key for upsert
    if business.get("google_maps_url"):
        unique_key = {"google_maps_url": business["google_maps_url"]}
        key_desc = f"google_maps_url={business['google_maps_url']}"
    elif business.get("phone"):
        unique_key = {"phone": business["phone"]}
        key_desc = f"phone={business['phone']}"
    else:
        logger.warning(f"Business missing both google_maps_url and phone, cannot save: {business.get('name')}")
        return False
    
    try:
        # Prepare update operation
        now = datetime.utcnow()
        
        # Use $set for all fields (will update existing or set on insert)
        # Use $setOnInsert for created_at (only set on first insert)
        update_op = {
            "$set": business,
            "$setOnInsert": {"created_at": now}
        }
        
        # Execute atomic upsert
        result = collection.update_one(
            unique_key,
            update_op,
            upsert=True if DB_UPSERT_ON_INSERT else False
        )
        
        if result.upserted_id:
            logger.info(f"✅ Inserted new business: {business.get('name')} | {key_desc} | _id={result.upserted_id}")
            return True
        elif result.modified_count > 0:
            logger.info(f"🔄 Updated existing business: {business.get('name')} | {key_desc}")
            return False
        else:
            logger.debug(f"ℹ️  No changes for business: {business.get('name')} | {key_desc}")
            return False
            
    except errors.DuplicateKeyError:
        logger.info(f"⚠️  Duplicate business (race condition): {business.get('name')} | {key_desc}")
        return False
    except errors.PyMongoError as e:
        logger.error(f"❌ Error saving business: {business.get('name')} | {key_desc} | Error: {e}")
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


def search_businesses(
    query: Optional[str] = None,
    location: Optional[str] = None,
    category: Optional[str] = None,
    has_phone: Optional[bool] = None,
    has_website: Optional[bool] = None,
    min_rating: Optional[float] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    Advanced search for businesses with multiple filters.
    
    Args:
        query: Search term for business name (case-insensitive partial match).
        location: Filter by location (case-insensitive partial match).
        category: Filter by category (case-insensitive partial match).
        has_phone: Filter businesses with phone numbers if True.
        has_website: Filter businesses with websites if True.
        min_rating: Minimum rating threshold.
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
    
    Returns:
        List of business dictionaries matching the filters.
    """
    collection = get_collection()
    
    # Build query filter
    filters = {}
    
    if query:
        # Case-insensitive partial match on name
        filters["name"] = {"$regex": query, "$options": "i"}
    
    if location:
        # Case-insensitive partial match on location
        filters["location"] = {"$regex": location, "$options": "i"}
    
    if category:
        # Case-insensitive partial match on category
        filters["category"] = {"$regex": category, "$options": "i"}
    
    if has_phone is True:
        # Filter for businesses with non-empty phone
        filters["phone"] = {"$exists": True, "$ne": "", "$ne": None}
    
    if has_website is True:
        # Filter for businesses with non-empty website
        filters["website"] = {"$exists": True, "$ne": "", "$ne": None}
    
    if min_rating is not None:
        # Filter by minimum rating
        filters["rating"] = {"$gte": min_rating}
    
    try:
        # Execute query with pagination
        cursor = collection.find(filters).sort("rating", -1).skip(offset).limit(limit)
        businesses = list(cursor)
        
        # Convert ObjectId to string for JSON serialization
        for business in businesses:
            if "_id" in business:
                business["_id"] = str(business["_id"])
        
        logger.info(f"Search returned {len(businesses)} businesses (filters={filters}, offset={offset}, limit={limit})")
        return businesses
        
    except errors.PyMongoError as e:
        logger.error(f"Error searching businesses: {e}")
        return []


def get_search_count(
    query: Optional[str] = None,
    location: Optional[str] = None,
    category: Optional[str] = None,
    has_phone: Optional[bool] = None,
    has_website: Optional[bool] = None,
    min_rating: Optional[float] = None
) -> int:
    """
    Get count of businesses matching search filters.
    
    Args:
        Same as search_businesses (without limit/offset).
    
    Returns:
        Total count of matching businesses.
    """
    collection = get_collection()
    
    # Build query filter (same as search_businesses)
    filters = {}
    
    if query:
        filters["name"] = {"$regex": query, "$options": "i"}
    
    if location:
        filters["location"] = {"$regex": location, "$options": "i"}
    
    if category:
        filters["category"] = {"$regex": category, "$options": "i"}
    
    if has_phone is True:
        filters["phone"] = {"$exists": True, "$ne": "", "$ne": None}
    
    if has_website is True:
        filters["website"] = {"$exists": True, "$ne": "", "$ne": None}
    
    if min_rating is not None:
        filters["rating"] = {"$gte": min_rating}
    
    try:
        count = collection.count_documents(filters)
        logger.info(f"Search count: {count} businesses (filters={filters})")
        return count
    except errors.PyMongoError as e:
        logger.error(f"Error counting search results: {e}")
        return 0


def upsert_business(business_data: Dict) -> bool:
    """
    Upsert a business record with comprehensive deduplication logic.
    
    This is an alias for save_business() to match the naming convention
    requested in the requirements.
    
    Args:
        business_data: Dictionary with business data.
    
    Returns:
        True if inserted (new), False if updated (duplicate) or error.
    """
    return save_business(business_data)


# Initialize connection and indexes on module import
try:
    create_indexes()
except Exception as e:
    logger.warning(f"Could not initialize MongoDB on import: {e}")
    logger.warning("MongoDB will be initialized on first use")


# NEW FUNCTIONS FOR FEATURE F: Data Quality & Search Optimization

def update_business_score(business_id, score_data: Dict) -> bool:
    """
    Update business with lead score data.
    
    Args:
        business_id: ObjectId or string ID of business
        score_data: Dict with lead scoring information
        
    Returns:
        True if updated successfully, False otherwise
    """
    collection = get_collection()
    
    try:
        from bson import ObjectId
        
        # Convert string to ObjectId if needed
        if isinstance(business_id, str):
            business_id = ObjectId(business_id)
        
        result = collection.update_one(
            {"_id": business_id},
            {"$set": {
                "lead_score": score_data,
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            logger.debug(f"Updated lead score for business {business_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating business score: {e}")
        return False


def update_business_emails(business_id, emails: List[Dict]) -> bool:
    """
    Update business with enriched email data.
    
    Args:
        business_id: ObjectId or string ID of business
        emails: List of email dictionaries from enrichment
        
    Returns:
        True if updated successfully, False otherwise
    """
    collection = get_collection()
    
    try:
        from bson import ObjectId
        
        # Convert string to ObjectId if needed
        if isinstance(business_id, str):
            business_id = ObjectId(business_id)
        
        # Extract primary email
        primary_email = emails[0]['email'] if emails else None
        
        result = collection.update_one(
            {"_id": business_id},
            {"$set": {
                "email": primary_email,
                "emails": emails,
                "email_enriched_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated emails for business {business_id}: {len(emails)} emails")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating business emails: {e}")
        return False


def update_completeness_flags(business_id) -> bool:
    """
    Update completeness flags for a business based on current data.
    
    Args:
        business_id: ObjectId or string ID of business
        
    Returns:
        True if updated successfully, False otherwise
    """
    collection = get_collection()
    
    try:
        from bson import ObjectId
        
        # Convert string to ObjectId if needed
        if isinstance(business_id, str):
            business_id = ObjectId(business_id)
        
        # Get business
        business = collection.find_one({"_id": business_id})
        if not business:
            return False
        
        # Calculate flags
        flags = {
            "has_phone": bool(business.get("phone")),
            "has_website": bool(business.get("website")),
            "has_email": bool(business.get("email")),
            "has_hours": bool(business.get("hours")),
            "has_rating": bool(business.get("rating")),
            "has_reviews": bool(business.get("reviews")),
            "has_services": bool(business.get("services")),
        }
        
        enrichment_fields = []
        if not business.get("email"):
            enrichment_fields.append("email")
        if not business.get("phone"):
            enrichment_fields.append("phone")
        if not business.get("website"):
            enrichment_fields.append("website")
        if not business.get("hours"):
            enrichment_fields.append("hours")
        
        result = collection.update_one(
            {"_id": business_id},
            {"$set": {
                "completeness_flags": flags,
                "enrichment_fields": enrichment_fields,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating completeness flags: {e}")
        return False


def search_businesses_by_tier(tier: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """
    Search businesses by lead tier with pagination.
    
    Args:
        tier: Lead tier (HOT, WARM, COLD, LOW) or None for all
        limit: Maximum number of results
        
    Returns:
        List of business dictionaries
    """
    collection = get_collection()
    
    try:
        query = {}
        if tier:
            query["lead_score.tier"] = tier.upper()
        
        cursor = collection.find(query).sort("lead_score.total_score", -1).limit(limit)
        businesses = list(cursor)
        
        # Convert ObjectId to string
        for business in businesses:
            if "_id" in business:
                business["_id"] = str(business["_id"])
        
        logger.info(f"Found {len(businesses)} businesses with tier={tier}")
        return businesses
    except Exception as e:
        logger.error(f"Error searching by tier: {e}")
        return []


def get_business_by_id(business_id) -> Optional[Dict]:
    """
    Get a single business by ID.
    
    Args:
        business_id: ObjectId or string ID
        
    Returns:
        Business dictionary or None if not found
    """
    collection = get_collection()
    
    try:
        from bson import ObjectId
        
        # Convert string to ObjectId if needed
        if isinstance(business_id, str):
            business_id = ObjectId(business_id)
        
        business = collection.find_one({"_id": business_id})
        
        if business and "_id" in business:
            business["_id"] = str(business["_id"])
        
        return business
    except Exception as e:
        logger.error(f"Error fetching business by ID: {e}")
        return None

