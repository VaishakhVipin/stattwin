# Supported League IDs and Multi-League Player Retrieval

This document lists the core set of domestic league IDs bundled with StatTwin and explains how to fetch players from multiple leagues (e.g., Premier League + Bundesliga) for season-level similarity workflows.

## Core League IDs (Static Registry)

Europe (Major 1st Tier):
- 9 — Premier League (England)
- 13 — La Liga (Spain)
- 20 — Bundesliga (Germany)
- 11 — Serie A (Italy)
- 16 — Ligue 1 (France)

Europe (Other 1st Tier):
- 23 — Eredivisie (Netherlands)
- 24 — Primeira Liga (Portugal)
- 22 — Belgian Pro League (Belgium)
- 30 — Scottish Premiership (Scotland)
- 31 — Swiss Super League (Switzerland)
- 32 — Austrian Bundesliga (Austria)
- 33 — Danish Superliga (Denmark)
- 34 — Eliteserien (Norway)
- 35 — Allsvenskan (Sweden)
- 36 — Veikkausliiga (Finland)

Europe (2nd Tier):
- 46 — Championship (England)
- 47 — La Liga 2 (Spain)
- 48 — 2. Bundesliga (Germany)
- 49 — Serie B (Italy)
- 50 — Ligue 2 (France)

Americas:
- 26 — Major League Soccer (USA)
- 27 — Liga MX (Mexico)
- 28 — Brasileirão (Brazil)
- 29 — Primera División (Argentina)
- 41 — Liga BetPlay (Colombia)
- 40 — Primera División (Chile)
- 42 — Liga 1 (Peru)
- 43 — Canadian Premier League (Canada)

Africa:
- 44 — Egyptian Premier League (Egypt)
- 45 — Premier Division (South Africa)

Asia/Oceania:
- 25 — J1 League (Japan)
- 37 — K League 1 (South Korea)
- 38 — Chinese Super League (China)
- 39 — A-League (Australia)

Notes:
- These IDs come from `app/core/leagues.py` and can be extended at runtime via FBRef discovery (domestic leagues only).
- To list all currently registered leagues programmatically:

```python
from app.core.leagues import get_league_registry
reg = get_league_registry()
for li in reg.get_all_leagues():
    print(li.league_id, li.name, f"({li.country})")
```

## Getting Players From Multiple Leagues

FBRef returns season-level player aggregates per team using `/player-season-stats`. To build a cross-league dataset:

1) Enumerate teams for each league-season (we use `/matches` at league level and collect unique `home_team_id`/`away_team_id`).
2) For each team, fetch `/player-season-stats?team_id=...&league_id=...&season_id=...`.
3) Flatten the response into rows with identity columns and numeric stats.
4) Concatenate rows across leagues.

Example:

```python
from typing import Dict, List
import pandas as pd

from app.core.fbref_client import create_fbref_client

# Minimal flattener (adapt as needed)
def flatten_player_season(p: Dict, league_label: str, season_id: str) -> Dict:
    meta = (p.get("meta_data") or {})
    buckets = (p.get("stats") or {})
    base = (buckets.get("stats") or {})
    shooting = (buckets.get("shooting") or {})
    passing = (buckets.get("passing") or {})
    defense = (buckets.get("defense") or {})
    return {
        "player_id": meta.get("player_id"),
        "name": meta.get("player_name"),
        "position": base.get("positions"),
        "age": meta.get("age"),
        "league": league_label,
        "continent": "Europe",  # adjust if needed
        "season": season_id,
        "minutes": base.get("min"),
        "xg": base.get("xg"),
        "xa": passing.get("xa"),
        "key_passes": passing.get("key_passes"),
        "progressive_passes": passing.get("pass_prog") or base.get("passes_prog"),
        "shots": shooting.get("sh"),
        "shots_on_target": shooting.get("sot"),
        "passes_completed": passing.get("pass_cmp"),
        "passes_attempted": passing.get("pass_att"),
        "tackles": defense.get("tkl"),
        "interceptions": defense.get("int"),
    }

# Enumerate teams for a league-season via league-level matches
def list_teams_in_league(client, league_id: int, season_id: str) -> List[Dict[str, str]]:
    matches = client.get_matches(league_id=league_id, season_id=season_id)
    teams = {}
    for m in matches:
        for tid, tname in [
            (m.get("home_team_id"), m.get("home")),
            (m.get("away_team_id"), m.get("away")),
        ]:
            key = (tid or tname)
            if key and key not in teams:
                teams[key] = {"team_id": str(tid) if tid else None, "team_name": tname}
    return list(teams.values())

# Build dataset for one league-season
def build_league_dataset(client, league_id: int, season_id: str) -> pd.DataFrame:
    league_label = {
        9: "Premier League",
        20: "Bundesliga",
    }.get(league_id, str(league_id))
    rows: List[Dict] = []
    for t in list_teams_in_league(client, league_id, season_id):
        team_id = t.get("team_id") or t.get("team_name")
        if not team_id:
            continue
        players = client.get_player_season_stats(team_id=str(team_id), league_id=league_id, season_id=season_id)
        for p in players:
            r = flatten_player_season(p, league_label, season_id)
            if r.get("player_id"):
                rows.append(r)
    return pd.DataFrame(rows)

# Build multi-league dataset (e.g., EPL + Bundesliga)
def build_multi_league_dataset(league_ids: List[int], season_id: str) -> pd.DataFrame:
    client = create_fbref_client()
    frames = [build_league_dataset(client, lid, season_id) for lid in league_ids]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # Drop duplicates if players transferred within the season and appear twice
    if not df.empty and {"player_id", "league", "season"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["player_id", "league", "season"]).reset_index(drop=True)
    return df

# Example usage:
# df = build_multi_league_dataset([9, 20], "2023-2024")  # Premier League + Bundesliga
```

Once you have the combined DataFrame, run the preprocessing and similarity steps as usual. You can also filter to specific leagues before or after similarity:

```python
from app.algorithms.preprocessing import preprocess, PreprocessingConfig
from app.algorithms.similarity import similar_to_query, WeightConfig

processed, artifacts, report = preprocess(df, PreprocessingConfig(
    per90_cols=[c for c in [
        "shots", "shots_on_target", "passes_completed", "passes_attempted", "tackles", "interceptions"
    ] if c in df.columns]
))

result = similar_to_query(
    processed,
    query_id="<player_id>",
    top_k=10,
    weights=WeightConfig(position="FW"),
    restrict_to_query_positions=True,
    # Optional: limit candidates to these leagues
    filters={"league_in": ["Premier League", "Bundesliga"], "season_in": ["2023-2024"]},
    return_columns=["player_id", "name", "position", "league", "season"],
)
```

Tips:
- Respect API rate limits (1 request every 3 seconds). The client includes a limiter and on-disk caching.
- If you already cached one league, you can build the second league later and concatenate from disk to save time.
- Use `restrict_to_query_positions=True` to skip GKs/DFs when the query is a FW, etc., for faster comparisons.
