"""
Quick validation script to test company search API endpoints.
Run after starting the FastAPI server.

Usage:
    python scripts/test_endpoints.py
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:9000"

def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result with formatting"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"   {details}")
    print()


def test_endpoint(name: str, url: str, expected_keys: list = None) -> bool:
    """Generic endpoint test"""
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print_result(name, False, f"Status code: {response.status_code}")
            return False
        
        data = response.json()
        
        # Check expected keys
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    print_result(name, False, f"Missing key: {key}")
                    return False
        
        print_result(name, True, f"Status: {response.status_code}, Keys: {list(data.keys())[:3]}")
        return True
        
    except requests.exceptions.ConnectionError:
        print_result(name, False, "Connection refused. Is the server running?")
        return False
    except Exception as e:
        print_result(name, False, f"Error: {str(e)}")
        return False


def main():
    """Run all endpoint tests"""
    print("=" * 60)
    print("Company Search API - Endpoint Validation")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = []
    
    # Test 1: List companies (basic)
    results.append(
        test_endpoint(
            "List Companies (Basic)",
            f"{BASE_URL}/companies?limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 2: Search query
    results.append(
        test_endpoint(
            "Search by Query",
            f"{BASE_URL}/companies?query=coffee&limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 3: Location filter
    results.append(
        test_endpoint(
            "Filter by Location",
            f"{BASE_URL}/companies?location=Austin&limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 4: Rating filter
    results.append(
        test_endpoint(
            "Filter by Rating",
            f"{BASE_URL}/companies?rating_min=4.5&limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 5: Has website filter
    results.append(
        test_endpoint(
            "Filter by Has Website",
            f"{BASE_URL}/companies?has_website=true&limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 6: Sorting
    results.append(
        test_endpoint(
            "Sort by Rating",
            f"{BASE_URL}/companies?sort_by=rating&order=desc&limit=5",
            expected_keys=["total", "results"]
        )
    )
    
    # Test 7: Categories metadata
    results.append(
        test_endpoint(
            "Get Categories",
            f"{BASE_URL}/companies/meta/categories?limit=10",
            expected_keys=["categories"]
        )
    )
    
    # Test 8: Locations metadata
    results.append(
        test_endpoint(
            "Get Locations",
            f"{BASE_URL}/companies/meta/locations?limit=10",
            expected_keys=["locations"]
        )
    )
    
    # Test 9: Statistics
    results.append(
        test_endpoint(
            "Database Statistics",
            f"{BASE_URL}/companies/stats/summary",
            expected_keys=["total_companies"]
        )
    )
    
    # Test 10: Check if CSV export endpoint exists (don't download)
    try:
        response = requests.head(f"{BASE_URL}/companies/export/csv?limit=1", timeout=5)
        success = response.status_code in [200, 405]  # 405 means HEAD not allowed, but endpoint exists
        print_result("CSV Export Endpoint", success, f"Status: {response.status_code}")
        results.append(success)
    except Exception as e:
        print_result("CSV Export Endpoint", False, str(e))
        results.append(False)
    
    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"SUMMARY: {passed}/{total} tests passed ({percentage:.1f}%)")
    print("=" * 60)
    
    if passed == total:
        print("✅ All tests passed! API is working correctly.")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed. Check errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure FastAPI server is running: uvicorn app.main:app --reload --port 9000")
        print("2. Check MongoDB connection in .env")
        print("3. Verify database has data (run a scrape first)")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
