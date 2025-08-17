# Player Similarity: Features and Position-Specific Considerations

This document explains, in detail, what features are considered for player-to-player comparisons in the similarity engine, how they are engineered, normalized, and how weighting works by position. It also clarifies how positional restrictions affect the candidate set.

## Overview of the Pipeline

1. Input Dataset: Season-level player aggregates per league/season.
2. Cleaning: Missing value imputation, optional row-drop for excessive missingness, outlier clipping.
3. Per-90 Conversion: Selected rate stats are converted to per-90 using minutes.
4. Feature Engineering: Ratios and composite features derived from raw stats.
5. Normalization: Z-score (or robust) normalization to create *_z features.
6. Similarity: Cosine similarity (default) or Euclidean-based similarity, optionally weighted by position.
7. Candidate Restriction: Optionally restrict comparison to players sharing canonical positions (GK/DF/MF/FW).

The similarity engine operates primarily on the normalized columns (suffix `_z`).

## Data Cleaning and Preparation

- Missing Numerical Values: Imputed by median (default) or mean/zero per configuration.
- Missing Categorical Values: Mode imputation or row drop, depending on configuration.
- Outliers: IQR clipping (default) or winsorization at chosen quantiles.
- Per-90: For columns listed in `per90_cols` (e.g., shots, shots_on_target, passes_completed, passes_attempted, tackles, interceptions). Per-90 is computed as `(stat / minutes) * 90`, with safe division (0 and NaNs handled).
- Ratio Features (examples):
  - `sot_ratio = shots_on_target / shots`
  - `pass_completion = (passes_completed / passes_attempted) * 100`
  - `tackles_win_ratio = tackles_won / tackles` (if tackles_won present)
  - `aerial_win_ratio = aerials_won / aerials_contested` (if present)
- Composite Features:
  - `def_actions = tackles + interceptions`

After these steps, numerical columns (especially per-90 and engineered ratios) are standardized. For StandardScaler, columns are centered by mean and scaled by standard deviation; for RobustScaler, by median and IQR. Resulting normalized features are named with `_z` suffix and are the default inputs to the similarity engine.

## Position-Restricted Candidate Set

When `restrict_to_query_positions=True`, candidates are filtered to only those sharing at least one canonical position tag with the query: GK, DF, MF, FW. Positions are parsed from the `position` column, recognizing delimiters like commas or slashes (e.g., `DF,MF` or `MF/FW`). This step reduces noise and improves relevance.

## Position-Based Weighting

The similarity engine supports a `WeightConfig` which can boost or de-emphasize groups of features based on a specified position. If `WeightConfig.position` is set to one of `GK/DF/MF/FW`, a multiplicative boost is applied to features whose names contain certain keywords. The default groups are:

- Shooting-centric (boosted for FW):
  - keywords: shot, xg, goal, np_xg, sot
  - Typical features: shots_per90_z, shots_on_target_per90_z, xg_per90_z, g_per90_z (if present)

- Passing/Creation (boosted for MF):
  - keywords: pass, assit/assist, key_pass, prog/kp
  - Typical features: passes_completed_per90_z, key_passes_per90_z, progressive_passes_per90_z

- Defending (boosted for DF):
  - keywords: tackle, interception, clear, block, aerial, press
  - Typical features: tackles_per90_z, interceptions_per90_z, def_actions_per90_z (if composite normalized), aerials_won_per90_z

- Goalkeeping (boosted for GK):
  - keywords: save, psxg, stop, claim, sweep
  - Typical features: saves_per90_z, psxg_z, save_pct_z (if present)

The boost factor defaults to 1.5×, and unlisted features remain at base weight (1.0). Column-specific weights can alternatively be provided via `WeightConfig.column_weights`.

## Features Considered by Position (Typical)

Actual available features depend on the data returned by the source API for a league/season. Below is a guide to typical features used per position; the engine includes all numeric *_z columns it finds by default.

- For Forwards (FW):
  - shots_per90_z, shots_on_target_per90_z
  - xg_per90_z, np_xg_per90_z (if present)
  - key_passes_per90_z, progressive_passes_per90_z
  - touches_att_pen_area_per90_z (if present), carries into box (if present)

- For Midfielders (MF):
  - progressive_passes_per90_z, key_passes_per90_z
  - passes_completed_per90_z, pass_completion_z
  - xA_per90_z (if present), carries/progressive carries per90_z
  - defensive contribution (tackles_per90_z, interceptions_per90_z) where applicable

- For Defenders (DF):
  - tackles_per90_z, interceptions_per90_z, def_actions_per90_z
  - clearances_per90_z, blocks_per90_z (if present)
  - aerial_duels_won_per90_z and ratios (if present)
  - progressive_passes_per90_z for ball-playing profiles

- For Goalkeepers (GK):
  - saves_per90_z, save_pct_z
  - psxg_z (post-shot expected goals), claims/sweeps per90_z
  - passing metrics where relevant for distribution

Because the system automatically discovers available *_z features, it adapts to what the dataset contains. You can explicitly pass `feature_cols` to the similarity function for total control.

## Similarity Metric

- Cosine Similarity (default): Measures the cosine of the angle between vectors; robust to scale differences after normalization. We use row-normalization and a fast dot product for efficiency.
- Euclidean-based Similarity: Computes distances in weighted feature space, then converts to a bounded similarity score as `1 / (1 + distance)`.

## Handling Missing Values During Similarity

- Feature matrix uses `np.nan_to_num` to replace NaNs/infinities with 0 for similarity computation.
- This ensures players with missing values don’t break the calculation; however, more NaNs can reduce meaningful comparability.

## Practical Tips

- Restrict to positions: Use `restrict_to_query_positions=True` for relevance and performance.
- Weighting: Set `WeightConfig(position='FW'|'MF'|'DF'|'GK')` to emphasize position-relevant features.
- Custom features: Provide `feature_cols` to `similar_to_query` for a curated set of metrics.
- Multi-league datasets: Ensure consistent feature availability across leagues, or unionize and let NaN handling manage gaps.

## Example Usage Snippet

```
res = similar_to_query(
    df_processed,
    query_id=target_id,
    top_k=15,
    weights=WeightConfig(position='FW'),
    restrict_to_query_positions=True,
    return_columns=['player_id','name','position','league','season']
)
```

This will compare the target player against candidates in the same position group, with forward-centric features boosted, and return the top-15 most similar players.
