"""
Skill Context Module.

Provides context information for skill activation checks.
The SkillContext contains all relevant race state needed to determine
if a skill's conditions are met.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class SessionType(Enum):
    """Type of racing session."""

    PRACTICE = "practice"
    QUALIFYING_Q1 = "q1"
    QUALIFYING_Q2 = "q2"
    QUALIFYING_Q3 = "q3"
    RACE = "race"
    SPRINT = "sprint"


class WeatherCondition(Enum):
    """Weather conditions."""

    DRY = "dry"
    LIGHT_RAIN = "light_rain"
    MODERATE_RAIN = "moderate_rain"
    HEAVY_RAIN = "heavy_rain"
    TORRENTIAL_RAIN = "torrential_rain"


class TrackCondition(Enum):
    """Track surface condition."""

    DRY = "dry"
    DAMP = "damp"
    WET = "wet"
    FLOODED = "flooded"


@dataclass
class SkillContext:
    """
        Context for skill activation checks.

        This class encapsulates all relevant race state information needed
    to determine if a skill's trigger conditions are met.

        Attributes:
            session_type: Type of session (race, qualifying, etc.)
            lap_number: Current lap number
            total_laps: Total laps in race

            # Weather
            weather_condition: Current weather
            track_condition: Current track condition
            rain_intensity: 0-1 scale of rain intensity

            # Position and racing
            position: Current race position
            is_defending: Whether driver is defending a position
            is_attacking: Whether driver is attacking/overtaking
            is_in_drs_zone: Whether driver is currently in DRS zone
            drs_zone_consecutive_laps: Consecutive laps in DRS zone
            gap_to_ahead: Time gap to car ahead (seconds)
            gap_to_behind: Time gap to car behind (seconds)

            # Teammate info
            teammate_name: Name of teammate
            teammate_position: Teammate's position
            teammate_gap: Gap to teammate (negative if ahead)
            is_behind_teammate: Whether driver is behind teammate
            teammate_has_direct_threat: Whether teammate is under threat

            # Opponent info (for VS_SPECIFIC_DRIVER skills)
            opponent_name: Name of opponent being raced
            opponent_is_specific_target: Whether opponent is a specific rival

            # Tire info
            tire_compound: Current tire compound
            tire_age: Laps on current tires
            is_past_tire_cliff: Whether past tire degradation cliff
            tire_degradation_factor: Current degradation factor
            has_fresh_tires: Whether tires are fresh (< 3 laps)

            # Race state
            is_race_start: Whether this is the start phase (laps 1-2)
            is_first_lap: Whether this is lap 1
            is_danger_situation: Whether in danger (Q1/Q2 cutoff, etc.)
            is_forming_train: Whether a train is forming behind
            is_in_multi_car_train: Whether this overtake is within a multi-car train (3+ cars within 1s)

            # Stint info
            stint_number: Current stint number
            laps_since_pit: Laps since last pit stop

            # Team orders
            team_order_issued: Whether a team order was issued
            team_order_to_let_through: Whether order is to let teammate through
            team_order_to_defend: Whether order is to defend teammate

            # Incident info
            incident_ahead: Whether there's an incident ahead
            incident_distance: Distance to incident (seconds)
            is_in_incident_zone: Whether driver is in incident zone

            # Qualifying specific
            qualifying_cutoff_position: Position that gets eliminated
            is_in_danger_zone: Whether in elimination zone

            # Race progress
            race_progress_pct: Race progress (0.0 to 1.0)

            # Additional data (for extensibility)
            extra_data: Dict for additional context-specific data
    """

    # Session info
    session_type: SessionType = SessionType.RACE
    lap_number: int = 1
    total_laps: int = 66

    # Weather
    weather_condition: WeatherCondition = WeatherCondition.DRY
    track_condition: TrackCondition = TrackCondition.DRY
    rain_intensity: float = 0.0

    # Position and racing
    position: int = 1
    is_defending: bool = False
    is_attacking: bool = False
    is_in_drs_zone: bool = False
    drs_zone_consecutive_laps: int = 0
    gap_to_ahead: float = float("inf")
    gap_to_behind: float = float("inf")

    # Teammate info
    teammate_name: Optional[str] = None
    teammate_position: Optional[int] = None
    teammate_gap: Optional[float] = None
    is_behind_teammate: bool = False
    teammate_has_direct_threat: bool = False

    # Opponent info
    opponent_name: Optional[str] = None
    opponent_is_specific_target: bool = False

    # Tire info
    tire_compound: str = "MEDIUM"
    tire_age: int = 0
    is_past_tire_cliff: bool = False
    tire_degradation_factor: float = 1.0
    has_fresh_tires: bool = True

    # Race state
    is_race_start: bool = False
    is_first_lap: bool = False
    is_danger_situation: bool = False
    is_forming_train: bool = False
    is_in_multi_car_train: bool = False

    # Stint info
    stint_number: int = 1
    laps_since_pit: int = 0

    # Team orders
    team_order_issued: bool = False
    team_order_to_let_through: bool = False
    team_order_to_defend: bool = False
    team_order_active: bool = False  # 当前是否处于车队指令生效状态
    team_order_target: Optional[str] = None  # 让车指令的目标车手
    team_order_beneficiary: Optional[str] = None  # 让车指令的受益车手
    team_order_mode: Optional[str] = None  # 车队指令模式: "yield", "defend", "swap"

    # Incident info
    incident_ahead: bool = False
    incident_distance: float = float("inf")
    is_in_incident_zone: bool = False
    is_losing_control: bool = False

    # Qualifying specific
    qualifying_cutoff_position: int = 15
    is_in_danger_zone: bool = False

    # Race progress
    race_progress_pct: float = 0.0

    # Additional data
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def is_qualifying(self) -> bool:
        """Check if current session is qualifying."""
        return self.session_type in [
            SessionType.QUALIFYING_Q1,
            SessionType.QUALIFYING_Q2,
            SessionType.QUALIFYING_Q3,
        ]

    def get_qualifying_stage(self) -> Optional[str]:
        """Get qualifying stage (Q1/Q2/Q3) if in qualifying."""
        if self.session_type == SessionType.QUALIFYING_Q1:
            return "Q1"
        elif self.session_type == SessionType.QUALIFYING_Q2:
            return "Q2"
        elif self.session_type == SessionType.QUALIFYING_Q3:
            return "Q3"
        return None

    def is_raining(self) -> bool:
        """Check if it's currently raining."""
        return self.weather_condition in [
            WeatherCondition.LIGHT_RAIN,
            WeatherCondition.MODERATE_RAIN,
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.TORRENTIAL_RAIN,
        ]

    def is_heavy_rain(self) -> bool:
        """Check if it's heavy rain."""
        return self.weather_condition in [
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.TORRENTIAL_RAIN,
        ]

    def is_in_danger(self) -> bool:
        """
        Check if driver is in danger situation.

        In qualifying: in elimination zone
        In race: significant gap behind with threat
        """
        if self.is_qualifying():
            return self.is_in_danger_zone
        return self.is_danger_situation

    def is_teammate_directly_ahead(self) -> bool:
        """Check if teammate is directly ahead (within 2 seconds)."""
        if self.teammate_gap is None:
            return False
        return self.teammate_gap > 0 and self.teammate_gap < 2.0

    def is_teammate_under_threat(self) -> bool:
        """Check if teammate is under direct threat from behind."""
        return self.teammate_has_direct_threat

    def is_team_order_active(self) -> bool:
        """Check if a team order is currently active."""
        return self.team_order_active or self.team_order_issued

    def is_yield_order(self) -> bool:
        """Check if current team order is to yield position."""
        return (
            self.team_order_active
            and self.team_order_mode == "yield"
            and self.team_order_to_let_through
        )

    def is_defend_order(self) -> bool:
        """Check if current team order is to defend position."""
        return (
            self.team_order_active
            and self.team_order_mode == "defend"
            and self.team_order_to_defend
        )

    def is_helping_teammate_scenario(
        self,
        teammate_name: str,
        third_driver_in_train: bool = True,
    ) -> bool:
        """
        Check if this is a "好大哥" (Bottas helping Zhou) scenario.

        Conditions:
        1. Team order active or overtake mode
        2. Driver, teammate, and third driver are in a train
        3. Teammate is behind

        Args:
            teammate_name: Name of teammate to help
            third_driver_in_train: Whether there's a third driver in the train

        Returns:
            True if all conditions are met
        """
        # Check if team order is active or in overtake/attack mode
        if not (self.team_order_active or self.is_attacking or self.is_defending):
            return False

        # Check if teammate matches
        if self.teammate_name != teammate_name:
            return False

        # Check if teammate is behind (gap positive means we're ahead)
        if not self.is_behind_teammate:
            return False

        # Check if in multi-car train (optional)
        if third_driver_in_train and not self.is_in_multi_car_train:
            return False

        return True

    def is_vs_driver(self, driver_name: str) -> bool:
        """Check if currently racing against specific driver."""
        return self.opponent_name == driver_name

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "session_type": self.session_type.value,
            "lap_number": self.lap_number,
            "weather": self.weather_condition.value,
            "position": self.position,
            "is_defending": self.is_defending,
            "is_attacking": self.is_attacking,
            "is_in_drs_zone": self.is_in_drs_zone,
            "drs_consecutive_laps": self.drs_zone_consecutive_laps,
            "tire_compound": self.tire_compound,
            "tire_age": self.tire_age,
            "is_past_cliff": self.is_past_tire_cliff,
            "opponent": self.opponent_name,
        }

    @classmethod
    def from_race_state(
        cls,
        driver: str,
        race_state: Any,
        driver_data: Dict,
        session_type: str = "race",
    ) -> "SkillContext":
        """
        Create SkillContext from race state.

        This is a factory method to create context from the simulation's
        race state object.

        Args:
            driver: Driver name
            race_state: RaceState object from simulation
            driver_data: Driver data dictionary
            session_type: Type of session

        Returns:
            SkillContext populated from race state
        """
        # This will be implemented when integrating with simulation
        context = cls()

        # Map session type
        session_map = {
            "q1": SessionType.QUALIFYING_Q1,
            "q2": SessionType.QUALIFYING_Q2,
            "q3": SessionType.QUALIFYING_Q3,
            "race": SessionType.RACE,
            "sprint": SessionType.SPRINT,
        }
        context.session_type = session_map.get(session_type.lower(), SessionType.RACE)

        # Populate from race state (to be implemented)
        # This is a placeholder - actual implementation will extract
        # data from the race state object

        return context
