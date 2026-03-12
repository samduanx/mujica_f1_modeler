"""
Front Wing Replacement System for F1 Race Simulation.

Handles front wing damage tracking and replacement during pit stops.
Based on the dice rolling mechanics defined in the simulation rules.

Damage Sources:
- driver_error: Driver mistakes (locked brakes, off-track, etc.)
- overtake_collision: Collision during overtaking
- vehicle_fault(aerodynamics): Aerodynamic component failures

Exclusions:
- WIDELONSO skill damage does NOT trigger front wing replacement
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum
import random


class FrontWingSeverity(Enum):
    """Front wing damage severity levels"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"


# Front wing replacement configuration
# Probability of replacement based on severity (d10 threshold)
FRONT_WING_REPLACEMENT_CONFIG = {
    FrontWingSeverity.MINOR: {
        "probability": 0.20,
        "threshold_d10": 9,
    },  # 20% chance, need >= 9
    FrontWingSeverity.MODERATE: {
        "probability": 0.50,
        "threshold_d10": 6,
    },  # 50% chance, need >= 6
    FrontWingSeverity.MAJOR: {
        "probability": 0.80,
        "threshold_d10": 3,
    },  # 80% chance, need >= 3
    FrontWingSeverity.SEVERE: {
        "probability": 1.00,
        "threshold_d10": 0,
    },  # 100% chance, auto-replace
}

# Time calculation constants
FRONT_WING_TIME_BASE = 4.5  # Base time in seconds
FRONT_WING_TIME_PER_D10 = 0.1  # Additional time per d10 point


@dataclass
class FrontWingDamage:
    """Represents front wing damage for a driver"""

    driver: str
    damage_amount: float  # 0.0 to 1.0
    severity: FrontWingSeverity
    source: str  # Event type that caused the damage
    lap_occurred: int
    replaced: bool = False
    replacement_lap: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "driver": self.driver,
            "damage_amount": self.damage_amount,
            "severity": self.severity.value,
            "source": self.source,
            "lap_occurred": self.lap_occurred,
            "replaced": self.replaced,
            "replacement_lap": self.replacement_lap,
        }


@dataclass
class FrontWingReplacementResult:
    """Result of a front wing replacement decision"""

    replaced: bool
    severity: FrontWingSeverity
    d10_roll: int
    threshold: int
    extra_time: float
    total_time: float
    message: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "replaced": self.replaced,
            "severity": self.severity.value,
            "d10_roll": self.d10_roll,
            "threshold": self.threshold,
            "extra_time": self.extra_time,
            "total_time": self.total_time,
            "message": self.message,
        }


class FrontWingManager:
    """
    Manages front wing damage and replacement during pit stops.

    Responsibilities:
    - Track front wing damage per driver
    - Determine if replacement is needed during pit stop
    - Calculate additional time for replacement
    - Log dice rolls for the mechanic
    """

    def __init__(self):
        """Initialize front wing manager"""
        self.damage_records: Dict[str, FrontWingDamage] = {}

    def add_damage(
        self,
        driver: str,
        severity: FrontWingSeverity,
        source: str,
        lap: int,
        damage_amount: Optional[float] = None,
    ) -> FrontWingDamage:
        """
        Add front wing damage for a driver.

        Args:
            driver: Driver name
            severity: Damage severity level
            source: Event type that caused damage (e.g., "driver_error", "overtake_collision")
            lap: Lap number when damage occurred
            damage_amount: Specific damage amount (auto-calculated from severity if None)

        Returns:
            FrontWingDamage record
        """
        # Auto-calculate damage amount from severity if not provided
        if damage_amount is None:
            damage_amount = self._severity_to_damage_amount(severity)

        damage = FrontWingDamage(
            driver=driver,
            damage_amount=damage_amount,
            severity=severity,
            source=source,
            lap_occurred=lap,
        )
        self.damage_records[driver] = damage
        return damage

    def _severity_to_damage_amount(self, severity: FrontWingSeverity) -> float:
        """Convert severity level to damage amount"""
        mapping = {
            FrontWingSeverity.MINOR: 0.15,
            FrontWingSeverity.MODERATE: 0.35,
            FrontWingSeverity.MAJOR: 0.60,
            FrontWingSeverity.SEVERE: 0.85,
        }
        return mapping.get(severity, 0.15)

    def check_replacement_needed(self, driver: str) -> Optional[FrontWingDamage]:
        """
        Check if a driver has unreplaced front wing damage.

        Args:
            driver: Driver name

        Returns:
            FrontWingDamage if unreplaced damage exists, None otherwise
        """
        damage = self.damage_records.get(driver)
        if damage and not damage.replaced:
            return damage
        return None

    def attempt_replacement(
        self,
        driver: str,
        lap: int,
        dice_roll: Optional[int] = None,
    ) -> FrontWingReplacementResult:
        """
        Attempt to replace front wing during pit stop.

        First dice roll (d10): Determine if replacement happens based on severity
        Second dice roll (d10): Calculate additional time (4.5 + 0.1 * d10)

        Args:
            driver: Driver name
            lap: Current lap number
            dice_roll: Optional pre-rolled d10 value (for testing)

        Returns:
            FrontWingReplacementResult with decision and timing
        """
        damage = self.check_replacement_needed(driver)

        if not damage:
            return FrontWingReplacementResult(
                replaced=False,
                severity=FrontWingSeverity.MINOR,
                d10_roll=0,
                threshold=0,
                extra_time=0.0,
                total_time=0.0,
                message=f"{driver}: No front wing damage to replace",
            )

        config = FRONT_WING_REPLACEMENT_CONFIG[damage.severity]
        threshold = config["threshold_d10"]

        # First dice roll: Decide if replacement happens
        # For severe damage, always replace (threshold = 0)
        if dice_roll is not None:
            d10_roll = max(1, min(10, dice_roll))
        else:
            d10_roll = random.randint(1, 10)

        # Check if replacement should happen
        if damage.severity == FrontWingSeverity.SEVERE:
            # Severe damage always requires replacement
            should_replace = True
        else:
            # Roll must meet or exceed threshold
            should_replace = d10_roll >= threshold

        if not should_replace:
            return FrontWingReplacementResult(
                replaced=False,
                severity=damage.severity,
                d10_roll=d10_roll,
                threshold=threshold,
                extra_time=0.0,
                total_time=0.0,
                message=(
                    f"{driver}: Front wing replacement skipped "
                    f"(rolled {d10_roll}, needed >= {threshold})"
                ),
            )

        # Second dice roll: Calculate additional time
        time_d10 = random.randint(1, 10)
        extra_time = FRONT_WING_TIME_BASE + (FRONT_WING_TIME_PER_D10 * time_d10)

        # Mark damage as replaced
        damage.replaced = True
        damage.replacement_lap = lap

        return FrontWingReplacementResult(
            replaced=True,
            severity=damage.severity,
            d10_roll=d10_roll,
            threshold=threshold,
            extra_time=extra_time,
            total_time=extra_time,
            message=(
                f"{driver}: Front wing replaced (+{extra_time:.2f}s) "
                f"[decision roll: {d10_roll}, time roll: {time_d10}]"
            ),
        )

    def get_damage(self, driver: str) -> Optional[FrontWingDamage]:
        """Get damage record for a driver"""
        return self.damage_records.get(driver)

    def clear_damage(self, driver: str):
        """Clear damage record for a driver"""
        if driver in self.damage_records:
            del self.damage_records[driver]

    def create_damage_from_incident(
        self,
        driver: str,
        incident_type: str,
        incident_severity: str,
        lap: int,
    ) -> Optional[FrontWingDamage]:
        """
        Create front wing damage from an incident.

        Args:
            driver: Driver name
            incident_type: Type of incident ("driver_error", "overtake_collision", etc.)
            incident_severity: Incident severity ("minor", "moderate", "major", "severe")
            lap: Lap number

        Returns:
            FrontWingDamage if created, None if incident type doesn't cause front wing damage
        """
        # EXCLUDE: WIDELONSO skill damage does NOT create front wing damage
        # This ensures skill-based vehicle damage is separate from front wing damage
        # Alonso's overtake incidents (as normal collisions) will still create damage,
        # but WIDELONSO skill-specific damage will not
        if incident_type in ("widelonso", "widelonso_skill", "skill_damage"):
            return None
        
        # Map incident severity to front wing severity
        severity_map = {
            "minor": FrontWingSeverity.MINOR,
            "moderate": FrontWingSeverity.MODERATE,
            "major": FrontWingSeverity.MAJOR,
            "severe": FrontWingSeverity.SEVERE,
            "catastrophic": FrontWingSeverity.SEVERE,
            "terminal": FrontWingSeverity.SEVERE,
        }

        front_wing_severity = severity_map.get(incident_severity.lower())
        if not front_wing_severity:
            return None

        return self.add_damage(
            driver=driver,
            severity=front_wing_severity,
            source=incident_type,
            lap=lap,
        )

    def get_all_damage_records(self) -> Dict[str, FrontWingDamage]:
        """Get all damage records"""
        return self.damage_records.copy()

    def reset(self):
        """Reset all damage records (for new race)"""
        self.damage_records.clear()


# Global instance for use across the simulation
_front_wing_manager: Optional[FrontWingManager] = None


def get_front_wing_manager() -> FrontWingManager:
    """Get or create the global front wing manager instance"""
    global _front_wing_manager
    if _front_wing_manager is None:
        _front_wing_manager = FrontWingManager()
    return _front_wing_manager


def reset_front_wing_manager():
    """Reset the global front wing manager"""
    global _front_wing_manager
    if _front_wing_manager:
        _front_wing_manager.reset()
    _front_wing_manager = None
