# Player Similarity in StatTwin

This document explains how StatTwin computes player similarity and how we efficiently limit comparisons to relevant players by position.

## Overview

StatTwin turns each player-season into a numeric feature vector and computes similarity between players using either cosine similarity (default) or a Euclidean-based score. The pipeline:

1. Build dataset (e.g., via FBRef player-season-stats per team within a league-season)
2. Preprocess to create normalized features:
   - Clean missing/outliers
   - Per-90 conversions for rate stats
   - Ratio/engineered features (e.g., pass completion, SOT ratio)
   - Normalize (z-score or robust) -> columns suffixed with `_z`
3. Similarity scoring between a query player and candidate players

## Features Used

- The similarity engine automatically uses all numeric columns ending with `_z` (normalized features) as the feature vector unless explicit `feature_cols` are supplied.
- Typical inputs include per-90 versions of shots, SOT, passes, tackles, interceptions, xG, xA, key passes, progressive passes, etc.

## Similarity Metrics

- Cosine similarity (default): dot product of row-normalized feature vectors in [-1, 1]. Higher is more similar.
- Euclidean-based score: convert L2 distance d to a similarity 1/(1 + d) in (0, 1].

## Weighting

Optionally emphasize feature groups using `WeightConfig`:
- Explicit column weights: map of `{feature_name: weight}`
- Position-based weighting: set `position='FW'|'MF'|'DF'|'GK'` to boost features whose names contain certain keywords (e.g., shooting for FW, passing for MF, defending for DF, goalkeeping for GK).

## Position-Restricted Candidate Set (Speed-up)

To avoid comparing a forward against goalkeepers/center backs unnecessarily, we restrict the candidate pool to players who share at least one canonical position tag with the query.

- Canonical tags: `GK`, `DF`, `MF`, `FW`.
- Query positions are parsed from the `position` column (comma, slash, or space-separated).
- When enabled, only rows whose `position` includes at least one of the query's tags are considered.

Usage:

```python
from algorithms.similarity import similar_to_query, WeightConfig

res = similar_to_query(
    df,
    query_id="92e7e919",  # example player_id
    top_k=10,
    weights=WeightConfig(position="FW"),
    restrict_to_query_positions=True,
    return_columns=["player_id", "name", "position", "league", "season"],
)
```

Notes:
- If the query has no recognizable position tags, the restriction is skipped.
- You can still pass additional filters (age range, league/season, etc.).

## API

Key functions in `app/algorithms/similarity.py`:
- `get_feature_columns(df)`: selects `*_z` columns as features.
- `similar_to_query(...)`: computes top-k most similar players to a query row by id or index.
  - Important parameters: `feature_cols`, `query_id`, `weights`, `metric`, `top_k`, `filters`, `restrict_to_query_positions`, `return_columns`.
- `rank_all_against_all(...)`: convenience to compute top-k neighbors for each row.

## Practical Tips

- Ensure preprocessing produced `_z` columns; otherwise pass explicit `feature_cols`.
- Use `restrict_to_query_positions=True` to speed up and improve relevance.
- Set `top_k` relative to your pool size; when heavily filtered (e.g., by position + league), smaller values are sufficient.
- Consider `WeightConfig(position=...)` to tailor relevance by role.
