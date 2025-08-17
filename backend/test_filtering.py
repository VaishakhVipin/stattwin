#!/usr/bin/env python3
"""
Tests for the Player Filtering System.
Covers individual filters, combined pipeline, and validation.
"""

import sys
from pathlib import Path
import pandas as pd

# Ensure the app directory is on sys.path for module resolution
app_path = Path(__file__).parent / "app"
if str(app_path) not in sys.path:
    sys.path.append(str(app_path))

from algorithms.filtering import (
    FilterSpec,
    filter_by_age,
    filter_by_league,
    filter_by_continent,
    filter_by_position,
    filter_by_season,
    apply_filters,
    apply_filters_with_report,
    validate_filters,
)


def make_meta_df() -> pd.DataFrame:
    data = [
        {"player_id": "p1", "name": "A", "position": "FW", "age": 24, "league": "EPL", "continent": "Europe", "season": "2023-2024"},
        {"player_id": "p2", "name": "B", "position": "MF", "age": 29, "league": "EPL", "continent": "Europe", "season": "2023-2024"},
        {"player_id": "p3", "name": "C", "position": "DF", "age": 21, "league": "La Liga", "continent": "Europe", "season": "2023-2024"},
        {"player_id": "p4", "name": "D", "position": "FW", "age": 31, "league": "Serie A", "continent": "Europe", "season": "2022-2023"},
    ]
    return pd.DataFrame(data)


def test_individual_filters() -> bool:
    try:
        df = make_meta_df()
        # Age 22..30 should include p1 (24), p2 (29), exclude p3 (21) and p4 (31)
        age_df = filter_by_age(df, (22, 30))
        assert set(age_df["player_id"]) == {"p1", "p2"}

        # League EPL -> p1, p2
        lg_df = filter_by_league(df, ["EPL"])
        assert set(lg_df["player_id"]) == {"p1", "p2"}

        # Continent Europe -> all
        ct_df = filter_by_continent(df, ["Europe"])
        assert set(ct_df["player_id"]) == {"p1", "p2", "p3", "p4"}

        # Position FW -> p1, p4
        pos_df = filter_by_position(df, ["FW"])
        assert set(pos_df["player_id"]) == {"p1", "p4"}

        # Season 2023-2024 -> p1, p2, p3
        ss_df = filter_by_season(df, ["2023-2024"])
        assert set(ss_df["player_id"]) == {"p1", "p2", "p3"}

        return True
    except AssertionError as e:
        print(f"❌ Individual filters test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Individual filters test error: {e}")
        return False


def test_combined_pipeline_and_validation() -> bool:
    try:
        df = make_meta_df()
        spec = FilterSpec(
            age_range=(22, 30),
            league_in=["EPL"],
            continent_in=["Europe"],
            position_in=["FW", "MF"],
            season_in=["2023-2024"],
        )
        filtered = apply_filters(df, spec)
        # Expect p1 (FW, 24, EPL, 23-24) and p2 (MF, 29, EPL, 23-24)
        assert set(filtered["player_id"]) == {"p1", "p2"}

        # Validation: ok on full df
        issues_ok = validate_filters(df, spec)
        assert not issues_ok["missing_columns"] and not issues_ok["invalid_values"]

        # Validation: missing column (league)
        df_bad = df.drop(columns=["league"])  # simulate missing
        issues_bad = validate_filters(df_bad, FilterSpec(league_in=["EPL"]))
        assert "league" in issues_bad["missing_columns"], "Missing league should be reported"

        # Validation: invalid age range
        issues_age = validate_filters(df, FilterSpec(age_range=(30, 20)))
        assert "age_range: lo>hi" in issues_age["invalid_values"], "Invalid age range should be reported"
        return True
    except AssertionError as e:
        print(f"❌ Combined/validation test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Combined/validation test error: {e}")
        return False


def main():
    print("🚀 Filtering System Tests")
    print("=" * 60)

    tests = [
        ("Individual Filters", test_individual_filters),
        ("Combined & Validation", test_combined_pipeline_and_validation),
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
        print("🎉 All filtering tests passed!")
    else:
        print("❌ Some filtering tests failed. Check logs above.")


if __name__ == "__main__":
    main()
