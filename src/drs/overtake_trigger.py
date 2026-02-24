"""
Time-Interval Based Overtake Trigger System.

This module implements a pure probability-based overtake trigger system
without a fixed overtake limit. Overtakes occur based on:
- Time intervals (0.2s resolution matching simulation)
- Track characteristics
- Gap proximity
- Race situation
- DRS availability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import random


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class TimeIntervalConfig:
    """
    Configuration for time-interval based overtakes.

    All probabilities are per 0.2 second interval (matching simulation resolution).

    Base probabilities calibrated for realistic race outcomes:
    - Monza: ~50-60 overtakes per race
    - Silverstone: ~20-30 overtakes per race
    - Monaco: ~0-2 overtakes per race
    """

    interval_seconds: float = 0.2  # Match simulation resolution
    base_probability: float = 0.0008  # ~0.08% per interval (calibrated for 20-30/race)

    # Modifiers
    start_race_bonus: float = 1.5  # First 3 laps
    late_race_bonus: float = 1.3  # Final 10% of race
    pit_window_bonus: float = 1.2  # During pit stops
    drs_zone_bonus: float = 2.0  # In DRS zone
    consecutive_penalty: float = 0.15  # Strong penalty after consecutive overtakes
    max_consecutive: int = 2  # Max before strong penalty


# Track-specific configurations
TRACK_CONFIGS = {
    "Monza": TimeIntervalConfig(
        base_probability=0.0003,  # ~0.03% per interval (~50/race with realistic conditions)
        start_race_bonus=1.8,
        late_race_bonus=1.5,
        drs_zone_bonus=2.5,
        consecutive_penalty=0.2,
        max_consecutive=2,
    ),
    "Monaco": TimeIntervalConfig(
        base_probability=0.00002,  # Very low base (~0.4/race)
        start_race_bonus=1.0,  # No bonus
        late_race_bonus=1.0,
        drs_zone_bonus=1.0,
        pit_window_bonus=1.0,
        consecutive_penalty=0.1,
        max_consecutive=1,
    ),
    "Silverstone": TimeIntervalConfig(
        base_probability=0.0012,  # ~0.12% per interval (~26/race)
        start_race_bonus=1.5,
        late_race_bonus=1.3,
        drs_zone_bonus=2.0,
        pit_window_bonus=1.2,
        consecutive_penalty=0.18,
        max_consecutive=2,
    ),
    "default": TimeIntervalConfig(
        base_probability=0.0010,  # Default track
        start_race_bonus=1.5,
        late_race_bonus=1.3,
        drs_zone_bonus=2.0,
        consecutive_penalty=0.2,
        max_consecutive=2,
    ),
}


# Section type constants
SECTION_DRS_ZONE = "drs_zone"
SECTION_STRAIGHT = "straight"
SECTION_CORNER_ENTRY = "corner_entry"
SECTION_CORNER_EXIT = "corner_exit"
SECTION_S_CURVE = "s_curve"
SECTION_HAIRPIN = "hairpin"
SECTION_TECH_SECTION = "tech_section"


# Section modifiers (adjusted for realistic outcomes)
SECTION_MODIFIERS = {
    SECTION_DRS_ZONE: 1.8,
    SECTION_STRAIGHT: 1.3,
    SECTION_CORNER_ENTRY: 1.1,
    SECTION_CORNER_EXIT: 0.9,
    SECTION_S_CURVE: 1.15,
    SECTION_HAIRPIN: 0.4,
    SECTION_TECH_SECTION: 0.5,
}


# Gap modifiers
def get_gap_modifier(gap_ahead: float) -> float:
    """Get modifier based on gap to car ahead"""
    if gap_ahead <= 0.3:
        return 2.5  # Very close!
    elif gap_ahead <= 0.5:
        return 1.8  # Close
    elif gap_ahead <= 1.0:
        return 1.0  # Within DRS range
    elif gap_ahead <= 2.0:
        return 0.4  # Hard to catch
    else:
        return 0.05  # Not catching


# ============================================================================
# Main Trigger System
# ============================================================================


class TimeIntervalOvertakeSystem:
    """
    Time-interval based overtake probability system.

    Key principles:
    1. No fixed overtake limit
    2. Probability per time interval (0.2s)
    3. Dynamic modifiers based on race situation
    4. Clustering prevention (reduce probability after consecutive overtakes)
    """

    def __init__(
        self, track_name: str = "default", config: Optional[TimeIntervalConfig] = None
    ):
        """
        Initialize the trigger system.

        Args:
            track_name: Name of the track (for track-specific config)
            config: Optional custom configuration
        """
        if config is None:
            config = TRACK_CONFIGS.get(track_name, TRACK_CONFIGS["default"])

        self.config = config
        self.track_name = track_name

        # Tracking
        self.consecutive_overtakes = 0
        self.last_overtake_time = 0.0
        self.rolling_window_overtakes: List[
            Tuple[float, int]
        ] = []  # [(timestamp, count), ...]
        self.total_overtakes = 0
        self.overtake_log: List[Dict] = []

    def get_overtake_probability(
        self,
        current_time: float,
        lap: int,
        total_laps: int,
        in_drs_zone: bool,
        gap_ahead: float,
        section_type: str = SECTION_STRAIGHT,
        drivers_in_range: int = 1,
    ) -> float:
        """
        Calculate overtake probability for current interval.

        Returns probability (0.0 to 1.0) for this 0.2s interval.

        Args:
            current_time: Current race time in seconds
            lap: Current lap number
            total_laps: Total race laps
            in_drs_zone: Whether in DRS zone
            gap_ahead: Gap to car ahead in seconds
            section_type: Type of track section
            drivers_in_range: Number of drivers within 1 second

        Returns:
            Probability of overtake occurring (0.0 to 1.0)
        """
        # Start with base probability
        prob = self.config.base_probability

        # Apply modifiers
        prob *= self._get_lap_modifier(lap, total_laps)
        prob *= self._get_drs_modifier(in_drs_zone)
        prob *= get_gap_modifier(gap_ahead)
        prob *= self._get_section_modifier(section_type)
        prob *= self._get_consecutive_penalty(current_time)
        prob *= self._get_density_modifier(drivers_in_range)

        return min(1.0, max(0.0, prob))

    def should_overtake(
        self,
        current_time: float,
        lap: int,
        total_laps: int,
        in_drs_zone: bool,
        gap_ahead: float,
        section_type: str = SECTION_STRAIGHT,
        drivers_in_range: int = 1,
        attacker_name: str = "Unknown",
        defender_name: str = "Unknown",
        sector_flag_manager=None,
        current_sector: int = 1,
        safety_response_manager=None,
        blue_flag_manager=None,
    ) -> Tuple[bool, str, Dict]:
        """
        Determine if an overtake should occur.

        Args:
            Same as get_overtake_probability plus driver names for logging
            sector_flag_manager: Optional SectorFlagManager to check for yellow flags
            current_sector: Current sector number (1-3)
            safety_response_manager: Optional SafetyResponseManager (VSC/SC)
            blue_flag_manager: Optional BlueFlagManager to check for lapping situations

        Returns:
            Tuple of (should_overtake, reason, debug_info)
        """
        # Check for lapping situation (blue flags)
        if blue_flag_manager is not None:
            is_lapping = blue_flag_manager.is_lapping_situation(
                attacker_name, defender_name
            )
            if is_lapping:
                debug_info = {
                    "is_lapping_situation": True,
                    "attacker": attacker_name,
                    "defender": defender_name,
                }
                return (
                    True,
                    f"Lapping situation - {attacker_name} lapping {defender_name}",
                    debug_info,
                )

        # Check for VSC/SC - no overtaking under VSC or SC
        if safety_response_manager is not None and safety_response_manager.is_active:
            response_type = safety_response_manager.current_response.value
            debug_info = {
                "blocked_by_safety_car": True,
                "response_type": response_type,
            }
            return False, f"Overtake blocked - {response_type} active", debug_info

        # Check for yellow flags - no overtaking under yellow
        if sector_flag_manager is not None:
            if not sector_flag_manager.can_overtake(current_sector):
                flag_state = sector_flag_manager.get_flag_state(current_sector)
                debug_info = {
                    "blocked_by_flag": True,
                    "flag_state": flag_state.value,
                    "sector": current_sector,
                }
                return (
                    False,
                    f"Overtake blocked - {flag_state.value} flag in sector {current_sector}",
                    debug_info,
                )

        prob = self.get_overtake_probability(
            current_time,
            lap,
            total_laps,
            in_drs_zone,
            gap_ahead,
            section_type,
            drivers_in_range,
        )

        # Build debug info
        debug_info = {
            "base_prob": self.config.base_probability,
            "lap_mod": self._get_lap_modifier(lap, total_laps),
            "drs_mod": self._get_drs_modifier(in_drs_zone),
            "gap_mod": get_gap_modifier(gap_ahead),
            "section_mod": self._get_section_modifier(section_type),
            "consecutive_mod": self._get_consecutive_penalty(current_time),
            "density_mod": self._get_density_modifier(drivers_in_range),
            "final_prob": prob,
            "sector": current_sector,
        }

        if random.random() < prob:
            reason = self._get_probability_explanation(
                lap, total_laps, in_drs_zone, gap_ahead, section_type
            )
            return True, reason, debug_info
        else:
            reason = f"Probability {prob:.4f} did not trigger"
            return False, reason, debug_info

    def check_sector_flag(
        self,
        sector_flag_manager,
        current_sector: int,
    ) -> Tuple[bool, str]:
        """
        Check if overtaking is allowed in current sector.

        Args:
            sector_flag_manager: SectorFlagManager instance
            current_sector: Current sector number

        Returns:
            Tuple of (can_overtake, reason)
        """
        if sector_flag_manager is None:
            return True, "No flag manager"

        if sector_flag_manager.can_overtake(current_sector):
            return True, "Green flag"
        else:
            flag_state = sector_flag_manager.get_flag_state(current_sector)
            return False, f"{flag_state.value} flag in sector {current_sector}"

    def record_overtake(
        self,
        current_time: float,
        attacker_name: str = "Unknown",
        defender_name: str = "Unknown",
        reason: str = "unknown",
    ):
        """Record an overtake occurrence"""
        self.consecutive_overtakes += 1
        self.last_overtake_time = current_time
        self.total_overtakes += 1

        # Add to rolling window
        self.rolling_window_overtakes.append((current_time, 1))

        # Clean old entries (keep last 30 seconds)
        cutoff = current_time - 30.0
        self.rolling_window_overtakes = [
            (t, c) for t, c in self.rolling_window_overtakes if t > cutoff
        ]

        # Log the overtake
        self.overtake_log.append(
            {
                "time": current_time,
                "lap": None,  # Will be filled by caller
                "attacker": attacker_name,
                "defender": defender_name,
                "reason": reason,
            }
        )

    def get_statistics(self) -> Dict:
        """Get system statistics"""
        return {
            "total_overtakes": self.total_overtakes,
            "consecutive_overtakes": self.consecutive_overtakes,
            "track_name": self.track_name,
            "recent_activity": len(
                [
                    t
                    for t, _ in self.rolling_window_overtakes
                    if t > self.last_overtake_time - 5.0
                ]
            ),
        }

    # =========================================================================
    # Modifier Functions
    # =========================================================================

    def _get_lap_modifier(self, lap: int, total_laps: float) -> float:
        """Get modifier based on race progress"""
        progress = lap / total_laps

        if lap <= 3:
            return self.config.start_race_bonus
        elif progress >= 0.9:  # Final 10%
            return self.config.late_race_bonus
        elif 0.35 <= progress <= 0.5:  # Pit window
            return self.config.pit_window_bonus
        else:
            return 1.0

    def _get_drs_modifier(self, in_drs_zone: bool) -> float:
        """Get modifier based on DRS availability"""
        if in_drs_zone:
            return self.config.drs_zone_bonus
        return 1.0

    def _get_section_modifier(self, section_type: str) -> float:
        """Get modifier based on track section"""
        return SECTION_MODIFIERS.get(section_type, 1.0)

    def _get_consecutive_penalty(self, current_time: float) -> float:
        """Reduce probability after consecutive overtakes"""
        # Check rolling window (last 10 seconds for stronger prevention)
        recent = [
            c for t, c in self.rolling_window_overtakes if current_time - t < 10.0
        ]
        recent_count = sum(recent)

        if recent_count >= 1:
            # Exponential decay for clustering prevention
            return self.config.consecutive_penalty**recent_count
        return 1.0

    def _get_density_modifier(self, drivers_in_range: int) -> float:
        """More cars in range = more opportunities"""
        if drivers_in_range >= 4:
            return 2.0  # Train situation
        elif drivers_in_range >= 2:
            return 1.3  # Multiple battles
        return 1.0

    def _get_probability_explanation(
        self,
        lap: int,
        total_laps: int,
        in_drs_zone: bool,
        gap_ahead: float,
        section_type: str,
    ) -> str:
        """Generate explanation for probability trigger"""
        reasons = []

        if lap <= 3:
            reasons.append("start_race")
        elif lap / total_laps >= 0.9:
            reasons.append("late_race")
        elif 0.35 <= lap / total_laps <= 0.5:
            reasons.append("pit_window")

        if in_drs_zone:
            reasons.append("drs_zone")

        if gap_ahead <= 0.3:
            reasons.append("very_close")
        elif gap_ahead <= 0.5:
            reasons.append("close")

        reasons.append(section_type)

        return "_".join(reasons)

    def reset(self):
        """Reset the system for a new race"""
        self.consecutive_overtakes = 0
        self.last_overtake_time = 0.0
        self.rolling_window_overtakes = []
        self.total_overtakes = 0
        self.overtake_log = []


# ============================================================================
# Helper Functions
# ============================================================================


def create_trigger_system(track_name: str) -> TimeIntervalOvertakeSystem:
    """Create a trigger system for a specific track"""
    return TimeIntervalOvertakeSystem(track_name)


def get_track_config(track_name: str) -> TimeIntervalConfig:
    """Get configuration for a specific track"""
    return TRACK_CONFIGS.get(track_name, TRACK_CONFIGS["default"])
