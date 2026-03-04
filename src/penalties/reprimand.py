"""
Reprimand Tracker.

Manages reprimands for drivers.
3 reprimands in a season = 10-place grid penalty.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


# 3 reprimands = 10-place grid penalty
REPRIMANDS_FOR_GRID_PENALTY = 3


@dataclass
class ReprimandEntry:
    """A single reprimand entry."""

    reprimand_id: str
    driver: str
    reason: str
    race_name: str
    date: datetime
    is_driving_offense: bool = False

    def to_dict(self):
        return {
            "reprimand_id": self.reprimand_id,
            "driver": self.driver,
            "reason": self.reason,
            "race_name": self.race_name,
            "date": self.date.isoformat(),
            "is_driving_offense": self.is_driving_offense,
        }


class ReprimandTracker:
    """
    Track reprimands for drivers.

    According to F1 Sporting Regulations:
    - 3 reprimands in a season = 10-place grid penalty
    - At least 2 must be for driving offenses to trigger grid penalty
    """

    def __init__(self):
        """Initialize the reprimand tracker."""
        # driver -> list of reprimand entries
        self._reprimands: Dict[str, List[ReprimandEntry]] = {}

        # Track grid penalties from reprimands
        self._grid_penalties_from_reprimands: Dict[str, int] = {}

        # Counter for unique IDs
        self._reprimand_counter = 0

    def add_reprimand(
        self,
        driver: str,
        reason: str,
        race_name: str,
        is_driving_offense: bool = False,
        date: Optional[datetime] = None,
    ) -> ReprimandEntry:
        """
        Add a reprimand to a driver.

        Args:
            driver: Driver name
            reason: Reason for the reprimand
            race_name: The race where reprimand was given
            is_driving_offense: Whether this is a driving offense
            date: Date of reprimand (default: now)

        Returns:
            The created reprimand entry
        """
        self._reprimand_counter += 1

        if date is None:
            date = datetime.now()

        entry = ReprimandEntry(
            reprimand_id=f"R{self._reprimand_counter:04d}",
            driver=driver,
            reason=reason,
            race_name=race_name,
            date=date,
            is_driving_offense=is_driving_offense,
        )
        
        if driver not in self._reprimands:
            self._reprimands[driver] = []
        
        self._reprimands[driver].append(entry)

        return entry

    def get_reprimand_count(self, driver: str) -> int:
        """
        Get total number of reprimands for a driver.

        Args:
            driver: Driver name

        Returns:
            Number of reprimands
        """
        if driver not in self._reprimands:
            return 0
        return len(self._reprimands[driver])

    def get_driving_offense_count(self, driver: str) -> int:
        """
        Get number of reprimands for driving offenses.

        Args:
            driver: Driver name

        Returns:
            Number of driving offense reprimands
        """
        if driver not in self._reprimands:
            return 0
        return sum(
            1
            for r in self._reprimands[driver]
            if getattr(r, "is_driving_offense", False)
        )

    def should_trigger_grid_penalty(self, driver: str) -> bool:
        """
        Check if reprimands should trigger a 10-place grid penalty.

        Per regulations: 3 reprimands, with at least 2 for driving offenses.

        Args:
            driver: Driver name

        Returns:
            True if should trigger grid penalty
        """
        total = self.get_reprimand_count(driver)
        driving = self.get_driving_offense_count(driver)

        return total >= REPRIMANDS_FOR_GRID_PENALTY and driving >= 2

    def apply_grid_penalty_from_reprimand(self, driver: str) -> bool:
        """
        Apply 10-place grid penalty from accumulated reprimands.

        Should be called when should_trigger_grid_penalty() returns True.

        Args:
            driver: Driver name

        Returns:
            True if grid penalty was applied
        """
        if self.should_trigger_grid_penalty(driver):
            if driver not in self._grid_penalties_from_reprimands:
                self._grid_penalties_from_reprimands[driver] = 0
            self._grid_penalties_from_reprimands[driver] += 10
            return True
        return False

    def get_grid_penalty_from_reprimands(self, driver: str) -> int:
        """
        Get grid penalty positions from reprimands.

        Args:
            driver: Driver name

        Returns:
            Positions to drop
        """
        return self._grid_penalties_from_reprimands.get(driver, 0)

    def get_all_reprimands(self, driver: str) -> List[ReprimandEntry]:
        """Get all reprimands for a driver."""
        return self._reprimands.get(driver, [])

    def reset_driver(self, driver: str):
        """Reset reprimands for a driver."""
        if driver in self._reprimands:
            del self._reprimands[driver]
        if driver in self._grid_penalties_from_reprimands:
            del self._grid_penalties_from_reprimands[driver]

    def reset_all(self):
        """Reset all reprimands."""
        self._reprimands.clear()
        self._grid_penalties_from_reprimands.clear()
        self._reprimand_counter = 0
