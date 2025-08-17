#!/usr/bin/env python3
"""
Live E2E using FBRef API without match-level dependency:
- Enumerate teams via league matches
- For each team, fetch player-season-stats (aggregate season level)
- Build player dataset, preprocess, filter, and run similarity for a target player by id or name
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure the app directory is on sys.path for module resolution
app_path = Path(__file__).parent / "app"
if str(app_path) not in sys.path:
    sys.path.append(str(app_path))

from core.fbref_client import create_fbref_client  # type: ignore
from algorithms.preprocessing import PreprocessingConfig, preprocess  # type: ignore
from algorithms.similarity import similar_to_query, WeightConfig  # type: ignore
from algorithms.filtering import FilterSpec, apply_filters  # type: ignore

# Tester-local defaults so you don't need to export env vars in the shell
DEFAULTS = {
    "TEST_LEAGUE_ID": 32,
    "TEST_SEASON_ID": "2021-22",
    "TEST_TARGET_NAME": "Darwin Núñez",
    # Robust enumeration with reliable fallback season for listing
    "ENUMERATION_ORDER": "team-season-stats,season-details,standings,matches,manual",
    "ENUMERATION_FALLBACK_SEASON_ID": "2022-23",
    # Network/resilience knobs
    "RATE_LIMIT_SECONDS": 6.0,
    "TIMEOUT_SECONDS": 20.0,
    "RETRY_TOTAL": 3,
    "RETRY_BACKOFF": 1.0,
}


def _to_float(x: object) -> Optional[float]:
    """Best-effort conversion of FBRef numeric-like values to float (handles '+0.40', '-0.01')."""
    if x is None:
        return None
    if isinstance(x, (int, float, np.number)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        # Remove leading '+' and any surrounding spaces
        if s.startswith("+"):
            s = s[1:]
        # Replace commas and percentage signs if present (rare)
        s = s.replace(",", "").replace("%", "")
        try:
            return float(s)
        except Exception:
            return None
    return None


def _flatten_player_season(p: Dict[str, any], league_id: int, season_id: str) -> Dict[str, object]:
    """Flatten a single player season record from FBRef into our schema, extracting a richer set of stats."""
    meta = p.get("meta_data", {}) or {}
    buckets = p.get("stats", {}) or {}
    base = buckets.get("stats", {}) or {}
    shooting = buckets.get("shooting", {}) or {}
    passing = buckets.get("passing", {}) or {}
    passing_types = buckets.get("passing_types", {}) or {}
    defense = buckets.get("defense", {}) or {}
    possession = buckets.get("possession", {}) or {}
    gca = buckets.get("gca", {}) or {}
    playingtime = buckets.get("playingtime", {}) or {}
    keepers = buckets.get("keepers", {}) or {}
    keepers_adv = buckets.get("keepersadv", {}) or {}
    misc = buckets.get("misc", {}) or {}

    player_id = meta.get("player_id") or p.get("player_id")
    name = meta.get("player_name") or p.get("player_name")

    # Best-effort club and country extraction from payloads
    club = (
        meta.get("team_name")
        or base.get("team")
        or p.get("team_name")
        or p.get("team")
    )
    country = (
        meta.get("country")
        or meta.get("nationality")
        or meta.get("player_country_code")
        or base.get("nationality")
        or p.get("country")
        or p.get("nationality")
    )

    row: Dict[str, object] = {
        # Identity/meta
        "player_id": player_id,
        "name": name,
        "position": base.get("positions") or meta.get("positions"),
        "age": meta.get("age"),
        "league": "Premier League" if league_id == 9 else str(league_id),
        "continent": "Europe",
        "season": season_id,
        "club": club,
        "country": country,
        # Core volume & contributions
        "minutes": base.get("min"),
        "matches_played": base.get("matches_played"),
        "starts": base.get("starts"),
        "goals": base.get("gls"),
        "assists": base.get("ast"),
        "non_pen_goals": base.get("non_pen_gls"),
        "xg": base.get("xg"),
        "np_xg": base.get("non_pen_xg"),
        "xa": passing.get("xa"),
        "xag": base.get("xag") or passing.get("xag"),
        # Shooting
        "shots": shooting.get("sh"),
        "shots_on_target": shooting.get("sot"),
        "gls_xg_diff": shooting.get("gls_xg_diff"),
        "np_gls_xg_diff": shooting.get("non_pen_gls_xg_diff"),
        "avg_shot_distance": shooting.get("avg_sh_dist"),
        # Passing totals & creation
        "passes_completed": passing.get("pass_cmp"),
        "passes_attempted": passing.get("pass_att"),
        "pass_completion_pct": passing.get("pct_pass_cmp"),
        "key_passes": passing.get("key_passes"),
        "progressive_passes": passing.get("pass_prog") or base.get("passes_prog"),
        "progressive_pass_distance": passing.get("pass_prog_ttl_dist"),
        "passes_final_third": passing.get("pass_fthird"),
        "passes_into_box": passing.get("pass_opp_box"),
        "crosses_into_box": passing.get("cross_opp_box"),
        "crosses": passing_types.get("crosses"),
        "through_balls": passing_types.get("through_balls"),
        # Shot-creating / goal-creating actions
        "sca": gca.get("ttl_sca"),
        "gca": gca.get("gca"),
        # Defending
        "tackles": defense.get("tkl"),
        "tackles_won": defense.get("tkl_won"),
        "tackles_vs_dribbles": defense.get("tkl_drb"),
        "tackles_vs_dribbles_att": defense.get("tkl_drb_att"),
        "interceptions": defense.get("int"),
        "blocks": defense.get("blocks"),
        "clearances": defense.get("clearances"),
        "tkl_plus_int": defense.get("tkl_plus_int"),
        "defensive_errors": defense.get("def_error"),
        # Possession & carrying
        "touches": possession.get("touches"),
        "touches_def_box": possession.get("touch_def_box"),
        "touches_def_third": possession.get("touch_def_third"),
        "touches_mid_third": possession.get("touch_mid_third"),
        "touches_final_third": possession.get("touch_fthird"),
        "touches_opp_box": possession.get("touch_opp_box"),
        "take_on_att": possession.get("take_on_att"),
        "take_on_suc": possession.get("take_on_suc"),
        "take_on_suc_pct": possession.get("pct_take_on_suc"),
        "carries": possession.get("carries"),
        "carry_total_distance": possession.get("ttl_carries_dist"),
        "carry_progressive_distance": possession.get("ttl_carries_prog_dist"),
        "carries_final_third": possession.get("carries_fthird"),
        "carries_opp_box": possession.get("carries_opp_box"),
        "pass_received": possession.get("pass_recvd"),
        "pass_progressive_received": possession.get("pass_prog_rcvd"),
        # Playing time context (coerce strings)
        "pct_squad_minutes": _to_float(playingtime.get("pct_squad_min")),
        "per90_plus_minus": _to_float(playingtime.get("per90_plus_minus")),
        "per90_on_off": _to_float(playingtime.get("per90_on_off")),
        "per90_x_plus_minus": _to_float(playingtime.get("per90_x_plus_minus")),
        "per90_x_on_off": _to_float(playingtime.get("per90_x_on_off")),
        # Keeper stats (when available)
        "saves": keepers.get("saves") or keepers_adv.get("ttl_saves"),
        "save_pct": keepers.get("save_pct"),
        "clean_sheets": keepers.get("clean_sheets"),
        "psxg": keepers_adv.get("ttl_psxg") or keepers.get("psxg"),
        "psxg_per_sot": keepers_adv.get("psxg_per_sot"),
        # Misc
        "fouls_committed": misc.get("fls_com"),
        "fouls_drawn": misc.get("fls_drawn"),
        "offsides": misc.get("offside"),
        "penalties_won": misc.get("pk_won"),
        "penalties_conceded": misc.get("pk_conceded"),
        "own_goals": misc.get("og"),
        "ball_recoveries": misc.get("ball_recov"),
        "aerials_won": misc.get("air_dual_won"),
        "aerials_lost": misc.get("air_dual_lost"),
        "aerial_win_pct": misc.get("pct_air_dual_won"),
    }
    return row


def build_league_season_player_dataset(client, league_id: int, season_id: str) -> pd.DataFrame:
    teams = client.list_teams_in_league(league_id, season_id)
    rows: List[Dict] = []
    failed_teams: List[str] = []
    for t in teams:
        team_id = t.get("team_id") or t.get("id") or t.get("team") or t.get("team_name")
        if not team_id:
            continue
        try:
            ps = client.get_player_season_stats(team_id=str(team_id), league_id=league_id, season_id=season_id)
        except Exception:
            ps = []
        if not ps:
            failed_teams.append(str(team_id))
            continue
        for p in ps:
            try:
                row = _flatten_player_season(p, league_id, season_id)
                if row.get("player_id") and row.get("name"):
                    rows.append(row)
            except Exception:
                continue
    df = pd.DataFrame(rows)
    if df.empty:
        # Fallback team enumeration via league-season-details
        alt_teams = client.list_teams_from_season(league_id, season_id)
        for t in alt_teams:
            team_id = t.get("team_id") or t.get("id") or t.get("team") or t.get("team_name")
            if not team_id:
                continue
            if str(team_id) in failed_teams:
                # We already tried and got none; still attempt once via fallback context
                pass
            try:
                ps = client.get_player_season_stats(team_id=str(team_id), league_id=league_id, season_id=season_id)
            except Exception:
                ps = []
            for p in ps:
                try:
                    row = _flatten_player_season(p, league_id, season_id)
                    if row.get("player_id") and row.get("name"):
                        rows.append(row)
                except Exception:
                    continue
        df = pd.DataFrame(rows)
    # Drop duplicates if any (same player appearing twice unexpectedly)
    if not df.empty and "player_id" in df.columns:
        df = df.drop_duplicates(subset=["player_id", "season"], keep="first").reset_index(drop=True)
    return df


def find_player_season_in_team_by_name(
    client,
    *,
    team_id: str,
    league_id: int,
    season_id: str,
    target_player_name: Optional[str] = None,
    target_player_id: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """Retrieve player's season from a specific team quickly and return flattened row."""
    ps = client.get_player_season_stats(team_id=str(team_id), league_id=league_id, season_id=season_id)
    tname_lc = target_player_name.lower() if isinstance(target_player_name, str) else None
    for p in ps:
        meta = (p.get("meta_data", {}) or {})
        pid = meta.get("player_id") or p.get("player_id")
        pname = meta.get("player_name") or p.get("player_name")
        if target_player_id and pid == target_player_id:
            return _flatten_player_season(p, league_id, season_id)
        if tname_lc and isinstance(pname, str) and pname.lower() == tname_lc:
            return _flatten_player_season(p, league_id, season_id)
    return None


def find_player_season_in_league_by_name(
    client,
    *,
    league_id: int,
    season_id: str,
    target_player_name: Optional[str] = None,
    target_player_id: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """Search the target player across teams in a specific league/season and return a flattened season row.
    This performs a team-by-team scan using player-season-stats and stops at first match.
    """
    if not target_player_name and not target_player_id:
        return None
    teams = client.list_teams_in_league(league_id, season_id)
    tname_lc = target_player_name.lower() if isinstance(target_player_name, str) else None
    for t in teams:
        team_id = t.get("team_id") or t.get("id") or t.get("team") or t.get("team_name")
        if not team_id:
            continue
        ps = client.get_player_season_stats(team_id=str(team_id), league_id=league_id, season_id=season_id)
        for p in ps:
            meta = (p.get("meta_data", {}) or {})
            pid = meta.get("player_id") or p.get("player_id")
            pname = meta.get("player_name") or p.get("player_name")
            if target_player_id and pid == target_player_id:
                return _flatten_player_season(p, league_id, season_id)
            if tname_lc and isinstance(pname, str) and pname.lower() == tname_lc:
                return _flatten_player_season(p, league_id, season_id)
    return None


def run_fbref_end_to_end_league(
    *,
    league_id: int,
    season_id: str,
    target_player_id: Optional[str] = None,
    target_player_name: Optional[str] = None,
    position_weight: Optional[str] = None,
    top_k: int = 10,
    # Optional separate source for the target player (cross-league comparisons)
    target_source_league_id: Optional[int] = None,
    target_source_season_id: Optional[str] = None,
    target_source_team_id: Optional[str] = None,
    client: Optional[object] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if client is None:
        # Build a client with tester-provided settings (falls back to env/defaults inside the factory)
        client = create_fbref_client()
    df_raw = build_league_season_player_dataset(client, league_id, season_id)
    if df_raw.empty:
        # Report actual client settings to help troubleshoot
        order = getattr(client, "enumeration_order", None) or "matches,season-details,standings,manual"
        rls = getattr(getattr(client, "rate_limiter", None), "min_interval", None)
        to = getattr(client, "request_timeout", None)
        manual = os.getenv("FBREF_TEAM_IDS", "")
        raise RuntimeError(
            "Empty dataset for league/season; upstream API likely unavailable or enumerations failed.\n"
            f"Hints: Try ENUMERATION_ORDER=standings,season-details,matches,manual; RATE_LIMIT_SECONDS=6; or provide FBREF_TEAM_IDS to bypass enumeration.\n"
            f"Current settings -> ENUM_ORDER='{order}', RATE_LIMIT='{rls}', TIMEOUT='{to}', TEAM_IDS='{manual}'"
        )

    print(f"[info] Built raw dataset: rows={len(df_raw)}, cols={len(df_raw.columns)}")

    # If target not in this league dataset and separate source is provided, attempt to fetch
    def _main_league_value(lid: int) -> str:
        return "Premier League" if lid == 9 else str(lid)

    found_in_main: bool = False
    qid: Optional[str] = None
    if target_player_id is not None and (df_raw["player_id"] == target_player_id).any():
        found_in_main = True
        qid = target_player_id
    elif target_player_name is not None and (df_raw["name"].astype(str).str.lower() == target_player_name.lower()).any():
        found_in_main = True
        qid = df_raw.loc[df_raw["name"].astype(str).str.lower() == target_player_name.lower(), "player_id"].iloc[0]

    if not found_in_main and (target_source_league_id and target_source_season_id):
        extra: Optional[Dict[str, object]] = None
        if target_source_team_id:
            extra = find_player_season_in_team_by_name(
                client,
                team_id=target_source_team_id,
                league_id=target_source_league_id,
                season_id=target_source_season_id,
                target_player_name=target_player_name,
                target_player_id=target_player_id,
            )
        if extra is None:
            extra = find_player_season_in_league_by_name(
                client,
                league_id=target_source_league_id,
                season_id=target_source_season_id,
                target_player_name=target_player_name,
                target_player_id=target_player_id,
            )
        if extra is not None:
            print(
                f"[info] Appending cross-league target from league={extra.get('league')} season={extra.get('season')}"
            )
            df_raw = pd.concat([df_raw, pd.DataFrame([extra])], ignore_index=True)
            qid = str(extra.get("player_id")) if extra.get("player_id") is not None else None
        else:
            print("[warn] Cross-league target not found; proceeding without it.")

    # Preprocess (disable aggressive row dropping to avoid empty-after-clean)
    per90_cols_candidates = [
        # shooting
        "shots", "shots_on_target",
        # passing/creation
        "passes_completed", "passes_attempted", "key_passes", "progressive_passes",
        "passes_into_box", "passes_final_third", "crosses", "through_balls",
        # defending
        "tackles", "tackles_won", "interceptions", "blocks", "clearances",
        # carrying/possession
        "touches", "take_on_att", "take_on_suc", "carries", "carries_final_third",
        "carries_opp_box", "pass_received", "pass_progressive_received",
        # gca/sca are already counts; include per90 as well
        "sca", "gca",
        # goalkeeper volumes
        "saves",
    ]
    per90_cols = [c for c in per90_cols_candidates if c in df_raw.columns]
    cfg = PreprocessingConfig(per90_cols=per90_cols, dropna_row_threshold=None)
    processed, artifacts, report = preprocess(df_raw, cfg)

    if processed.empty:
        raise RuntimeError("All rows were dropped or became invalid during preprocessing. Try relaxing filters or re-run later.")

    # Choose target by id or name (now in processed)
    if qid is not None and (processed["player_id"] == qid).any():
        print(f"Selected query by id: {qid}")
    elif target_player_name is not None and (processed["name"].astype(str).str.lower() == target_player_name.lower()).any():
        qid = processed.loc[processed["name"].astype(str).str.lower() == target_player_name.lower(), "player_id"].iloc[0]
        print(f"Selected query by name: {target_player_name} -> id {qid}")
    else:
        # Fallback: first row
        qid = processed.iloc[0]["player_id"]
        print("[warn] Target player not found in dataset; falling back to first row.")

    # Log the chosen query row details for cross-check
    qrow = processed.loc[processed["player_id"] == qid].iloc[0]
    print(
        "Query Player => id={id}, name={name}, club={club}, country={country}, position={pos}, league={league}, season={season}".format(
            id=qrow.get("player_id"),
            name=qrow.get("name"),
            club=qrow.get("club"),
            country=qrow.get("country"),
            pos=qrow.get("position"),
            league=qrow.get("league"),
            season=qrow.get("season"),
        )
    )

    # Build filters to restrict results to the main league only (keep cross-league query row in df)
    main_league_val = _main_league_value(league_id)
    filters = {"league_in": [main_league_val]}

    wcfg = WeightConfig(position=position_weight) if position_weight else None
    res = similar_to_query(
        processed,
        query_id=qid,
        top_k=min(top_k, len(processed) - 1),
        weights=wcfg,
        return_columns=["player_id", "name", "position", "league"],
        restrict_to_query_positions=True,
        filters=filters,
    )  # type: ignore[arg-type]
    return res, processed


def main():
    print("🚀 Live End-to-End (FBRef) League Season Test")
    print("=" * 60)
    league_id = int(DEFAULTS["TEST_LEAGUE_ID"])  # use tester-local defaults
    season_id = DEFAULTS["TEST_SEASON_ID"]
    target_name = DEFAULTS["TEST_TARGET_NAME"]  # Example target player name

    # Optional separate league/season/team for the target player (cross-league)
    target_src_league = os.getenv("FBREF_TARGET_SOURCE_LEAGUE_ID")
    target_src_season = os.getenv("FBREF_TARGET_SOURCE_SEASON_ID")
    target_src_team = os.getenv("FBREF_TARGET_SOURCE_TEAM_ID")
    target_src_league_id = int(target_src_league) if target_src_league else None

    # Build a configured client from tester-controlled settings (env or internal defaults)
    enum_order = DEFAULTS["ENUMERATION_ORDER"]
    rate_limit_s = float(DEFAULTS["RATE_LIMIT_SECONDS"])
    timeout_s = float(DEFAULTS["TIMEOUT_SECONDS"])
    retry_total = int(DEFAULTS["RETRY_TOTAL"])
    retry_backoff = float(DEFAULTS["RETRY_BACKOFF"])
    enum_fb_season = DEFAULTS["ENUMERATION_FALLBACK_SEASON_ID"]

    client = create_fbref_client(
        rate_limit_seconds=rate_limit_s,
        timeout_seconds=timeout_s,
        retry_total=retry_total,
        retry_backoff=retry_backoff,
        enumeration_order=enum_order,
        enumeration_fallback_season_id=enum_fb_season,
    )

    # Log run-time settings for transparency
    print(f"Settings: ENUM_ORDER={enum_order}, RATE_LIMIT={rate_limit_s}s, TIMEOUT={timeout_s}s, RETRIES={retry_total}, BACKOFF={retry_backoff}, ENUM_FB_SEASON={enum_fb_season}")
    manual = os.getenv("FBREF_TEAM_IDS")
    if manual:
        print(f"Manual team ids provided: {manual}")

    # Optional: List-only mode to extract team ids for a stable season
    list_only = os.getenv("FBREF_LIST_TEAMS_ONLY", "").lower() in {"1", "true", "yes"}
    if list_only:
        teams = client.list_teams_in_league(league_id, season_id)
        if not teams:
            print("❌ Could not enumerate teams for the requested league/season.")
            return
        # Print as CSV for easy copy-paste
        team_ids = []
        print("team_id,team_name")
        for t in teams:
            tid = t.get("team_id") or ""
            tname = t.get("team_name") or ""
            print(f"{tid},{tname}")
            if tid:
                team_ids.append(str(tid))
        save_to = os.getenv("FBREF_SAVE_TEAM_IDS_TO")
        if save_to and team_ids:
            try:
                with open(save_to, "w", encoding="utf-8") as f:
                    f.write(",".join(team_ids))
                print(f"✅ Saved {len(team_ids)} team ids to {save_to}")
            except Exception as e:
                print(f"⚠️ Failed to save team ids to {save_to}: {e}")
        print("ℹ️ You can now set FBREF_TEAM_IDS to the comma-separated list above for a flaky season and re-run.")
        return

    try:
        res, processed = run_fbref_end_to_end_league(
            league_id=league_id,
            season_id=season_id,
            target_player_name=target_name,
            top_k=10,
            target_source_league_id=target_src_league_id,
            target_source_season_id=target_src_season,
            target_source_team_id=target_src_team,
            client=client,
        )
        print(res.head(10))
        print("\n✅ Live E2E (league season) completed")
    except Exception as e:
        print(f"❌ Live E2E failed: {e}")


if __name__ == "__main__":
    main()
