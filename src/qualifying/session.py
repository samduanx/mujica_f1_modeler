"""
Qualifying Session Manager

Manages individual qualifying sessions (Q1, Q2, Q3, SQ1, SQ2, SQ3).
"""

from typing import List, Tuple, Optional
from src.qualifying.types import (
    QualifyingSessionState,
    QualifyingLap,
    FlagState,
    QualifyingIncident,
)


class QualifyingSessionManager:
    """Manages a single qualifying session (Q1, Q2, or Q3)."""

    def __init__(
        self,
        session_name: str,
        duration_minutes: int,
        drivers: List[str],
        elimination_count: int = 5,
    ):
        """
        Initialize session manager.

        Args:
            session_name: Name of session (Q1, Q2, Q3, etc.)
            duration_minutes: Session duration in minutes
            drivers: List of participating drivers
            elimination_count: Number of drivers to eliminate
        """
        self.session_name = session_name
        self.duration = duration_minutes * 60.0  # Convert to seconds
        self.elimination_count = elimination_count

        self.state = QualifyingSessionState(
            session_name=session_name,
            duration=self.duration,
            remaining_time=self.duration,
            drivers_active=drivers.copy(),
            drivers_eliminated=[],
            best_times={driver: float("inf") for driver in drivers},
            laps_completed={driver: [] for driver in drivers},
        )

        self.incidents: List[QualifyingIncident] = []
        self.elapsed_time: float = 0.0

    def start_session(self) -> None:
        """Start the session timer."""
        self.state.clock_running = True
        print(f"\n{'=' * 60}")
        print(f"{self.session_name} STARTED - {self.duration / 60:.0f} minutes")
        print(f"Drivers: {len(self.state.drivers_active)}")
        print(f"Eliminating: {self.elimination_count} drivers")
        print(f"{'=' * 60}")

    def update_time(self, elapsed_seconds: float) -> None:
        """
        Update session time.

        Args:
            elapsed_seconds: Seconds elapsed since last update
        """
        if not self.state.clock_running:
            return

        self.elapsed_time += elapsed_seconds
        self.state.remaining_time = max(0, self.duration - self.elapsed_time)

        # Auto-end if time expires
        if self.state.remaining_time <= 0:
            self.state.clock_running = False

    def pause_session(self) -> None:
        """Pause session (e.g., for red flag)."""
        self.state.clock_running = False
        self.state.flag_state = FlagState.RED
        print(f"\n*** {self.session_name} PAUSED - Red Flag ***")

    def resume_session(self) -> None:
        """Resume session after pause."""
        self.state.clock_running = True
        self.state.flag_state = FlagState.GREEN
        print(f"\n*** {self.session_name} RESUMED ***")
        print(f"Remaining time: {self.state.remaining_time / 60:.1f} minutes")

    def record_lap_time(
        self, driver: str, lap_time: float, lap: Optional[QualifyingLap] = None
    ) -> None:
        """
        Record a driver's lap time.

        Args:
            driver: Driver name
            lap_time: Lap time in seconds
            lap: Optional QualifyingLap object with details
        """
        if driver not in self.state.drivers_active:
            return

        # Update best time
        current_best = self.state.best_times.get(driver, float("inf"))
        if lap_time < current_best:
            self.state.best_times[driver] = lap_time

        # Store lap details
        if lap:
            if driver not in self.state.laps_completed:
                self.state.laps_completed[driver] = []
            self.state.laps_completed[driver].append(lap)

    def record_incident(self, incident: QualifyingIncident) -> None:
        """Record an incident during the session."""
        self.incidents.append(incident)

        # Handle flag
        if incident.flag_triggered == "red":
            self.pause_session()
        elif incident.flag_triggered == "yellow":
            self.state.flag_state = FlagState.YELLOW

    def get_current_standings(self) -> List[Tuple[str, float]]:
        """
        Get current classification.

        Returns:
            List of (driver, best_time) tuples sorted by time
        """
        # Filter out drivers with no valid time
        valid_times = {
            driver: time
            for driver, time in self.state.best_times.items()
            if time != float("inf") and driver in self.state.drivers_active
        }

        # Sort by time
        sorted_drivers = sorted(valid_times.items(), key=lambda x: x[1])
        return sorted_drivers

    def get_driver_position(self, driver: str) -> int:
        """Get current position of a driver."""
        standings = self.get_current_standings()
        for pos, (drv, _) in enumerate(standings, 1):
            if drv == driver:
                return pos
        return len(self.state.drivers_active)

    def is_driver_safe(self, driver: str) -> bool:
        """
        Check if driver is currently safe from elimination.

        Returns:
            True if driver is in advancing positions
        """
        position = self.get_driver_position(driver)
        advancing_count = len(self.state.drivers_active) - self.elimination_count
        return position <= advancing_count and position > 0

    def get_cutoff_time(self) -> Optional[float]:
        """Get the current cutoff time for advancing."""
        standings = self.get_current_standings()
        advancing_count = len(self.state.drivers_active) - self.elimination_count

        if len(standings) >= advancing_count:
            return standings[advancing_count - 1][1]
        return None

    def end_session(self) -> Tuple[List[str], List[str]]:
        """
        End session and determine advancing/eliminated drivers.

        Returns:
            Tuple of (advancing_drivers, eliminated_drivers)
        """
        self.state.clock_running = False

        # Get final standings
        standings = self.get_current_standings()

        # Sort all active drivers by best time
        sorted_drivers = [driver for driver, _ in standings]

        # Add drivers with no time to the end
        for driver in self.state.drivers_active:
            if driver not in sorted_drivers:
                sorted_drivers.append(driver)

        # Determine advancing and eliminated
        if self.elimination_count == 0:
            # Q3/SQ3 - no elimination, all drivers advance (for pole position determination)
            advancing = sorted_drivers
            eliminated = []
        elif len(sorted_drivers) > self.elimination_count:
            advancing = sorted_drivers[: -self.elimination_count]
            eliminated = sorted_drivers[-self.elimination_count :]
        else:
            advancing = sorted_drivers
            eliminated = []

        # Update state
        self.state.drivers_active = advancing
        self.state.drivers_eliminated = eliminated

        # Print results
        print(f"\n{'=' * 60}")
        print(f"{self.session_name} RESULTS")
        print(f"{'=' * 60}")
        print(f"\nAdvancing to next session ({len(advancing)} drivers):")
        for i, driver in enumerate(advancing, 1):
            time = self.state.best_times.get(driver, None)
            time_str = f"{time:.3f}s" if time and time != float("inf") else "No time"
            print(f"  {i}. {driver} - {time_str}")

        if self.elimination_count > 0:
            print(f"\nEliminated ({len(eliminated)} drivers):")
            for i, driver in enumerate(eliminated, 1):
                time = self.state.best_times.get(driver, None)
                time_str = f"{time:.3f}s" if time and time != float("inf") else "No time"
                grid_pos = len(advancing) + i
                print(f"  {grid_pos}. {driver} - {time_str}")
        else:
            print(f"\nGrid positions determined ({len(advancing)} drivers)")

        return advancing, eliminated

    def get_session_summary(self) -> dict:
        """Get session summary statistics."""
        return {
            "session": self.session_name,
            "duration": self.duration,
            "remaining_time": self.state.remaining_time,
            "total_laps": sum(len(laps) for laps in self.state.laps_completed.values()),
            "incidents": len(self.incidents),
            "standings": self.get_current_standings()[:10],  # Top 10
        }
