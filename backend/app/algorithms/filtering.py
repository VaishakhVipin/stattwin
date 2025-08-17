from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


@dataclass
class FilterSpec:
    age_range: Optional[Tuple[float, float]] = None
    league_in: Optional[Iterable[str]] = None
    continent_in: Optional[Iterable[str]] = None
    position_in: Optional[Iterable[str]] = None
    season_in: Optional[Iterable[str]] = None


# ------------------------- Helpers -------------------------

def _ensure_iter(x: Optional[Iterable[str]]) -> List[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return list(x)
    return [str(x)]


def _missing_columns(df: pd.DataFrame, cols: Iterable[str]) -> List[str]:
    return [c for c in cols if c not in df.columns]


# ------------------------- Individual Filters -------------------------

def filter_by_age(df: pd.DataFrame, age_range: Tuple[float, float]) -> pd.DataFrame:
    if "age" not in df.columns:
        return df.copy()
    lo, hi = age_range
    return df[(df["age"] >= lo) & (df["age"] <= hi)]


def filter_by_league(df: pd.DataFrame, leagues: Iterable[str]) -> pd.DataFrame:
    if "league" not in df.columns:
        return df.copy()
    vals = _ensure_iter(leagues)
    if not vals:
        return df.copy()
    return df[df["league"].isin(vals)]


def filter_by_continent(df: pd.DataFrame, continents: Iterable[str]) -> pd.DataFrame:
    if "continent" not in df.columns:
        return df.copy()
    vals = _ensure_iter(continents)
    if not vals:
        return df.copy()
    return df[df["continent"].isin(vals)]


def filter_by_position(df: pd.DataFrame, positions: Iterable[str]) -> pd.DataFrame:
    if "position" not in df.columns:
        return df.copy()
    vals = _ensure_iter(positions)
    if not vals:
        return df.copy()
    return df[df["position"].isin(vals)]


def filter_by_season(df: pd.DataFrame, seasons: Iterable[str]) -> pd.DataFrame:
    if "season" not in df.columns:
        return df.copy()
    vals = _ensure_iter(seasons)
    if not vals:
        return df.copy()
    return df[df["season"].isin(vals)]


# ------------------------- Validation -------------------------

def validate_filters(df: pd.DataFrame, spec: FilterSpec) -> Dict[str, List[str]]:
    issues: Dict[str, List[str]] = {"missing_columns": [], "invalid_values": []}

    # Check required columns per filter
    colmap = {
        "age_range": ["age"],
        "league_in": ["league"],
        "continent_in": ["continent"],
        "position_in": ["position"],
        "season_in": ["season"],
    }
    for key, cols in colmap.items():
        val = getattr(spec, key)
        if val is not None:
            missing = _missing_columns(df, cols)
            if missing:
                issues["missing_columns"].extend(missing)

    # Basic sanity: age_range ordering
    if spec.age_range is not None:
        lo, hi = spec.age_range
        if lo > hi:
            issues["invalid_values"].append("age_range: lo>hi")

    # Remove duplicates in lists
    issues["missing_columns"] = sorted(list(set(issues["missing_columns"])))
    issues["invalid_values"] = sorted(list(set(issues["invalid_values"])))
    return issues


# ------------------------- Combined Pipeline -------------------------

def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    out = df.copy()
    # Age
    if spec.age_range is not None and "age" in out.columns:
        out = filter_by_age(out, spec.age_range)
    # League
    if spec.league_in is not None and "league" in out.columns:
        out = filter_by_league(out, spec.league_in)
    # Continent
    if spec.continent_in is not None and "continent" in out.columns:
        out = filter_by_continent(out, spec.continent_in)
    # Position
    if spec.position_in is not None and "position" in out.columns:
        out = filter_by_position(out, spec.position_in)
    # Season
    if spec.season_in is not None and "season" in out.columns:
        out = filter_by_season(out, spec.season_in)
    return out


def apply_filters_with_report(df: pd.DataFrame, spec: FilterSpec) -> tuple[pd.DataFrame, Dict[str, List[str]]]:
    issues = validate_filters(df, spec)
    return apply_filters(df, spec), issues
