"""
F1 Weather System Package.

This package provides weather simulation for F1 races including:
- Weather generation based on real-world 2022 F1 data
- Track condition modeling
- Race control responses (VSC, SC, Red Flag)
- Weather events during races
- Weather impact on lap times

Usage:
    from weather import WeatherGenerator, WeatherState, WeatherType

    generator = WeatherGenerator(seed=42)
    weather = generator.generate_initial_weather("Monaco")
"""

from weather.weather_generator import (
    WeatherGenerator,
    WeatherEvent,
    WeatherForecast,
    generate_weather_for_all_2022_races,
)

from weather.weather_types import (
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    WeatherState,
    TrackClimateProfile,
    RACE_CALENDAR_2022,
    get_track_info,
)

__all__ = [
    # Generator
    "WeatherGenerator",
    "WeatherEvent",
    "WeatherForecast",
    "generate_weather_for_all_2022_races",
    # Types
    "WeatherType",
    "TrackCondition",
    "RaceControlState",
    "RainIntensity",
    "WeatherState",
    "TrackClimateProfile",
    # Data
    "RACE_CALENDAR_2022",
    "get_track_info",
]

__version__ = "1.0.0"
