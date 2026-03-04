"""
Penalty Manager.

Central coordinator for all penalties in a race.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid

from src.penalties.penalty_types import (
    Penalty,
    PenaltyType,
    PenaltyReason,
    TimeLoss,
)


class PenaltyManager:
    """
    Central manager for all race penalties.

    Responsibilities:
    - Assess new penalties
    - Track pending penalties for each driver
    - Serve penalties (at pit stop or post-race)
    - Generate penalty summaries for race reports
    """

    def __init__(self):
        """Initialize the penalty manager."""
        # All penalties assessed this race
        self.penalties: List[Penalty] = []

        # Time losses (non-penalty incidents like unsafe release)
        self.time_losses: List[TimeLoss] = []

        # Pending penalties (not yet served)
        self._pending_penalties: Dict[str, List[Penalty]] = {}  # driver -> penalties

        # Penalty counter for unique IDs
        self._penalty_counter = 0

    def assess_penalty(
        self,
        driver: str,
        penalty_type: PenaltyType,
        reason: str,
        time_assessed: float,
        lap_assessed: int,
        reason_enum: Optional[PenaltyReason] = None,
        points: Optional[int] = None,
        additional_info: Optional[Dict] = None,
    ) -> Penalty:
        """
        Assess a new penalty to a driver.

        Args:
            driver: Driver name
            penalty_type: Type of penalty
            reason: Description of the infraction
            time_assessed: Race time when penalty was given
            lap_assessed: Lap number when penalty was given
            reason_enum: Categorized reason (optional)
            points: Override penalty points (optional)
            additional_info: Extra information (optional)

        Returns:
            The created Penalty object
        """
        self._penalty_counter += 1
        penalty = Penalty(
            penalty_id=f"P{self._penalty_counter:04d}",
            penalty_type=penalty_type,
            driver=driver,
            time_assessed=time_assessed,
            lap_assessed=lap_assessed,
            reason=reason,
            reason_enum=reason_enum,
            points=points if points is not None else penalty_type.default_points,
            additional_info=additional_info or {},
        )

        self.penalties.append(penalty)

        # Add to pending if not a grid penalty or time loss
        if penalty_type not in [PenaltyType.TIME_LOSS]:
            if driver not in self._pending_penalties:
                self._pending_penalties[driver] = []
            self._pending_penalties[driver].append(penalty)

        return penalty

    def add_time_loss(
        self,
        driver: str,
        seconds: float,
        reason: str,
        time_assessed: float = 0.0,
        lap_assessed: int = 0,
    ) -> TimeLoss:
        """
        Add a time loss from incidents like unsafe release.

        Time losses don't carry penalty points but affect race time.

        Args:
            driver: Driver affected
            seconds: Time lost
            reason: Description of the incident
            time_assessed: Race time (optional)
            lap_assessed: Lap number (optional)

        Returns:
            The created TimeLoss object
        """
        time_loss = TimeLoss(
            driver=driver,
            seconds=seconds,
            reason=reason,
            time_assessed=time_assessed,
            lap_assessed=lap_assessed,
        )

        self.time_losses.append(time_loss)
        return time_loss

    def get_pending_penalties(self, driver: str) -> List[Penalty]:
        """
        Get all pending (unserved) penalties for a driver.

        Args:
            driver: Driver name

        Returns:
            List of pending penalties
        """
        return self._pending_penalties.get(driver, [])

    def has_pending_penalties(self, driver: str) -> bool:
        """Check if driver has any pending penalties."""
        return len(self.get_pending_penalties(driver)) > 0

    def serve_penalty(
        self,
        driver: str,
        penalty_id: str,
        served_at: str = "pit_stop",
        served_at_lap: Optional[int] = None,
        time_served: float = 0.0,
    ) -> bool:
        """
        Mark a penalty as served.

        Args:
            driver: Driver name
            penalty_id: ID of the penalty to serve
            served_at: "pit_stop" or "post_race"
            served_at_lap: Lap when served (optional)
            time_served: Actual time added to race (for post-race)

        Returns:
            True if penalty was found and served
        """
        penalties = self._pending_penalties.get(driver, [])

        for penalty in penalties:
            if penalty.penalty_id == penalty_id:
                penalty.is_served = True
                penalty.served_at = served_at
                penalty.served_at_lap = served_at_lap
                penalty.time_served = time_served

                # Remove from pending
                self._pending_penalties[driver].remove(penalty)
                return True

        return False

    def serve_all_time_penalties_at_pit(self, driver: str, lap: int) -> List[Penalty]:
        """
        Serve all pending time penalties for a driver at pit stop.

        Args:
            driver: Driver name
            lap: Current lap number

        Returns:
            List of penalties that were served
        """
        served = []
        pending = self.get_pending_penalties(driver)

        for penalty in pending[:]:  # Copy list to modify during iteration
            if penalty.penalty_type in [
                PenaltyType.TIME_5S,
                PenaltyType.TIME_10S,
                PenaltyType.TIME_15S,
            ]:
                self.serve_penalty(
                    driver=driver,
                    penalty_id=penalty.penalty_id,
                    served_at="pit_stop",
                    served_at_lap=lap,
                )
                served.append(penalty)

        return served

    def get_time_losses(self, driver: Optional[str] = None) -> List[TimeLoss]:
        """
        Get time losses for a driver or all drivers.

        Args:
            driver: Driver name (optional, returns all if None)

        Returns:
            List of time losses
        """
        if driver is None:
            return self.time_losses

        return [tl for tl in self.time_losses if tl.driver == driver]

    def get_total_time_loss(self, driver: str) -> float:
        """Get total time loss for a driver (from time losses only)."""
        return sum(tl.seconds for tl in self.time_losses if tl.driver == driver)

    def get_penalties_summary(self) -> Dict:
        """
        Get a summary of all penalties for the race.

        Returns:
            Dictionary with penalty statistics
        """
        summary = {
            "total_penalties": len(self.penalties),
            "total_time_losses": len(self.time_losses),
            "by_type": {},
            "by_driver": {},
            "pending": sum(len(p) for p in self._pending_penalties.values()),
        }

        # Count by type
        for penalty in self.penalties:
            ptype = penalty.penalty_type.value
            summary["by_type"][ptype] = summary["by_type"].get(ptype, 0) + 1

        # Count by driver
        for penalty in self.penalties:
            if penalty.driver not in summary["by_driver"]:
                summary["by_driver"][penalty.driver] = []
            summary["by_driver"][penalty.driver].append(penalty.to_dict())

        return summary

    def get_post_race_time_penalties(self, driver: str) -> float:
        """
        Get total time penalties that must be added to final race time.

        These are penalties that weren't served at a pit stop.

        Args:
            driver: Driver name

        Returns:
            Total seconds to add to race time
        """
        total = 0.0

        for penalty in self.penalties:
            if (
                penalty.driver == driver
                and not penalty.is_served
                and penalty.penalty_type
                in [
                    PenaltyType.TIME_5S,
                    PenaltyType.TIME_10S,
                    PenaltyType.TIME_15S,
                ]
            ):
                total += penalty.penalty_type.time_seconds or 0.0

        return total

    def reset(self):
        """Reset the penalty manager for a new race."""
        self.penalties.clear()
        self.time_losses.clear()
        self._pending_penalties.clear()
        self._penalty_counter = 0
