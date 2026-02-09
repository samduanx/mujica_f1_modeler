#!/usr/bin/env python3
"""
DRS Prototype Runner

Demonstrates the DRS simulation system with Monaco and Monza tracks.
"""

import sys

sys.path.insert(0, "src")

from drs.zones.monaco_2024 import get_config as get_monaco_config
from drs.zones.monza_2024 import get_config as get_monza_config
from drs.driver_state import TEST_DRIVERS
from drs.simulator import (
    TimeSteppedDRSSimulator,
    SimulationConfig,
    create_test_driver_states,
)


def run_monaco_simulation(num_laps: int = 5, verbose: bool = True):
    """Run Monaco DRS simulation"""
    print("\n" + "=" * 60)
    print("MONACO GRAND PRIX 2024 - DRS SIMULATION")
    print("=" * 60)

    # Get configuration
    config = get_monaco_config()

    # Create driver states
    driver_states = create_test_driver_states(
        TEST_DRIVERS[:6]
    )  # 6 drivers for faster testing

    # Create simulation configuration
    sim_config = SimulationConfig(
        time_resolution=0.2,
        random_seed=42,
        enable_drs=True,
        enable_tyre_degradation=True,
        verbose=verbose,
    )

    # Create and run simulator
    simulator = TimeSteppedDRSSimulator(
        config=config, drivers=driver_states, simulation_config=sim_config
    )

    return simulator.simulate_race(num_laps)


def run_monza_simulation(num_laps: int = 5, verbose: bool = True):
    """Run Monza DRS simulation"""
    print("\n" + "=" * 60)
    print("MONZA GRAND PRIX 2024 - DRS SIMULATION")
    print("=" * 60)

    # Get configuration
    config = get_monza_config()

    # Create driver states
    driver_states = create_test_driver_states(TEST_DRIVERS[:6])

    # Create simulation configuration
    sim_config = SimulationConfig(
        time_resolution=0.2,
        random_seed=42,
        enable_drs=True,
        enable_tyre_degradation=True,
        verbose=verbose,
    )

    # Create and run simulator
    simulator = TimeSteppedDRSSimulator(
        config=config, drivers=driver_states, simulation_config=sim_config
    )

    return simulator.simulate_race(num_laps)


def compare_tracks(monaco_results: dict, monza_results: dict):
    """Compare DRS effects between tracks"""
    print("\n" + "=" * 60)
    print("CROSS-TRACK COMPARISON")
    print("=" * 60)

    # Get average DRS gains
    monaco_drivers = list(monaco_results["drs_statistics"].keys())
    monza_drivers = list(monza_results["drs_statistics"].keys())

    monza_avg_gain = sum(
        monza_results["drs_statistics"][d]["total_gain"] for d in monza_drivers
    ) / len(monza_drivers)

    monaco_avg_gain = sum(
        monaco_results["drs_statistics"][d]["total_gain"] for d in monaco_drivers
    ) / len(monaco_drivers)

    print(f"\nAverage DRS Gain per Driver:")
    print(f"  Monaco: {monaco_avg_gain:.3f}s")
    print(f"  Monza:  {monza_avg_gain:.3f}s")
    print(f"  Ratio:  {monza_avg_gain / monaco_avg_gain:.1f}x (expected ~4x)")

    # Get average lap times
    monaco_avg_lap = sum(monaco_results["average_lap_times"].values()) / len(
        monaco_results["average_lap_times"]
    )
    monza_avg_lap = sum(monza_results["average_lap_times"].values()) / len(
        monza_results["average_lap_times"]
    )

    print(f"\nAverage Lap Times:")
    print(f"  Monaco: {monaco_avg_lap:.3f}s (expected ~76s)")
    print(f"  Monza:  {monza_avg_lap:.3f}s (expected ~84s)")

    print("\n" + "=" * 60)


def main():
    """Main entry point for DRS prototype"""
    print("\n" + "=" * 60)
    print("F1 DRS SIMULATION PROTOTYPE")
    print("=" * 60)
    print("Time Resolution: 0.2s intervals")
    print("Test Drivers: 6")
    print("Test Laps: 5")
    print("=" * 60)

    # Run Monaco simulation
    monaco_results = run_monaco_simulation(num_laps=5, verbose=True)

    # Run Monza simulation
    monza_results = run_monza_simulation(num_laps=5, verbose=True)

    # Compare results
    compare_tracks(monaco_results, monza_results)

    print("\nPrototype simulation complete!")
    return monaco_results, monza_results


if __name__ == "__main__":
    main()
