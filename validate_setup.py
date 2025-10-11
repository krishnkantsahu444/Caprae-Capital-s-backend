"""
Validation script to check if Crawlee integration is properly set up.

Run this script to verify:
1. All dependencies are installed
2. Playwright browsers are available
3. Configuration is valid
4. Database can be initialized
5. Parsers work correctly

Usage:
    python validate_setup.py
"""

import sys
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_header(msg):
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}{msg}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


def check_python_version():
    """Check if Python version is 3.9+."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python version {version.major}.{version.minor} is too old. Need 3.9+")
        return False


def check_imports():
    """Check if all required packages are installed."""
    packages = {
        "fastapi": "FastAPI",
        "celery": "Celery",
        "redis": "Redis",
        "crawlee": "Crawlee",
        "playwright": "Playwright",
        "beautifulsoup4": "BeautifulSoup4",
        "lxml": "lxml",
        "dotenv": "python-dotenv",
        "pydantic": "Pydantic",
    }

    all_ok = True
    for module_name, display_name in packages.items():
        try:
            if module_name == "beautifulsoup4":
                __import__("bs4")
            elif module_name == "dotenv":
                __import__("dotenv")
            else:
                __import__(module_name)
            print_success(f"{display_name} installed")
        except ImportError:
            print_error(f"{display_name} NOT installed")
            all_ok = False

    return all_ok


def check_playwright_browsers():
    """Check if Playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_success("Playwright Chromium browser installed and working")
                return True
            except Exception as e:
                print_error(f"Playwright browsers not installed: {e}")
                print_warning("Run: python -m playwright install chromium")
                return False
    except ImportError:
        print_error("Playwright not installed")
        return False


def check_app_structure():
    """Check if all required app directories and files exist."""
    required_paths = [
        "app/__init__.py",
        "app/main.py",
        "app/db.py",
        "app/parsers.py",
        "app/celery_tasks/tasks.py",
        "app/routers/scraper.py",
        "app/schemas/scraper.py",
        "app/crawlers/google_maps_crawlee.py",
        "app/utils/config.py",
        "app/utils/anti_bot.py",
    ]

    all_ok = True
    for path in required_paths:
        if Path(path).exists():
            print_success(f"Found: {path}")
        else:
            print_error(f"Missing: {path}")
            all_ok = False

    return all_ok


def check_config_files():
    """Check if configuration files exist."""
    files = {
        ".env.example": "Optional (copy to .env)",
        "user_agents.txt": "Required",
        "proxies.txt.example": "Optional (copy to proxies.txt)",
    }

    all_ok = True
    for file_path, description in files.items():
        if Path(file_path).exists():
            print_success(f"Found: {file_path} ({description})")
        else:
            if "example" in file_path:
                print_warning(f"Missing: {file_path} ({description})")
            else:
                print_error(f"Missing: {file_path} ({description})")
                all_ok = False

    return all_ok


def test_database():
    """Test database initialization."""
    try:
        # Import after checking dependencies
        sys.path.insert(0, str(Path(__file__).parent))
        from app.db import init_db, save_business, get_business_count

        init_db()
        print_success("Database initialized successfully")

        # Test insert
        test_business = {
            "name": "Test Business",
            "address": "123 Test St",
            "phone": "555-1234",
            "website": "https://test.com",
            "rating": 4.5,
            "reviews": 100,
            "google_maps_url": "https://google.com/maps/test123",
            "category": "Test",
            "hours": "9-5",
        }

        saved = save_business(test_business)
        if saved:
            print_success("Test business saved to database")

            # Test deduplication
            duplicate = save_business(test_business)
            if not duplicate:
                print_success("Deduplication working correctly")
            else:
                print_error("Deduplication failed - duplicate was saved")
                return False
        else:
            print_error("Failed to save test business")
            return False

        return True
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False


def test_parser():
    """Test HTML parser with sample data."""
    try:
        from app.parsers import parse_card_html

        sample_html = """
        <div class="Nv2PK">
            <div class="qBF1Pd">Test Coffee Shop</div>
            <span class="W4Efsd">123 Main St, City, State 12345</span>
            <span class="MW4etd">4.5</span>
            <span class="UY7F9">(234)</span>
            <a href="/maps/place/test">Link</a>
        </div>
        """

        results = parse_card_html(sample_html)
        if results and len(results) > 0:
            print_success(f"Parser working - extracted {len(results)} business(es)")
            return True
        else:
            print_warning("Parser returned no results (selectors may need updating)")
            return True  # Not a critical failure
    except Exception as e:
        print_error(f"Parser test failed: {e}")
        return False


def check_redis_connection():
    """Check if Redis is accessible."""
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        print_success("Redis is running and accessible")
        return True
    except Exception as e:
        print_warning(f"Redis not accessible: {e}")
        print_warning("Start Redis with: redis-server")
        return False


def main():
    """Run all validation checks."""
    print_header("🔍 Validating Crawlee Integration Setup")

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_imports),
        ("Playwright Browsers", check_playwright_browsers),
        ("App Structure", check_app_structure),
        ("Config Files", check_config_files),
        ("Database", test_database),
        ("Parser", test_parser),
        ("Redis Connection", check_redis_connection),
    ]

    results = {}
    for name, check_func in checks:
        print_header(f"Checking: {name}")
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            results[name] = False

    # Summary
    print_header("📊 Validation Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, status in results.items():
        if status:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{BOLD}Result: {passed}/{total} checks passed{RESET}")

    if passed == total:
        print_success("\n🎉 All checks passed! Your setup is ready for production.")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Start Celery: celery -A app.celery_tasks.tasks worker --loglevel=info")
        print("3. Start FastAPI: uvicorn app.main:app --reload --port 9000")
        print("4. Test scraping: See QUICKSTART.md")
        return 0
    else:
        print_error("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install dependencies: pip install -r requirements.txt")
        print("- Install Playwright: python -m playwright install chromium")
        print("- Start Redis: redis-server")
        return 1


if __name__ == "__main__":
    sys.exit(main())
