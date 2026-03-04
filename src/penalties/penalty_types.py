"""
Penalty Types and Core Data Classes.

Defines the fundamental penalty types and structures used throughout the penalty system.
Based on FIA Formula 1 Sporting Regulations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class PenaltyType(Enum):
    """
    Types of penalties in F1 according to Sporting Regulations.

    Time penalties can be served:
    - At pit stop (if driver will pit)
    - After race (if driver won't pit)

    Drive-through and stop-and-go must be served during the race.
    """

    # Time penalties (added to race time)
    TIME_5S = "5s_time_penalty"
    TIME_10S = "10s_time_penalty"
    TIME_15S = "15s_time_penalty"

    # Drive-through penalty (must drive through pit lane)
    DRIVE_THROUGH = "drive_through"

    # Stop-and-go penalties (must stop in pit box)
    STOP_GO_5S = "stop_go_5s"
    STOP_GO_10S = "stop_go_10s"
    STOP_GO_15S = "stop_go_15s"

    # Grid penalties (for future races)
    GRID_DROP_5 = "grid_drop_5"
    GRID_DROP_10 = "grid_drop_10"
    BACK_OF_GRID = "back_of_grid"

    # Other penalties
    REPRIMAND = "reprimand"
    DISQUALIFICATION = "disqualification"
    RACE_BAN = "race_ban"

    # Non-penalty time losses (for incidents like unsafe release)
    TIME_LOSS = "time_loss"

    @property
    def time_seconds(self) -> Optional[float]:
        """Get time penalty value in seconds if applicable."""
        mapping = {
            PenaltyType.TIME_5S: 5.0,
            PenaltyType.TIME_10S: 10.0,
            PenaltyType.TIME_15S: 15.0,
            PenaltyType.DRIVE_THROUGH: 20.0,  # Approximate
            PenaltyType.STOP_GO_5S: 5.0,
            PenaltyType.STOP_GO_10S: 10.0,
            PenaltyType.STOP_GO_15S: 15.0,
        }
        return mapping.get(self)

    @property
    def default_points(self) -> int:
        """Get default penalty points for this type."""
        mapping = {
            PenaltyType.TIME_5S: 1,
            PenaltyType.TIME_10S: 2,
            PenaltyType.TIME_15S: 3,
            PenaltyType.DRIVE_THROUGH: 3,
            PenaltyType.STOP_GO_5S: 3,
            PenaltyType.STOP_GO_10S: 3,
            PenaltyType.STOP_GO_15S: 3,
            PenaltyType.GRID_DROP_5: 0,
            PenaltyType.GRID_DROP_10: 0,
            PenaltyType.BACK_OF_GRID: 0,
            PenaltyType.REPRIMAND: 0,
            PenaltyType.DISQUALIFICATION: 0,
            PenaltyType.RACE_BAN: 0,
            PenaltyType.TIME_LOSS: 0,  # No points for time losses (like unsafe release)
        }
        return mapping.get(self, 0)

    @property
    def is_served_at_pit(self) -> bool:
        """Whether this penalty must be served during a pit stop."""
        return self in [
            PenaltyType.TIME_5S,
            PenaltyType.TIME_10S,
            PenaltyType.TIME_15S,
            PenaltyType.DRIVE_THROUGH,
            PenaltyType.STOP_GO_5S,
            PenaltyType.STOP_GO_10S,
            PenaltyType.STOP_GO_15S,
        ]

    @property
    def is_grid_penalty(self) -> bool:
        """Whether this is a grid penalty for a future race."""
        return self in [
            PenaltyType.GRID_DROP_5,
            PenaltyType.GRID_DROP_10,
            PenaltyType.BACK_OF_GRID,
        ]


class PenaltyReason(Enum):
    """Common reasons for penalties in F1."""

    # Overtaking/Collision related
    CAUSING_COLLISION = "causing_collision"
    LEAVING_TRACK_GAINING_ADVANTAGE = "leaving_track_gaining_advantage"

    # Flag related
    BLUE_FLAG_VIOLATION = "blue_flag_violation"
    YELLOW_FLAG_VIOLATION = "yellow_flag_violation"
    VSC_VIOLATION = "vsc_violation"
    SC_VIOLATION = "sc_violation"

    # Pit lane
    UNSAFE_RELEASE = "unsafe_release"
    PIT_LANE_SPEEDING = "pit_lane_speeding"
    IMPEDING = "impeding"

    # Race conduct
    WEAVING = "weaving"
    RELEASING_CAR_DANGEROUSLY = "releasing_car_dangerously"

    # Other
    TECHNICAL_INFRACTION = "technical_infraction"
    OTHER = "other"


@dataclass
class Penalty:
    """
    Represents a penalty assessed to a driver.

    Attributes:
        penalty_id: Unique identifier for the penalty
        penalty_type: Type of penalty
        driver: Name of the driver penalized
        time_assessed: When penalty was given (race time in seconds)
        lap_assessed: Lap number when penalty was given
        reason: Description of the infraction
        reason_enum: Categorized reason for the penalty
        points: Penalty points (if any) - 12 points = race ban
        is_served: Whether the penalty has been served
        served_at: When/how the penalty was served
        served_at_lap: Lap when penalty was served (if applicable)
        time_served: Time penalty added to race (for post-race serving)
        additional_info: Any extra information
    """

    penalty_id: str
    penalty_type: PenaltyType
    driver: str
    time_assessed: float  # Race time in seconds
    lap_assessed: int
    reason: str
    reason_enum: Optional[PenaltyReason] = None
    points: int = 0
    is_served: bool = False
    served_at: Optional[str] = None  # "pit_stop" or "post_race"
    served_at_lap: Optional[int] = None
    time_served: float = 0.0  # Actual time added to race
    additional_info: Dict = field(default_factory=dict)

    def __post_init__(self):
        # Auto-set points from penalty type if not specified
        if self.points == 0:
            self.points = self.penalty_type.default_points

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "penalty_id": self.penalty_id,
            "penalty_type": self.penalty_type.value,
            "driver": self.driver,
            "time_assessed": self.time_assessed,
            "lap_assessed": self.lap_assessed,
            "reason": self.reason,
            "reason_enum": self.reason_enum.value if self.reason_enum else None,
            "points": self.points,
            "is_served": self.is_served,
            "served_at": self.served_at,
            "served_at_lap": self.served_at_lap,
            "time_served": self.time_served,
            "additional_info": self.additional_info,
        }


@dataclass
class TimeLoss:
    """
    Represents a time loss from incidents that don't carry penalty points.
    Used for things like unsafe releases where multiple drivers may be affected.
    """

    driver: str
    seconds: float
    reason: str
    time_assessed: float = 0.0
    lap_assessed: int = 0

    def to_dict(self) -> Dict:
        return {
            "driver": self.driver,
            "seconds": self.seconds,
            "reason": self.reason,
            "time_assessed": self.time_assessed,
            "lap_assessed": self.lap_assessed,
        }
