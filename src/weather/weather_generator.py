"""
Weather Generator with Real-World 2022 F1 Data Calibration.

Generates realistic weather patterns for F1 races based on:
- Geographic location (tropical/temperate/desert climate)
- Season/month of race
- Historical weather patterns

The generator uses the 2022 F1 race calendar to calibrate weather
probability for each circuit.
"""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from weather.weather_types import (
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    WeatherState,
    RACE_CALENDAR_2022,
    get_track_info,
)


# Climate-based rain probability modifiers
CLIMATE_RAIN_MODIFIERS = {
    "desert": {
        "rain_chance_multiplier": 0.2,
        "rain_intensity_bias": 0.1,  # Light rain more likely
        "thunderstorm_chance": 0.01,
        "typical_rain_duration": (10, 20),  # minutes
    },
    "tropical": {
        "rain_chance_multiplier": 1.5,
        "rain_intensity_bias": 0.6,  # Heavy rain more likely
        "thunderstorm_chance": 0.15,
        "typical_rain_duration": (20, 45),
    },
    "temperate": {
        "rain_chance_multiplier": 1.3,
        "rain_intensity_bias": 0.4,
        "thunderstorm_chance": 0.08,
        "typical_rain_duration": (15, 35),
    },
    "continental": {
        "rain_chance_multiplier": 1.0,
        "rain_intensity_bias": 0.5,
        "thunderstorm_chance": 0.12,
        "typical_rain_duration": (15, 30),
    },
    "mediterranean": {
        "rain_chance_multiplier": 0.7,
        "rain_intensity_bias": 0.3,
        "thunderstorm_chance": 0.05,
        "typical_rain_duration": (10, 25),
    },
}

# Month-based seasonal modifiers (1-12)
SEASONAL_RAIN_MODIFIERS = {
    1: {"modifier": 1.2, "description": "Winter - higher rain in temperate"},
    2: {"modifier": 1.1, "description": "Late winter"},
    3: {"modifier": 1.0, "description": "Spring transition"},
    4: {"modifier": 1.1, "description": "Spring showers"},
    5: {"modifier": 1.0, "description": "Late spring"},
    6: {"modifier": 0.9, "description": "Early summer"},
    7: {"modifier": 0.8, "description": "Summer"},
    8: {"modifier": 0.9, "description": "Late summer"},
    9: {"modifier": 1.1, "description": "Fall transition"},
    10: {"modifier": 1.2, "description": "Fall rains"},
    11: {"modifier": 1.3, "description": "Late fall"},
    12: {"modifier": 1.2, "description": "Winter rains"},
}


@dataclass
class WeatherEvent:
    """Represents a weather event during the race."""

    event_type: str  # 'rain_start', 'rain_stop', 'intensify', 'weaken', 'dry_line'
    timestamp: float  # Minutes into the race
    intensity: float  # 0-1 scale
    duration: float  # Minutes
    description: str


@dataclass
class WeatherForecast:
    """Weather forecast for a race."""

    race_name: str
    race_date: str
    predicted_weather: List[WeatherState]
    rain_probability: float
    temperature_estimate: Tuple[float, float]
    humidity_estimate: Tuple[float, float]
    confidence: float  # 0-1


@dataclass
class DynamicWeatherPattern:
    """
    Tracks weather changes during a session.

    Models the "British summer" effect where weather can go from
    dry to rain and back multiple times during a 2-hour race.

    Attributes:
        track_name: Name of the track
        weather_change_probability: Base probability of weather change per minute
        current_weather_state: Current weather pattern (CLEAR or RAIN)
        time_since_last_change: Minutes since last weather change
        min_time_between_changes: Minimum minutes between weather changes
        max_time_between_changes: Maximum minutes between weather changes
        change_history: Record of all weather changes
    """

    track_name: str = ""
    weather_change_probability: float = 0.15
    current_weather_state: str = "CLEAR"  # "CLEAR" or "RAIN"
    time_since_last_change: float = 0.0
    min_time_between_changes: float = 10.0  # minutes
    max_time_between_changes: float = 45.0  # minutes
    change_history: List[dict] = field(default_factory=list)

    def should_change_weather(self, race_time_minutes: float) -> bool:
        """
        Determine if weather should change at the current race time.

        Args:
            race_time_minutes: Current race time in minutes

        Returns:
            True if weather should change, False otherwise
        """
        # Check if minimum time has passed since last change
        if self.time_since_last_change < self.min_time_between_changes:
            return False

        # Time-based probability increases as time progresses
        # British summer effect: afternoon showers more common
        time_factor = min(1.0, race_time_minutes / 60.0)  # Increases towards race end

        # Calculate effective probability
        effective_prob = self.weather_change_probability * (0.5 + 0.5 * time_factor)

        # Random check
        return random.random() < effective_prob

    def trigger_weather_change(
        self, race_time_minutes: float, current_weather: WeatherState
    ) -> Tuple[WeatherState, str]:
        """
        Trigger a weather change and return the new weather state.

        Args:
            race_time_minutes: Current race time in minutes
            current_weather: Current weather state

        Returns:
            Tuple of (new weather state, description of change)
        """
        # Toggle weather state
        if self.current_weather_state == "CLEAR":
            self.current_weather_state = "RAIN"
            new_intensity = random.choice(
                [RainIntensity.LIGHT, RainIntensity.MODERATE, RainIntensity.HEAVY]
            )
            change_desc = f"Rain starts at minute {race_time_minutes:.1f}"
        else:
            self.current_weather_state = "CLEAR"
            new_intensity = RainIntensity.NONE
            change_desc = f"Rain stops at minute {race_time_minutes:.1f}"

        # Record the change
        self.change_history.append(
            {
                "time": race_time_minutes,
                "from_state": current_weather.weather_type.value,
                "to_state": self.current_weather_state,
                "description": change_desc,
            }
        )

        # Reset timer
        self.time_since_last_change = 0.0

        # Create new weather state
        new_weather = WeatherState(
            weather_type=WeatherType.CLEAR
            if new_intensity == RainIntensity.NONE
            else WeatherType.LIGHT_RAIN,
            track_condition=TrackCondition.DRY
            if new_intensity == RainIntensity.NONE
            else TrackCondition.WET,
            race_control=RaceControlState.GREEN,
            temperature=current_weather.temperature,
            track_temperature=current_weather.track_temperature,
            humidity=current_weather.humidity,
            wind_speed=current_weather.wind_speed,
            precipitation_probability=50.0
            if new_intensity != RainIntensity.NONE
            else 10.0,
            rain_intensity=new_intensity,
            visibility=10000.0 if new_intensity == RainIntensity.NONE else 3000.0,
            rainfall_accumulation=0.0,
            timestamp=datetime.now(),
            weather_change_probability=self.weather_change_probability,
            last_weather_change_time=race_time_minutes,
            weather_history=self.change_history.copy(),
        )

        return new_weather, change_desc


class WeatherGenerator:
    """
    Generates realistic weather patterns for F1 races.

    Uses 2022 F1 race calendar data to calibrate weather probability
    based on track location, climate type, and race month.

    Usage:
        generator = WeatherGenerator()

        # Generate initial weather for a race
        initial_weather = generator.generate_initial_weather("Monaco")

        # Generate weather events during the race
        events = generator.generate_race_weather_events("Monaco", race_duration=120)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the weather generator.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = random.Random(seed)
        self.calendar = RACE_CALENDAR_2022
        self._last_weather: Optional[WeatherState] = None
        self._event_history: List[WeatherEvent] = []

    def _get_month_from_date(self, date_str: str) -> int:
        """Extract month from date string."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.month
        except:
            return 9  # Default to September

    def _calculate_base_rain_probability(self, track_info: dict) -> float:
        """
        Calculate base rain probability for a track based on:
        - Climate type
        - Season/month
        - Historical patterns
        """
        base_chance = track_info.get("rain_chance", 0.25)
        climate = track_info.get("climate", "temperate")
        rainy_months = track_info.get("rainy_months", [])

        # Get climate modifier
        climate_mod = CLIMATE_RAIN_MODIFIERS.get(climate, {})
        rain_multiplier = climate_mod.get("rain_chance_multiplier", 1.0)

        # Get race month
        race_date = track_info.get("date", "2022-09-01")
        race_month = self._get_month_from_date(race_date)

        # Apply seasonal modifier
        seasonal_mod = SEASONAL_RAIN_MODIFIERS.get(race_month, {}).get("modifier", 1.0)

        # Check if race is in rainy season
        if race_month in rainy_months:
            seasonal_mod *= 1.3  # Boost rain chance in rainy season

        # Calculate final probability
        final_prob = base_chance * rain_multiplier * seasonal_mod

        # Clamp between 2% and 60%
        return max(0.02, min(0.60, final_prob))

    def _get_rain_intensity(self, climate: str) -> RainIntensity:
        """
        Determine rain intensity based on climate.

        Returns weighted random intensity biased by climate type.
        """
        climate_mod = CLIMATE_RAIN_MODIFIERS.get(climate, {})
        bias = climate_mod.get("rain_intensity_bias", 0.4)

        roll = self.rng.random()

        # Bias towards lighter rain in desert, heavier in tropical
        if roll < bias * 0.5:
            return RainIntensity.LIGHT
        elif roll < bias:
            return RainIntensity.MODERATE
        elif roll < bias + 0.3:
            return RainIntensity.HEAVY
        else:
            return RainIntensity.TORRENTIAL

    def _determine_weather_type(self, rain_intensity: RainIntensity) -> WeatherType:
        """Map rain intensity to weather type."""
        if rain_intensity == RainIntensity.NONE:
            return WeatherType.CLEAR
        elif rain_intensity == RainIntensity.LIGHT:
            return self.rng.choice(
                [WeatherType.PARTLY_CLOUDY, WeatherType.CLOUDY, WeatherType.LIGHT_RAIN]
            )
        elif rain_intensity == RainIntensity.MODERATE:
            return self.rng.choice(
                [
                    WeatherType.CLOUDY,
                    WeatherType.OVERCAST,
                    WeatherType.LIGHT_RAIN,
                    WeatherType.MODERATE_RAIN,
                ]
            )
        elif rain_intensity == RainIntensity.HEAVY:
            return self.rng.choice(
                [
                    WeatherType.OVERCAST,
                    WeatherType.MODERATE_RAIN,
                    WeatherType.HEAVY_RAIN,
                ]
            )
        else:  # TORRENTIAL
            return self.rng.choice(
                [
                    WeatherType.HEAVY_RAIN,
                    WeatherType.TORRENTIAL_RAIN,
                    WeatherType.THUNDERSTORM,
                ]
            )

    def _calculate_track_condition(self, weather: WeatherState) -> TrackCondition:
        """Calculate track condition based on rain intensity and accumulation."""
        rain_int = weather.rain_intensity

        if rain_int == RainIntensity.NONE:
            # Could be drying
            if weather.rainfall_accumulation > 0:
                return TrackCondition.DAMP
            return TrackCondition.DRY
        elif rain_int == RainIntensity.LIGHT:
            if weather.rainfall_accumulation < 0.5:
                return TrackCondition.DAMP
            return TrackCondition.WET
        elif rain_int == RainIntensity.MODERATE:
            return TrackCondition.WET
        elif rain_int == RainIntensity.HEAVY:
            return (
                TrackCondition.FLOODED
                if weather.rainfall_accumulation > 3
                else TrackCondition.WET
            )
        else:  # TORRENTIAL
            return TrackCondition.FLOODED

    def generate_initial_weather(self, gp_name: str) -> WeatherState:
        """
        Generate initial weather conditions for a race.

        Args:
            gp_name: Grand Prix name (e.g., "Monaco", "Britain", "Singapore")

        Returns:
            WeatherState with initial race conditions
        """
        track_info = get_track_info(gp_name)

        # Calculate rain probability
        rain_prob = self._get_month_from_date(track_info.get("date", "2022-09-01"))
        base_rain_prob = self._calculate_base_rain_probability(track_info)

        # Determine if it will rain during the race
        will_rain = self.rng.random() < base_rain_prob

        # Determine rain intensity if raining
        climate = track_info.get("climate", "temperate")
        rain_intensity = (
            self._get_rain_intensity(climate) if will_rain else RainIntensity.NONE
        )

        # Generate weather type
        weather_type = self._determine_weather_type(rain_intensity)

        # Generate temperatures
        temp_range = track_info.get("temp_range", (15, 25))
        humidity_range = track_info.get("humidity", (50, 70))

        temperature = self.rng.uniform(temp_range[0], temp_range[1])
        track_temp = temperature + self.rng.uniform(3, 8)  # Track is typically warmer
        humidity = self.rng.uniform(humidity_range[0], humidity_range[1])

        # Wind speed
        wind_speed = self.rng.uniform(5, 25)

        # Precipitation probability
        precip_prob = base_rain_prob * 100 if will_rain else self.rng.uniform(0, 20)

        # Visibility
        if rain_intensity == RainIntensity.NONE:
            visibility = self.rng.uniform(8000, 10000)
        elif rain_intensity == RainIntensity.LIGHT:
            visibility = self.rng.uniform(5000, 8000)
        elif rain_intensity == RainIntensity.MODERATE:
            visibility = self.rng.uniform(2000, 5000)
        elif rain_intensity == RainIntensity.HEAVY:
            visibility = self.rng.uniform(500, 2000)
        else:
            visibility = self.rng.uniform(100, 500)

        # Race control state
        race_control = RaceControlState.GREEN
        if rain_intensity == RainIntensity.HEAVY:
            race_control = RaceControlState.SAFETY_CAR
        elif rain_intensity == RainIntensity.TORRENTIAL:
            race_control = RaceControlState.RED_FLAG

        weather = WeatherState(
            weather_type=weather_type,
            track_condition=TrackCondition.DRY
            if rain_intensity == RainIntensity.NONE
            else TrackCondition.WET,
            race_control=race_control,
            temperature=temperature,
            track_temperature=track_temp,
            humidity=humidity,
            wind_speed=wind_speed,
            precipitation_probability=precip_prob,
            rain_intensity=rain_intensity,
            visibility=visibility,
            rainfall_accumulation=0.0,
            timestamp=datetime.now(),
            weather_change_probability=track_info.get(
                "weather_change_probability", 0.15
            ),
        )

        self._last_weather = weather
        return weather

    def generate_race_weather_events(
        self,
        gp_name: str,
        race_duration: float = 120.0,
        num_events: Optional[int] = None,
    ) -> List[WeatherEvent]:
        """
        Generate weather events that occur during the race.

        Args:
            gp_name: Grand Prix name
            race_duration: Race duration in minutes
            num_events: Number of weather events (auto-calculated if None)

        Returns:
            List of WeatherEvent objects
        """
        track_info = get_track_info(gp_name)
        base_rain_prob = self._calculate_base_rain_probability(track_info)

        # Calculate number of events based on rain probability
        if num_events is None:
            # More rain = more potential events
            if base_rain_prob < 0.1:
                num_events = self.rng.randint(0, 2)
            elif base_rain_prob < 0.25:
                num_events = self.rng.randint(1, 3)
            elif base_rain_prob < 0.4:
                num_events = self.rng.randint(2, 4)
            else:
                num_events = self.rng.randint(3, 6)

        events = []
        climate = track_info.get("climate", "temperate")

        # Generate events at random times during the race
        event_times = sorted(
            self.rng.sample(
                range(int(race_duration)), min(num_events, int(race_duration))
            )
        )

        for i, event_time in enumerate(event_times):
            event_type = self.rng.choice(
                ["rain_start", "rain_intensify", "rain_weaken", "rain_stop", "dry_line"]
            )

            if event_type == "rain_stop":
                intensity = 0.0
                duration = self.rng.uniform(10, 30)
            elif event_type in ["rain_intensify", "rain_weaken"]:
                intensity = self.rng.uniform(0.3, 0.8)
                duration = self.rng.uniform(5, 20)
            else:  # rain_start or dry_line
                intensity = self.rng.uniform(0.2, 0.9)
                climate_mod = CLIMATE_RAIN_MODIFIERS.get(climate, {})
                dur_range = climate_mod.get("typical_rain_duration", (15, 30))
                duration = self.rng.uniform(dur_range[0], dur_range[1])

            # Create event description
            descriptions = {
                "rain_start": f"Rain begins at minute {event_time}",
                "rain_intensify": f"Rain intensifies at minute {event_time}",
                "rain_weaken": f"Rain eases at minute {event_time}",
                "rain_stop": f"Rain stops at minute {event_time}",
                "dry_line": f"Dry line forms at minute {event_time}",
            }

            event = WeatherEvent(
                event_type=event_type,
                timestamp=float(event_time),
                intensity=intensity,
                duration=duration,
                description=descriptions.get(
                    event_type, f"Weather change at minute {event_time}"
                ),
            )
            events.append(event)

        self._event_history.extend(events)
        return events

    def update_weather(
        self, current_weather: WeatherState, delta_time: float
    ) -> WeatherState:
        """
        Update weather state based on elapsed time.

        Args:
            current_weather: Current weather state
            delta_time: Time elapsed in minutes

        Returns:
            Updated weather state
        """
        weather = current_weather

        # Update rainfall accumulation based on rain intensity
        if weather.rain_intensity != RainIntensity.NONE:
            # mm per minute based on intensity
            rate = {
                RainIntensity.LIGHT: 0.5,
                RainIntensity.MODERATE: 2.0,
                RainIntensity.HEAVY: 5.0,
                RainIntensity.TORRENTIAL: 10.0,
            }.get(weather.rain_intensity, 0)

            weather.rainfall_accumulation += rate * (delta_time / 60.0)

        # Update track condition
        weather.track_condition = self._calculate_track_condition(weather)

        # Update race control if needed
        if weather.rain_intensity == RainIntensity.TORRENTIAL:
            weather.race_control = RaceControlState.RED_FLAG
        elif weather.rain_intensity == RainIntensity.HEAVY:
            if weather.race_control == RaceControlState.GREEN:
                weather.race_control = RaceControlState.SAFETY_CAR
        elif weather.track_condition == TrackCondition.WET:
            if weather.race_control == RaceControlState.GREEN:
                weather.race_control = RaceControlState.YELLOW

        # Decrease accumulation over time (drying)
        if (
            weather.rain_intensity == RainIntensity.NONE
            and weather.rainfall_accumulation > 0
        ):
            drying_rate = 0.1  # mm per minute
            weather.rainfall_accumulation = max(
                0, weather.rainfall_accumulation - drying_rate * (delta_time / 60.0)
            )

        # Update visibility
        if weather.rain_intensity != RainIntensity.NONE:
            target_visibility = {
                RainIntensity.LIGHT: 5000,
                RainIntensity.MODERATE: 2500,
                RainIntensity.HEAVY: 800,
                RainIntensity.TORRENTIAL: 200,
            }.get(weather.rain_intensity, 5000)
            weather.visibility = weather.visibility * 0.95 + target_visibility * 0.05

        weather.timestamp = datetime.now()
        self._last_weather = weather
        return weather

    def update_weather_during_race(
        self,
        current_weather: WeatherState,
        race_time_minutes: float,
        gp_name: str,
    ) -> Tuple[Optional[WeatherState], List[str]]:
        """
        Update weather during a race, potentially triggering weather changes
        for tracks with unpredictable weather (Britain, Belgium, Netherlands).

        Args:
            current_weather: Current weather state
            race_time_minutes: Current race time in minutes
            gp_name: Grand Prix name

        Returns:
            Tuple of (new weather state if changed, list of change descriptions)
        """
        track_info = get_track_info(gp_name)
        weather_change_prob = track_info.get("weather_change_probability", 0.15)

        changes = []

        # Only apply dynamic weather for tracks with high change probability
        if weather_change_prob < 0.20:
            return None, changes

        # Initialize dynamic pattern if not exists
        if not hasattr(self, "_dynamic_weather"):
            self._dynamic_weather = DynamicWeatherPattern(
                track_name=gp_name,
                weather_change_probability=weather_change_prob,
                current_weather_state="RAIN"
                if current_weather.rain_intensity != RainIntensity.NONE
                else "CLEAR",
            )

        # Calculate time delta since last call
        time_delta = 1.0
        if hasattr(self, "_last_race_time"):
            time_delta = max(1.0, race_time_minutes - self._last_race_time)
        self._last_race_time = race_time_minutes

        # Update time since last change
        self._dynamic_weather.time_since_last_change += time_delta

        # Check if weather should change
        if self._dynamic_weather.should_change_weather(race_time_minutes):
            new_weather, change_desc = self._dynamic_weather.trigger_weather_change(
                race_time_minutes, current_weather
            )
            changes.append(change_desc)
            self._last_weather = new_weather
            return new_weather, changes

        return None, changes

    def get_weather_forecast(self, gp_name: str) -> WeatherForecast:
        """
        Generate a weather forecast for a race.

        Args:
            gp_name: Grand Prix name

        Returns:
            WeatherForecast with predictions
        """
        track_info = get_track_info(gp_name)
        base_rain_prob = self._calculate_base_rain_probability(track_info)

        temp_range = track_info.get("temp_range", (15, 25))
        humidity_range = track_info.get("humidity", (50, 70))

        # Generate predicted weather states
        predicted = []

        # Initial
        initial = self.generate_initial_weather(gp_name)
        predicted.append(initial)

        # Mid-race
        if self.rng.random() < base_rain_prob:
            mid_weather = self.generate_initial_weather(gp_name)
            mid_weather.rain_intensity = self._get_rain_intensity(track_info["climate"])
            mid_weather.weather_type = self._determine_weather_type(
                mid_weather.rain_intensity
            )
            predicted.append(mid_weather)

        # Race start conditions (less likely to be wet)
        start_rain_prob = base_rain_prob * 0.5
        confidence = (
            0.5 + (1 - base_rain_prob) * 0.3
        )  # More confident when rain unlikely

        return WeatherForecast(
            race_name=gp_name,
            race_date=track_info.get("date", "2022-09-01"),
            predicted_weather=predicted,
            rain_probability=base_rain_prob,
            temperature_estimate=temp_range,
            humidity_estimate=humidity_range,
            confidence=confidence,
        )

    def get_track_climate_info(self, gp_name: str) -> dict:
        """Get detailed climate information for a track."""
        track_info = get_track_info(gp_name)
        climate = track_info.get("climate", "temperate")
        climate_data = CLIMATE_RAIN_MODIFIERS.get(climate, {})
        race_month = self._get_month_from_date(track_info.get("date", "2022-09-01"))

        return {
            "track": gp_name,
            "country": track_info.get("country", "Unknown"),
            "climate_type": climate,
            "race_month": race_month,
            "base_rain_chance": track_info.get("rain_chance", 0.25),
            "rain_chance_multiplier": climate_data.get("rain_chance_multiplier", 1.0),
            "calculated_rain_probability": self._calculate_base_rain_probability(
                track_info
            ),
            "rainy_months": track_info.get("rainy_months", []),
            "is_rainy_season": race_month in track_info.get("rainy_months", []),
            "temperature_range": track_info.get("temp_range", (15, 25)),
            "humidity_range": track_info.get("humidity", (50, 70)),
        }


def generate_weather_for_all_2022_races(seed: Optional[int] = None) -> Dict[str, dict]:
    """
    Generate weather for all 2022 F1 races.

    Useful for calibration and testing.

    Args:
        seed: Random seed for reproducibility

    Returns:
        Dictionary mapping race names to weather data
    """
    generator = WeatherGenerator(seed=seed)
    results = {}

    for race_name in RACE_CALENDAR_2022.keys():
        track_info = get_track_info(race_name)
        base_prob = generator._calculate_base_rain_probability(track_info)

        # Generate multiple samples
        samples = []
        for _ in range(100):
            initial = generator.generate_initial_weather(race_name)
            events = generator.generate_race_weather_events(
                race_name, race_duration=120
            )

            # Count rain events
            rain_events = sum(1 for e in events if "rain" in e.event_type)

            samples.append(
                {
                    "initial_weather": initial.weather_type.value,
                    "initial_rain_intensity": initial.rain_intensity.name,
                    "num_events": len(events),
                    "rain_events": rain_events,
                    "track_condition": initial.track_condition.value,
                }
            )

        # Calculate statistics
        rain_count = sum(1 for s in samples if s["initial_rain_intensity"] != "NONE")
        avg_events = sum(s["num_events"] for s in samples) / len(samples)

        results[race_name] = {
            "track_info": track_info,
            "base_rain_probability": base_prob,
            "samples": samples,
            "rain_occurred_count": rain_count,
            "rain_occurred_percentage": rain_count,
            "average_events": avg_events,
            "climate_info": generator.get_track_climate_info(race_name),
        }

    return results


if __name__ == "__main__":
    # Demo usage
    generator = WeatherGenerator(seed=42)

    print("=" * 60)
    print("Weather Generator - 2022 F1 Races Calibration")
    print("=" * 60)

    # Test a few specific races
    test_races = ["Monaco", "Britain", "Singapore", "Bahrain", "Brazil"]

    for race in test_races:
        print(f"\n{race}:")
        info = generator.get_track_climate_info(race)
        print(f"  Climate: {info['climate_type']}")
        print(f"  Base rain chance: {info['base_rain_chance']:.1%}")
        print(f"  Calculated probability: {info['calculated_rain_probability']:.1%}")
        print(f"  Rainy season: {info['is_rainy_season']}")

        # Generate sample weather
        weather = generator.generate_initial_weather(race)
        print(f"  Sample weather: {weather.weather_type.value}")
        print(f"  Rain intensity: {weather.rain_intensity.name}")
