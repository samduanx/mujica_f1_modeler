"""
Penalty Service.

Handles the mechanics of serving penalties during a race:
- Time penalties served at pit stop vs. post-race
- Drive-through penalties
- Stop-and-go penalties
"""

import random
from typing import Dict, List, Optional, Tuple

from src.penalties.penalty_types import Penalty, PenaltyType


class PenaltyService:
    """
    Handles penalty serving mechanics.

    Time penalties can be served:
    - At pit stop: penalty added to pit time (+ random 0-0.5s overhead)
    - Post-race: penalty added directly to final time

    Drive-through and stop-and-go must be served during the race.
    """

    # Typical time impact of different penalties (in seconds)
    DRIVE_THROUGH_TIME = 20.0  # Approximate time lost
    STOP_GO_5S_TIME = 5.0
    STOP_GO_10S_TIME = 10.0
    STOP_GO_15S_TIME = 15.0

    # Random overhead for serving at pit
    PIT_OVERHEAD_MIN = 0.0
    PIT_OVERHEAD_MAX = 0.5

    def __init__(self):
        """Initialize the penalty service."""
        pass

    def should_serve_at_pit(
        self,
        penalty: Penalty,
        will_pit: bool,
    ) -> bool:
        """
        Determine if a penalty should be served at a pit stop.

        Args:
            penalty: The penalty to serve
            will_pit: Whether the driver will pit in the remaining race

        Returns:
            True if should serve at pit, False to serve post-race
        """
        # Time penalties can be served at pit or post-race
        if penalty.penalty_type in [
            PenaltyType.TIME_5S,
            PenaltyType.TIME_10S,
            PenaltyType.TIME_15S,
        ]:
            return will_pit

        # Drive-through and stop-and-go must be served during race
        # If driver won't pit, this would be a problem in real race
        # But for simulation, we'll convert to time penalty
        return will_pit

    def get_pit_stop_penalty_time(
        self,
        penalty: Penalty,
    ) -> float:
        """
        Get the time impact of serving a penalty at a pit stop.

        Time penalties at pit stop: penalty_time + random(0-0.5s) overhead
        Drive-through: just the drive-through time
        Stop-and-go: stop time + penalty time

        Args:
            penalty: The penalty being served

        Returns:
            Additional seconds added to pit time
        """
        overhead = random.uniform(self.PIT_OVERHEAD_MIN, self.PIT_OVERHEAD_MAX)

        if penalty.penalty_type == PenaltyType.TIME_5S:
            return 5.0 + overhead
        elif penalty.penalty_type == PenaltyType.TIME_10S:
            return 10.0 + overhead
        elif penalty.penalty_type == PenaltyType.TIME_15S:
            return 15.0 + overhead
        elif penalty.penalty_type == PenaltyType.DRIVE_THROUGH:
            return self.DRIVE_THROUGH_TIME
        elif penalty.penalty_type == PenaltyType.STOP_GO_5S:
            return self.STOP_GO_5S_TIME + 5.0
        elif penalty.penalty_type == PenaltyType.STOP_GO_10S:
            return self.STOP_GO_10S_TIME + 10.0
        elif penalty.penalty_type == PenaltyType.STOP_GO_15S:
            return self.STOP_GO_15S_TIME + 15.0

        return 0.0

    def get_post_race_penalty_time(
        self,
        penalty: Penalty,
    ) -> float:
        """
        Get the time penalty to add to final race time.

        Only applies to time penalties served post-race.

        Args:
            penalty: The penalty being served

        Returns:
            Seconds to add to final race time
        """
        if penalty.penalty_type == PenaltyType.TIME_5S:
            return 5.0
        elif penalty.penalty_type == PenaltyType.TIME_10S:
            return 10.0
        elif penalty.penalty_type == PenaltyType.TIME_15S:
            return 15.0

        # Drive-through or stop-and-go served post-race
        # In real F1, these would need to be served during race
        # For simulation, approximate with time penalty
        elif penalty.penalty_type == PenaltyType.DRIVE_THROUGH:
            return self.DRIVE_THROUGH_TIME
        elif penalty.penalty_type == PenaltyType.STOP_GO_5S:
            return self.STOP_GO_5S_TIME + 5.0
        elif penalty.penalty_type == PenaltyType.STOP_GO_10S:
            return self.STOP_GO_10S_TIME + 10.0
        elif penalty.penalty_type == PenaltyType.STOP_GO_15S:
            return self.STOP_GO_15S_TIME + 15.0

        return 0.0

    def get_penalty_time_impact(
        self,
        penalty: Penalty,
        serve_at_pit: bool,
    ) -> float:
        """
        Get the total time impact of a penalty.

        Args:
            penalty: The penalty
            serve_at_pit: Whether serving at pit stop

        Returns:
            Additional seconds to race time
        """
        if serve_at_pit:
            return self.get_pit_stop_penalty_time(penalty)
        else:
            return self.get_post_race_penalty_time(penalty)

    def can_serve_during_race(self, penalty: Penalty) -> bool:
        """
        Check if a penalty can be served during the race.

        All penalties can theoretically be served during race,
        but drive-through/stop-and-go are the only ones that MUST be.

        Args:
            penalty: The penalty

        Returns:
            True if can be served during race
        """
        return penalty.penalty_type in [
            PenaltyType.TIME_5S,
            PenaltyType.TIME_10S,
            PenaltyType.TIME_15S,
            PenaltyType.DRIVE_THROUGH,
            PenaltyType.STOP_GO_5S,
            PenaltyType.STOP_GO_10S,
            PenaltyType.STOP_GO_15S,
        ]

    def calculate_total_penalty_time(
        self,
        penalties: List[Penalty],
        serve_at_pit: bool,
    ) -> float:
        """
        Calculate total time impact for multiple penalties.

        Args:
            penalties: List of penalties
            serve_at_pit: Whether serving at pit stop

        Returns:
            Total additional seconds
        """
        total = 0.0
        for penalty in penalties:
            total += self.get_penalty_time_impact(penalty, serve_at_pit)
        return total

    def serve_penalties_at_pit(
        self,
        penalties: List[Penalty],
    ) -> Tuple[float, List[Penalty]]:
        """
        Serve multiple penalties at a pit stop.

        Args:
            penalties: List of penalties to serve

        Returns:
            Tuple of (additional pit time, list of served penalties)
        """
        total_time = 0.0
        served = []

        for penalty in penalties:
            time_impact = self.get_pit_stop_penalty_time(penalty)
            total_time += time_impact
            served.append(penalty)

        return total_time, served
