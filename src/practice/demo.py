"""
Free Practice System Demo

Demonstrates the Free Practice system with a quick simulation.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from practice import PracticeWeekendSimulator, WeekendType, RRatingConnector


def demo_normal_weekend():
    """Demo a normal race weekend with FP1, FP2, FP3."""
    print("\n" + "=" * 80)
    print("DEMO: NORMAL RACE WEEKEND (FP1, FP2, FP3)")
    print("=" * 80)

    # Driver data
    drivers = [
        "Verstappen",
        "Perez",
        "Leclerc",
        "Sainz",
        "Hamilton",
        "Russell",
        "Norris",
        "Piastri",
    ]

    driver_ratings = {
        "Verstappen": 100.5,
        "Perez": 97.5,
        "Leclerc": 99.0,
        "Sainz": 97.0,
        "Hamilton": 98.0,
        "Russell": 97.5,
        "Norris": 96.5,
        "Piastri": 95.5,
    }

    # Create simulator
    simulator = PracticeWeekendSimulator(
        track="Spain",
        track_base_time=78.5,
        weekend_type=WeekendType.NORMAL,
        drivers=drivers,
        driver_ratings=driver_ratings,
        seed=42,
    )

    # Run all sessions
    results = simulator.run_all_sessions()

    # Export R ratings
    print("\n" + "=" * 80)
    print("R RATING EXPORT FOR QUALIFYING/RACE")
    print("=" * 80)

    r_ratings = simulator.get_all_final_r_ratings()
    deltas = simulator.get_r_rating_deltas()

    print(f"{'Driver':<15} {'Base R':<10} {'Delta':<10} {'Final R':<10}")
    print("-" * 50)

    for driver in sorted(drivers, key=lambda d: r_ratings[d], reverse=True):
        base = driver_ratings[driver]
        delta = deltas[driver]
        final = r_ratings[driver]
        print(f"{driver:<15} {base:<10.2f} {delta:>+8.2f}  {final:<10.2f}")

    # Export to JSON
    json_export = simulator.export_r_ratings(output_format="json")
    print("\nJSON Export Sample:")
    print(json_export[:500] + "...")

    return simulator


def demo_sprint_weekend():
    """Demo a 2022 sprint weekend with restrictive parc fermé."""
    print("\n" + "=" * 80)
    print("DEMO: 2022 SPRINT WEEKEND (FP1 ONLY - RESTRICTIVE PARC FERMÉ)")
    print("=" * 80)

    # Driver data
    drivers = [
        "Verstappen",
        "Perez",
        "Leclerc",
        "Sainz",
        "Hamilton",
        "Russell",
        "Norris",
        "Piastri",
    ]

    driver_ratings = {
        "Verstappen": 100.5,
        "Perez": 97.5,
        "Leclerc": 99.0,
        "Sainz": 97.0,
        "Hamilton": 98.0,
        "Russell": 97.5,
        "Norris": 96.5,
        "Piastri": 95.5,
    }

    # Create simulator
    simulator = PracticeWeekendSimulator(
        track="Imola",
        track_base_time=82.0,
        weekend_type=WeekendType.SPRINT,
        drivers=drivers,
        driver_ratings=driver_ratings,
        seed=42,
    )

    # Run all sessions
    results = simulator.run_all_sessions()

    # Show parc fermé info
    print("\n" + "=" * 80)
    print("PARC FERMÉ STATUS")
    print("=" * 80)
    print(f"Active: {results.parc_ferme_state.is_active}")
    print(f"Activated After: {results.parc_ferme_state.activated_after}")
    print(f"Weekend Type: {results.parc_ferme_state.weekend_type.value}")

    # Export R ratings
    print("\n" + "=" * 80)
    print("R RATING EXPORT (ONE CHANCE ONLY!)")
    print("=" * 80)

    r_ratings = simulator.get_all_final_r_ratings()
    deltas = simulator.get_r_rating_deltas()

    print(f"{'Driver':<15} {'Base R':<10} {'Delta':<10} {'Final R':<10}")
    print("-" * 50)

    for driver in sorted(drivers, key=lambda d: r_ratings[d], reverse=True):
        base = driver_ratings[driver]
        delta = deltas[driver]
        final = r_ratings[driver]
        print(f"{driver:<15} {base:<10.2f} {delta:>+8.2f}  {final:<10.2f}")

    return simulator


def demo_connector():
    """Demo the RRatingConnector for system integration."""
    print("\n" + "=" * 80)
    print("DEMO: R RATING CONNECTOR FOR SYSTEM INTEGRATION")
    print("=" * 80)

    from src.practice import RRatingConnector

    drivers = ["Verstappen", "Leclerc", "Hamilton"]
    driver_ratings = {
        "Verstappen": 100.5,
        "Leclerc": 99.0,
        "Hamilton": 98.0,
    }

    simulator = PracticeWeekendSimulator(
        track="Monaco",
        track_base_time=72.5,
        weekend_type=WeekendType.NORMAL,
        drivers=drivers,
        driver_ratings=driver_ratings,
        seed=42,
    )

    simulator.run_all_sessions()

    # Create connector
    connector = RRatingConnector(simulator)

    # Get R ratings for different sessions
    print("\nR Ratings for Qualifying:")
    quali_ratings = connector.get_r_for_qualifying()
    for driver, r in sorted(quali_ratings.items(), key=lambda x: x[1], reverse=True):
        print(f"  {driver}: {r:.2f}")

    print("\nR Ratings for Race:")
    race_ratings = connector.get_r_for_race()
    for driver, r in sorted(race_ratings.items(), key=lambda x: x[1], reverse=True):
        print(f"  {driver}: {r:.2f}")

    print("\nSetup Deltas:")
    for driver in drivers:
        delta = connector.get_setup_delta(driver)
        print(f"  {driver}: {delta:+.2f}")

    print("\nExport to Qualifying System:")
    export = connector.export_to_qualifying_system()
    print(f"  Weekend Type: {export['weekend_type']}")
    print(f"  Parc Fermé Active: {export['parc_ferme_active']}")
    print(f"  Number of Drivers: {len(export['driver_ratings'])}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("F1 FREE PRACTICE SYSTEM DEMO")
    print("=" * 80)

    # Run demos
    demo_normal_weekend()
    demo_sprint_weekend()
    demo_connector()

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nThe Free Practice system is ready to use!")
    print("- Normal weekends: FP1, FP2, FP3 with averaged setups")
    print("- 2022 Sprint weekends: FP1 only with restrictive parc fermé")
    print("- R rating export for qualifying and race integration")
    print("=" * 80 + "\n")
