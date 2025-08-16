from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .player import Player
from core.leagues import get_league_registry, LeagueInfo


class SimilarPlayer(BaseModel):
    """A player similar to the reference player."""
    player: Player = Field(..., description="Player data")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score (0-1, higher is more similar)")
    similarity_breakdown: Optional[Dict[str, float]] = Field(None, description="Breakdown of similarity by stat category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "player": {
                    "metadata": {
                        "player_id": "92e7e919",
                        "full_name": "Son Heung-min",
                        "positions": ["FW", "MF"]
                    },
                    "age": 31,
                    "league": "Premier League",
                    "team": "Tottenham Hotspur"
                },
                "similarity_score": 0.89,
                "similarity_breakdown": {
                    "shooting": 0.92,
                    "passing": 0.85,
                    "defense": 0.78
                }
            }
        }


class SimilarityRequest(BaseModel):
    """Request model for finding similar players."""
    reference_player_id: str = Field(..., description="ID of the reference player")
    
    # League and season filters
    league_ids: Optional[List[int]] = Field(None, description="List of league IDs to search in")
    league_id: Optional[int] = Field(None, description="Single league ID (legacy support)")
    season_id: Optional[str] = Field(None, description="Season to search in")
    
    # Player filters
    positions: Optional[List[str]] = Field(None, description="List of positions to filter by")
    position: Optional[str] = Field(None, description="Single position filter (legacy support)")
    age_min: Optional[int] = Field(None, ge=16, le=50, description="Minimum age")
    age_max: Optional[int] = Field(None, ge=16, le=50, description="Maximum age")
    
    # Status filters
    status: Optional[str] = Field(None, description="Player status: Active/Retired/Unknown")
    is_active: Optional[bool] = Field(None, description="Whether to include only active players")
    
    # Gender filter (currently M only)
    gender: str = Field("M", description="Player gender (M/F) - currently M only")
    
    # Results
    max_results: int = Field(5, ge=1, le=100, description="Maximum number of similar players to return")
    
    @validator('age_max')
    def age_max_must_be_greater_than_min(cls, v, values):
        if v is not None and values.get('age_min') is not None:
            if v < values['age_min']:
                raise ValueError('age_max must be greater than or equal to age_min')
        return v
    
    @validator('age_min')
    def age_min_must_be_valid(cls, v):
        if v is not None and (v < 16 or v > 50):
            raise ValueError('age_min must be between 16 and 50')
        return v
    
    @validator('age_max')
    def age_max_must_be_valid(cls, v):
        if v is not None and (v < 16 or v > 50):
            raise ValueError('age_max must be between 16 and 50')
        return v
    
    @validator('league_ids')
    def validate_league_ids(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('league_ids cannot be empty list')
        
        # Validate that all league IDs exist in our registry
        if v is not None:
            registry = get_league_registry()
            for league_id in v:
                if not registry.get_league(league_id):
                    raise ValueError(f'League ID {league_id} not found in registry')
        
        return v
    
    @validator('positions')
    def validate_positions(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError('positions cannot be empty list')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v not in ['M', 'F']:
            raise ValueError('gender must be M or F')
        return v
    
    def get_league_info(self) -> List[LeagueInfo]:
        """Get detailed information about the requested leagues."""
        if not self.league_ids:
            return []
        
        registry = get_league_registry()
        return [registry.get_league(league_id) for league_id in self.league_ids if registry.get_league(league_id)]
    
    def get_major_leagues_only(self) -> List[int]:
        """Get only major league IDs from the request."""
        if not self.league_ids:
            return []
        
        registry = get_league_registry()
        major_league_ids = registry.get_major_league_ids()
        return [league_id for league_id in self.league_ids if league_id in major_league_ids]
    
    def get_league_names(self) -> List[str]:
        """Get the names of the requested leagues."""
        league_info = self.get_league_info()
        return [league.name for league in league_info]
    
    def get_countries(self) -> List[str]:
        """Get the countries of the requested leagues."""
        league_info = self.get_league_info()
        return list(set([league.country for league in league_info]))
    
    def get_continents(self) -> List[str]:
        """Get the continents of the requested leagues."""
        league_info = self.get_league_info()
        return list(set([league.continent for league in league_info if league.continent]))
    
    class Config:
        json_schema_extra = {
            "example": {
                "reference_player_id": "92e7e919",
                "league_ids": [9, 13, 20],  # Premier League, La Liga, Bundesliga
                "season_id": "2023-2024",
                "positions": ["ST", "CF", "LW"],  # Multiple positions
                "age_min": 25,
                "age_max": 35,
                "status": "Active",
                "is_active": True,
                "gender": "M",
                "max_results": 5
            }
        }


class SimilarityResponse(BaseModel):
    """Response model for similarity search results."""
    reference_player: Player = Field(..., description="Reference player data")
    similar_players: List[SimilarPlayer] = Field(..., description="List of similar players")
    filters_applied: Dict[str, Any] = Field(..., description="Filters that were applied to the search")
    search_metadata: Dict[str, Any] = Field(..., description="Search metadata and performance info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reference_player": {
                    "metadata": {
                        "player_id": "92e7e919",
                        "full_name": "Son Heung-min",
                        "positions": ["FW", "MF"]
                    }
                },
                "similar_players": [
                    {
                        "player": {
                            "metadata": {
                                "player_id": "abc123",
                                "full_name": "Similar Player",
                                "positions": ["FW"]
                            },
                            "similarity_score": 0.89
                        }
                    }
                ],
                "filters_applied": {
                    "league_id": 9,
                    "position": "FW",
                    "age_range": [25, 35]
                },
                "search_metadata": {
                    "total_players_searched": 500,
                    "search_time_ms": 245,
                    "algorithm_used": "cosine_similarity"
                }
            }
        }


class PlayerSearchRequest(BaseModel):
    """Request model for searching players."""
    query: str = Field(..., min_length=1, max_length=100, description="Player name to search for")
    league_id: Optional[int] = Field(None, description="League ID to filter by")
    position: Optional[str] = Field(None, description="Position to filter by")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of results to return")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Son Heung-min",
                "league_id": 9,
                "position": "FW",
                "max_results": 20
            }
        }


class PlayerSearchResponse(BaseModel):
    """Response model for player search results."""
    players: List[Player] = Field(..., description="List of matching players")
    total_results: int = Field(..., description="Total number of matching players")
    search_metadata: Dict[str, Any] = Field(..., description="Search metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "players": [
                    {
                        "metadata": {
                            "player_id": "92e7e919",
                            "full_name": "Son Heung-min",
                            "positions": ["FW", "MF"]
                        }
                    }
                ],
                "total_results": 1,
                "search_metadata": {
                    "search_time_ms": 45,
                    "query": "Son Heung-min"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Player not found",
                "detail": "No player found with ID: invalid_id",
                "error_code": "PLAYER_NOT_FOUND"
            }
        }
