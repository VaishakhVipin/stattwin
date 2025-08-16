from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler


# ------------------------ Config & Artifacts ------------------------

@dataclass
class RatioSpec:
    numerator: str
    denominator: str
    output: str
    multiplier: Optional[float] = None  # e.g., 100 for percentages


def _default_ratio_specs() -> List[RatioSpec]:
    return [
        RatioSpec("shots_on_target", "shots", "sot_ratio", None),
        RatioSpec("passes_completed", "passes_attempted", "pass_completion", 100.0),
        RatioSpec("tackles_won", "tackles", "tackles_win_ratio", None),
        RatioSpec("aerials_won", "aerials_contested", "aerial_win_ratio", None),
    ]


@dataclass
class PreprocessingConfig:
    # Identity/metadata columns to preserve untouched
    id_cols: List[str] = field(default_factory=lambda: [
        "player_id", "name", "position", "age", "league", "continent", "season"
    ])
    # Raw numeric columns to clean (missing/outliers). If empty, auto-detect numeric columns.
    numeric_cols: List[str] = field(default_factory=list)
    # Minutes column for per-90 conversion
    minutes_col: str = "minutes"
    # Columns to convert to per-90. If empty, uses numeric_cols (excluding minutes_col)
    per90_cols: List[str] = field(default_factory=list)
    # Ratio features to compute
    ratio_specs: List[RatioSpec] = field(default_factory=_default_ratio_specs)
    # Outlier handling method: 'iqr' or 'winsorize'
    outlier_method: str = "iqr"
    # Winsorize limits (used when outlier_method='winsorize') in quantiles
    winsor_limits: Tuple[float, float] = (0.01, 0.99)
    # Missing value strategy for numeric cols: 'median' | 'mean' | 'zero'
    missing_numeric: str = "median"
    # Missing value strategy for non-numeric cols: 'mode' | 'drop' | 'keep'
    missing_non_numeric: str = "mode"
    # Drop rows exceeding this fraction of missing values (0..1). None disables.
    dropna_row_threshold: Optional[float] = 0.6
    # Normalization
    use_robust_scaler: bool = False  # if True use RobustScaler, else StandardScaler (z-score)
    # Which columns to normalize. If empty, normalize per-90 + engineered numeric features
    normalize_cols: List[str] = field(default_factory=list)


@dataclass
class PreprocessingArtifacts:
    scaler: Optional[Any]
    normalized_columns: List[str]
    per90_columns: List[str]
    ratio_columns: List[str]


# ------------------------ Helpers ------------------------

def _safe_divide(a: pd.Series, b: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        res = a.astype(float) / b.replace({0: np.nan}).astype(float)
    return res.replace([np.inf, -np.inf], np.nan)


def _numeric_columns(df: pd.DataFrame, exclude: Iterable[str] = ()) -> List[str]:
    cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in cols if c not in set(exclude)]


# ------------------------ Cleaning ------------------------

def clean_data(df: pd.DataFrame, cfg: PreprocessingConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    report: Dict[str, Any] = {"dropped_rows": 0, "imputed_numeric": {}, "imputed_non_numeric": []}
    out = df.copy()

    # Optionally drop rows with too many missing values
    if cfg.dropna_row_threshold is not None:
        frac_missing = out.isna().mean(axis=1)
        to_drop = frac_missing > cfg.dropna_row_threshold
        report["dropped_rows"] = int(to_drop.sum())
        if report["dropped_rows"]:
            out = out.loc[~to_drop].copy()

    # Determine numeric cols
    numeric_cols = cfg.numeric_cols or _numeric_columns(out, exclude=[cfg.minutes_col])

    # Impute numeric missing
    for col in numeric_cols:
        if col not in out.columns:
            continue
        if out[col].isna().any():
            if cfg.missing_numeric == "median":
                val = out[col].median()
            elif cfg.missing_numeric == "mean":
                val = out[col].mean()
            elif cfg.missing_numeric == "zero":
                val = 0.0
            else:
                val = out[col].median()
            out[col] = out[col].fillna(val)
            report["imputed_numeric"][col] = val

    # Impute non-numeric missing
    if cfg.missing_non_numeric in ("mode", "drop"):
        non_num_cols = [c for c in out.columns if c not in numeric_cols]
        for col in non_num_cols:
            if out[col].isna().any():
                if cfg.missing_non_numeric == "mode":
                    mode_val = out[col].mode(dropna=True)
                    if len(mode_val) > 0:
                        out[col] = out[col].fillna(mode_val.iloc[0])
                        report["imputed_non_numeric"].append(col)
                elif cfg.missing_non_numeric == "drop":
                    # drop rows where this col is missing
                    before = len(out)
                    out = out.loc[~out[col].isna()].copy()
                    report["dropped_rows"] += (before - len(out))

    # Outlier handling for numeric columns
    if cfg.outlier_method == "iqr":
        for col in numeric_cols:
            if col not in out.columns:
                continue
            q1 = out[col].quantile(0.25)
            q3 = out[col].quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr) or iqr == 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            out[col] = out[col].clip(lower, upper)
    elif cfg.outlier_method == "winsorize":
        lo, hi = cfg.winsor_limits
        for col in numeric_cols:
            if col not in out.columns:
                continue
            lower = out[col].quantile(lo)
            upper = out[col].quantile(hi)
            out[col] = out[col].clip(lower, upper)

    report["numeric_cols"] = numeric_cols
    return out, report


# ------------------------ Per-90 Conversion ------------------------

def per90(df: pd.DataFrame, cfg: PreprocessingConfig) -> Tuple[pd.DataFrame, List[str]]:
    out = df.copy()
    if cfg.minutes_col not in out.columns:
        return out, []
    per_cols = cfg.per90_cols or [c for c in (cfg.numeric_cols or _numeric_columns(out)) if c != cfg.minutes_col]
    created: List[str] = []
    mins = out[cfg.minutes_col].replace({0: np.nan})
    for col in per_cols:
        if col not in out.columns:
            continue
        new_col = f"{col}_per90"
        out[new_col] = _safe_divide(out[col], mins) * 90.0
        created.append(new_col)
    return out, created


# ------------------------ Feature Engineering ------------------------

def engineer_features(df: pd.DataFrame, cfg: PreprocessingConfig) -> Tuple[pd.DataFrame, List[str]]:
    out = df.copy()
    created: List[str] = []

    # Ratios
    for spec in cfg.ratio_specs:
        if spec.numerator in out.columns and spec.denominator in out.columns:
            val = _safe_divide(out[spec.numerator], out[spec.denominator])
            if spec.multiplier is not None:
                val = val * float(spec.multiplier)
            out[spec.output] = val
            created.append(spec.output)

    # Example combined features (can be expanded based on dataset)
    # Defensive actions: tackles + interceptions if available
    if "tackles" in out.columns and "interceptions" in out.columns:
        out["def_actions"] = out["tackles"].astype(float) + out["interceptions"].astype(float)
        created.append("def_actions")

    return out, created


# ------------------------ Normalization ------------------------

def normalize(df: pd.DataFrame, cfg: PreprocessingConfig, cols: Optional[Sequence[str]] = None) -> Tuple[pd.DataFrame, List[str], Any]:
    out = df.copy()
    target_cols = list(cols) if cols is not None else (cfg.normalize_cols or [])
    if not target_cols:
        # default: normalize all numeric engineered/per90 columns (exclude id/meta and minutes)
        numeric = _numeric_columns(out, exclude=cfg.id_cols + [cfg.minutes_col])
        target_cols = [c for c in numeric if c.endswith("_per90") or c in numeric]

    if not target_cols:
        return out, [], None

    scaler = RobustScaler() if cfg.use_robust_scaler else StandardScaler()

    # Create mask of NaNs to restore after scaling
    mask = out[target_cols].isna()
    X = out[target_cols].astype(float)
    # Impute column-wise for scaler fitting (mean for StandardScaler, median for RobustScaler)
    if isinstance(scaler, RobustScaler):
        fill_vals = X.median()
    else:
        fill_vals = X.mean()
    X_filled = X.fillna(fill_vals)

    transformed = scaler.fit_transform(X_filled.values)

    z_cols: List[str] = []
    for i, c in enumerate(target_cols):
        zc = f"{c}_z"
        col_vals = transformed[:, i]
        # Restore NaNs where original was NaN
        col_series = pd.Series(col_vals, index=out.index)
        col_series[mask[c]] = np.nan
        out[zc] = col_series.values
        z_cols.append(zc)
    return out, z_cols, scaler


# ------------------------ Validation ------------------------

def validate(df: pd.DataFrame, cfg: PreprocessingConfig) -> Dict[str, Any]:
    issues: Dict[str, Any] = {}

    # Minutes should be non-negative
    if cfg.minutes_col in df.columns:
        invalid_minutes = int((df[cfg.minutes_col] < 0).sum())
        if invalid_minutes:
            issues["invalid_minutes"] = invalid_minutes

    # Percentages (if features present) should be in [0, 100]
    for col in df.columns:
        if col.endswith("_pct") or col in {"pass_completion"}:  # example percentage-like columns
            below0 = int((df[col] < 0).sum())
            above100 = int((df[col] > 100).sum())
            if below0 or above100:
                issues[f"out_of_range_{col}"] = {"lt0": below0, "gt100": above100}

    # Missingness report
    miss = df.isna().sum()
    issues["missing_counts"] = miss[miss > 0].to_dict()

    return issues


# ------------------------ Orchestrated Pipeline ------------------------

def preprocess(df: pd.DataFrame, cfg: Optional[PreprocessingConfig] = None) -> Tuple[pd.DataFrame, PreprocessingArtifacts, Dict[str, Any]]:
    """Run the full preprocessing pipeline on a DataFrame.

    Steps:
    - Clean (missing values, outliers)
    - Per-90 conversion
    - Feature engineering (ratios, composites)
    - Normalization (z-score or robust)
    - Validation report
    """
    cfg = cfg or PreprocessingConfig()

    cleaned, clean_report = clean_data(df, cfg)
    with_per90, per90_cols = per90(cleaned, cfg)
    engineered, ratio_cols = engineer_features(with_per90, cfg)
    normalized, z_cols, scaler = normalize(engineered, cfg)

    artifacts = PreprocessingArtifacts(
        scaler=scaler,
        normalized_columns=z_cols,
        per90_columns=per90_cols,
        ratio_columns=ratio_cols,
    )

    validation_report = validate(normalized, cfg)
    report = {"cleaning": clean_report, "validation": validation_report}

    return normalized, artifacts, report
