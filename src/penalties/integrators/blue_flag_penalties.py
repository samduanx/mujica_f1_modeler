"""
Blue Flag Penalty Handler.

Integrates with the blue flag system to assess penalties
for blue flag violations.
"""

from typing import Optional

from src.penalties.penalty_types import (
    PenaltyType,
    PenaltyReason,
)
from src.penalties.penalty_manager import PenaltyManager
from src.incidents.blue_flag import ResistanceLevel


class BlueFlagPenaltyHandler:
    """
    Handle penalties for blue flag violations.

    Maintains existing escalation:
    - warning_logged: no penalty
    - warning_announced: no penalty
    - 5s_penalty: 5-second time penalty
    - drive_through: drive-through penalty
    """

    def __init__(self, penalty_manager: PenaltyManager):
        """
        Initialize the blue flag penalty handler.

        Args:
            penalty_manager: The penalty manager to use
        """
        self.penalty_manager = penalty_manager

    def handle_blue_flag_violation(
        self,
        driver: str,
        resistance_level: ResistanceLevel,
        offense_count: int,
        time: float,
        lap: int,
    ) -> Optional[dict]:
        """
        Handle a blue flag violation.

        Args:
            driver: Driver who violated blue flag
            resistance_level: Level of resistance shown
            offense_count: Number of offenses by this driver
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info or None
        """
        # Determine penalty based on resistance level and offense count
        penalty = self._determine_penalty(resistance_level, offense_count)

        if penalty is None:
            return None

        # Map penalty string to PenaltyType
        penalty_type_map = {
            "5s_penalty": PenaltyType.TIME_5S,
            "drive_through": PenaltyType.DRIVE_THROUGH,
        }

        penalty_type = penalty_type_map.get(penalty)
        if penalty_type is None:
            return None

        # Points for penalty
        points = 1 if penalty_type == PenaltyType.TIME_5S else 3

        # Assess penalty
        p = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=penalty_type,
            reason=f"Blue flag violation (resistance: {resistance_level.value})",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.BLUE_FLAG_VIOLATION,
            points=points,
            additional_info={
                "resistance_level": resistance_level.value,
                "offense_count": offense_count,
            },
        )

        return {
            "penalty": p,
            "penalty_type": penalty_type.value,
            "driver_penalized": driver,
            "offense_count": offense_count,
        }

    def _determine_penalty(
        self,
        resistance_level: ResistanceLevel,
        offense_count: int,
    ) -> Optional[str]:
        """
        Determine penalty based on resistance level and offense count.

        Args:
            resistance_level: Level of resistance
            offense_count: Number of offenses

        Returns:
            Penalty string or None
        """
        # Build penalty map
        penalty_map = {
            # MINOR resistance
            (ResistanceLevel.MINOR, 1): None,  # warning
            (ResistanceLevel.MINOR, 2): None,  # warning
            (ResistanceLevel.MINOR, 3): "5s_penalty",
            # MODERATE resistance
            (ResistanceLevel.MODERATE, 1): None,  # warning
            (ResistanceLevel.MODERATE, 2): "5s_penalty",
            (ResistanceLevel.MODERATE, 3): "drive_through",
            # STRONG resistance
            (ResistanceLevel.STRONG, 1): "5s_penalty",
            (ResistanceLevel.STRONG, 2): "drive_through",
            (ResistanceLevel.STRONG, 3): "drive_through",
            # VIOLATION - certain penalty
            (ResistanceLevel.VIOLATION, 1): "drive_through",
            (ResistanceLevel.VIOLATION, 2): "drive_through",
            (ResistanceLevel.VIOLATION, 3): "drive_through",
        }

        key = (resistance_level, min(offense_count, 3))
        return penalty_map.get(key)
