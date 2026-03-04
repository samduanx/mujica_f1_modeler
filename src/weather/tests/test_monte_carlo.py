"""
Monte Carlo Weather System Validation Test.

This script runs 100 weather simulations per track for all 23 tracks
from the 2022 F1 calendar to validate the weather generator's behavior
against real-world weather patterns.

Usage:
    uv run python src/weather/tests/test_monte_carlo.py
"""

import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any
import random

# Add src to path
sys.path.insert(0, "src")

from weather.weather_generator import WeatherGenerator
from weather.weather_types import (
    WeatherType,
    RainIntensity,
    RACE_CALENDAR_2022,
    get_track_info,
)


def categorize_weather(weather_type: WeatherType) -> str:
    """Categorize weather type into general categories."""
    if weather_type in [WeatherType.CLEAR, WeatherType.PARTLY_CLOUDY]:
        return "clear"
    elif weather_type in [WeatherType.CLOUDY, WeatherType.OVERCAST]:
        return "overcast"
    elif weather_type == WeatherType.LIGHT_RAIN:
        return "light_rain"
    elif weather_type == WeatherType.MODERATE_RAIN:
        return "moderate_rain"
    elif weather_type in [
        WeatherType.HEAVY_RAIN,
        WeatherType.TORRENTIAL_RAIN,
        WeatherType.THUNDERSTORM,
    ]:
        return "heavy"
    return "clear"


def categorize_intensity(rain_intensity: RainIntensity) -> str:
    """Categorize rain intensity."""
    if rain_intensity == RainIntensity.NONE:
        return "none"
    elif rain_intensity == RainIntensity.LIGHT:
        return "light"
    elif rain_intensity == RainIntensity.MODERATE:
        return "moderate"
    else:  # HEAVY or TORRENTIAL
        return "heavy"


def run_monte_carlo_simulation(
    gp_name: str, num_runs: int = 100, seed: int = 42
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a specific GP.

    Args:
        gp_name: Grand Prix name
        num_runs: Number of simulations to run
        seed: Random seed for reproducibility

    Returns:
        Dictionary with simulation results
    """
    # Get track info to get base rain probability
    track_info = get_track_info(gp_name)

    # Create weather generator with specific seed for each run
    generator = WeatherGenerator(seed=seed)

    # Calculate base rain probability
    base_rain_prob = generator._calculate_base_rain_probability(track_info)

    # Track statistics
    weather_categories = defaultdict(int)
    intensity_categories = defaultdict(int)
    rain_events = 0
    total_events = 0

    for run in range(num_runs):
        # Use different seed for each run
        run_seed = seed + run
        generator = WeatherGenerator(seed=run_seed)

        # Generate initial weather
        initial_weather = generator.generate_initial_weather(gp_name)

        # Generate race weather events
        events = generator.generate_race_weather_events(gp_name, race_duration=120)

        # Categorize initial weather
        weather_cat = categorize_weather(initial_weather.weather_type)
        intensity_cat = categorize_intensity(initial_weather.rain_intensity)

        weather_categories[weather_cat] += 1
        intensity_categories[intensity_cat] += 1

        # Count rain events
        if initial_weather.rain_intensity != RainIntensity.NONE:
            rain_events += 1

        # Count events during race
        total_events += len(events)

    return {
        "gp_name": gp_name,
        "base_rain_prob": base_rain_prob,
        "num_runs": num_runs,
        "weather_categories": dict(weather_categories),
        "intensity_categories": dict(intensity_categories),
        "rain_events": rain_events,
        "total_events": total_events,
        "avg_rain_events": rain_events / num_runs,
        "avg_events_per_run": total_events / num_runs,
    }


def print_results_table(results: List[Dict[str, Any]]) -> None:
    """Print results in a formatted table."""
    print("\n" + "=" * 120)
    print("MONTE CARLO WEATHER SIMULATION RESULTS (100 runs per track)")
    print("=" * 120)
    print()

    # Header
    print(
        f"{'Track':<20} {'Base Rain%':>12} {'Rain Runs':>10} {'Avg Rain':>10} "
        f"{'Clear':>8} {'Light':>8} {'Moderate':>10} {'Heavy':>8}"
    )
    print("-" * 120)

    for r in results:
        gp = r["gp_name"]
        base = r["base_rain_prob"] * 100
        rain_runs = r["rain_events"]
        avg_rain = r["avg_rain_events"]

        # Get weather categories
        clear = r["weather_categories"].get("clear", 0) + r["weather_categories"].get(
            "overcast", 0
        )
        light = r["intensity_categories"].get("light", 0)
        moderate = r["intensity_categories"].get("moderate", 0)
        heavy = r["intensity_categories"].get("heavy", 0)

        print(
            f"{gp:<20} {base:>11.1f}% {rain_runs:>10} {avg_rain:>9.1f} "
            f"{clear:>8} {light:>8} {moderate:>10} {heavy:>8}"
        )

    print("-" * 120)


def generate_markdown_table(results: List[Dict[str, Any]]) -> str:
    """Generate markdown table for documentation."""
    md = "# Monte Carlo Weather Simulation Results\n\n"
    md += "## 2022 F1 Calendar - 100 Runs Per Track\n\n"
    md += "| Track | Base Rain Prob (%) | Expected Rain Events | Avg per 100 | Clear | Light Rain | Moderate | Heavy |\n"
    md += "|-------|-------------------|---------------------|-------------|-------|------------|----------|-------|\n"

    for r in results:
        gp = r["gp_name"]
        base = r["base_rain_prob"] * 100
        expected = r["base_rain_prob"] * 100
        avg = r["avg_rain_events"]

        # Get weather categories
        clear = r["weather_categories"].get("clear", 0) + r["weather_categories"].get(
            "overcast", 0
        )
        light = r["intensity_categories"].get("light", 0)
        moderate = r["intensity_categories"].get("moderate", 0)
        heavy = r["intensity_categories"].get("heavy", 0)

        md += f"| {gp} | {base:.1f}% | {expected:.0f} | {avg:.1f} | {clear} | {light} | {moderate} | {heavy} |\n"

    return md


def compare_with_real_world(results: List[Dict[str, Any]]) -> str:
    """
    Compare simulation results with real-world 2022 F1 weather.

    Real-world data from 2022 season:
    - Bahrain (March 20) - Dry
    - Saudi Arabia (March 27) - Dry
    - Australia (April 10) - Dry
    - Emilia Romagna (April 24) - Rain in qualifying (Sprint weekend)
    - Miami (May 8) - Brief shower
    - Spain (May 22) - Dry
    - Monaco (May 29) - Generally dry
    - Azerbaijan (June 12) - Dry
    - Canada (June 19) - Rain on race day
    - Britain (July 3) - Dry
    - Austria (July 10) - Dry
    - France (July 24) - Dry
    - Hungary (July 31) - Dry
    - Belgium (August 28) - Rain (often)
    - Netherlands (September 4) - Rain possible
    - Italy (September 11) - Dry
    - Singapore (October 2) - High chance of rain
    - Japan (October 9) - Typhoon concerns, rain
    - USA (October 23) - Dry
    - Mexico (October 30) - Dry
    - Brazil (November 13) - Rain during race
    - Abu Dhabi (November 20) - Dry
    - China (Sept 2022) - Historical rain possible
    """

    # Real-world 2022 race day weather (rain during race)
    real_world_rain_gps = {
        "Emilia Romagna": "Rain in qualifying (sprint weekend)",
        "Canada": "Rain on race day",
        "Belgium": "Often rain, wet race",
        "Netherlands": "Rain possible",
        "Singapore": "High chance of rain",
        "Japan": "Typhoon, rain",
        "Brazil": "Rain during race",
    }

    real_world_dry_gps = {
        "Bahrain": "Dry",
        "Saudi Arabia": "Dry",
        "Australia": "Dry",
        "Spain": "Dry",
        "Monaco": "Generally dry",
        "Azerbaijan": "Dry",
        "Britain": "Dry",
        "Austria": "Dry",
        "France": "Dry",
        "Hungary": "Dry",
        "Italy": "Dry",
        "USA": "Dry",
        "Mexico": "Dry",
        "Abu Dhabi": "Dry",
    }

    md = "\n\n## Real-World 2022 F1 Weather Comparison\n\n"
    md += "### Races with Rain During Race\n"
    md += "| Track | Sim Rain % | Real-World Condition |\n"
    md += "|-------|-----------|---------------------|\n"

    for gp, condition in real_world_rain_gps.items():
        for r in results:
            if r["gp_name"] == gp:
                sim_rain = r["avg_rain_events"]
                md += f"| {gp} | {sim_rain:.0f}% | {condition} |\n"
                break

    md += "\n### Races Without Rain\n"
    md += "| Track | Sim Rain % | Real-World Condition |\n"
    md += "|-------|-----------|---------------------|\n"

    for gp, condition in real_world_dry_gps.items():
        for r in results:
            if r["gp_name"] == gp:
                sim_rain = r["avg_rain_events"]
                md += f"| {gp} | {sim_rain:.0f}% | {condition} |\n"
                break

    return md


def generate_analysis(results: List[Dict[str, Any]]) -> str:
    """Generate analysis and calibration recommendations."""

    md = "\n\n## Analysis and Calibration Recommendations\n\n"

    # Identify tracks where simulation significantly differs from reality
    md += "### Tracks Requiring Calibration\n\n"

    # Expected to have rain but simulation shows low rain
    md += "**Lower than expected rain:**\n"
    for r in results:
        if r["gp_name"] in [
            "Belgium",
            "Netherlands",
            "Singapore",
            "Japan",
            "Brazil",
            "Canada",
        ]:
            if r["avg_rain_events"] < 30:
                md += f"- {r['gp_name']}: Simulated {r['avg_rain_events']:.0f}% vs expected >40%\n"

    # Expected to be dry but simulation shows high rain
    md += "\n**Higher than expected rain:**\n"
    for r in results:
        if r["gp_name"] in [
            "Bahrain",
            "Saudi Arabia",
            "Abu Dhabi",
            "Azerbaijan",
            "Spain",
            "Monaco",
        ]:
            if r["avg_rain_events"] > 15:
                md += f"- {r['gp_name']}: Simulated {r['avg_rain_events']:.0f}% vs expected <10%\n"

    md += "\n### Recommendations\n\n"
    md += "1. **Desert tracks (Bahrain, Saudi Arabia, Abu Dhabi, Azerbaijan):**\n"
    md += "   - Consider reducing base rain chance to 1-2%\n"
    md += "   - These tracks virtually never have rain during race day\n\n"

    md += "2. **High-rain tracks (Belgium, Netherlands, Britain):**\n"
    md += "   - Increase base rain chance to 50-60%\n"
    md += "   - These tracks have high likelihood of wet conditions\n\n"

    md += "3. **Tropical tracks (Singapore, Japan, Brazil):\n"
    md += "   - Keep or slightly increase rain probability\n"
    md += "   - These are known for unpredictable tropical showers\n\n"

    md += "4. **Seasonal adjustments:\n"
    md += "   - Consider stronger rainy season multipliers for:\n"
    md += "     - Japan (typhoon season - September/October)\n"
    md += "     - Brazil (Southern hemisphere summer)\n"
    md += "     - Singapore (year-round tropical rain)\n"

    return md


def main():
    """Main function to run Monte Carlo simulation."""
    print("Starting Monte Carlo Weather Simulation Test...")
    print("Running 100 simulations per track for all 23 2022 F1 tracks\n")

    # Get all track names from the 2022 calendar
    tracks = list(RACE_CALENDAR_2022.keys())

    print(f"Testing {len(tracks)} tracks: {', '.join(tracks)}\n")

    results = []

    for i, track in enumerate(tracks):
        print(f"[{i + 1}/{len(tracks)}] Running simulation for {track}...", end=" ")
        result = run_monte_carlo_simulation(track, num_runs=100, seed=42)
        results.append(result)
        print(f"Done. Rain events: {result['rain_events']}/100")

    # Print results table
    print_results_table(results)

    # Generate markdown output
    markdown = generate_markdown_table(results)
    markdown += compare_with_real_world(results)
    markdown += generate_analysis(results)

    # Save to docs
    output_path = "docs/MONTE_CARLO_WEATHER_RESULTS.md"
    with open(output_path, "w") as f:
        f.write(markdown)

    print(f"\nResults saved to {output_path}")

    # Also print the markdown to console
    print(markdown)

    return results


if __name__ == "__main__":
    main()
