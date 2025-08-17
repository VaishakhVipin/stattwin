import time
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
import os
from .config import settings
from .leagues import get_league_registry, LeagueInfo
from .data_manager import get_data_manager  # Added: caching

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBRefRateLimiter:
    """Rate limiter for FBRef API calls - default 1 request every 3 seconds (configurable)."""
    
    def __init__(self, min_interval: Optional[float] = None):
        self.last_call_time = None
        if min_interval is not None:
            self.min_interval = float(min_interval)
        else:
            try:
                self.min_interval = float(os.getenv("FBREF_RATE_LIMIT_SECONDS", "3"))
            except Exception:
                self.min_interval = 3.0
    
    def wait_if_needed(self):
        """Wait if we need to respect the interval."""
        if self.last_call_time is not None:
            elapsed = (datetime.now() - self.last_call_time).total_seconds()
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.info(f"Rate limiting: Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        self.last_call_time = datetime.now()


class FBRefClient:
    """Client for interacting with the FBRef API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        rate_limit_seconds: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        retry_total: Optional[int] = None,
        retry_backoff: Optional[float] = None,
        enumeration_order: Optional[str] = None,
        enumeration_fallback_season_id: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = settings.FBREF_API_BASE_URL
        self.enumeration_order = enumeration_order
        self.enumeration_fallback_season_id = enumeration_fallback_season_id
        self.rate_limiter = FBRefRateLimiter(min_interval=rate_limit_seconds)
        self.data_manager = get_data_manager()  # Added: DataManager for caching
        # Request timeout configurable via env or override
        if timeout_seconds is not None:
            self.request_timeout = float(timeout_seconds)
        else:
            try:
                self.request_timeout = float(os.getenv("FBREF_TIMEOUT_SECONDS", "30"))
            except Exception:
                self.request_timeout = 30.0
        
        # Set up session with retry strategy (configurable)
        self.session = requests.Session()
        if retry_total is None:
            try:
                retry_total = int(os.getenv("FBREF_RETRY_TOTAL", "5"))
            except Exception:
                retry_total = 5
        if retry_backoff is None:
            try:
                retry_backoff = float(os.getenv("FBREF_RETRY_BACKOFF", "1.5"))
            except Exception:
                retry_backoff = 1.5
        retry_strategy = Retry(
            total=retry_total,
            backoff_factor=retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'StatTwin/1.0 (https://github.com/VaishakhVipin/stattwin)',
            'Accept': 'application/json'
        })
        
        logger.info(
            f"FBRef client configured: timeout={self.request_timeout:.0f}s, rate_limit={self.rate_limiter.min_interval:.1f}s, "
            f"retries={retry_total} backoff={retry_backoff}, enum_order={self.enumeration_order or 'ENV/DEFAULT'}, "
            f"enum_fb_season={self.enumeration_fallback_season_id or 'ENV/None'}"
        )

        # Generate a new API key for this session
        self._generate_api_key()

    # --------------------- Helpers ---------------------
    def _normalize_season_id(self, season_id: Optional[str]) -> Optional[str]:
        """Normalize season formats like '2015-16'/'2015/16'/'2015–16' -> '2015-2016'."""
        if not season_id:
            return season_id
        s = str(season_id).strip()
        if not s:
            return s
        # Unify separators
        s2 = s.replace("/", "-").replace("–", "-").replace("—", "-")
        # If already YYYY-YYYY, keep
        if len(s2) == 9 and s2[:4].isdigit() and s2[4] == '-' and s2[5:].isdigit():
            return s2
        # If YYYY-YY, expand to YYYY-YYYY
        if len(s2) == 7 and s2[:4].isdigit() and s2[4] == '-' and s2[5:7].isdigit():
            start = int(s2[:4])
            end2 = int(s2[5:7])
            century = (start // 100) * 100
            end_full = century + end2
            if end_full < start:
                end_full += 100
            norm = f"{start}-{end_full}"
            logger.info(f"Normalizing season_id '{s}' -> '{norm}'")
            return norm
        # Otherwise, return cleaned value
        if s2 != s:
            logger.info(f"Normalizing season_id '{s}' -> '{s2}'")
        return s2
    
    def _generate_api_key(self):
        """Generate a new API key for this session."""
        try:
            logger.info("Generating new FBRef API key...")
            response = self.session.post(f"{self.base_url}/generate_api_key")
            response.raise_for_status()
            
            data = response.json()
            self.api_key = data.get('api_key')
            
            if self.api_key:
                # Update headers with the new API key
                self.session.headers.update({'X-API-Key': self.api_key})
                logger.info("✅ API key generated successfully")
            else:
                logger.error("❌ Failed to get API key from response")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate API key: {e}")
            # Fallback to environment variable if available
            self.api_key = os.getenv("FBREF_API_KEY")
            if self.api_key:
                self.session.headers.update({'X-API-Key': self.api_key})
                logger.info("Using fallback API key from environment")
            else:
                logger.warning("No API key available - some endpoints may fail")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a rate-limited GET request to the FBRef API with filesystem caching."""
        url = f"{self.base_url}{endpoint}"
        
        def fetch_fn() -> Dict[str, Any]:
            # Only rate-limit when we actually hit the network
            self.rate_limiter.wait_if_needed()
            logger.info(f"Making request to: {url}")
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            return response.json()
        
        try:
            # Use DataManager cache (default TTL from configuration)
            data = self.data_manager.get_or_fetch_raw(
                endpoint=endpoint,
                params=params or {},
                fetch_fn=fetch_fn,
                max_age=self.data_manager.config.default_ttl,
                version=None,
            )
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise FBRefAPIError(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise FBRefAPIError(f"Invalid JSON response: {e}")
    
    def get_countries(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get countries data.
        
        Args:
            country: Optional country name filter
            
        Returns:
            List of countries with their data
        """
        endpoint = "/countries"
        params = {}
        if country:
            params['country'] = country
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get countries: {e}")
            return []
    
    def get_leagues(self, country_code: str) -> List[Dict[str, Any]]:
        """
        Get leagues for a specific country.
        
        Args:
            country_code: Three-letter country code
            
        Returns:
            List of leagues for the country
        """
        endpoint = "/leagues"
        params = {'country_code': country_code}
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get leagues for {country_code}: {e}")
            return []
    
    def discover_leagues(self) -> List[LeagueInfo]:
        """
        Discover all available leagues from FBRef API and update our registry.
        This method fetches leagues from all countries and merges them with our predefined list.
        """
        logger.info("🔍 Discovering leagues from FBRef API...")
        
        # Get our predefined league registry
        registry = get_league_registry()
        discovered_leagues = []
        
        try:
            # Get all countries first
            countries = self.get_countries()
            logger.info(f"Found {len(countries)} countries")
            
            for country in countries:
                country_code = country.get('country_code')
                if not country_code:
                    continue
                
                try:
                    # Get leagues for this country
                    leagues_data = self.get_leagues(country_code)
                    
                    for league_group in leagues_data:
                        league_type = league_group.get('league_type')
                        leagues = league_group.get('leagues', [])
                        
                        for league in leagues:
                            league_id = league.get('league_id')
                            competition_name = league.get('competition_name')
                            gender = league.get('gender', 'M')
                            
                            if league_id and competition_name and gender == 'M':
                                # Check if we already have this league in our registry
                                existing_league = registry.get_league(league_id)
                                
                                if existing_league:
                                    # Update with any new information from API
                                    logger.debug(f"League {competition_name} (ID: {league_id}) already in registry")
                                else:
                                    # This is a new league - add it to discovered list
                                    discovered_league = LeagueInfo(
                                        league_id=league_id,
                                        name=competition_name,
                                        country=country.get('country', 'Unknown'),
                                        country_code=country_code,
                                        tier=league.get('tier', 'Unknown'),
                                        league_type=league_type,
                                        gender=gender,
                                        first_season=league.get('first_season'),
                                        last_season=league.get('last_season'),
                                        is_major=False,  # Default to False for discovered leagues
                                        continent=self._get_continent_from_country(country.get('country', '')),
                                        governing_body=country.get('governing_body')
                                    )
                                    discovered_leagues.append(discovered_league)
                                    logger.info(f"Discovered new league: {competition_name} (ID: {league_id}) from {country.get('country', 'Unknown')}")
                
                except Exception as e:
                    logger.warning(f"Failed to get leagues for country {country_code}: {e}")
                    continue
                
                # Rate limiting between countries
                time.sleep(3)
            
            logger.info(f"✅ League discovery complete. Found {len(discovered_leagues)} new leagues")
            return discovered_leagues
            
        except Exception as e:
            logger.error(f"League discovery failed: {e}")
            return []
    
    def _get_continent_from_country(self, country_name: str) -> str:
        """Helper method to determine continent from country name."""
        european_countries = {
            'England', 'Spain', 'Germany', 'Italy', 'France', 'Netherlands', 'Portugal', 
            'Belgium', 'Scotland', 'Switzerland', 'Austria', 'Denmark', 'Norway', 
            'Sweden', 'Finland', 'Poland', 'Czech Republic', 'Hungary', 'Romania', 
            'Bulgaria', 'Croatia', 'Serbia', 'Slovenia', 'Slovakia', 'Ukraine', 
            'Belarus', 'Moldova', 'Estonia', 'Latvia', 'Lithuania', 'Iceland', 
            'Ireland', 'Wales', 'Northern Ireland', 'Greece', 'Cyprus', 'Malta'
        }
        
        asian_countries = {
            'Japan', 'South Korea', 'China', 'Australia', 'India', 'Thailand', 
            'Vietnam', 'Malaysia', 'Singapore', 'Indonesia', 'Philippines', 
            'Saudi Arabia', 'Iran', 'Iraq', 'Kuwait', 'Qatar', 'UAE', 'Oman', 
            'Yemen', 'Jordan', 'Lebanon', 'Syria', 'Israel', 'Palestine'
        }
        
        north_american_countries = {
            'United States', 'Canada', 'Mexico', 'Costa Rica', 'Honduras', 
            'El Salvador', 'Guatemala', 'Nicaragua', 'Panama', 'Belize'
        }
        
        south_american_countries = {
            'Brazil', 'Argentina', 'Chile', 'Colombia', 'Peru', 'Uruguay', 
            'Paraguay', 'Ecuador', 'Bolivia', 'Venezuela', 'Guyana', 'Suriname'
        }
        
        african_countries = {
            'Egypt', 'South Africa', 'Nigeria', 'Ghana', 'Morocco', 'Algeria', 
            'Tunisia', 'Senegal', 'Cameroon', 'Ivory Coast', 'Kenya', 'Uganda'
        }
        
        if country_name in european_countries:
            return "Europe"
        elif country_name in asian_countries:
            return "Asia"
        elif country_name in north_american_countries:
            return "North America"
        elif country_name in south_american_countries:
            return "South America"
        elif country_name in african_countries:
            return "Africa"
        else:
            return "Unknown"
    
    def get_supported_leagues(self) -> List[LeagueInfo]:
        """
        Get all leagues currently supported by our system.
        This includes both predefined leagues and any discovered from FBRef.
        """
        registry = get_league_registry()
        return registry.get_all_leagues()
    
    def get_major_leagues(self) -> List[LeagueInfo]:
        """Get all major leagues."""
        registry = get_league_registry()
        return registry.get_major_leagues()
    
    def get_league_info(self, league_id: int) -> Optional[LeagueInfo]:
        """Get detailed information about a specific league."""
        registry = get_league_registry()
        return registry.get_league(league_id)
    
    def search_leagues(self, query: str) -> List[LeagueInfo]:
        """Search leagues by name, country, or other criteria."""
        registry = get_league_registry()
        return registry.search_leagues(query)
        """
        Get leagues for a specific country.
        
        Args:
            country_code: Three-letter country code
            
        Returns:
            List of leagues for the country
        """
        endpoint = "/leagues"
        params = {'country_code': country_code}
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get leagues for {country_code}: {e}")
            return []
    
    def get_league_seasons(self, league_id: int) -> List[Dict[str, Any]]:
        """
        Get seasons for a specific league.
        
        Args:
            league_id: League ID
            
        Returns:
            List of seasons for the league
        """
        endpoint = "/league-seasons"
        params = {'league_id': league_id}
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get seasons for league {league_id}: {e}")
            return []
    
    def get_teams(self, team_id: str, season_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get team data including roster and schedule.
        
        Args:
            team_id: Team ID
            season_id: Optional season ID
            
        Returns:
            Team data with roster and schedule
        """
        endpoint = "/teams"
        params = {'team_id': team_id}
        if season_id:
            params['season_id'] = self._normalize_season_id(season_id)
        
        try:
            response = self._make_request(endpoint, params)
            return response
        except Exception as e:
            logger.error(f"Failed to get team data for {team_id}: {e}")
            return {}
    
    def get_players(self, player_id: str) -> Dict[str, Any]:
        """
        Get player metadata.
        
        Args:
            player_id: Player ID
            
        Returns:
            Player metadata
        """
        endpoint = "/players"
        params = {'player_id': player_id}
        
        try:
            response = self._make_request(endpoint, params)
            return response
        except Exception as e:
            logger.error(f"Failed to get player data for {player_id}: {e}")
            return {}
    
    def get_player_season_stats(self, team_id: str, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get season-level player stats for a team.
        
        Args:
            team_id: Team ID
            league_id: League ID
            season_id: Optional season ID
            
        Returns:
            List of player season stats
        """
        endpoint = "/player-season-stats"
        params = {
            'team_id': team_id,
            'league_id': league_id
        }
        if season_id:
            params['season_id'] = self._normalize_season_id(season_id)
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('players', [])
        except Exception as e:
            logger.error(f"Failed to get player season stats: {e}")
            return []
    
    def get_player_match_stats(self, player_id: str, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get match-level player stats.
        
        Args:
            player_id: Player ID
            league_id: League ID
            season_id: Optional season ID
            
        Returns:
            List of player match stats
        """
        endpoint = "/player-match-stats"
        params = {
            'player_id': player_id,
            'league_id': league_id
        }
        if season_id:
            params['season_id'] = self._normalize_season_id(season_id)
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get player match stats: {e}")
            return []
    
    def get_league_standings(self, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Deprecated in our flow: we avoid relying on standings for team enumeration."""
        endpoint = "/league-standings"
        params: Dict[str, Any] = {"league_id": league_id}
        if season_id:
            params["season_id"] = self._normalize_season_id(season_id)
        try:
            response = self._make_request(endpoint, params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get league standings for league {league_id} season {season_id}: {e}")
            return []

    def get_team_season_stats(self, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve season-level team stats; useful for enumerating team ids when matches/season-details fail."""
        endpoint = "/team-season-stats"
        params: Dict[str, Any] = {"league_id": league_id}
        if season_id:
            params["season_id"] = self._normalize_season_id(season_id)
        try:
            response = self._make_request(endpoint, params)
            # Some implementations return under 'data'
            data = response.get("data")
            if isinstance(data, list):
                return data
            # Otherwise return raw list if response itself is a list
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"Failed to get team season stats for league {league_id} season {season_id}: {e}")
            return []

    def get_matches(self, league_id: Optional[int] = None, season_id: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve match meta-data. If team_id is provided, returns team matches; otherwise league matches (per fbref.md)."""
        endpoint = "/matches"
        params: Dict[str, Any] = {}
        if team_id:
            params["team_id"] = team_id
        elif league_id is not None:
            params["league_id"] = league_id
        if season_id:
            params["season_id"] = self._normalize_season_id(season_id)
        try:
            response = self._make_request(endpoint, params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get matches (league_id={league_id}, team_id={team_id}, season_id={season_id}): {e}")
            return []

    def list_teams_in_league(self, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Enumerate teams via league-level matches (home/away team ids) as per fbref.md.
        Avoids standings to stay within documented flow.
        """
        teams: Dict[str, Dict[str, Any]] = {}

        def add(team_id: Optional[str], team_name: Optional[str]):
            if not team_id and not team_name:
                return
            key = (team_id or team_name or "").strip()
            if key and key not in teams:
                teams[key] = {"team_id": team_id, "team_name": team_name}

        # Enumeration order can be controlled by programmatic override or env var
        order_env = (self.enumeration_order or os.getenv("FBREF_ENUMERATION_ORDER", "matches,season-details,team-season-stats,standings,manual"))
        steps = [s.strip().lower() for s in order_env.split(",") if s.strip()]

        def do_matches():
            matches = self.get_matches(league_id=league_id, season_id=season_id)
            for m in matches:
                home_id = m.get("home_team_id") or m.get("home_id") or (m.get("home") if isinstance(m.get("home"), str) else None)
                away_id = m.get("away_team_id") or m.get("away_id") or (m.get("away") if isinstance(m.get("away"), str) else None)
                home_name = m.get("home") or m.get("home_team") or m.get("home_name")
                away_name = m.get("away") or m.get("away_team") or m.get("away_name")
                if home_id or home_name:
                    add(str(home_id) if home_id is not None else None, str(home_name) if home_name is not None else None)
                if away_id or away_name:
                    add(str(away_id) if away_id is not None else None, str(away_name) if away_name is not None else None)
            return "matches"

        def do_season_details():
            for t in self.list_teams_from_season(league_id, season_id):
                add(t.get("team_id"), t.get("team_name"))
            return "season-details"

        def do_standings():
            standings = self.get_league_standings(league_id, season_id)
            for row in standings:
                tid = row.get("team_id") or row.get("id")
                tname = row.get("team_name") or row.get("team") or row.get("name")
                add(str(tid) if tid is not None else None, str(tname) if tname is not None else None)
            return "standings"

        def do_team_stats():
            rows = self.get_team_season_stats(league_id, season_id)
            # Try a generic deep extraction similar to list_teams_from_season
            def try_extract(obj: Any):
                if isinstance(obj, dict):
                    tid = obj.get("team_id") or obj.get("id")
                    tname = obj.get("team_name") or obj.get("team") or obj.get("name")
                    team_obj = obj.get("team")
                    if isinstance(team_obj, dict):
                        tid = tid or team_obj.get("team_id") or team_obj.get("id")
                        tname = tname or team_obj.get("team_name") or team_obj.get("name")
                    if tid or tname:
                        add(str(tid) if tid is not None else None, str(tname) if tname is not None else None)
                    for v in obj.values():
                        try_extract(v)
                elif isinstance(obj, list):
                    for it in obj:
                        try_extract(it)
            try_extract(rows)
            return "team-season-stats"

        def do_manual():
            manual = os.getenv("FBREF_TEAM_IDS")
            if manual:
                for tid in [x.strip() for x in manual.split(",") if x.strip()]:
                    add(tid, None)
            return "manual"

        action_map = {
            "matches": do_matches,
            "season-details": do_season_details,
            "standings": do_standings,
            "team-season-stats": do_team_stats,
            "manual": do_manual,
        }

        def run_steps(for_season: Optional[str]) -> List[str]:
            local_tried: List[str] = []
            for step in steps:
                fn = action_map.get(step)
                if not fn:
                    continue
                before = len(teams)
                # Temporarily swap season_id for this attempt
                nonlocal season_id
                orig_season = season_id
                season_id = for_season
                tag = fn()
                season_id = orig_season
                after = len(teams)
                local_tried.append(f"{tag}:{after-before}")
                if teams:
                    logger.info(
                        f"Team enumeration succeeded via {tag} (found={len(teams)}; increments={after-before})"
                    )
                    break
            return local_tried

        tried: List[str] = run_steps(season_id)
        if teams:
            return list(teams.values())

        # Optional: try an alternate season for team enumeration only
        fallback_season = self.enumeration_fallback_season_id or os.getenv("FBREF_ENUMERATION_FALLBACK_SEASON_ID")
        if fallback_season:
            logger.info(
                f"Primary enumeration failed; trying fallback season for team listing: {fallback_season}"
            )
            tried_fb = run_steps(fallback_season)
            tried.extend([f"fb:{x}" for x in tried_fb])
            if teams:
                logger.info(
                    f"Team enumeration succeeded via fallback season {fallback_season} (found={len(teams)})"
                )
                return list(teams.values())

        logger.warning(f"No teams could be enumerated (order={order_env}; tried={';'.join(tried)})")
        return []

    def get_league_season_details(self, league_id: int, season_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve meta-data for a specific league and season, typically includes teams and other info."""
        endpoint = "/league-season-details"
        params: Dict[str, Any] = {"league_id": league_id}
        if season_id:
            params["season_id"] = self._normalize_season_id(season_id)
        try:
            response = self._make_request(endpoint, params)
            return response
        except Exception as e:
            logger.error(f"Failed to get league season details for league {league_id} season {season_id}: {e}")
            return {}

    def list_teams_from_season(self, league_id: int, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return teams (team_id, team_name) from league-season-details endpoint."""
        payload = self.get_league_season_details(league_id, season_id)
        teams: Dict[str, Dict[str, Any]] = {}

        def add_team(team_id: Optional[str], team_name: Optional[str]):
            if not team_id and not team_name:
                return
            key = (team_id or team_name or "").strip()
            if key and key not in teams:
                teams[key] = {"team_id": team_id, "team_name": team_name}

        def try_extract(obj: Any):
            if isinstance(obj, dict):
                # Direct keys
                tid = obj.get("team_id") or obj.get("id")
                tname = obj.get("team_name") or obj.get("team") or obj.get("name")
                # Nested
                team_obj = obj.get("team")
                if isinstance(team_obj, dict):
                    tid = tid or team_obj.get("team_id") or team_obj.get("id")
                    tname = tname or team_obj.get("team_name") or team_obj.get("name")
                if tid or tname:
                    add_team(str(tid) if tid is not None else None, str(tname) if tname is not None else None)
                for v in obj.values():
                    try_extract(v)
            elif isinstance(obj, list):
                for it in obj:
                    try_extract(it)

        try_extract(payload)
        return list(teams.values())
    
    def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            # Try to get countries as a simple test
            response = self._make_request("/countries")
            return 'data' in response
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class FBRefAPIError(Exception):
    """Custom exception for FBRef API errors."""
    pass


# Convenience function to create client
def create_fbref_client(api_key: Optional[str] = None, **kwargs: Any) -> FBRefClient:
    """Create and return a configured FBRef client. Additional keyword args configure behavior."""
    return FBRefClient(api_key=api_key, **kwargs)
