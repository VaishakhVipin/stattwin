#!/usr/bin/env python3
"""
Tests for the Data Preprocessing Engine.
Validates cleaning, per-90 conversion, feature engineering, normalization, and validation.
"""

import sys
from typing import List
import numpy as np
import pandas as pd

from pathlib import Path

# Ensure the app directory is on sys.path for module resolution
app_path = Path(__file__).parent / "app"
if str(app_path) not in sys.path:
    sys.path.append(str(app_path))

try:
    from algorithms.preprocessing import (
        PreprocessingConfig,
        preprocess,
        clean_data,
    )
except ImportError:
    # Fallback: attempt to add backend root (when running from repo root)
    backend_root = Path(__file__).parent
    alt_app = backend_root / "app"
    if str(alt_app) not in sys.path:
        sys.path.append(str(alt_app))
    from algorithms.preprocessing import (
        PreprocessingConfig,
        preprocess,
        clean_data,
    )


def make_sample_df() -> pd.DataFrame:
    # Construct a small dataset with edge cases
    data = {
        "player_id": ["p1", "p2", "p3"],
        "name": ["A", "B", "C"],
        "position": ["FW", "MF", "DF"],
        "age": [24, 29, 21],
        "league": ["EPL", "EPL", "EPL"],
        "continent": ["Europe", "Europe", "Europe"],
        "season": ["2023-2024", "2023-2024", "2023-2024"],
        "minutes": [900, 0, 450],  # include a zero to test per90 safe divide
        # raw stats
        "shots": [10, 2, 1000],  # 1000 is an outlier candidate
        "shots_on_target": [5, 1, 100],
        "passes_completed": [50, 0, 30],
        "passes_attempted": [100, 0, 45],  # zero denominator row for ratios
        "tackles": [10, 4, 2],
        "interceptions": [8, 2, 1],
        "aerials_won": [3, 1, 0],
        "aerials_contested": [6, 1, 0],  # zero denominator -> ratio NaN
    }
    return pd.DataFrame(data)


def test_cleaning_and_outliers() -> bool:
    try:
        # Use a small numeric-only frame to guarantee IQR clipping
        df = pd.DataFrame({"shots": [1, 2, 3, 4, 100]})
        q1 = df["shots"].quantile(0.25)
        q3 = df["shots"].quantile(0.75)
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr if iqr > 0 else df["shots"].max()

        cfg = PreprocessingConfig()
        cleaned, report = clean_data(df, cfg)

        # Outlier clipped to <= upper bound
        assert cleaned["shots"].max() <= upper + 1e-9, "Outlier not clipped by IQR"
        assert isinstance(report, dict)
        return True
    except AssertionError as e:
        print(f"❌ Cleaning/outlier test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Cleaning/outlier test error: {e}")
        return False


def test_full_pipeline() -> bool:
    try:
        df = make_sample_df()
        # Limit per90 to real rate stats (avoid age_per90, etc.)
        per90_cols: List[str] = [
            "shots",
            "shots_on_target",
            "passes_completed",
            "passes_attempted",
            "tackles",
            "interceptions",
            "aerials_won",
            "aerials_contested",
        ]
        cfg = PreprocessingConfig(per90_cols=per90_cols)

        processed, artifacts, report = preprocess(df, cfg)

        # Columns created
        assert "shots_per90" in processed.columns, "Missing per-90 column"
        assert "pass_completion" in processed.columns, "Missing ratio feature"
        assert "def_actions" in processed.columns, "Missing engineered feature"

        # Per-90 value check for row p1: 10 shots over 900 minutes => 1.0 per90
        p1 = processed.loc[processed["player_id"] == "p1"].iloc[0]
        assert np.isfinite(p1["shots_per90"]) and abs(p1["shots_per90"] - 1.0) < 1e-6, "Incorrect per-90 calculation"

        # Ratio value check for pass_completion on p1: 50/100 * 100 = 50
        assert abs(p1["pass_completion"] - 50.0) < 1e-6, "Incorrect pass_completion"

        # Ratio should be NaN when denominator=0 (p2)
        p2 = processed.loc[processed["player_id"] == "p2"].iloc[0]
        assert pd.isna(p2["pass_completion"]), "Expected NaN for zero denominator"

        # Normalization artifacts
        z_cols = artifacts.normalized_columns
        assert any(c.endswith("_z") for c in z_cols), "No normalized columns produced"

        # Validation report should include missing counts for pass_completion (due to zero denom)
        missing = report.get("validation", {}).get("missing_counts", {})
        assert missing.get("pass_completion", 0) >= 1, "Validation missing_counts should flag ratio NaN"

        return True
    except AssertionError as e:
        print(f"❌ Full pipeline test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Full pipeline test error: {e}")
        return False


def main():
    print("🚀 Preprocessing Engine Tests")
    print("=" * 60)

    tests = [
        ("Cleaning & Outliers", test_cleaning_and_outliers),
        ("Full Pipeline", test_full_pipeline),
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
        print("🎉 All preprocessing tests passed!")
    else:
        print("❌ Some preprocessing tests failed. Check logs above.")


if __name__ == "__main__":
    main()
