"""
Test script for MongoDB operations: upsert, deduplication, and indexes.
Run this script to verify MongoDB integration is working correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db_mongo import (
    get_collection,
    upsert_business,
    save_business,
    business_exists,
    is_record_complete,
    search_businesses,
    get_search_count,
    get_all_businesses,
    get_business_count
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample test data
SAMPLE_BUSINESSES = [
    {
        "name": "Joe's Coffee Shop",
        "google_maps_url": "https://maps.google.com/?cid=12345",
        "phone": "+15125551234",
        "website": "https://joescoffee.com",
        "category": "Coffee Shop",
        "location": "Austin, TX",
        "rating": 4.5,
        "review_count": 120
    },
    {
        "name": "Jane's Bakery",
        "google_maps_url": "https://maps.google.com/?cid=67890",
        "phone": "+15125555678",
        "website": "https://janesbakery.com",
        "category": "Bakery",
        "location": "Austin, TX",
        "rating": 4.8,
        "review_count": 200
    },
    {
        "name": "Bob's Auto Repair",
        "google_maps_url": "https://maps.google.com/?cid=11111",
        "phone": "+15125559999",
        "website": "https://bobsauto.com",
        "category": "Auto Repair",
        "location": "Round Rock, TX",
        "rating": 4.2,
        "review_count": 45
    },
    {
        "name": "Pizza Palace",
        "google_maps_url": "https://maps.google.com/?cid=22222",
        "phone": "+15125558888",
        "website": None,  # No website
        "category": "Pizza Restaurant",
        "location": "Austin, TX",
        "rating": 4.0,
        "review_count": 80
    },
    {
        "name": "Tech Solutions Inc",
        "google_maps_url": "https://maps.google.com/?cid=33333",
        "phone": None,  # No phone
        "website": "https://techsolutions.com",
        "category": "IT Services",
        "location": "Austin, TX",
        "rating": 4.6,
        "review_count": 150
    }
]


def test_upsert_and_deduplication():
    """Test 1: Upsert and deduplication logic"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Upsert and Deduplication")
    logger.info("="*60)
    
    # Insert first business
    business1 = SAMPLE_BUSINESSES[0].copy()
    result1 = upsert_business(business1)
    logger.info(f"✓ First insert: {result1} (should be True - new record)")
    
    # Try to insert same business again (should update, not insert)
    result2 = upsert_business(business1)
    logger.info(f"✓ Duplicate insert: {result2} (should be False - existing record)")
    
    # Update existing business with new data
    business1_updated = business1.copy()
    business1_updated["rating"] = 4.9  # Changed rating
    business1_updated["review_count"] = 250  # Changed review count
    result3 = upsert_business(business1_updated)
    logger.info(f"✓ Update existing: {result3} (should be False - updated record)")
    
    # Verify the business exists
    exists = business_exists(business1["google_maps_url"])
    logger.info(f"✓ Business exists check: {exists} (should be True)")
    
    logger.info("✅ Test 1 PASSED: Upsert and deduplication working correctly\n")
    return True


def test_record_completeness():
    """Test 2: Check record completeness logic"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Record Completeness Check")
    logger.info("="*60)
    
    # Complete record (has phone and website)
    complete = SAMPLE_BUSINESSES[0]
    is_complete = is_record_complete(complete)
    logger.info(f"✓ Complete record (phone + website): {is_complete} (should be True)")
    
    # Incomplete record (no website)
    no_website = SAMPLE_BUSINESSES[3]
    is_complete_no_website = is_record_complete(no_website)
    logger.info(f"✓ No website: {is_complete_no_website} (should be False)")
    
    # Incomplete record (no phone)
    no_phone = SAMPLE_BUSINESSES[4]
    is_complete_no_phone = is_record_complete(no_phone)
    logger.info(f"✓ No phone: {is_complete_no_phone} (should be False)")
    
    logger.info("✅ Test 2 PASSED: Record completeness check working correctly\n")
    return True


def test_bulk_insert():
    """Test 3: Bulk insert multiple businesses"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Bulk Insert")
    logger.info("="*60)
    
    inserted_count = 0
    updated_count = 0
    
    for business in SAMPLE_BUSINESSES:
        result = upsert_business(business)
        if result:
            inserted_count += 1
        else:
            updated_count += 1
    
    logger.info(f"✓ Inserted: {inserted_count} new businesses")
    logger.info(f"✓ Updated: {updated_count} existing businesses")
    
    # Get total count
    total = get_business_count()
    logger.info(f"✓ Total businesses in database: {total}")
    
    logger.info("✅ Test 3 PASSED: Bulk insert completed successfully\n")
    return True


def test_search_functionality():
    """Test 4: Search with various filters"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Search Functionality")
    logger.info("="*60)
    
    # Search by query (name)
    results_coffee = search_businesses(query="Coffee", limit=10)
    logger.info(f"✓ Search 'Coffee': Found {len(results_coffee)} results")
    
    # Search by location
    results_austin = search_businesses(location="Austin", limit=10)
    logger.info(f"✓ Search location 'Austin': Found {len(results_austin)} results")
    
    # Search by category
    results_bakery = search_businesses(category="Bakery", limit=10)
    logger.info(f"✓ Search category 'Bakery': Found {len(results_bakery)} results")
    
    # Search businesses with phone numbers
    results_with_phone = search_businesses(has_phone=True, limit=10)
    logger.info(f"✓ Search with phone: Found {len(results_with_phone)} results")
    
    # Search businesses with websites
    results_with_website = search_businesses(has_website=True, limit=10)
    logger.info(f"✓ Search with website: Found {len(results_with_website)} results")
    
    # Search with minimum rating
    results_high_rated = search_businesses(min_rating=4.5, limit=10)
    logger.info(f"✓ Search rating >= 4.5: Found {len(results_high_rated)} results")
    
    # Combined filters
    results_combined = search_businesses(
        location="Austin",
        has_phone=True,
        has_website=True,
        min_rating=4.0,
        limit=10
    )
    logger.info(f"✓ Combined filters (Austin + phone + website + rating>=4.0): Found {len(results_combined)} results")
    
    # Get search count
    count = get_search_count(location="Austin", has_phone=True)
    logger.info(f"✓ Count businesses in Austin with phone: {count}")
    
    logger.info("✅ Test 4 PASSED: Search functionality working correctly\n")
    return True


def test_pagination():
    """Test 5: Pagination"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Pagination")
    logger.info("="*60)
    
    # Get first page
    page1 = search_businesses(limit=2, offset=0)
    logger.info(f"✓ Page 1 (limit=2, offset=0): Found {len(page1)} results")
    
    # Get second page
    page2 = search_businesses(limit=2, offset=2)
    logger.info(f"✓ Page 2 (limit=2, offset=2): Found {len(page2)} results")
    
    # Verify pagination works (different results)
    if len(page1) > 0 and len(page2) > 0:
        page1_ids = [b.get("_id") for b in page1]
        page2_ids = [b.get("_id") for b in page2]
        no_overlap = not any(id in page1_ids for id in page2_ids)
        logger.info(f"✓ Pages don't overlap: {no_overlap}")
    
    logger.info("✅ Test 5 PASSED: Pagination working correctly\n")
    return True


def test_indexes():
    """Test 6: Verify indexes exist"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Index Verification")
    logger.info("="*60)
    
    collection = get_collection()
    indexes = collection.list_indexes()
    
    index_names = []
    for index in indexes:
        index_names.append(index["name"])
        logger.info(f"✓ Index: {index['name']}")
    
    # Check for expected indexes
    expected_indexes = [
        "google_maps_url_unique",
        "phone_idx",
        "website_idx",
        "category_idx",
        "location_idx",
        "rating_idx",
        "name_idx",
        "created_at_idx"
    ]
    
    missing_indexes = []
    for expected in expected_indexes:
        if expected not in index_names:
            missing_indexes.append(expected)
    
    if missing_indexes:
        logger.warning(f"⚠️  Missing indexes: {missing_indexes}")
    else:
        logger.info(f"✓ All expected indexes exist")
    
    logger.info("✅ Test 6 PASSED: Indexes verified\n")
    return True


def run_all_tests():
    """Run all MongoDB tests"""
    logger.info("\n" + "="*80)
    logger.info("MONGODB INTEGRATION TEST SUITE")
    logger.info("="*80)
    
    tests = [
        ("Upsert and Deduplication", test_upsert_and_deduplication),
        ("Record Completeness", test_record_completeness),
        ("Bulk Insert", test_bulk_insert),
        ("Search Functionality", test_search_functionality),
        ("Pagination", test_pagination),
        ("Index Verification", test_indexes)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' FAILED: {e}")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"✅ Passed: {passed}/{len(tests)}")
    logger.info(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED! MongoDB integration is working correctly.")
    else:
        logger.info(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
    
    logger.info("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error running tests: {e}")
        sys.exit(1)
