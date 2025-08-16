"""
Data storage and caching utilities for StatTwin.

Features:
- Local file storage for raw FBRef responses
- Processed data storage (JSON/Parquet)
- Basic filesystem caching to avoid re-fetching
- Data versioning and cleanup

Usage example:
    dm = get_data_manager()
    # Cache raw response
    cached = dm.load_raw(endpoint="/players", params={"player_id": "92e7e919"}, max_age=timedelta(hours=12))
    if cached is None:
        data = client.get_players("92e7e919")
        dm.save_raw("/players", {"player_id": "92e7e919"}, data)

    # Save processed dataframe
    df = pd.DataFrame([...])
    dm.save_processed_parquet("player_season_stats", df, version="2023-2024")
"""
from __future__ import annotations

import json
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - optional at runtime if only raw JSON is used
    pd = None  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------- Helpers ----------------------

def _slug(text: str) -> str:
    safe = [c if c.isalnum() or c in ("-", "_") else "-" for c in text.strip()]
    s = "".join(safe)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-") or "unknown"


def _stable_key(endpoint: str, params: Optional[Dict[str, Any]]) -> str:
    """Build a stable cache key from endpoint string and params dict."""
    try:
        payload = {
            "endpoint": endpoint,
            "params": params or {},
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except Exception:
        # Fallback: string repr
        blob = f"{endpoint}|{str(params)}"
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()  # nosec - cache key only


@dataclass
class DataManagerConfig:
    base_dir: Path
    namespace: str = "fbref"
    default_ttl: timedelta = timedelta(hours=12)
    keep_last_versions: int = 5


class DataManager:
    """Filesystem-based data manager with raw/processed caches."""

    def __init__(self, config: Optional[DataManagerConfig] = None):
        if config is None:
            # Compute backend/data as the base folder
            # data_manager.py -> core -> app -> backend
            backend_root = Path(__file__).resolve().parents[2]
            base_dir = backend_root / "data"
            config = DataManagerConfig(base_dir=base_dir)
        self.config = config

        # Directories
        self.raw_dir = self.config.base_dir / "raw" / self.config.namespace
        self.processed_dir = self.config.base_dir / "processed" / self.config.namespace
        self.metadata_dir = self.config.base_dir / "metadata" / self.config.namespace

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------- RAW STORAGE ----------------------
    def _raw_dir_for(self, endpoint: str) -> Path:
        return self.raw_dir / _slug(endpoint).lstrip("/")

    def _raw_filename(self, key: str, version: Optional[str]) -> str:
        # Use microsecond precision to avoid filename collisions within the same second
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        if version:
            return f"{ts}_{key}_v{_slug(version)}.json"
        return f"{ts}_{key}.json"

    def save_raw(self, endpoint: str, params: Optional[Dict[str, Any]], data: Any, version: Optional[str] = None) -> Path:
        """Save raw JSON payload for an endpoint+params to disk."""
        target_dir = self._raw_dir_for(endpoint)
        target_dir.mkdir(parents=True, exist_ok=True)
        key = _stable_key(endpoint, params)
        path = target_dir / self._raw_filename(key, version)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _find_latest_raw(self, endpoint: str, params: Optional[Dict[str, Any]]) -> Optional[Path]:
        target_dir = self._raw_dir_for(endpoint)
        if not target_dir.exists():
            return None
        key = _stable_key(endpoint, params)
        # Find files containing the key
        candidates = sorted(target_dir.glob(f"*{key}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None

    def load_raw(self, endpoint: str, params: Optional[Dict[str, Any]], max_age: Optional[timedelta] = None) -> Optional[Any]:
        """Load most recent cached raw JSON if within max_age (or default ttl)."""
        path = self._find_latest_raw(endpoint, params)
        if path is None:
            return None
        # Use default TTL only when max_age is None. Respect zero/negative TTL.
        ttl = self.config.default_ttl if max_age is None else max_age
        # If caller explicitly requests <=0 TTL, always expire
        if ttl <= timedelta(0):
            return None
        age = datetime.utcnow() - datetime.utcfromtimestamp(path.stat().st_mtime)
        # Expire when age >= ttl
        if age >= ttl:
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_cached_raw_age(self, endpoint: str, params: Optional[Dict[str, Any]]) -> Optional[timedelta]:
        path = self._find_latest_raw(endpoint, params)
        if path is None:
            return None
        return datetime.utcnow() - datetime.utcfromtimestamp(path.stat().st_mtime)

    def get_or_fetch_raw(self, endpoint: str, params: Optional[Dict[str, Any]], fetch_fn: Callable[[], Any], max_age: Optional[timedelta] = None, version: Optional[str] = None) -> Any:
        """Return cached raw data if fresh; otherwise call fetch_fn(), cache, and return."""
        cached = self.load_raw(endpoint, params, max_age=max_age)
        if cached is not None:
            return cached
        data = fetch_fn()
        self.save_raw(endpoint, params, data, version=version)
        return data

    # ---------------------- PROCESSED STORAGE ----------------------
    def _processed_base(self, name: str) -> Path:
        return self.processed_dir / _slug(name)

    def _processed_file(self, name: str, version: Optional[str], ext: str) -> Path:
        base = self._processed_base(name)
        base.mkdir(parents=True, exist_ok=True)
        v = f"_v{_slug(version)}" if version else ""
        # Use microsecond precision to avoid overwriting within the same second
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
        return base / f"{_slug(name)}{v}_{ts}.{ext}"

    # JSON processed
    def save_processed_json(self, name: str, data: Any, version: Optional[str] = None) -> Path:
        path = self._processed_file(name, version, "json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def load_latest_processed_json(self, name: str, version: Optional[str] = None) -> Optional[Any]:
        base = self._processed_base(name)
        if not base.exists():
            return None
        pattern = f"{_slug(name)}{'_v' + _slug(version) if version else ''}_*.json"
        candidates = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        try:
            with candidates[0].open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    # Parquet processed
    def save_processed_parquet(self, name: str, df: Any, version: Optional[str] = None) -> Path:
        if pd is None:
            raise RuntimeError("pandas is required to save parquet data. Please install pandas and pyarrow.")
        path = self._processed_file(name, version, "parquet")
        try:
            df.to_parquet(path, index=False)  # requires pyarrow or fastparquet
        except Exception as e:
            raise RuntimeError("Failed to save parquet. Ensure 'pyarrow' (or 'fastparquet') is installed.") from e
        return path

    def load_latest_processed_parquet(self, name: str, version: Optional[str] = None) -> Optional[Any]:
        if pd is None:
            raise RuntimeError("pandas is required to load parquet data. Please install pandas and pyarrow.")
        base = self._processed_base(name)
        if not base.exists():
            return None
        pattern = f"{_slug(name)}{'_v' + _slug(version) if version else ''}_*.parquet"
        candidates = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        try:
            return pd.read_parquet(candidates[0])
        except Exception as e:
            raise RuntimeError("Failed to load parquet. Ensure 'pyarrow' (or 'fastparquet') is installed.") from e

    # ---------------------- CLEANUP ----------------------
    def cleanup_raw(self, older_than: timedelta) -> int:
        """Remove raw cache files older than the provided age. Returns count removed."""
        # If non-positive threshold, do not remove anything (treat as 0 = keep fresh files)
        if older_than <= timedelta(0):
            return 0
        count = 0
        cutoff = datetime.utcnow() - older_than
        if not self.raw_dir.exists():
            return 0
        for path in self.raw_dir.rglob("*.json"):
            mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    path.unlink()
                    count += 1
                except Exception:
                    pass
        return count

    def cleanup_processed_versions(self, name: str, keep_last: Optional[int] = None, include_parquet: bool = True, include_json: bool = True, version: Optional[str] = None) -> int:
        """Keep only the last N processed files for a dataset name. Returns count removed."""
        base = self._processed_base(name)
        if not base.exists():
            return 0
        keep = keep_last if keep_last is not None else self.config.keep_last_versions
        removed = 0
        patterns: List[str] = []
        suffix_v = f"_v{_slug(version)}" if version else ""
        if include_json:
            patterns.append(f"{_slug(name)}{suffix_v}_*.json")
        if include_parquet:
            patterns.append(f"{_slug(name)}{suffix_v}_*.parquet")
        for pattern in patterns:
            files = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[keep:]:
                try:
                    old.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed


# Singleton-style accessor
_dm_singleton: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    global _dm_singleton
    if _dm_singleton is None:
        _dm_singleton = DataManager()
    return _dm_singleton
