"""
Monte Carlo Analysis for VSC/SC Frequency Investigation.

This script runs large-scale Monte Carlo simulations to investigate whether
there are indeed an unusually high number of VSC (Virtual Safety Car) and
SC (Safety Car) events per race weekend.

Run with: uv run python src/debug/monte_carlo_vsc_analysis.py
"""

import sys
import os
import random
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Use a faster approach: analyze the VSC/SC trigger logic directly
# rather than running full simulations

# =============================================================================
# VSC/SC TRIGGER LOGIC (extracted from enhanced_long_dist_sim.py)
# =============================================================================


def roll_d100() -> int:
    """Roll a d100 (1-100)."""
    return random.randint(1, 100)


# Typical race configurations
TRACK_CONFIGS = {
    # Normal tracks with typical race laps
    "Monaco": {"laps": 78, "base_lap_time": 75.0},
    "Spain": {"laps": 66, "base_lap_time": 80.0},
    "Monza": {"laps": 53, "base_lap_time": 85.0},
    "Australia": {"laps": 58, "base_lap_time": 83.0},
    "Bahrain": {"laps": 57, "base_lap_time": 88.0},
    "China": {"laps": 56, "base_lap_time": 86.0},
    "Japan": {"laps": 53, "base_lap_time": 88.0},
    # Sprint tracks
    "Imola": {
        "laps": 63,
        "sprint_laps": 21,
        "base_lap_time": 82.0,
    },  # Main race ~63 laps
    "Austria": {
        "laps": 71,
        "sprint_laps": 24,
        "base_lap_time": 68.0,
    },  # Main race ~71 laps
    "Sao_Paulo": {
        "laps": 71,
        "sprint_laps": 24,
        "base_lap_time": 72.0,
    },  # Main race ~71 laps
}

# Weather probability (from weather system)
# Based on docs/WEATHER_SYSTEM.md - typical rain probability
WEATHER_RAIN_PROBABILITY = 0.15  # 15% chance of rain during race
WEATHER_HEAVY_RAIN_PROBABILITY = 0.03  # 3% chance of heavy rain


def simulate_race_vsc_sc(num_laps: int, seed: int, enable_weather: bool = True) -> Dict:
    """
    Simulate VSC/SC events for a single race.

    This simulates the trigger logic from enhanced_long_dist_sim.py:
    - Random trigger: 2% SC, 3% VSC per lap (after lap 3)
    - Weather trigger: ~15% rain → VSC, ~3% heavy rain → SC

    Returns:
        Dictionary with VSC/SC counts and details
    """
    random.seed(seed)

    vsc_count = 0
    sc_count = 0
    vsc_laps = []
    sc_laps = []

    for lap in range(1, num_laps + 1):
        # Skip first 3 laps (per simulation logic)
        if lap <= 3:
            continue

        # ===================================================================
        # 1. Weather-based VSC/SC (only if enabled)
        # ===================================================================
        if enable_weather:
            weather_roll = random.random()

            # Heavy rain → SC
            if weather_roll < WEATHER_HEAVY_RAIN_PROBABILITY:
                sc_count += 1
                sc_laps.append(lap)
                continue  # Skip random triggers during weather SC

            # Moderate rain → VSC
            elif weather_roll < WEATHER_RAIN_PROBABILITY:
                vsc_count += 1
                vsc_laps.append(lap)
                continue  # Skip random triggers during weather VSC

        # ===================================================================
        # 2. Random VSC/SC trigger (per lap, 5% total)
        # ===================================================================
        sc_roll = roll_d100()

        if sc_roll >= 98:  # 2% SC
            sc_count += 1
            sc_laps.append(lap)
        elif sc_roll >= 95:  # 3% VSC
            vsc_count += 1
            vsc_laps.append(lap)

    return {
        "vsc_count": vsc_count,
        "sc_count": sc_count,
        "total_safety_events": vsc_count + sc_count,
        "vsc_laps": vsc_laps,
        "sc_laps": sc_laps,
        "num_laps": num_laps,
    }


def simulate_sprint_weekend(
    track_name: str, seed: int, enable_weather: bool = True
) -> Dict:
    """
    Simulate a complete sprint weekend (sprint race + main race).

    Returns:
        VSC/SC counts for sprint + main race combined
    """
    config = TRACK_CONFIGS.get(track_name, {"laps": 60, "sprint_laps": 21})

    # Simulate sprint race
    sprint_result = simulate_race_vsc_sc(
        config.get("sprint_laps", 21), seed, enable_weather
    )

    # Simulate main race (different seed)
    main_result = simulate_race_vsc_sc(config["laps"], seed + 1, enable_weather)

    return {
        "track": track_name,
        "sprint_vsc": sprint_result["vsc_count"],
        "sprint_sc": sprint_result["sc_count"],
        "main_vsc": main_result["vsc_count"],
        "main_sc": main_result["sc_count"],
        "total_vsc": sprint_result["vsc_count"] + main_result["vsc_count"],
        "total_sc": sprint_result["sc_count"] + main_result["sc_count"],
        "total_safety_events": (
            sprint_result["vsc_count"]
            + sprint_result["sc_count"]
            + main_result["vsc_count"]
            + main_result["sc_count"]
        ),
        "sprint_laps": config.get("sprint_laps", 21),
        "main_laps": config["laps"],
        "total_laps": config.get("sprint_laps", 21) + config["laps"],
    }


def run_monte_carlo_experiment(
    num_simulations: int = 1000, enable_weather: bool = True
) -> Dict:
    """
    Run Monte Carlo experiment to analyze VSC/SC frequency.

    Returns:
        Statistics and raw data from all simulations
    """
    print(f"\n{'=' * 80}")
    print(f"MONTE CARLO VSC/SC ANALYSIS")
    print(f"{'=' * 80}")
    print(f"Simulations per category: {num_simulations}")
    print(f"Weather enabled: {enable_weather}")
    print(f"{'=' * 80}\n")

    results = {
        "normal_weekends": [],
        "sprint_weekends": [],
    }

    # =============================================================================
    # 1. Normal Race Weekends (50-78 laps)
    # =============================================================================
    print("Simulating normal race weekends...")

    normal_tracks = [
        "Monaco",
        "Spain",
        "Monza",
        "Australia",
        "Bahrain",
        "China",
        "Japan",
    ]

    for i in range(num_simulations):
        # Pick random track
        track = random.choice(normal_tracks)
        config = TRACK_CONFIGS[track]

        result = simulate_race_vsc_sc(
            config["laps"], seed=i, enable_weather=enable_weather
        )
        result["track"] = track
        result["weekend_type"] = "normal"

        results["normal_weekends"].append(result)

    # =============================================================================
    # 2. Sprint Race Weekends (sprint 21-24 laps + main 50-70 laps)
    # =============================================================================
    print("Simulating sprint race weekends...")

    sprint_tracks = ["Imola", "Austria", "Sao_Paulo"]

    for i in range(num_simulations):
        # Pick random sprint track
        track = random.choice(sprint_tracks)

        result = simulate_sprint_weekend(
            track, seed=i + num_simulations, enable_weather=enable_weather
        )
        result["weekend_type"] = "sprint"

        results["sprint_weekends"].append(result)

    return results


def analyze_results(results: Dict) -> Dict:
    """Analyze and summarize the Monte Carlo results."""

    def compute_stats(data_list: List[Dict], key: str) -> Dict:
        values = [d[key] for d in data_list]
        return {
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "median": np.median(values),
            "p25": np.percentile(values, 25),
            "p75": np.percentile(values, 75),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99),
        }

    # Normal weekends analysis
    normal_data = results["normal_weekends"]

    normal_stats = {
        "vsc": compute_stats(normal_data, "vsc_count"),
        "sc": compute_stats(normal_data, "sc_count"),
        "total": compute_stats(normal_data, "total_safety_events"),
        "num_simulations": len(normal_data),
    }

    # Sprint weekends analysis
    sprint_data = results["sprint_weekends"]

    sprint_stats = {
        "vsc": compute_stats(sprint_data, "total_vsc"),
        "sc": compute_stats(sprint_data, "total_sc"),
        "total": compute_stats(sprint_data, "total_safety_events"),
        "sprint_only_vsc": compute_stats(sprint_data, "sprint_vsc"),
        "sprint_only_sc": compute_stats(sprint_data, "sprint_sc"),
        "main_only_vsc": compute_stats(sprint_data, "main_vsc"),
        "main_only_sc": compute_stats(sprint_data, "main_sc"),
        "num_simulations": len(sprint_data),
        "avg_total_laps": np.mean([d["total_laps"] for d in sprint_data]),
    }

    return {
        "normal_weekends": normal_stats,
        "sprint_weekends": sprint_stats,
    }


def print_analysis(analysis: Dict):
    """Print formatted analysis results."""

    print(f"\n{'=' * 80}")
    print("ANALYSIS RESULTS")
    print(f"{'=' * 80}")

    # =============================================================================
    # Normal Weekends
    # =============================================================================
    normal = analysis["normal_weekends"]
    print(f"\n### NORMAL RACE WEEKENDS (n={normal['num_simulations']})")
    print(f"Average laps per race: ~60-78")
    print(f"\n  VSC Events:")
    print(f"    Mean: {normal['vsc']['mean']:.2f}")
    print(f"    Std:  {normal['vsc']['std']:.2f}")
    print(f"    95th percentile: {normal['vsc']['p95']:.1f}")
    print(f"    Range: [{normal['vsc']['min']:.0f}, {normal['vsc']['max']:.0f}]")

    print(f"\n  SC Events:")
    print(f"    Mean: {normal['sc']['mean']:.2f}")
    print(f"    Std:  {normal['sc']['std']:.2f}")
    print(f"    95th percentile: {normal['sc']['p95']:.1f}")
    print(f"    Range: [{normal['sc']['min']:.0f}, {normal['sc']['max']:.0f}]")

    print(f"\n  TOTAL Safety Events (VSC + SC):")
    print(f"    Mean: {normal['total']['mean']:.2f}")
    print(f"    Std:  {normal['total']['std']:.2f}")
    print(f"    Median: {normal['total']['median']:.1f}")
    print(f"    95th percentile: {normal['total']['p95']:.1f}")
    print(f"    Range: [{normal['total']['min']:.0f}, {normal['total']['max']:.0f}]")

    # =============================================================================
    # Sprint Weekends
    # =============================================================================
    sprint = analysis["sprint_weekends"]
    print(f"\n\n### SPRINT RACE WEEKENDS (n={sprint['num_simulations']})")
    print(f"Average total laps (sprint + main): ~{sprint['avg_total_laps']:.0f}")
    print(f"\n  VSC Events (total):")
    print(f"    Mean: {sprint['vsc']['mean']:.2f}")
    print(f"    Std:  {sprint['vsc']['std']:.2f}")
    print(f"    95th percentile: {sprint['vsc']['p95']:.1f}")
    print(f"    Range: [{sprint['vsc']['min']:.0f}, {sprint['vsc']['max']:.0f}]")

    print(f"\n  SC Events (total):")
    print(f"    Mean: {sprint['sc']['mean']:.2f}")
    print(f"    Std:  {sprint['sc']['std']:.2f}")
    print(f"    95th percentile: {sprint['sc']['p95']:.1f}")
    print(f"    Range: [{sprint['sc']['min']:.0f}, {sprint['sc']['max']:.0f}]")

    print(f"\n  TOTAL Safety Events (VSC + SC):")
    print(f"    Mean: {sprint['total']['mean']:.2f}")
    print(f"    Std:  {sprint['total']['std']:.2f}")
    print(f"    Median: {sprint['total']['median']:.1f}")
    print(f"    95th percentile: {sprint['total']['p95']:.1f}")
    print(f"    Range: [{sprint['total']['min']:.0f}, {sprint['total']['max']:.0f}]")

    # Breakdown
    print(f"\n  --- Breakdown ---")
    print(
        f"  Sprint race only: VSC={sprint['sprint_only_vsc']['mean']:.2f}, SC={sprint['sprint_only_sc']['mean']:.2f}"
    )
    print(
        f"  Main race only:   VSC={sprint['main_only_vsc']['mean']:.2f}, SC={sprint['main_only_sc']['mean']:.2f}"
    )

    # =============================================================================
    # Comparison
    # =============================================================================
    print(f"\n\n{'=' * 80}")
    print("COMPARISON: NORMAL vs SPRINT WEEKENDS")
    print(f"{'=' * 80}")

    vsc_diff = sprint["vsc"]["mean"] - normal["vsc"]["mean"]
    sc_diff = sprint["sc"]["mean"] - normal["sc"]["mean"]
    total_diff = sprint["total"]["mean"] - normal["total"]["mean"]

    print(
        f"\n  VSC: Sprint avg {sprint['vsc']['mean']:.2f} vs Normal avg {normal['vsc']['mean']:.2f}"
    )
    print(
        f"       Difference: {vsc_diff:+.2f} ({vsc_diff / normal['vsc']['mean'] * 100:+.1f}%)"
    )

    print(
        f"\n  SC:  Sprint avg {sprint['sc']['mean']:.2f} vs Normal avg {normal['sc']['mean']:.2f}"
    )
    print(
        f"       Difference: {sc_diff:+.2f} ({sc_diff / normal['sc']['mean'] * 100:+.1f}%)"
    )

    print(f"\n  TOTAL Safety Events:")
    print(f"       Sprint avg: {sprint['total']['mean']:.2f}")
    print(f"       Normal avg: {normal['total']['mean']:.2f}")
    print(
        f"       Difference: {total_diff:+.2f} ({total_diff / normal['total']['mean'] * 100:+.1f}%)"
    )

    # Theoretical expectation
    print(f"\n{'=' * 80}")
    print("THEORETICAL EXPECTATION")
    print(f"{'=' * 80}")
    print(f"\nBased on 5% trigger probability per lap (after lap 3):")
    print(f"  - Normal race (~60 laps): ~{60 * 0.05:.1f} safety events expected")
    print(f"  - Sprint + Main (~90 laps): ~{90 * 0.05:.1f} safety events expected")
    print(f"\nWith weather (15% rain × VSC, 3% heavy rain × SC):")
    print(f"  - Additional ~0.18 events per race from weather")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Monte Carlo VSC/SC Analysis")
    parser.add_argument(
        "-n",
        "--num-simulations",
        type=int,
        default=1000,
        help="Number of simulations per category (default: 1000)",
    )
    parser.add_argument(
        "--no-weather",
        action="store_true",
        help="Disable weather-based VSC/SC triggers",
    )
    parser.add_argument("-o", "--output", type=str, help="Output JSON file for results")

    args = parser.parse_args()

    # Run experiment
    results = run_monte_carlo_experiment(
        num_simulations=args.num_simulations, enable_weather=not args.no_weather
    )

    # Analyze
    analysis = analyze_results(results)

    # Print
    print_analysis(analysis)

    # Save if requested
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "num_simulations": args.num_simulations,
            "weather_enabled": not args.no_weather,
            "analysis": analysis,
            "sample_results": {
                "normal": results["normal_weekends"][:10],
                "sprint": results["sprint_weekends"][:10],
            },
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\n\nResults saved to: {args.output}")

    return analysis


if __name__ == "__main__":
    main()
