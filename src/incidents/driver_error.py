"""
Driver Error System.

Handles driver errors based on DR values and race conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from enum import Enum
import random

if TYPE_CHECKING:
    from incidents.dice_roller import DiceRoller


class DriverErrorType(Enum):
    """Types of driver errors"""

    LOCKED_BRAKES = "locked_brakes"
    OFF_TRACK = "off_track"
    CORNER_MISTAKE = "corner_mistake"
    SPIN = "spin"
    POLE_POSITION_ERROR = "pole_position_error"
    UNDERSHOOT_CORNER = "undershoot_corner"
    OVERSHOT_CORNER = "overshoot_corner"
    BRAKING_POINT_ERROR = "braking_point_error"


class ErrorSeverity(Enum):
    """Severity levels for driver errors"""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"


@dataclass
class DriverError:
    """Represents a driver error incident"""

    driver: str
    error_type: DriverErrorType
    severity: ErrorSeverity
    time_penalty: float
    position_impact: int
    affected_drivers: List[str] = field(default_factory=list)
    narrative: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "driver": self.driver,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "time_penalty": self.time_penalty,
            "position_impact": self.position_impact,
            "affected_drivers": self.affected_drivers,
            "narrative": self.narrative,
        }


class DriverErrorProbability:
    """
    Calculate driver error probability based on DR value.

    Higher DR = Lower error probability
    """

    # Base error probability per lap
    BASE_ERROR_PROB = 0.03  # 3% per lap

    def get_error_probability(
        self,
        dr_value: float,
        lap_number: int,
        tyre_degradation: float,
        race_position: int,
        under_pressure: bool,
        is_first_lap: bool = False,
        r_value: float = None,
    ) -> float:
        """
        Calculate error probability for a driver.

        Args:
            dr_value: Driver's DR value (typically 80-92)
            lap_number: Current lap
            tyre_degradation: Current tyre degradation factor
            race_position: Current position (1 = leader)
            under_pressure: Being pressured by car behind
            is_first_lap: Whether this is the first lap
            r_value: Driver's R value (100.5 = elite, <99 = lower tier)

        Returns:
            Error probability (0.0 to 1.0)
        """
        # R-value based error control: Elite drivers (R>=100) almost never make errors
        if r_value is not None:
            if r_value >= 100.0:
                # Elite drivers: Virtually no errors (0.1% chance)
                return 0.001
            elif r_value >= 99.5:
                # Good drivers: Very low error rate (0.5% chance)
                base_prob = 0.005
            else:
                # Lower tier drivers: Normal error rate
                base_prob = self.BASE_ERROR_PROB
        else:
            base_prob = self.BASE_ERROR_PROB

        prob = base_prob

        # DR modifier - higher DR = lower error probability (only for lower tier drivers)
        if r_value is None or r_value < 100.0:
            dr_factor = (dr_value - 80) / 40
            prob -= dr_factor * 0.02

        # Tyre degradation factor
        if tyre_degradation > 1.2:
            prob *= 1.5
        elif tyre_degradation > 1.1:
            prob *= 1.2

        # Position factor - leaders make fewer errors
        if race_position <= 3:
            prob *= 0.8
        elif race_position >= 15:
            prob *= 1.2

        # Pressure factor
        if under_pressure:
            prob *= 1.3

        # Lap factor
        if is_first_lap:
            prob *= 1.5
        elif lap_number <= 3:
            prob *= 1.2

        return max(0.0, min(1.0, prob))

    def get_error_roll_threshold(self, dr_value: float) -> int:
        """
        Get the dice roll threshold for errors based on DR.

        Higher DR = higher threshold (harder to make errors)

        Args:
            dr_value: Driver's DR value

        Returns:
            Roll threshold (1-20)
        """
        # Base threshold
        base_threshold = 15

        # DR adjustment
        dr_adjustment = (dr_value - 80) / 2  # DR 92 = +6

        return int(max(5, min(20, base_threshold + dr_adjustment)))


class DriverErrorResolver:
    """
    Resolve driver errors using confronting dice mechanics.
    """

    # Error type mappings
    ERROR_NARRATIVES = {
        DriverErrorType.LOCKED_BRAKES: "{driver} locks up at the braking zone",
        DriverErrorType.OFF_TRACK: "{driver} runs wide and goes off track",
        DriverErrorType.SPIN: "{driver} spins out of control",
        DriverErrorType.CORNER_MISTAKE: "{driver} makes a mistake at the corner",
        DriverErrorType.POLE_POSITION_ERROR: "{driver} loses control at the apex",
        DriverErrorType.UNDERSHOOT_CORNER: "{driver} undershoots the corner",
        DriverErrorType.OVERSHOT_CORNER: "{driver} overshoots the corner",
        DriverErrorType.BRAKING_POINT_ERROR: "{driver} gets the braking point wrong",
    }

    # Severity settings - REDUCED PENALTIES
    # Position penalties reduced from -1/-2/-3 to 0/-1/-1
    # Focus on time penalties rather than position drops
    SEVERITY_SETTINGS = {
        ErrorSeverity.MINOR: {
            "time_penalty": 0.5,
            "position_impact": 0,
        },  # No position loss
        ErrorSeverity.MODERATE: {
            "time_penalty": 1.5,
            "position_impact": 0,
        },  # Reduced: was -1
        ErrorSeverity.MAJOR: {
            "time_penalty": 3.0,
            "position_impact": -1,
        },  # Reduced: was -2
        ErrorSeverity.SEVERE: {
            "time_penalty": 5.0,
            "position_impact": -1,
        },  # Reduced: was -3
    }

    def __init__(self, dice_roller: Optional["DiceRoller"] = None):
        """Initialize resolver with optional dice roller"""
        self.dice_roller = dice_roller
        self.probability_calculator = DriverErrorProbability()

    def resolve_error(
        self,
        driver_name: str,
        dr_value: float,
        error_type: Optional[DriverErrorType] = None,
        affected_drivers: Optional[List[Dict]] = None,
    ) -> DriverError:
        """
        Resolve a driver error incident.

        Args:
            driver_name: Name of the driver making the error
            dr_value: Driver's DR value
            error_type: Specific error type (random if None)
            affected_drivers: List of affected driver info

        Returns:
            DriverError with full details
        """
        # Select error type if not specified
        if error_type is None:
            error_type = random.choice(list(DriverErrorType))

        # Roll for error severity
        roll = self._roll_d20() if self.dice_roller else random.randint(1, 20)

        # Calculate threshold based on DR
        threshold = self.probability_calculator.get_error_roll_threshold(dr_value)

        # Determine severity based on roll vs threshold
        if roll >= threshold + 5:
            severity = ErrorSeverity.MINOR
        elif roll >= threshold:
            severity = ErrorSeverity.MODERATE
        elif roll >= threshold - 5:
            severity = ErrorSeverity.MAJOR
        else:
            severity = ErrorSeverity.SEVERE

        # Get severity settings
        settings = self.SEVERITY_SETTINGS[severity]

        # Generate narrative
        narrative_template = self.ERROR_NARRATIVES.get(
            error_type, "{driver} makes an error"
        )
        narrative = narrative_template.format(driver=driver_name)

        # Process affected drivers
        affected_list = []
        if affected_drivers:
            for driver_info in affected_drivers:
                affected_name = driver_info.get("name", "Unknown")
                affected_dr = driver_info.get("dr_value", 85)

                # Affected driver can roll to avoid consequences
                if self._can_avoid_incident(affected_dr):
                    continue  # Avoided
                else:
                    # Caught in the incident
                    affected_list.append(
                        {
                            "name": affected_name,
                            "time_loss": settings["time_penalty"] * 0.5,
                        }
                    )
                    narrative += f", catching {affected_name}"

        return DriverError(
            driver=driver_name,
            error_type=error_type,
            severity=severity,
            time_penalty=settings["time_penalty"],
            position_impact=settings["position_impact"],
            affected_drivers=[a["name"] for a in affected_list],
            narrative=narrative,
        )

    def _roll_d20(self) -> int:
        """Roll a d20"""
        if self.dice_roller:
            return self.dice_roller.roll_d20()
        return random.randint(1, 20)

    def _can_avoid_incident(self, dr_value: float) -> bool:
        """
        Determine if a driver can avoid an incident.

        Higher DR = better chance to avoid
        """
        roll = self._roll_d20()
        threshold = self.probability_calculator.get_error_roll_threshold(dr_value)

        # Need to roll above threshold to avoid
        return roll >= threshold


class DriverErrorSimulator:
    """
    Simulate driver errors throughout a race.
    """

    def __init__(self, dice_roller: Optional["DiceRoller"] = None):
        """Initialize simulator"""
        self.dice_roller = dice_roller
        self.resolver = DriverErrorResolver(dice_roller)
        self.errors: List[DriverError] = []

    def simulate_lap_errors(
        self,
        drivers: List[Dict],
        lap_number: int,
        is_first_lap: bool = False,
    ) -> List[DriverError]:
        """
        Simulate driver errors for a lap.

        Args:
            drivers: List of driver info dicts with 'name', 'dr_value', 'position', etc.
            lap_number: Current lap number
            is_first_lap: Whether this is the first lap

        Returns:
            List of errors that occurred
        """
        lap_errors = []

        for driver in drivers:
            # Calculate error probability
            prob = self.resolver.probability_calculator.get_error_probability(
                dr_value=driver.get("dr_value", 85),
                lap_number=lap_number,
                tyre_degradation=driver.get("tyre_degradation", 1.0),
                race_position=driver.get("position", 10),
                under_pressure=driver.get("under_pressure", False),
                is_first_lap=is_first_lap,
            )

            # Roll for error
            if random.random() < prob:
                error = self.resolver.resolve_error(
                    driver_name=driver.get("name", "Unknown"),
                    dr_value=driver.get("dr_value", 85),
                )
                lap_errors.append(error)
                self.errors.append(error)

        return lap_errors

    def get_statistics(self) -> Dict:
        """Get error statistics"""
        return {
            "total_errors": len(self.errors),
            "by_severity": self._count_by_severity(),
            "by_type": self._count_by_type(),
        }

    def _count_by_severity(self) -> Dict[str, int]:
        """Count errors by severity"""
        counts = {}
        for error in self.errors:
            counts[error.severity.value] = counts.get(error.severity.value, 0) + 1
        return counts

    def _count_by_type(self) -> Dict[str, int]:
        """Count errors by type"""
        counts = {}
        for error in self.errors:
            counts[error.error_type.value] = counts.get(error.error_type.value, 0) + 1
        return counts
