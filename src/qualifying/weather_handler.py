"""
Qualifying Weather Handler

Handles weather conditions during qualifying sessions.
Integrates with existing weather system.
"""

from typing import Optional
from src.qualifying.types import QualifyingWeatherState


class QualifyingWeatherHandler:
    """Handles weather conditions during qualifying."""

    def __init__(self, track_name: str = ""):
        """
        Initialize weather handler.

        Args:
            track_name: Name of the track
        """
        self.track_name = track_name
        self.current_state = QualifyingWeatherState()
        self.weather_log: list = []

    def update_conditions(
        self,
        track_condition: str = "dry",
        rain_intensity: float = 0.0,
        track_temperature: float = 25.0,
        air_temperature: float = 22.0,
    ) -> QualifyingWeatherState:
        """
        Update weather conditions.

        Args:
            track_condition: Track condition (dry, damp, wet)
            rain_intensity: Rain intensity (0.0 - 1.0)
            track_temperature: Track temperature in Celsius
            air_temperature: Air temperature in Celsius

        Returns:
            Updated weather state
        """
        self.current_state = QualifyingWeatherState(
            track_condition=track_condition,
            rain_intensity=rain_intensity,
            track_temperature=track_temperature,
            air_temperature=air_temperature,
            drs_enabled=self._check_drs_availability(track_condition),
        )

        # Log the change
        self.weather_log.append(
            {
                "track_condition": track_condition,
                "rain_intensity": rain_intensity,
                "drs_enabled": self.current_state.drs_enabled,
            }
        )

        return self.current_state

    def _check_drs_availability(self, track_condition: str) -> bool:
        """
        Check if DRS is available.

        DRS is disabled if track is declared wet.
        """
        return track_condition not in ["wet", "damp"]

    def get_recommended_tyres(self) -> str:
        """
        Get recommended tyre compound for current conditions.

        Returns:
            Recommended tyre (DRY, INTER, WET)
        """
        if self.current_state.track_condition == "wet":
            return "WET"
        elif self.current_state.track_condition in ["damp", "mixed"]:
            return "INTER"
        else:
            return "DRY"

    def is_dry_condition(self) -> bool:
        """Check if conditions are dry."""
        return self.current_state.track_condition == "dry"

    def should_red_flag(self) -> bool:
        """
        Determine if conditions warrant a red flag.

        Returns:
            True if session should be red flagged
        """
        # Red flag for very heavy rain
        if self.current_state.rain_intensity > 0.8:
            return True

        # Red flag for flooded track
        if self.current_state.track_condition == "flooded":
            return True

        return False

    def get_weather_impact_on_lap_time(self) -> float:
        """
        Calculate weather impact on lap time.

        Returns:
            Time penalty in seconds
        """
        condition_penalties = {
            "dry": 0.0,
            "damp": 2.0,
            "wet": 5.0,
            "flooded": 10.0,
        }

        base_penalty = condition_penalties.get(self.current_state.track_condition, 0.0)

        # Additional penalty for rain intensity
        rain_penalty = self.current_state.rain_intensity * 3.0

        return base_penalty + rain_penalty

    def get_session_summary(self) -> dict:
        """Get weather summary for the session."""
        return {
            "track_name": self.track_name,
            "final_condition": self.current_state.track_condition,
            "max_rain_intensity": max(
                (w["rain_intensity"] for w in self.weather_log), default=0.0
            ),
            "drs_disabled_periods": sum(
                1 for w in self.weather_log if not w["drs_enabled"]
            ),
            "weather_changes": len(self.weather_log) - 1 if self.weather_log else 0,
        }
