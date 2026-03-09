"""
Monte Carlo test for qualifying lap time generation.
Tests probability of drivers getting no lap times due to incidents.
"""

import random
from collections import defaultdict
from typing import List, Tuple


def simulate_qualifying_run(num_drivers: int = 20) -> Tuple[int, List[str]]:
    """
    Simulate one qualifying run and return number of drivers with no lap times.

    Returns:
        Tuple of (num_no_lap_times, list of driver names with no times)
    """
    # Simulate 20 drivers (or variable number)
    drivers = [f"Driver{i}" for i in range(num_drivers)]

    no_lap_time_drivers = []

    for driver in drivers:
        # Generate lap time
        lap_time = 75.0 + random.uniform(-0.5, 0.5)

        # Check for incidents (same logic as main.py)
        incident_roll = random.randint(1, 100)

        if incident_roll <= 5:  # 5% crash chance
            # Bug: No lap time recorded!
            no_lap_time_drivers.append(driver)
        elif incident_roll <= 15:  # 10% track limits chance
            # Bug: No lap time recorded!
            no_lap_time_drivers.append(driver)
        # else: lap time recorded normally

    return len(no_lap_time_drivers), no_lap_time_drivers


def run_monte_carlo(iterations: int = 100, num_drivers: int = 20) -> dict:
    """
    Run Monte Carlo simulation.

    Args:
        iterations: Number of qualifying simulations to run
        num_drivers: Number of drivers in each simulation

    Returns:
        Statistics about no-lap-time occurrences
    """
    results = defaultdict(int)
    total_no_lap_times = 0

    for i in range(iterations):
        num_no_lap, drivers = simulate_qualifying_run(num_drivers)
        results[num_no_lap] += 1
        total_no_lap_times += num_no_lap

    avg_no_lap_times = total_no_lap_times / iterations

    print(f"\n{'=' * 60}")
    print(
        f"Monte Carlo Qualifying Test Results ({iterations} iterations, {num_drivers} drivers)"
    )
    print(f"{'=' * 60}")
    print(f"\nDistribution of drivers with no lap times:")
    for num_no_lap in sorted(results.keys()):
        count = results[num_no_lap]
        pct = (count / iterations) * 100
        bar = "█" * int(pct / 2)
        print(f"  {num_no_lap:2d} drivers: {count:3d} times ({pct:5.1f}%) {bar}")

    print(f"\nAverage drivers with no lap times per session: {avg_no_lap_times:.2f}")
    print(f"Expected (theoretical): {num_drivers * 0.15:.2f} (15% of {num_drivers})")

    # Probability of at least one driver having no time
    prob_at_least_one = (results[0] / iterations) * 100
    print(
        f"\nProbability of at least 1 driver with no time: {100 - prob_at_least_one:.1f}%"
    )
    print(
        f"Probability of 3+ drivers with no time: {sum(results[i] for i in range(3, 100)) / iterations * 100:.1f}%"
    )
    print(
        f"Probability of 4+ drivers with no time: {sum(results[i] for i in range(4, 100)) / iterations * 100:.1f}%"
    )

    return {
        "results": dict(results),
        "avg_no_lap_times": avg_no_lap_times,
        "prob_at_least_one": 100 - prob_at_least_one,
    }


if __name__ == "__main__":
    print("Running Monte Carlo simulation for qualifying lap times...\n")

    # Test with 20 drivers
    print("\n### TEST 1: 20 drivers ###")
    run_monte_carlo(iterations=100, num_drivers=20)

    # Test with 22 drivers
    print("\n\n### TEST 2: 22 drivers ###")
    run_monte_carlo(iterations=100, num_drivers=22)

    print("\n\n### ANALYSIS ###")
    print("Current logic: 15% chance per driver to get no lap time")
    print("  - 20 drivers: Expected ~3 drivers with no time per session")
    print("  - 22 drivers: Expected ~3.3 drivers with no time per session")
    print("\nThe bug causes drivers with incidents to have NO lap recorded at all.")
    print("This is incorrect - the lap should be recorded, then flagged as deleted.")
