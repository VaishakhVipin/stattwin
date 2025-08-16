#!/usr/bin/env python3
"""
Test script for the StatTwin DataManager (data storage & caching).
Validates raw caching, processed JSON/Parquet storage, and cleanup logic.
"""

import sys
import time
from pathlib import Path
from datetime import timedelta
from tempfile import TemporaryDirectory

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from core.data_manager import DataManager, DataManagerConfig  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # type: ignore


def test_raw_cache() -> bool:
    print("🧪 Testing RAW cache...")
    try:
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "data"
            cfg = DataManagerConfig(base_dir=base_dir, namespace="testdm", default_ttl=timedelta(seconds=3600))
            dm = DataManager(cfg)

            endpoint = "/players"
            params = {"player_id": "92e7e919"}
            payload = {"ok": True, "id": params["player_id"]}

            # save_raw + load_raw
            p = dm.save_raw(endpoint, params, payload)
            print(f"   Saved raw -> {p}")
            loaded = dm.load_raw(endpoint, params, max_age=timedelta(days=1))
            assert loaded == payload, "Loaded payload mismatch"

            # get_or_fetch_raw should return cached without calling fetch_fn on second call
            calls = {"n": 0}

            def fetch_fn():
                calls["n"] += 1
                return {"ok": True, "fetched": True}

            # First: cached exists so fetch_fn should not be called
            data1 = dm.get_or_fetch_raw(endpoint, params, fetch_fn, max_age=timedelta(days=1))
            assert data1 == payload and calls["n"] == 0, "Cache hit should not fetch"

            # Force expiration -> should fetch
            data2 = dm.load_raw(endpoint, params, max_age=timedelta(seconds=0))
            assert data2 is None, "Expected expired cache"
            data3 = dm.get_or_fetch_raw(endpoint, params, fetch_fn, max_age=timedelta(seconds=0))
            assert data3.get("fetched") is True and calls["n"] == 1, "Expected fetch on miss"

            # Age check
            age = dm.get_cached_raw_age(endpoint, params)
            assert age is not None, "Expected cached age"
        return True
    except AssertionError as e:
        print(f"❌ RAW cache assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ RAW cache test failed: {e}")
        return False


def test_processed_json() -> bool:
    print("🧪 Testing processed JSON storage...")
    try:
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "data"
            dm = DataManager(DataManagerConfig(base_dir=base_dir, namespace="testdm"))

            name = "sample_dataset"
            data = {"a": 1, "b": [1, 2, 3]}
            p = dm.save_processed_json(name, data, version="v1")
            print(f"   Saved processed JSON -> {p}")
            loaded = dm.load_latest_processed_json(name, version="v1")
            assert loaded == data, "Processed JSON mismatch"
        return True
    except AssertionError as e:
        print(f"❌ Processed JSON assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Processed JSON test failed: {e}")
        return False


def test_processed_parquet() -> bool:
    print("🧪 Testing processed Parquet storage...")
    if pd is None:
        print("⚠️  pandas/pyarrow not available; skipping Parquet test")
        return True
    try:
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "data"
            dm = DataManager(DataManagerConfig(base_dir=base_dir, namespace="testdm"))

            name = "player_season_stats"
            df = pd.DataFrame({"id": [1, 2, 3], "val": [10.0, 20.5, 30.1]})
            p = dm.save_processed_parquet(name, df, version="2023-2024")
            print(f"   Saved processed Parquet -> {p}")
            df2 = dm.load_latest_processed_parquet(name, version="2023-2024")
            assert df2 is not None and df2.shape == df.shape, "Parquet read/write shape mismatch"
        return True
    except AssertionError as e:
        print(f"❌ Processed Parquet assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Processed Parquet test failed: {e}")
        return False


def test_cleanup() -> bool:
    print("🧪 Testing cleanup utilities...")
    try:
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "data"
            dm = DataManager(DataManagerConfig(base_dir=base_dir, namespace="testdm"))

            # Create rolling processed JSON files
            name = "rolling"
            for i in range(7):
                dm.save_processed_json(name, {"i": i})
                time.sleep(0.01)  # ensure different mtimes

            base = dm._processed_base(name)
            total_before = len(list(base.glob("*.json")))
            removed = dm.cleanup_processed_versions(name, keep_last=3, include_parquet=False, include_json=True)
            total_after = len(list(base.glob("*.json")))

            assert total_before == 7, f"Expected 7 files before, got {total_before}"
            assert removed == 4 and total_after == 3, f"Cleanup mismatch (removed={removed}, after={total_after})"

            # Raw cleanup (create fake old files)
            ep = "/teams"
            for i in range(3):
                dm.save_raw(ep, {"i": i}, {"ok": True})
            # Set older_than very small to remove none (fresh files)
            removed_raw = dm.cleanup_raw(older_than=timedelta(seconds=0))
            assert removed_raw == 0, "Should not remove fresh raw files"
        return True
    except AssertionError as e:
        print(f"❌ Cleanup assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Cleanup test failed: {e}")
        return False


def main():
    print("🚀 StatTwin DataManager Test")
    print("=" * 60)

    tests = [
        ("RAW Cache", test_raw_cache),
        ("Processed JSON", test_processed_json),
        ("Processed Parquet", test_processed_parquet),
        ("Cleanup", test_cleanup),
    ]

    results = []
    for name, fn in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        ok = fn()
        results.append((name, ok))

    print("\n" + "=" * 60)
    print("📊 DataManager Test Results:")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        print(f"  {name}: {'✅ PASSED' if ok else '❌ FAILED'}")
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All DataManager tests passed! Caching and storage are ready.")
    else:
        print("❌ Some DataManager tests failed. Check logs above.")


if __name__ == "__main__":
    main()
