# app/db_motor.py
"""
Async MongoDB connector using Motor for FastAPI endpoints.
This coexists with db_mongo.py (sync pymongo) used by Celery tasks.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from typing import Optional
import logging
from app.utils.config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

logger = logging.getLogger(__name__)

# Global Motor client (async)
client: Optional[AsyncIOMotorClient] = None
db = None
collection: Optional[AsyncIOMotorCollection] = None


def init_motor() -> AsyncIOMotorCollection:
    """
    Initialize Motor (async MongoDB client) for FastAPI.
    Creates indexes idempotently.
    Returns the collection object.
    """
    global client, db, collection
    
    if client is None:
        logger.info(f"Initializing Motor client for MongoDB: {MONGO_URI}")
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]
        logger.info(f"Motor initialized: Database={MONGO_DB_NAME}, Collection={MONGO_COLLECTION}")
    
    return collection


async def create_indexes_async():
    """
    Create MongoDB indexes asynchronously.
    Call this during FastAPI startup event.
    """
    if collection is None:
        init_motor()
    
    try:
        # Unique index on google_maps_url for deduplication
        await collection.create_index("google_maps_url", unique=True)
        logger.info("Created unique index on 'google_maps_url'")
        
        # Standard indexes for common filters
        await collection.create_index("category")
        logger.info("Created index on 'category'")
        
        await collection.create_index("location")
        logger.info("Created index on 'location'")
        
        await collection.create_index("rating")
        logger.info("Created index on 'rating'")
        
        await collection.create_index("created_at")
        logger.info("Created index on 'created_at'")
        
        # Compound index for common query patterns
        await collection.create_index([("category", 1), ("rating", -1)])
        logger.info("Created compound index on 'category' and 'rating'")
        
        logger.info("✅ All Motor indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Index creation warning (may already exist): {e}")


def get_collection() -> AsyncIOMotorCollection:
    """
    Get the Motor collection instance.
    Initializes if not already done.
    """
    if collection is None:
        return init_motor()
    return collection


async def close_motor():
    """
    Close Motor client connection.
    Call this during FastAPI shutdown event.
    """
    global client
    if client:
        client.close()
        logger.info("Motor client closed")
