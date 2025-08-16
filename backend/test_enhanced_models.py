#!/usr/bin/env python3
"""
Test script for the enhanced StatTwin models with league integration.
Run this to verify that all models work correctly with the league system.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from models.player import Player, Position, Foot
from models.similarity_result import SimilarityRequest, SimilarityResponse, SimilarPlayer
from core.leagues import get_league_registry, get_major_leagues


def test_league_integration():
    """Test that models integrate correctly with the league system."""
    print("🧪 Testing League Integration...")
    print("=" * 50)
    
    try:
        # Test SimilarityRequest with league validation
        print("🔍 Testing SimilarityRequest with league validation...")
        
        # Valid request with major leagues
        valid_request = SimilarityRequest(
            reference_player_id="92e7e919",
            league_ids=[9, 13, 20],  # Premier League, La Liga, Bundesliga
            season_id="2023-2024",
            positions=["ST", "CF", "LW"],
            age_min=25,
            age_max=35,
            status="Active",
            is_active=True,
            gender="M",
            max_results=5
        )
        
        print("✅ Valid request created successfully")
        
        # Test league information methods
        league_info = valid_request.get_league_info()
        print(f"✅ League info retrieved: {len(league_info)} leagues")
        
        league_names = valid_request.get_league_names()
        print(f"✅ League names: {league_names}")
        
        countries = valid_request.get_countries()
        print(f"✅ Countries: {countries}")
        
        continents = valid_request.get_continents()
        print(f"✅ Continents: {continents}")
        
        major_only = valid_request.get_major_leagues_only()
        print(f"✅ Major leagues only: {major_only}")
        
        # Test invalid league ID
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                league_ids=[99999],  # Invalid league ID
                gender="M"
            )
            print("❌ Should have failed with invalid league ID")
            return False
        except Exception as e:
            print(f"✅ Correctly caught invalid league ID: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ League integration test failed: {e}")
        return False


def test_comprehensive_league_support():
    """Test that we support all major leagues in our models."""
    print("\n🏆 Testing Comprehensive League Support...")
    print("=" * 50)
    
    try:
        registry = get_league_registry()
        major_leagues = get_major_leagues()
        
        print(f"✅ Found {len(major_leagues)} major leagues")
        
        # Test that we can create requests for all major leagues
        major_league_ids = [league.league_id for league in major_leagues]
        
        # Test a request with all major European leagues
        european_major_ids = [league.league_id for league in major_leagues if league.continent == "Europe"]
        
        european_request = SimilarityRequest(
            reference_player_id="test123",
            league_ids=european_major_ids,
            gender="M",
            max_results=10
        )
        
        print(f"✅ European major leagues request created: {len(european_major_ids)} leagues")
        print(f"   Leagues: {european_request.get_league_names()}")
        
        # Test a request with all major non-European leagues
        non_european_major_ids = [league.league_id for league in major_leagues if league.continent != "Europe"]
        
        non_european_request = SimilarityRequest(
            reference_player_id="test123",
            league_ids=non_european_major_ids,
            gender="M",
            max_results=10
        )
        
        print(f"✅ Non-European major leagues request created: {len(non_european_major_ids)} leagues")
        print(f"   Leagues: {non_european_request.get_league_names()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive league support test failed: {e}")
        return False


def test_league_filtering():
    """Test league filtering capabilities."""
    print("\n🔍 Testing League Filtering...")
    print("=" * 50)
    
    try:
        # Test filtering by continent
        european_request = SimilarityRequest(
            reference_player_id="test123",
            league_ids=[9, 13, 20, 11, 16],  # Big 5 European leagues
            gender="M"
        )
        
        european_continents = european_request.get_continents()
        print(f"✅ European request continents: {european_continents}")
        
        # Test filtering by country
        england_request = SimilarityRequest(
            reference_player_id="test123",
            league_ids=[9, 46],  # Premier League + Championship
            gender="M"
        )
        
        england_countries = england_request.get_countries()
        print(f"✅ England request countries: {england_countries}")
        
        # Test mixed continent request
        mixed_request = SimilarityRequest(
            reference_player_id="test123",
            league_ids=[9, 26, 28],  # Premier League, MLS, Brasileirão
            gender="M"
        )
        
        mixed_continents = mixed_request.get_continents()
        print(f"✅ Mixed request continents: {mixed_continents}")
        
        return True
        
    except Exception as e:
        print(f"❌ League filtering test failed: {e}")
        return False


def test_model_serialization_with_leagues():
    """Test that models with league data can be serialized."""
    print("\n💾 Testing Model Serialization with Leagues...")
    print("=" * 50)
    
    try:
        # Create a request with league data
        request = SimilarityRequest(
            reference_player_id="92e7e919",
            league_ids=[9, 13, 20],
            positions=["ST", "CF"],
            age_min=25,
            age_max=30,
            gender="M"
        )
        
        # Test JSON serialization
        request_json = request.model_dump_json()
        print("✅ SimilarityRequest serialized to JSON successfully")
        print(f"   JSON length: {len(request_json)} characters")
        
        # Test dict conversion
        request_dict = request.model_dump()
        print("✅ SimilarityRequest converted to dict successfully")
        print(f"   Dict keys: {list(request_dict.keys())}")
        
        # Test that league information is preserved
        league_names = request.get_league_names()
        print(f"✅ League names preserved: {league_names}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model serialization test failed: {e}")
        return False


def test_league_validation():
    """Test league validation rules."""
    print("\n✅ Testing League Validation...")
    print("=" * 50)
    
    try:
        # Test empty league_ids list
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                league_ids=[],
                gender="M"
            )
            print("❌ Should have failed with empty league_ids")
            return False
        except Exception as e:
            print(f"✅ Correctly caught empty league_ids: {e}")
        
        # Test invalid league ID
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                league_ids=[99999],
                gender="M"
            )
            print("❌ Should have failed with invalid league ID")
            return False
        except Exception as e:
            print(f"✅ Correctly caught invalid league ID: {e}")
        
        # Test valid league IDs
        try:
            valid_request = SimilarityRequest(
                reference_player_id="test123",
                league_ids=[9, 13, 20],
                gender="M"
            )
            print("✅ Valid league IDs accepted")
        except Exception as e:
            print(f"❌ Valid league IDs rejected: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ League validation test failed: {e}")
        return False


def main():
    """Run all enhanced model tests."""
    print("🚀 StatTwin Enhanced Models with League Integration Test")
    print("=" * 70)
    
    # Run all tests
    tests = [
        ("League Integration", test_league_integration),
        ("Comprehensive League Support", test_comprehensive_league_support),
        ("League Filtering", test_league_filtering),
        ("Model Serialization with Leagues", test_model_serialization_with_leagues),
        ("League Validation", test_league_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*25} {test_name} {'='*25}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Enhanced Models Test Results:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enhanced model tests passed!")
        print("\n📋 League Integration Summary:")
        
        registry = get_league_registry()
        all_leagues = registry.get_all_leagues()
        major_leagues = registry.get_major_leagues()
        
        print(f"   Total Supported Leagues: {len(all_leagues)}")
        print(f"   Major Leagues: {len(major_leagues)}")
        print(f"   League Validation: ✅ Working")
        print(f"   League Filtering: ✅ Working")
        print(f"   League Information: ✅ Working")
        
        print("\n✅ Your enhanced models are ready to work with all major national domestic leagues!")
        print("\n🌍 Supported League Categories:")
        
        # Show major leagues by continent
        by_continent = {}
        for league in major_leagues:
            continent = league.continent or "Unknown"
            if continent not in by_continent:
                by_continent[continent] = []
            by_continent[continent].append(league)
        
        for continent, leagues in by_continent.items():
            print(f"   {continent}: {len(leagues)} major leagues")
            for league in leagues:
                print(f"     - {league.name} ({league.country})")
        
    else:
        print("❌ Some enhanced model tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Check league registry integration")
        print("2. Verify model validation rules")
        print("3. Check for import errors")


if __name__ == "__main__":
    main()
