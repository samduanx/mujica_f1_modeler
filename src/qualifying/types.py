"""
Qualifying Types Module

Core data structures for the F1 Qualification System.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any


class QualifyingSessionType(Enum):
    """Type of qualifying session."""
    STANDARD = "standard"      # Q1/Q2/Q3 for Grand Prix
    SPRINT = "sprint"          # SQ1/SQ2/SQ3 for Sprint race
    ATA = "ata"                # Alternative Tyre Allocation


class FlagState(Enum):
    """Flag states during qualifying."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class QualifyingLap:
    """A complete qualifying lap attempt."""
    driver: str
    session: str  # "Q1", "Q2", "Q3", "SQ1", "SQ2", "SQ3"
    
    # Lap phases (all times in seconds)
    out_lap_time: float = 0.0
    flying_lap_time: float = 0.0
    in_lap_time: float = 0.0
    total_time: float = 0.0
    
    # Timing
    release_time: float = 0.0  # Time released from pits
    crossing_time: float = 0.0  # Time crossed start/finish
    
    # Tyre info
    tyre_compound: str = ""
    tyre_condition: str = "new"  # new, scrubbed, used
    tyre_temperature: float = 0.0  # Operating window critical
    
    # Track conditions
    track_condition: str = "dry"
    track_temperature: float = 0.0
    track_evolution: float = 0.0  # Track grip improvement
    
    # Incidents
    traffic_encountered: bool = False
    traffic_impact: float = 0.0  # Time lost to traffic
    drs_used: bool = False
    drs_zones_used: int = 0
    
    # Result
    valid_lap: bool = True
    deleted_lap: bool = False  # Track limits violation
    best_lap: bool = False


@dataclass
class QualifyingResult:
    """Complete qualifying result for a driver."""
    driver: str
    team: str
    q1_time: Optional[float] = None
    q2_time: Optional[float] = None
    q3_time: Optional[float] = None
    grid_position: int = 0
    race_start_tyre: str = ""  # Strategist decision (free choice for all in 2022+)
    eliminated_in: Optional[str] = None  # "Q1", "Q2", or None
    
    def get_best_time(self) -> Optional[float]:
        """Get best lap time across all sessions."""
        times = [t for t in [self.q1_time, self.q2_time, self.q3_time] if t is not None]
        return min(times) if times else None


@dataclass
class QualifyingSessionConfig:
    """Configuration for a qualifying session."""
    session_type: QualifyingSessionType = QualifyingSessionType.STANDARD
    
    # Session timings (minutes)
    q1_duration: int = 18
    q2_duration: int = 15
    q3_duration: int = 12
    
    # Sprint session timings
    sq1_duration: int = 12
    sq2_duration: int = 10
    sq3_duration: int = 8
    
    # Track characteristics
    track_name: str = ""
    track_length_km: float = 0.0
    base_lap_time: float = 0.0


@dataclass
class QualifyingSessionState:
    """Runtime state for a qualifying session."""
    session_name: str = ""  # "Q1", "Q2", "Q3", "SQ1", "SQ2", "SQ3"
    duration: float = 0.0  # seconds
    remaining_time: float = 0.0  # seconds
    clock_running: bool = True
    
    drivers_active: List[str] = field(default_factory=list)
    drivers_eliminated: List[str] = field(default_factory=list)
    best_times: Dict[str, float] = field(default_factory=dict)
    current_grid: Dict[str, int] = field(default_factory=dict)
    
    # Lap tracking
    laps_completed: Dict[str, List[QualifyingLap]] = field(default_factory=dict)
    
    # Session state
    flag_state: FlagState = FlagState.GREEN
    
    def get_standings(self) -> List[Tuple[str, float]]:
        """Get current standings sorted by lap time."""
        sorted_drivers = sorted(
            self.best_times.items(),
            key=lambda x: x[1] if x[1] is not None else float('inf')
        )
        return sorted_drivers
    
    def get_driver_position(self, driver: str) -> int:
        """Get current position of a driver."""
        standings = self.get_standings()
        for pos, (drv, _) in enumerate(standings, 1):
            if drv == driver:
                return pos
        return len(self.drivers_active) + len(self.drivers_eliminated)


@dataclass
class QualifyingIncident:
    """An incident during qualifying."""
    driver: str
    incident_type: str  # "crash", "spin", "off_track", "track_limits"
    severity: str  # "minor", "major", "critical"
    sector: int
    time_lost: float = 0.0
    flag_triggered: Optional[str] = None  # "yellow", "red", None
    lap_deleted: bool = False
    session_time: float = 0.0


@dataclass
class TyreAllocation:
    """Tyre allocation for a driver."""
    driver: str
    soft: int = 8
    medium: int = 3
    hard: int = 2
    inter: int = 4
    wet: int = 3
    
    # Track usage
    used_sets: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_available(self, compound: str) -> int:
        """Get available sets of a compound."""
        return getattr(self, compound.lower(), 0)
    
    def use_set(self, compound: str, session: str) -> bool:
        """Use a tyre set. Returns False if not available."""
        attr = compound.lower()
        current = getattr(self, attr, 0)
        if current <= 0:
            return False
        setattr(self, attr, current - 1)
        self.used_sets.append({
            "compound": compound,
            "session": session,
            "condition": "new"
        })
        return True


@dataclass
class QualifyingWeatherState:
    """Weather state during qualifying."""
    track_condition: str = "dry"  # dry, damp, wet
    rain_intensity: float = 0.0  # 0.0 - 1.0
    track_temperature: float = 25.0
    air_temperature: float = 22.0
    drs_enabled: bool = True


@dataclass
class QualifyingResults:
    """Complete qualifying session results."""
    session_type: QualifyingSessionType
    track_name: str
    results: List[QualifyingResult] = field(default_factory=list)
    
    # Session times
    q1_times: Dict[str, float] = field(default_factory=dict)
    q2_times: Dict[str, float] = field(default_factory=dict)
    q3_times: Dict[str, float] = field(default_factory=dict)
    
    # Race start tyres (all free choice in 2022+)
    race_start_tyres: Dict[str, str] = field(default_factory=dict)
    
    # Incidents and flags
    incidents: List[QualifyingIncident] = field(default_factory=list)
    
    # Weather log
    weather_changes: List[Tuple[float, QualifyingWeatherState]] = field(default_factory=list)
    
    def get_grid_positions(self) -> Dict[str, int]:
        """Get final grid positions."""
        return {r.driver: r.grid_position for r in self.results}
    
    def get_pole_sitter(self) -> Optional[str]:
        """Get pole position driver."""
        for r in self.results:
            if r.grid_position == 1:
                return r.driver
        return None
