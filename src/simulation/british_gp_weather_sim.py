"""
British GP Weather Simulation Script.

Comprehensive British GP (Silverstone) race simulation with full weather system integration.
This script tests weather impacts on the race including:
- Dynamic weather changes during the race
- Weather-based pit stop strategies
- DRS enable/disable based on conditions
- conditions
- Race Driver performance in wet control responses to weather

Usage:
    uv run python src/simulation/british_gp_weather_sim.py --seed 42 --weather-start clear
    uv run python src/simulation/british_gp_weather_sim.py --seed 42 --weather-start light_rain --weather-chaos --verbose
"""

import argparse
import sys
import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Handle PYTHONPATH for module imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import weather system
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
from weather.integrators.enhanced_sim_weather import (
    SimWeatherIntegration,
    WEATHER_LAP_TIME_IMPACT,
    TRACK_CONDITION_IMPACT,
    WeatherLapData,
    RaceWeatherLog,
)

# Import simulation components
from incidents import (
    IncidentManager,
    IncidentType,
    IncidentSeverity,
    DiceRoller,
    roll_d6,
    roll_d10,
    roll_d100,
)
from drs.driver_state import DriverRaceState
from drs.base_config import TrackDRSConfig, DRSZone
from drs.zones import TRACKS as DRS_TRACKS


# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# British GP Configuration
BRITISH_GP_CONFIG = {
    "gp_name": "Britain",
    "track_name": "Silverstone",
    "laps": 52,
    "base_lap_time": 93.3,  # seconds
    "race_duration_minutes": 120.0,
}

# Tyre compounds for British GP (C1=Hard, C2=Medium, C3=Soft)
TYRE_COMPOUNDS = ["C1", "C2", "C3"]  # Hard, Medium, Soft
TYRE_NAMES = {
    "C1": "HARD",
    "C2": "MEDIUM",
    "C3": "SOFT",
    "INTER": "INTERMEDIATE",
    "WET": "WET",
}

# Driver wet weather performance modifiers
# +5% = specialist, 0% = average, -5% = struggles
WET_WEATHER_MODIFIERS = {
    # Wet weather specialists
    "Verstappen": 0.05,
    "Hamilton": 0.05,
    "Alonso": 0.05,
    "Leclerc": 0.03,
    # Average performers
    "Perez": 0.0,
    "Sainz": 0.0,
    "Russell": 0.0,
    "Norris": 0.0,
    "Ocon": 0.0,
    # Strugglers in wet
    "Stroll": -0.03,
    "Magnussen": -0.03,
    "Tsunoda": -0.02,
    "Latifi": -0.03,
    "Zhou": -0.02,
    # Default
    "default": 0.0,
}

# Team pit strategy aggressiveness (for weather changes)
TEAM_AGGRESSIVENESS = {
    "Red Bull": 0.9,  # Pits early for inters/wets
    "Ferrari": 0.85,  # Aggressive
    "Mercedes": 0.6,  # Conservative
    "McLaren": 0.7,
    "Aston Martin": 0.55,  # Very conservative
    "Alpine": 0.7,
    "Williams": 0.65,
    "AlphaTauri": 0.75,
    "Alfa Romeo": 0.7,
    "Haas": 0.6,
}

# Track base lap times
TRACK_BASE_LAP_TIMES = {
    "silverstone": 93.3,
    "spain": 89.0,
    "monaco": 76.0,
}

# Default lap counts
DEFAULT_LAP_COUNTS = {
    "silverstone": 52,
    "spain": 66,
}


# =============================================================================
# DATA CLASSES FOR WEATHER SIMULATION
# =============================================================================


@dataclass
class DriverState:
    """State of a driver at a point in the race."""

    driver_name: str
    team: str
    position: int
    lap_time: float
    total_time: float
    current_tyre: str
    tyre_age: int
    pit_stops: int = 0
    pit_laps: List[int] = field(default_factory=list)
    wet_weather_modifier: float = 0.0

    # Weather-specific tracking
    last_lap_time_dry: Optional[float] = None
    wet_laps_completed: int = 0

    # DRS state
    drs_enabled: bool = False

    # Performance tracking
    lap_times: List[float] = field(default_factory=list)


@dataclass
class WeatherPitDecision:
    """Record of a pit decision based on weather."""

    lap: int
    driver: str
    team: str
    current_tyre: str
    new_tyre: str
    reason: str  # 'rain_start', 'rain_intensify', 'track_drying', etc.
    weather_state: str
    aggressiveness: float


@dataclass
class DRSEvent:
    """Record of DRS enable/disable events."""

    lap: int
    race_time: float
    enabled: bool
    reason: str  # 'weather', 'race_control', 'safety_car', etc.


@dataclass
class RaceControlEvent:
    """Record of race control state changes."""

    lap: int
    race_time: float
    old_state: RaceControlState
    new_state: RaceControlState
    reason: str


# =============================================================================
# MAIN SIMULATION CLASS
# =============================================================================


class BritishGPWeatherSimulator:
    """
    British GP Weather Simulation with full weather system integration.

    This simulator integrates:
    - SimWeatherIntegration for dynamic weather
    - Weather-based pit stop strategies
    - DRS enable/disable based on conditions
    - Driver-specific wet weather performance
    - Comprehensive race logging and reporting
    """

    # Class-level variable for weather pit stop cooldown tracking
    _weather_pit_cooldowns: Dict[str, int] = {}

    def __init__(
        self,
        seed: int = 42,
        weather_start: str = "clear",
        weather_chaos: bool = False,
        verbose: bool = False,
    ):
        """Initialize the British GP weather simulator."""
        self.seed = seed
        self.weather_start = weather_start
        self.weather_chaos = weather_chaos
        self.verbose = verbose

        # Initialize random seed
        import random

        random.seed(seed)

        # Initialize weather integration
        self.weather_integration = SimWeatherIntegration("Britain", seed=seed)

        # Set initial weather if specified
        if weather_start != "clear":
            self._set_initial_weather(weather_start)

        # Race state
        self.current_lap = 0
        self.current_race_time = 0.0  # minutes
        self.race_control_state = RaceControlState.GREEN
        self.drs_allowed = True

        # Driver states
        self.drivers: Dict[str, DriverState] = {}
        self.driver_order: List[str] = []

        # Initialize drivers (using Spain team data)
        self._initialize_drivers()

        # Event logs
        self.weather_events_log: List[Tuple[int, str, str]] = []
        self.pit_decisions: List[WeatherPitDecision] = []
        self.drs_events: List[DRSEvent] = []
        self.race_control_events: List[RaceControlEvent] = []
        self.lap_logs: List[Dict[str, Any]] = []

        # Track conditions
        self.current_weather: Optional[WeatherState] = None

        # Statistics
        self.stats = {
            "total_pit_stops": 0,
            "weather_pit_stops": 0,
            "dry_laps": 0,
            "wet_laps": 0,
            "drs_enabled_laps": 0,
            "drs_disabled_laps": 0,
            "race_control_changes": 0,
        }

        # Track previous weather for change detection
        self._previous_weather: Optional[WeatherState] = None
        self._previous_rain_intensity: RainIntensity = RainIntensity.NONE

        # Weather pit stop cooldowns (driver name -> lap when last pitted)
        self._weather_pit_cooldowns: Dict[str, int] = {}
        self._weather_pit_cooldown_laps = 5  # Minimum laps between weather pits

    def _set_initial_weather(self, weather_type: str):
        """Set the initial weather to a specific type."""
        weather_map = {
            "clear": WeatherType.CLEAR,
            "light_rain": WeatherType.LIGHT_RAIN,
            "moderate_rain": WeatherType.MODERATE_RAIN,
            "heavy_rain": WeatherType.HEAVY_RAIN,
        }

        wt = weather_map.get(weather_type, WeatherType.CLEAR)

        # Generate initial weather then override
        initial = self.weather_integration.generator.generate_initial_weather("Britain")
        initial.weather_type = wt

        if wt == WeatherType.CLEAR:
            initial.rain_intensity = RainIntensity.NONE
            initial.track_condition = TrackCondition.DRY
        elif wt == WeatherType.LIGHT_RAIN:
            initial.rain_intensity = RainIntensity.LIGHT
            initial.track_condition = TrackCondition.DAMP
        elif wt == WeatherType.MODERATE_RAIN:
            initial.rain_intensity = RainIntensity.MODERATE
            initial.track_condition = TrackCondition.WET
        elif wt == WeatherType.HEAVY_RAIN:
            initial.rain_intensity = RainIntensity.HEAVY
            initial.track_condition = TrackCondition.FLOODED

        self.weather_integration._current_weather = initial

    def _generate_weather_chaos_events(self):
        """Generate random weather events when weather chaos mode is enabled."""
        import random

        # Number of random weather events (2-5 events during the race)
        num_events = random.randint(2, 5)

        # Generate random event times (in minutes)
        race_duration = BRITISH_GP_CONFIG["race_duration_minutes"]
        event_times = sorted(
            [random.uniform(10, race_duration - 10) for _ in range(num_events)]
        )

        for event_time in event_times:
            # Determine event type
            event_types = [
                ("rain_start", 0.4),
                ("rain_intensify", 0.2),
                ("rain_weaken", 0.2),
                ("rain_stop", 0.2),
            ]
            event_type = random.choices(
                [t[0] for t in event_types], weights=[t[1] for t in event_types]
            )[0]

            # Create weather event
            event = WeatherEvent(
                timestamp=event_time,
                event_type=event_type,
                intensity=random.random(),
                duration=random.uniform(5, 30),
                description=f"Chaos mode: {event_type}",
            )
            self.weather_integration._weather_events.append(event)

        # Re-sort events by timestamp
        self.weather_integration._weather_events.sort(key=lambda e: e.timestamp)

        if self.verbose:
            print(
                f"  Generated {num_events} random weather events (weather chaos mode)"
            )

    def _is_weather_deteriorating(
        self, prev: WeatherState, current: WeatherState
    ) -> bool:
        """Check if weather is deteriorating (e.g., clear → rain)."""
        # Check for rain starting
        if prev.rain_intensity == RainIntensity.NONE and current.rain_intensity in [
            RainIntensity.LIGHT,
            RainIntensity.MODERATE,
            RainIntensity.HEAVY,
            RainIntensity.TORRENTIAL,
        ]:
            return True
        # Check for rain intensifying
        rain_order = [
            RainIntensity.NONE,
            RainIntensity.LIGHT,
            RainIntensity.MODERATE,
            RainIntensity.HEAVY,
            RainIntensity.TORRENTIAL,
        ]
        prev_idx = rain_order.index(prev.rain_intensity)
        curr_idx = rain_order.index(current.rain_intensity)
        return curr_idx > prev_idx + 1  # Significant jump (e.g., light → moderate)

    def _deploy_vsc_for_weather_change(self, lap: int):
        """Deploy VSC when weather deteriorates significantly."""
        old_state = self.race_control_state

        # Determine appropriate response based on weather severity
        if self.current_weather.rain_intensity in [
            RainIntensity.HEAVY,
            RainIntensity.TORRENTIAL,
        ]:
            new_state = RaceControlState.SAFETY_CAR
        else:
            new_state = RaceControlState.VSC

        if new_state != old_state:
            self.race_control_state = new_state
            self.race_control_events.append(
                RaceControlEvent(
                    lap=lap,
                    race_time=self.current_race_time,
                    old_state=old_state,
                    new_state=new_state,
                    reason=f"Weather deterioration: {self.current_weather.weather_type.value}",
                )
            )
            self.stats["race_control_changes"] += 1

            if self.verbose:
                print(
                    f"  *** {new_state.value.upper()} DEPLOYED due to weather change ***"
                )

    def _check_pit_for_weather(
        self,
        driver: str,
        driver_state: DriverState,
        new_tyre: str,
        weather: WeatherState,
        current_lap: int,
    ) -> Tuple[bool, str]:
        """
        Check if a driver should pit for weather with cooldown logic.

        Returns:
            Tuple of (should_pit, reason)
        """
        current_tyre = driver_state.current_tyre

        # Don't pit if already on correct tires
        if current_tyre == new_tyre:
            return False, "already_on_correct_tyre"

        # Check cooldown period (5 laps between weather-triggered pit stops)
        last_pit_lap = self._weather_pit_cooldowns.get(driver, 0)
        if current_lap - last_pit_lap < self._weather_pit_cooldown_laps:
            return False, "pit_cooldown"

        # Check if driver is already on a suitable wet weather tyre
        if current_tyre in ["INTER", "WET"]:
            # If already on inters and recommended is also inters, don't pit
            if current_tyre == "INTER" and new_tyre == "INTER":
                return False, "maintaining_intermediates"
            # If already on wets and wets are recommended, don't pit
            if current_tyre == "WET" and new_tyre == "WET":
                return False, "maintaining_wets"

        # Use the existing should_pit_for_weather logic for the actual decision
        return self.should_pit_for_weather(driver, current_tyre, new_tyre, weather)

    def _initialize_drivers(self):
        """Initialize driver states using Spain team data."""
        # Read driver data from spain_team.csv
        import csv

        driver_data = {}
        try:
            with open("data/spain_team.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    team = row.get("Teams", "").strip()
                    if team:
                        # Extract driver name from team or use default drivers
                        driver_data[team] = {
                            "Team": team,
                        }
        except FileNotFoundError:
            print("Warning: spain_team.csv not found, using default drivers")

        # Default driver assignments (based on 2024 F1 grid)
        default_drivers = [
            ("Verstappen", "Red Bull"),
            ("Perez", "Red Bull"),
            ("Leclerc", "Ferrari"),
            ("Sainz", "Ferrari"),
            ("Hamilton", "Mercedes"),
            ("Russell", "Mercedes"),
            ("Norris", "McLaren"),
            ("Piastri", "McLaren"),
            ("Alonso", "Aston Martin"),
            ("Stroll", "Aston Martin"),
            ("Ocon", "Alpine"),
            ("Gasly", "Alpine"),
            ("Albon", "Williams"),
            ("Colapinto", "Williams"),
            ("Tsunoda", "AlphaTauri"),
            ("Lawson", "AlphaTauri"),
            ("Bottas", "Alfa Romeo"),
            ("Zhou", "Alfa Romeo"),
            ("Magnussen", "Haas"),
            ("Bearman", "Haas"),
        ]

        # Create driver states
        position = 1
        for driver, team in default_drivers:
            wet_modifier = WET_WEATHER_MODIFIERS.get(
                driver, WET_WEATHER_MODIFIERS["default"]
            )

            # Base lap time varies by team (simplified)
            base_time = BRITISH_GP_CONFIG["base_lap_time"]

            self.drivers[driver] = DriverState(
                driver_name=driver,
                team=team,
                position=position,
                lap_time=base_time,
                total_time=0.0,
                current_tyre="C2",  # Start on medium (common choice for Silverstone)
                tyre_age=0,
                wet_weather_modifier=wet_modifier,
            )
            self.driver_order.append(driver)
            position += 1

    def get_tyre_for_conditions(self, weather: WeatherState) -> str:
        """
        Determine the appropriate tyre compound based on conditions.

        Returns:
            Tyre compound string (C1, C2, C3, INTER, WET)
        """
        rain_intensity = weather.rain_intensity
        track_condition = weather.track_condition

        if (
            rain_intensity == RainIntensity.NONE
            or rain_intensity == RainIntensity.LIGHT
        ):
            if track_condition == TrackCondition.DRY:
                return "C2"  # Medium - good for Silverstone
            elif track_condition == TrackCondition.DAMP:
                return "INTER"
        elif rain_intensity == RainIntensity.MODERATE:
            return "INTER"
        elif (
            rain_intensity == RainIntensity.HEAVY
            or rain_intensity == RainIntensity.TORRENTIAL
        ):
            return "WET"

        return "C2"  # Default

    def should_pit_for_weather(
        self,
        driver: str,
        current_tyre: str,
        new_tyre: str,
        weather: WeatherState,
    ) -> Tuple[bool, str]:
        """
        Determine if a driver should pit based on weather conditions.

        Args:
            driver: Driver name
            current_tyre: Current tyre compound
            new_tyre: Recommended tyre
            weather: Current weather state

        Returns:
            Tuple of (should_pit, reason)
        """
        if current_tyre == new_tyre:
            return False, "same_tyre"

        team = self.drivers[driver].team
        aggressiveness = TEAM_AGGRESSIVENESS.get(team, 0.7)

        rain_intensity = weather.rain_intensity
        track_condition = weather.track_condition

        # Check if we need to switch to wet tires
        if new_tyre == "WET":
            if (
                rain_intensity == RainIntensity.HEAVY
                or rain_intensity == RainIntensity.TORRENTIAL
            ):
                # Must pit - heavy rain
                return True, "heavy_rain"
            elif rain_intensity == RainIntensity.MODERATE:
                # Check team aggressiveness
                if random.random() < aggressiveness:
                    return True, "moderate_rain_aggressive"
                return False, "wait_for_heavier"

        elif new_tyre == "INTER":
            if (
                track_condition == TrackCondition.WET
                or track_condition == TrackCondition.FLOODED
            ):
                if random.random() < aggressiveness:
                    return True, "wet_track_inter"
            elif rain_intensity == RainIntensity.LIGHT:
                if random.random() < (aggressiveness * 0.5):
                    return True, "light_rain_inter"

        # Check if drying conditions - could switch back to slicks
        if current_tyre in ["INTER", "WET"]:
            if (
                rain_intensity == RainIntensity.NONE
                and track_condition == TrackCondition.DRY
            ):
                if random.random() < (aggressiveness * 0.6):
                    return True, "track_drying"

        return False, "no_need"

    def calculate_lap_time(
        self,
        driver: str,
        base_lap_time: float,
        weather: WeatherState,
        race_control: RaceControlState,
    ) -> float:
        """
        Calculate lap time with all modifiers.

        Args:
            driver: Driver name
            base_lap_time: Base lap time in seconds
            weather: Current weather state
            race_control: Current race control state

        Returns:
            Actual lap time in seconds
        """
        # Get weather modifier from integration
        weather_modifier = self.weather_integration.get_lap_time_modifier(weather)

        # Get driver wet weather modifier
        driver_state = self.drivers[driver]
        wet_modifier = driver_state.wet_weather_modifier

        # Check if rainy conditions
        is_rainy = weather.rain_intensity not in [
            RainIntensity.NONE,
            RainIntensity.LIGHT,
        ]

        # Apply wet weather modifier (positive = slower)
        if is_rainy:
            weather_modifier += wet_modifier

        # Race control modifier
        rc_modifier = 0.0
        if race_control == RaceControlState.VSC:
            rc_modifier = 0.30  # ~30% slower under VSC
        elif race_control == RaceControlState.SAFETY_CAR:
            rc_modifier = 0.50  # ~50% slower under SC
        elif race_control == RaceControlState.RED_FLAG:
            rc_modifier = 1.0  # Race stopped
        elif race_control == RaceControlState.YELLOW:
            rc_modifier = 0.05
        elif race_control == RaceControlState.DOUBLE_YELLOW:
            rc_modifier = 0.10

        # Calculate final lap time
        lap_time = base_lap_time * (1 + weather_modifier + rc_modifier)

        # Add some randomness
        import random

        lap_time *= random.uniform(0.98, 1.02)

        return lap_time

    def update_drs_state(
        self, weather: WeatherState, race_control: RaceControlState
    ) -> bool:
        """
        Update DRS allowed state based on conditions.

        Returns:
            True if DRS is allowed, False otherwise
        """
        # DRS disabled conditions
        if race_control != RaceControlState.GREEN:
            return False

        if weather.rain_intensity in [
            RainIntensity.MODERATE,
            RainIntensity.HEAVY,
            RainIntensity.TORRENTIAL,
        ]:
            return False

        if weather.track_condition in [TrackCondition.WET, TrackCondition.FLOODED]:
            return False

        return True

    def update_race_control(self, weather: WeatherState) -> Optional[RaceControlState]:
        """
        Update race control state based on weather conditions.

        Returns:
            New race control state if changed, None otherwise
        """
        old_state = self.race_control_state

        # Determine new state based on weather
        if weather.rain_intensity == RainIntensity.TORRENTIAL:
            new_state = RaceControlState.RED_FLAG
        elif weather.rain_intensity == RainIntensity.HEAVY:
            if self.race_control_state == RaceControlState.GREEN:
                new_state = RaceControlState.SAFETY_CAR
            else:
                new_state = self.race_control_state
        elif weather.rain_intensity == RainIntensity.MODERATE:
            if self.race_control_state == RaceControlState.GREEN:
                new_state = RaceControlState.VSC
            else:
                new_state = self.race_control_state
        elif weather.track_condition == TrackCondition.FLOODED:
            new_state = RaceControlState.RED_FLAG
        else:
            # Gradually return to green if conditions improve
            if self.race_control_state in [
                RaceControlState.VSC,
                RaceControlState.SAFETY_CAR,
            ]:
                if weather.rain_intensity in [RainIntensity.NONE, RainIntensity.LIGHT]:
                    new_state = RaceControlState.GREEN
                else:
                    new_state = self.race_control_state
            else:
                new_state = RaceControlState.GREEN

        # Update state if changed
        if new_state != old_state:
            self.race_control_state = new_state

            # Log event
            self.race_control_events.append(
                RaceControlEvent(
                    lap=self.current_lap,
                    race_time=self.current_race_time,
                    old_state=old_state,
                    new_state=new_state,
                    reason=f"Weather: {weather.weather_type.value}",
                )
            )
            self.stats["race_control_changes"] += 1

            return new_state

        return None

    def run_race(self) -> Dict[str, Any]:
        """
        Run the complete British GP race simulation.

        Returns:
            Race results and statistics
        """
        total_laps = BRITISH_GP_CONFIG["laps"]
        base_lap_time = BRITISH_GP_CONFIG["base_lap_time"]

        if self.verbose:
            print(f"\n{'=' * 60}")
            print(f"BRITISH GP WEATHER SIMULATION")
            print(f"{'=' * 60}")
            print(f"Seed: {self.seed}")
            print(f"Initial Weather: {self.weather_start}")
            print(f"Weather Chaos: {self.weather_chaos}")
            print(f"Total Laps: {total_laps}")
            print(f"{'=' * 60}\n")

        # Initialize weather for race
        self.weather_integration.initialize_race(
            race_duration=BRITISH_GP_CONFIG["race_duration_minutes"]
        )

        # Re-apply initial weather override if specified (since initialize_race resets it)
        if self.weather_start != "clear":
            self._set_initial_weather(self.weather_start)

        # Initialize weather chaos if enabled - generate random weather events
        if self.weather_chaos:
            self._generate_weather_chaos_events()

        # Store initial race control state for change detection
        self._previous_rain_intensity = (
            self.weather_integration._current_weather.rain_intensity
        )

        # Race loop
        for lap in range(1, total_laps + 1):
            self.current_lap = lap

            # Calculate race time in minutes (average lap time)
            avg_lap_time_seconds = base_lap_time / 60.0
            self.current_race_time = lap * avg_lap_time_seconds

            # Get current weather
            self.current_weather = self.weather_integration.get_current_weather(
                lap=lap, race_time=self.current_race_time
            )

            # Log weather if it changed
            if lap == 1:
                self.weather_events_log.append(
                    (
                        lap,
                        "race_start",
                        f"Race start - {self.current_weather.weather_type.value}, "
                        f"rain: {self.current_weather.rain_intensity.name}, "
                        f"track: {self.current_weather.track_condition.value}",
                    )
                )
            else:
                # Check for weather changes by comparing to previous lap
                prev_weather = self.weather_integration.get_current_weather(
                    lap=lap - 1, race_time=self.current_race_time - avg_lap_time_seconds
                )
                if prev_weather.weather_type != self.current_weather.weather_type:
                    self.weather_events_log.append(
                        (
                            lap,
                            "weather_change",
                            f"Lap {lap} - {prev_weather.weather_type.value} → "
                            f"{self.current_weather.weather_type.value}",
                        )
                    )
                    # Check for significant weather deterioration
                    if self._is_weather_deteriorating(
                        prev_weather, self.current_weather
                    ):
                        self._deploy_vsc_for_weather_change(lap)

            # Check for rain intensity changes that need VSC
            current_rain = self.current_weather.rain_intensity
            if current_rain != self._previous_rain_intensity and current_rain in [
                RainIntensity.MODERATE,
                RainIntensity.HEAVY,
            ]:
                if self.race_control_state == RaceControlState.GREEN:
                    self._deploy_vsc_for_weather_change(lap)
            self._previous_rain_intensity = current_rain

            # Update race control state
            self.update_race_control(self.current_weather)

            # Update DRS state
            new_drs_allowed = self.update_drs_state(
                self.current_weather, self.race_control_state
            )
            if new_drs_allowed != self.drs_allowed:
                reason = "weather_improved" if new_drs_allowed else "weather_worsened"
                if self.race_control_state != RaceControlState.GREEN:
                    reason = f"race_control_{self.race_control_state.value}"
                self.drs_events.append(
                    DRSEvent(
                        lap=lap,
                        race_time=self.current_race_time,
                        enabled=new_drs_allowed,
                        reason=reason,
                    )
                )
                self.drs_allowed = new_drs_allowed

            # Determine recommended tyre
            recommended_tyre = self.get_tyre_for_conditions(self.current_weather)

            # Track wet/dry laps
            if self.current_weather.track_condition == TrackCondition.DRY:
                self.stats["dry_laps"] += 1
            else:
                self.stats["wet_laps"] += 1

            if self.drs_allowed:
                self.stats["drs_enabled_laps"] += 1
            else:
                self.stats["drs_disabled_laps"] += 1

            # Process each driver
            lap_results = {}
            for driver in self.driver_order:
                driver_state = self.drivers[driver]

                # Calculate lap time
                lap_time = self.calculate_lap_time(
                    driver, base_lap_time, self.current_weather, self.race_control_state
                )

                # Store dry lap time for comparison
                if self.current_weather.track_condition == TrackCondition.DRY:
                    driver_state.last_lap_time_dry = lap_time
                elif self.current_weather.track_condition != TrackCondition.DRY:
                    driver_state.wet_laps_completed += 1

                # Check for weather-based pit decision (with cooldown)
                should_pit, pit_reason = self._check_pit_for_weather(
                    driver,
                    driver_state,
                    recommended_tyre,
                    self.current_weather,
                    lap,
                )

                if should_pit:
                    # Record pit stop time for cooldown
                    self._weather_pit_cooldowns[driver] = lap
                    # Save old tyre before changing
                    old_tyre = driver_state.current_tyre
                    # Execute pit stop
                    pit_time = 22.0  # Average pit stop time
                    lap_time += pit_time
                    driver_state.pit_stops += 1
                    driver_state.pit_laps.append(lap)
                    driver_state.current_tyre = recommended_tyre
                    driver_state.tyre_age = 0
                    self.stats["total_pit_stops"] += 1
                    self.stats["weather_pit_stops"] += 1

                    # Log pit decision (using old_tyre for "From" field)
                    self.pit_decisions.append(
                        WeatherPitDecision(
                            lap=lap,
                            driver=driver,
                            team=driver_state.team,
                            current_tyre=old_tyre,
                            new_tyre=recommended_tyre,
                            reason=pit_reason,
                            weather_state=self.current_weather.weather_type.value,
                            aggressiveness=TEAM_AGGRESSIVENESS.get(
                                driver_state.team, 0.7
                            ),
                        )
                    )

                # Update driver state
                driver_state.lap_time = lap_time
                driver_state.total_time += lap_time
                driver_state.tyre_age += 1
                driver_state.lap_times.append(lap_time)
                driver_state.drs_enabled = self.drs_allowed

                lap_results[driver] = lap_time

            # Sort drivers by total time
            self.driver_order.sort(key=lambda d: self.drivers[d].total_time)

            # Update positions
            for pos, driver in enumerate(self.driver_order, 1):
                self.drivers[driver].position = pos

            # Log lap results
            if self.verbose:
                self._log_lap_results(lap, lap_results)

        if self.verbose:
            print(f"\n{'=' * 60}")
            print("RACE COMPLETE")
            print(f"{'=' * 60}\n")

        return self._generate_results()

    def _log_lap_results(self, lap: int, lap_results: Dict[str, float]):
        """Log lap results for a single lap."""
        if self.current_weather is None:
            weather_desc = "Unknown"
        else:
            weather_desc = f"{self.current_weather.weather_type.value}"
            if self.current_weather.rain_intensity != RainIntensity.NONE:
                weather_desc += f" ({self.current_weather.rain_intensity.name})"

        rc_desc = self.race_control_state.value
        drs_desc = "DRS ON" if self.drs_allowed else "DRS OFF"

        print(
            f"Lap {lap:2d} | Weather: {weather_desc:20s} | RC: {rc_desc:12s} | {drs_desc}"
        )

        # Show top 3 lap times
        sorted_times = sorted(lap_results.items(), key=lambda x: x[1])[:3]
        for driver, time in sorted_times:
            print(f"       {driver:12s}: {time:.3f}s")

    def _generate_results(self) -> Dict[str, Any]:
        """Generate final race results."""
        # Sort by final position
        final_order = sorted(
            self.driver_order, key=lambda d: self.drivers[d].total_time
        )

        results = {
            "gp_name": "Britain",
            "track": "Silverstone",
            "laps": BRITISH_GP_CONFIG["laps"],
            "total_time_seconds": self.drivers[final_order[0]].total_time
            if final_order
            else 0,
            "positions": [],
            "pit_stops": [],
            "weather_events": self.weather_events_log,
            "pit_decisions": self.pit_decisions,
            "drs_events": self.drs_events,
            "race_control_events": self.race_control_events,
            "stats": self.stats,
            "seed": self.seed,
            "initial_weather": self.weather_start,
        }

        # Add position data
        for driver in final_order:
            ds = self.drivers[driver]
            results["positions"].append(
                {
                    "position": ds.position,
                    "driver": driver,
                    "team": ds.team,
                    "total_time": ds.total_time,
                    "gap": ds.total_time - self.drivers[final_order[0]].total_time
                    if final_order
                    else 0,
                    "pit_stops": ds.pit_stops,
                    "pit_laps": ds.pit_laps,
                    "final_tyre": ds.current_tyre,
                    "wet_laps": ds.wet_laps_completed,
                    "wet_modifier": ds.wet_weather_modifier,
                }
            )

        return results


# =============================================================================
# REPORT GENERATION
# =============================================================================


def generate_race_report(results: Dict[str, Any]) -> str:
    """Generate a markdown race report."""
    from datetime import datetime

    lines = []

    # Header
    lines.append("# F1 British GP 2024 Weather Simulation Report")
    lines.append("")
    lines.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"**Seed:** {results['seed']}")
    lines.append(f"**Initial Weather:** {results['initial_weather']}")
    lines.append("")

    # Race Summary
    lines.append("## 🏁 Race Summary")
    lines.append("")
    lines.append(f"- **Track:** {results['track']}")
    lines.append(f"- **Laps:** {results['laps']}")
    lines.append(
        f"- **Total Race Time:** {results['total_time_seconds']:.1f}s ({results['total_time_seconds'] / 60:.1f}min)"
    )
    lines.append("")

    # Weather Impact Statistics
    lines.append("## 🌧️ Weather Impact Statistics")
    lines.append("")
    stats = results["stats"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Dry Laps | {stats['dry_laps']} |")
    lines.append(f"| Wet Laps | {stats['wet_laps']} |")
    lines.append(f"| DRS Enabled Laps | {stats['drs_enabled_laps']} |")
    lines.append(f"| DRS Disabled Laps | {stats['drs_disabled_laps']} |")
    lines.append(f"| Race Control Changes | {stats['race_control_changes']} |")
    lines.append("")

    # Race Results
    lines.append("## 🏆 Race Results")
    lines.append("")
    lines.append("| Pos | Driver | Team | Total Time | Gap | Pit Stops | Final Tyre |")
    lines.append("|-----|--------|------|------------|-----|-----------|------------|")

    for p in results["positions"]:
        gap_str = f"+{p['gap']:.3f}s" if p["gap"] > 0 else "WINNER"
        lines.append(
            f"| {p['position']:2d} | {p['driver']:12s} | {p['team']:15s} | "
            f"{p['total_time']:8.1f}s | {gap_str:10s} | {p['pit_stops']:3d} | {p['final_tyre']:5s} |"
        )
    lines.append("")

    # Weather Events
    lines.append("## 🌦️ Weather Events")
    lines.append("")
    if results["weather_events"]:
        lines.append("| Lap | Event Type | Description |")
        lines.append("|-----|------------|-------------|")
        for lap, event_type, desc in results["weather_events"]:
            lines.append(f"| {lap} | {event_type} | {desc} |")
    else:
        lines.append("No weather changes during the race.")
    lines.append("")

    # Weather-Based Pit Stops
    lines.append("## 🛠️ Weather-Based Pit Stops")
    lines.append("")
    if results["pit_decisions"]:
        lines.append("| Lap | Driver | Team | From | To | Reason |")
        lines.append("|-----|--------|------|------|-----|--------|")
        for pd in results["pit_decisions"]:
            lines.append(
                f"| {pd.lap} | {pd.driver:12s} | {pd.team:15s} | "
                f"{pd.current_tyre:5s} | {pd.new_tyre:5s} | {pd.reason} |"
            )
    else:
        lines.append("No weather-based pit stops.")
    lines.append("")

    # DRS Events
    lines.append("## 💨 DRS Usage Events")
    lines.append("")
    if results["drs_events"]:
        lines.append("| Lap | Time (min) | Status | Reason |")
        lines.append("|-----|------------|--------|--------|")
        for de in results["drs_events"]:
            status = "ENABLED" if de.enabled else "DISABLED"
            lines.append(
                f"| {de.lap} | {de.race_time:6.1f} | {status:8s} | {de.reason} |"
            )
    else:
        lines.append("No DRS state changes during the race.")
    lines.append("")

    # Race Control Events
    lines.append("## 🚩 Race Control State Changes")
    lines.append("")
    if results["race_control_events"]:
        lines.append("| Lap | Time (min) | From | To | Reason |")
        lines.append("|-----|------------|------|-----|--------|")
        for rc in results["race_control_events"]:
            lines.append(
                f"| {rc.lap} | {rc.race_time:6.1f} | "
                f"{rc.old_state.value:12s} | {rc.new_state.value:12s} | {rc.reason} |"
            )
    else:
        lines.append("No race control state changes.")
    lines.append("")

    # Driver Wet Weather Performance
    lines.append("## 🌧️ Driver Wet Weather Performance")
    lines.append("")
    lines.append("| Driver | Team | Wet Laps | Wet Modifier |")
    lines.append("|--------|------|----------|--------------|")
    for p in results["positions"]:
        driver = p["driver"]
        modifier = p.get("wet_modifier", 0.0)
        tier = (
            "Specialist"
            if modifier >= 0.04
            else "Struggler"
            if modifier < 0
            else "Average"
        )
        lines.append(
            f"| {driver:12s} | {p['team']:15s} | {p['wet_laps']:8d} | "
            f"{modifier:+.1%} ({tier}) |"
        )
    lines.append("")

    # Analysis
    lines.append("## 📊 Weather Impact Analysis")
    lines.append("")

    dry_laps = stats["dry_laps"]
    wet_laps = stats["wet_laps"]
    total_laps = dry_laps + wet_laps

    if wet_laps > 0:
        lines.append(f"- **Wet Race Percentage:** {wet_laps / total_laps * 100:.1f}%")
        lines.append(
            f"- **Weather Impact:** Significant weather changes affected {wet_laps} laps"
        )
        lines.append("")
        lines.append("### Key Observations:")

        # Analyze pit strategies
        aggressive_teams = sum(
            1 for pd in results["pit_decisions"] if pd.aggressiveness > 0.75
        )
        conservative_teams = sum(
            1 for pd in results["pit_decisions"] if pd.aggressiveness < 0.65
        )

        lines.append(f"- **Aggressive pit responses:** {aggressive_teams}")
        lines.append(f"- **Conservative pit responses:** {conservative_teams}")

        # DRS analysis
        drs_off_pct = (
            stats["drs_disabled_laps"] / total_laps * 100 if total_laps > 0 else 0
        )
        lines.append(f"- **DRS unavailable:** {drs_off_pct:.1f}% of race laps")
    else:
        lines.append("- **Weather Impact:** Dry race with no precipitation")

    lines.append("")
    lines.append("---")
    lines.append("*Report generated by F1 British GP Weather Simulation System*")

    return "\n".join(lines)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for the simulation."""
    parser = argparse.ArgumentParser(description="British GP Weather Simulation")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--weather-start",
        type=str,
        default="clear",
        choices=["clear", "light_rain", "moderate_rain", "heavy_rain"],
        help="Initial weather condition",
    )
    parser.add_argument(
        "--weather-chaos",
        action="store_true",
        help="Enable random weather changes during race",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed lap-by-lap output"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/reports/british_gp_weather_race_report.md",
        help="Output file path",
    )

    args = parser.parse_args()

    # Create output directory if needed
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Run simulation
    simulator = BritishGPWeatherSimulator(
        seed=args.seed,
        weather_start=args.weather_start,
        weather_chaos=args.weather_chaos,
        verbose=args.verbose,
    )

    print(f"Starting British GP Weather Simulation...")
    print(f"  Seed: {args.seed}")
    print(f"  Initial Weather: {args.weather_start}")
    print(f"  Weather Chaos: {args.weather_chaos}")
    print()

    results = simulator.run_race()

    # Generate and save report
    report = generate_race_report(results)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nRace report saved to: {args.output}")
    print(f"\nSimulation complete!")
    print(
        f"  Winner: {results['positions'][0]['driver']} ({results['positions'][0]['team']})"
    )
    print(f"  Total Time: {results['positions'][0]['total_time']:.1f}s")
    print(f"  Weather Pit Stops: {results['stats']['weather_pit_stops']}")
    print(f"  Race Control Changes: {results['stats']['race_control_changes']}")


if __name__ == "__main__":
    main()
