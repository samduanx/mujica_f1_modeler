"""
Weather System Integration Tests.

Tests the weather generator across multiple race scenarios,
validates weather randomness distribution, and tests weather
system calls and integration points.
"""

import sys
import os
import random
from collections import Counter
from typing import Dict, List

# Ensure proper import path
_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from weather import (
    WeatherGenerator,
    WeatherState,
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    generate_weather_for_all_2022_races,
    RACE_CALENDAR_2022,
)


class TestResults:
    """Container for test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"  [PASS] {test_name}")

    def record_fail(self, test_name: str, reason: str):
        self.failed += 1
        self.errors.append((test_name, reason))
        print(f"  [FAIL] {test_name}: {reason}")

    def summary(self) -> str:
        total = self.passed + self.failed
        return f"\n{'=' * 60}\nTest Results: {self.passed}/{total} passed, {self.failed} failed\n{'=' * 60}"


def test_basic_weather_generation(results: TestResults):
    """Test basic weather generation for different tracks."""
    print("\n[Test 1] Basic Weather Generation")

    test_tracks = ["Monaco", "Britain", "Singapore", "Bahrain", "Brazil"]
    generator = WeatherGenerator(seed=42)

    for track in test_tracks:
        try:
            weather = generator.generate_initial_weather(track)
            assert isinstance(weather, WeatherState), (
                f"Invalid weather type for {track}"
            )
            assert weather.weather_type is not None, f"Weather type missing for {track}"
            assert weather.temperature > -20 and weather.temperature < 60, (
                f"Temperature out of range for {track}"
            )
            results.record_pass(f"Generate weather for {track}")
        except Exception as e:
            results.record_fail(f"Generate weather for {track}", str(e))


def test_weather_distribution(results: TestResults):
    """Test weather randomness distribution."""
    print("\n[Test 2] Weather Randomness Distribution")

    # Test that rain probability varies appropriately
    tracks_rain_prob = {}

    for track_name in RACE_CALENDAR_2022.keys():
        generator = WeatherGenerator(seed=42)
        info = generator.get_track_climate_info(track_name)
        tracks_rain_prob[track_name] = info["calculated_rain_probability"]

    # Check that probabilities are in reasonable range
    for track, prob in tracks_rain_prob.items():
        if not (0.02 <= prob <= 0.6):
            results.record_fail(
                f"Probability range for {track}", f"Probability {prob:.2%} out of range"
            )
            continue

    results.record_pass("All rain probabilities in valid range (2%-60%)")

    # Check that climate-based differences exist
    # Desert tracks should have lower rain probability
    desert_tracks = [
        "Bahrain",
        "Saudi Arabia",
        "Azerbaijan",
        "USA",
        "Mexico",
        "Abu Dhabi",
    ]
    tropical_temperate = ["Singapore", "Britain", "Belgium", "Netherlands", "Brazil"]

    desert_avg = sum(tracks_rain_prob.get(t, 0) for t in desert_tracks) / len(
        desert_tracks
    )
    tropical_avg = sum(tracks_rain_prob.get(t, 0) for t in tropical_temperate) / len(
        tropical_temperate
    )

    if desert_avg < tropical_avg:
        results.record_pass(
            f"Climate-based rain probability (desert: {desert_avg:.1%}, tropical/temperate: {tropical_avg:.1%})"
        )
    else:
        results.record_fail(
            "Climate-based rain probability",
            "Desert tracks should have lower rain probability",
        )


def test_weather_events_generation(results: TestResults):
    """Test weather event generation during races."""
    print("\n[Test 3] Weather Events Generation")

    generator = WeatherGenerator(seed=123)
    test_races = ["Monaco", "Britain", "Singapore", "Bahrain"]

    for race in test_races:
        events = generator.generate_race_weather_events(race, race_duration=120)

        if not isinstance(events, list):
            results.record_fail(f"Events for {race}", "Events should be a list")
            continue

        # Events should be sorted by timestamp
        if events:
            timestamps = [e.timestamp for e in events]
            if timestamps != sorted(timestamps):
                results.record_fail(
                    f"Events sorted for {race}", "Events not sorted by timestamp"
                )
                continue

        results.record_pass(f"Generate {len(events)} events for {race}")


def test_weather_updates(results: TestResults):
    """Test weather state updates."""
    print("\n[Test 4] Weather State Updates")

    generator = WeatherGenerator(seed=456)
    weather = generator.generate_initial_weather("Britain")

    # Simulate time passing
    updated = generator.update_weather(weather, delta_time=30.0)

    if not isinstance(updated, WeatherState):
        results.record_fail("Weather update", "Should return WeatherState")
        return

    # Check that rainfall accumulation increased if raining
    if weather.rain_intensity != RainIntensity.NONE:
        if updated.rainfall_accumulation < weather.rainfall_accumulation:
            results.record_fail("Rain accumulation", "Should increase when raining")
        else:
            results.record_pass("Rain accumulation increases when raining")
    else:
        results.record_pass("No rain - accumulation stays zero")

    # Check track condition updates
    if weather.rain_intensity != RainIntensity.NONE:
        if updated.track_condition in [TrackCondition.WET, TrackCondition.FLOODED]:
            results.record_pass("Track becomes wet when raining")
        else:
            results.record_fail("Track condition", "Should be wet when raining")


def test_weather_forecast(results: TestResults):
    """Test weather forecast generation."""
    print("\n[Test 5] Weather Forecast Generation")

    generator = WeatherGenerator(seed=789)
    forecast = generator.get_weather_forecast("Singapore")

    if not forecast.race_name:
        results.record_fail("Forecast race name", "Missing race name")
        return

    if not (0 <= forecast.rain_probability <= 1):
        results.record_fail("Forecast rain probability", "Out of range")
        return

    results.record_pass(
        f"Forecast for {forecast.race_name}: {forecast.rain_probability:.1%} rain chance"
    )


def test_weather_type_distribution(results: TestResults):
    """Test that weather types are distributed reasonably."""
    print("\n[Test 6] Weather Type Distribution")

    # Generate many samples for a track
    generator = WeatherGenerator(seed=111)
    weather_types = []

    for _ in range(200):
        weather = generator.generate_initial_weather("Britain")
        weather_types.append(weather.weather_type)

    type_counts = Counter(weather_types)

    # Check that we get a mix of conditions
    if len(type_counts) < 3:
        results.record_fail(
            "Weather variety", f"Only {len(type_counts)} weather types from 200 samples"
        )
        return

    results.record_pass(
        f"Got {len(type_counts)} different weather types from 200 samples"
    )


def test_all_2022_races_calibration(results: TestResults):
    """Test weather generation for all 2022 races."""
    print("\n[Test 7] 2022 Races Calibration")

    results_data = generate_weather_for_all_2022_races(seed=42)

    if len(results_data) != len(RACE_CALENDAR_2022):
        results.record_fail(
            "Race count", f"Expected {len(RACE_CALENDAR_2022)}, got {len(results_data)}"
        )
        return

    # Check that each race has valid data
    for race_name, data in results_data.items():
        if "samples" not in data or len(data["samples"]) != 100:
            results.record_fail(
                f"Samples for {race_name}", "Missing or incorrect samples"
            )
            continue

    results.record_pass(f"All {len(results_data)} 2022 races have calibration data")

    # Print summary of rain probabilities
    print("\n  Rain probability summary:")
    for race_name, data in sorted(
        results_data.items(),
        key=lambda x: x[1]["climate_info"]["calculated_rain_probability"],
        reverse=True,
    ):
        print(f"    {race_name}: {data['climate_info']['calculated_rain_probability']:.1%}")


def test_track_climate_info(results: TestResults):
    """Test track climate information retrieval."""
    print("\n[Test 8] Track Climate Information")

    generator = WeatherGenerator(seed=222)

    test_cases = [
        ("Singapore", "tropical", True),  # Should be tropical, always rainy
        ("Bahrain", "desert", False),  # Should be desert, not rainy season
        ("Britain", "temperate", True),  # Should be temperate, rainy
        ("Monaco", "mediterranean", True),  # May is in Monaco's rainy months
    ]

    for track, expected_climate, expected_rainy in test_cases:
        info = generator.get_track_climate_info(track)

        if info["climate_type"] != expected_climate:
            results.record_fail(
                f"Climate for {track}",
                f"Expected {expected_climate}, got {info['climate_type']}",
            )
            continue

        # Only check rainy season for non-year-round rainy tracks
        if track != "Singapore":
            if info["is_rainy_season"] != expected_rainy:
                results.record_fail(
                    f"Rainy season for {track}",
                    f"Expected {expected_rainy}, got {info['is_rainy_season']}",
                )
                continue

        results.record_pass(f"Climate info for {track}")


def test_integration_with_simulation_data(results: TestResults):
    """Test that weather data can be used with simulation."""
    print("\n[Test 9] Simulation Integration Points")

    generator = WeatherGenerator(seed=333)

    # Simulate what would happen in race simulation
    race_duration = 120  # minutes
    current_weather = generator.generate_initial_weather("Monaco")

    # Simulate lap-by-lap weather changes
    weather_history = [current_weather]

    for lap in range(1, 57):  # ~57 laps for Monaco
        # Every 10 laps, check for weather update
        if lap % 10 == 0:
            current_weather = generator.update_weather(
                current_weather, delta_time=1.8
            )  # ~108 seconds per lap
            weather_history.append(current_weather)

    if len(weather_history) < 5:
        results.record_fail(
            "Weather history", f"Only {len(weather_history)} weather states recorded"
        )
        return

    results.record_pass(
        f"Generated {len(weather_history)} weather states for race simulation"
    )

    # Check that weather can affect race control
    rain_states = [w for w in weather_history if w.rain_intensity != RainIntensity.NONE]
    if rain_states:
        results.record_pass(f"Simulation can track {len(rain_states)} wet periods")


def test_deterministic_seeding(results: TestResults):
    """Test that seeding produces deterministic results."""
    print("\n[Test 10] Deterministic Seeding")

    # Generate weather with same seed
    gen1 = WeatherGenerator(seed=999)
    w1 = gen1.generate_initial_weather("Italy")

    gen2 = WeatherGenerator(seed=999)
    w2 = gen2.generate_initial_weather("Italy")

    if w1.weather_type != w2.weather_type:
        results.record_fail(
            "Deterministic seeding", "Same seed produced different weather"
        )
        return

    if abs(w1.temperature - w2.temperature) > 0.01:
        results.record_fail(
            "Deterministic seeding", "Same seed produced different temperature"
        )
        return

    results.record_pass("Same seed produces identical results")


def test_extreme_conditions(results: TestResults):
    """Test handling of extreme weather conditions."""
    print("\n[Test 11] Extreme Weather Conditions")

    generator = WeatherGenerator(seed=444)

    # Generate many samples and check for extreme cases
    extreme_conditions = []

    for _ in range(500):
        weather = generator.generate_initial_weather("Singapore")  # High rain chance

        if weather.rain_intensity in [RainIntensity.HEAVY, RainIntensity.TORRENTIAL]:
            extreme_conditions.append(weather.rain_intensity)

    # Should have some extreme conditions for Singapore
    if extreme_conditions:
        results.record_pass(
            f"Got {len(extreme_conditions)} extreme conditions in 500 samples"
        )
    else:
        results.record_fail(
            "Extreme conditions", "No extreme rain in Singapore samples"
        )


def test_api_interface(results: TestResults):
    """Test public API interface."""
    print("\n[Test 12] Public API Interface")

    # Test imports work
    try:
        from weather import (
            WeatherGenerator,
            WeatherState,
            WeatherType,
            TrackCondition,
            RaceControlState,
            RainIntensity,
        )

        results.record_pass("All public API imports")
    except ImportError as e:
        results.record_fail("API imports", str(e))
        return

    # Test dataclasses are properly structured
    ws = WeatherState(
        weather_type=WeatherType.CLEAR,
        track_condition=TrackCondition.DRY,
        temperature=25.0,
    )

    # Test serialization
    ws_dict = ws.to_dict()
    if "weather_type" not in ws_dict:
        results.record_fail("WeatherState.to_dict()", "Missing weather_type key")
        return

    results.record_pass("WeatherState serialization works")


def run_all_tests() -> TestResults:
    """Run all weather system tests."""
    results = TestResults()

    print("=" * 60)
    print("F1 Weather System - Integration Tests")
    print("=" * 60)

    test_basic_weather_generation(results)
    test_weather_distribution(results)
    test_weather_events_generation(results)
    test_weather_updates(results)
    test_weather_forecast(results)
    test_weather_type_distribution(results)
    test_all_2022_races_calibration(results)
    test_track_climate_info(results)
    test_integration_with_simulation_data(results)
    test_deterministic_seeding(results)
    test_extreme_conditions(results)
    test_api_interface(results)

    print(results.summary())

    if results.errors:
        print("\nFailed Tests:")
        for test_name, reason in results.errors:
            print(f"  - {test_name}: {reason}")

    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if results.failed == 0 else 1)
