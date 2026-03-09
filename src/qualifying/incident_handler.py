"""
Qualifying Incident Handler

Handles incidents during qualifying sessions using dice rolling.
Integrates with existing incident system to generate flags.
"""

import random
from typing import Optional, List
from src.qualifying.types import QualifyingIncident, FlagState


def roll_d100() -> int:
    """Roll a 100-sided die."""
    return random.randint(1, 100)


class QualifyingIncidentHandler:
    """Handles incidents during qualifying sessions."""

    # Incident probability thresholds (based on 1d100 roll)
    # Lower rolls = more severe incidents
    INCIDENT_THRESHOLDS = {
        "crash": 1,  # Roll <= 1: Crash (Red flag)
        "spin": 3,  # Roll <= 3: Spin/Off (Yellow flag)
        "off_track": 8,  # Roll <= 8: Off track excursion (Yellow)
        "track_limits": 15,  # Roll <= 15: Track limits violation (Lap deleted)
    }

    def __init__(self):
        self.incidents: List[QualifyingIncident] = []
        self.active_flags: List[str] = []  # Track active flags

    def roll_for_incident(
        self,
        driver: str,
        driver_dr: float,
        track_condition: str = "dry",
        pressure_level: float = 0.0,
        lap_phase: str = "flying",
    ) -> Optional[QualifyingIncident]:
        """
        Roll for potential incident during a lap.

        Args:
            driver: Driver name
            driver_dr: Driver DR value (affects probability)
            track_condition: Track condition (dry, damp, wet)
            pressure_level: Pressure level (0.0 - 1.0)
            lap_phase: Phase of lap (out, flying, in)

        Returns:
            QualifyingIncident if incident occurred, None otherwise
        """
        # Base roll
        base_roll = roll_d100()

        # Calculate modifiers
        dr_modifier = (driver_dr - 80) / 5  # -4 to +4

        # Track condition modifier
        condition_modifiers = {
            "dry": 0,
            "damp": 3,
            "wet": 8,
        }
        condition_modifier = condition_modifiers.get(track_condition, 0)

        # Pressure modifier
        pressure_modifier = pressure_level * 5

        # Lap phase modifier (flying lap is highest risk)
        phase_modifiers = {
            "out": -2,
            "flying": 0,
            "in": -1,
        }
        phase_modifier = phase_modifiers.get(lap_phase, 0)

        # Calculate final roll (lower = worse incident)
        final_roll = max(
            1,
            min(
                100,
                base_roll
                + dr_modifier
                + condition_modifier
                + pressure_modifier
                + phase_modifier,
            ),
        )

        # Check for incidents
        if final_roll <= self.INCIDENT_THRESHOLDS["crash"]:
            return self._create_crash_incident(driver)
        elif final_roll <= self.INCIDENT_THRESHOLDS["spin"]:
            return self._create_spin_incident(driver)
        elif final_roll <= self.INCIDENT_THRESHOLDS["off_track"]:
            return self._create_off_track_incident(driver)
        elif final_roll <= self.INCIDENT_THRESHOLDS["track_limits"]:
            return self._create_track_limits_incident(driver)

        return None

    def _create_crash_incident(self, driver: str) -> QualifyingIncident:
        """Create a crash incident (Red flag)."""
        return QualifyingIncident(
            driver=driver,
            incident_type="crash",
            severity="critical",
            sector=random.randint(1, 3),
            time_lost=999.0,  # Session stopping
            flag_triggered="red",
            lap_deleted=True,
        )

    def _create_spin_incident(self, driver: str) -> QualifyingIncident:
        """Create a spin/off incident (Yellow flag)."""
        return QualifyingIncident(
            driver=driver,
            incident_type="spin",
            severity="major",
            sector=random.randint(1, 3),
            time_lost=random.uniform(2.0, 5.0),
            flag_triggered="yellow",
            lap_deleted=True,
        )

    def _create_off_track_incident(self, driver: str) -> QualifyingIncident:
        """Create an off-track excursion (Yellow flag)."""
        return QualifyingIncident(
            driver=driver,
            incident_type="off_track",
            severity="minor",
            sector=random.randint(1, 3),
            time_lost=random.uniform(0.5, 2.0),
            flag_triggered="yellow",
            lap_deleted=False,
        )

    def _create_track_limits_incident(self, driver: str) -> QualifyingIncident:
        """Create a track limits violation (Lap deleted)."""
        return QualifyingIncident(
            driver=driver,
            incident_type="track_limits",
            severity="minor",
            sector=random.randint(1, 3),
            time_lost=0.0,
            flag_triggered=None,
            lap_deleted=True,
        )

    def record_incident(self, incident: QualifyingIncident) -> None:
        """Record an incident."""
        self.incidents.append(incident)

    def get_incidents_for_session(self, session_name: str) -> List[QualifyingIncident]:
        """Get all incidents for a session."""
        return [inc for inc in self.incidents]

    def get_red_flag_count(self) -> int:
        """Get number of red flags."""
        return sum(1 for inc in self.incidents if inc.flag_triggered == "red")

    def get_yellow_flag_count(self) -> int:
        """Get number of yellow flags."""
        return sum(1 for inc in self.incidents if inc.flag_triggered == "yellow")

    def get_lap_deletions(self) -> List[str]:
        """Get list of drivers who had laps deleted."""
        return [inc.driver for inc in self.incidents if inc.lap_deleted]
