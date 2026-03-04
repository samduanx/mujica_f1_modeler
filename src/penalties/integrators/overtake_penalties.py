"""
Overtake Penalty Handler.

Integrates with the overtaking system to assess penalties
for collisions during overtake attempts.
"""

from typing import Optional

from src.penalties.penalty_types import (
    PenaltyType,
    PenaltyReason,
)
from src.penalties.penalty_manager import PenaltyManager
from src.incidents.incident_types import IncidentSeverity


class OvertakePenaltyHandler:
    """
    Handle penalties for overtake-related incidents.

    Maps incident severity to penalty types:
    - MINOR → 5s time penalty (1 point)
    - MODERATE → 10s time penalty (2 points)
    - MAJOR → Drive-through (3 points)
    """

    def __init__(self, penalty_manager: PenaltyManager):
        """
        Initialize the overtake penalty handler.

        Args:
            penalty_manager: The penalty manager to use
        """
        self.penalty_manager = penalty_manager

    def handle_overtake_collision(
        self,
        attacker: str,
        defender: str,
        severity: IncidentSeverity,
        time: float,
        lap: int,
    ) -> Optional[dict]:
        """
        Handle a collision during an overtake attempt.

        Args:
            attacker: Driver who attempted the overtake
            defender: Driver who was defending
            severity: Severity of the collision
            time: Race time when incident occurred
            lap: Lap number

        Returns:
            Dictionary with penalty info or None
        """
        # Determine penalty based on severity
        if severity == IncidentSeverity.MINOR:
            penalty_type = PenaltyType.TIME_5S
            points = 1
        elif severity == IncidentSeverity.MODERATE:
            penalty_type = PenaltyType.TIME_10S
            points = 2
        elif severity == IncidentSeverity.MAJOR:
            penalty_type = PenaltyType.DRIVE_THROUGH
            points = 3
        else:
            # SEVERE or unknown - treat as drive-through
            penalty_type = PenaltyType.DRIVE_THROUGH
            points = 3

        # Assess penalty to the attacker (caused collision)
        penalty = self.penalty_manager.assess_penalty(
            driver=attacker,
            penalty_type=penalty_type,
            reason=f"Causing collision with {defender} during overtake",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.CAUSING_COLLISION,
            points=points,
        )

        return {
            "penalty": penalty,
            "penalty_type": penalty_type.value,
            "driver_penalized": attacker,
            "victim": defender,
        }

    def handle_leaving_track_gain_advantage(
        self,
        driver: str,
        time: float,
        lap: int,
    ) -> Optional[dict]:
        """
        Handle a driver leaving the track and gaining an advantage.

        Args:
            driver: Driver who left track
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=PenaltyType.TIME_5S,
            reason="Leaving track and gaining an advantage",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.LEAVING_TRACK_GAINING_ADVANTAGE,
            points=1,
        )

        return {
            "penalty": penalty,
            "penalty_type": PenaltyType.TIME_5S.value,
            "driver_penalized": driver,
        }
