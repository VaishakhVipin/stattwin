#!/usr/bin/env python3
"""
Test script for the StatTwin league management system.
Run this to verify that all leagues are properly configured and accessible.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from core.leagues import (
    get_league_registry, get_major_leagues, get_league_by_id,
    get_leagues_by_country, get_league_hierarchy, LeagueTier, LeagueType
)
from core.fbref_client import FBRefClient


def test_league_registry():
    """Test the league registry functionality."""
    print("🧪 Testing League Registry...")
    print("=" * 50)
    
    try:
        registry = get_league_registry()
        
        # Test basic functionality
        all_leagues = registry.get_all_leagues()
        major_leagues = registry.get_major_leagues()
        
        print(f"✅ Total leagues: {len(all_leagues)}")
        print(f"✅ Major leagues: {len(major_leagues)}")
        
        # Test league retrieval by ID
        premier_league = registry.get_league(9)
        if premier_league:
            print(f"✅ Premier League found: {premier_league.name} ({premier_league.country})")
            print(f"   Tier: {premier_league.tier}")
            print(f"   Continent: {premier_league.continent}")
            print(f"   Governing Body: {premier_league.governing_body}")
            print(f"   Is Major: {premier_league.is_major}")
        else:
            print("❌ Premier League not found")
            return False
        
        # Test leagues by country
        england_leagues = registry.get_leagues_by_country("ENG")
        print(f"✅ England leagues: {len(england_leagues)}")
        for league in england_leagues:
            print(f"   - {league.name} (ID: {league.league_id}, Tier: {league.tier})")
        
        # Test leagues by continent
        european_leagues = registry.get_leagues_by_continent("Europe")
        print(f"✅ European leagues: {len(european_leagues)}")
        
        # Test leagues by tier
        first_tier_leagues = registry.get_leagues_by_tier(LeagueTier.FIRST)
        print(f"✅ First tier leagues: {len(first_tier_leagues)}")
        
        return True
        
    except Exception as e:
        print(f"❌ League registry test failed: {e}")
        return False


def test_major_leagues():
    """Test major league functionality."""
    print("\n🏆 Testing Major Leagues...")
    print("=" * 50)
    
    try:
        major_leagues = get_major_leagues()
        
        print(f"✅ Found {len(major_leagues)} major leagues:")
        
        # Group by continent
        by_continent = {}
        for league in major_leagues:
            continent = league.continent or "Unknown"
            if continent not in by_continent:
                by_continent[continent] = []
            by_continent[continent].append(league)
        
        for continent, leagues in by_continent.items():
            print(f"\n🌍 {continent}:")
            for league in leagues:
                print(f"   - {league.name} ({league.country})")
        
        # Verify we have the Big 5 European leagues
        big5_ids = {9, 13, 20, 11, 16}  # Premier League, La Liga, Bundesliga, Serie A, Ligue 1
        big5_found = {league.league_id for league in major_leagues if league.league_id in big5_ids}
        
        if len(big5_found) == 5:
            print(f"\n✅ All Big 5 European leagues found: {big5_found}")
        else:
            print(f"\n⚠️  Missing Big 5 leagues. Found: {big5_found}, Expected: {big5_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ Major leagues test failed: {e}")
        return False


def test_league_search():
    """Test league search functionality."""
    print("\n🔍 Testing League Search...")
    print("=" * 50)
    
    try:
        registry = get_league_registry()
        
        # Test search by league name
        premier_results = registry.search_leagues("Premier")
        print(f"✅ 'Premier' search results: {len(premier_results)}")
        for league in premier_results:
            print(f"   - {league.name} ({league.country})")
        
        # Test search by country
        spain_results = registry.search_leagues("Spain")
        print(f"✅ 'Spain' search results: {len(spain_results)}")
        for league in spain_results:
            print(f"   - {league.name} (Tier: {league.tier})")
        
        # Test search by country code
        ger_results = registry.search_leagues("GER")
        print(f"✅ 'GER' search results: {len(ger_results)}")
        for league in ger_results:
            print(f"   - {league.name} (Tier: {league.tier})")
        
        return True
        
    except Exception as e:
        print(f"❌ League search test failed: {e}")
        return False


def test_league_hierarchy():
    """Test league hierarchy organization."""
    print("\n🏗️  Testing League Hierarchy...")
    print("=" * 50)
    
    try:
        hierarchy = get_league_hierarchy()
        
        print(f"✅ Found {len(hierarchy)} continents:")
        
        for continent, countries in hierarchy.items():
            print(f"\n🌍 {continent}:")
            for country, leagues in countries.items():
                print(f"   🇺🇳 {country}: {len(leagues)} leagues")
                for league in leagues:
                    tier_icon = "🥇" if league.tier == LeagueTier.FIRST else "🥈" if league.tier == LeagueTier.SECOND else "🥉"
                    major_icon = "⭐" if league.is_major else "  "
                    print(f"     {tier_icon} {major_icon} {league.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ League hierarchy test failed: {e}")
        return False


def test_fbref_integration():
    """Test FBRef client integration with leagues."""
    print("\n🔗 Testing FBRef Integration...")
    print("=" * 50)
    
    try:
        # Note: This would require an actual API connection
        # For now, we'll test the methods that don't require API calls
        
        client = FBRefClient()
        
        # Test getting supported leagues
        supported_leagues = client.get_supported_leagues()
        print(f"✅ FBRef client reports {len(supported_leagues)} supported leagues")
        
        # Test getting major leagues
        major_leagues = client.get_major_leagues()
        print(f"✅ FBRef client reports {len(major_leagues)} major leagues")
        
        # Test league info retrieval
        premier_info = client.get_league_info(9)
        if premier_info:
            print(f"✅ Premier League info retrieved: {premier_info.name}")
        else:
            print("❌ Premier League info not found")
        
        # Test league search
        search_results = client.search_leagues("Premier")
        print(f"✅ FBRef client search found {len(search_results)} 'Premier' leagues")
        
        return True
        
    except Exception as e:
        print(f"❌ FBRef integration test failed: {e}")
        print("   Note: This is expected if no API connection is available")
        return False


def main():
    """Run all league tests."""
    print("🚀 StatTwin League Management System Test")
    print("=" * 60)
    
    # Run all tests
    tests = [
        ("League Registry", test_league_registry),
        ("Major Leagues", test_major_leagues),
        ("League Search", test_league_search),
        ("League Hierarchy", test_league_hierarchy),
        ("FBRef Integration", test_fbref_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 League System Test Results:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All league system tests passed!")
        print("\n📋 League Coverage Summary:")
        
        registry = get_league_registry()
        all_leagues = registry.get_all_leagues()
        major_leagues = registry.get_major_leagues()
        
        # Count by continent
        by_continent = {}
        for league in all_leagues:
            continent = league.continent or "Unknown"
            if continent not in by_continent:
                by_continent[continent] = 0
            by_continent[continent] += 1
        
        print(f"   Total Leagues: {len(all_leagues)}")
        print(f"   Major Leagues: {len(major_leagues)}")
        print(f"   Continents: {len(by_continent)}")
        
        for continent, count in sorted(by_continent.items()):
            print(f"   {continent}: {count} leagues")
        
        print("\n✅ Your league system is ready to support all major national domestic leagues!")
        
    else:
        print("❌ Some league system tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Check league registry initialization")
        print("2. Verify league data structure")
        print("3. Check for import errors")


if __name__ == "__main__":
    main()
