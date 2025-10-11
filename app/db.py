"""SQLite database layer for lead persistence with deduplication."""
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Optional, List
from utils.config import DB_PATH, resolve_path

# Thread-local storage for database connections
_local = threading.local()


def get_connection():
    """Get a thread-safe database connection."""
    if not hasattr(_local, "conn"):
        db_path = resolve_path(DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            phone TEXT,
            website TEXT,
            rating REAL,
            reviews INTEGER,
            google_maps_url TEXT UNIQUE,
            category TEXT,
            hours TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on google_maps_url for faster lookups
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_google_maps_url
        ON businesses(google_maps_url)
    """)

    conn.commit()


def save_business(business: Dict) -> bool:
    """
    Save a business to the database with deduplication.

    Args:
        business: Dictionary with business data. Must include 'google_maps_url' for deduplication.

    Returns:
        True if inserted successfully, False if duplicate (already exists).
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO businesses (
                name, address, phone, website, rating, reviews,
                google_maps_url, category, hours
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            business.get("name"),
            business.get("address"),
            business.get("phone"),
            business.get("website"),
            business.get("rating"),
            business.get("reviews"),
            business.get("google_maps_url"),
            business.get("category"),
            business.get("hours"),
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Duplicate google_maps_url
        return False
    except Exception as e:
        print(f"Error saving business: {e}")
        return False


def get_all_businesses() -> List[Dict]:
    """Retrieve all businesses from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM businesses ORDER BY created_at DESC")
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_business_count() -> int:
    """Get the total number of businesses in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM businesses")
    return cur.fetchone()[0]


def business_exists(google_maps_url: str) -> bool:
    """Check if a business with the given URL already exists."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM businesses WHERE google_maps_url = ? LIMIT 1", (google_maps_url,))
    return cur.fetchone() is not None


# Initialize database on module import
init_db()
