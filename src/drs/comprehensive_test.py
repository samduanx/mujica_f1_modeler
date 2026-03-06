#!/usr/bin/env python3
"""
Comprehensive DRS System Test

Tests the DRS simulation across multiple tracks and identifies issues.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.drs.simulator import TimeSteppedDRSSimulator, SimulationConfig
from src.drs.driver_state import create_test_driver_states

# Import available track configurations
from src.drs.zones import get_monaco_config, get_monza_config, get_spain_config, get_bahrain_config


# Available track configurations
TRACK_CONFIGS = {
    "Monaco": get_monaco_config,
    "Monza": get_monza_config,
    "Spain": get_spain_config,
    "Bahrain": get_bahrain_config,
}


def run_track_test(track_name, config_func, num_laps=5, verbose=False):
    """Run a single track test"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {track_name}")
    print(f"{'=' * 60}")

    try:
        config = config_func()

        # Create driver states
        drivers = create_test_driver_states()

        # Create simulation config
        sim_config = SimulationConfig(
            time_resolution=0.2, random_seed=42, enable_drs=True, verbose=verbose
        )

        # Create and run simulator
        simulator = TimeSteppedDRSSimulator(
            config=config, drivers=drivers, simulation_config=sim_config
        )

        results = simulator.simulate_race(num_laps)

        # Analyze results
        avg_lap_time = sum(results["average_lap_times"].values()) / len(
            results["average_lap_times"]
        )
        avg_drs_gain = sum(
            stats["total_gain"] for stats in results["drs_statistics"].values()
        ) / len(results["drs_statistics"])

        print(f"\nTrack Analysis:")
        print(f"  Total Distance: {config.total_distance}m")
        print(f"  Base Lap Time: {config.calculate_base_lap_time():.1f}s")
        print(f"  Simulated Avg Lap: {avg_lap_time:.2f}s")
        print(f"  Avg DRS Gain/Driver: {avg_drs_gain:.2f}s")
        print(f"  Difficulty: {config.difficulty}")

        # Check DRS zones
        total_drs_zones = sum(
            len(sector.drs_zones) for sector in config.sectors.values()
        )
        print(f"  DRS Zones: {total_drs_zones}")

        return {
            "track": track_name,
            "success": True,
            "avg_lap_time": avg_lap_time,
            "avg_drs_gain": avg_drs_gain,
            "total_drs_zones": total_drs_zones,
            "base_lap_time": config.calculate_base_lap_time(),
            "error": None,
        }

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

        return {
            "track": track_name,
            "success": False,
            "error": str(e),
            "avg_lap_time": 0,
            "avg_drs_gain": 0,
            "total_drs_zones": 0,
            "base_lap_time": 0,
        }


def identify_issues(results):
    """Identify potential issues from test results"""
    issues = []

    for result in results:
        if not result["success"]:
            issues.append(f"CRITICAL: {result['track']} - {result['error']}")
            continue

        # Check for unrealistic lap times
        if result["avg_lap_time"] < 50:
            issues.append(
                f"{result['track']}: Unrealistic lap time ({result['avg_lap_time']:.2f}s) - too fast"
            )

        if result["avg_lap_time"] > 150:
            issues.append(
                f"{result['track']}: Unrealistic lap time ({result['avg_lap_time']:.2f}s) - too slow"
            )

        # Check for DRS zone issues
        if result["total_drs_zones"] == 0:
            issues.append(f"{result['track']}: No DRS zones configured")

        if result["avg_drs_gain"] < 0:
            issues.append(
                f"{result['track']}: Negative DRS gain ({result['avg_drs_gain']:.2f}s)"
            )

        # Check lap time vs base time ratio
        if result["base_lap_time"] > 0:
            ratio = result["avg_lap_time"] / result["base_lap_time"]
            if ratio < 0.8:
                issues.append(
                    f"{result['track']}: Lap time {ratio:.2f}x of base - unrealistic"
                )
            elif ratio > 1.3:
                issues.append(
                    f"{result['track']}: Lap time {ratio:.2f}x of base - degradation too high"
                )

    return issues


def main():
    """Run comprehensive tests"""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE DRS SYSTEM TEST")
    print("Testing across all available tracks (2022-2024)")
    print("=" * 60)

    results = []

    # Test each track
    for track_name, config_func in TRACK_CONFIGS.items():
        result = run_track_test(track_name, config_func, num_laps=3, verbose=False)
        results.append(result)

    # Identify issues
    print("\n" + "=" * 60)
    print("ISSUE ANALYSIS")
    print("=" * 60)

    issues = identify_issues(results)

    if issues:
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ No major issues found")

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(
        f"{'Track':<15} {'Avg Lap':<10} {'DRS Gain':<12} {'DRS Zones':<10} {'Status'}"
    )
    print("-" * 60)

    for result in results:
        status = "✅" if result["success"] else "❌"
        print(
            f"{result['track']:<15} {result['avg_lap_time']:<10.2f} "
            f"{result['avg_drs_gain']:<12.2f} {result['total_drs_zones']:<10} {status}"
        )

    return results, issues


if __name__ == "__main__":
    main()
