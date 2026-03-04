"""
Incident Penalty Handler.

Handles penalties for various race incidents including:
- Unsafe releases (time loss to all drivers involved)
- Impeding
- Pit lane speeding
- Weaving/multiple direction changes
"""

import random
from typing import List, Dict

from src.penalties.penalty_types import (
    PenaltyType,
    PenaltyReason,
    TimeLoss,
)
from src.penalties.penalty_manager import PenaltyManager


class IncidentPenaltyHandler:
    """
    Handle penalties for general race incidents.

    Note: Unsafe releases don't give driver penalties - instead
    time loss is applied to ALL drivers involved (max 5 seconds).
    """

    def __init__(self, penalty_manager: PenaltyManager):
        """
        Initialize the incident penalty handler.

        Args:
            penalty_manager: The penalty manager to use
        """
        self.penalty_manager = penalty_manager

    def handle_unsafe_release(
        self,
        involved_drivers: List[str],
        severity: str,
        time: float,
        lap: int,
    ) -> Dict:
        """
        Handle an unsafe release from pit lane.

        No driver penalty - instead time loss to ALL drivers involved.
        Time loss is based on severity (max 5 seconds).

        Args:
            involved_drivers: List of drivers involved in the incident
            severity: "minor", "moderate", or "major"
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with time losses for all drivers
        """
        # Time loss based on severity (max 5 seconds)
        severity_map = {
            "minor": (1.0, 2.0),
            "moderate": (3.0, 4.0),
            "major": (5.0, 5.0),  # Max 5 seconds
        }

        min_time, max_time = severity_map.get(severity, (3.0, 4.0))

        time_losses = []
        for driver in involved_drivers:
            time_loss_seconds = random.uniform(min_time, max_time)
            tl = self.penalty_manager.add_time_loss(
                driver=driver,
                seconds=time_loss_seconds,
                reason=f"Unsafe release (severity: {severity})",
                time_assessed=time,
                lap_assessed=lap,
            )
            time_losses.append(tl)

        return {
            "time_losses": time_losses,
            "involved_drivers": involved_drivers,
            "severity": severity,
        }

    def handle_impeding(
        self,
        driver: str,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle impeding another driver.

        Args:
            driver: Driver who impeded
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty_type = PenaltyType.TIME_5S
        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=penalty_type,
            reason="Impeding another driver",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.IMPEDING,
            points=2,
        )

        return {
            "penalty": penalty,
            "penalty_type": penalty_type.value,
            "driver_penalized": driver,
        }

    def handle_pit_lane_speeding(
        self,
        driver: str,
        speed_over_limit: float,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle pit lane speeding.

        Args:
            driver: Driver who exceeded speed limit
            speed_over_limit: How much over the limit
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=PenaltyType.TIME_5S,
            reason=f"Pit lane speeding ({speed_over_limit:.1f} km/h over limit)",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.PIT_LANE_SPEEDING,
            points=1,
        )

        return {
            "penalty": penalty,
            "penalty_type": PenaltyType.TIME_5S.value,
            "driver_penalized": driver,
        }

    def handle_weaving(
        self,
        driver: str,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle multiple direction changes (weaving).

        Args:
            driver: Driver who was weaving
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=PenaltyType.TIME_5S,
            reason="Multiple direction changes (weaving)",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.WEAVING,
            points=1,
        )

        return {
            "penalty": penalty,
            "penalty_type": PenaltyType.TIME_5S.value,
            "driver_penalized": driver,
        }

    def handle_dangerous_release(
        self,
        driver: str,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle a dangerous release (more severe than unsafe release).

        Args:
            driver: Driver who released car dangerously
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=PenaltyType.TIME_10S,
            reason="Dangerous release from pit lane",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.RELEASING_CAR_DANGEROUSLY,
            points=2,
        )

        return {
            "penalty": penalty,
            "penalty_type": PenaltyType.TIME_10S.value,
            "driver_penalized": driver,
        }
