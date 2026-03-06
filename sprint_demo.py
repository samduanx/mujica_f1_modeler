"""
Sprint Race System Demo.

This script demonstrates the sprint race system and how to use the
StartingGridConnector to pass sprint results to the main race.

Usage:
    uv run python sprint_demo.py --track Imola --seed 42
    uv run python sprint_demo.py --track Austria --seed 42
    uv run python sprint_demo.py --track Sao_Paulo --seed 42
"""

import argparse
import sys
import os

# Handle PYTHONPATH for module imports
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Add src directory to path
_src_path = os.path.join(_project_root, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from sprint import run_sprint_race, StartingGridConnector, GridSourceType


def demo_sprint_race(track_name: str, seed: int = 42):
    """
    Run a demo of the sprint race system.

    This demonstrates:
    1. Running a sprint race
    2. Using StartingGridConnector to get grid positions
    3. Showing how results would be passed to main race
    """
    print("=" * 70)
    print("SPRINT RACE SYSTEM DEMO")
    print("=" * 70)
    print(f"\nTrack: {track_name}")
    print(f"Seed: {seed}")

    # Step 1: Run sprint race
    print("\n" + "-" * 70)
    print("STEP 1: Running Sprint Race")
    print("-" * 70)

    sprint_results = run_sprint_race(track_name=track_name, seed=seed)

    # Step 2: Create StartingGridConnector from sprint results
    print("\n" + "-" * 70)
    print("STEP 2: Creating StartingGridConnector")
    print("-" * 70)

    connector = StartingGridConnector.from_sprint_results(sprint_results)

    print(f"\nConnector Source Type: {connector.source_type.value}")
    print(f"Number of Drivers: {len(connector.grid_positions)}")

    # Step 3: Get starting grid
    print("\n" + "-" * 70)
    print("STEP 3: Sprint Race Results (Main Race Starting Grid)")
    print("-" * 70)

    grid_positions = connector.get_starting_grid()
    sorted_grid = connector.get_sorted_grid()

    print("\n| Position | Driver |")
    print("|----------|--------|")
    for pos, driver in sorted_grid:
        print(f"| {pos:8} | {driver:20} |")

    # Step 4: Show source info
    print("\n" + "-" * 70)
    print("STEP 4: Source Information")
    print("-" * 70)

    source_info = connector.get_source_info()
    print(f"\nSource Type: {source_info['source_type']}")
    print(f"Number of Drivers: {source_info['num_drivers']}")

    # Step 5: Demonstrate connector usage for main race
    print("\n" + "-" * 70)
    print("STEP 5: Connector Usage for Main Race")
    print("-" * 70)

    print("\nThe StartingGridConnector can be used in two ways:")
    print("\n1. Direct grid positions:")
    print("   grid = connector.get_starting_grid()")
    print("   # Returns: {driver_name -> grid_position}")

    print("\n2. Apply to driver data:")
    print("   driver_data = connector.apply_to_driver_data(driver_data)")
    print("   # Adds 'grid_position' field to each driver's data")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print(f"\nSprint race results saved to: {sprint_results.get('output_dir', 'N/A')}")
    print("\nThese results would be used to set the starting grid for the main race.")

    return sprint_results, connector


def demo_qualifying_connector():
    """
    Demo the StartingGridConnector with qualifying results (placeholder).

    This shows how the same connector interface will work for qualifying
    when that system is implemented.
    """
    print("\n" + "=" * 70)
    print("QUALIFYING CONNECTOR DEMO (Placeholder)")
    print("=" * 70)

    # Simulated qualifying results
    qualifying_results = {
        "grid_positions": {
            "Verstappen": 1,
            "Leclerc": 2,
            "Hamilton": 3,
            "Sainz": 4,
            "Perez": 5,
        }
    }

    connector = StartingGridConnector.from_qualifying_results(qualifying_results)

    print("\nQualifying results would be processed similarly:")
    print(f"Source Type: {connector.source_type.value}")

    grid = connector.get_starting_grid()
    print("\nGrid Positions:")
    for driver, pos in sorted(grid.items(), key=lambda x: x[1]):
        print(f"  P{pos}: {driver}")


def demo_manual_connector():
    """
    Demo the StartingGridConnector with manual configuration.
    """
    print("\n" + "=" * 70)
    print("MANUAL GRID CONNECTOR DEMO")
    print("=" * 70)

    # Manual grid positions
    manual_grid = {
        "Verstappen": 1,
        "Leclerc": 2,
        "Hamilton": 3,
        "Sainz": 4,
        "Perez": 5,
        "Russell": 6,
        "Norris": 7,
        "Piastri": 8,
    }

    connector = StartingGridConnector.manual(
        grid_positions=manual_grid, description="Test grid for development"
    )

    print(f"\nSource Type: {connector.source_type.value}")
    print(f"Description: {connector.source_data.get('description')}")

    grid = connector.get_starting_grid()
    print("\nManual Grid Configuration:")
    for driver, pos in sorted(grid.items(), key=lambda x: x[1]):
        print(f"  P{pos}: {driver}")


def main():
    parser = argparse.ArgumentParser(description="Sprint Race System Demo")
    parser.add_argument(
        "--track",
        type=str,
        default="Imola",
        choices=["Imola", "Austria", "Sao_Paulo"],
        help="Sprint race track",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--demo-all",
        action="store_true",
        help="Run all connector demos",
    )

    args = parser.parse_args()

    # Run main sprint demo
    demo_sprint_race(args.track, args.seed)

    # Run additional demos if requested
    if args.demo_all:
        demo_qualifying_connector()
        demo_manual_connector()

    return 0


if __name__ == "__main__":
    sys.exit(main())
