"""
League definitions and management for StatTwin.
Contains all major national domestic leagues accessible via FBRef API,
with support for dynamically registering additional national leagues
(discovered from FBRef) while excluding international competitions.
"""

from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass


class LeagueTier(str, Enum):
    """League tiers/levels."""
    FIRST = "1st"
    SECOND = "2nd"
    THIRD = "3rd"
    FOURTH = "4th"
    FIFTH = "5th"


class LeagueType(str, Enum):
    """Types of leagues."""
    DOMESTIC_LEAGUE = "domestic_leagues"
    DOMESTIC_CUP = "domestic_cups"
    INTERNATIONAL = "international_competitions"
    NATIONAL_TEAM = "national_team_competitions"


@dataclass
class LeagueInfo:
    """Information about a specific league."""
    league_id: int
    name: str
    country: str
    country_code: str
    tier: LeagueTier
    league_type: LeagueType
    gender: str = "M"  # Currently M only as per FBRef.md
    first_season: Optional[str] = None
    last_season: Optional[str] = None
    is_major: bool = False
    continent: Optional[str] = None
    governing_body: Optional[str] = None


class LeagueRegistry:
    """Registry of all supported leagues."""
    
    def __init__(self):
        self._leagues: Dict[int, LeagueInfo] = {}
        self._leagues_by_country: Dict[str, List[LeagueInfo]] = {}
        self._major_leagues: Set[int] = set()
        # Internal maps for normalization
        self._tier_map: Dict[str, LeagueTier] = {
            "1st": LeagueTier.FIRST,
            "2nd": LeagueTier.SECOND,
            "3rd": LeagueTier.THIRD,
            "4th": LeagueTier.FOURTH,
            "5th": LeagueTier.FIFTH,
        }
        self._initialize_leagues()
    
    # ---------------------- Normalization helpers ----------------------
    def _normalize_tier(self, tier_val: Any) -> LeagueTier:
        if isinstance(tier_val, LeagueTier):
            return tier_val
        if isinstance(tier_val, str):
            return self._tier_map.get(tier_val.strip(), LeagueTier.FIRST)
        return LeagueTier.FIRST

    def _normalize_league_type(self, league_type: Any) -> LeagueType:
        if isinstance(league_type, LeagueType):
            return league_type
        if isinstance(league_type, str):
            lt = league_type.strip().lower()
            if lt == LeagueType.DOMESTIC_LEAGUE.value:
                return LeagueType.DOMESTIC_LEAGUE
            if lt == LeagueType.DOMESTIC_CUP.value:
                return LeagueType.DOMESTIC_CUP
            if lt == LeagueType.INTERNATIONAL.value:
                return LeagueType.INTERNATIONAL
            if lt == LeagueType.NATIONAL_TEAM.value:
                return LeagueType.NATIONAL_TEAM
        # Default to domestic league if unknown, since we only register those via discovery
        return LeagueType.DOMESTIC_LEAGUE

    def _normalize_gender(self, gender: Optional[str]) -> str:
        g = (gender or "M").upper()
        return "M" if g not in ("M", "F") else g

    def _normalize_country_code(self, code: Optional[str]) -> str:
        return (code or "").upper()

    def _continent_from_country(self, country_name: str) -> str:
        """Determine continent from country name (kept local to avoid circular imports)."""
        european_countries = {
            'England', 'Spain', 'Germany', 'Italy', 'France', 'Netherlands', 'Portugal',
            'Belgium', 'Scotland', 'Switzerland', 'Austria', 'Denmark', 'Norway',
            'Sweden', 'Finland', 'Poland', 'Czech Republic', 'Hungary', 'Romania',
            'Bulgaria', 'Croatia', 'Serbia', 'Slovenia', 'Slovakia', 'Ukraine',
            'Belarus', 'Moldova', 'Estonia', 'Latvia', 'Lithuania', 'Iceland',
            'Ireland', 'Wales', 'Northern Ireland', 'Greece', 'Cyprus', 'Malta',
            'Turkey', 'Russia'
        }
        asian_countries = {
            'Japan', 'South Korea', 'China', 'Australia', 'India', 'Thailand',
            'Vietnam', 'Malaysia', 'Singapore', 'Indonesia', 'Philippines',
            'Saudi Arabia', 'Iran', 'Iraq', 'Kuwait', 'Qatar', 'UAE', 'Oman',
            'Yemen', 'Jordan', 'Lebanon', 'Syria', 'Israel', 'Palestine'
        }
        north_american_countries = {
            'United States', 'Canada', 'Mexico', 'Costa Rica', 'Honduras',
            'El Salvador', 'Guatemala', 'Nicaragua', 'Panama', 'Belize', 'Jamaica'
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
        if country_name in asian_countries:
            return "Asia"
        if country_name in north_american_countries:
            return "North America"
        if country_name in south_american_countries:
            return "South America"
        if country_name in african_countries:
            return "Africa"
        return "Unknown"

    # ---------------------- Initialization (static core set) ----------------------
    def _initialize_leagues(self):
        """Initialize a core set of supported domestic leagues (1st and 2nd tiers)."""
        
        # Major European Leagues (Big 5 + Others)
        self._add_league(LeagueInfo(
            league_id=9,
            name="Premier League",
            country="England",
            country_code="ENG",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=13,
            name="La Liga",
            country="Spain",
            country_code="ESP",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=20,
            name="Bundesliga",
            country="Germany",
            country_code="GER",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=11,
            name="Serie A",
            country="Italy",
            country_code="ITA",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=16,
            name="Ligue 1",
            country="France",
            country_code="FRA",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        # Other Major European Leagues
        self._add_league(LeagueInfo(
            league_id=23,
            name="Eredivisie",
            country="Netherlands",
            country_code="NED",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=24,
            name="Primeira Liga",
            country="Portugal",
            country_code="POR",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=22,
            name="Belgian Pro League",
            country="Belgium",
            country_code="BEL",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=25,
            name="J1 League",
            country="Japan",
            country_code="JPN",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="Asia",
            governing_body="AFC"
        ))
        
        # Major Non-European Leagues
        self._add_league(LeagueInfo(
            league_id=26,
            name="Major League Soccer",
            country="United States",
            country_code="USA",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="North America",
            governing_body="CONCACAF"
        ))
        
        self._add_league(LeagueInfo(
            league_id=27,
            name="Liga MX",
            country="Mexico",
            country_code="MEX",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="North America",
            governing_body="CONCACAF"
        ))
        
        self._add_league(LeagueInfo(
            league_id=28,
            name="Brasileirão",
            country="Brazil",
            country_code="BRA",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="South America",
            governing_body="CONMEBOL"
        ))
        
        self._add_league(LeagueInfo(
            league_id=29,
            name="Primera División",
            country="Argentina",
            country_code="ARG",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=True,
            continent="South America",
            governing_body="CONMEBOL"
        ))
        
        # Additional European Leagues
        self._add_league(LeagueInfo(
            league_id=30,
            name="Scottish Premiership",
            country="Scotland",
            country_code="SCO",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=31,
            name="Swiss Super League",
            country="Switzerland",
            country_code="SUI",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=32,
            name="Austrian Bundesliga",
            country="Austria",
            country_code="AUT",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=33,
            name="Danish Superliga",
            country="Denmark",
            country_code="DEN",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=34,
            name="Norwegian Eliteserien",
            country="Norway",
            country_code="NOR",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=35,
            name="Swedish Allsvenskan",
            country="Sweden",
            country_code="SWE",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=36,
            name="Finnish Veikkausliiga",
            country="Finland",
            country_code="FIN",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        # Additional Asian Leagues
        self._add_league(LeagueInfo(
            league_id=37,
            name="K League 1",
            country="South Korea",
            country_code="KOR",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Asia",
            governing_body="AFC"
        ))
        
        self._add_league(LeagueInfo(
            league_id=38,
            name="Chinese Super League",
            country="China",
            country_code="CHN",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Asia",
            governing_body="AFC"
        ))
        
        self._add_league(LeagueInfo(
            league_id=39,
            name="A-League",
            country="Australia",
            country_code="AUS",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Oceania",
            governing_body="AFC"
        ))
        
        # Additional South American Leagues
        self._add_league(LeagueInfo(
            league_id=40,
            name="Primera División",
            country="Chile",
            country_code="CHI",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="South America",
            governing_body="CONMEBOL"
        ))
        
        self._add_league(LeagueInfo(
            league_id=41,
            name="Liga BetPlay",
            country="Colombia",
            country_code="COL",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="South America",
            governing_body="CONMEBOL"
        ))
        
        self._add_league(LeagueInfo(
            league_id=42,
            name="Liga 1",
            country="Peru",
            country_code="PER",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="South America",
            governing_body="CONMEBOL"
        ))
        
        # Additional North American Leagues
        self._add_league(LeagueInfo(
            league_id=43,
            name="Canadian Premier League",
            country="Canada",
            country_code="CAN",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="North America",
            governing_body="CONCACAF"
        ))
        
        # Additional African Leagues
        self._add_league(LeagueInfo(
            league_id=44,
            name="Egyptian Premier League",
            country="Egypt",
            country_code="EGY",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Africa",
            governing_body="CAF"
        ))
        
        self._add_league(LeagueInfo(
            league_id=45,
            name="South African Premier Division",
            country="South Africa",
            country_code="RSA",
            tier=LeagueTier.FIRST,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Africa",
            governing_body="CAF"
        ))
        
        # Additional European Second Divisions
        self._add_league(LeagueInfo(
            league_id=46,
            name="Championship",
            country="England",
            country_code="ENG",
            tier=LeagueTier.SECOND,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=47,
            name="La Liga 2",
            country="Spain",
            country_code="ESP",
            tier=LeagueTier.SECOND,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=48,
            name="2. Bundesliga",
            country="Germany",
            country_code="GER",
            tier=LeagueTier.SECOND,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=49,
            name="Serie B",
            country="Italy",
            country_code="ITA",
            tier=LeagueTier.SECOND,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
        
        self._add_league(LeagueInfo(
            league_id=50,
            name="Ligue 2",
            country="France",
            country_code="FRA",
            tier=LeagueTier.SECOND,
            league_type=LeagueType.DOMESTIC_LEAGUE,
            is_major=False,
            continent="Europe",
            governing_body="UEFA"
        ))
    
    # ---------------------- Core add/merge operations ----------------------
    def _add_league(self, league: LeagueInfo):
        """Add a league to the registry (internal)."""
        # Normalize values
        normalized_tier = self._normalize_tier(league.tier)
        normalized_type = self._normalize_league_type(league.league_type)
        normalized_gender = self._normalize_gender(league.gender)
        country_code = self._normalize_country_code(league.country_code)

        # Exclude non-club international competitions entirely
        if normalized_type in (LeagueType.INTERNATIONAL, LeagueType.NATIONAL_TEAM):
            return

        # Create a normalized copy
        normalized = LeagueInfo(
            league_id=league.league_id,
            name=league.name,
            country=league.country,
            country_code=country_code,
            tier=normalized_tier,
            league_type=normalized_type,
            gender=normalized_gender,
            first_season=league.first_season,
            last_season=league.last_season,
            is_major=league.is_major,
            continent=league.continent,
            governing_body=league.governing_body,
        )

        # Insert/update
        self._leagues[normalized.league_id] = normalized
        
        if normalized.country_code not in self._leagues_by_country:
            self._leagues_by_country[normalized.country_code] = []
        
        # Avoid duplicates in country list (update in place)
        existing_list = self._leagues_by_country[normalized.country_code]
        for idx, existing in enumerate(existing_list):
            if existing.league_id == normalized.league_id:
                existing_list[idx] = normalized
                break
        else:
            existing_list.append(normalized)
        
        if normalized.is_major:
            self._major_leagues.add(normalized.league_id)

    def add_or_update_league(self, league: LeagueInfo) -> None:
        """Public method to add or update a single league (domestic leagues preferred)."""
        self._add_league(league)

    def add_leagues(self, leagues: List[LeagueInfo], include_cups: bool = False) -> int:
        """Add multiple leagues to the registry.
        Only domestic leagues are added by default. Set include_cups=True to also include domestic cups.
        International competitions and national team competitions are always excluded.
        Returns number of leagues added/updated.
        """
        count = 0
        for league in leagues:
            lt = self._normalize_league_type(league.league_type)
            if lt == LeagueType.DOMESTIC_LEAGUE or (include_cups and lt == LeagueType.DOMESTIC_CUP):
                self._add_league(league)
                count += 1
        return count

    def add_leagues_from_fbref(self, country: Dict[str, Any], league_groups: List[Dict[str, Any]], include_cups: bool = False, gender: str = "M") -> int:
        """Add leagues from FBRef /leagues endpoint payload for a given country.
        - country: dict item from /countries (expects keys: country, country_code, governing_body)
        - league_groups: list of groups from /leagues (each has league_type and leagues[])
        - include_cups: include domestic cups if True (defaults False)
        - gender: filter gender ('M' or 'F'), defaults to 'M'
        Returns number of leagues added.
        """
        g = self._normalize_gender(gender)
        added = 0
        country_name = country.get('country', 'Unknown')
        cc = self._normalize_country_code(country.get('country_code'))
        continent = self._continent_from_country(country_name)
        governing_body = country.get('governing_body')

        for group in league_groups or []:
            group_type = self._normalize_league_type(group.get('league_type'))
            if group_type not in (LeagueType.DOMESTIC_LEAGUE, LeagueType.DOMESTIC_CUP):
                continue  # ignore international and national team comps
            if group_type == LeagueType.DOMESTIC_CUP and not include_cups:
                continue

            for lg in group.get('leagues', []) or []:
                # Gender filter
                if self._normalize_gender(lg.get('gender')) != g:
                    continue
                # Build LeagueInfo and add
                li = LeagueInfo(
                    league_id=int(lg.get('league_id')),
                    name=str(lg.get('competition_name')),
                    country=country_name,
                    country_code=cc,
                    tier=self._normalize_tier(lg.get('tier')),
                    league_type=group_type,
                    gender=g,
                    first_season=lg.get('first_season'),
                    last_season=lg.get('last_season'),
                    is_major=False,
                    continent=continent,
                    governing_body=governing_body,
                )
                self._add_league(li)
                added += 1
        return added

    # ---------------------- Query methods ----------------------
    def get_league(self, league_id: int) -> Optional[LeagueInfo]:
        """Get league information by ID."""
        return self._leagues.get(league_id)
    
    def get_leagues_by_country(self, country_code: str) -> List[LeagueInfo]:
        """Get all leagues for a specific country."""
        return self._leagues_by_country.get(country_code.upper(), [])
    
    def get_major_leagues(self) -> List[LeagueInfo]:
        """Get all major leagues."""
        return [self._leagues[league_id] for league_id in self._major_leagues if league_id in self._leagues]
    
    def get_leagues_by_continent(self, continent: str) -> List[LeagueInfo]:
        """Get all leagues for a specific continent."""
        return [league for league in self._leagues.values() if league.continent == continent]
    
    def get_leagues_by_tier(self, tier: LeagueTier) -> List[LeagueInfo]:
        """Get all leagues for a specific tier."""
        return [league for league in self._leagues.values() if league.tier == tier]
    
    def get_all_leagues(self) -> List[LeagueInfo]:
        """Get all leagues."""
        return list(self._leagues.values())
    
    def get_league_ids(self) -> List[int]:
        """Get all league IDs."""
        return list(self._leagues.keys())
    
    def get_major_league_ids(self) -> List[int]:
        """Get all major league IDs."""
        return list(self._major_leagues)
    
    def search_leagues(self, query: str) -> List[LeagueInfo]:
        """Search leagues by name or country."""
        query_lower = query.lower()
        results = []
        
        for league in self._leagues.values():
            if (query_lower in league.name.lower() or 
                query_lower in league.country.lower() or
                query_lower in league.country_code.lower()):
                results.append(league)
        
        return results
    
    def get_league_hierarchy(self) -> Dict[str, Dict[str, List[LeagueInfo]]]:
        """Get leagues organized by continent and country."""
        hierarchy = {}
        
        for league in self._leagues.values():
            continent = league.continent or "Unknown"
            country = league.country
            
            if continent not in hierarchy:
                hierarchy[continent] = {}
            
            if country not in hierarchy[continent]:
                hierarchy[continent][country] = []
            
            hierarchy[continent][country].append(league)
        
        return hierarchy


# Global instance
league_registry = LeagueRegistry()


def get_league_registry() -> LeagueRegistry:
    """Get the global league registry instance."""
    return league_registry


def get_major_leagues() -> List[LeagueInfo]:
    """Get all major leagues."""
    return league_registry.get_major_leagues()


def get_league_by_id(league_id: int) -> Optional[LeagueInfo]:
    """Get league information by ID."""
    return league_registry.get_league(league_id)


def get_leagues_by_country(country_code: str) -> List[LeagueInfo]:
    """Get all leagues for a specific country."""
    return league_registry.get_leagues_by_country(country_code)


def get_league_hierarchy() -> Dict[str, Dict[str, List[LeagueInfo]]]:
    """Get leagues organized by continent and country."""
    return league_registry.get_league_hierarchy()


def register_discovered_leagues(leagues: List[LeagueInfo], include_cups: bool = False) -> int:
    """Convenience function to register a list of discovered leagues.
    Only domestic leagues are added by default; set include_cups=True to add domestic cups too.
    International and national team competitions are ignored.
    Returns number of leagues added/updated.
    """
    return league_registry.add_leagues(leagues, include_cups=include_cups)
