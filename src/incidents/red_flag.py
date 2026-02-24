"""
Red Flag System for F1 Simulator.

Implements red flag procedures based on F1 Sporting Regulations:
- Red flag triggers (weather, track blocked, multiple incidents)
- Race distance thresholds (90% = race ends, <75% = restart)
- Restart procedures (standing start)
- Points calculation flags for different race end scenarios
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class RaceEndReason(Enum):
    """
    Reasons for race ending - useful for points calculation.

    Attributes:
        NORMAL: Race completed normally
        RED_FLAG_TIME: Red flag, race ended due to insufficient time
        RED_FLAG_THRESHOLD: Red flag, race ended (>90% complete)
        RED_FLAG_RESTART: Red flag, race resumed with standing start
        ABANDONED: Race abandoned (less than 2 laps)
    """

    NORMAL = "normal"
    RED_FLAG_TIME = "red_flag_time"  # Insufficient time to restart
    RED_FLAG_THRESHOLD = "red_flag_threshold"  # >90% complete
    RED_FLAG_RESTART = "red_flag_restart"  # Race resumed
    ABANDONED = "abandoned"  # Less than 2 laps


class RaceCompletionStatus(Enum):
    """
    Race completion status for points calculation.

    FULL: 100% distance completed - full points
    PARTIAL_RED_FLAG: Red flag ended race, partial points (if 75-90%)
    PARTIAL_ABANDONED: Race abandoned, no points (if <75%)
    """

    FULL = "full"
    PARTIAL_RED_FLAG = "partial_red_flag"  # 75-90%, ended due to time
    PARTIAL_THRESHOLD = "partial_threshold"  # >90%, full points
    PARTIAL_ABANDONED = "partial_abandoned"  # <75%, no points


class RedFlagOutcome(Enum):
    """Red flag outcomes"""

    RESTART = "restart"  # Race will resume
    END = "end"  # Race ended
    ABANDON = "abandon"  # Race abandoned


class RestartType(Enum):
    """Type of race restart"""

    STANDING = "standing"
    ROLLING = "rolling"


@dataclass
class RedFlagRaceDistanceRules:
    """
    Race distance rules for red flag situations.

    Based on F1 Sporting Regulations Article 5.4:
    - Less than 2 laps completed: Race may be abandoned
    - 2-75% complete: Race can be resumed
    - 75-90% complete: Race may be ended if insufficient time
    - More than 90% complete: Race may be ended
    """

    # Minimum laps for classification
    min_laps_for_result: int = 2

    # Distance thresholds (as percentage)
    resume_threshold: float = 0.75  # 75% - can still resume
    end_race_threshold: float = 0.90  # 90% - race may be ended

    # Maximum race duration in seconds (2 hours + 1 lap buffer)
    max_race_duration: float = 7200

    # Estimated time for restart procedure (seconds)
    restart_overhead: float = 600  # 10 minutes

    def determine_outcome(
        self,
        completed_laps: int,
        total_laps: int,
        race_time: float,
    ) -> Dict:
        """
        Determine race outcome based on red flag timing.

        Args:
            completed_laps: Number of laps completed before red flag
            total_laps: Total race distance in laps
            race_time: Current race time in seconds

        Returns:
            Dict containing:
            - outcome: "restart", "end", "abandon"
            - reason: Human-readable explanation
            - end_reason: RaceEndReason enum value
            - completion_status: RaceCompletionStatus for points
            - classification_lap: Lap to use for results
            - full_points: Whether full points are awarded
        """
        completion_ratio = completed_laps / total_laps

        # Less than minimum laps - no result
        if completed_laps < self.min_laps_for_result:
            return {
                "outcome": RedFlagOutcome.ABANDON.value,
                "reason": "Less than 2 laps completed - race abandoned",
                "end_reason": RaceEndReason.ABANDONED,
                "completion_status": RaceCompletionStatus.PARTIAL_ABANDONED,
                "classification_lap": 0,
                "full_points": False,
                "points_percentage": 0.0,
                "remaining_laps": total_laps,
            }

        # More than 90% complete - race ends (threshold rule)
        if completion_ratio >= self.end_race_threshold:
            return {
                "outcome": RedFlagOutcome.END.value,
                "reason": f"More than 90% complete ({completion_ratio:.1%}) - race ended",
                "end_reason": RaceEndReason.RED_FLAG_THRESHOLD,
                "completion_status": RaceCompletionStatus.PARTIAL_THRESHOLD,
                "classification_lap": completed_laps,
                "full_points": True,  # Full points even though not 100%
                "points_percentage": 1.0,
                "remaining_laps": total_laps - completed_laps,
            }

        # More than 75% but less than 90% - check time
        if completion_ratio >= self.resume_threshold:
            can_restart = self._can_restart_race(race_time)

            if not can_restart:
                # Insufficient time - end race
                return {
                    "outcome": RedFlagOutcome.END.value,
                    "reason": f"75-90% complete ({completion_ratio:.1%}), insufficient time for restart - race ended",
                    "end_reason": RaceEndReason.RED_FLAG_TIME,
                    "completion_status": RaceCompletionStatus.PARTIAL_RED_FLAG,
                    "classification_lap": completed_laps,
                    "full_points": True,  # Full points if >75%
                    "points_percentage": 1.0,
                    "remaining_laps": total_laps - completed_laps,
                    "insufficient_time": True,  # Flag for points calculation
                }
            else:
                # Time available - restart
                return {
                    "outcome": RedFlagOutcome.RESTART.value,
                    "reason": f"75-90% complete ({completion_ratio:.1%}), restart possible",
                    "end_reason": RaceEndReason.RED_FLAG_RESTART,
                    "completion_status": RaceCompletionStatus.FULL,  # Will complete
                    "classification_lap": None,
                    "full_points": False,  # Not ended yet
                    "points_percentage": None,
                    "remaining_laps": total_laps - completed_laps,
                    "restart_type": RestartType.STANDING.value,
                }

        # Less than 75% - always restart
        return {
            "outcome": RedFlagOutcome.RESTART.value,
            "reason": f"Less than 75% complete ({completion_ratio:.1%}) - standing restart",
            "end_reason": RaceEndReason.RED_FLAG_RESTART,
            "completion_status": RaceCompletionStatus.FULL,  # Will complete
            "classification_lap": None,
            "full_points": False,  # Not ended yet
            "points_percentage": None,
            "remaining_laps": total_laps - completed_laps,
            "restart_type": RestartType.STANDING.value,
        }

    def _can_restart_race(self, current_race_time: float) -> bool:
        """
        Check if race can be restarted within time limits.

        F1 races have a maximum duration (typically 2 hours + 1 lap).
        """
        return (current_race_time + self.restart_overhead) < self.max_race_duration


@dataclass
class RedFlagTrigger:
    """
    Determine when red flag should be shown.

    Based on F1 Sporting Regulations and common racing practices.
    """

    # Minimum incidents for multi-incident trigger
    min_incidents_for_severe: int = 2

    def should_red_flag(
        self,
        incidents: List,  # List of Incident objects
        sector_flags: Optional[Dict[int, str]] = None,  # sector -> flag type
        weather: str = "dry",
        track_blocked: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if red flag should be shown.

        Triggers:
        - Track completely blocked
        - All sectors under double yellow
        - Multiple serious collisions
        - Severe weather (heavy rain, storm, poor visibility)
        - Track surface unsafe (oil, major debris)
        - Medical emergency requiring track access

        Args:
            incidents: List of active incidents
            sector_flags: Dict of sector -> flag status
            weather: Current weather condition
            track_blocked: Whether track is blocked

        Returns:
            Tuple of (should_red_flag, reason)
        """
        # Track completely blocked
        if track_blocked:
            return True, "Track completely blocked"

        # All sectors under double yellow
        if sector_flags:
            double_yellow_sectors = sum(
                1
                for flag in sector_flags.values()
                if flag in ["double_yellow", "DOUBLE_YELLOW"]
            )
            if double_yellow_sectors >= len(sector_flags) and double_yellow_sectors > 0:
                return True, "All sectors under double yellow - unsafe conditions"

        # Multiple serious incidents
        if incidents:
            severe_count = sum(
                1
                for i in incidents
                if hasattr(i, "severity") and i.severity.value == "severe"
            )
            if severe_count >= self.min_incidents_for_severe:
                return True, f"Multiple serious incidents ({severe_count} severe)"

        # Severe weather
        severe_weather_conditions = [
            "heavy_rain",
            "storm",
            "fog",
            "poor_visibility",
            "hurricane",
            "tornado",
        ]
        if weather in severe_weather_conditions:
            return True, f"Severe weather: {weather}"

        # Check for medical emergency in incidents
        for incident in incidents:
            if hasattr(incident, "description"):
                if "medical" in incident.description.lower():
                    return True, "Medical emergency"

        return False, "No red flag conditions met"

    def get_trigger_description(self, reason: str) -> str:
        """
        Get formatted description for red flag trigger.

        Args:
            reason: The reason for red flag

        Returns:
            Formatted message for display
        """
        return f"RED FLAG: {reason}"


@dataclass
class RedFlagManager:
    """
    Manage red flag periods during a race.

    Attributes:
        total_laps: Total race distance in laps
        track_length_km: Track length in kilometers
        is_red_flag: Whether red flag is currently shown
        start_time: Time when red flag was shown
        start_lap: Lap when red flag was shown
        start_distance: Distance covered when red flag shown
        outcome: Final race outcome
        classification_lap: Lap to use for final classification
        end_reason: Reason for race ending (for points calculation)
    """

    total_laps: int = 0
    track_length_km: float = 0.0

    # State
    is_red_flag: bool = False
    start_time: Optional[float] = None
    start_lap: Optional[int] = None
    start_distance: float = 0.0

    # Results
    outcome: Optional[str] = None
    classification_lap: Optional[int] = None
    end_reason: Optional[RaceEndReason] = None
    completion_status: Optional[RaceCompletionStatus] = None
    full_points: bool = False
    points_percentage: float = 1.0

    # History
    red_flag_periods: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        self.distance_rules = RedFlagRaceDistanceRules()

    def show_red_flag(
        self,
        race_time: float,
        lap: int,
        reason: str,
        car_positions: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str]:
        """
        Show red flag.

        All cars must return to pits immediately.

        Args:
            race_time: Current race time
            lap: Current lap number
            reason: Reason for red flag
            car_positions: Optional dict of car -> distance for tracking

        Returns:
            Tuple of (success, message)
        """
        if self.is_red_flag:
            return False, "Red flag already shown"

        self.is_red_flag = True
        self.start_time = race_time
        self.start_lap = lap
        self.start_distance = max(car_positions.values()) if car_positions else 0.0

        self.red_flag_periods.append(
            {
                "start_time": race_time,
                "start_lap": lap,
                "reason": reason,
                "start_distance": self.start_distance,
                "end_time": None,
                "duration": None,
                "outcome": None,
            }
        )

        return True, f"RED FLAG - Lap {lap}: {reason}"

    def assess_race_status(self) -> Dict:
        """
        Determine race outcome based on distance covered.

        Called after red flag to decide:
        - End race (if >90% or conditions prevent restart)
        - Standing restart (if <90% and conditions permit)

        Returns:
            Dict with race outcome details including:
            - outcome: "restart", "end", "abandon"
            - end_reason: RaceEndReason for points calculation
            - completion_status: RaceCompletionStatus
            - full_points: Whether full points awarded
            - insufficient_time: Flag for points system
        """
        if self.start_lap is None:
            return {"error": "Red flag not shown"}

        result = self.distance_rules.determine_outcome(
            completed_laps=self.start_lap,
            total_laps=self.total_laps,
            race_time=self.start_time if self.start_time else 0,
        )

        self.outcome = result.get("outcome")
        self.classification_lap = result.get("classification_lap")
        self.end_reason = result.get("end_reason")
        self.completion_status = result.get("completion_status")
        self.full_points = result.get("full_points", False)
        self.points_percentage = result.get("points_percentage", 1.0)

        return result

    def resume_race(
        self,
        race_time: float,
        standing_start: bool = True,
    ) -> Dict:
        """
        Resume race after red flag.

        Args:
            race_time: Current time when resuming
            standing_start: Whether to use standing start

        Returns:
            Dict with restart details
        """
        if not self.is_red_flag:
            return {"error": "Red flag not active"}

        self.is_red_flag = False

        if self.red_flag_periods:
            period = self.red_flag_periods[-1]
            period["end_time"] = race_time
            period["duration"] = race_time - period["start_time"]
            period["outcome"] = "restart"
            period["standing_start"] = standing_start

        return {
            "outcome": "restart",
            "restart_type": "standing" if standing_start else "rolling",
            "resumed_at": race_time,
            "remaining_laps": self.total_laps - (self.start_lap or 0),
            "resume_lap": (self.start_lap or 0) + 1,
        }

    def end_race_early(
        self,
        race_time: float,
        insufficient_time: bool = False,
    ) -> Dict:
        """
        End race early due to red flag.

        Results are taken from last completed lap before red flag.

        Args:
            race_time: Current time
            insufficient_time: Whether ending due to insufficient time

        Returns:
            Dict with race end details
        """
        if not self.is_red_flag:
            return {"error": "Red flag not active"}

        self.is_red_flag = False

        if self.red_flag_periods:
            period = self.red_flag_periods[-1]
            period["end_time"] = race_time
            period["duration"] = race_time - period["start_time"]
            period["outcome"] = "ended"

        # Build result
        result = {
            "outcome": "ended",
            "classification_lap": self.start_lap,
            "end_reason": self.end_reason,
            "completion_status": self.completion_status,
            "full_points": self.full_points,
            "points_percentage": self.points_percentage,
            "insufficient_time": insufficient_time,
        }

        if insufficient_time:
            result["reason"] = "Red flag - insufficient time to resume"
        else:
            result["reason"] = (
                f"Red flag - race distance threshold met ({self.start_lap}/{self.total_laps} laps)"
            )

        return result

    def get_points_info(self) -> Dict:
        """
        Get information useful for points calculation.

        Returns:
            Dict with:
            - end_reason: RaceEndReason enum value
            - completion_status: RaceCompletionStatus
            - full_points: Whether full points awarded
            - points_percentage: Percentage of points to award
            - classification_lap: Lap to use for final classification
        """
        return {
            "end_reason": self.end_reason.value if self.end_reason else None,
            "completion_status": self.completion_status.value
            if self.completion_status
            else None,
            "full_points": self.full_points,
            "points_percentage": self.points_percentage,
            "classification_lap": self.classification_lap,
            "insufficient_time": self.end_reason == RaceEndReason.RED_FLAG_TIME
            if self.end_reason
            else False,
        }

    def get_summary(self) -> Dict:
        """Get summary of red flag occurrences"""
        return {
            "total_red_flags": len(self.red_flag_periods),
            "periods": self.red_flag_periods,
            "final_outcome": self.outcome,
            "classification_lap": self.classification_lap,
            "end_reason": self.end_reason.value if self.end_reason else None,
            "points_info": self.get_points_info(),
        }


@dataclass
class RedFlagRestart:
    """
    Manage restart after red flag.
    """

    def __init__(self, red_flag_manager: RedFlagManager):
        self.rf_manager = red_flag_manager

    def prepare_standing_restart(
        self,
        grid_positions: Dict[str, int],  # car -> grid position
        car_status: Optional[Dict[str, str]] = None,  # car -> status
    ) -> Dict:
        """
        Prepare standing restart grid.

        Grid order is based on positions at last completed lap before red flag.

        Args:
            grid_positions: Dict of car -> position at time of red flag
            car_status: Optional dict of car -> status (running, retired, etc.)

        Returns:
            Dict with restart grid information
        """
        # Filter out retired/non-running cars if status provided
        if car_status:
            running_cars = {
                car: pos
                for car, pos in grid_positions.items()
                if car_status.get(car) == "running"
            }
        else:
            running_cars = grid_positions

        # Sort by position
        sorted_grid = sorted(running_cars.items(), key=lambda x: x[1])

        return {
            "restart_type": RestartType.STANDING.value,
            "grid": [car for car, _ in sorted_grid],
            "positions": {car: i + 1 for i, (car, _) in enumerate(sorted_grid)},
            "formation_lap": True,
            "total_cars": len(sorted_grid),
        }

    def get_restart_message(self) -> str:
        """Get restart announcement message"""
        if self.rf_manager.outcome == RedFlagOutcome.END.value:
            return "RACE ENDED - Results taken from lap before red flag"
        elif self.rf_manager.outcome == RedFlagOutcome.RESTART.value:
            return "RACE WILL RESUME - Standing start"
        elif self.rf_manager.outcome == RedFlagOutcome.ABANDON.value:
            return "RACE ABANDONED"
        else:
            return "RACE SUSPENDED"

    def get_classification_message(self) -> str:
        """Get message about final classification"""
        end_reason = self.rf_manager.end_reason

        if end_reason == RaceEndReason.RED_FLAG_TIME:
            return "Race ended due to insufficient time (red flag)"
        elif end_reason == RaceEndReason.RED_FLAG_THRESHOLD:
            return "Race ended (>90% distance covered)"
        elif end_reason == RaceEndReason.RED_FLAG_RESTART:
            return "Race resumed after red flag"
        elif end_reason == RaceEndReason.ABANDONED:
            return "Race abandoned (less than 2 laps)"
        else:
            return "Race completed normally"
