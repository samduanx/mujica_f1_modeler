"""
Weather Types and Data Classes for F1 Weather System.

Defines weather conditions, track states, and related enums used
throughout the weather system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class WeatherType(Enum):
    """Weather condition types with increasing severity."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    MODERATE_RAIN = "moderate_rain"
    HEAVY_RAIN = "heavy_rain"
    TORRENTIAL_RAIN = "torrential_rain"
    THUNDERSTORM = "thunderstorm"


class TrackCondition(Enum):
    """Track surface condition states."""

    DRY = "dry"
    DAMP = "damp"
    WET = "wet"
    FLOODED = "flooded"


class RaceControlState(Enum):
    """Race control flags and states."""

    GREEN = "green"  # All clear
    YELLOW = "yellow"  # Caution
    DOUBLE_YELLOW = "double_yellow"  # Sector yellow
    SAFETY_CAR = "safety_car"
    VSC = "virtual_safety_car"
    RED_FLAG = "red_flag"
    WET_START = "wet_start"  # 2026 wet start regulations


class RainIntensity(Enum):
    """Rain intensity levels."""

    NONE = 0
    LIGHT = 1
    MODERATE = 2
    HEAVY = 3
    TORRENTIAL = 4


@dataclass
class WeatherState:
    """
    Current weather state for a race.

    Attributes:
        weather_type: Current weather condition
        track_condition: Current track surface state
        race_control: Current race control state
        temperature: Air temperature in Celsius
        track_temperature: Track surface temperature in Celsius
        humidity: Humidity percentage (0-100)
        wind_speed: Wind speed in km/h
        precipitation_probability: Chance of rain (0-100)
        rain_intensity: Current rain intensity level
        visibility: Visibility in meters
        rainfall_accumulation: Millimeters of rain accumulated
        timestamp: When this state was recorded
        weather_change_probability: How likely weather is to change during this session (0-1)
        last_weather_change_time: When weather last changed (minutes into race)
        weather_history: Track of weather changes during race
    """

    weather_type: WeatherType = WeatherType.CLEAR
    track_condition: TrackCondition = TrackCondition.DRY
    race_control: RaceControlState = RaceControlState.GREEN
    temperature: float = 25.0
    track_temperature: float = 30.0
    humidity: float = 50.0
    wind_speed: float = 10.0
    precipitation_probability: float = 0.0
    rain_intensity: RainIntensity = RainIntensity.NONE
    visibility: float = 10000.0
    rainfall_accumulation: float = 0.0
    timestamp: Optional[datetime] = None
    # Dynamic weather tracking
    weather_change_probability: float = 0.0
    last_weather_change_time: float = 0.0
    weather_history: list = field(default_factory=list)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "weather_type": self.weather_type.value,
            "track_condition": self.track_condition.value,
            "race_control": self.race_control.value,
            "temperature": self.temperature,
            "track_temperature": self.track_temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "precipitation_probability": self.precipitation_probability,
            "rain_intensity": self.rain_intensity.name,
            "visibility": self.visibility,
            "rainfall_accumulation": self.rainfall_accumulation,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "weather_change_probability": self.weather_change_probability,
            "last_weather_change_time": self.last_weather_change_time,
            "weather_history": self.weather_history,
        }


@dataclass
class TrackClimateProfile:
    """
    Climate profile for a specific track.

    Defines the baseline weather characteristics for a circuit based on
    its geographic location and typical race month.
    """

    name: str
    country: str
    climate_type: (
        str  # 'tropical', 'desert', 'temperate', 'continental', 'mediterranean'
    )
    latitude: float
    longitude: float
    typical_temperature_range: tuple  # (min, max) in Celsius
    humidity_range: tuple  # (min, max) in percentage
    baseline_rain_chance: float  # Base probability of rain (0-1)
    rainy_season_months: list  # Months with increased rain chance
    monsoon_influence: bool  # Affected by monsoon patterns


# 2022 F1 Race Calendar with dates and track profiles
RACE_CALENDAR_2022 = {
    "Bahrain": {
        "date": "2022-03-20",
        "country": "Bahrain",
        "climate": "desert",
        "lat": 26.0325,
        "lon": 50.5106,
        "temp_range": (18, 28),
        "humidity": (30, 50),
        "rain_chance": 0.05,
        "rainy_months": [],
    },
    "Saudi Arabia": {
        "date": "2022-03-27",
        "country": "Saudi Arabia",
        "climate": "desert",
        "lat": 21.5433,
        "lon": 39.1728,
        "temp_range": (22, 32),
        "humidity": (25, 45),
        "rain_chance": 0.03,
        "rainy_months": [],
    },
    "Australia": {
        "date": "2022-04-10",
        "country": "Australia",
        "climate": "temperate",
        "lat": -37.8497,
        "lon": 144.7680,
        "temp_range": (12, 22),
        "humidity": (50, 70),
        "rain_chance": 0.25,
        "rainy_months": [6, 7, 8],  # Australian winter
    },
    "Emilia Romagna": {
        "date": "2022-04-24",
        "country": "Italy",
        "climate": "mediterranean",
        "lat": 44.3439,
        "lon": 11.7140,
        "temp_range": (12, 22),
        "humidity": (55, 75),
        "rain_chance": 0.30,
        "rainy_months": [3, 4, 5, 10, 11],
    },
    "Miami": {
        "date": "2022-05-08",
        "country": "USA",
        "climate": "tropical",
        "lat": 25.9582,
        "lon": -80.2389,
        "temp_range": (25, 32),
        "humidity": (70, 90),
        "rain_chance": 0.40,
        "rainy_months": [5, 6, 7, 8, 9, 10],  # Miami rainy season starts May
    },
    "Spain": {
        "date": "2022-05-22",
        "country": "Spain",
        "climate": "mediterranean",
        "lat": 41.5700,
        "lon": 2.2611,
        "temp_range": (18, 28),
        "humidity": (40, 65),
        "rain_chance": 0.15,
        "rainy_months": [3, 4, 5, 9, 10, 11],
    },
    "Monaco": {
        "date": "2022-05-29",
        "country": "Monaco",
        "climate": "mediterranean",
        "lat": 43.7347,
        "lon": 7.4206,
        "temp_range": (18, 25),
        "humidity": (55, 75),
        "rain_chance": 0.20,
        "rainy_months": [3, 4, 5, 10, 11],
    },
    "Azerbaijan": {
        "date": "2022-06-12",
        "country": "Azerbaijan",
        "climate": "desert",
        "lat": 40.3426,
        "lon": 49.6478,
        "temp_range": (22, 32),
        "humidity": (35, 55),
        "rain_chance": 0.10,
        "rainy_months": [],
    },
    "Canada": {
        "date": "2022-06-19",
        "country": "Canada",
        "climate": "continental",
        "lat": 45.5017,
        "lon": -73.5723,
        "temp_range": (15, 25),
        "humidity": (50, 70),
        "rain_chance": 0.35,
        "rainy_months": [5, 6, 7, 8],
    },
    "Britain": {
        "date": "2022-07-03",
        "country": "UK",
        "climate": "temperate",
        "lat": 52.0786,
        "lon": -1.0169,
        "temp_range": (12, 22),
        "humidity": (55, 80),
        "rain_chance": 0.18,  # Calibrated from 54% to ~25% (mid-summer)
        "rainy_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # UK is rainy!
        "weather_change_probability": 0.45,  # High - British summer is unpredictable
    },
    "Austria": {
        "date": "2022-07-10",
        "country": "Austria",
        "climate": "continental",
        "lat": 47.2197,
        "lon": 14.7647,
        "temp_range": (15, 25),
        "humidity": (50, 70),
        "rain_chance": 0.29,  # Calibrated from 60% to ~30% (mid-summer)
        "rainy_months": [5, 6, 7, 8],
    },
    "France": {
        "date": "2022-07-24",
        "country": "France",
        "climate": "mediterranean",
        "lat": 43.2667,
        "lon": 5.4000,
        "temp_range": (22, 32),
        "humidity": (45, 65),
        "rain_chance": 0.15,
        "rainy_months": [3, 4, 5, 9, 10, 11],
    },
    "Hungary": {
        "date": "2022-07-31",
        "country": "Hungary",
        "climate": "continental",
        "lat": 47.5839,
        "lon": 19.2487,
        "temp_range": (18, 28),
        "humidity": (45, 65),
        "rain_chance": 0.29,  # Calibrated from 60% to ~30% (mid-summer)
        "rainy_months": [5, 6, 7],
    },
    "Belgium": {
        "date": "2022-08-28",
        "country": "Belgium",
        "climate": "temperate",
        "lat": 50.4372,
        "lon": 5.9714,
        "temp_range": (12, 22),
        "humidity": (60, 85),
        "rain_chance": 0.45,
        "rainy_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "weather_change_probability": 0.40,  # High - Spa is famous for weather changes
    },
    "Netherlands": {
        "date": "2022-09-04",
        "country": "Netherlands",
        "climate": "temperate",
        "lat": 52.3874,
        "lon": 4.6465,
        "temp_range": (10, 20),
        "humidity": (65, 85),
        "rain_chance": 0.40,
        "rainy_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "weather_change_probability": 0.35,  # Moderate-high - maritime climate
    },
    "Italy": {
        "date": "2022-09-11",
        "country": "Italy",
        "climate": "mediterranean",
        "lat": 45.6156,
        "lon": 9.2811,
        "temp_range": (15, 25),
        "humidity": (55, 75),
        "rain_chance": 0.15,  # Calibrated from 25% to ~15% (late summer)
        "rainy_months": [3, 4, 5, 9, 10, 11],
    },
    "Singapore": {
        "date": "2022-10-02",
        "country": "Singapore",
        "climate": "tropical",
        "lat": 1.2914,
        "lon": 103.8644,
        "temp_range": (26, 32),
        "humidity": (80, 95),
        "rain_chance": 0.50,
        "rainy_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # Year-round rain
    },
    "Japan": {
        "date": "2022-10-09",
        "country": "Japan",
        "climate": "temperate",
        "lat": 34.8431,
        "lon": 136.5411,
        "temp_range": (15, 25),
        "humidity": (60, 80),
        "rain_chance": 0.35,
        "rainy_months": [6, 7, 8, 9],  # Typhoon season
    },
    "USA": {
        "date": "2022-10-23",
        "country": "USA",
        "climate": "desert",
        "lat": 30.1328,
        "lon": -97.6411,
        "temp_range": (18, 28),
        "humidity": (40, 60),
        "rain_chance": 0.10,
        "rainy_months": [],
    },
    "Mexico": {
        "date": "2022-10-30",
        "country": "Mexico",
        "climate": "desert",
        "lat": 19.4043,
        "lon": -99.0967,
        "temp_range": (15, 25),
        "humidity": (45, 65),
        "rain_chance": 0.15,
        "rainy_months": [5, 6, 7, 8, 9],
    },
    "Brazil": {
        "date": "2022-11-13",
        "country": "Brazil",
        "climate": "tropical",
        "lat": -23.7036,
        "lon": -46.6997,
        "temp_range": (18, 28),
        "humidity": (65, 85),
        "rain_chance": 0.45,
        "rainy_months": [10, 11, 12, 1, 2, 3],  # Brazilian summer/rainy season
    },
    "Abu Dhabi": {
        "date": "2022-11-20",
        "country": "UAE",
        "climate": "desert",
        "lat": 24.4672,
        "lon": 54.6071,
        "temp_range": (22, 32),
        "humidity": (40, 60),
        "rain_chance": 0.05,
        "rainy_months": [],
    },
    "China": {
        "date": "2022-09-25",  # End of September 2022 (manually set)
        "country": "China",
        "climate": "continental",
        "lat": 31.3389,
        "lon": 121.2102,
        "temp_range": (18, 28),
        "humidity": (55, 75),
        "rain_chance": 0.25,
        "rainy_months": [6, 7, 8, 9],
    },
}


def get_track_info(gp_name: str) -> dict:
    """Get track information for a given GP name."""
    # Handle case variations
    gp_name_lower = gp_name.lower()

    for track_name, info in RACE_CALENDAR_2022.items():
        if track_name.lower() == gp_name_lower or gp_name_lower in track_name.lower():
            # Add default weather_change_probability if not present
            if "weather_change_probability" not in info:
                info["weather_change_probability"] = 0.15  # Default moderate chance
            return info

    # Default fallback
    return {
        "date": "2022-11-20",
        "country": "Unknown",
        "climate": "temperate",
        "lat": 0,
        "lon": 0,
        "temp_range": (15, 25),
        "humidity": (50, 70),
        "rain_chance": 0.25,
        "rainy_months": [],
        "weather_change_probability": 0.15,
    }
