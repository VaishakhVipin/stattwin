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
    """Rate limiter for FBRef API calls - 1 request every 3 seconds."""
    
    def __init__(self):
        self.last_call_time = None
        self.min_interval = 3  # 3 seconds between calls
    
    def wait_if_needed(self):
        """Wait if we need to respect the 3-second interval."""
        if self.last_call_time is not None:
            elapsed = (datetime.now() - self.last_call_time).total_seconds()
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.info(f"Rate limiting: Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        
        self.last_call_time = datetime.now()


class FBRefClient:
    """Client for interacting with the FBRef API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = settings.FBREF_API_BASE_URL
        self.rate_limiter = FBRefRateLimiter()
        self.data_manager = get_data_manager()  # Added: DataManager for caching
        
        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'StatTwin/1.0 (https://github.com/yourusername/stattwin)',
            'Accept': 'application/json'
        })
        
        # Generate a new API key for this session
        self._generate_api_key()
    
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
            response = self.session.get(url, params=params, timeout=30)
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
            params['season_id'] = season_id
        
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
            params['season_id'] = season_id
        
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
            params['season_id'] = season_id
        
        try:
            response = self._make_request(endpoint, params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get player match stats: {e}")
            return []
    
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
def create_fbref_client(api_key: Optional[str] = None) -> FBRefClient:
    """Create and return a configured FBRef client."""
    return FBRefClient(api_key=api_key)
