"""
Driver Interaction Module

Handles driver compliance checks:
- DriverComplianceRoller: Checks how well a driver follows strategist instructions
"""

from dataclasses import dataclass
from typing import Optional
from src.strategist.strategist_types import (
    DriverComplianceLevel,
    ComplianceCheck,
    determine_compliance_outcome,
)


@dataclass
class DriverProfile:
    """
    Profile for a driver's behavior and characteristics.

    These affect how likely they are to follow the strategist's instructions.
    """

    name: str
    aggression: float  # 0.0-1.0
    stubbornness: float  # 0.0-1.0
    professionalism: float  # 0.0-1.0

    def get_aggression_modifier(self) -> int:
        """Higher aggression = less compliant"""
        if self.aggression >= 0.8:
            return -2
        elif self.aggression >= 0.6:
            return -1
        else:
            return 0

    def get_stubbornness_modifier(self) -> int:
        """Higher stubbornness = less compliant"""
        if self.stubbornness >= 0.8:
            return -3
        elif self.stubbornness >= 0.6:
            return -2
        elif self.stubbornness >= 0.4:
            return -1
        else:
            return 0

    def get_professionalism_modifier(self) -> int:
        """Higher professionalism = more compliant"""
        if self.professionalism >= 0.8:
            return 1
        elif self.professionalism >= 0.6:
            return 0
        else:
            return -1


class DriverComplianceRoller:
    """
    Handles driver compliance checks.

    Determines how well a driver follows the strategist's instructions
    based on various factors.
    """

    def __init__(self, driver: DriverProfile):
        """
        Initialize with driver profile.

        Args:
            driver: Driver profile
        """
        self.driver = driver

    def check_compliance(
        self,
        strategist_trust: float,  # 0.0-1.0
        recent_strategist_failures: int = 0,
        decision_importance: int = 0,  # 0-4
        forced_decision: bool = False,
    ) -> ComplianceCheck:
        """
        Check driver compliance with strategist instruction.

        Args:
            strategist_trust: How much driver trusts strategist (0.0-1.0)
            recent_strategist_failures: Recent failed decisions
            decision_importance: How critical the decision is (0-4)
            forced_decision: Whether driver has choice

        Returns:
            ComplianceCheck with result
        """
        import random

        roll = random.randint(1, 20)

        # Calculate modifiers
        modifier = 0

        # Trust modifier (-2 to +2)
        if strategist_trust >= 0.8:
            modifier += 2
        elif strategist_trust >= 0.6:
            modifier += 1
        elif strategist_trust <= 0.2:
            modifier -= 2
        elif strategist_trust <= 0.4:
            modifier -= 1

        # Driver attributes
        modifier += self.driver.get_aggression_modifier()
        modifier += self.driver.get_stubbornness_modifier()
        modifier += self.driver.get_professionalism_modifier()

        # Recent failures penalty
        if recent_strategist_failures >= 3:
            modifier -= 2
        elif recent_strategist_failures >= 1:
            modifier -= 1

        # Decision importance (higher importance = more likely to comply)
        modifier += decision_importance

        # Forced decision (driver has no choice)
        if forced_decision:
            modifier += 2

        # Calculate final value
        final_value = roll + modifier

        # Determine outcome
        outcome = determine_compliance_outcome(roll, final_value)

        # Get effectiveness
        effectiveness = ComplianceCheck.get_effectiveness(outcome)

        return ComplianceCheck(
            roll=roll,
            modifier=modifier,
            final_value=final_value,
            outcome=outcome,
            effectiveness=effectiveness,
        )

    def will_driver_follow(
        self,
        strategist_trust: float,
        decision_importance: int = 2,
    ) -> bool:
        """
        Simple check if driver will follow instruction.

        Args:
            strategist_trust: Trust level (0.0-1.0)
            decision_importance: How important (0-4)

        Returns:
            True if likely to follow
        """
        # Base chance
        chance = 0.5

        # Adjust for trust
        chance += (strategist_trust - 0.5) * 0.4  # +/-20%

        # Adjust for decision importance
        chance += decision_importance * 0.05  # +5% per importance level

        # Adjust for driver traits
        chance -= self.driver.stubbornness * 0.1
        chance -= self.driver.aggression * 0.1
        chance += self.driver.professionalism * 0.1

        import random

        return random.random() < chance


# Default driver profiles for F1 drivers
DEFAULT_DRIVER_PROFILES = {
    # Protagonist driver (Ferrari)
    "Nakamura": DriverProfile(
        name="Nakamura",
        aggression=0.5,
        stubbornness=0.4,
        professionalism=0.8,
    ),
    # Sample other drivers
    "Verstappen": DriverProfile(
        name="Verstappen",
        aggression=0.9,
        stubbornness=0.6,
        professionalism=0.9,
    ),
    "Hamilton": DriverProfile(
        name="Hamilton",
        aggression=0.7,
        stubbornness=0.3,
        professionalism=0.95,
    ),
    "Leclerc": DriverProfile(
        name="Leclerc",
        aggression=0.75,
        stubbornness=0.5,
        professionalism=0.85,
    ),
    "Norris": DriverProfile(
        name="Norris",
        aggression=0.6,
        stubbornness=0.4,
        professionalism=0.8,
    ),
    "Russell": DriverProfile(
        name="Russell",
        aggression=0.65,
        stubbornness=0.45,
        professionalism=0.9,
    ),
    "Perez": DriverProfile(
        name="Perez",
        aggression=0.5,
        stubbornness=0.35,
        professionalism=0.85,
    ),
    "Alonso": DriverProfile(
        name="Alonso",
        aggression=0.6,
        stubbornness=0.7,
        professionalism=0.95,
    ),
}


def get_driver_profile(driver_name: str) -> DriverProfile:
    """
    Get driver profile by name.

    Args:
        driver_name: Driver's name

    Returns:
        DriverProfile (or generic if not found)
    """
    if driver_name in DEFAULT_DRIVER_PROFILES:
        return DEFAULT_DRIVER_PROFILES[driver_name]

    # Return generic profile
    return DriverProfile(
        name=driver_name,
        aggression=0.5,
        stubbornness=0.5,
        professionalism=0.7,
    )
