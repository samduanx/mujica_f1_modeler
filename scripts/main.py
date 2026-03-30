"""
F1 Race Weekend Simulator - Main Entry Point

This module serves as the main entrance for simulating complete F1 race weekends,
including all sessions:
- FP1 (Free Practice 1) - placeholder, not yet implemented
- FP2 (Free Practice 2) - placeholder, not yet implemented
- FP3 (Free Practice 3) - placeholder, not yet implemented
- Qualifying (Q1, Q2, Q3) - implemented with tyre allocation and incidents
- Sprint - 100km sprint race (Imola, Austria, Sao Paulo)
- Race - fully implemented using enhanced_long_dist_sim

Configuration:
    All track, session, driver, and lap time data is loaded from JSON files
    in the data/ directory:
    - data/tracks.json: Track configurations (available_tracks, sprint_tracks)
    - data/sessions.json: Session types and configurations
    - data/drivers.json: Driver and team data (2024 grid)
    - data/track_lap_times.json: Base lap times for tracks

Supported Tracks:
- Monaco, Spain, Monza, Italy, Australia, Bahrain, China, Japan, Austria

Sprint Race Tracks (2022):
- Imola (Emilia Romagna GP) - 21 laps, ~100km
- Austria (Red Bull Ring) - 24 laps, ~100km
- Sao_Paulo (Brazil GP) - 24 laps, ~100km

Usage:
    # Run a full race weekend (runs all sessions - FP1/FP2/FP3 are placeholders)
    uv run python scripts/main.py --gp-name Monaco

    # Run only the race
    uv run python scripts/main.py --gp-name Monaco --sessions race

    # Run qualifying and race
    uv run python scripts/main.py --gp-name Spain --sessions qualifying,race

    # Run sprint race and main race (sprint weekend format)
    uv run python scripts/main.py --gp-name Imola --sessions sprint,race

    # Run only sprint race
    uv run python scripts/main.py --gp-name Austria --sessions sprint

    # Run multiple tracks
    uv run python scripts/main.py --tracks Monaco,Spain,Monza

    # Run test suite (runs race simulation on all distinctive tracks)
    uv run python scripts/main.py --test-suite

    # With random seed for reproducibility
    uv run python scripts/main.py --gp-name Monaco --seed 42
"""

import argparse
import sys
import os
import shutil
import glob
from datetime import datetime
from typing import List, Optional, Dict, Any

# Handle PYTHONPATH for module imports (scripts/ is inside project root)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_path = os.path.join(_project_root, "src")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from src.utils.config_loader import (
    get_available_tracks,
    get_sprint_tracks,
    get_all_tracks,
    get_track_config,
    is_sprint_track,
    get_session_types,
    get_output_base_dir,
    get_qualifying_sessions_config,
    get_practice_config,
    get_sprint_config,
    get_drivers,
    get_teams,
    get_driver_team,
    get_top_tier_drivers,
    get_bottom_tier_drivers,
    get_track_lap_time,
    get_default_lap_time,
)


# =============================================================================
# CONFIGURATION ACCESS
# =============================================================================

# These module-level constants provide backward-compatible access to
# configuration data loaded from JSON files in the data/ directory.
AVAILABLE_TRACKS = get_available_tracks()
SPRINT_TRACKS = get_sprint_tracks()
SESSION_TYPES = get_session_types()
OUTPUT_BASE_DIR = get_output_base_dir()


# =============================================================================
# Andretti team participates in these Grand Prix (22 drivers total):
# =============================================================================
ANDRETTI_GP_ATTENDANCE = [
    "miami",  # Miami GP
    "spain",  # Spain GP
    "canada",  # Canada GP
    "hungary",  # Hungary GP
    "italy",  # Italy (Monza)
    "monza",  # Monza (alias for Italy)
    "singapore",  # Singapore GP
    "united states",  # US (Austin)
    "united_states",  # US (Austin) - alternative key
    "austin",  # US (Austin) - alternative key
    "mexico",  # Mexico GP
    "brazil",  # Brazil GP
]


def is_andretti_participating(gp_name: str) -> bool:
    """Check if Andretti team participates in the given GP."""
    gp_lower = gp_name.lower().strip()
    return gp_lower in ANDRETTI_GP_ATTENDANCE


def filter_andretti_drivers_for_gp(drivers: List[str], gp_name: str) -> List[str]:
    """
    Filter out Andretti drivers if they don't participate in this GP.

    Args:
        drivers: List of driver names
        gp_name: Name of the Grand Prix

    Returns:
        Filtered list of drivers (Andretti drivers removed if not attending)
    """
    if is_andretti_participating(gp_name):
        return drivers

    teams = get_teams()
    return [d for d in drivers if teams.get(d) != "Andretti"]


def get_race_weekend_output_dir(
    track_name: str, runtime_datetime: Optional[datetime] = None
) -> str:
    """
    Create and return the output directory for a race weekend.

    Args:
        track_name: Name of the track
        runtime_datetime: Runtime timestamp (default: now)

    Returns:
        Path to the output directory
    """
    if runtime_datetime is None:
        runtime_datetime = datetime.now()

    datetime_str = runtime_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{track_name}_{datetime_str}"
    output_dir = os.path.join(OUTPUT_BASE_DIR, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def create_session_subdirs(base_dir: str, sessions: List[str]) -> Dict[str, str]:
    """
    Create subdirectories for each session.

    Args:
        base_dir: Base output directory
        sessions: List of session names

    Returns:
        Dictionary mapping session names to their directory paths
    """
    session_dirs = {}
    for session in sessions:
        session_dir = os.path.join(base_dir, session)
        os.makedirs(session_dir, exist_ok=True)
        session_dirs[session] = session_dir
    return session_dirs


def copy_race_outputs_to_weekend(
    source_dir: str,
    dest_dir: str,
    gp_name: str,
) -> dict:
    """
    Copy race simulation outputs to race weekend subdirectory.

    Args:
        source_dir: Source directory (outputs/enhanced_sim/{track}_{datetime})
        dest_dir: Destination directory (race weekend race/ subfolder)
        gp_name: GP/track name for file naming

    Returns:
        Dictionary with paths to copied files
    """
    os.makedirs(dest_dir, exist_ok=True)

    copied_files = {}

    # Files to copy
    files_to_copy = [
        f"race_results_{gp_name.lower()}.csv",
        f"dice_rolls_{gp_name.lower()}.csv",
        f"race_report_{gp_name.lower()}.md",
    ]

    for filename in files_to_copy:
        src_path = os.path.join(source_dir, filename)
        if os.path.exists(src_path):
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(src_path, dest_path)
            copied_files[filename] = dest_path

    return copied_files


def generate_session_summary(
    session: str,
    track_name: str,
    status: str,
    output_dir: str,
) -> str:
    """
    Generate a simple session summary markdown file.

    Args:
        session: Session name (fp1, fp2, fp3, qualifying, race)
        track_name: Track name
        status: Session status
        output_dir: Directory to save the summary

    Returns:
        Path to the generated summary file
    """
    summary_lines = [
        f"# {session.upper()} Session Summary",
        "",
        f"**Track:** {track_name}",
        f"**Session:** {session.upper()}",
        f"**Status:** {status}",
        "",
    ]

    if status == "not_implemented":
        summary_lines.extend(
            [
                "## Notes",
                "",
                "This session type is not yet implemented.",
                "",
                "Future implementation will include:",
                "",
            ]
        )
        # Load session features from configuration
        if session in ["fp1", "fp2", "fp3"]:
            practice_config = get_practice_config(session)
            if practice_config and "features" in practice_config:
                for feature in practice_config["features"]:
                    summary_lines.append(f"- {feature}")
        elif session == "qualifying":
            # Load qualifying config from sessions.json
            qual_config = get_qualifying_sessions_config(is_sprint_weekend=False)
            for q_session in qual_config:
                summary_lines.append(
                    f"- {q_session['name']}: {q_session['duration_minutes']} minutes ({q_session['description']})"
                )
        elif session == "sprint":
            sprint_config = get_sprint_config()
            if sprint_config and "features" in sprint_config:
                for feature in sprint_config["features"]:
                    summary_lines.append(f"- {feature}")
    elif status == "completed":
        summary_lines.extend(["## Results", ""])

        # For race sessions, try to read and display results from CSV
        if session == "race":
            csv_path = os.path.join(
                output_dir, f"race_results_{track_name.lower()}.csv"
            )
            if os.path.exists(csv_path):
                try:
                    import csv as csv_module

                    with open(csv_path, "r", encoding="utf-8") as f:
                        reader = csv_module.DictReader(f)
                        rows = list(reader)

                    summary_lines.append("**Race Results:**")
                    summary_lines.append("")
                    summary_lines.append("| Pos | Driver | Team | Total Time | Pits |")
                    summary_lines.append("|-----|--------|------|------------|------|")
                    for row in rows:
                        try:
                            total_time = float(row.get("total_time", 0))
                            summary_lines.append(
                                f"| {row.get('position', '')} | {row.get('driver', '')} | "
                                f"{row.get('team', '')} | {total_time:.3f}s | "
                                f"{row.get('num_pits', '')} |"
                            )
                        except (ValueError, TypeError):
                            summary_lines.append(
                                f"| {row.get('position', '')} | {row.get('driver', '')} | "
                                f"{row.get('team', '')} | {row.get('total_time', 'N/A')} | "
                                f"{row.get('num_pits', '')} |"
                            )
                    summary_lines.append("")
                except Exception as e:
                    summary_lines.append(
                        f"Race completed. Results saved to CSV file: {e}"
                    )
                    summary_lines.append("")
            else:
                summary_lines.append("Race simulation completed successfully.")
                summary_lines.append("")
        else:
            summary_lines.append("Simulation completed successfully.")
            summary_lines.append("")
    elif status == "error":
        summary_lines.extend(
            [
                "## Error",
                "",
                "An error occurred during simulation.",
            ]
        )

    summary_content = "\n".join(summary_lines)
    summary_path = os.path.join(output_dir, f"session_summary_{session}.md")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_content)

    return summary_path


# =============================================================================
# SESSION SIMULATION MODULES (PLACEHOLDERS FOR NOT-YET-IMPLEMENTED MODULES)
# =============================================================================


# Global practice session storage (persisted across FP1/FP2/FP3)
_practice_sessions: Dict[str, Any] = {}


def _merge_setup_tuning_deltas(
    session_deltas: List[Dict[str, float]],
) -> Dict[str, float]:
    """Merge multiple setup tuning delta dicts by averaging per driver."""
    if not session_deltas:
        return {}

    merged: Dict[str, List[float]] = {}
    for deltas in session_deltas:
        for driver, delta in deltas.items():
            merged.setdefault(driver, []).append(float(delta))

    return {driver: sum(values) / len(values) for driver, values in merged.items()}


def _collect_setup_tuning_deltas(results: Dict[str, dict]) -> Dict[str, float]:
    """
    Collect setup tuning deltas from completed practice sessions.

    Priority:
    1) FP3 parc fermé final deltas (normal weekend)
    2) Average of available FP setup deltas (FP1/FP2)
    """
    fp3 = results.get("fp3") or results.get("practice3")
    if fp3 and fp3.get("status") == "completed":
        fp3_deltas = fp3.get("r_rating_deltas", {})
        if fp3_deltas:
            return {driver: float(delta) for driver, delta in fp3_deltas.items()}

    session_deltas: List[Dict[str, float]] = []
    for key in ["fp1", "practice1", "fp2", "practice2"]:
        session_result = results.get(key)
        if session_result and session_result.get("status") == "completed":
            deltas = session_result.get("setup_results", {})
            if deltas:
                session_deltas.append(deltas)

    return _merge_setup_tuning_deltas(session_deltas)


def _get_driver_ratings(track_name: str) -> Dict[str, float]:
    """Get base driver ratings with track-specific adjustments."""
    drivers = get_drivers()
    base_ratings = {
        "Verstappen": 100.0,
        "Perez": 99.6,
        "Leclerc": 99.8,
        "Sainz": 99.5,
        "Hamilton": 99.7,
        "Russell": 99.4,
        "Norris": 100.1,
        "Ricciardo": 99.875,
        "Alonso": 99.2,
        "Ocon": 99.3,
        "Gasly": 99.35,
        "Tsunoda": 99.45,
        "Vettel": 99.1,
        "Stroll": 99.25,
        "Albon": 99.15,
        "Latifi": 98.9,
        "Bottas": 100.2,
        "Zhou": 99.65,
        "Schumacher": 98.95,
        "Magnussen": 99.05,
        "Hulkenberg": 98.85,
        "Grosjean": 98.75,
        "Schwartzman": 99.6,
    }

    driver_ratings = {}
    for driver in drivers:
        base = base_ratings.get(driver, 99.5)
        if track_name == "Monaco":
            if driver in ["Leclerc", "Alonso", "Hamilton"]:
                base -= 0.1
        elif track_name in ["Monza", "Italy"]:
            if driver in ["Verstappen", "Hamilton"]:
                base -= 0.1
        driver_ratings[driver] = base

    return driver_ratings


def simulate_fp1(
    track_name: str,
    output_dir: Optional[str] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> dict:
    """
    Simulate Free Practice 1 session.
    """
    print(f"\n{'=' * 60}")
    print(f"FP1 - Free Practice 1 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")

    try:
        import csv
        from src.practice import PracticeSessionManager, PracticeSessionType

        # Get driver ratings
        driver_ratings = _get_driver_ratings(track_name)
        base_lap_time = get_track_lap_time(track_name, 80.0)

        # Filter Andretti drivers if not participating
        all_drivers = get_drivers()
        filtered_drivers = filter_andretti_drivers_for_gp(all_drivers, track_name)

        # Create and run FP1 session
        fp1_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP1,
            track=track_name,
            track_base_time=base_lap_time,
            drivers=filtered_drivers,
            driver_ratings=driver_ratings,
            duration_minutes=60,
            seed=seed,
        )
        fp1_results = fp1_manager.run_session()

        # Store results for later sessions
        global _practice_sessions
        _practice_sessions["fp1"] = fp1_results

        print(f"\nFP1 Complete - Setup tuning results recorded")
        print(f"  {len(fp1_results.setup_results)} drivers completed setup tuning")

        if output_dir:
            generate_session_summary("fp1", track_name, "completed", output_dir)

            # Generate full report and CSVs
            os.makedirs(output_dir, exist_ok=True)
            teams = get_teams()

            # 1. Generate results CSV
            results_csv_path = os.path.join(
                output_dir, f"fp1_results_{track_name.lower()}.csv"
            )
            with open(results_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Driver", "Team", "Best Lap (s)", "Laps Completed", "R Delta"]
                )
                for driver in fp1_results.best_times.keys():
                    best_time = fp1_results.best_times.get(driver, 0)
                    laps = len(fp1_results.lap_times.get(driver, []))
                    r_delta = fp1_results.setup_results.get(driver, None)
                    r_delta_val = r_delta.r_rating_delta if r_delta else 0.0
                    writer.writerow(
                        [
                            driver,
                            teams.get(driver, "Unknown"),
                            f"{best_time:.3f}" if best_time < float("inf") else "",
                            laps,
                            f"{r_delta_val:+.2f}" if r_delta else "",
                        ]
                    )
            print(f"FP1 results saved to: {results_csv_path}")

            # 2. Generate dice rolls CSV
            dice_csv_path = os.path.join(
                output_dir, f"dice_rolls_{track_name.lower()}.csv"
            )
            with open(dice_csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Driver", "Category", "Roll Value", "R Delta"])
                for driver, setup in fp1_results.setup_results.items():
                    writer.writerow(
                        [
                            driver,
                            "aerodynamics",
                            setup.aerodynamics,
                            f"{setup.r_rating_delta:+.2f}",
                        ]
                    )
                    writer.writerow([driver, "suspension", setup.suspension, ""])
                    writer.writerow([driver, "differential", setup.differential, ""])
                    writer.writerow([driver, "brake_balance", setup.brake_balance, ""])
                    writer.writerow([driver, "tyre_pressure", setup.tyre_pressure, ""])
            print(f"FP1 dice rolls saved to: {dice_csv_path}")

            # 3. Generate full markdown report
            report_path = os.path.join(
                output_dir, f"fp1_report_{track_name.lower()}.md"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# FP1 Report - {track_name}\n\n")
                f.write(f"**Session:** Free Practice 1\n\n")
                f.write(f"**Track:** {track_name}\n\n")

                # Results table
                f.write("## Session Results\n\n")
                f.write("| Pos | Driver | Team | Best Lap | Laps | R Delta |\n")
                f.write("|-----|--------|------|----------|------|---------|\n")

                # Sort by best lap time
                standings = sorted(
                    fp1_results.best_times.items(),
                    key=lambda x: x[1] if x[1] < float("inf") else 9999,
                )
                for pos, (driver, best_time) in enumerate(standings, 1):
                    laps = len(fp1_results.lap_times.get(driver, []))
                    r_delta = fp1_results.setup_results.get(driver, None)
                    r_delta_str = f"{r_delta.r_rating_delta:+.2f}" if r_delta else ""
                    best_str = f"{best_time:.3f}" if best_time < float("inf") else ""
                    team = teams.get(driver, "Unknown")
                    f.write(
                        f"| {pos} | {driver} | {team} | {best_str} | {laps} | {r_delta_str} |\n"
                    )

                # Setup tuning results
                f.write("\n## Setup Tuning Results\n\n")
                f.write(
                    "| Driver | Aero | Susp | Diff | Brake | Tyre | Total | R Delta |\n"
                )
                f.write(
                    "|--------|------|------|------|-------|------|-------|---------|\n"
                )
                for driver, setup in fp1_results.setup_results.items():
                    f.write(
                        f"| {driver} | {setup.aerodynamics} | {setup.suspension} | "
                        f"{setup.differential} | {setup.brake_balance} | {setup.tyre_pressure} | "
                        f"{setup.total_effect:+.1f} | {setup.r_rating_delta:+.2f} |\n"
                    )

                f.write("\n## Session Statistics\n\n")
                f.write(f"- Total Laps: {fp1_results.total_laps}\n")
                f.write(f"- Incidents: {len(fp1_results.incidents)}\n")

            print(f"FP1 report saved to: {report_path}")

        return {
            "session": "fp1",
            "status": "completed",
            "track": track_name,
            "setup_results": {
                d: r.r_rating_delta for d, r in fp1_results.setup_results.items()
            },
        }

    except Exception as e:
        print(f"Error during FP1 simulation: {e}")
        import traceback

        traceback.print_exc()

        if output_dir:
            generate_session_summary("fp1", track_name, "error", output_dir)

        return {
            "session": "fp1",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


def simulate_fp2(
    track_name: str,
    output_dir: Optional[str] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> dict:
    """
    Simulate Free Practice 2 session.
    """
    print(f"\n{'=' * 60}")
    print(f"FP2 - Free Practice 2 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")

    try:
        import csv
        from src.practice import PracticeSessionManager, PracticeSessionType

        # Get driver ratings
        driver_ratings = _get_driver_ratings(track_name)
        base_lap_time = get_track_lap_time(track_name, 80.0)

        # Filter Andretti drivers if not participating
        all_drivers = get_drivers()
        filtered_drivers = filter_andretti_drivers_for_gp(all_drivers, track_name)

        # Create and run FP2 session
        fp2_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP2,
            track=track_name,
            track_base_time=base_lap_time,
            drivers=filtered_drivers,
            driver_ratings=driver_ratings,
            duration_minutes=60,
            seed=seed + 1 if seed else None,
        )
        fp2_results = fp2_manager.run_session()

        # Store results
        global _practice_sessions
        _practice_sessions["fp2"] = fp2_results

        print(f"\nFP2 Complete - Setup tuning results recorded")
        print(f"  {len(fp2_results.setup_results)} drivers completed setup tuning")

        if output_dir:
            generate_session_summary("fp2", track_name, "completed", output_dir)

            # Get teams for report
            teams = get_teams()

            # 1. Save results CSV
            results_csv_path = os.path.join(
                output_dir, f"fp2_results_{track_name.lower()}.csv"
            )
            with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Driver", "Team", "Best Lap", "Laps", "R Delta"])

                # Sort by best lap time
                standings = sorted(
                    fp2_results.best_times.items(),
                    key=lambda x: x[1] if x[1] < float("inf") else 9999,
                )
                for driver, best_time in standings:
                    laps = len(fp2_results.lap_times.get(driver, []))
                    r_delta = fp2_results.setup_results.get(driver, None)
                    r_delta_val = r_delta.r_rating_delta if r_delta else 0.0
                    best_str = f"{best_time:.3f}" if best_time < float("inf") else ""
                    team = teams.get(driver, "Unknown")
                    writer.writerow(
                        [driver, team, best_str, laps, f"{r_delta_val:+.2f}"]
                    )

            print(f"FP2 results saved to: {results_csv_path}")

            # 2. Save dice rolls CSV
            dice_csv_path = os.path.join(
                output_dir, f"fp2_dice_rolls_{track_name.lower()}.csv"
            )
            with open(dice_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Driver", "Category", "Roll Value", "R Delta"])
                for driver, setup in fp2_results.setup_results.items():
                    writer.writerow([driver, "aerodynamics", setup.aerodynamics, ""])
                    writer.writerow([driver, "suspension", setup.suspension, ""])
                    writer.writerow([driver, "differential", setup.differential, ""])
                    writer.writerow([driver, "brake_balance", setup.brake_balance, ""])
                    writer.writerow([driver, "tyre_pressure", setup.tyre_pressure, ""])
            print(f"FP2 dice rolls saved to: {dice_csv_path}")

            # 3. Generate full markdown report
            report_path = os.path.join(
                output_dir, f"fp2_report_{track_name.lower()}.md"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# FP2 Report - {track_name}\n\n")
                f.write(f"**Session:** Free Practice 2\n\n")
                f.write(f"**Track:** {track_name}\n\n")

                # Results table
                f.write("## Session Results\n\n")
                f.write("| Pos | Driver | Team | Best Lap | Laps | R Delta |\n")
                f.write("|-----|--------|------|----------|------|---------|\n")

                # Sort by best lap time
                standings = sorted(
                    fp2_results.best_times.items(),
                    key=lambda x: x[1] if x[1] < float("inf") else 9999,
                )
                for pos, (driver, best_time) in enumerate(standings, 1):
                    laps = len(fp2_results.lap_times.get(driver, []))
                    r_delta = fp2_results.setup_results.get(driver, None)
                    r_delta_str = f"{r_delta.r_rating_delta:+.2f}" if r_delta else ""
                    best_str = f"{best_time:.3f}" if best_time < float("inf") else ""
                    team = teams.get(driver, "Unknown")
                    f.write(
                        f"| {pos} | {driver} | {team} | {best_str} | {laps} | {r_delta_str} |\n"
                    )

                # Setup tuning results
                f.write("\n## Setup Tuning Results\n\n")
                f.write(
                    "| Driver | Aero | Susp | Diff | Brake | Tyre | Total | R Delta |\n"
                )
                f.write(
                    "|--------|------|------|------|-------|------|-------|---------|\n"
                )
                for driver, setup in fp2_results.setup_results.items():
                    f.write(
                        f"| {driver} | {setup.aerodynamics} | {setup.suspension} | "
                        f"{setup.differential} | {setup.brake_balance} | {setup.tyre_pressure} | "
                        f"{setup.total_effect:+.1f} | {setup.r_rating_delta:+.2f} |\n"
                    )

                f.write("\n## Session Statistics\n\n")
                f.write(f"- Total Laps: {fp2_results.total_laps}\n")
                f.write(f"- Incidents: {len(fp2_results.incidents)}\n")

            print(f"FP2 report saved to: {report_path}")

        return {
            "session": "fp2",
            "status": "completed",
            "track": track_name,
            "setup_results": {
                d: r.r_rating_delta for d, r in fp2_results.setup_results.items()
            },
        }

    except Exception as e:
        print(f"Error during FP2 simulation: {e}")
        import traceback

        traceback.print_exc()

        if output_dir:
            generate_session_summary("fp2", track_name, "error", output_dir)

        return {
            "session": "fp2",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


# (file continues...)
