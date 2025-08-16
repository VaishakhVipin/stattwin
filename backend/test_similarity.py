#!/usr/bin/env python3
"""
Tests for the Similarity Engine.
Validates cosine/euclidean similarity, position-based weighting, ranking, filters, and batch API.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure the app directory is on sys.path for module resolution
app_path = Path(__file__).parent / "app"
if str(app_path) not in sys.path:
    sys.path.append(str(app_path))

from algorithms.similarity import (
    similar_to_query,
    WeightConfig,
    rank_all_against_all,
)


def make_basic_df() -> pd.DataFrame:
    # Features named to integrate with WeightConfig keywords
    # shots_per90_z (shooting), passes_completed_per90_z (passing)
    data = [
        {"player_id": "pA", "name": "A", "position": "FW", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 1.0, "passes_completed_per90_z": 0.0},
        {"player_id": "pB", "name": "B", "position": "FW", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 0.9, "passes_completed_per90_z": 0.1},
        {"player_id": "pC", "name": "C", "position": "DF", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": -1.0, "passes_completed_per90_z": 0.0},
        {"player_id": "pD", "name": "D", "position": "MF", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 0.707, "passes_completed_per90_z": 0.707},
    ]
    return pd.DataFrame(data)


def make_weight_flip_df() -> pd.DataFrame:
    data = [
        {"player_id": "pQ", "name": "Q", "position": "MF", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 0.7, "passes_completed_per90_z": 0.7},  # query row
        {"player_id": "pB", "name": "B", "position": "FW", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 0.9, "passes_completed_per90_z": 0.6},
        {"player_id": "pC", "name": "C", "position": "MF", "league": "EPL", "season": "2023-2024",
         "shots_per90_z": 0.6, "passes_completed_per90_z": 0.9},
    ]
    return pd.DataFrame(data)


def test_cosine_and_euclidean() -> bool:
    try:
        df = make_basic_df()
        # Cosine similarity: query pA (1,0). Expect pB then pD as top-2.
        res_cos = similar_to_query(df, query_id="pA", top_k=2, metric="cosine", return_columns=["player_id"])  # type: ignore[arg-type]
        top_ids = res_cos["player_id"].tolist()
        assert top_ids == ["pB", "pD"], f"Unexpected cosine ranking: {top_ids}"

        # Euclidean (converted to similarity 1/(1+d)): nearest should still be pB then pD
        res_euc = similar_to_query(df, query_id="pA", top_k=2, metric="euclidean", return_columns=["player_id"])  # type: ignore[arg-type]
        top_ids_e = res_euc["player_id"].tolist()
        assert top_ids_e == ["pB", "pD"], f"Unexpected euclidean ranking: {top_ids_e}"
        return True
    except AssertionError as e:
        print(f"❌ Cosine/Euclidean test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Cosine/Euclidean test error: {e}")
        return False


def test_position_weighting_flip() -> bool:
    try:
        df = make_weight_flip_df()
        # With FW weighting (boost shots), B should outrank C
        res_fw = similar_to_query(
            df,
            query_id="pQ",
            weights=WeightConfig(position="FW"),
            top_k=2,
            return_columns=["player_id"],
        )
        ids_fw = res_fw["player_id"].tolist()
        assert ids_fw == ["pB", "pC"], f"FW weighting expected B> C, got {ids_fw}"

        # With MF weighting (boost passes), C should outrank B
        res_mf = similar_to_query(
            df,
            query_id="pQ",
            weights=WeightConfig(position="MF"),
            top_k=2,
            return_columns=["player_id"],
        )
        ids_mf = res_mf["player_id"].tolist()
        assert ids_mf == ["pC", "pB"], f"MF weighting expected C> B, got {ids_mf}"
        return True
    except AssertionError as e:
        print(f"❌ Weighting flip test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Weighting flip test error: {e}")
        return False


def test_filters_and_batch() -> bool:
    try:
        df = make_basic_df()
        # Filter out EPL to force empty? Instead filter position to only MF, which keeps D
        res = similar_to_query(
            df,
            query_id="pA",
            top_k=3,
            filters={"position_in": ["MF"]},
            return_columns=["player_id", "position"],
        )
        ids = res["player_id"].tolist()
        assert ids == ["pD"], f"Filter should keep only D, got {ids}"

        # Batch
        allres = rank_all_against_all(df, top_k=1)
        assert len(allres) == len(df), "Batch results count mismatch"
        # For pA top-1 should be B
        ra = allres["pA"]
        assert ra.iloc[0]["player_id"] == "pB", "Batch pA top-1 should be B"
        return True
    except AssertionError as e:
        print(f"❌ Filters/Batch test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Filters/Batch test error: {e}")
        return False


def main():
    print("🚀 Similarity Engine Tests")
    print("=" * 60)
    tests = [
        ("Cosine & Euclidean", test_cosine_and_euclidean),
        ("Position Weighting Flip", test_position_weighting_flip),
        ("Filters & Batch", test_filters_and_batch),
    ]
    results = []
    for name, fn in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        ok = fn()
        results.append((name, ok))

    print("\n" + "=" * 60)
    print("📊 Test Results:")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        print(f"  {name}: {'✅ PASSED' if ok else '❌ FAILED'}")
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All similarity tests passed!")
    else:
        print("❌ Some similarity tests failed. Check logs above.")


if __name__ == "__main__":
    main()
