"""
Grid Penalty Tracker.

Manages grid penalties for future races.
Penalties accumulate and are applied to starting positions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class GridPenaltyEntry:
    """A single grid penalty entry."""

    penalty_id: str
    driver: str
    positions_dropped: int
    reason: str
    race_name: str  # The race where penalty was given
    applied: bool = False

    def to_dict(self):
        return {
            "penalty_id": self.penalty_id,
            "driver": self.driver,
            "positions_dropped": self.positions_dropped,
            "reason": self.reason,
            "race_name": self.race_name,
            "applied": self.applied,
        }


class GridPenaltyTracker:
    """
    Track grid penalties for future races.

    Grid penalties are stored and applied when generating
    starting grids for upcoming races.
    """

    def __init__(self):
        """Initialize the grid penalty tracker."""
        # driver -> list of grid penalty entries
        self._penalties: Dict[str, List[GridPenaltyEntry]] = {}

        # Counter for unique IDs
        self._penalty_counter = 0

    def add_grid_penalty(
        self,
        driver: str,
        positions_dropped: int,
        reason: str,
        race_name: str,
    ) -> GridPenaltyEntry:
        """
        Add a grid penalty for a driver.

        Args:
            driver: Driver name
            positions_dropped: Number of positions to drop
            reason: Reason for the penalty
            race_name: The race where penalty was given

        Returns:
            The created penalty entry
        """
        self._penalty_counter += 1

        entry = GridPenaltyEntry(
            penalty_id=f"GP{self._penalty_counter:04d}",
            driver=driver,
            positions_dropped=positions_dropped,
            reason=reason,
            race_name=race_name,
        )

        if driver not in self._penalties:
            self._penalties[driver] = []
        self._penalties[driver].append(entry)

        return entry

    def get_pending_penalties(self, driver: str) -> List[GridPenaltyEntry]:
        """
        Get pending (not applied) grid penalties for a driver.

        Args:
            driver: Driver name

        Returns:
            List of pending grid penalties
        """
        if driver not in self._penalties:
            return []

        return [p for p in self._penalties[driver] if not p.applied]

    def get_total_positions_drop(self, driver: str) -> int:
        """
        Get total positions to drop for a driver.

        Args:
            driver: Driver name

        Returns:
            Total positions to drop
        """
        pending = self.get_pending_penalties(driver)
        return sum(p.positions_dropped for p in pending)

    def apply_penalties(self, driver: str) -> int:
        """
        Apply all pending grid penalties for a driver.

        Marks penalties as applied after they've been used
        to modify starting grid.

        Args:
            driver: Driver name

        Returns:
            Total positions dropped
        """
        total_drop = self.get_total_positions_drop(driver)

        if driver in self._penalties:
            for entry in self._penalties[driver]:
                if not entry.applied:
                    entry.applied = True

        return total_drop

    def apply_to_grid(
        self,
        original_grid: List[str],
    ) -> Dict[str, int]:
        """
        Apply grid penalties to a starting grid.

        Args:
            original_grid: List of driver names in qualifying order

        Returns:
            Dictionary of driver -> positions dropped
        """
        # Build position map
        position_map = {driver: pos for pos, driver in enumerate(original_grid)}
        drops = {}

        # Process drivers in order (front to back)
        for driver in original_grid:
            drop = self.get_total_positions_drop(driver)
            if drop > 0:
                drops[driver] = drop
                # Apply so they're not used again
                self.apply_penalties(driver)

        return drops

    def get_all_pending(self) -> Dict[str, List[GridPenaltyEntry]]:
        """Get all pending penalties for all drivers."""
        result = {}
        for driver, penalties in self._penalties.items():
            pending = [p for p in penalties if not p.applied]
            if pending:
                result[driver] = pending
        return result

    def reset_driver(self, driver: str):
        """Reset penalties for a driver."""
        if driver in self._penalties:
            del self._penalties[driver]

    def reset_all(self):
        """Reset all penalties."""
        self._penalties.clear()
        self._penalty_counter = 0
