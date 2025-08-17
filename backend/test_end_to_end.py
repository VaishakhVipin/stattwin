#!/usr/bin/env python3
"""
End-to-end test: preprocessing -> filtering -> similarity.
Validates that the full pipeline works together and produces expected ranking.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure the app directory is on sys.path for module resolution
app_path = Path(__file__).parent / "app"
if str(app_path) not in sys.path:
    sys.path.append(str(app_path))

from algorithms.preprocessing import PreprocessingConfig, preprocess
from algorithms.filtering import FilterSpec, apply_filters
from algorithms.similarity import similar_to_query, WeightConfig


def make_raw_df() -> pd.DataFrame:
    # Build a small realistic dataset with minutes and raw stats
    data = [
        {"player_id": "pA", "name": "A", "position": "FW", "age": 24, "league": "EPL", "continent": "Europe", "season": "2023-2024",
         "minutes": 900, "shots": 20, "shots_on_target": 10, "passes_completed": 300, "passes_attempted": 400, "tackles": 10, "interceptions": 5},
        {"player_id": "pB", "name": "B", "position": "FW", "age": 25, "league": "EPL", "continent": "Europe", "season": "2023-2024",
         "minutes": 800, "shots": 18, "shots_on_target": 9, "passes_completed": 280, "passes_attempted": 380, "tackles": 8, "interceptions": 6},
        {"player_id": "pC", "name": "C", "position": "MF", "age": 27, "league": "La Liga", "continent": "Europe", "season": "2023-2024",
         "minutes": 950, "shots": 6, "shots_on_target": 3, "passes_completed": 700, "passes_attempted": 800, "tackles": 20, "interceptions": 15},
        {"player_id": "pD", "name": "D", "position": "FW", "age": 30, "league": "EPL", "continent": "Europe", "season": "2022-2023",
         "minutes": 700, "shots": 15, "shots_on_target": 7, "passes_completed": 210, "passes_attempted": 300, "tackles": 6, "interceptions": 4},
    ]
    return pd.DataFrame(data)


def test_end_to_end_pipeline() -> bool:
    try:
        raw = make_raw_df()
        # Preprocess: per90 on our raw stat columns
        per90_cols = [
            "shots", "shots_on_target", "passes_completed", "passes_attempted", "tackles", "interceptions"
        ]
        cfg = PreprocessingConfig(per90_cols=per90_cols)
        processed, artifacts, report = preprocess(raw, cfg)

        # Basic sanity on outputs
        z_cols = [c for c in processed.columns if c.endswith("_z")]
        assert z_cols, "No normalized columns created"

        # Filter: EPL, season 2023-2024, age 20..28
        spec = FilterSpec(age_range=(20, 28), league_in=["EPL"], season_in=["2023-2024"])
        filtered = apply_filters(processed, spec)
        # Should keep pA and pB
        keep = set(filtered["player_id"].tolist())
        assert keep == {"pA", "pB"}, f"Filtering mismatch, kept: {keep}"

        # Similarity: query pA, expect pB as top-1 regardless of weighting
        res = similar_to_query(filtered, query_id="pA", top_k=1, return_columns=["player_id"])  # type: ignore[arg-type]
        assert res.iloc[0]["player_id"] == "pB", f"Expected pB as most similar to pA, got {res.iloc[0]['player_id']}"

        # Try position-based weighting (FW) should not change top-1 here
        res_fw = similar_to_query(filtered, query_id="pA", top_k=1, weights=WeightConfig(position="FW"), return_columns=["player_id"])  # type: ignore[arg-type]
        assert res_fw.iloc[0]["player_id"] == "pB", "Weighted similarity changed expected top-1"

        return True
    except AssertionError as e:
        print(f"❌ End-to-end pipeline test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ End-to-end pipeline test error: {e}")
        return False


def main():
    print("🚀 End-to-End Pipeline Test")
    print("=" * 60)
    ok = test_end_to_end_pipeline()
    print("\n" + "=" * 60)
    print("📊 Test Result:")
    print(f"  End-to-End: {'✅ PASSED' if ok else '❌ FAILED'}")


if __name__ == "__main__":
    main()
