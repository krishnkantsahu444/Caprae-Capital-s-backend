"""Integration smoke test for end-to-end scraping workflow.

This test runs a small scrape to verify:
1. Crawlee spider can access Google Maps
2. Card parsing works
3. Detail page enrichment works
4. Phone normalization works
5. DB upsert works
6. At least one complete record is saved

Run with: RUN_INTEGRATION=true pytest tests/test_integration_smoke.py -v -s

NOTE: This test is slow (~30-60 seconds) and makes real network requests.
      Skip in CI unless RUN_INTEGRATION=true is set.
"""
import sys
import os
import pytest
import asyncio
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from crawlers.google_maps_crawlee import GoogleMapsCrawlee
from db_mongo import get_collection, get_business_count, is_record_complete

# Configure logging for visibility during test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Check if integration tests should run
RUN_INTEGRATION = os.getenv("RUN_INTEGRATION", "false").lower() == "true"

# Skip all tests in this module unless RUN_INTEGRATION is set
pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Integration tests skipped. Set RUN_INTEGRATION=true to run."
)


@pytest.fixture
def safe_query():
    """Safe query for testing that won't overwhelm Google."""
    return {
        "query": "coffee shop",
        "location": "Berkeley, CA",  # Small town for fewer results
        "max_results": 3,  # Minimal for fast test
    }


@pytest.mark.slow
@pytest.mark.integration
def test_smoke_scrape_end_to_end(safe_query):
    """
    Smoke test: Run minimal scrape and verify complete records are saved.
    
    This test:
    - Runs Crawlee spider with max_results=3
    - Verifies at least 1 record is saved to MongoDB
    - Verifies at least 1 record has both phone and website (complete)
    """
    print("\n" + "="*80)
    print("🔥 SMOKE TEST: Running minimal end-to-end scrape")
    print("="*80)
    
    # Get initial count
    collection = get_collection()
    initial_count = collection.count_documents({})
    print(f"📊 Initial DB count: {initial_count}")
    
    # Run crawler
    print(f"\n🚀 Starting crawl: {safe_query['query']} in {safe_query['location']}")
    print(f"   Max results: {safe_query['max_results']}")
    print(f"   Headless: False (for debugging)")
    
    crawler = GoogleMapsCrawlee(
        query=safe_query["query"],
        location=safe_query["location"],
        max_results=safe_query["max_results"],
        headless=False,  # Set to False so dev can see browser
        use_proxies=False,  # No proxies for local test
    )
    
    try:
        # Run synchronously
        result = crawler.run()
        
        print(f"\n✅ Crawl completed!")
        print(f"   Results scraped: {result['results_count']}")
        
    except Exception as e:
        pytest.fail(f"❌ Crawl failed with exception: {e}")
    
    # Verify results
    final_count = collection.count_documents({})
    new_records = final_count - initial_count
    
    print(f"\n📊 Final DB count: {final_count}")
    print(f"   New records: {new_records}")
    
    # Assert at least 1 record was saved
    assert new_records >= 1, f"Expected at least 1 new record, got {new_records}"
    
    # Check for complete records (phone + website)
    complete_count = collection.count_documents({
        "phone": {"$exists": True, "$ne": None},
        "website": {"$exists": True, "$ne": None}
    })
    
    print(f"\n✨ Complete records (phone + website): {complete_count}")
    
    # Get sample of saved records
    recent_records = list(collection.find().sort("created_at", -1).limit(safe_query["max_results"]))
    
    print(f"\n📋 Sample of saved records:")
    for i, record in enumerate(recent_records[:3], 1):
        name = record.get("name", "Unknown")
        phone = record.get("phone", "N/A")
        website = record.get("website", "N/A")
        complete = is_record_complete(record)
        
        print(f"   {i}. {name}")
        print(f"      Phone: {phone}")
        print(f"      Website: {website}")
        print(f"      Complete: {'✅' if complete else '⚠️'}")
    
    # Assert at least 1 complete record exists
    assert complete_count >= 1, (
        f"Expected at least 1 complete record (phone + website), got {complete_count}. "
        f"This suggests detail page enrichment is not working."
    )
    
    print(f"\n" + "="*80)
    print("✅ SMOKE TEST PASSED!")
    print("="*80)


@pytest.mark.slow
@pytest.mark.integration
def test_phone_normalization_in_db():
    """
    Verify that saved phone numbers are normalized (no special characters except +).
    """
    print("\n🔍 Testing phone normalization in DB...")
    
    collection = get_collection()
    
    # Find records with phone numbers
    records_with_phone = list(collection.find(
        {"phone": {"$exists": True, "$ne": None}},
        {"name": 1, "phone": 1}
    ).limit(10))
    
    assert len(records_with_phone) > 0, "No records with phone numbers found in DB"
    
    print(f"   Found {len(records_with_phone)} records with phones")
    
    # Check normalization
    for record in records_with_phone:
        phone = record.get("phone", "")
        name = record.get("name", "Unknown")
        
        # Phone should only contain digits and + and |
        valid_chars = set("0123456789+|")
        phone_chars = set(phone)
        invalid_chars = phone_chars - valid_chars
        
        print(f"   - {name}: {phone}")
        
        assert len(invalid_chars) == 0, (
            f"Phone for '{name}' contains invalid characters: {invalid_chars}. "
            f"Phone: {phone}"
        )
    
    print("   ✅ All phone numbers are properly normalized")


@pytest.mark.slow  
@pytest.mark.integration
def test_upsert_behavior():
    """
    Test that upserting the same business doesn't create duplicates.
    """
    print("\n🔍 Testing upsert behavior...")
    
    from db_mongo import save_business
    
    collection = get_collection()
    
    # Create a test business
    test_business = {
        "name": "Test Business - Upsert Test",
        "google_maps_url": "https://www.google.com/maps/place/test_upsert_12345",
        "phone": "+15555551234",
        "website": "https://test.com",
        "address": "123 Test St",
        "category": "Test Category",
        "rating": 5.0,
    }
    
    # Get initial count
    initial_count = collection.count_documents({})
    
    # Save once
    saved1 = save_business(test_business.copy())
    count_after_1 = collection.count_documents({})
    
    # Save again (should update, not insert)
    test_business["phone"] = "+15555559999"  # Change phone
    saved2 = save_business(test_business.copy())
    count_after_2 = collection.count_documents({})
    
    # Clean up
    collection.delete_one({"google_maps_url": test_business["google_maps_url"]})
    
    print(f"   Initial count: {initial_count}")
    print(f"   After 1st save: {count_after_1} (saved={saved1})")
    print(f"   After 2nd save: {count_after_2} (saved={saved2})")
    
    # Verify upsert behavior
    assert count_after_1 == initial_count + 1, "First save should insert"
    assert count_after_2 == count_after_1, "Second save should update, not insert duplicate"
    
    print("   ✅ Upsert works correctly (no duplicates)")


if __name__ == "__main__":
    # Run with: python tests/test_integration_smoke.py
    # Make sure to set RUN_INTEGRATION=true
    
    if not RUN_INTEGRATION:
        print("\n⚠️  Integration tests are disabled.")
        print("   Set environment variable: RUN_INTEGRATION=true")
        print("   Then run: pytest tests/test_integration_smoke.py -v -s")
        sys.exit(0)
    
    pytest.main([__file__, "-v", "-s", "--tb=short"])
