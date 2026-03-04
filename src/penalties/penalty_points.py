"""
Penalty Points System.

Tracks penalty points on drivers' Super Licences.
Penalty points expire after 12 months.
12 points = automatic race ban.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# 12 points triggers a race ban
POINTS_FOR_RACE_BAN = 12

# Points expire after 12 months
POINTS_EXPIRY_MONTHS = 12


@dataclass
class PenaltyPointEntry:
    """A single penalty point entry with expiry tracking."""

    points: int
    date_added: datetime
    reason: str
    expires_at: datetime = field(init=False)

    def __post_init__(self):
        self.expires_at = self.date_added + timedelta(days=30 * POINTS_EXPIRY_MONTHS)

    def is_expired(self, current_date: Optional[datetime] = None) -> bool:
        """Check if these points have expired."""
        if current_date is None:
            current_date = datetime.now()
        return current_date >= self.expires_at


class PenaltyPoints:
    """
    Track penalty points for drivers across races.

    Points are added when penalties are assessed and expire after 12 months.
    When a driver reaches 12 points, they receive an automatic race ban.
    """

    def __init__(self):
        """Initialize the penalty points tracker."""
        # driver -> list of point entries
        self._points: Dict[str, List[PenaltyPointEntry]] = {}

        # Track drivers who have served race bans
        self._race_ban_history: Dict[str, int] = {}  # driver -> number of bans

    def add_points(
        self,
        driver: str,
        points: int,
        reason: str,
        date_added: Optional[datetime] = None,
    ) -> List[PenaltyPointEntry]:
        """
        Add penalty points to a driver.

        Args:
            driver: Driver name
            points: Number of points to add
            reason: Reason for the points
            date_added: When points were added (default: now)

        Returns:
            List of created point entries
        """
        if date_added is None:
            date_added = datetime.now()

        entries = []
        for _ in range(points):
            entry = PenaltyPointEntry(
                points=1,  # Each entry is 1 point
                date_added=date_added,
                reason=reason,
            )
            entries.append(entry)

            if driver not in self._points:
                self._points[driver] = []
            self._points[driver].append(entry)

        return entries

    def get_points(self, driver: str, current_date: Optional[datetime] = None) -> int:
        """
        Get current valid penalty points for a driver.

        Args:
            driver: Driver name
            current_date: Date to check points at (default: now)

        Returns:
            Current valid points (expired points excluded)
        """
        if current_date is None:
            current_date = datetime.now()

        if driver not in self._points:
            return 0

        total = 0
        for entry in self._points[driver]:
            if not entry.is_expired(current_date):
                total += entry.points

        return total

    def get_all_points_with_expiry(self, driver: str) -> Dict:
        """
        Get all points with their expiry information.

        Args:
            driver: Driver name

        Returns:
            Dictionary with current, expiring soon, and expired points
        """
        if driver not in self._points:
            return {
                "current": 0,
                "expiring_soon": 0,
                "expired": 0,
                "entries": [],
            }

        current_date = datetime.now()
        thirty_days = timedelta(days=30)

        current = 0
        expiring_soon = 0
        expired = 0

        for entry in self._points[driver]:
            if entry.is_expired(current_date):
                expired += entry.points
            elif entry.expires_at - current_date < thirty_days:
                expiring_soon += entry.points
            else:
                current += entry.points

        return {
            "current": current,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "total": current + expiring_soon + expired,
            "entries": [
                {
                    "points": e.points,
                    "date_added": e.date_added.isoformat(),
                    "expires_at": e.expires_at.isoformat(),
                    "reason": e.reason,
                }
                for e in self._points[driver]
            ],
        }

    def check_race_ban(self, driver: str) -> bool:
        """
        Check if driver should receive a race ban (12+ points).

        Args:
            driver: Driver name

        Returns:
            True if driver has 12+ points and should be banned
        """
        current_points = self.get_points(driver)
        return current_points >= POINTS_FOR_RACE_BAN

    def expire_points(self, current_date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Remove expired points from all drivers.

        Args:
            current_date: Date to check against (default: now)

        Returns:
            Dictionary of drivers and how many points expired
        """
        if current_date is None:
            current_date = datetime.now()

        expired_counts = {}

        for driver, entries in self._points.items():
            expired = 0
            remaining = []

            for entry in entries:
                if entry.is_expired(current_date):
                    expired += 1
                else:
                    remaining.append(entry)

            if expired > 0:
                expired_counts[driver] = expired
                self._points[driver] = remaining

        return expired_counts

    def serve_race_ban(self, driver: str) -> bool:
        """
        Record that a driver has served a race ban.

        This removes all current points after the ban is served.

        Args:
            driver: Driver name

        Returns:
            True if driver was banned (had 12+ points)
        """
        if self.check_race_ban(driver):
            # Clear all current points
            if driver in self._points:
                self._points[driver] = [
                    e for e in self._points[driver] if e.is_expired()
                ]

            # Record ban
            if driver not in self._race_ban_history:
                self._race_ban_history[driver] = 0
            self._race_ban_history[driver] += 1

            return True

        return False

    def get_race_ban_count(self, driver: str) -> int:
        """Get number of race bans a driver has served."""
        return self._race_ban_history.get(driver, 0)

    def get_all_drivers_points(self) -> Dict[str, int]:
        """Get points for all drivers."""
        return {driver: self.get_points(driver) for driver in self._points.keys()}

    def reset_driver(self, driver: str):
        """Reset points for a driver (e.g., after season reset)."""
        if driver in self._points:
            del self._points[driver]
        if driver in self._race_ban_history:
            del self._race_ban_history[driver]

    def reset_all(self):
        """Reset all points (e.g., for new season)."""
        self._points.clear()
        self._race_ban_history.clear()
