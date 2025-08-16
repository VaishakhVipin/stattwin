#!/usr/bin/env python3
"""
Test script for the StatTwin data models.
Run this to verify that all models are working correctly.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from models.player import Player, Position, Foot
from models.similarity_result import SimilarPlayer, SimilarityRequest, SimilarityResponse


def test_player_model():
    """Test the Player model with sample data."""
    print("🧪 Testing Player Model...")
    print("=" * 50)
    
    try:
        # Create a sample player
        sample_player = Player(
            metadata={
                "player_id": "92e7e919",
                "full_name": "Son Heung-min",
                "positions": [Position.LW, Position.ST],
                "footed": Foot.LEFT,
                "date_of_birth": "1992-07-08",
                "nationality": "South Korea",
                "height": 183.0,
                "weight": 78.0,
                "gender": "M"
            },
            age=31,
            league="Premier League",
            team="Tottenham Hotspur",
            season="2023-2024",
            continent="Asia",
            status="Active",
            is_active=True
        )
        
        print("✅ Player model created successfully")
        print(f"   Name: {sample_player.metadata.full_name}")
        print(f"   Positions: {[pos.value for pos in sample_player.metadata.positions]}")
        print(f"   Primary Position: {sample_player.primary_position}")
        print(f"   Position Group: {sample_player.position_group}")
        print(f"   Age: {sample_player.age}")
        print(f"   League: {sample_player.league}")
        print(f"   Gender: {sample_player.metadata.gender}")
        print(f"   Status: {sample_player.status}")
        print(f"   Active: {sample_player.is_active}")
        
        # Test position weights
        print(f"   Position Weights: {sample_player.position_weights}")
        
        # Test model validation
        print("\n🔍 Testing model validation...")
        
        # Test invalid age
        try:
            invalid_player = Player(
                metadata={
                    "player_id": "test123",
                    "full_name": "Test Player",
                    "positions": [Position.DF]
                },
                age=15  # Invalid age
            )
            print("❌ Should have failed with age < 16")
        except Exception as e:
            print(f"✅ Correctly caught invalid age: {e}")
        
        # Test invalid position
        try:
            invalid_player = Player(
                metadata={
                    "player_id": "test123",
                    "full_name": "Test Player",
                    "positions": ["INVALID"]  # Invalid position
                }
            )
            print("❌ Should have failed with invalid position")
        except Exception as e:
            print(f"✅ Correctly caught invalid position: {e}")
        
        # Test different position types
        print("\n🔍 Testing different position types...")
        
        # Test goalkeeper
        gk_player = Player(
            metadata={
                "player_id": "gk123",
                "full_name": "Test GK",
                "positions": [Position.GK]
            }
        )
        print(f"   Goalkeeper: {gk_player.primary_position} - {gk_player.position_group}")
        print(f"   GK Weights: {gk_player.position_weights}")
        
        # Test center back
        cb_player = Player(
            metadata={
                "player_id": "cb123",
                "full_name": "Test CB",
                "positions": [Position.CB]
            }
        )
        print(f"   Center Back: {cb_player.primary_position} - {cb_player.position_group}")
        print(f"   CB Weights: {cb_player.position_weights}")
        
        # Test striker
        st_player = Player(
            metadata={
                "player_id": "st123",
                "full_name": "Test ST",
                "positions": [Position.ST]
            }
        )
        print(f"   Striker: {st_player.primary_position} - {st_player.position_group}")
        print(f"   ST Weights: {st_player.position_weights}")
        
        return True
        
    except Exception as e:
        print(f"❌ Player model test failed: {e}")
        return False


def test_similarity_models():
    """Test the similarity result models."""
    print("\n🧪 Testing Similarity Models...")
    print("=" * 50)
    
    try:
        # Test SimilarityRequest
        print("🔍 Testing SimilarityRequest...")
        request = SimilarityRequest(
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
        print("✅ SimilarityRequest created successfully")
        print(f"   Multiple Leagues: {request.league_ids}")
        print(f"   Multiple Positions: {request.positions}")
        print(f"   Status Filter: {request.status}")
        print(f"   Gender Filter: {request.gender}")
        
        # Test age validation
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                age_min=30,
                age_max=25  # Invalid: max < min
            )
            print("❌ Should have failed with age_max < age_min")
        except Exception as e:
            print(f"✅ Correctly caught invalid age range: {e}")
        
        # Test new validation rules
        print("\n🔍 Testing new validation rules...")
        
        # Test empty league_ids
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                league_ids=[]  # Invalid: empty list
            )
            print("❌ Should have failed with empty league_ids")
        except Exception as e:
            print(f"✅ Correctly caught empty league_ids: {e}")
        
        # Test empty positions
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                positions=[]  # Invalid: empty list
            )
            print("❌ Should have failed with empty positions")
        except Exception as e:
            print(f"✅ Correctly caught empty positions: {e}")
        
        # Test invalid gender
        try:
            invalid_request = SimilarityRequest(
                reference_player_id="test123",
                gender="X"  # Invalid gender
            )
            print("❌ Should have failed with invalid gender")
        except Exception as e:
            print(f"✅ Correctly caught invalid gender: {e}")
        
        # Test SimilarPlayer
        print("\n🔍 Testing SimilarPlayer...")
        similar_player = SimilarPlayer(
            player=Player(
                metadata={
                    "player_id": "abc123",
                    "full_name": "Similar Player",
                    "positions": [Position.ST]
                }
            ),
            similarity_score=0.89,
            similarity_breakdown={
                "shooting": 0.92,
                "passing": 0.85,
                "defense": 0.78
            }
        )
        print("✅ SimilarPlayer created successfully")
        print(f"   Similarity Score: {similar_player.similarity_score}")
        
        # Test SimilarityResponse
        print("\n🔍 Testing SimilarityResponse...")
        response = SimilarityResponse(
            reference_player=Player(
                metadata={
                    "player_id": "92e7e919",
                    "full_name": "Son Heung-min",
                    "positions": [Position.LW, Position.ST]
                }
            ),
            similar_players=[similar_player],
            filters_applied={
                "league_id": 9,
                "position": "FW",
                "age_range": [25, 35]
            },
            search_metadata={
                "total_players_searched": 500,
                "search_time_ms": 245,
                "algorithm_used": "cosine_similarity"
            }
        )
        print("✅ SimilarityResponse created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Similarity models test failed: {e}")
        return False


def test_model_serialization():
    """Test that models can be serialized to JSON."""
    print("\n🧪 Testing Model Serialization...")
    print("=" * 50)
    
    try:
        # Create a sample player
        player = Player(
            metadata={
                "player_id": "test123",
                "full_name": "Test Player",
                "positions": [Position.CM]
            },
            age=25,
            league="Test League"
        )
        
        # Test JSON serialization
        player_json = player.model_dump_json()
        print("✅ Player model serialized to JSON successfully")
        print(f"   JSON length: {len(player_json)} characters")
        
        # Test JSON with indentation
        player_json_pretty = player.model_dump_json(indent=2)
        print("✅ Player model serialized to pretty JSON successfully")
        
        # Test dict conversion
        player_dict = player.model_dump()
        print("✅ Player model converted to dict successfully")
        print(f"   Dict keys: {list(player_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model serialization test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 StatTwin Data Models Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Player Model", test_player_model),
        ("Similarity Models", test_similarity_models),
        ("Model Serialization", test_model_serialization)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your data models are ready to use.")
        print("\nNext steps:")
        print("1. Test with real FBRef data")
        print("2. Build the preprocessing algorithms")
        print("3. Implement the similarity engine")
    else:
        print("❌ Some tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("1. Check Pydantic installation")
        print("2. Verify model imports")
        print("3. Check for syntax errors in models")
