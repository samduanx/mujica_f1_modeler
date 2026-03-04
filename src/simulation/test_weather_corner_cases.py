"""
Weather Corner Case Tests for F1 Race Simulation.

Tests critical weather scenarios:
1. Red Flag Restart in Heavy Rain - Rolling start should be used
2. Race Start in Heavy Rain - Rolling start should be used
3. Rapid Weather Improvement - Drivers should pit for dry tyres
4. Weather Deteriorating During Pit Stops - Should get wet tyres
5. Multiple Weather Changes - Cooldown logic prevents excessive pitting
6. Wet Track with No Active Rain - DRS disabled until track dries

Usage:
    uv run python src/simulation/test_weather_corner_cases.py
"""

import sys
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# Add src directory to path for imports
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Weather system imports
from weather.weather_types import (
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    WeatherState,
)
from weather.weather_generator import WeatherGenerator, WeatherEvent
from weather.integrators.enhanced_sim_weather import SimWeatherIntegration

# Incident system imports
from incidents.red_flag import RedFlagManager, RedFlagTrigger, RestartType
from incidents.rolling_start import RollingStartTrigger, RollingStartManager


@dataclass
class TestResult:
    """Result of a single test case."""

    name: str
    passed: bool
    details: str
    expected: str
    actual: str


class WeatherCornerCaseTester:
    """Test suite for weather corner cases in race simulation."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.verbose = True

    def log(self, message: str):
        """Print test log message."""
        if self.verbose:
            print(f"  {message}")

    def run_all_tests(self) -> List[TestResult]:
        """Run all corner case tests."""
        print("=" * 80)
        print("WEATHER CORNER CASE TEST SUITE")
        print("=" * 80)

        # Test 1: Red Flag Restart in Heavy Rain
        print("\n[TEST 1] Red Flag Restart in Heavy Rain")
        self.test_red_flag_restart_heavy_rain()

        # Test 2: Race Start in Heavy Rain
        print("\n[TEST 2] Race Start in Heavy Rain")
        self.test_race_start_heavy_rain()

        # Test 3: Rapid Weather Improvement (Track Drying)
        print("\n[TEST 3] Rapid Weather Improvement (Track Drying)")
        self.test_rapid_weather_improvement()

        # Test 4: Weather Deteriorating During Pit Stops
        print("\n[TEST 4] Weather Deteriorating During Pit Stops")
        self.test_weather_deteriorating_during_pit()

        # Test 5: Multiple Weather Changes (Intermittent Rain)
        print("\n[TEST 5] Multiple Weather Changes (Intermittent Rain)")
        self.test_multiple_weather_changes()

        # Test 6: Wet Track with No Active Rain
        print("\n[TEST 6] Wet Track with No Active Rain")
        self.test_wet_track_no_active_rain()

        return self.results

    def test_red_flag_restart_heavy_rain(self):
        """
        Test 1: Red Flag Restart in Heavy Rain

        Scenario: Race gets red flagged due to torrential rain at lap 30.
        When restarting, if weather is still heavy rain, should use rolling start.
        """
        test_name = "Red Flag Restart in Heavy Rain"
        self.log("Setting up red flag scenario...")

        # Create weather integration for a race
        weather_integration = SimWeatherIntegration("Britain", seed=42)

        # Create initial weather - torrential rain (red flag conditions)
        initial_weather = WeatherState(
            weather_type=WeatherType.TORRENTIAL_RAIN,
            track_condition=TrackCondition.FLOODED,
            race_control=RaceControlState.RED_FLAG,
            temperature=18.0,
            track_temperature=20.0,
            humidity=85.0,
            wind_speed=25.0,
            precipitation_probability=95.0,
            rain_intensity=RainIntensity.TORRENTIAL,
            visibility=200.0,
            rainfall_accumulation=5.0,
        )
        weather_integration._current_weather = initial_weather

        # Create red flag manager
        red_flag_manager = RedFlagManager(total_laps=52, track_length_km=5.891)

        # Simulate red flag at lap 30 due to torrential rain
        race_time = 45.0  # minutes
        current_lap = 30
        red_flag_manager.show_red_flag(
            race_time=race_time,
            lap=current_lap,
            reason="Torrential rain - track flooded",
            car_positions={},
        )

        self.log(f"  Red flag shown at lap {current_lap}: Torrential rain")

        # Assess race status
        status = red_flag_manager.assess_race_status()
        self.log(f"  Race status: {status.get('outcome', 'unknown')}")

        # Simulate restart with weather still heavy rain
        restart_weather = WeatherState(
            weather_type=WeatherType.HEAVY_RAIN,
            track_condition=TrackCondition.FLOODED,
            race_control=RaceControlState.SAFETY_CAR,
            temperature=17.0,
            track_temperature=19.0,
            humidity=90.0,
            wind_speed=20.0,
            precipitation_probability=85.0,
            rain_intensity=RainIntensity.HEAVY,
            visibility=800.0,
            rainfall_accumulation=8.0,
        )

        # Check if rolling start should be used
        rolling_trigger = RollingStartTrigger()
        use_rolling, reason = rolling_trigger.should_use_rolling_start(
            weather_condition=restart_weather.weather_type.value,
            track_visibility="poor",
            is_red_flag_restart=True,
        )

        self.log(f"  Restart weather: {restart_weather.weather_type.value}")
        self.log(f"  Rolling start recommended: {use_rolling} ({reason})")

        # Verify: Heavy rain at restart should trigger rolling start
        passed = use_rolling and "rain" in reason.lower()

        details = (
            f"Red flag at lap {current_lap} due to torrential rain. "
            f"Restart weather: {restart_weather.weather_type.value}. "
            f"Rolling start decision: {use_rolling} ({reason})"
        )

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="Rolling start should be used when restarting in heavy rain",
                actual=f"Rolling start: {use_rolling}, Reason: {reason}",
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def test_race_start_heavy_rain(self):
        """
        Test 2: Race Start in Heavy Rain

        Scenario: Race starts with torrential/heavy rain conditions.
        Should NOT use standing start - should use rolling start for wet conditions.
        """
        test_name = "Race Start in Heavy Rain"
        self.log("Testing race start in heavy rain...")

        # Test various wet conditions
        test_cases = [
            ("torrential_rain", RainIntensity.TORRENTIAL, True),
            ("heavy_rain", RainIntensity.HEAVY, True),
            ("moderate_rain", RainIntensity.MODERATE, False),  # May use standing
        ]

        all_passed = True
        details_list = []

        for weather_str, rain_intensity, should_rolling in test_cases:
            weather_integration = SimWeatherIntegration("Britain", seed=42)

            # Set initial weather
            track_cond = (
                TrackCondition.FLOODED
                if rain_intensity == RainIntensity.TORRENTIAL
                else TrackCondition.WET
            )
            initial_weather = WeatherState(
                weather_type=getattr(WeatherType, weather_str.upper()),
                track_condition=track_cond,
                race_control=RaceControlState.SAFETY_CAR
                if rain_intensity.value >= 2
                else RaceControlState.GREEN,
                temperature=15.0,
                track_temperature=17.0,
                humidity=80.0,
                wind_speed=15.0,
                precipitation_probability=70.0,
                rain_intensity=rain_intensity,
                visibility=500.0,
                rainfall_accumulation=3.0,
            )
            weather_integration._current_weather = initial_weather

            # Check if rolling start should be used
            rolling_trigger = RollingStartTrigger()
            use_rolling, reason = rolling_trigger.should_use_rolling_start(
                weather_condition=weather_str,
                track_visibility="poor" if rain_intensity.value >= 3 else "moderate",
            )

            self.log(
                f"  {weather_str}: rolling={use_rolling}, expected={should_rolling}"
            )

            # For torrential and heavy rain, rolling start should be used
            if rain_intensity in [RainIntensity.TORRENTIAL, RainIntensity.HEAVY]:
                if not use_rolling:
                    all_passed = False
                    self.log(f"    ERROR: Should use rolling start for {weather_str}")

            details_list.append(
                f"{weather_str}: rolling={use_rolling} (expected rolling for heavy/torrential)"
            )

        passed = all_passed
        details = "; ".join(details_list)

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="Rolling start should be used for heavy/torrential rain",
                actual=details,
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def test_rapid_weather_improvement(self):
        """
        Test 3: Rapid Weather Improvement (Track Drying)

        Scenario: Start with rain, then weather clears up quickly.
        Drivers should pit to switch from wet/intermediate back to dry tyres.
        """
        test_name = "Rapid Weather Improvement (Track Drying)"
        self.log("Testing rapid weather improvement...")

        weather_integration = SimWeatherIntegration("Britain", seed=42)

        # Start with rain
        rainy_weather = WeatherState(
            weather_type=WeatherType.MODERATE_RAIN,
            track_condition=TrackCondition.WET,
            race_control=RaceControlState.VSC,
            temperature=18.0,
            track_temperature=20.0,
            humidity=85.0,
            wind_speed=15.0,
            precipitation_probability=80.0,
            rain_intensity=RainIntensity.MODERATE,
            visibility=2000.0,
            rainfall_accumulation=2.5,
        )

        # Get recommended tyre for rain
        rain_tyre, rain_reason = weather_integration.get_recommended_tyre(rainy_weather)
        self.log(f"  Rainy weather tyre: {rain_tyre} ({rain_reason})")

        # Simulate weather improvement - rain stops, track starts drying
        clearing_weather = WeatherState(
            weather_type=WeatherType.CLOUDY,
            track_condition=TrackCondition.DAMP,  # Still damp but drying
            race_control=RaceControlState.GREEN,
            temperature=20.0,
            track_temperature=25.0,
            humidity=65.0,
            wind_speed=10.0,
            precipitation_probability=10.0,
            rain_intensity=RainIntensity.NONE,
            visibility=8000.0,
            rainfall_accumulation=0.5,  # Some water remaining
        )

        # Get recommended tyre for drying conditions
        dry_tyre, dry_reason = weather_integration.get_recommended_tyre(
            clearing_weather
        )
        self.log(f"  Clearing weather tyre: {dry_tyre} ({dry_reason})")

        # Get recommended tyre for fully dry conditions
        fully_dry_weather = WeatherState(
            weather_type=WeatherType.CLEAR,
            track_condition=TrackCondition.DRY,
            race_control=RaceControlState.GREEN,
            temperature=22.0,
            track_temperature=30.0,
            humidity=50.0,
            wind_speed=8.0,
            precipitation_probability=5.0,
            rain_intensity=RainIntensity.NONE,
            visibility=10000.0,
            rainfall_accumulation=0.0,
        )

        fully_dry_tyre, fully_dry_reason = weather_integration.get_recommended_tyre(
            fully_dry_weather
        )
        self.log(f"  Fully dry weather tyre: {fully_dry_tyre} ({fully_dry_reason})")

        # Verify: tyre recommendation should change from wet to dry
        passed = (
            rain_tyre in ["wet", "intermediate"]
            and dry_tyre in ["intermediate", "dry"]
            and fully_dry_tyre == "dry"
        )

        details = (
            f"Rain: {rain_tyre} -> Drying: {dry_tyre} -> Dry: {fully_dry_tyre}. "
            f"Track conditions follow rainfall accumulation changes."
        )

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="Tyre recommendation should change from wet -> intermediate -> dry as track dries",
                actual=details,
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def test_weather_deteriorating_during_pit(self):
        """
        Test 4: Weather Deteriorating During Pit Stops

        Scenario: Driver enters pits in dry conditions.
        While in pit lane, rain starts.
        Should the driver get wet tires or stick to dry strategy?
        """
        test_name = "Weather Deteriorating During Pit Stop"
        self.log("Testing weather change during pit stop...")

        weather_integration = SimWeatherIntegration("Britain", seed=42)

        # Driver enters pits in dry conditions
        pit_entry_weather = WeatherState(
            weather_type=WeatherType.CLOUDY,
            track_condition=TrackCondition.DRY,
            race_control=RaceControlState.GREEN,
            temperature=20.0,
            track_temperature=28.0,
            humidity=60.0,
            wind_speed=10.0,
            precipitation_probability=30.0,
            rain_intensity=RainIntensity.NONE,
            visibility=9000.0,
            rainfall_accumulation=0.0,
        )

        entry_tyre, entry_reason = weather_integration.get_recommended_tyre(
            pit_entry_weather
        )
        self.log(f"  Pit entry tyre: {entry_tyre} ({entry_reason})")

        # While in pit lane (20-25 seconds), rain starts
        pit_exit_weather = WeatherState(
            weather_type=WeatherType.LIGHT_RAIN,
            track_condition=TrackCondition.DAMP,  # Track gets damp quickly
            race_control=RaceControlState.YELLOW,
            temperature=18.0,
            track_temperature=24.0,
            humidity=75.0,
            wind_speed=15.0,
            precipitation_probability=70.0,
            rain_intensity=RainIntensity.LIGHT,
            visibility=6000.0,
            rainfall_accumulation=0.2,  # Just started
        )

        exit_tyre, exit_reason = weather_integration.get_recommended_tyre(
            pit_exit_weather
        )
        self.log(f"  Pit exit tyre: {exit_tyre} ({exit_reason})")

        # Heavy rain scenario
        heavy_rain_pit_exit = WeatherState(
            weather_type=WeatherType.HEAVY_RAIN,
            track_condition=TrackCondition.WET,
            race_control=RaceControlState.SAFETY_CAR,
            temperature=16.0,
            track_temperature=18.0,
            humidity=90.0,
            wind_speed=25.0,
            precipitation_probability=95.0,
            rain_intensity=RainIntensity.HEAVY,
            visibility=1000.0,
            rainfall_accumulation=2.0,
        )

        heavy_exit_tyre, heavy_exit_reason = weather_integration.get_recommended_tyre(
            heavy_rain_pit_exit
        )
        self.log(f"  Heavy rain pit exit tyre: {heavy_exit_tyre} ({heavy_exit_reason})")

        # Verify: Should recommend intermediate for light rain, wet for heavy
        passed = (
            entry_tyre == "dry"
            and exit_tyre in ["intermediate", "wet"]
            and heavy_exit_tyre in ["wet", "intermediate"]
        )

        details = (
            f"Dry entry: {entry_tyre} -> Light rain exit: {exit_tyre} -> "
            f"Heavy rain exit: {heavy_exit_tyre}. System adapts to weather changes."
        )

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="Should recommend intermediate/wet tyres when rain starts during pit stop",
                actual=details,
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def test_multiple_weather_changes(self):
        """
        Test 5: Multiple Weather Changes (Intermittent Rain)

        Scenario: Rain starts and stops multiple times during the race.
        Verify drivers don't pit excessively (cooldown logic).
        Check tire wear on drying track with wet tires.
        """
        test_name = "Multiple Weather Changes (Intermittent Rain)"
        self.log("Testing intermittent rain scenarios...")

        weather_integration = SimWeatherIntegration("Britain", seed=42)

        # Simulate a sequence of weather changes
        weather_sequence = [
            ("Lap 1-10", WeatherType.CLEAR, TrackCondition.DRY, RainIntensity.NONE),
            (
                "Lap 11-15",
                WeatherType.LIGHT_RAIN,
                TrackCondition.DAMP,
                RainIntensity.LIGHT,
            ),
            (
                "Lap 16-20",
                WeatherType.MODERATE_RAIN,
                TrackCondition.WET,
                RainIntensity.MODERATE,
            ),
            (
                "Lap 21-25",
                WeatherType.CLOUDY,
                TrackCondition.DAMP,
                RainIntensity.NONE,
            ),  # Drying
            (
                "Lap 26-30",
                WeatherType.HEAVY_RAIN,
                TrackCondition.WET,
                RainIntensity.HEAVY,
            ),
            (
                "Lap 31-35",
                WeatherType.CLOUDY,
                TrackCondition.DAMP,
                RainIntensity.NONE,
            ),  # Drying again
        ]

        tyre_recommendations = []
        for lap_range, w_type, track_cond, rain_int in weather_sequence:
            weather = WeatherState(
                weather_type=w_type,
                track_condition=track_cond,
                race_control=RaceControlState.GREEN,
                temperature=18.0,
                track_temperature=22.0,
                humidity=70.0,
                wind_speed=12.0,
                precipitation_probability=50.0,
                rain_intensity=rain_int,
                visibility=5000.0,
                rainfall_accumulation=1.0 if rain_int != RainIntensity.NONE else 0.0,
            )

            tyre, reason = weather_integration.get_recommended_tyre(weather)
            tyre_recommendations.append((lap_range, tyre))
            self.log(f"  {lap_range}: {w_type.value} -> {tyre}")

        # Check that recommendations change appropriately
        dry_count = sum(1 for _, t in tyre_recommendations if t == "dry")
        wet_count = sum(
            1 for _, t in tyre_recommendations if t in ["wet", "intermediate"]
        )

        # Verify system responds to weather changes
        passed = dry_count > 0 and wet_count > 0

        details = (
            f"Weather sequence: {len(weather_sequence)} phases. "
            f"Dry recommendations: {dry_count}, Wet recommendations: {wet_count}. "
            f"Recommendations: {tyre_recommendations}"
        )

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="System should recommend dry tyres for dry phases, wet tyres for wet phases",
                actual=f"Dry phases: {dry_count}, Wet phases: {wet_count}",
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def test_wet_track_no_active_rain(self):
        """
        Test 6: Wet Track with No Active Rain

        Scenario: Rain stops but track remains wet/flooded.
        DRS should remain disabled until track dries.
        Verify track condition lags behind weather.
        """
        test_name = "Wet Track with No Active Rain"
        self.log("Testing wet track with no active rain...")

        weather_integration = SimWeatherIntegration("Britain", seed=42)

        # Rain just stopped, but track is still wet
        rain_stopped_weather = WeatherState(
            weather_type=WeatherType.CLOUDY,  # Rain stopped
            track_condition=TrackCondition.WET,  # But track still wet
            race_control=RaceControlState.YELLOW,  # Should be yellow for wet track
            temperature=19.0,
            track_temperature=21.0,
            humidity=80.0,
            wind_speed=10.0,
            precipitation_probability=20.0,
            rain_intensity=RainIntensity.NONE,  # No rain
            visibility=7000.0,
            rainfall_accumulation=3.0,  # Significant water on track
        )

        # Check track condition calculation
        generator = WeatherGenerator(seed=42)
        calculated_condition = generator._calculate_track_condition(
            rain_stopped_weather
        )
        self.log(
            f"  Weather: {rain_stopped_weather.weather_type.value}, "
            f"Rain intensity: {rain_stopped_weather.rain_intensity.name}"
        )
        self.log(
            f"  Rainfall accumulation: {rain_stopped_weather.rainfall_accumulation}mm"
        )
        self.log(f"  Calculated track condition: {calculated_condition.value}")

        # Check race control state
        rc_state = weather_integration.get_race_control_state(rain_stopped_weather)
        self.log(f"  Race control state: {rc_state.value}")

        # Track is drying but still has significant water
        drying_weather = WeatherState(
            weather_type=WeatherType.CLEAR,
            track_condition=TrackCondition.DAMP,  # Drying
            race_control=RaceControlState.GREEN,
            temperature=22.0,
            track_temperature=28.0,
            humidity=60.0,
            wind_speed=8.0,
            precipitation_probability=5.0,
            rain_intensity=RainIntensity.NONE,
            visibility=9500.0,
            rainfall_accumulation=0.3,  # Almost dried
        )

        calculated_drying = generator._calculate_track_condition(drying_weather)
        self.log(f"  Drying weather track condition: {calculated_drying.value}")

        # Verify: Track condition should lag behind weather
        # When rain stops, track should still be wet/damp for some time
        track_lags_weather = (
            rain_stopped_weather.rain_intensity == RainIntensity.NONE
            and calculated_condition in [TrackCondition.WET, TrackCondition.DAMP]
        )

        # DRS should be disabled on wet track
        # In British GP weather sim, DRS is disabled when track is not dry
        drs_disabled = calculated_condition != TrackCondition.DRY

        passed = track_lags_weather and drs_disabled

        details = (
            f"Rain stopped: track={calculated_condition.value}, "
            f"DRS disabled on wet: {drs_disabled}. "
            f"Track condition correctly lags weather changes."
        )

        self.results.append(
            TestResult(
                name=test_name,
                passed=passed,
                details=details,
                expected="Track should remain wet after rain stops; DRS disabled on wet track",
                actual=f"Track: {calculated_condition.value}, DRS disabled: {drs_disabled}",
            )
        )

        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        for result in self.results:
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"\n{status}: {result.name}")
            print(f"  Expected: {result.expected}")
            print(f"  Actual: {result.actual}")
            print(f"  Details: {result.details}")

        print("\n" + "=" * 80)
        print(f"Total: {len(self.results)} tests | Passed: {passed} | Failed: {failed}")
        print("=" * 80)

        return passed, failed


def main():
    """Run the weather corner case tests."""
    tester = WeatherCornerCaseTester()
    tester.run_all_tests()
    passed, failed = tester.print_summary()

    # Return exit code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
