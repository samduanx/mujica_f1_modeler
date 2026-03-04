"""
Vehicle Fault System.

Handles vehicle component faults based on team stability ratings.
Based on dice_rolling_rules.md structure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random


class ComponentType(Enum):
    """Types of vehicle components"""

    ENGINE = "engine"
    HYBRID = "hybrid"
    BATTERY = "battery"
    CHASSIS = "chassis"
    SUSPENSION = "suspension"
    TYRE = "tyre"
    BRAKES = "brakes"
    AERODYNAMICS = "aerodynamics"


class FaultSeverity(Enum):
    """Severity levels for faults"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    TERMINAL = "terminal"  # Retirement required


@dataclass
class ComponentFault:
    """Represents a component failure"""

    component: str
    fault_type: str
    severity: FaultSeverity
    time_loss: float
    repairable: bool
    affected_systems: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "component": self.component,
            "fault_type": self.fault_type,
            "severity": self.severity.value,
            "time_loss": self.time_loss,
            "repairable": self.repairable,
            "affected_systems": self.affected_systems,
        }


@dataclass
class TeamStability:
    """
    Team's car stability configuration.

    Based on actual data from data/spain_team.csv:
    - Stability range: 95.0 - 98.5
    - Higher stability = lower fault probability
    """

    team_name: str
    base_stability: float  # 95-100, higher = more stable

    # Component-specific reliability (1-10, higher = more reliable)
    engine_reliability: int = 8
    hybrid_reliability: int = 8
    battery_reliability: int = 7
    chassis_reliability: int = 8
    suspension_reliability: int = 8
    tyre_reliability: int = 9
    brake_reliability: int = 8
    aero_reliability: int = 8

    def get_component_reliability(self, component: ComponentType) -> int:
        """Get reliability rating for a specific component"""
        reliability_map = {
            ComponentType.ENGINE: self.engine_reliability,
            ComponentType.HYBRID: self.hybrid_reliability,
            ComponentType.BATTERY: self.battery_reliability,
            ComponentType.CHASSIS: self.chassis_reliability,
            ComponentType.SUSPENSION: self.suspension_reliability,
            ComponentType.TYRE: self.tyre_reliability,
            ComponentType.BRAKES: self.brake_reliability,
            ComponentType.AERODYNAMICS: self.aero_reliability,
        }
        return reliability_map.get(component, 5)

    def get_fault_probability(
        self,
        laps_on_pu: int,
        race_distance_km: float,
        has_incident_damage: bool = False,
        lap_progress: float = 0.5,
    ) -> float:
        """
        Calculate base fault probability for this team.

        Based on dice_rolling_rules.md structure:
        - Stability >= 96: 81-90 = driver error, 91-100 = mechanical fault
        - Stability < 96: 91-100 = driver error, 81-90 = mechanical fault

        Args:
            laps_on_pu: Laps completed on current power unit
            race_distance_km: Total race distance
            has_incident_damage: Whether car has existing damage
            lap_progress: Progress through the current lap (0.0 to 1.0)

        Returns:
            Fault probability per lap
        """
        # Base probability from stability (inverse relationship)
        # Higher stability = lower fault probability
        # Range: 95 -> ~0.02, 98.5 -> ~0.007
        stability_factor = (100 - self.base_stability) / 250

        # PU age factor - faults increase with PU age
        # More significant in later stages of PU life
        pu_factor = (laps_on_pu / 50) * 0.01

        # Race distance factor
        distance_factor = race_distance_km / 300 * 0.005

        # Damage factor
        damage_factor = 0.0
        if has_incident_damage:
            damage_factor = 0.02

        # Lap position factor - faults more likely at certain lap points
        position_factor = 1.0
        if 0.3 < lap_progress < 0.4:  # Approaching pit window
            position_factor = 1.3

        total_prob = (
            stability_factor * position_factor
            + pu_factor
            + distance_factor
            + damage_factor
        )

        return min(0.08, max(0.005, total_prob))

    def get_mechanical_fault_threshold(self) -> int:
        """
        Get the threshold for mechanical fault roll.

        Based on stability:
        - Stability >= 96: Fault on 91-100
        - Stability < 96: Fault on 81-100
        """
        if self.base_stability >= 96:
            return 90  # Top 10% = fault
        else:
            return 80  # Top 20% = fault

    def get_driver_error_threshold(self) -> int:
        """
        Get the threshold for driver error roll.

        Based on stability:
        - Stability >= 96: Error on 81-90
        - Stability < 96: Error on 91-95
        """
        if self.base_stability >= 96:
            return 90  # 81-90 = error
        else:
            return 95  # 91-95 = error


class VehicleFaultResolver:
    """
    Handle vehicle component fault resolution.

    Based on dice_rolling_rules.md structure.
    """

    # Engine fault tables
    ENGINE_FAULTS = {
        (1, 3): {
            "type": "internal_combustion",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 15.0,
            "repairable": True,
        },
        (4, 6): {
            "type": "hybrid_system",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 12.0,
            "repairable": True,
        },
        (7, 9): {
            "type": "battery_issue",
            "severity": FaultSeverity.MODERATE,
            "time_loss": 8.0,
            "repairable": True,
        },
        (10, 10): {
            "type": "catastrophic_failure",
            "severity": FaultSeverity.TERMINAL,
            "time_loss": 0.0,
            "repairable": False,
        },
    }

    # Mechanical fault tables
    MECHANICAL_FAULTS = {
        (1, 3): {
            "type": "chassis_failure",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 20.0,
            "repairable": True,
        },
        (4, 6): {
            "type": "hydraulic_failure",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 15.0,
            "repairable": True,
        },
        (7, 9): {
            "type": "electrical_failure",
            "severity": FaultSeverity.MODERATE,
            "time_loss": 10.0,
            "repairable": True,
        },
        (10, 10): {
            "type": "catastrophic_failure",
            "severity": FaultSeverity.TERMINAL,
            "time_loss": 0.0,
            "repairable": False,
        },
    }

    # Tyre fault tables
    TYRE_FAULTS = {
        (1, 3): {
            "type": "debris_puncture",
            "severity": FaultSeverity.MODERATE,
            "time_loss": 3.0,
            "repairable": False,
        },
        (4, 6): {
            "type": "overheat_burst",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 5.0,
            "repairable": False,
        },
        (7, 9): {
            "type": "manufacturing_defect",
            "severity": FaultSeverity.MODERATE,
            "time_loss": 2.0,
            "repairable": False,
        },
        (10, 10): {
            "type": "structural_failure",
            "severity": FaultSeverity.MAJOR,
            "time_loss": 8.0,
            "repairable": False,
        },
    }

    def __init__(self, team_stability: TeamStability):
        """Initialize resolver with team stability"""
        self.stability = team_stability

    def check_for_fault(
        self,
        laps_on_pu: int,
        race_distance_km: float,
        has_incident_damage: bool = False,
        lap_progress: float = 0.5,
    ) -> Optional[ComponentFault]:
        """
        Check if a fault occurs for this team.

        Returns:
            ComponentFault if fault occurs, None otherwise
        """
        # Calculate fault probability
        prob = self.stability.get_fault_probability(
            laps_on_pu=laps_on_pu,
            race_distance_km=race_distance_km,
            has_incident_damage=has_incident_damage,
            lap_progress=lap_progress,
        )

        # Roll for fault
        if random.random() > prob:
            return None

        # Fault occurred - determine component
        component_roll = random.randint(1, 100)

        # Component selection table (based on reliability)
        if component_roll <= 30:
            return self._resolve_engine_fault()
        elif component_roll <= 50:
            return self._resolve_chassis_fault()
        elif component_roll <= 70:
            return self._resolve_suspension_fault()
        elif component_roll <= 85:
            return self._resolve_tyre_fault()
        else:
            return self._resolve_misc_fault()

    def check_mechanical_fault(self) -> Optional[ComponentFault]:
        """
        Check for mechanical fault using dice_rolling_rules.md thresholds.

        Returns:
            ComponentFault if fault occurs, None otherwise
        """
        roll = random.randint(1, 100)
        threshold = self.stability.get_mechanical_fault_threshold()

        if roll > threshold:
            # Determine fault type
            fault_roll = random.randint(1, 10)

            if fault_roll <= 5:
                return self._resolve_engine_fault()
            else:
                return self._resolve_mechanical_fault()

        return None

    def _resolve_engine_fault(self) -> ComponentFault:
        """Resolve engine-related fault"""
        roll = random.randint(1, 10)

        for range_roll, config in self.ENGINE_FAULTS.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return ComponentFault(
                    component="engine",
                    fault_type=config["type"],
                    severity=config["severity"],
                    time_loss=config["time_loss"],
                    repairable=config["repairable"],
                    affected_systems=["PU"]
                    if config["severity"] == FaultSeverity.MAJOR
                    else [],
                )

        return ComponentFault(
            component="engine",
            fault_type="unknown",
            severity=FaultSeverity.MINOR,
            time_loss=1.0,
            repairable=True,
            affected_systems=[],
        )

    def _resolve_mechanical_fault(self) -> ComponentFault:
        """Resolve mechanical-related fault"""
        roll = random.randint(1, 10)

        for range_roll, config in self.MECHANICAL_FAULTS.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return ComponentFault(
                    component="mechanical",
                    fault_type=config["type"],
                    severity=config["severity"],
                    time_loss=config["time_loss"],
                    repairable=config["repairable"],
                    affected_systems=[],
                )

        return ComponentFault(
            component="mechanical",
            fault_type="unknown",
            severity=FaultSeverity.MINOR,
            time_loss=1.0,
            repairable=True,
            affected_systems=[],
        )

    def _resolve_chassis_fault(self) -> ComponentFault:
        """Resolve chassis-related fault"""
        roll = random.randint(1, 10)

        if roll <= 5:
            return ComponentFault(
                component="chassis",
                fault_type="structural_damage",
                severity=FaultSeverity.MAJOR,
                time_loss=18.0,
                repairable=True,
                affected_systems=[],
            )
        else:
            return ComponentFault(
                component="chassis",
                fault_type="aero_damage",
                severity=FaultSeverity.MODERATE,
                time_loss=10.0,
                repairable=True,
                affected_systems=["aerodynamics"],
            )

    def _resolve_suspension_fault(self) -> ComponentFault:
        """Resolve suspension-related fault"""
        roll = random.randint(1, 10)

        if roll <= 7:
            return ComponentFault(
                component="suspension",
                fault_type="suspension_failure",
                severity=FaultSeverity.MAJOR,
                time_loss=15.0,
                repairable=True,
                affected_systems=[],
            )
        else:
            return ComponentFault(
                component="suspension",
                fault_type="steering_issue",
                severity=FaultSeverity.MODERATE,
                time_loss=8.0,
                repairable=True,
                affected_systems=[],
            )

    def _resolve_tyre_fault(self) -> ComponentFault:
        """Resolve tyre-related fault"""
        roll = random.randint(1, 10)

        for range_roll, config in self.TYRE_FAULTS.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return ComponentFault(
                    component="tyre",
                    fault_type=config["type"],
                    severity=config["severity"],
                    time_loss=config["time_loss"],
                    repairable=config["repairable"],
                    affected_systems=[],
                )

        return ComponentFault(
            component="tyre",
            fault_type="unknown",
            severity=FaultSeverity.MINOR,
            time_loss=1.0,
            repairable=False,
            affected_systems=[],
        )

    def _resolve_misc_fault(self) -> ComponentFault:
        """Resolve miscellaneous faults"""
        roll = random.randint(1, 10)

        if roll <= 5:
            return ComponentFault(
                component="brakes",
                fault_type="brake_failure",
                severity=FaultSeverity.MAJOR,
                time_loss=12.0,
                repairable=True,
                affected_systems=[],
            )
        else:
            return ComponentFault(
                component="hydraulics",
                fault_type="hydraulic_leak",
                severity=FaultSeverity.MODERATE,
                time_loss=10.0,
                repairable=True,
                affected_systems=[],
            )


# Pre-configured team stability values from Spain 2024 data
TEAM_STABILITIES = {
    "Aston Martin": TeamStability(
        team_name="Aston Martin",
        base_stability=98.5,
        engine_reliability=9,
        hybrid_reliability=9,
        battery_reliability=8,
        chassis_reliability=9,
        suspension_reliability=9,
        tyre_reliability=9,
        brake_reliability=9,
        aero_reliability=9,
    ),
    "Mercedes": TeamStability(
        team_name="Mercedes",
        base_stability=97.0,
        engine_reliability=9,
        hybrid_reliability=9,
        battery_reliability=9,
        chassis_reliability=8,
        suspension_reliability=9,
        tyre_reliability=9,
        brake_reliability=9,
        aero_reliability=8,
    ),
    "Haas": TeamStability(
        team_name="Haas",
        base_stability=97.5,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=8,
        chassis_reliability=8,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=8,
    ),
    "Alpine": TeamStability(
        team_name="Alpine",
        base_stability=97.75,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=7,
        chassis_reliability=8,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=8,
    ),
    "Andretti": TeamStability(
        team_name="Andretti",
        base_stability=97.0,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=8,
        chassis_reliability=8,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=8,
    ),
    "McLaren": TeamStability(
        team_name="McLaren",
        base_stability=96.5,
        engine_reliability=9,
        hybrid_reliability=9,
        battery_reliability=9,
        chassis_reliability=9,
        suspension_reliability=9,
        tyre_reliability=9,
        brake_reliability=9,
        aero_reliability=9,
    ),
    "Red Bull": TeamStability(
        team_name="Red Bull",
        base_stability=96.0,
        engine_reliability=9,
        hybrid_reliability=9,
        battery_reliability=8,
        chassis_reliability=9,
        suspension_reliability=9,
        tyre_reliability=9,
        brake_reliability=9,
        aero_reliability=9,
    ),
    "AlphaTauri": TeamStability(
        team_name="AlphaTauri",
        base_stability=96.0,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=8,
        chassis_reliability=8,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=8,
    ),
    "Ferrari": TeamStability(
        team_name="Ferrari",
        base_stability=95.0,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=7,
        chassis_reliability=9,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=9,
    ),
    "Alfa Romeo": TeamStability(
        team_name="Alfa Romeo",
        base_stability=95.0,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=7,
        chassis_reliability=8,
        suspension_reliability=8,
        tyre_reliability=9,
        brake_reliability=8,
        aero_reliability=8,
    ),
    "Williams": TeamStability(
        team_name="Williams",
        base_stability=95.0,
        engine_reliability=8,
        hybrid_reliability=8,
        battery_reliability=7,
        chassis_reliability=7,
        suspension_reliability=7,
        tyre_reliability=8,
        brake_reliability=7,
        aero_reliability=7,
    ),
}


def get_team_stability(team_name: str) -> TeamStability:
    """
    Get team stability configuration.

    Args:
        team_name: Name of the team

    Returns:
        TeamStability configuration or default if not found
    """
    return TEAM_STABILITIES.get(
        team_name,
        TeamStability(
            team_name=team_name,
            base_stability=96.0,  # Default stability
        ),
    )


def estimate_fault_probability(stability: float, laps: int = 70) -> float:
    """
    Estimate total fault probability for a race.

    Args:
        stability: Team stability value
        laps: Number of laps in race

    Returns:
        Estimated total fault probability
    """
    base = (100 - stability) / 250
    pu_factor = (laps / 50) * 0.01
    return min(0.08, base + pu_factor)
