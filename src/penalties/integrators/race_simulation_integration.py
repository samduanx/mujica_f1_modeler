"""
Race Simulation Integration.

Integrates the penalty system with the enhanced race simulation.
"""

from typing import Dict, List, Optional, Tuple

from src.penalties.penalty_manager import PenaltyManager
from src.penalties.penalty_points import PenaltyPoints, POINTS_FOR_RACE_BAN
from src.penalties.penalty_service import PenaltyService
from src.penalties.penalty_types import (
    PenaltyType,
    Penalty,
)
from src.penalties.integrators.overtake_penalties import OvertakePenaltyHandler
from src.penalties.integrators.blue_flag_penalties import BlueFlagPenaltyHandler
from src.penalties.integrators.vsc_penalties import VSCViolationHandler
from src.penalties.integrators.incident_penalties import IncidentPenaltyHandler
from src.incidents.incident_types import IncidentSeverity
from src.incidents.blue_flag import ResistanceLevel


class RacePenaltyIntegration:
    """
    Integrates penalty system with race simulation.

    Responsibilities:
    - Initialize penalty system components
    - Assess penalties from race incidents
    - Serve penalties at pit stops
    - Apply post-race penalties to final results
    - Track penalty points across races
    """

    def __init__(self, track_name: str, year: int):
        """
        Initialize the penalty integration.

        Args:
            track_name: Name of the track
            year: Race year
        """
        self.track_name = track_name
        self.year = year

        # Initialize penalty system components
        self.penalty_manager = PenaltyManager()
        self.penalty_points = PenaltyPoints()
        self.penalty_service = PenaltyService()

        # Initialize integrators
        self.overtake_handler = OvertakePenaltyHandler(self.penalty_manager)
        self.blue_flag_handler = BlueFlagPenaltyHandler(self.penalty_manager)
        self.vsc_handler = VSCViolationHandler(self.penalty_manager)
        self.incident_handler = IncidentPenaltyHandler(self.penalty_manager)

        # Track which drivers have served penalties at which pit stops
        self.served_at_pit: Dict[str, List[int]] = {}

    def handle_overtake_collision(
        self,
        attacker: str,
        defender: str,
        severity: IncidentSeverity,
        race_time: float,
        lap: int,
    ) -> Optional[Dict]:
        """
        Handle an overtake collision incident.

        Args:
            attacker: Attacking driver
            defender: Defending driver
            severity: Collision severity
            race_time: Current race time
            lap: Current lap

        Returns:
            Penalty info dict or None
        """
        result = self.overtake_handler.handle_overtake_collision(
            attacker=attacker,
            defender=defender,
            severity=severity,
            time=race_time,
            lap=lap,
        )

        if result and result.get("penalty"):
            # Add penalty points
            self.penalty_points.add_points(
                result["driver_penalized"],
                result["penalty"].points,
                f"Overtake collision with {defender}",
            )

        return result

    def handle_blue_flag_violation(
        self,
        driver: str,
        resistance_level: ResistanceLevel,
        offense_count: int,
        race_time: float,
        lap: int,
    ) -> Optional[Dict]:
        """Handle blue flag violation."""
        result = self.blue_flag_handler.handle_blue_flag_violation(
            driver=driver,
            resistance_level=resistance_level,
            offense_count=offense_count,
            time=race_time,
            lap=lap,
        )

        if result and result.get("penalty"):
            self.penalty_points.add_points(
                driver, result["penalty"].points, "Blue flag violation"
            )

        return result

    def handle_unsafe_release(
        self,
        involved_drivers: List[str],
        severity: str,
        race_time: float,
        lap: int,
    ) -> Dict:
        """
        Handle unsafe release from pit.

        Note: No penalty points, just time loss to all involved drivers.
        """
        return self.incident_handler.handle_unsafe_release(
            involved_drivers=involved_drivers,
            severity=severity,
            time=race_time,
            lap=lap,
        )

    def handle_pit_stop_with_penalties(
        self,
        driver: str,
        lap: int,
        base_pit_time: float,
        has_more_pit_stops: bool,
    ) -> Tuple[float, List[Penalty]]:
        """
        Handle pit stop including any penalty serving.

        Args:
            driver: Driver name
            lap: Current lap
            base_pit_time: Normal pit stop time
            has_more_pit_stops: Whether driver will pit again

        Returns:
            Tuple of (total_pit_time, list_of_served_penalties)
        """
        total_pit_time = base_pit_time
        served_penalties = []

        # Get pending penalties for this driver
        pending = self.penalty_manager.get_pending_penalties(driver)

        if not pending:
            return total_pit_time, served_penalties

        # Check which penalties can be served
        penalties_to_serve = []
        for penalty in pending:
            # Time penalties can be served at pit or post-race
            if penalty.penalty_type in [
                PenaltyType.TIME_5S,
                PenaltyType.TIME_10S,
                PenaltyType.TIME_15S,
            ]:
                # Serve at pit if driver will pit again, or serve all if this is the last stop
                if has_more_pit_stops:
                    penalties_to_serve.append(penalty)
            # Drive-through and stop-and-go must be served during race
            elif penalty.penalty_type in [
                PenaltyType.DRIVE_THROUGH,
                PenaltyType.STOP_GO_5S,
                PenaltyType.STOP_GO_10S,
                PenaltyType.STOP_GO_15S,
            ]:
                penalties_to_serve.append(penalty)

        # Calculate penalty time
        if penalties_to_serve:
            penalty_time, served = self.penalty_service.serve_penalties_at_pit(
                penalties_to_serve
            )
            total_pit_time += penalty_time

            # Mark penalties as served
            for penalty in served:
                self.penalty_manager.serve_penalty(
                    driver=driver,
                    penalty_id=penalty.penalty_id,
                    served_at="pit_stop",
                    served_at_lap=lap,
                )
                served_penalties.append(penalty)

        return total_pit_time, served_penalties

    def _has_more_pit_stops(self, driver: str, current_lap: int, total_laps: int = 70) -> bool:
        """
        Check if driver has more pit stops scheduled.

        This is a simple heuristic - in a full implementation, this would
        be connected to the actual pit strategy data from the simulation.

        Args:
            driver: Driver name
            current_lap: Current lap number
            total_laps: Total race distance (default: 70 for typical F1 race)

        Returns:
            True if driver likely has more pit stops
        """
        # Simple heuristic: if more than 20% of race remaining, assume more stops possible
        # This is a placeholder - real implementation would check strategy data
        remaining_fraction = (total_laps - current_lap) / total_laps
        return remaining_fraction > 0.2

    def get_post_race_penalty_time(self, driver: str) -> float:
        """
        Get total time penalties to add after race.

        Args:
            driver: Driver name

        Returns:
            Total seconds to add to race time
        """
        return self.penalty_manager.get_post_race_time_penalties(driver)

    def get_total_time_loss(self, driver: str) -> float:
        """Get total time loss from incidents like unsafe release."""
        return self.penalty_manager.get_total_time_loss(driver)

    def check_race_bans(self) -> List[str]:
        """
        Check for drivers who should be banned.

        Returns:
            List of driver names who should receive race ban
        """
        banned = []
        for driver, points in self.penalty_points.get_all_drivers_points().items():
            if points >= POINTS_FOR_RACE_BAN:
                banned.append(driver)
        return banned

    def get_penalties_summary(self) -> Dict:
        """Get summary of all penalties for this race."""
        return self.penalty_manager.get_penalties_summary()

    def get_penalty_points_summary(self) -> Dict[str, int]:
        """Get penalty points for all drivers."""
        return self.penalty_points.get_all_drivers_points()

    def reset(self):
        """Reset for a new race."""
        self.penalty_manager.reset()
        self.served_at_pit.clear()
