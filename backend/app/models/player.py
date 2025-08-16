from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class Position(str, Enum):
    """Player positions with specific soccer roles."""
    # Goalkeeper
    GK = "GK"  # Goalkeeper
    
    # Defenders
    CB = "CB"  # Center Back
    LB = "LB"  # Left Back
    RB = "RB"  # Right Back
    WB = "WB"  # Wing Back (Left/Right)
    SW = "SW"  # Sweeper
    
    # Midfielders
    DM = "DM"  # Defensive Midfielder (Holding)
    CM = "CM"  # Central Midfielder
    AM = "AM"  # Attacking Midfielder
    LM = "LM"  # Left Midfielder
    RM = "RM"  # Right Midfielder
    WM = "WM"  # Wide Midfielder
    
    # Forwards
    ST = "ST"  # Striker
    CF = "CF"  # Center Forward
    LW = "LW"  # Left Winger
    RW = "RW"  # Right Winger
    SS = "SS"  # Second Striker
    
    # Legacy positions (for backward compatibility)
    DF = "DF"  # Defender (generic)
    MF = "MF"  # Midfielder (generic)
    FW = "FW"  # Forward (generic)
    
    @classmethod
    def get_position_group(cls, position: str) -> str:
        """Get the general position group for a specific position."""
        if position in [cls.GK]:
            return "Goalkeeper"
        elif position in [cls.CB, cls.LB, cls.RB, cls.WB, cls.SW, cls.DF]:
            return "Defender"
        elif position in [cls.DM, cls.CM, cls.AM, cls.LM, cls.RM, cls.WM, cls.MF]:
            return "Midfielder"
        elif position in [cls.ST, cls.CF, cls.LW, cls.RW, cls.SS, cls.FW]:
            return "Forward"
        else:
            return "Unknown"
    
    @classmethod
    def get_position_weights(cls, position: str) -> Dict[str, float]:
        """Get position-specific weights for similarity calculations."""
        weights = {
            # Goalkeeper weights
            "GK": {
                "goalkeeper": 0.40,
                "defense": 0.25,
                "passing": 0.20,
                "possession": 0.10,
                "shooting": 0.05
            },
            # Defender weights
            "CB": {
                "defense": 0.35,
                "passing": 0.25,
                "possession": 0.20,
                "goalkeeper": 0.15,
                "shooting": 0.05
            },
            "LB": {
                "defense": 0.30,
                "passing": 0.25,
                "possession": 0.20,
                "shooting": 0.15,
                "goalkeeper": 0.10
            },
            "RB": {
                "defense": 0.30,
                "passing": 0.25,
                "possession": 0.20,
                "shooting": 0.15,
                "goalkeeper": 0.10
            },
            "WB": {
                "defense": 0.25,
                "passing": 0.25,
                "possession": 0.20,
                "shooting": 0.20,
                "goalkeeper": 0.10
            },
            # Midfielder weights
            "DM": {
                "defense": 0.30,
                "passing": 0.30,
                "possession": 0.25,
                "shooting": 0.10,
                "goalkeeper": 0.05
            },
            "CM": {
                "passing": 0.30,
                "possession": 0.25,
                "defense": 0.20,
                "shooting": 0.20,
                "goalkeeper": 0.05
            },
            "AM": {
                "passing": 0.30,
                "shooting": 0.25,
                "possession": 0.25,
                "defense": 0.15,
                "goalkeeper": 0.05
            },
            "LM": {
                "passing": 0.25,
                "possession": 0.25,
                "shooting": 0.20,
                "defense": 0.20,
                "goalkeeper": 0.10
            },
            "RM": {
                "passing": 0.25,
                "possession": 0.25,
                "shooting": 0.20,
                "defense": 0.20,
                "goalkeeper": 0.10
            },
            # Forward weights
            "ST": {
                "shooting": 0.40,
                "possession": 0.25,
                "passing": 0.20,
                "defense": 0.10,
                "goalkeeper": 0.05
            },
            "CF": {
                "shooting": 0.35,
                "possession": 0.25,
                "passing": 0.25,
                "defense": 0.10,
                "goalkeeper": 0.05
            },
            "LW": {
                "shooting": 0.30,
                "possession": 0.25,
                "passing": 0.25,
                "defense": 0.15,
                "goalkeeper": 0.05
            },
            "RW": {
                "shooting": 0.30,
                "possession": 0.25,
                "passing": 0.25,
                "defense": 0.15,
                "goalkeeper": 0.05
            },
            "SS": {
                "shooting": 0.35,
                "passing": 0.25,
                "possession": 0.25,
                "defense": 0.10,
                "goalkeeper": 0.05
            }
        }
        
        # Return weights for specific position or default to balanced weights
        return weights.get(position, {
            "shooting": 0.20,
            "passing": 0.20,
            "defense": 0.20,
            "possession": 0.20,
            "goalkeeper": 0.20
        })


class Foot(str, Enum):
    """Player's preferred foot."""
    LEFT = "Left"
    RIGHT = "Right"
    BOTH = "Both"


class StatsBase(BaseModel):
    """Base class for statistics with common fields."""
    matches_played: Optional[int] = Field(None, ge=0, description="Number of matches played")
    starts: Optional[int] = Field(None, ge=0, description="Number of matches started")
    minutes: Optional[int] = Field(None, ge=0, description="Total minutes played")
    
    @validator('starts')
    def starts_cannot_exceed_matches(cls, v, values):
        if v is not None and values.get('matches_played') is not None:
            if v > values['matches_played']:
                raise ValueError('Starts cannot exceed matches played')
        return v


class GeneralStats(StatsBase):
    """General player statistics."""
    goals: Optional[float] = Field(None, ge=0, description="Goals scored")
    assists: Optional[float] = Field(None, ge=0, description="Assists provided")
    goals_and_assists: Optional[float] = Field(None, ge=0, description="Goals + assists")
    non_penalty_goals: Optional[float] = Field(None, ge=0, description="Non-penalty goals")
    expected_goals: Optional[float] = Field(None, ge=0, description="Expected goals (xG)")
    expected_assists: Optional[float] = Field(None, ge=0, description="Expected assists (xA)")
    penalty_goals: Optional[float] = Field(None, ge=0, description="Penalty goals scored")
    penalty_attempts: Optional[float] = Field(None, ge=0, description="Penalty attempts")
    yellow_cards: Optional[int] = Field(None, ge=0, description="Yellow cards received")
    red_cards: Optional[int] = Field(None, ge=0, description="Red cards received")
    
    # Per 90 statistics
    goals_per_90: Optional[float] = Field(None, ge=0, description="Goals per 90 minutes")
    assists_per_90: Optional[float] = Field(None, ge=0, description="Assists per 90 minutes")
    goals_and_assists_per_90: Optional[float] = Field(None, ge=0, description="Goals + assists per 90")
    non_penalty_goals_per_90: Optional[float] = Field(None, ge=0, description="Non-penalty goals per 90")
    expected_goals_per_90: Optional[float] = Field(None, ge=0, description="Expected goals per 90")
    expected_assists_per_90: Optional[float] = Field(None, ge=0, description="Expected assists per 90")


class ShootingStats(BaseModel):
    """Shooting statistics."""
    shots: Optional[int] = Field(None, ge=0, description="Total shots")
    shots_on_target: Optional[int] = Field(None, ge=0, description="Shots on target")
    shot_accuracy: Optional[float] = Field(None, ge=0, le=100, description="Shot accuracy percentage")
    goals_per_shot: Optional[float] = Field(None, ge=0, le=1, description="Goals per shot")
    goals_per_shot_on_target: Optional[float] = Field(None, ge=0, le=1, description="Goals per shot on target")
    average_shot_distance: Optional[float] = Field(None, ge=0, description="Average shot distance in yards")
    free_kick_shots: Optional[int] = Field(None, ge=0, description="Free kick shots")
    non_penalty_expected_goals_per_shot: Optional[float] = Field(None, description="Non-penalty xG per shot")
    goals_minus_expected_goals: Optional[float] = Field(None, description="Goals minus expected goals")


class PassingStats(BaseModel):
    """Passing statistics."""
    passes_completed: Optional[int] = Field(None, ge=0, description="Passes completed")
    passes_attempted: Optional[int] = Field(None, ge=0, description="Passes attempted")
    pass_completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Pass completion percentage")
    total_pass_distance: Optional[float] = Field(None, ge=0, description="Total pass distance in yards")
    
    # Pass types
    short_passes_completed: Optional[int] = Field(None, ge=0, description="Short passes completed")
    short_passes_attempted: Optional[int] = Field(None, ge=0, description="Short passes attempted")
    short_pass_completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Short pass completion rate")
    
    medium_passes_completed: Optional[int] = Field(None, ge=0, description="Medium passes completed")
    medium_passes_attempted: Optional[int] = Field(None, ge=0, description="Medium passes attempted")
    medium_pass_completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Medium pass completion rate")
    
    long_passes_completed: Optional[int] = Field(None, ge=0, description="Long passes completed")
    long_passes_attempted: Optional[int] = Field(None, ge=0, description="Long passes attempted")
    long_pass_completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Long pass completion rate")
    
    # Advanced passing
    expected_assists: Optional[float] = Field(None, description="Expected assists (xA)")
    assists_minus_expected_assists: Optional[float] = Field(None, description="Assists minus expected assists")
    progressive_passes: Optional[int] = Field(None, ge=0, description="Progressive passes")
    progressive_pass_distance: Optional[float] = Field(None, ge=0, description="Progressive pass distance")
    key_passes: Optional[int] = Field(None, ge=0, description="Key passes")
    passes_into_final_third: Optional[int] = Field(None, ge=0, description="Passes into final third")
    passes_into_penalty_area: Optional[int] = Field(None, ge=0, description="Passes into penalty area")
    crosses_into_penalty_area: Optional[int] = Field(None, ge=0, description="Crosses into penalty area")


class PassingTypesStats(BaseModel):
    """Detailed passing type statistics."""
    live_passes: Optional[int] = Field(None, ge=0, description="Live ball passes")
    dead_ball_passes: Optional[int] = Field(None, ge=0, description="Dead ball passes")
    free_kick_passes: Optional[int] = Field(None, ge=0, description="Free kick passes")
    through_balls: Optional[int] = Field(None, ge=0, description="Through balls")
    switches: Optional[int] = Field(None, ge=0, description="Switches of play")
    crosses: Optional[int] = Field(None, ge=0, description="Crosses")
    passes_offside: Optional[int] = Field(None, ge=0, description="Passes that resulted in offside")
    passes_blocked: Optional[int] = Field(None, ge=0, description="Passes blocked by defenders")
    throw_ins: Optional[int] = Field(None, ge=0, description="Throw-ins taken")
    corner_kicks: Optional[int] = Field(None, ge=0, description="Corner kicks taken")
    corner_kicks_in_swinger: Optional[int] = Field(None, ge=0, description="In-swinging corner kicks")
    corner_kicks_out_swinger: Optional[int] = Field(None, ge=0, description="Out-swinging corner kicks")
    corner_kicks_straight: Optional[int] = Field(None, ge=0, description="Straight corner kicks")


class GoalCreationStats(BaseModel):
    """Goal creation and shot creation actions."""
    total_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Total shot creating actions")
    shot_creating_actions_per_90: Optional[float] = Field(None, ge=0, description="Shot creating actions per 90")
    
    # Shot creating action types
    pass_live_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from live passes")
    pass_dead_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from dead ball passes")
    take_on_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from take-ons")
    shot_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from shots")
    foul_drawn_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from fouls drawn")
    defensive_action_shot_creating_actions: Optional[int] = Field(None, ge=0, description="Shot creating actions from defensive actions")
    
    # Goal creating actions
    total_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Total goal creating actions")
    goal_creating_actions_per_90: Optional[float] = Field(None, ge=0, description="Goal creating actions per 90")
    
    # Goal creating action types
    pass_live_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from live passes")
    pass_dead_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from dead ball passes")
    take_on_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from take-ons")
    shot_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from shots")
    foul_drawn_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from fouls drawn")
    defensive_action_goal_creating_actions: Optional[int] = Field(None, ge=0, description="Goal creating actions from defensive actions")


class DefenseStats(BaseModel):
    """Defensive statistics."""
    tackles: Optional[int] = Field(None, ge=0, description="Total tackles")
    tackles_won: Optional[int] = Field(None, ge=0, description="Tackles won")
    tackle_win_rate: Optional[float] = Field(None, ge=0, le=100, description="Tackle win rate percentage")
    
    # Tackles by field position
    tackles_defensive_third: Optional[int] = Field(None, ge=0, description="Tackles in defensive third")
    tackles_middle_third: Optional[int] = Field(None, ge=0, description="Tackles in middle third")
    tackles_attacking_third: Optional[int] = Field(None, ge=0, description="Tackles in attacking third")
    
    # Dribbler tackles
    tackles_vs_dribbles: Optional[int] = Field(None, ge=0, description="Tackles vs dribbles")
    dribbles_challenged: Optional[int] = Field(None, ge=0, description="Dribbles challenged")
    dribble_tackle_success_rate: Optional[float] = Field(None, ge=0, le=100, description="Dribble tackle success rate")
    
    # Other defensive actions
    blocks: Optional[int] = Field(None, ge=0, description="Total blocks")
    shots_blocked: Optional[int] = Field(None, ge=0, description="Shots blocked")
    interceptions: Optional[int] = Field(None, ge=0, description="Interceptions")
    tackles_plus_interceptions: Optional[int] = Field(None, ge=0, description="Tackles plus interceptions")
    clearances: Optional[int] = Field(None, ge=0, description="Clearances")
    defensive_errors: Optional[int] = Field(None, ge=0, description="Defensive errors")


class PossessionStats(BaseModel):
    """Possession and ball control statistics."""
    touches: Optional[int] = Field(None, ge=0, description="Total touches")
    
    # Touches by field position
    touches_defensive_box: Optional[int] = Field(None, ge=0, description="Touches in defensive box")
    touches_defensive_third: Optional[int] = Field(None, ge=0, description="Touches in defensive third")
    touches_middle_third: Optional[int] = Field(None, ge=0, description="Touches in middle third")
    touches_final_third: Optional[int] = Field(None, ge=0, description="Touches in final third")
    touches_penalty_area: Optional[int] = Field(None, ge=0, description="Touches in penalty area")
    
    # Take-ons
    take_ons_attempted: Optional[int] = Field(None, ge=0, description="Take-ons attempted")
    take_ons_completed: Optional[int] = Field(None, ge=0, description="Take-ons completed")
    take_on_success_rate: Optional[float] = Field(None, ge=0, le=100, description="Take-on success rate")
    take_ons_tackled: Optional[int] = Field(None, ge=0, description="Take-ons tackled")
    take_on_tackle_rate: Optional[float] = Field(None, ge=0, le=100, description="Take-on tackle rate")
    
    # Carries
    carries: Optional[int] = Field(None, ge=0, description="Total carries")
    total_carry_distance: Optional[float] = Field(None, ge=0, description="Total carry distance in yards")
    progressive_carry_distance: Optional[float] = Field(None, ge=0, description="Progressive carry distance")
    carries_into_final_third: Optional[int] = Field(None, ge=0, description="Carries into final third")
    carries_into_penalty_area: Optional[int] = Field(None, ge=0, description="Carries into penalty area")
    carries_miscontrolled: Optional[int] = Field(None, ge=0, description="Carries miscontrolled")
    carries_dispossessed: Optional[int] = Field(None, ge=0, description="Carries dispossessed")
    
    # Pass receiving
    passes_received: Optional[int] = Field(None, ge=0, description="Passes received")
    progressive_passes_received: Optional[int] = Field(None, ge=0, description="Progressive passes received")


class GoalkeeperStats(BaseModel):
    """Goalkeeper-specific statistics."""
    goals_against: Optional[int] = Field(None, ge=0, description="Goals conceded")
    goals_against_per_90: Optional[float] = Field(None, ge=0, description="Goals conceded per 90 minutes")
    shots_on_target_against: Optional[int] = Field(None, ge=0, description="Shots on target against")
    saves: Optional[int] = Field(None, ge=0, description="Saves made")
    save_percentage: Optional[float] = Field(None, ge=0, le=100, description="Save percentage")
    clean_sheets: Optional[int] = Field(None, ge=0, description="Clean sheets")
    clean_sheet_percentage: Optional[float] = Field(None, ge=0, le=100, description="Clean sheet percentage")
    
    # Penalty statistics
    penalty_attempts_against: Optional[int] = Field(None, ge=0, description="Penalty attempts against")
    penalties_saved: Optional[int] = Field(None, ge=0, description="Penalties saved")
    penalty_save_percentage: Optional[float] = Field(None, ge=0, le=100, description="Penalty save percentage")
    
    # Advanced goalkeeper stats
    post_shot_expected_goals: Optional[float] = Field(None, description="Post-shot expected goals (PSxG)")
    post_shot_expected_goals_per_shot_on_target: Optional[float] = Field(None, description="PSxG per shot on target")
    goals_against_minus_post_shot_expected_goals: Optional[float] = Field(None, description="Goals against minus PSxG")
    
    # Distribution
    launched_passes_completed: Optional[int] = Field(None, ge=0, description="Launched passes completed")
    launched_passes_attempted: Optional[int] = Field(None, ge=0, description="Launched passes attempted")
    launched_pass_completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Launched pass completion rate")
    passes_attempted: Optional[int] = Field(None, ge=0, description="Passes attempted")
    throws_attempted: Optional[int] = Field(None, ge=0, description="Throws attempted")
    percentage_passes_launched: Optional[float] = Field(None, ge=0, le=100, description="Percentage of passes launched")
    average_pass_length: Optional[float] = Field(None, ge=0, description="Average pass length in yards")
    
    # Goalkeeper actions
    goalkeeper_actions: Optional[int] = Field(None, ge=0, description="Goalkeeper actions")
    percentage_goalkeeper_launches: Optional[float] = Field(None, ge=0, le=100, description="Percentage of goalkeeper launches")
    average_goalkeeper_length: Optional[float] = Field(None, ge=0, description="Average goalkeeper action length")
    
    # Crosses
    crosses_faced: Optional[int] = Field(None, ge=0, description="Crosses faced")
    crosses_stopped: Optional[int] = Field(None, ge=0, description="Crosses stopped")
    cross_stop_percentage: Optional[float] = Field(None, ge=0, le=100, description="Cross stop percentage")
    
    # Defensive actions
    defensive_actions_outside_box: Optional[int] = Field(None, ge=0, description="Defensive actions outside box")
    average_distance_defensive_actions: Optional[float] = Field(None, ge=0, description="Average distance of defensive actions")


class PlayingTimeStats(BaseModel):
    """Playing time and availability statistics."""
    minutes_per_match_played: Optional[float] = Field(None, ge=0, le=90, description="Minutes per match played")
    percentage_squad_minutes: Optional[float] = Field(None, ge=0, le=100, description="Percentage of squad minutes")
    average_minutes_as_starter: Optional[float] = Field(None, ge=0, le=90, description="Average minutes as starter")
    substitutions: Optional[int] = Field(None, ge=0, description="Number of substitutions")
    average_minutes_as_sub: Optional[float] = Field(None, ge=0, le=90, description="Average minutes as substitute")
    unused_substitutions: Optional[int] = Field(None, ge=0, description="Unused substitutions")
    
    # Team performance when on pitch
    team_goals_on_pitch: Optional[int] = Field(None, ge=0, description="Team goals when player on pitch")
    team_goals_against_on_pitch: Optional[int] = Field(None, ge=0, description="Team goals against when player on pitch")
    plus_minus_per_90: Optional[str] = Field(None, description="Plus-minus per 90 minutes")
    on_off_plus_minus: Optional[str] = Field(None, description="On-off plus-minus")
    
    # Expected goals when on pitch
    team_expected_goals_on_pitch: Optional[float] = Field(None, description="Team xG when player on pitch")
    team_expected_goals_against_on_pitch: Optional[float] = Field(None, description="Team xGA when player on pitch")
    expected_plus_minus_per_90: Optional[str] = Field(None, description="Expected plus-minus per 90")
    on_off_expected_plus_minus: Optional[str] = Field(None, description="On-off expected plus-minus")


class MiscellaneousStats(BaseModel):
    """Miscellaneous statistics."""
    second_yellow_cards: Optional[int] = Field(None, ge=0, description="Second yellow cards")
    fouls_committed: Optional[int] = Field(None, ge=0, description="Fouls committed")
    fouls_drawn: Optional[int] = Field(None, ge=0, description="Fouls drawn")
    offsides: Optional[int] = Field(None, ge=0, description="Offsides")
    penalties_won: Optional[int] = Field(None, ge=0, description="Penalties won")
    penalties_conceded: Optional[int] = Field(None, ge=0, description="Penalties conceded")
    own_goals: Optional[int] = Field(None, ge=0, description="Own goals")
    ball_recoveries: Optional[int] = Field(None, ge=0, description="Ball recoveries")
    aerial_duels_won: Optional[int] = Field(None, ge=0, description="Aerial duels won")
    aerial_duels_lost: Optional[int] = Field(None, ge=0, description="Aerial duels lost")
    aerial_duel_win_rate: Optional[float] = Field(None, ge=0, le=100, description="Aerial duel win rate")


class PlayerStats(BaseModel):
    """Complete player statistics."""
    general: GeneralStats = Field(default_factory=GeneralStats, description="General statistics")
    shooting: ShootingStats = Field(default_factory=ShootingStats, description="Shooting statistics")
    passing: PassingStats = Field(default_factory=PassingStats, description="Passing statistics")
    passing_types: PassingTypesStats = Field(default_factory=PassingTypesStats, description="Passing type statistics")
    goal_creation: GoalCreationStats = Field(default_factory=GoalCreationStats, description="Goal creation statistics")
    defense: DefenseStats = Field(default_factory=DefenseStats, description="Defensive statistics")
    possession: PossessionStats = Field(default_factory=PossessionStats, description="Possession statistics")
    goalkeeper: Optional[GoalkeeperStats] = Field(None, description="Goalkeeper statistics (if applicable)")
    playing_time: PlayingTimeStats = Field(default_factory=PlayingTimeStats, description="Playing time statistics")
    miscellaneous: MiscellaneousStats = Field(default_factory=MiscellaneousStats, description="Miscellaneous statistics")


class PlayerMetadata(BaseModel):
    """Player metadata and personal information."""
    player_id: str = Field(..., description="Unique player identifier")
    full_name: str = Field(..., description="Player's full name")
    positions: List[Position] = Field(..., description="Positions the player can play")
    footed: Optional[Foot] = Field(None, description="Player's preferred foot")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    birth_city: Optional[str] = Field(None, description="City of birth")
    nationality: Optional[str] = Field(None, description="Player's nationality")
    wages: Optional[str] = Field(None, description="Player's wages")
    height: Optional[float] = Field(None, ge=0, description="Height in centimeters")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kilograms")
    photo_url: Optional[str] = Field(None, description="URL to player photo")
    birth_country: Optional[str] = Field(None, description="Country of birth")
    gender: str = Field("M", description="Player gender (M/F) - currently M only")


class Player(BaseModel):
    """Complete player model with metadata and statistics."""
    metadata: PlayerMetadata = Field(..., description="Player metadata")
    stats: PlayerStats = Field(default_factory=PlayerStats, description="Player statistics")
    
    # Additional fields for StatTwin
    age: Optional[int] = Field(None, ge=16, le=50, description="Player's age")
    league: Optional[str] = Field(None, description="Current league")
    team: Optional[str] = Field(None, description="Current team")
    season: Optional[str] = Field(None, description="Season")
    continent: Optional[str] = Field(None, description="Continent")
    status: str = Field("Active", description="Player status: Active/Retired/Unknown")
    is_active: bool = Field(True, description="Whether player is currently active")
    
    @property
    def primary_position(self) -> str:
        """Get the primary position (first position in the list)."""
        return self.metadata.positions[0].value if self.metadata.positions else "Unknown"
    
    @property
    def position_group(self) -> str:
        """Get the general position group."""
        return Position.get_position_group(self.primary_position)
    
    @property
    def position_weights(self) -> Dict[str, float]:
        """Get position-specific weights for similarity calculations."""
        return Position.get_position_weights(self.primary_position)
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "player_id": "92e7e919",
                    "full_name": "Son Heung-min",
                    "positions": ["LW", "ST"],
                    "footed": "Left",
                    "date_of_birth": "1992-07-08",
                    "nationality": "South Korea",
                    "height": 183.0,
                    "weight": 78.0,
                    "gender": "M"
                },
                "age": 31,
                "league": "Premier League",
                "team": "Tottenham Hotspur",
                "season": "2023-2024",
                "continent": "Asia",
                "status": "Active",
                "is_active": True
            }
        }
