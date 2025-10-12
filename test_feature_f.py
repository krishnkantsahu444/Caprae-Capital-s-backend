"""
Tests for Feature F: Data Quality & Search Optimization
"""
import pytest
import sys
sys.path.insert(0, 'app')

from utils.normalization import (
    add_completeness_flags,
    calculate_enrichment_fields,
    normalize_business_response
)


class TestNormalization:
    """Test normalization utility functions."""
    
    def test_add_completeness_flags(self):
        """Test completeness flags are correctly calculated."""
        business = {
            "name": "Test Business",
            "phone": "+1-123-456-7890",
            "website": "https://test.com",
            "email": None,
            "hours": "9am-5pm"
        }
        
        result = add_completeness_flags(business)
        flags = result["completeness_flags"]
        
        assert flags["has_phone"] == True
        assert flags["has_website"] == True
        assert flags["has_email"] == False
        assert flags["has_hours"] == True
        print("✅ test_add_completeness_flags PASSED")
    
    def test_calculate_enrichment_fields(self):
        """Test enrichment fields are correctly identified."""
        business = {
            "name": "Test Business",
            "phone": "+1-123-456-7890",
            "website": None,
            "email": None
        }
        
        fields = calculate_enrichment_fields(business)
        
        assert "email" in fields
        assert "website" in fields
        assert "phone" not in fields
        print("✅ test_calculate_enrichment_fields PASSED")
    
    def test_normalize_business_response(self):
        """Test business response is fully normalized."""
        from bson import ObjectId
        
        business = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Test Business",
            "category": "Restaurant",
            "location": "New York, NY",
            "rating": 4.5,
            "reviews": 100,
            "phone": "+1-123-456-7890",
            "website": "https://test.com",
            "email": None
        }
        
        normalized = normalize_business_response(business)
        
        # Check all required fields exist
        assert "id" in normalized
        assert "name" in normalized
        assert "lead_score" in normalized
        assert "completeness_flags" in normalized
        assert "enrichment_fields" in normalized
        
        # Check completeness flags
        assert normalized["completeness_flags"]["has_phone"] == True
        assert normalized["completeness_flags"]["has_email"] == False
        
        # Check enrichment fields
        assert "email" in normalized["enrichment_fields"]
        
        print("✅ test_normalize_business_response PASSED")


class TestMongoDBIndexes:
    """Test MongoDB indexes are created correctly."""
    
    def test_indexes_created(self):
        """Test that all required indexes exist."""
        from db_mongo import get_collection
        
        collection = get_collection()
        indexes = list(collection.list_indexes())
        
        index_names = [idx['name'] for idx in indexes]
        
        # Check core indexes
        assert "google_maps_url_unique" in index_names
        assert "category_idx" in index_names
        assert "location_idx" in index_names
        
        # Check new Feature F indexes
        assert "lead_score_idx" in index_names
        assert "lead_tier_idx" in index_names
        assert "category_location_score_idx" in index_names
        assert "has_phone_flag_idx" in index_names
        assert "has_email_flag_idx" in index_names
        
        print("✅ test_indexes_created PASSED")
        print(f"   Found {len(index_names)} indexes")
        for name in index_names:
            print(f"   - {name}")


def run_all_tests():
    """Run all Feature F tests."""
    print("=" * 60)
    print("Feature F: Data Quality & Search Optimization - Tests")
    print("=" * 60)
    
    # Test normalization
    print("\n📦 Testing Normalization...")
    test_norm = TestNormalization()
    test_norm.test_add_completeness_flags()
    test_norm.test_calculate_enrichment_fields()
    test_norm.test_normalize_business_response()
    
    # Test MongoDB indexes
    print("\n📊 Testing MongoDB Indexes...")
    test_mongo = TestMongoDBIndexes()
    test_mongo.test_indexes_created()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
