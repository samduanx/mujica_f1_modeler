"""
Incident Types and Core Data Classes.

Defines the fundamental types and structures used throughout the incident system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class IncidentType(Enum):
    """Main incident categories"""

    OVERTAKE_COLLISION = "overtake_collision"
    DRIVER_ERROR = "driver_error"
    VEHICLE_FAULT = "vehicle_fault"
    DOUBLE_ATTACK = "double_attack"
    INCIDENT_DAMAGE = "incident_damage"
    BLUE_FLAG_VIOLATION = "blue_flag_violation"
    LAPPING_INCIDENT = "lapping_incident"


class IncidentSeverity(Enum):
    """Incident severity levels"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"


class TrackDifficulty(Enum):
    """Track difficulty classification for incident calculations"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def collision_risk_factor(self) -> float:
        """Get collision risk factor for track difficulty"""
        factors = {
            TrackDifficulty.LOW: 0.8,
            TrackDifficulty.MEDIUM: 1.0,
            TrackDifficulty.HIGH: 1.3,
        }
        return factors.get(self, 1.0)


@dataclass
class Incident:
    """
    Represents a race incident.

    Attributes:
        incident_id: Unique identifier for the incident
        incident_type: Type of incident
        time: Race time in seconds when incident occurred
        lap: Lap number when incident occurred
        driver: Name of the driver involved
        severity: Severity level of the incident
        description: Brief description of what happened
        position_impact: Number of positions lost/gained
        time_penalty: Seconds added to lap time
        is_retirement: Whether the incident caused retirement
        affected_drivers: List of other drivers affected
        narrative: Generated narrative text for the incident
    """

    incident_id: str
    incident_type: IncidentType
    time: float  # Race time in seconds
    lap: int
    driver: str
    severity: IncidentSeverity
    description: str
    position_impact: int = 0
    time_penalty: float = 0.0
    is_retirement: bool = False
    affected_drivers: List[str] = field(default_factory=list)
    narrative: str = ""

    def __post_init__(self):
        if self.affected_drivers is None:
            self.affected_drivers = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "incident_id": self.incident_id,
            "incident_type": self.incident_type.value,
            "time": self.time,
            "lap": self.lap,
            "driver": self.driver,
            "severity": self.severity.value,
            "description": self.description,
            "position_impact": self.position_impact,
            "time_penalty": self.time_penalty,
            "is_retirement": self.is_retirement,
            "affected_drivers": self.affected_drivers,
            "narrative": self.narrative,
        }

    def apply_time_penalty(self, driver_lap_times: List[float]) -> List[float]:
        """Apply time penalty to driver's lap times"""
        if self.time_penalty > 0 and driver_lap_times:
            # Add penalty to the lap where incident occurred
            last_lap_idx = -1
            driver_lap_times[last_lap_idx] += self.time_penalty
        return driver_lap_times


@dataclass
class IncidentConfig:
    """Configuration for incident system behavior"""

    # Probabilities (per simulation interval or lap)
    base_overtake_collision_prob: float = 0.03
    base_driver_error_prob: float = 0.02

    # Timing constraints
    min_interval_for_incident: float = 5.0  # Seconds
    max_incidents_per_race: int = 5

    # Feature flags
    enable_double_attack: bool = True
    enable_vehicle_faults: bool = True
    enable_driver_errors: bool = True

    # Track defaults
    default_track_difficulty: TrackDifficulty = TrackDifficulty.MEDIUM


@dataclass
class IncidentStatistics:
    """Statistics for incident analysis"""

    total_incidents: int = 0
    incidents_by_type: Dict[str, int] = field(default_factory=dict)
    incidents_by_driver: Dict[str, int] = field(default_factory=dict)
    incidents_by_severity: Dict[str, int] = field(default_factory=dict)

    retirements: int = 0
    total_time_lost: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_incidents": self.total_incidents,
            "incidents_by_type": self.incidents_by_type,
            "incidents_by_driver": self.incidents_by_driver,
            "incidents_by_severity": self.incidents_by_severity,
            "retirements": self.retirements,
            "total_time_lost": self.total_time_lost,
        }

    def add_incident(self, incident: Incident):
        """Add an incident to the statistics"""
        self.total_incidents += 1

        # Count by type
        inc_type = incident.incident_type.value
        self.incidents_by_type[inc_type] = self.incidents_by_type.get(inc_type, 0) + 1

        # Count by driver
        self.incidents_by_driver[incident.driver] = (
            self.incidents_by_driver.get(incident.driver, 0) + 1
        )

        # Count by severity
        severity = incident.severity.value
        self.incidents_by_severity[severity] = (
            self.incidents_by_severity.get(severity, 0) + 1
        )

        # Track retirements and time lost
        if incident.is_retirement:
            self.retirements += 1
        self.total_time_lost += incident.time_penalty
