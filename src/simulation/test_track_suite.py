"""
Test Suite for Running F1 Simulations on Multiple Distinctive Tracks.

This test suite runs simulations for at least 4 distinctive tracks:
- Monaco (street circuit, low speed, high complexity)
- Monza (high speed, low downforce)
- Spain (technical, medium speed)
- Japan (high downforce, technical)

Usage:
    uv run python src/simulation/test_track_suite.py
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Handle PYTHONPATH for module imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Import the enhanced simulation module
from simulation.enhanced_long_dist_sim import main as run_simulation


# =============================================================================
# TRACK CONFIGURATION
# =============================================================================


@dataclass
class TrackConfig:
    """Configuration for a specific track."""

    name: str
    year: int
    seed: int
    description: str
    characteristics: str
    gp_name: str = (
        None  # Override for gp-name if different from name (e.g., Monza -> Italy)
    )


# Track configurations for the test suite
# Note: Monza is the Italian GP, so we use "Italy" as the gp-name for track characteristics
TRACK_CONFIGS: List[TrackConfig] = [
    TrackConfig(
        name="Monaco",
        year=2024,
        seed=42,
        description="Street circuit - low speed, high complexity, tight corners",
        characteristics="Street | Low Speed | High Complexity",
    ),
    TrackConfig(
        name="Monza",
        year=2024,
        seed=123,
        description="High speed circuit - low downforce, longest straights",
        characteristics="High Speed | Low Downforce | Power Track",
        gp_name="Italy",  # Monza = Italian GP in the simulation
    ),
    TrackConfig(
        name="Spain",
        year=2024,
        seed=456,
        description="Technical circuit - medium speed, challenging corners",
        characteristics="Technical | Medium Speed | High Downforce",
    ),
    TrackConfig(
        name="Japan",
        year=2024,
        seed=789,
        description="High downforce - technical, demanding corners",
        characteristics="High Downforce | Technical | Fast Corners",
    ),
]

# All available tracks (for reference)
ALL_TRACKS: List[str] = [
    "Monaco",
    "Monza",
    "Spain",
    "Bahrain",
    "Australia",
    "Japan",
    "China",
    "Italy",
]


# =============================================================================
# OUTPUT DIRECTORY SETUP
# =============================================================================

RACE_REPORTS_DIR = os.path.join("outputs", "race_reports")
os.makedirs(RACE_REPORTS_DIR, exist_ok=True)


# =============================================================================
# DRIVER DATA GENERATION
# =============================================================================

# Default driver/team data for generating CSV files
# Matches docs/spain_ratings.csv reference file
DEFAULT_DRIVER_DATA = [
    # Red Bull
    ("Verstappen", "Red Bull", 100.5, 308.34, 309.89),
    ("Perez", "Red Bull", 99.925, 308.34, 308.11),
    # Mercedes
    ("Hamilton", "Mercedes", 100.4, 308.00, 309.23),
    ("Russell", "Mercedes", 100.0, 308.00, 308.00),
    # Ferrari
    ("Leclerc", "Ferrari", 100.4, 307.71, 308.94),
    ("Sainz", "Ferrari", 99.95, 307.71, 307.55),
    # AlphaTauri
    ("Gasly", "AlphaTauri", 100.1, 299.54, 299.84),
    ("Tsunoda", "AlphaTauri", 99.85, 299.54, 299.09),
    # Alpine
    ("Alonso", "Alpine", 100.5, 296.16, 297.64),
    ("Ocon", "Alpine", 99.85, 296.16, 295.72),
    # Aston Martin
    ("Vettel", "Aston Martin", 100.3, 296.58, 297.46),
    ("Stroll", "Aston Martin", 99.7, 296.58, 295.69),
    # Andretti
    ("Grosjean", "Andretti", 100.1, 294.55, 294.84),
    ("Schwartzman", "Andretti", 99.6, 294.55, 293.37),
    # McLaren
    ("Norris", "McLaren", 100.1, 294.38, 294.67),
    ("Piastri", "McLaren", 99.875, 294.38, 294.01),
    # Alfa Romeo
    ("Bottas", "Alfa Romeo", 100.2, 293.98, 294.57),
    ("Zhou", "Alfa Romeo", 99.65, 293.98, 292.95),
    # Haas
    ("Magnussen", "Haas", 100.1, 290.03, 290.32),
    ("Schumacher", "Haas", 99.675, 290.03, 289.08),
    # Williams
    ("Albon", "Williams", 100.1, 289.55, 289.84),
    ("Latifi", "Williams", 99.625, 289.55, 288.46),
]  # 22 drivers total - matches reference file docs/spain_ratings.csv


def create_driver_csv(track_name: str, output_dir: str = "outputs/tables") -> str:
    """
    Create a driver CSV file for a given track if it doesn't exist.

    Args:
        track_name: Name of the track (e.g., "Monaco", "Monza")
        output_dir: Directory to save the CSV file

    Returns:
        Path to the CSV file
    """
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, f"{track_name}.csv")

    # If file already exists, return the path
    if os.path.exists(csv_path):
        return csv_path

    # Create the CSV file with driver data
    with open(csv_path, "w") as f:
        f.write("Driver,Team,DR,PR,RO\n")

        # Apply track-specific adjustments to performance
        for driver, team, dr, pr, ro in DEFAULT_DRIVER_DATA:
            # Adjust values based on track characteristics
            if track_name == "Monaco":
                # Monaco favors technical drivers, slightly slower times
                adjusted_pr = pr * 1.08  # Slower due to tight corners
                adjusted_ro = ro * 1.06
            elif track_name == "Monza":
                # Monza - high speed, faster times
                adjusted_pr = pr * 0.92  # Faster due to long straights
                adjusted_ro = ro * 0.93
            elif track_name == "Spain":
                # Spain - medium speed, baseline
                adjusted_pr = pr
                adjusted_ro = ro
            elif track_name == "Japan":
                # Japan - high downforce, technical
                adjusted_pr = pr * 1.02
                adjusted_ro = ro * 1.01
            elif track_name == "Bahrain":
                # Bahrain - desert track
                adjusted_pr = pr * 0.98
                adjusted_ro = ro * 0.99
            elif track_name == "Australia":
                # Australia - street/technical
                adjusted_pr = pr * 1.04
                adjusted_ro = ro * 1.03
            elif track_name == "China":
                # China - mixed layout
                adjusted_pr = pr * 1.01
                adjusted_ro = ro * 1.00
            elif track_name == "Italy":
                # Italy - Monza-like
                adjusted_pr = pr * 0.93
                adjusted_ro = ro * 0.94
            else:
                # Default - no adjustment
                adjusted_pr = pr
                adjusted_ro = ro

            f.write(f"{driver},{team},{dr},{adjusted_pr:.2f},{adjusted_ro:.2f}\n")

    print(f"Created driver CSV: {csv_path}")
    return csv_path


# =============================================================================
# RACE REPORT GENERATION
# =============================================================================


def generate_race_report(
    track_name: str,
    year: int,
    seed: int,
    success: bool,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None,
    gp_name: Optional[str] = None,
) -> str:
    """
    Generate a race report summary.

    Args:
        track_name: Name of the track (display name)
        year: Race year
        seed: Random seed used
        success: Whether simulation completed successfully
        output_path: Path to race results if successful
        error_message: Error message if failed
        gp_name: GP name used for file naming (defaults to track_name)

    Returns:
        Path to the generated report
    """
    # Use gp_name for file naming if provided
    file_name_base = (gp_name or track_name).lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_path is None:
        report_path = os.path.join(
            RACE_REPORTS_DIR, f"race_report_{file_name_base}_{year}_{timestamp}.md"
        )
    else:
        base_name = os.path.basename(output_path).replace(".csv", "")
        report_path = os.path.join(RACE_REPORTS_DIR, f"{base_name}_report.md")

    # Find the corresponding dice rolls file (use gp_name for file lookup)
    dice_rolls_path = os.path.join(
        "outputs",
        "enhanced_sim",
        "dice_rolls",
        f"dice_rolls_{file_name_base}_{year}.csv",
    )

    race_results_path = os.path.join(
        "outputs",
        "enhanced_sim",
        "race_results",
        f"race_results_{file_name_base}_{year}.csv",
    )

    # Get track config for description (use track_name for config lookup)
    track_config = next(
        (t for t in TRACK_CONFIGS if t.name == track_name and t.year == year), None
    )
    description = track_config.description if track_config else "Unknown track"
    characteristics = track_config.characteristics if track_config else "Unknown"

    with open(report_path, "w") as f:
        f.write(f"# Race Report: {track_name} {year}\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"## Track Information\n\n")
        f.write(f"- **Track:** {track_name}\n")
        f.write(f"- **Year:** {year}\n")
        f.write(f"- **Random Seed:** {seed}\n")
        f.write(f"- **Description:** {description}\n")
        f.write(f"- **Characteristics:** {characteristics}\n\n")

        f.write(f"## Simulation Status\n\n")
        if success:
            f.write(f"✅ **Status:** Completed Successfully\n\n")
            f.write(f"## Output Files\n\n")
            f.write(f"- Race Results: `{race_results_path}`\n")
            f.write(f"- Dice Rolls: `{dice_rolls_path}`\n")
        else:
            f.write(f"❌ **Status:** Failed\n\n")
            f.write(f"## Error\n\n")
            f.write(f"```\n{error_message}\n```\n")

    return report_path


def copy_results_to_reports(track_name: str, year: int) -> List[str]:
    """
    Copy simulation results to the race reports directory.

    Args:
        track_name: Name of the track
        year: Race year

    Returns:
        List of copied file paths
    """
    copied_files = []

    # Source directories
    source_dirs = [
        os.path.join("outputs", "enhanced_sim", "race_results"),
        os.path.join("outputs", "enhanced_sim", "dice_rolls"),
    ]

    for source_dir in source_dirs:
        if not os.path.exists(source_dir):
            continue

        # Find files for this track
        for filename in os.listdir(source_dir):
            if filename.endswith(f"_{track_name.lower()}_{year}.csv"):
                source_path = os.path.join(source_dir, filename)
                dest_path = os.path.join(RACE_REPORTS_DIR, filename)

                try:
                    shutil.copy2(source_path, dest_path)
                    copied_files.append(dest_path)
                except Exception as e:
                    print(f"Warning: Could not copy {filename}: {e}")

    return copied_files


# =============================================================================
# TEST RUNNER
# =============================================================================


def run_track_simulation(
    track_config: TrackConfig, verbose: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Run simulation for a single track.

    Args:
        track_config: Track configuration
        verbose: Whether to print progress

    Returns:
        Tuple of (success, error_message)
    """
    track_name = track_config.name
    year = track_config.year
    seed = track_config.seed
    # Use gp_name if specified (e.g., Monza -> Italy)
    gp_name = track_config.gp_name if track_config.gp_name else track_name

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Running simulation for: {track_name} {year}")
        print(f"Seed: {seed}")
        print(f"Description: {track_config.description}")
        print(f"{'=' * 60}")

    try:
        # Create driver CSV if needed (use display name for CSV file)
        csv_path = create_driver_csv(track_name)

        # Run simulation with CLI arguments
        # We need to call the simulation programmatically
        argv = [
            "--gp-name",
            gp_name,  # Use gp_name for the simulation
            "--seed",
            str(seed),
            "--csv-file",
            csv_path,
        ]

        if verbose:
            print(f"\nExecuting: enhanced simulation with args: {argv}")

        # Run the simulation
        run_simulation(argv)

        # Copy results to race reports (use gp_name for file naming)
        copied = copy_results_to_reports(gp_name, year)

        if verbose:
            print(f"\n✅ {track_name} {year} - Simulation completed successfully!")
            print(f"   Results copied to: {copied}")

        # Generate report
        report_path = generate_race_report(
            track_name=track_name,  # Keep display name
            gp_name=gp_name,  # Use gp_name for file naming
            year=year,
            seed=seed,
            success=True,
            output_path=copied[0] if copied else None,
        )

        if verbose:
            print(f"   Report: {report_path}")

        return True, None

    except Exception as e:
        error_msg = str(e)

        if verbose:
            print(f"\n❌ {track_name} {year} - Simulation failed!")
            print(f"   Error: {error_msg}")

        # Generate failure report
        report_path = generate_race_report(
            track_name=track_name,  # Keep display name
            gp_name=gp_name,  # Use gp_name for file naming
            year=year,
            seed=seed,
            success=False,
            error_message=error_msg,
        )

        if verbose:
            print(f"   Report: {report_path}")

        return False, error_msg


def run_all_track_tests(
    track_configs: Optional[List[TrackConfig]] = None,
    stop_on_error: bool = False,
    verbose: bool = True,
) -> Dict[str, Dict]:
    """
    Run simulations for all configured tracks.

    Args:
        track_configs: List of track configurations (defaults to TRACK_CONFIGS)
        stop_on_error: Whether to stop on first error
        verbose: Whether to print progress

    Returns:
        Dictionary of results per track
    """
    if track_configs is None:
        track_configs = TRACK_CONFIGS

    results = {}

    if verbose:
        print("\n" + "=" * 60)
        print("F1 TRACK TEST SUITE")
        print("=" * 60)
        print(f"Running simulations for {len(track_configs)} tracks:")
        for tc in track_configs:
            print(f"  - {tc.name} ({tc.year}) - {tc.characteristics}")
        print("=" * 60)

    # Ensure output directories exist
    os.makedirs(RACE_REPORTS_DIR, exist_ok=True)
    os.makedirs("outputs/enhanced_sim/race_results", exist_ok=True)
    os.makedirs("outputs/enhanced_sim/dice_rolls", exist_ok=True)

    # Run each track simulation
    for i, track_config in enumerate(track_configs, 1):
        if verbose:
            print(f"\n[{i}/{len(track_configs)}] ", end="")

        success, error = run_track_simulation(track_config, verbose=verbose)

        results[track_config.name] = {
            "success": success,
            "error": error,
            "year": track_config.year,
            "seed": track_config.seed,
        }

        if not success and stop_on_error:
            print("\n⚠️ Stopping due to error (stop_on_error=True)")
            break

    return results


def print_summary(results: Dict[str, Dict]) -> None:
    """Print a summary of all test results."""
    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print("=" * 60)

    total = len(results)
    successful = sum(1 for r in results.values() if r["success"])
    failed = total - successful

    print(f"\nTotal Tracks: {total}")
    print(f"Successful:  {successful}")
    print(f"Failed:      {failed}")

    if failed > 0:
        print("\nFailed Tracks:")
        for track_name, result in results.items():
            if not result["success"]:
                print(f"  - {track_name}: {result['error']}")

    print("\n" + "=" * 60)
    print(f"Results saved to: {RACE_REPORTS_DIR}")
    print("=" * 60)


# =============================================================================
# MAIN FUNCTION
# =============================================================================


def main(argv=None):
    """
    Main entry point for the test suite.

    Usage:
        uv run python src/simulation/test_track_suite.py
        uv run python src/simulation/test_track_suite.py --tracks Monaco Spain
        uv run python src/simulation/test_track_suite.py --stop-on-error
    """
    parser = argparse.ArgumentParser(
        description="Run F1 simulations on multiple distinctive tracks"
    )
    parser.add_argument(
        "--tracks",
        nargs="+",
        help="Specific tracks to run (default: all 4 distinctive tracks)",
        choices=ALL_TRACKS,
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop running if any simulation fails",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )
    parser.add_argument(
        "--list-tracks",
        action="store_true",
        help="List all available tracks and exit",
    )

    args = parser.parse_args(argv)

    if args.list_tracks:
        print("Available tracks:")
        for track in ALL_TRACKS:
            # Find config if exists
            config = next((t for t in TRACK_CONFIGS if t.name == track), None)
            if config:
                print(f"  - {track}: {config.characteristics}")
            else:
                print(f"  - {track}")
        return

    # Determine which tracks to run
    if args.tracks:
        # Filter configs for requested tracks
        selected_tracks = [tc for tc in TRACK_CONFIGS if tc.name in args.tracks]

        # Check for unknown tracks
        unknown = set(args.tracks) - {tc.name for tc in TRACK_CONFIGS}
        if unknown:
            print(f"Warning: Unknown tracks: {unknown}")

        if not selected_tracks:
            print("Error: No valid tracks selected")
            return
    else:
        selected_tracks = TRACK_CONFIGS

    # Run simulations
    results = run_all_track_tests(
        track_configs=selected_tracks,
        stop_on_error=args.stop_on_error,
        verbose=not args.quiet,
    )

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    failed = sum(1 for r in results.values() if not r["success"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
