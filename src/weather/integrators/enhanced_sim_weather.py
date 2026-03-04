"""
Enhanced Simulation Weather Integration.

Integrates the weather system with the enhanced race simulation
(enhanced_long_dist_sim.py).

This integration provides:
- Weather initialization for races
- Weather events during the race
- Weather impact on lap times
- Race control responses (VSC, SC, Red Flag triggers)
- Track condition effects on tyre selection
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import sys
import os

# Ensure proper import path - go up to project root
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Add src directory to path for weather module imports
src_path = os.path.join(_project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from weather import (
    WeatherGenerator,
    WeatherState,
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    WeatherEvent,
    get_track_info,
)


# Weather impact on lap times (percentage increase)
WEATHER_LAP_TIME_IMPACT = {
    WeatherType.CLEAR: 0.0,
    WeatherType.PARTLY_CLOUDY: 0.0,
    WeatherType.CLOUDY: 0.02,
    WeatherType.OVERCAST: 0.03,
    WeatherType.LIGHT_RAIN: 0.08,
    WeatherType.MODERATE_RAIN: 0.12,
    WeatherType.HEAVY_RAIN: 0.18,
    WeatherType.TORRENTIAL_RAIN: 0.25,
    WeatherType.THUNDERSTORM: 0.30,
}

# Track condition impact on lap times
TRACK_CONDITION_IMPACT = {
    TrackCondition.DRY: 0.0,
    TrackCondition.DAMP: 0.05,
    TrackCondition.WET: 0.10,
    TrackCondition.FLOODED: 0.20,
}

# Rain intensity impact on visibility (factor)
VISIBILITY_IMPACT = {
    RainIntensity.NONE: 1.0,
    RainIntensity.LIGHT: 0.8,
    RainIntensity.MODERATE: 0.5,
    RainIntensity.HEAVY: 0.3,
    RainIntensity.TORRENTIAL: 0.15,
}


@dataclass
class WeatherLapData:
    """Weather data for a specific lap."""

    lap: int
    race_time: float  # minutes into race
    weather: WeatherState
    lap_time_modifier: float  # percentage
    recommended_tyre: str  # 'dry', 'intermediate', 'wet'


@dataclass
class RaceWeatherLog:
    """Complete weather log for a race."""

    gp_name: str
    initial_weather: WeatherState
    weather_events: List[WeatherEvent]
    lap_data: List[WeatherLapData] = field(default_factory=list)

    def add_lap_data(self, lap_data: WeatherLapData):
        self.lap_data.append(lap_data)

    def get_wet_laps(self) -> int:
        """Get number of laps run in wet conditions."""
        return sum(1 for ld in self.lap_data if ld.recommended_tyre != "dry")

    def get_rain_events(self) -> int:
        """Get number of rain-related events."""
        return sum(1 for e in self.weather_events if "rain" in e.event_type)


class SimWeatherIntegration:
    """
    Integrates weather system with enhanced race simulation.

    This class provides the interface between the weather generator
    and the race simulation, handling:
    - Initial weather setup
    - Weather event triggering
    - Lap time calculations
    - Race control responses

    Usage:
        weather_integration = SimWeatherIntegration("Monaco", seed=42)

        # Initialize race weather
        weather_integration.initialize_race()

        # Get current weather for a lap
        current_weather = weather_integration.get_current_weather(lap=1, race_time=1.5)

        # Calculate lap time impact
        lap_modifier = weather_integration.get_lap_time_modifier(current_weather)

        # Check if race control response needed
        rc_response = weather_integration.get_race_control_state(current_weather)
    """

    def __init__(self, gp_name: str, seed: Optional[int] = None):
        """
        Initialize weather integration for a race.

        Args:
            gp_name: Grand Prix name (e.g., "Monaco", "Britain")
            seed: Random seed for reproducibility
        """
        self.gp_name = gp_name
        self.seed = seed

        # Initialize weather generator
        self.generator = WeatherGenerator(seed=seed)

        # Track info
        self.track_info = get_track_info(gp_name)

        # State
        self._current_weather: Optional[WeatherState] = None
        self._weather_events: List[WeatherEvent] = []
        self._next_event_index: int = 0
        self._race_log: Optional[RaceWeatherLog] = None
        self._last_event_time: float = 0.0

    def initialize_race(self, race_duration: float = 120.0) -> RaceWeatherLog:
        """
        Initialize weather for the race.

        Args:
            race_duration: Expected race duration in minutes

        Returns:
            RaceWeatherLog with initial conditions
        """
        # Generate initial weather
        self._current_weather = self.generator.generate_initial_weather(self.gp_name)

        # Generate weather events during the race
        self._weather_events = self.generator.generate_race_weather_events(
            self.gp_name, race_duration=race_duration
        )

        # Sort events by timestamp
        self._weather_events.sort(key=lambda e: e.timestamp)
        self._next_event_index = 0
        self._last_event_time = 0.0

        # Create race log
        self._race_log = RaceWeatherLog(
            gp_name=self.gp_name,
            initial_weather=self._current_weather,
            weather_events=self._weather_events,
        )

        return self._race_log

    def get_current_weather(self, lap: int, race_time: float) -> WeatherState:
        """
        Get weather state at a specific point in the race.

        Args:
            lap: Current lap number
            race_time: Race time in minutes

        Returns:
            Current weather state
        """
        if self._current_weather is None:
            self.initialize_race()

        # At this point, _current_weather is guaranteed to be set
        assert self._current_weather is not None

        # Process any weather events that have occurred
        self._process_weather_events(race_time)

        return self._current_weather

    def _process_weather_events(self, race_time: float):
        """Process weather events up to the current race time."""
        if not self._weather_events:
            return

        # Ensure we have weather state
        if self._current_weather is None:
            self._current_weather = self.generator.generate_initial_weather(
                self.gp_name
            )

        # Calculate time since last check
        delta_time = race_time - self._last_event_time

        # Update weather based on time elapsed
        if delta_time > 0:
            self._current_weather = self.generator.update_weather(
                self._current_weather, delta_time
            )

        # Process new events
        while self._next_event_index < len(self._weather_events):
            event = self._weather_events[self._next_event_index]

            if event.timestamp <= race_time:
                self._apply_weather_event(event)
                self._next_event_index += 1
            else:
                break

        self._last_event_time = race_time

    def _apply_weather_event(self, event: WeatherEvent):
        """Apply a weather event to the current state."""
        # Ensure weather state exists
        if self._current_weather is None:
            self._current_weather = self.generator.generate_initial_weather(
                self.gp_name
            )

        assert self._current_weather is not None
        current = self._current_weather

        if event.event_type == "rain_start":
            # Start raining
            intensity_map = {
                (0, 0.3): RainIntensity.LIGHT,
                (0.3, 0.6): RainIntensity.MODERATE,
                (0.6, 0.8): RainIntensity.HEAVY,
                (0.8, 1.0): RainIntensity.TORRENTIAL,
            }

            for (low, high), intensity in intensity_map.items():
                if low <= event.intensity < high:
                    current.rain_intensity = intensity
                    break

            current.weather_type = self._determine_weather_type()

        elif event.event_type == "rain_intensify":
            # Increase rain intensity
            rain_int = current.rain_intensity
            if rain_int == RainIntensity.LIGHT:
                current.rain_intensity = RainIntensity.MODERATE
            elif rain_int == RainIntensity.MODERATE:
                current.rain_intensity = RainIntensity.HEAVY
            elif rain_int == RainIntensity.HEAVY:
                current.rain_intensity = RainIntensity.TORRENTIAL

        elif event.event_type == "rain_weaken":
            # Decrease rain intensity
            rain_int = current.rain_intensity
            if rain_int == RainIntensity.TORRENTIAL:
                current.rain_intensity = RainIntensity.HEAVY
            elif rain_int == RainIntensity.HEAVY:
                current.rain_intensity = RainIntensity.MODERATE
            elif rain_int == RainIntensity.MODERATE:
                current.rain_intensity = RainIntensity.LIGHT
            elif rain_int == RainIntensity.LIGHT:
                current.rain_intensity = RainIntensity.NONE

        elif event.event_type == "rain_stop":
            # Stop raining
            current.rain_intensity = RainIntensity.NONE
            current.weather_type = WeatherType.CLOUDY

        current.track_condition = self.generator._calculate_track_condition(current)

    def _determine_weather_type(self) -> WeatherType:
        """Determine weather type based on current state."""
        # Ensure weather state exists
        if self._current_weather is None:
            self._current_weather = self.generator.generate_initial_weather(self.gp_name)
        
        intensity = self._current_weather.rain_intensity

        if intensity == RainIntensity.NONE:
            return WeatherType.CLEAR
        elif intensity == RainIntensity.LIGHT:
            return WeatherType.LIGHT_RAIN
        elif intensity == RainIntensity.MODERATE:
            return WeatherType.MODERATE_RAIN
        elif intensity == RainIntensity.HEAVY:
            return WeatherType.HEAVY_RAIN
        else:
            return WeatherType.TORRENTIAL_RAIN

    def get_lap_time_modifier(self, weather: Optional[WeatherState] = None) -> float:
        """
        Calculate the lap time modifier based on weather conditions.

        Args:
            weather: Weather state (uses current if None)

        Returns:
            Percentage modifier to add to base lap time
        """
        if weather is None:
            weather = self._current_weather or self.generator.generate_initial_weather(
                self.gp_name
            )

        weather_impact = WEATHER_LAP_TIME_IMPACT.get(weather.weather_type, 0.0)
        track_impact = TRACK_CONDITION_IMPACT.get(weather.track_condition, 0.0)

        return weather_impact + track_impact

    def get_race_control_state(
        self, weather: Optional[WeatherState] = None
    ) -> RaceControlState:
        """
        Determine race control state based on weather.

        Args:
            weather: Weather state (uses current if None)

        Returns:
            Current race control state
        """
        if weather is None:
            weather = self._current_weather or self.generator.generate_initial_weather(
                self.gp_name
            )

        # Check for red flag conditions
        if weather.rain_intensity == RainIntensity.TORRENTIAL:
            return RaceControlState.RED_FLAG

        # Check for safety car
        if weather.rain_intensity == RainIntensity.HEAVY:
            return RaceControlState.SAFETY_CAR

        # Check for VSC conditions
        if weather.rain_intensity in [RainIntensity.LIGHT, RainIntensity.MODERATE]:
            if weather.track_condition in [TrackCondition.WET, TrackCondition.FLOODED]:
                return RaceControlState.VSC

        # Check for yellow flag
        if weather.rain_intensity != RainIntensity.NONE:
            return RaceControlState.YELLOW

        return RaceControlState.GREEN

    def get_recommended_tyre(
        self, weather: Optional[WeatherState] = None, current_compound: str = "MEDIUM"
    ) -> Tuple[str, str]:
        """
        Get recommended tyre based on weather conditions.

        Args:
            weather: Weather state (uses current if None)
            current_compound: Current tyre compound

        Returns:
            Tuple of (recommended_tyre, reason)
        """
        if weather is None:
            weather = self._current_weather or self.generator.generate_initial_weather(
                self.gp_name
            )

        if weather.track_condition == TrackCondition.DRY:
            return "dry", "Track is dry - use dry compounds"
        elif weather.track_condition == TrackCondition.DAMP:
            return "intermediate", "Track is damp - use Intermediates"
        elif weather.track_condition in [TrackCondition.WET, TrackCondition.FLOODED]:
            if weather.rain_intensity in [
                RainIntensity.HEAVY,
                RainIntensity.TORRENTIAL,
            ]:
                return "wet", "Heavy rain - use Full Wet tyres"
            else:
                return "intermediate", "Light/moderate rain - use Intermediates"

        return "dry", "Default to dry compounds"

    def get_visibility_factor(self, weather: Optional[WeatherState] = None) -> float:
        """Get visibility factor based on weather (0-1, lower is worse)."""
        if weather is None:
            weather = self._current_weather or self.generator.generate_initial_weather(
                self.gp_name
            )

        return VISIBILITY_IMPACT.get(weather.rain_intensity, 1.0)

    def log_lap_weather(self, lap: int, race_time: float) -> WeatherLapData:
        """
        Log weather data for a specific lap.

        Args:
            lap: Lap number
            race_time: Race time in minutes

        Returns:
            WeatherLapData for this lap
        """
        weather = self.get_current_weather(lap, race_time)
        lap_modifier = self.get_lap_time_modifier(weather)
        recommended, _ = self.get_recommended_tyre(weather)

        lap_data = WeatherLapData(
            lap=lap,
            race_time=race_time,
            weather=weather,
            lap_time_modifier=lap_modifier,
            recommended_tyre=recommended,
        )

        if self._race_log:
            self._race_log.add_lap_data(lap_data)

        return lap_data

    def get_race_summary(self) -> Dict[str, Any]:
        """
        Get summary of race weather.

        Returns:
            Dictionary with race weather summary
        """
        if self._race_log is None:
            return {}

        return {
            "gp_name": self.gp_name,
            "initial_weather": self._race_log.initial_weather.weather_type.value,
            "initial_rain": self._race_log.initial_weather.rain_intensity.name,
            "total_events": len(self._race_log.weather_events),
            "rain_events": self._race_log.get_rain_events(),
            "wet_laps": self._race_log.get_wet_laps(),
            "total_laps": len(self._race_log.lap_data),
            "track_info": self.track_info,
        }

    def apply_weather_to_lap_time(
        self, base_lap_time: float, lap: int, race_time: float
    ) -> float:
        """
        Apply weather effects to a lap time.

        Args:
            base_lap_time: Base lap time in seconds
            lap: Current lap number
            race_time: Race time in minutes

        Returns:
            Modified lap time in seconds
        """
        weather = self.get_current_weather(lap, race_time)
        modifier = self.get_lap_time_modifier(weather)

        return base_lap_time * (1 + modifier)


def demonstrate_weather_integration(gp_name: str = "Monaco", seed: int = 42):
    """
    Demonstrate weather integration with race simulation.

    This shows how weather would be used during a race simulation.

    Args:
        gp_name: Grand Prix name
        seed: Random seed for reproducibility
    """
    print(f"\n{'=' * 60}")
    print(f"Weather Integration Demo - {gp_name}")
    print(f"{'=' * 60}")

    # Initialize weather integration
    weather = SimWeatherIntegration(gp_name, seed=seed)
    weather.initialize_race(race_duration=120)

    # Print initial conditions
    initial = weather._current_weather
    if initial is None:
        print("Error: Failed to initialize weather")
        return
    
    print(f"\nInitial Conditions:")
    print(f"  Weather: {initial.weather_type.value}")
    print(f"  Rain intensity: {initial.rain_intensity.name}")
    print(f"  Track condition: {initial.track_condition.value}")
    print(f"  Temperature: {initial.temperature:.1f}°C")
    print(f"  Race control: {initial.race_control.value}")

    # Print weather events
    if weather._weather_events:
        print(f"\nWeather Events ({len(weather._weather_events)} total):")
        for event in weather._weather_events[:5]:  # Show first 5
            print(f"  - {event.description}")

    # Simulate race laps
    print(f"\nLap-by-lap Weather (sample):")
    sample_laps = [1, 10, 20, 30, 40, 50, 60, 70]
    base_lap_time = 76.0  # Monaco base lap time

    for lap in sample_laps:
        race_time = lap * 1.5  # ~90 seconds per lap
        lap_data = weather.log_lap_weather(lap, race_time)

        print(f"\n  Lap {lap}:")
        print(f"    Weather: {lap_data.weather.weather_type.value}")
        print(f"    Rain: {lap_data.weather.rain_intensity.name}")
        print(f"    Track: {lap_data.weather.track_condition.value}")
        print(f"    Lap time modifier: +{lap_data.lap_time_modifier:.1%}")
        print(f"    Recommended tyre: {lap_data.recommended_tyre}")

        # Show lap time
        adjusted_time = base_lap_time * (1 + lap_data.lap_time_modifier)
        print(
            f"    Base lap time: {base_lap_time:.2f}s -> Adjusted: {adjusted_time:.2f}s"
        )

        # Show race control
        rc = weather.get_race_control_state(lap_data.weather)
        if rc != RaceControlState.GREEN:
            print(f"    Race Control: {rc.value.upper()}")

    # Print summary
    summary = weather.get_race_summary()
    print(f"\n{'=' * 60}")
    print(f"Race Weather Summary:")
    print(f"{'=' * 60}")
    print(f"  Initial weather: {summary.get('initial_weather', 'N/A')}")
    print(f"  Total events: {summary.get('total_events', 0)}")
    print(f"  Rain events: {summary.get('rain_events', 0)}")
    print(f"  Wet laps: {summary.get('wet_laps', 0)}")
    print(f"  Total laps logged: {summary.get('total_laps', 0)}")


if __name__ == "__main__":
    # Run demonstration
    demonstrate_weather_integration("Monaco")
    print("\n")
    demonstrate_weather_integration("Britain")
    print("\n")
    demonstrate_weather_integration("Singapore")
