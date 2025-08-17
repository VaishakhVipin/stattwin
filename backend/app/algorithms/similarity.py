from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity
from sklearn.metrics import pairwise_distances

ArrayLike = Union[np.ndarray, pd.DataFrame]


# ----------------------------- Utilities -----------------------------

def _to_matrix(X: ArrayLike, dtype: np.dtype = np.float32) -> np.ndarray:
    if isinstance(X, pd.DataFrame):
        return X.values.astype(dtype, copy=False)
    return np.asarray(X, dtype=dtype)


def get_feature_columns(df: pd.DataFrame, suffix: str = "_z") -> List[str]:
    """Default feature selector: all numeric columns ending with given suffix."""
    cols = [c for c in df.columns if c.endswith(suffix)]
    # keep only numeric
    return [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]


# ----------------------------- Core Metrics -----------------------------

def cosine_sim_matrix(X: ArrayLike) -> np.ndarray:
    """Return cosine similarity matrix for rows of X."""
    M = _to_matrix(X)
    return sk_cosine_similarity(M)


def euclidean_dist_matrix(X: ArrayLike) -> np.ndarray:
    """Return euclidean distance matrix for rows of X (L2)."""
    M = _to_matrix(X)
    return pairwise_distances(M, metric="euclidean")


# ----------------------------- Weighting -----------------------------

@dataclass
class WeightConfig:
    # Either provide explicit per-column weights, or auto by position
    column_weights: Optional[Dict[str, float]] = None
    position: Optional[str] = None  # e.g., 'FW', 'MF', 'DF', 'GK'
    base_weight: float = 1.0
    boost: float = 1.6  # multiplicative boost for matched keyword groups
    deboost: float = 0.85  # multiplicative de-emphasis for non-relevant groups
    # FBRef-aligned keyword groups (match against normalized feature names)
    keywords_shooting: Tuple[str, ...] = (
        "shot", "sh_", "sot", "xg", "np_xg", "np_gls", "gls", "avg_sh", "npxg", "gca", "sca",
        "touch_opp_box", "opp_box",
    )
    keywords_passing: Tuple[str, ...] = (
        "pass_", "key_pass", "xa", "xag", "pass_prog", "progressive_pass", "pass_fthird", "pass_opp_box",
        "passes_into_box", "passes_final_third", "through_balls", "crosses", "cross_opp_box", "pass_completion",
        "pct_pass_cmp", "pass_cmp", "pass_att",
    )
    keywords_progression: Tuple[str, ...] = (
        "prog", "progress", "carry", "carries", "take_on", "drib", "pass_prog_rcvd", "pass_progressive_received",
    )
    keywords_box_presence: Tuple[str, ...] = (
        "opp_box", "fthird", "final_third", "touch_opp_box", "carries_opp_box", "touches_final_third",
    )
    keywords_defending: Tuple[str, ...] = (
        "tkl", "tackle", "int", "interception", "clear", "block", "aerial", "air_dual", "tkl_drb",
        "tkl_plus_int", "press",
    )
    keywords_goalkeeping: Tuple[str, ...] = (
        "save", "psxg", "stop", "claim", "sweep", "gk_", "ga", "cs", "save_pct",
    )


def _auto_position_weights(feature_cols: Sequence[str], cfg: WeightConfig) -> np.ndarray:
    pos = (cfg.position or "").upper()
    w = np.full(len(feature_cols), cfg.base_weight, dtype=np.float32)

    def contains_any(name: str, keywords: Tuple[str, ...]) -> bool:
        lname = name.lower()
        return any(k in lname for k in keywords)

    def boost_group(keywords: Tuple[str, ...]):
        for i, c in enumerate(feature_cols):
            if contains_any(c, keywords):
                w[i] *= cfg.boost

    def deboost_group(keywords: Tuple[str, ...]):
        for i, c in enumerate(feature_cols):
            if contains_any(c, keywords):
                w[i] *= cfg.deboost

    if pos == "FW":
        boost_group(cfg.keywords_shooting)
        boost_group(cfg.keywords_box_presence)
        boost_group(cfg.keywords_creation if hasattr(cfg, 'keywords_creation') else cfg.keywords_passing)
        # Progression helpful for FW link-up
        boost_group(cfg.keywords_progression)
        # De-emphasize pure defending
        deboost_group(cfg.keywords_defending)
    elif pos == "MF":
        boost_group(cfg.keywords_passing)
        boost_group(cfg.keywords_progression)
        boost_group(cfg.keywords_box_presence)
        # Slight de-emphasis of pure shooting volume
        deboost_group(cfg.keywords_shooting)
    elif pos == "DF":
        boost_group(cfg.keywords_defending)
        # Ball-playing defenders: progressive passing gets a smaller boost
        boost_group(cfg.keywords_progression)
        # De-emphasize shooting
        deboost_group(cfg.keywords_shooting)
    elif pos == "GK":
        boost_group(cfg.keywords_goalkeeping)
        # De-emphasize outfield stats
        deboost_group(cfg.keywords_shooting)
        deboost_group(cfg.keywords_passing)
        deboost_group(cfg.keywords_defending)
        deboost_group(cfg.keywords_progression)
    else:
        # Unknown: uniform base
        pass
    return w


def make_weights(feature_cols: Sequence[str], cfg: Optional[WeightConfig] = None) -> np.ndarray:
    if cfg is None:
        return np.ones(len(feature_cols), dtype=np.float32)
    if cfg.column_weights:
        return np.array([float(cfg.column_weights.get(c, cfg.base_weight)) for c in feature_cols], dtype=np.float32)
    return _auto_position_weights(feature_cols, cfg)


def apply_weights(X: np.ndarray, weights: np.ndarray) -> np.ndarray:
    if weights is None:
        return X
    return X * weights.astype(X.dtype)


# ----------------------------- Query Similarity -----------------------------

def _row_normalize(M: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    return M / (norms + eps)


def _prepare_feature_matrix(df: pd.DataFrame, feature_cols: Sequence[str], na_fill: float = 0.0, dtype: np.dtype = np.float32) -> np.ndarray:
    X = df.loc[:, list(feature_cols)].astype(dtype)
    # Replace NaNs in features (e.g., ratios when denom=0)
    return np.nan_to_num(X.values, nan=na_fill, posinf=na_fill, neginf=na_fill)


def _parse_positions(pos: Optional[str]) -> List[str]:
    if not isinstance(pos, str) or not pos:
        return []
    s = pos.upper()
    # split on commas, slashes and whitespace
    tokens = [t.strip() for part in s.replace("/", ",").split(",") for t in part.split() if t.strip()]
    # keep only canonical tags
    allowed = {"GK", "DF", "MF", "FW"}
    return [t for t in tokens if t in allowed]


def similar_to_query(
    df: pd.DataFrame,
    feature_cols: Optional[Sequence[str]] = None,
    *,
    query_index: Optional[int] = None,
    query_id_col: str = "player_id",
    query_id: Optional[str] = None,
    weights: Optional[WeightConfig] = None,
    metric: str = "cosine",
    top_k: int = 10,
    filters: Optional[Dict[str, Union[Tuple[float, float], Iterable[str]]]] = None,
    return_columns: Optional[Sequence[str]] = None,
    restrict_to_query_positions: bool = False,
) -> pd.DataFrame:
    """Compute top-k similar players to a query row in df.

    - feature_cols: columns to use; defaults to all *_z numeric columns
    - query specified by row index or by id using query_id_col
    - weights: WeightConfig for column or position-based emphasis
    - metric: 'cosine' (default) or 'euclidean' (converted to a similarity score 1/(1+d))
    - filters: optional constraints applied to candidate rows, e.g.:
        {
          'age_range': (20, 30),
          'league_in': ['EPL', 'La Liga'],
          'position_in': ['FW','MF'],
          'continent_in': ['Europe'],
          'season_in': ['2023-2024']
        }
    - restrict_to_query_positions: when True, only compare against players who share
      at least one canonical position (GK/DF/MF/FW) with the query row.
    - return_columns: additional columns to include in the result
    """
    if feature_cols is None:
        feature_cols = get_feature_columns(df)
    if not feature_cols:
        raise ValueError("No feature columns provided or found (expected *_z columns).")

    # Determine query row index
    if query_index is None:
        if query_id is None:
            raise ValueError("Provide query_index or query_id.")
        matches = df.index[df[query_id_col] == query_id]
        if len(matches) == 0:
            raise ValueError(f"query_id {query_id!r} not found in column {query_id_col!r}.")
        query_index = int(matches[0])

    # Build candidate mask via filters
    mask = np.ones(len(df), dtype=bool)

    # Optional: restrict by query positions
    if restrict_to_query_positions and "position" in df.columns:
        qpos = _parse_positions(str(df.iloc[query_index]["position"]))
        if qpos:
            pos_series = df["position"].fillna("").astype(str).str.upper()
            mask &= pos_series.apply(lambda s: any(p in s for p in qpos)).values

    if filters:
        # numeric range filters
        age_range = filters.get("age_range") if "age_range" in filters else None
        if age_range is not None and "age" in df.columns:
            lo, hi = age_range  # type: ignore[arg-type]
            mask &= (df["age"] >= lo) & (df["age"] <= hi)
        # categorical
        for key, col in (
            ("league_in", "league"),
            ("position_in", "position"),
            ("continent_in", "continent"),
            ("season_in", "season"),
        ):
            vals = filters.get(key) if filters and key in filters else None
            if vals is not None and col in df.columns:
                mask &= df[col].isin(list(vals))

    # Always include the query row, but we'll exclude it after scoring
    mask[query_index] = True

    # Slice candidates
    idx = np.where(mask)[0]
    df_cand = df.iloc[idx]

    # Prepare features and weights
    X = _prepare_feature_matrix(df_cand, feature_cols)
    w = make_weights(feature_cols, weights)
    Xw = apply_weights(X, w)

    # Query vector
    q_local = int(np.where(idx == query_index)[0][0])
    q = Xw[q_local:q_local + 1]

    if metric == "cosine":
        # Efficient query-to-matrix cosine: normalize rows and do dot product
        Xn = _row_normalize(Xw)
        qn = _row_normalize(q)
        sims = (Xn @ qn.T).ravel()
        score = sims
    elif metric == "euclidean":
        dists = np.linalg.norm(Xw - q, axis=1)
        score = 1.0 / (1.0 + dists)
    else:
        raise ValueError("metric must be 'cosine' or 'euclidean'")

    # Exclude the query itself
    score[q_local] = -np.inf

    # Top-k via argpartition for performance
    k = min(top_k, score.size - 1)
    if k <= 0:
        return pd.DataFrame(columns=["index", "score"])  # nothing to return
    part_idx = np.argpartition(-score, k)[:k]
    order = part_idx[np.argsort(-score[part_idx])]

    # Build result
    result_idx = idx[order]
    cols = ["score"]
    if return_columns is None:
        return_columns = [c for c in ("player_id", "name", "position", "league", "season") if c in df.columns]
    cols += list(return_columns)

    out = pd.DataFrame({"score": score[order]})
    for c in return_columns:
        out[c] = df.iloc[result_idx][c].values
    out.index = result_idx
    out.reset_index(names="index", inplace=True)
    return out


# ----------------------------- Batch Ranking -----------------------------

def rank_all_against_all(
    df: pd.DataFrame,
    feature_cols: Optional[Sequence[str]] = None,
    *,
    weights: Optional[WeightConfig] = None,
    metric: str = "cosine",
    top_k: int = 10,
    id_col: str = "player_id",
) -> Dict[Union[int, str], pd.DataFrame]:
    """For each row in df, return top-k similar rows.

    Returns a dict keyed by id (if present) or index -> result DataFrame as from similar_to_query.
    Note: This computes per-query similarity efficiently without forming a full NxN matrix.
    """
    if feature_cols is None:
        feature_cols = get_feature_columns(df)
    results: Dict[Union[int, str], pd.DataFrame] = {}
    for i in range(len(df)):
        qid = df.iloc[i][id_col] if id_col in df.columns else i
        res = similar_to_query(
            df,
            feature_cols=feature_cols,
            query_index=i,
            weights=weights,
            metric=metric,
            top_k=top_k,
        )
        results[qid] = res
    return results