"""
Rolling Start System for F1 Simulator.

Implements rolling start procedures according to F1 Sporting Regulations:
- Formation lap(s) behind Safety Car count as race laps
- SC lights out signals impending restart
- Green flag at control line resumes racing
- Supports red flag rolling restarts

Based on Section 17 of INCIDENT_RESPONSE_PLAN.md
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RollingStartPhase(Enum):
    """Phases of a rolling start"""

    NOT_STARTED = "not_started"
    FORMATION = "formation"  # Behind SC, lights on
    SC_LIGHTS_OUT = "sc_lights_out"  # SC lights out, leader controls pace
    RACE_STARTED = "race_started"  # Green flag, racing
    FINISHED = "finished"


@dataclass
class RollingStartConfig:
    """Configuration for rolling start behavior"""

    # Probability of rolling start (non-weather)
    rolling_start_probability: float = 0.15  # 15% for red flag restarts

    # Formation lap behavior
    min_formation_laps: int = 1
    max_formation_laps: int = 3

    # SC lights out position (as fraction of lap)
    sc_lights_out_position: float = 0.85  # 85% through lap (pit entry)

    # Control line position (start/finish line)
    control_line_position: float = 0.0  # Start of lap

    # Time factor under SC (formation lap)
    formation_lap_time_factor: float = 0.60  # Same as SC


@dataclass
class RollingStartManager:
    """
    Manage rolling start procedures and lap counting.

    Critical: ALL laps behind SC count as race laps.
    """

    total_race_laps: int
    config: RollingStartConfig = field(default_factory=RollingStartConfig)

    # State
    phase: RollingStartPhase = RollingStartPhase.NOT_STARTED
    is_rolling_start: bool = False

    # Lap tracking
    completed_laps: int = 0
    formation_laps_completed: int = 0
    racing_laps_completed: int = 0

    # Timing
    current_lap_distance: float = 0.0  # 0.0 to 1.0

    # SC state
    sc_lights_on: bool = False
    sc_lights_out_lap: Optional[int] = None
    sc_entered_pits: bool = False

    # Race state
    green_flag_shown: bool = False
    race_start_time: Optional[float] = None

    def initiate_rolling_start(
        self,
        reason: str,
        current_lap: int = 0,
    ) -> Dict:
        """
        Initiate rolling start procedure.

        Args:
            reason: Why rolling start is being used
            current_lap: Current lap number (0 for race start)

        Returns:
            Dict with start information
        """
        self.is_rolling_start = True
        self.phase = RollingStartPhase.FORMATION
        self.sc_lights_on = True
        self.completed_laps = current_lap

        return {
            "rolling_start_initiated": True,
            "reason": reason,
            "phase": self.phase.value,
            "sc_lights": "ON",
            "message": "Rolling start - follow Safety Car",
            "laps_to_count": True,
        }

    def start_formation_lap(self, lap_number: int) -> Dict:
        """
        Begin formation lap behind Safety Car.

        The formation lap IS counted as a race lap.

        Args:
            lap_number: Current lap number

        Returns:
            Dict with formation lap information
        """
        self.phase = RollingStartPhase.FORMATION
        self.formation_laps_completed += 1
        self.completed_laps = lap_number
        self.sc_lights_on = True

        return {
            "phase": "formation",
            "lap": lap_number,
            "formation_lap_number": self.formation_laps_completed,
            "completed_laps": self.completed_laps,
            "remaining_laps": self.total_race_laps - self.completed_laps,
            "sc_lights": "ON",
            "overtaking": "PROHIBITED",
            "lap_counts": True,
        }

    def sc_lights_out(self, lap_number: int, race_time: float) -> Dict:
        """
        Safety Car lights go out - leader controls pace.

        Still behind SC but leader can control pace until control line.

        Args:
            lap_number: Current lap number
            race_time: Current race time

        Returns:
            Dict with lights out information
        """
        self.phase = RollingStartPhase.SC_LIGHTS_OUT
        self.sc_lights_on = False
        self.sc_lights_out_lap = lap_number

        return {
            "phase": "sc_lights_out",
            "lap": lap_number,
            "time": race_time,
            "message": "SC lights out - leader controls pace",
            "overtaking": "PROHIBITED until after control line",
            "sc_entering_pits": True,
        }

    def green_flag(self, lap_number: int, race_time: float) -> Dict:
        """
        Race officially starts - green flags.

        This happens when leader crosses the control line.

        Args:
            lap_number: Current lap number
            race_time: Current race time

        Returns:
            Dict with race start information
        """
        self.phase = RollingStartPhase.RACE_STARTED
        self.green_flag_shown = True
        self.race_start_time = race_time
        self.sc_entered_pits = True

        # Update racing lap count
        self.racing_laps_completed = lap_number - self.formation_laps_completed

        return {
            "phase": "race_started",
            "lap": lap_number,
            "time": race_time,
            "message": "GREEN FLAG - Racing begins",
            "overtaking": "PERMITTED",
            "formation_laps": self.formation_laps_completed,
            "racing_laps": self.racing_laps_completed,
        }

    def update_position(self, lap_distance: float) -> Optional[Dict]:
        """
        Update car position during rolling start.

        Used to trigger events based on track position.

        Args:
            lap_distance: Distance through lap (0.0 to 1.0)

        Returns:
            Event dict if milestone reached, None otherwise
        """
        self.current_lap_distance = lap_distance

        # Check for SC lights out position
        if (
            self.phase == RollingStartPhase.FORMATION
            and self.sc_lights_on
            and lap_distance >= self.config.sc_lights_out_position
        ):
            return {"event": "sc_lights_out_position"}

        # Check for control line (green flag)
        if (
            self.phase == RollingStartPhase.SC_LIGHTS_OUT
            and not self.green_flag_shown
            and lap_distance >= self.config.control_line_position
        ):
            return {"event": "control_line"}

        return None

    def complete_lap(self, lap_number: int) -> Dict:
        """
        Complete a lap during rolling start.

        Args:
            lap_number: Lap that was completed

        Returns:
            Dict with lap completion information
        """
        self.completed_laps = lap_number

        if self.phase == RollingStartPhase.RACE_STARTED:
            self.racing_laps_completed += 1

        return {
            "lap_completed": lap_number,
            "total_completed": self.completed_laps,
            "remaining": self.total_race_laps - self.completed_laps,
            "phase": self.phase.value,
        }

    def can_overtake(self) -> bool:
        """
        Check if overtaking is permitted.

        Rules:
        - Formation lap: NO
        - SC lights out to control line: NO
        - After control line: YES
        """
        if not self.is_rolling_start:
            return True

        return self.phase == RollingStartPhase.RACE_STARTED and self.green_flag_shown

    def get_lap_count_status(self) -> Dict:
        """
        Get current lap counting status.

        Returns:
            Dict with race distance information
        """
        return {
            "total_race_laps": self.total_race_laps,
            "completed_laps": self.completed_laps,
            "remaining_laps": self.total_race_laps - self.completed_laps,
            "formation_laps": self.formation_laps_completed,
            "racing_laps": self.racing_laps_completed,
            "is_rolling_start": self.is_rolling_start,
            "current_phase": self.phase.value,
        }

    def is_race_finished(self) -> bool:
        """Check if race is finished"""
        return self.completed_laps >= self.total_race_laps

    def get_target_lap_time(self) -> float:
        """
        Get target lap time for current phase.

        Returns:
            Time factor relative to normal lap time
        """
        if self.phase in [RollingStartPhase.FORMATION, RollingStartPhase.SC_LIGHTS_OUT]:
            return self.config.formation_lap_time_factor
        return 1.0  # Normal racing


class RollingStartTrigger:
    """
    Determine when rolling start should be used.
    """

    def __init__(self, config: Optional[RollingStartConfig] = None):
        self.config = config or RollingStartConfig()

    def should_use_rolling_start(
        self,
        weather_condition: str = "dry",
        track_visibility: str = "good",
        race_director_decision: Optional[str] = None,
        is_red_flag_restart: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if race should use rolling start.

        Args:
            weather_condition: Current weather
            track_visibility: Visibility level
            race_director_decision: Explicit RD decision
            is_red_flag_restart: Whether this is after red flag

        Returns:
            Tuple of (use_rolling_start, reason)
        """
        # Race director explicit decision
        if race_director_decision == "rolling_start":
            return True, "Race Director decision"

        # Wet conditions
        if weather_condition in ["heavy_rain", "storm"]:
            return True, "Heavy rain conditions"

        # Poor visibility
        if track_visibility in ["poor", "very_poor", "fog"]:
            return True, "Poor visibility"

        # Red flag restart - Race Director may choose rolling start
        if is_red_flag_restart:
            if random.random() < self.config.rolling_start_probability:
                return True, "Red flag - Race Director opted for rolling restart"

        return False, "Conditions suitable for standing start"


@dataclass
class RedFlagRollingRestart:
    """
    Handle red flag restart with rolling start.
    """

    def __init__(self, total_race_laps: int):
        self.rolling_start = RollingStartManager(total_race_laps=total_race_laps)

    def prepare_rolling_restart(
        self,
        grid_positions: Dict[str, int],
        laps_completed_before_rf: int,
    ) -> Dict:
        """
        Prepare rolling restart after red flag.

        Args:
            grid_positions: Final classification positions at red flag
            laps_completed_before_rf: Laps completed before red flag shown

        Returns:
            Restart configuration
        """
        # Set completed laps (they count!)
        self.rolling_start.completed_laps = laps_completed_before_rf

        # Initiate rolling start
        init_info = self.rolling_start.initiate_rolling_start(
            reason="Red flag rolling restart",
            current_lap=laps_completed_before_rf,
        )

        return {
            "restart_type": "rolling",
            "grid": grid_positions,
            "laps_completed": laps_completed_before_rf,
            "laps_remaining": self.rolling_start.total_race_laps
            - laps_completed_before_rf,
            "procedure": "formation_lap_behind_sc",
            **init_info,
        }

    def execute_formation_lap(self, lap_number: int) -> Dict:
        """Execute formation lap"""
        return self.rolling_start.start_formation_lap(lap_number)

    def signal_sc_lights_out(self, lap_number: int, race_time: float) -> Dict:
        """Signal SC lights out"""
        return self.rolling_start.sc_lights_out(lap_number, race_time)

    def signal_green_flag(self, lap_number: int, race_time: float) -> Dict:
        """Signal green flag - race resumes"""
        return self.rolling_start.green_flag(lap_number, race_time)


class RollingStartOvertakingRules:
    """
    Enforce overtaking rules during rolling start.
    """

    def __init__(self, rolling_start_manager: RollingStartManager):
        self.rs_manager = rolling_start_manager

    def check_overtake_legal(
        self,
        attacker_position: str,  # "leader", "chaser", "lapped"
        has_crossed_control_line: bool,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if overtake is legal.

        Returns:
            Tuple of (is_legal, penalty_info)
        """
        if not self.rs_manager.is_rolling_start:
            return True, None

        # Check phase
        if self.rs_manager.phase == RollingStartPhase.RACE_STARTED:
            if has_crossed_control_line:
                return True, None
            else:
                # Before control line - illegal
                return False, self._get_penalty()

        # Formation or SC lights out phase - always illegal
        return False, self._get_penalty()

    def _get_penalty(self) -> Dict:
        """Get penalty for illegal overtake"""
        return {
            "penalty_type": "time",
            "penalty_seconds": 5,
            "reason": "Illegal overtake during rolling start procedure",
        }


# Default configuration for normal dry conditions
DEFAULT_ROLLING_START_CONFIG = RollingStartConfig()
