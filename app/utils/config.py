"""Centralized configuration loader from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Database configuration - SQLite (legacy)
DB_PATH = os.getenv("DB_PATH", "leads.db")

# Database configuration - MongoDB (primary)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "crashlens")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "businesses")

# Anti-bot configuration
PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "proxies.txt")
USER_AGENTS_PATH = os.getenv("USER_AGENTS_PATH", "user_agents.txt")

# Crawler settings
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
MAX_PER_SESSION = int(os.getenv("MAX_PER_SESSION", "50"))
MAX_REQUESTS_PER_CRAWL = int(os.getenv("MAX_REQUESTS_PER_CRAWL", "20"))

# Delays (milliseconds)
MIN_DELAY_MS = int(os.getenv("MIN_DELAY_MS", "1000"))
MAX_DELAY_MS = int(os.getenv("MAX_DELAY_MS", "3500"))

# Detail page scraping configuration
DETAIL_PAGE_TIMEOUT = int(os.getenv("DETAIL_PAGE_TIMEOUT", "20000"))
MAX_DETAIL_ATTEMPTS = int(os.getenv("MAX_DETAIL_ATTEMPTS", "3"))
DETAIL_PAGE_DELAY_MS_MIN = int(os.getenv("DETAIL_PAGE_DELAY_MS_MIN", "1500"))
DETAIL_PAGE_DELAY_MS_MAX = int(os.getenv("DETAIL_PAGE_DELAY_MS_MAX", "3500"))

# Phone normalization (regex pattern to remove non-digits except +)
PHONE_NORMALIZE_REGEX = os.getenv("PHONE_NORMALIZE_REGEX", "[^0-9+]")

# Database behavior
DB_UPSERT_ON_INSERT = os.getenv("DB_UPSERT_ON_INSERT", "true").lower() == "true"


def get_project_root():
    """Return the absolute path to the project root."""
    return Path(__file__).parent.parent.parent


def resolve_path(relative_path: str) -> Path:
    """Resolve a relative path from the project root."""
    return get_project_root() / relative_path
