"""
VSC Violation Penalty Handler.

Handles penalties for VSC (Virtual Safety Car) and Safety Car violations.
"""

import random
from typing import List

from src.penalties.penalty_types import (
    PenaltyType,
    PenaltyReason,
)
from src.penalties.penalty_manager import PenaltyManager


class VSCViolationHandler:
    """
    Handle penalties for VSC/SC speed violations.

    When VSC or Safety Car is deployed, drivers must:
    - Stay within delta time
    - Not exceed speed limits

    Violations typically result in 5-10 second time penalty + 2 points.
    """

    def __init__(self, penalty_manager: PenaltyManager):
        """
        Initialize the VSC violation handler.

        Args:
            penalty_manager: The penalty manager to use
        """
        self.penalty_manager = penalty_manager

    def handle_vsc_violation(
        self,
        driver: str,
        speed_over_delta: float,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle a VSC speed violation.

        Args:
            driver: Driver who violated VSC
            speed_over_delta: How much over the delta they were
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        # Determine penalty based on severity
        if speed_over_delta < 1.0:
            penalty_type = PenaltyType.TIME_5S
            points = 2
        elif speed_over_delta < 3.0:
            penalty_type = PenaltyType.TIME_10S
            points = 2
        else:
            # Severe violation
            penalty_type = PenaltyType.TIME_10S
            points = 3

        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=penalty_type,
            reason=f"VSC speed violation ({speed_over_delta:.1f}s over delta)",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.VSC_VIOLATION,
            points=points,
            additional_info={"speed_over_delta": speed_over_delta},
        )

        return {
            "penalty": penalty,
            "penalty_type": penalty_type.value,
            "driver_penalized": driver,
        }

    def handle_sc_violation(
        self,
        driver: str,
        speed_over_limit: float,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle a Safety Car speed violation.

        Args:
            driver: Driver who violated SC
            speed_over_limit: How much over the SC speed limit
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        # SC violations are more severe
        if speed_over_limit < 2.0:
            penalty_type = PenaltyType.TIME_10S
            points = 2
        else:
            penalty_type = PenaltyType.STOP_GO_5S
            points = 3

        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=penalty_type,
            reason=f"Safety Car speed violation ({speed_over_limit:.1f}s over limit)",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.SC_VIOLATION,
            points=points,
            additional_info={"speed_over_limit": speed_over_limit},
        )

        return {
            "penalty": penalty,
            "penalty_type": penalty_type.value,
            "driver_penalized": driver,
        }

    def handle_yellow_flag_violation(
        self,
        driver: str,
        time: float,
        lap: int,
    ) -> dict:
        """
        Handle a yellow flag violation.

        Args:
            driver: Driver who violated yellow flag
            time: Race time
            lap: Lap number

        Returns:
            Dictionary with penalty info
        """
        penalty_type = PenaltyType.TIME_5S

        penalty = self.penalty_manager.assess_penalty(
            driver=driver,
            penalty_type=penalty_type,
            reason="Yellow flag violation",
            time_assessed=time,
            lap_assessed=lap,
            reason_enum=PenaltyReason.YELLOW_FLAG_VIOLATION,
            points=2,
        )

        return {
            "penalty": penalty,
            "penalty_type": penalty_type.value,
            "driver_penalized": driver,
        }
