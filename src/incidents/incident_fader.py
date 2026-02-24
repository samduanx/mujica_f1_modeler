"""
Incident Frequency Fader System.

Data-driven system to fade incident probability over the race.
Prevents excessive incidents ("crashfests") while maintaining realism.

Based on FastF1 calibration data from real F1 races.
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Target incident counts based on FastF1 calibration (dry conditions only)
# See calibrate_with_fastf1.py for source data
TARGET_INCIDENTS_NORMAL = {
    "total_incidents": 4,
    "yellow_flags": 2.5,
    "double_yellows": 1.2,
    "vsc_periods": 0.4,
    "sc_periods": 1.0,
    "red_flags": 0.15,
}

TARGET_INCIDENTS_CHAOS = {
    "total_incidents": 15,
    "yellow_flags": 5.6,
    "double_yellows": 3.6,
    "vsc_periods": 1.1,
    "sc_periods": 5.3,
    "red_flags": 1.4,
}


@dataclass
class FadingConfig:
    """Configuration for incident frequency fading"""

    # Fade rates per excess incident (percentage)
    yellow_fade_rate: float = 0.10  # 10% fade per excess
    double_yellow_fade_rate: float = 0.20  # 20% fade per excess
    vsc_fade_rate: float = 0.30  # 30% fade per excess
    sc_fade_rate: float = 0.40  # 40% fade per excess
    red_flag_fade_rate: float = 1.0  # 100% (max 1 per race)

    # Catch-up boost when far behind target
    catch_up_threshold: float = 0.5  # Below 50% of expected = boost
    catch_up_boost: float = 1.2  # 20% boost when behind


class IncidentFrequencyFader:
    """
    Data-driven system to fade incident frequency over race.

    Prevents "crashfests" by:
    1. Tracking incident counts vs FastF1-calibrated targets
    2. Reducing probability when ahead of target
    3. Slightly increasing when behind target
    4. Supporting chaos mode for wet/incident-heavy races
    """

    def __init__(
        self,
        race_type: str = "normal",
        config: Optional[FadingConfig] = None,
        total_laps: int = 70,
    ):
        """
        Initialize fader.

        Args:
            race_type: "normal" or "chaos"
            config: Optional custom fading configuration
            total_laps: Total race distance in laps
        """
        self.config = config or FadingConfig()
        self.total_laps = total_laps

        # Set targets based on race type
        self.targets = (
            TARGET_INCIDENTS_CHAOS if race_type == "chaos" else TARGET_INCIDENTS_NORMAL
        )
        self.race_type = race_type

        # Track incident counts
        self.incident_counts: Dict[str, int] = defaultdict(int)

        # Track fade history for debugging
        self.fade_history: List[Dict] = []

    def calculate_fade_factor(
        self,
        incident_type: str,
        laps_completed: int,
    ) -> float:
        """
        Calculate probability fade factor.

        Args:
            incident_type: Type of incident ("yellow", "vsc", etc.)
            laps_completed: Current lap number

        Returns:
            Multiplier (0.0 - 1.0+) for incident probability
        """
        target = self.targets.get(incident_type, 5)
        current_count = self.incident_counts.get(incident_type, 0)

        # Progress through race (0.0 to 1.0)
        race_progress = laps_completed / self.total_laps
        if race_progress <= 0:
            race_progress = 0.01  # Avoid division by zero

        # Calculate how many incidents we "should" have had by now
        expected_by_now = target * race_progress

        # Get fade rate for this incident type
        fade_rate = self._get_fade_rate(incident_type)

        # Calculate fade factor
        if current_count > expected_by_now:
            # We're ahead of target - fade probability
            excess = current_count - expected_by_now
            fade = max(0.1, 1.0 - (excess * fade_rate))

            self.fade_history.append(
                {
                    "lap": laps_completed,
                    "type": incident_type,
                    "current": current_count,
                    "expected": expected_by_now,
                    "excess": excess,
                    "fade_rate": fade_rate,
                    "fade_factor": fade,
                    "action": "fade",
                }
            )

            return fade

        elif current_count < expected_by_now * self.config.catch_up_threshold:
            # We're behind target - boost probability
            boost = self.config.catch_up_boost

            self.fade_history.append(
                {
                    "lap": laps_completed,
                    "type": incident_type,
                    "current": current_count,
                    "expected": expected_by_now,
                    "boost": boost,
                    "action": "boost",
                }
            )

            return boost

        # Normal range - no change
        return 1.0

    def _get_fade_rate(self, incident_type: str) -> float:
        """Get fade rate for incident type"""
        rates = {
            "yellow": self.config.yellow_fade_rate,
            "double_yellow": self.config.double_yellow_fade_rate,
            "vsc": self.config.vsc_fade_rate,
            "sc": self.config.sc_fade_rate,
            "red_flag": self.config.red_flag_fade_rate,
            # Aliases
            "yellow_flags": self.config.yellow_fade_rate,
            "vsc_periods": self.config.vsc_fade_rate,
            "sc_periods": self.config.sc_fade_rate,
            "red_flags": self.config.red_flag_fade_rate,
        }
        return rates.get(incident_type, 0.2)

    def apply_fading_to_roll(
        self,
        base_roll: int,
        incident_type: str,
        laps_completed: int,
    ) -> int:
        """
        Apply fading to a dice roll.

        Args:
            base_roll: Original dice roll (1-100)
            incident_type: Type of incident
            laps_completed: Current lap number

        Returns:
            Adjusted roll (higher = less likely to trigger)
        """
        fade_factor = self.calculate_fade_factor(incident_type, laps_completed)

        # Adjust roll based on fade factor
        if fade_factor < 1.0:
            # Fading - reduce chance (increase effective threshold)
            adjusted_roll = int(base_roll / fade_factor)
        elif fade_factor > 1.0:
            # Boosting - increase chance (decrease effective threshold)
            adjusted_roll = int(base_roll * fade_factor)
        else:
            adjusted_roll = base_roll

        return min(100, max(1, adjusted_roll))

    def record_incident(self, incident_type: str):
        """Record an incident occurrence"""
        self.incident_counts[incident_type] += 1

        # Also record aliases
        aliases = {
            "yellow": "yellow_flags",
            "double_yellow": "double_yellows",
            "vsc": "vsc_periods",
            "sc": "sc_periods",
            "red_flag": "red_flags",
        }
        if incident_type in aliases:
            self.incident_counts[aliases[incident_type]] += 1

    def get_current_counts(self) -> Dict[str, int]:
        """Get current incident counts"""
        return dict(self.incident_counts)

    def get_expected_counts(self, laps_completed: int) -> Dict[str, float]:
        """Get expected incident counts at current lap"""
        race_progress = laps_completed / self.total_laps
        return {key: value * race_progress for key, value in self.targets.items()}

    def get_fade_summary(self) -> Dict:
        """Get summary of fading behavior"""
        return {
            "race_type": self.race_type,
            "targets": self.targets,
            "current_counts": dict(self.incident_counts),
            "fade_history_length": len(self.fade_history),
        }

    def reset(self):
        """Reset fader for new race"""
        self.incident_counts.clear()
        self.fade_history.clear()


class ChaosModeController:
    """
    Controller for race chaos level.

    Allows dynamic adjustment of incident targets based on:
    - Track conditions
    - Historical data
    - User preferences
    """

    CHAOS_LEVELS = {
        0: 1.0,  # Normal
        1: 1.5,  # Slightly chaotic
        2: 2.5,  # Very chaotic
        3: 4.0,  # Maximum chaos
    }

    def __init__(self, base_fader: IncidentFrequencyFader):
        self.base_fader = base_fader
        self.chaos_level = 0

    def set_chaos_level(self, level: int):
        """Set chaos level (0-3)"""
        if level not in self.CHAOS_LEVELS:
            level = 0

        self.chaos_level = level
        multiplier = self.CHAOS_LEVELS[level]

        # Update targets
        for key in self.base_fader.targets:
            if self.chaos_level == 0:
                # Reset to normal
                self.base_fader.targets[key] = TARGET_INCIDENTS_NORMAL.get(
                    key, self.base_fader.targets[key]
                )
            else:
                # Apply multiplier
                self.base_fader.targets[key] = (
                    TARGET_INCIDENTS_NORMAL.get(key, 5) * multiplier
                )

    def get_chaos_description(self) -> str:
        """Get human-readable chaos level description"""
        descriptions = {
            0: "Normal race conditions",
            1: "Slightly chaotic - elevated incident rate",
            2: "Very chaotic - frequent safety car periods",
            3: "Maximum chaos - crashfest mode",
        }
        return descriptions.get(self.chaos_level, "Unknown")


# Default instances
default_fader = IncidentFrequencyFader(race_type="normal")
