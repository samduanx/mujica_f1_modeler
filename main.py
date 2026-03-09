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
    uv run python main.py --gp-name Monaco

    # Run only the race
    uv run python main.py --gp-name Monaco --sessions race

    # Run qualifying and race
    uv run python main.py --gp-name Spain --sessions qualifying,race

    # Run sprint race and main race (sprint weekend format)
    uv run python main.py --gp-name Imola --sessions sprint,race

    # Run only sprint race
    uv run python main.py --gp-name Austria --sessions sprint

    # Run multiple tracks
    uv run python main.py --tracks Monaco,Spain,Monza

    # Run test suite (runs race simulation on all distinctive tracks)
    uv run python main.py --test-suite

    # With random seed for reproducibility
    uv run python main.py --gp-name Monaco --seed 42
"""

import argparse
import sys
import os
import shutil
import glob
from datetime import datetime
from typing import List, Optional, Dict, Any

# Handle PYTHONPATH for module imports
_project_root = os.path.dirname(os.path.abspath(__file__))
_src_path = os.path.join(_project_root, "src")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Import configuration loader
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
# The actual data is stored in:
#   - data/tracks.json (available_tracks, sprint_tracks)
#   - data/sessions.json (session_types, output_base_dir)
#   - data/drivers.json (drivers, teams)
#   - data/track_lap_times.json (base lap times)
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
                    for row in rows[:20]:  # Top 20
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


def generate_race_weekend_report(
    track_name: str,
    sessions: List[str],
    session_results: Dict[str, dict],
    output_dir: str,
) -> str:
    """
    Generate a comprehensive race weekend report markdown file.

    Args:
        track_name: Track name
        sessions: List of sessions that were run
        session_results: Dictionary of session results
        output_dir: Directory to save the report

    Returns:
        Path to the generated report
    """
    track_config = AVAILABLE_TRACKS.get(track_name, {})
    gp_name = track_config.get("gp_name", track_name)

    lines = [
        f"# F1 Race Weekend Report - {track_name}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Event Information",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Track | {track_name} |",
        f"| GP Name | {gp_name} |",
        f"| Sessions Run | {', '.join(sessions)} |",
        f"| Output Directory | {output_dir} |",
        f"",
    ]

    # Session summaries with detailed results
    lines.extend(["## Session Summaries", ""])

    for session in sessions:
        result = session_results.get(session, {})
        status = result.get("status", "unknown")
        session_dir = os.path.join(output_dir, session)

        lines.extend(
            [
                f"### {session.upper()}",
                "",
                f"**Status:** {status}",
                "",
            ]
        )

        # Add session-specific details
        if session in ["fp1", "fp2", "fp3"] and status == "completed":
            setup_results = result.get("setup_results", {})
            if setup_results:
                lines.extend(["**Setup Tuning Results (R Rating Deltas):**", ""])
                lines.extend(["| Driver | R Delta |", "|--------|---------|"])
                # Sort by R delta (best first)
                sorted_results = sorted(
                    setup_results.items(), key=lambda x: x[1], reverse=True
                )
                for driver, delta in sorted_results[:10]:  # Top 10
                    lines.append(f"| {driver} | {delta:+.2f} |")
                if len(sorted_results) > 10:
                    lines.append(f"| ... ({len(sorted_results) - 10} more) | ... |")
                lines.append("")

            # Parc Ferme info for FP3
            if session == "fp3":
                r_deltas = result.get("r_rating_deltas", {})
                parc_ferme_active = result.get("parc_ferme_active", False)
                lines.append(
                    f"**Parc Fermé:** {'Active' if parc_ferme_active else 'Inactive'}"
                )
                lines.append("")
                if r_deltas:
                    lines.extend(
                        ["**Final R Rating Deltas (for Qualifying/Race):**", ""]
                    )
                    lines.extend(["| Driver | R Delta |", "|--------|---------|"])
                    sorted_deltas = sorted(
                        r_deltas.items(), key=lambda x: x[1], reverse=True
                    )
                    for driver, delta in sorted_deltas:
                        lines.append(f"| {driver} | {delta:+.2f} |")
                    lines.append("")

        elif session == "qualifying" and status == "completed":
            grid_positions = result.get("grid_positions", {})
            pole_sitter = result.get("pole_sitter")
            is_sprint = result.get("is_sprint_weekend", False)

            if is_sprint:
                lines.append("**Format:** Sprint Qualifying (SQ1/SQ2/SQ3)")
            else:
                lines.append("**Format:** Standard Qualifying (Q1/Q2/Q3)")
            lines.append("")

            if pole_sitter:
                lines.append(f"**Pole Position:** {pole_sitter}")
                lines.append("")

            if grid_positions:
                lines.extend(["**Starting Grid:**", ""])
                lines.extend(["| Position | Driver |", "|----------|--------|"])
                sorted_grid = sorted(grid_positions.items(), key=lambda x: x[1])
                for driver, pos in sorted_grid:
                    lines.append(f"| {pos} | {driver} |")
                lines.append("")

            csv_path = result.get("csv_path")
            if csv_path:
                lines.append(
                    f"**Results CSV:** [{os.path.basename(csv_path)}]({csv_path})"
                )
                lines.append("")

        elif session == "sprint" and status == "completed":
            final_positions = result.get("final_positions", {})
            if final_positions:
                lines.extend(["**Sprint Race Results:**", ""])
                lines.extend(["| Position | Driver |", "|----------|--------|"])
                sorted_positions = sorted(final_positions.items(), key=lambda x: x[0])
                for pos, driver in sorted_positions:
                    lines.append(f"| {pos} | {driver} |")
                lines.append("")
            lines.append(
                "**Note:** Sprint results determine the main race starting grid."
            )
            lines.append("")

        elif session == "race" and status == "completed":
            # Try to read detailed race results from session summary
            race_summary_path = os.path.join(session_dir, "session_summary_race.md")
            if os.path.exists(race_summary_path):
                try:
                    with open(race_summary_path, "r", encoding="utf-8") as f:
                        summary_content = f.read()
                    # Extract the results table from the summary
                    in_results_section = False
                    for line in summary_content.split("\n"):
                        if "## Results" in line:
                            in_results_section = True
                            continue
                        if in_results_section:
                            if (
                                line.strip().startswith("**")
                                and "Race Results:" not in line
                            ):
                                break
                            if line.strip():
                                lines.append(line)
                    lines.append("")
                except Exception as e:
                    # Fallback to CSV links if reading fails
                    lines.extend(["**Race Results:**", ""])
                    lines.extend(
                        [
                            f"- [Race Results CSV](race/race_results_{gp_name.lower()}.csv)",
                            f"- [Dice Rolls CSV](race/dice_rolls_{gp_name.lower()}.csv)",
                        ]
                    )
                    lines.append("")
            else:
                lines.extend(["**Race Results:**", ""])
                lines.extend(
                    [
                        f"- [Race Results CSV](race/race_results_{gp_name.lower()}.csv)",
                        f"- [Dice Rolls CSV](race/dice_rolls_{gp_name.lower()}.csv)",
                    ]
                )
                lines.append("")

        lines.append("")

    # Summary table
    lines.extend(
        [
            "## Session Status Overview",
            "",
            "| Session | Status |",
            "|---------|--------|",
        ]
    )

    for session in sessions:
        result = session_results.get(session, {})
        status = result.get("status", "unknown")
        lines.append(f"| {session.upper()} | {status} |")

    # Weekend flow diagram
    lines.extend(
        [
            "",
            "## Weekend Flow",
            "",
        ]
    )

    if "fp1" in sessions and "fp2" in sessions and "fp3" in sessions:
        lines.append("```")
        if "sprint" in sessions:
            lines.append("FP1 → [PARC FERMÉ] → Qualifying → Sprint → Race")
        else:
            lines.append("FP1 → FP2 → FP3 → [PARC FERMÉ] → Qualifying → Race")
        lines.append("```")
    else:
        lines.append(f"Sessions run: {' → '.join(sessions)}")

    lines.extend(
        [
            "",
            "---",
            "",
            f"*Report generated by F1 Race Weekend Simulator*",
            f"*Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ]
    )

    report_content = "\n".join(lines)
    report_path = os.path.join(output_dir, "race_weekend_report.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_path


# =============================================================================
# SESSION SIMULATION MODULES (PLACEHOLDERS FOR NOT-YET-IMPLEMENTED MODULES)
# =============================================================================


# Global practice session storage (persisted across FP1/FP2/FP3)
_practice_sessions: Dict[str, Any] = {}


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


def simulate_fp3(
    track_name: str,
    output_dir: Optional[str] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> dict:
    """
    Simulate Free Practice 3 session.
    After FP3, parc fermé is established.
    """
    print(f"\n{'=' * 60}")
    print(f"FP3 - Free Practice 3 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")

    try:
        from src.practice import PracticeSessionManager, PracticeSessionType
        from src.practice import ParcFermeCoordinator

        # Get driver ratings
        driver_ratings = _get_driver_ratings(track_name)
        base_lap_time = get_track_lap_time(track_name, 80.0)

        # Filter Andretti drivers if not participating
        all_drivers = get_drivers()
        filtered_drivers = filter_andretti_drivers_for_gp(all_drivers, track_name)

        # Create and run FP3 session
        fp3_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP3,
            track=track_name,
            track_base_time=base_lap_time,
            drivers=filtered_drivers,
            driver_ratings=driver_ratings,
            duration_minutes=60,
            seed=seed + 2 if seed else None,
        )
        fp3_results = fp3_manager.run_session()

        # Store results
        global _practice_sessions
        _practice_sessions["fp3"] = fp3_results

        # Setup parc fermé after FP3
        coordinator = ParcFermeCoordinator()
        parc_ferme = coordinator.setup_normal_weekend(
            fp1_setups=_practice_sessions.get("fp1", {}).setup_results,
            fp2_setups=_practice_sessions.get("fp2", {}).setup_results,
            fp3_setups=fp3_results.setup_results,
        )

        # Get final R rating deltas
        r_deltas = parc_ferme.get_r_rating_deltas()

        print(f"\nFP3 Complete - Parc Fermé established")
        print(f"  {len(fp3_results.setup_results)} drivers completed setup tuning")
        print(f"  Final R rating deltas computed for {len(r_deltas)} drivers")

        if output_dir:
            generate_session_summary("fp3", track_name, "completed", output_dir)

            # Get teams for report
            import csv

            teams = get_teams()

            # 1. Save results CSV
            results_csv_path = os.path.join(
                output_dir, f"fp3_results_{track_name.lower()}.csv"
            )
            with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Driver", "Team", "Best Lap", "Laps", "R Delta"])

                # Sort by best lap time
                standings = sorted(
                    fp3_results.best_times.items(),
                    key=lambda x: x[1] if x[1] < float("inf") else 9999,
                )
                for driver, best_time in standings:
                    laps = len(fp3_results.lap_times.get(driver, []))
                    r_delta = fp3_results.setup_results.get(driver, None)
                    r_delta_val = r_delta.r_rating_delta if r_delta else 0.0
                    best_str = f"{best_time:.3f}" if best_time < float("inf") else ""
                    team = teams.get(driver, "Unknown")
                    writer.writerow(
                        [driver, team, best_str, laps, f"{r_delta_val:+.2f}"]
                    )

            print(f"FP3 results saved to: {results_csv_path}")

            # 2. Save dice rolls CSV
            dice_csv_path = os.path.join(
                output_dir, f"fp3_dice_rolls_{track_name.lower()}.csv"
            )
            with open(dice_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Driver", "Category", "Roll Value", "R Delta"])
                for driver, setup in fp3_results.setup_results.items():
                    writer.writerow([driver, "aerodynamics", setup.aerodynamics, ""])
                    writer.writerow([driver, "suspension", setup.suspension, ""])
                    writer.writerow([driver, "differential", setup.differential, ""])
                    writer.writerow([driver, "brake_balance", setup.brake_balance, ""])
                    writer.writerow([driver, "tyre_pressure", setup.tyre_pressure, ""])
            print(f"FP3 dice rolls saved to: {dice_csv_path}")

            # 3. Generate full markdown report
            report_path = os.path.join(
                output_dir, f"fp3_report_{track_name.lower()}.md"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# FP3 Report - {track_name}\n\n")
                f.write(f"**Session:** Free Practice 3\n\n")
                f.write(f"**Track:** {track_name}\n\n")

                # Results table
                f.write("## Session Results\n\n")
                f.write("| Pos | Driver | Team | Best Lap | Laps | R Delta |\n")
                f.write("|-----|--------|------|----------|------|---------|\n")

                # Sort by best lap time
                standings = sorted(
                    fp3_results.best_times.items(),
                    key=lambda x: x[1] if x[1] < float("inf") else 9999,
                )
                for pos, (driver, best_time) in enumerate(standings, 1):
                    laps = len(fp3_results.lap_times.get(driver, []))
                    r_delta = fp3_results.setup_results.get(driver, None)
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
                for driver, setup in fp3_results.setup_results.items():
                    f.write(
                        f"| {driver} | {setup.aerodynamics} | {setup.suspension} | "
                        f"{setup.differential} | {setup.brake_balance} | {setup.tyre_pressure} | "
                        f"{setup.total_effect:+.1f} | {setup.r_rating_delta:+.2f} |\n"
                    )

                f.write("\n## Session Statistics\n\n")
                f.write(f"- Total Laps: {fp3_results.total_laps}\n")
                f.write(f"- Incidents: {len(fp3_results.incidents)}\n")

                # Parc Fermé info
                f.write("\n## Parc Fermé Status\n\n")
                f.write(
                    f"- Status: {'Active' if parc_ferme.is_active() else 'Inactive'}\n"
                )
                f.write(f"- Drivers with setup data: {len(r_deltas)}\n")

            print(f"FP3 report saved to: {report_path}")

        return {
            "session": "fp3",
            "status": "completed",
            "track": track_name,
            "r_rating_deltas": r_deltas,
            "parc_ferme_active": parc_ferme.is_active(),
        }

    except Exception as e:
        print(f"Error during FP3 simulation: {e}")
        import traceback

        traceback.print_exc()

        if output_dir:
            generate_session_summary("fp3", track_name, "error", output_dir)

        return {
            "session": "fp3",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


def simulate_qualifying(
    track_name: str,
    output_dir: Optional[str] = None,
    is_sprint_weekend: bool = False,
    setup_tuning_deltas: Optional[Dict[str, float]] = None,
    **kwargs,
) -> dict:
    """
    Simulate Qualifying session (Q1, Q2, Q3 or SQ1, SQ2, SQ3 for sprint).

    Args:
        track_name: Name of the track
        output_dir: Output directory for race weekend
        is_sprint_weekend: If True, use sprint qualifying format (SQ1/SQ2/SQ3)
        setup_tuning_deltas: Optional dict mapping driver names to R rating deltas from FP1/FP3 setup tuning
    """
    print(f"\n{'=' * 60}")
    print(f"Qualifying Session - {track_name}")
    print(f"{'=' * 60}")

    # Import qualifying module
    try:
        import csv
        import random

        # Load driver data from config
        all_drivers = get_drivers()
        teams = get_teams()

        # Filter Andretti drivers if not participating
        drivers = filter_andretti_drivers_for_gp(all_drivers, track_name)

        base_lap_time = get_track_lap_time(track_name, 80.0)

        # Import qualifying components
        from src.qualifying import (
            QualifyingSessionManager,
            QualifyingLap,
            QualifyingResult,
        )
        from src.qualifying.incident_handler import QualifyingIncidentHandler
        from src.qualifying.tyre_allocation import TyreAllocationManager

        # Create incident handler
        incident_handler = QualifyingIncidentHandler()

        # Get qualifying configuration with dynamic elimination based on driver count
        qual_config = get_qualifying_sessions_config(is_sprint_weekend, len(drivers))
        sessions_config = [
            (s["name"], s["duration_minutes"], s["elimination_count"])
            for s in qual_config
        ]

        active_drivers = drivers.copy()

        # Results storage
        driver_results = {
            d: QualifyingResult(d, teams.get(d, "Unknown")) for d in drivers
        }

        # Dice rolls tracking
        dice_rolls = []

        # ========================================================================
        # CHEQUERED FLAG LIMITATION NOTE (F1 2022 Sporting Regulations)
        # ========================================================================
        # Current system simulates qualifying sessions with a simplified time-based
        # model where all drivers set laps simultaneously (or in quick succession).
        #
        # This does NOT fully simulate the F1 2022 Sporting Regulations:
        # - Article 33.3: If a driver is on a flying lap when the chequered flag falls,
        #   that lap is valid if completed before the flag reaches the start/finish line
        # - Article 33.4: When session time expires, the session ends when the LEADER
        #   completes their lap; drivers who haven't started a flying lap cannot start one
        #
        # Real-world implications not simulated:
        # 1. Different driver positions on track when session ends
        # 2. Whether a driver is "on a flying lap" vs "in the pit" when time expires
        # 3. The leader completing their lap to "trigger" session end
        # 4. Drivers being unable to start new laps after time expires
        #
        # To implement fully, would need to simulate:
        # - Track position of each driver at each moment
        # - Lap start times and expected lap completion times
        # - Session end triggered by leader crossing the line
        # ========================================================================

        # Run each session
        for session_name, duration, elimination_count in sessions_config:
            print(f"\n{'-' * 60}")
            print(f"{session_name} - {duration} minutes")
            print(f"{'-' * 60}")

            session = QualifyingSessionManager(
                session_name, duration, active_drivers, elimination_count
            )
            session.start_session()

            # Get driver skill tiers from configuration
            top_tier_drivers = get_top_tier_drivers()
            bottom_tier_drivers = get_bottom_tier_drivers()

            # Load team PR values for qualifying performance calculation
            from src.utils.config_loader import get_all_teams_pr
            team_pr_values = get_all_teams_pr(track_name)
            max_pr = max(team_pr_values.values()) if team_pr_values else 308.0

            # Simulate each driver setting lap times
            for driver in active_drivers:
                # Generate realistic lap time with variation
                # NOTE: Significantly increased team PR impact for qualifying.
                # Qualifying is single-lap pace, so car performance matters more.
                base = base_lap_time

                # Get team for this driver
                team_name = teams.get(driver, "Unknown")
                team_pr = team_pr_values.get(team_name, 300.0)

                # Calculate team performance penalty (slower teams = higher lap time)
                # Formula: (max_PR - team_PR) * 0.08 for qualifying
                # This makes a ~19 second PR difference translate to ~1.5 seconds on track
                team_penalty = (max_pr - team_pr) * 0.08

                # Add driver skill variation (reduced from before, now team matters more)
                skill_factor = random.uniform(-0.15, 0.15)  # Further reduced
                if driver in top_tier_drivers:
                    skill_factor -= 0.2  # Top drivers gain less advantage
                elif driver in bottom_tier_drivers:
                    skill_factor += 0.2  # Slower drivers

                # Apply setup tuning delta from FP1/FP3
                setup_delta = 0.0
                if setup_tuning_deltas and driver in setup_tuning_deltas:
                    setup_delta = setup_tuning_deltas[driver]
                    setup_delta = max(-0.5, min(0.5, setup_delta))
                    skill_factor -= setup_delta * 0.3  # Reduced effect

                lap_time = (
                    base + team_penalty + skill_factor + random.uniform(-0.05, 0.05)
                )  # Reduced random variation

                # Check for incidents
                incident_roll = random.randint(1, 100)

                # Log dice roll
                dice_rolls.append(
                    {
                        "session": session_name,
                        "driver": driver,
                        "roll_type": "incident_check",
                        "roll_value": incident_roll,
                        "outcome": "",
                    }
                )

                lap_valid = True
                if incident_roll <= 5:  # 5% crash chance
                    incident = incident_handler._create_crash_incident(driver)
                    session.record_incident(incident)
                    print(f"  ! {driver} crashed - lap deleted, red flag")
                    dice_rolls[-1]["outcome"] = "crash"
                    lap_valid = False
                elif incident_roll <= 15:  # 10% track limits
                    incident = incident_handler._create_track_limits_incident(driver)
                    print(f"  ! {driver} track limits - lap deleted")
                    dice_rolls[-1]["outcome"] = "track_limits"
                    lap_valid = False
                else:
                    dice_rolls[-1]["outcome"] = "valid_lap"

                # Record lap time (even if invalid due to incident)
                session.record_lap_time(driver, lap_time)

                # Store lap time in results
                if session_name in ["Q1", "SQ1"]:
                    driver_results[driver].q1_time = lap_time
                elif session_name in ["Q2", "SQ2"]:
                    driver_results[driver].q2_time = lap_time
                elif session_name in ["Q3", "SQ3"]:
                    driver_results[driver].q3_time = lap_time

            # End session and get results
            if elimination_count > 0:
                advancing, eliminated = session.end_session()
                active_drivers = advancing

                # Mark eliminated drivers with grid position calculation
                num_drivers = len(
                    drivers
                )  # Actual number of drivers after Andretti filter
                for driver in eliminated:
                    driver_results[driver].eliminated_in = session_name
                    if session_name in ["Q1", "SQ1"]:
                        # Q1 eliminated: positions (total - elimination_count + 1) to total
                        q1_start_pos = num_drivers - elimination_count + 1
                        driver_results[driver].grid_position = (
                            q1_start_pos + eliminated.index(driver)
                        )
                    elif session_name in ["Q2", "SQ2"]:
                        # Q2 eliminated: positions (Q1 eliminated start - elimination_count) to (Q1 start - 1)
                        # After Q1 eliminates elimination_count drivers, remaining drivers advance to Q2
                        # Q2 eliminates elimination_count more drivers
                        # Q2 positions are right after Q3 positions (which are 1 to num_q3_drivers)
                        q2_start_pos = num_drivers - 2 * elimination_count + 1
                        driver_results[driver].grid_position = (
                            q2_start_pos + eliminated.index(driver)
                        )
            else:
                # For Q3/SQ3, get standings
                standings = session.get_current_standings()
                num_q3_drivers = len(active_drivers)
                # Assign grid positions 1-N based on Q3/SQ3 times
                for pos, (driver, _) in enumerate(standings[:num_q3_drivers], 1):
                    driver_results[driver].grid_position = pos
                # Handle drivers who reached Q3 but have no valid time
                no_time_drivers = [
                    d for d in active_drivers if driver_results[d].grid_position == 0
                ]
                no_time_drivers.sort(
                    key=lambda d: driver_results[d].q2_time or float("inf")
                )
                for i, driver in enumerate(no_time_drivers):
                    # Drivers are sorted by best Q2 time first (ascending).
                    # The driver with the best Q2 time among no-timers gets the best
                    # available position (right after all drivers who set valid Q3 times).
                    # Formula: num_q3_drivers - len(no_time_drivers) + 1 + i
                    # Example: 10 Q3 drivers, 2 no-time -> positions 9 and 10
                    driver_results[driver].grid_position = (
                        num_q3_drivers - len(no_time_drivers) + 1 + i
                    )
                session.end_session()

        # Collect final results
        final_results = list(driver_results.values())
        final_results.sort(key=lambda r: r.grid_position if r.grid_position else 99)

        # Generate output files
        csv_path = None
        md_path = None

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

            # Generate CSV file
            csv_filename = f"qualifying_results_{track_name.lower()}.csv"
            csv_path = os.path.join(output_dir, csv_filename)

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Grid Pos",
                        "Driver",
                        "Team",
                        "Q1 Time",
                        "Q2 Time",
                        "Q3 Time",
                        "Best Time",
                        "Eliminated In",
                        "Race Start Tyre",
                    ]
                )

                for r in final_results:
                    best = r.get_best_time()
                    writer.writerow(
                        [
                            r.grid_position,
                            r.driver,
                            r.team,
                            f"{r.q1_time:.3f}" if r.q1_time else "",
                            f"{r.q2_time:.3f}" if r.q2_time else "",
                            f"{r.q3_time:.3f}" if r.q3_time else "",
                            f"{best:.3f}" if best else "",
                            r.eliminated_in if r.eliminated_in else "",
                            r.race_start_tyre if r.race_start_tyre else "SOFT",
                        ]
                    )

            print(f"\nQualifying results saved to: {csv_path}")

            # Generate Markdown report
            md_filename = f"qualifying_report_{track_name.lower()}.md"
            md_path = os.path.join(output_dir, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(
                    f"# {'Sprint ' if is_sprint_weekend else ''}Qualifying Report - {track_name}\n\n"
                )
                f.write(
                    f"**Session Type:** {'Sprint Qualifying (SQ1/SQ2/SQ3)' if is_sprint_weekend else 'Standard Qualifying (Q1/Q2/Q3)'}\n\n"
                )
                f.write("## Starting Grid\n\n")
                f.write("| Pos | Driver | Team | Q1 | Q2 | Q3 | Best Time |\n")
                f.write("|-----|--------|------|----|----|----|-----------|\n")

                for r in final_results:
                    q1_str = f"{r.q1_time:.3f}" if r.q1_time else "-"
                    q2_str = f"{r.q2_time:.3f}" if r.q2_time else "-"
                    q3_str = f"{r.q3_time:.3f}" if r.q3_time else "-"
                    best = r.get_best_time()
                    best_str = f"{best:.3f}" if best else "-"

                    f.write(
                        f"| {r.grid_position} | {r.driver} | {r.team} | {q1_str} | {q2_str} | {q3_str} | {best_str} |\n"
                    )

                f.write("\n## Session Details\n\n")

                if is_sprint_weekend:
                    f.write(
                        "- **SQ1:** 12 minutes, eliminate slowest 6 (P17-22 determined)\n"
                    )
                    f.write(
                        "- **SQ2:** 10 minutes, eliminate slowest 6 (P11-16 determined)\n"
                    )
                    f.write(
                        "- **SQ3:** 8 minutes, top 10 battle for pole (P1-10 determined)\n"
                    )
                else:
                    f.write(
                        "- **Q1:** 18 minutes, eliminate slowest 6 (P17-22 determined)\n"
                    )
                    f.write(
                        "- **Q2:** 15 minutes, eliminate slowest 6 (P11-16 determined)\n"
                    )
                    f.write(
                        "- **Q3:** 12 minutes, top 10 battle for pole (P1-10 determined)\n"
                    )

                f.write("\n## Notes\n\n")
                f.write("- All times in seconds\n")
                f.write("- Grid positions determine the starting order for the ")
                f.write("sprint race\n" if is_sprint_weekend else "Grand Prix\n")

            print(f"Qualifying report saved to: {md_path}")

            # Generate dice rolls CSV
            if dice_rolls:
                dice_csv_filename = f"dice_rolls_{track_name.lower()}.csv"
                dice_csv_path = os.path.join(output_dir, dice_csv_filename)

                with open(dice_csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ["Session", "Driver", "Roll Type", "Roll Value", "Outcome"]
                    )
                    for roll in dice_rolls:
                        writer.writerow(
                            [
                                roll["session"],
                                roll["driver"],
                                roll["roll_type"],
                                roll["roll_value"],
                                roll["outcome"],
                            ]
                        )

                print(f"Dice rolls saved to: {dice_csv_path}")

        return {
            "session": "qualifying",
            "status": "completed",
            "track": track_name,
            "is_sprint_weekend": is_sprint_weekend,
            "grid_positions": {r.driver: r.grid_position for r in final_results},
            "pole_sitter": final_results[0].driver if final_results else None,
            "csv_path": csv_path,
            "report_path": md_path,
        }

    except Exception as e:
        import traceback

        print(f"Error during qualifying simulation: {e}")
        traceback.print_exc()

        return {
            "session": "qualifying",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


def simulate_sprint_qualifying(
    track_name: str,
    output_dir: Optional[str] = None,
    setup_tuning_deltas: Optional[Dict[str, float]] = None,
    **kwargs,
) -> dict:
    """
    Simulate Sprint Qualifying session (SQ1, SQ2, SQ3) for sprint weekends.

    2022 Sprint Weekend Format:
    - FP1 → Sprint Qualifying (SQ1/SQ2/SQ3) → Sprint Race → Qualifying (Q1/Q2/Q3) → Main Race

    Sprint Qualifying determines the grid for the Sprint Race (not the main race).

    Args:
        track_name: Name of the track
        output_dir: Output directory for race weekend
        setup_tuning_deltas: Optional dict mapping driver names to R rating deltas from FP1
    """
    print(f"\n{'=' * 60}")
    print(f"Sprint Qualifying Session (SQ1/SQ2/SQ3) - {track_name}")
    print(f"{'=' * 60}")
    print("Note: Sprint Qualifying determines the Sprint Race grid")
    print("      The main race grid is determined by Saturday's Qualifying\n")

    # Sprint qualifying uses the same logic as regular qualifying but with sprint format
    result = simulate_qualifying(
        track_name=track_name,
        output_dir=output_dir,
        is_sprint_weekend=True,  # This triggers SQ1/SQ2/SQ3 format
        setup_tuning_deltas=setup_tuning_deltas,
        **kwargs,
    )

    # Update the session identifier to distinguish from main qualifying
    if result.get("status") == "completed":
        result["session"] = "sprint_qualifying"
        # Rename output files to distinguish from main qualifying
        if output_dir and result.get("csv_path"):
            import os

            old_csv = result["csv_path"]
            new_csv = old_csv.replace(
                "qualifying_results_", "sprint_qualifying_results_"
            )
            if os.path.exists(old_csv) and old_csv != new_csv:
                os.rename(old_csv, new_csv)
                result["csv_path"] = new_csv
        if output_dir and result.get("report_path"):
            import os

            old_md = result["report_path"]
            new_md = old_md.replace("qualifying_report_", "sprint_qualifying_report_")
            if os.path.exists(old_md) and old_md != new_md:
                os.rename(old_md, new_md)
                result["report_path"] = new_md

    return result


def simulate_sprint(
    track_name: str,
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
    grid_positions: Optional[Dict[str, int]] = None,
    **kwargs,
) -> dict:
    """
    Simulate the Sprint Race session.

    Sprint races are 100km short races that determine the starting grid
    for the main Grand Prix. No mandatory pit stops.

    Available tracks: Imola, Austria, Sao_Paulo

    Args:
        track_name: Name of the sprint track
        seed: Random seed for reproducibility
        output_dir: Output directory for race weekend

    Returns:
        Dictionary with sprint results including finishing positions
    """
    # Check if track is a valid sprint track
    if track_name not in SPRINT_TRACKS:
        print(f"Error: {track_name} is not a valid sprint track")
        print(f"Available sprint tracks: {', '.join(SPRINT_TRACKS.keys())}")
        return {
            "session": "sprint",
            "status": "error",
            "track": track_name,
            "error": f"Invalid sprint track: {track_name}",
        }

    print(f"\n{'=' * 60}")
    print(f"SPRINT RACE - {track_name}")
    print(f"{'=' * 60}")

    # Import sprint simulation module
    try:
        import src.sprint
        from src.sprint import run_sprint_race, StartingGridConnector

        # Run sprint race - pass output_dir and grid_positions if provided
        # Grid positions come from Sprint Qualifying (SQ1/SQ2/SQ3)
        results = run_sprint_race(
            track_name=track_name,
            seed=seed,
            output_dir=output_dir,  # Pass race weekend output directory
            grid_positions=grid_positions,  # From Sprint Qualifying
        )

        # Generate session summary if output directory provided
        if output_dir:
            generate_session_summary("sprint", track_name, "completed", output_dir)

        return {
            "session": "sprint",
            "status": "completed",
            "track": track_name,
            "results": results,
            "final_positions": results.get("final_positions", {}),
            "output_dir": output_dir if output_dir else results.get("output_dir"),
        }

    except Exception as e:
        print(f"Error during sprint race simulation: {e}")

        if output_dir:
            generate_session_summary("sprint", track_name, "error", output_dir)

        return {
            "session": "sprint",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


def _generate_race_report(output_dir: str, track_name: str, gp_name: str) -> None:
    """Generate a full race report markdown file."""
    try:
        # Read race results CSV
        results_csv = os.path.join(output_dir, f"race_results_{gp_name.lower()}.csv")
        if not os.path.exists(results_csv):
            return

        import csv

        with open(results_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            results = list(reader)

        # Read dice rolls CSV
        dice_csv = os.path.join(output_dir, f"dice_rolls_{gp_name.lower()}.csv")
        dice_rolls = []
        if os.path.exists(dice_csv):
            with open(dice_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                dice_rolls = list(reader)

        # Generate report
        report_path = os.path.join(output_dir, f"race_report_{gp_name.lower()}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Race Report - {track_name}\n\n")
            f.write(f"**Grand Prix:** {gp_name}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Results table
            f.write("## Race Results\n\n")
            f.write("| Pos | Driver | Team | Total Time | Pits |\n")
            f.write("|-----|--------|------|------------|------|\n")

            for row in results[:20]:
                pos = row.get("position", "")
                driver = row.get("driver", "")
                team = row.get("team", "")
                total_time = row.get("total_time", "")
                pits = row.get("num_pits", "")
                f.write(f"| {pos} | {driver} | {team} | {total_time}s | {pits} |\n")

            # Dice rolls summary
            if dice_rolls:
                f.write("\n## Dice Rolls Summary\n\n")
                f.write(f"Total dice rolls: {len(dice_rolls)}\n\n")

                # Count by roll type
                roll_types = {}
                for roll in dice_rolls:
                    roll_type = roll.get("roll_type", "unknown")
                    roll_types[roll_type] = roll_types.get(roll_type, 0) + 1

                f.write("### Roll Types\n\n")
                for roll_type, count in sorted(roll_types.items()):
                    f.write(f"- {roll_type}: {count}\n")

            f.write("\n---\n\n")
            f.write("*Report generated by F1 Race Weekend Simulator*\n")

        print(f"Race report saved to: {report_path}")

    except Exception as e:
        print(f"Warning: Could not generate race report: {e}")


def simulate_race(
    track_name: str,
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
    is_race_weekend: bool = False,
    grid_positions: Optional[Dict[str, int]] = None,
    **kwargs,
) -> dict:
    """
    Simulate the Race session.

    This uses the existing enhanced_long_dist_sim module.

    Args:
        track_name: Name of the track
        seed: Random seed
        output_dir: Output directory for race weekend (if part of race weekend)
        is_race_weekend: If True, outputs go to race weekend subdir; else original location
        grid_positions: Dict mapping driver names to grid positions (1-based)
    """
    print(f"\n{'=' * 60}")
    print(f"RACE - Grand Prix")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")

    # Display grid positions if provided from qualifying or sprint
    if grid_positions:
        print(f"\nStarting Grid (from previous session):")
        print(f"{'-' * 40}")
        # Determine format: {driver: position} or {position: driver}
        first_key = next(iter(grid_positions.keys()))
        if isinstance(first_key, int):
            # Format is {position: driver} - from sprint
            sorted_grid = sorted(grid_positions.items(), key=lambda x: x[0])
            for pos, driver in sorted_grid[:10]:
                print(f"  P{pos:2d}: {driver}")
        else:
            # Format is {driver: position} - from qualifying
            sorted_grid = sorted(grid_positions.items(), key=lambda x: x[1])
            for driver, pos in sorted_grid[:10]:
                print(f"  P{pos:2d}: {driver}")
        if len(sorted_grid) > 10:
            print(f"  ... ({len(sorted_grid) - 10} more drivers)")
        print(f"{'-' * 40}")

    # Import the race simulation module
    import src.simulation.enhanced_long_dist_sim as elds
    from src.simulation.test_track_suite import create_driver_csv

    # Get the GP name for the track
    track_config = AVAILABLE_TRACKS.get(track_name, {})
    gp_name = track_config.get("gp_name", track_name)

    # Create driver CSV file for this track
    # If grid_positions provided from qualifying/sprint, use them
    csv_path = create_driver_csv(gp_name, grid_positions=grid_positions)

    # Prepare arguments for the simulation
    sim_args = [f"--gp-name", gp_name, "--csv-file", csv_path]

    if seed is not None:
        sim_args.extend(["--seed", str(seed)])

    # Determine output directory
    if is_race_weekend and output_dir:
        # When part of race weekend, save directly to race weekend directory
        sim_args.extend(["--output-dir", output_dir])
        race_output_path = output_dir
    else:
        # When run independently, use default location
        race_output_path = None

    # Run the race simulation
    print(f"\nStarting race simulation for {gp_name}...")

    try:
        result = elds.main(sim_args)

        # Note: enhanced_long_dist_sim.main() returns None (it writes to files instead)
        # So we check for output files instead of return value
        # The race simulation runs and generates files regardless of return value

        # If not using custom output dir, find the most recent output directory
        if race_output_path is None:
            original_output_dir = "outputs/enhanced_sim"
            if os.path.exists(original_output_dir):
                # Get all subdirectories matching the track name
                pattern = os.path.join(original_output_dir, f"{gp_name}_*")
                dirs = glob.glob(pattern)
                if dirs:
                    # Sort by modification time, get most recent
                    race_output_path = max(dirs, key=os.path.getmtime)

        # For race weekend mode, files are already in the correct location
        copied_files = {}
        if (
            is_race_weekend
            and output_dir
            and race_output_path
            and race_output_path != output_dir
        ):
            # Only copy if files are not already in the correct location
            copied_files = copy_race_outputs_to_weekend(
                race_output_path, output_dir, gp_name
            )

        # Generate session summary if output directory provided
        if output_dir:
            generate_session_summary("race", track_name, "completed", output_dir)

            # Generate full race report
            _generate_race_report(output_dir, track_name, gp_name)

        return {
            "session": "race",
            "status": "completed",
            "track": track_name,
            "gp_name": gp_name,
            "output_dir": output_dir,
            "is_race_weekend": is_race_weekend,
            "original_output_dir": race_output_path,
            "copied_files": copied_files if is_race_weekend else None,
        }
    except Exception as e:
        print(f"Error during race simulation: {e}")

        # Generate error session summary if output directory provided
        if output_dir:
            generate_session_summary("race", track_name, "error", output_dir)

        return {
            "session": "race",
            "status": "error",
            "track": track_name,
            "error": str(e),
        }


# =============================================================================
# RACE WEEKEND SIMULATION
# =============================================================================


def run_race_weekend(
    track_name: str,
    sessions: Optional[List[str]] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> dict:
    """
    Run a complete race weekend simulation.

    Args:
        track_name: Name of the track (e.g., "Monaco", "Spain", "Monza")
        sessions: List of sessions to run (default: all sessions)
        seed: Random seed for reproducibility

    Returns:
        Dictionary with simulation results
    """
    print(f"\n{'#' * 70}")
    print(f"# F1 RACE WEEKEND SIMULATION")
    print(f"# Track: {track_name}")
    print(f"# Sessions: {sessions or 'all'}")
    if seed:
        print(f"# Seed: {seed}")
    print(f"{'#' * 70}")

    # Default to all sessions
    if sessions is None:
        sessions = SESSION_TYPES

    # Determine if this is a full race weekend (multiple sessions) or single session
    is_full_weekend = len(sessions) > 1

    # Create output directory structure only for full race weekend
    output_base_dir = None
    session_dirs = {}

    if is_full_weekend:
        # Full race weekend - create race weekend structure
        runtime_datetime = datetime.now()
        output_base_dir = get_race_weekend_output_dir(track_name, runtime_datetime)
        session_dirs = create_session_subdirs(output_base_dir, sessions)
        print(f"\nOutput directory: {output_base_dir}")
    else:
        # Single session - let the simulation handle its own outputs
        print(f"\nSingle session mode - using default output locations")

    # Session mapping
    # 2022 Sprint Weekend Format: FP1 → Sprint Qualifying → Sprint → Qualifying → Race
    session_map = {
        "fp1": simulate_fp1,
        "fp2": simulate_fp2,
        "fp3": simulate_fp3,
        "practice1": simulate_fp1,
        "practice2": simulate_fp2,
        "practice3": simulate_fp3,
        "sprint_qualifying": simulate_sprint_qualifying,  # SQ1/SQ2/SQ3 for sprint grid
        "qualifying": simulate_qualifying,  # Q1/Q2/Q3 for main race grid
        "sprint": simulate_sprint,
        "race": simulate_race,
    }

    results = {}
    for session in sessions:
        session_key = session.lower()

        # Skip sprint for non-sprint tracks
        if session_key == "sprint" and track_name not in SPRINT_TRACKS:
            print(f"\nSkipping sprint - {track_name} is not a sprint weekend track")
            results[session_key] = {
                "session": "sprint",
                "status": "not_applicable",
                "track": track_name,
                "message": f"{track_name} does not have a sprint race",
            }
            continue

        if session_key in session_map:
            session_output_dir = session_dirs.get(session_key)

            # Pass is_race_weekend=True only for full race weekend simulation
            extra_kwargs = {}
            if is_full_weekend:
                extra_kwargs["output_dir"] = session_output_dir
                if session_key == "race":
                    extra_kwargs["is_race_weekend"] = True
                    # 2022 Sprint Weekend Format:
                    # - Sprint Qualifying (Friday) → Sprint Race (Saturday) → Main Race grid
                    # - Qualifying (Saturday) → Main Race grid (if sprint not run)
                    # Priority: Sprint Race results > Qualifying results
                    if (
                        "sprint" in results
                        and results["sprint"].get("status") == "completed"
                    ):
                        # Sprint final_positions is {position: driver}, need to convert to {driver: position}
                        sprint_positions = results["sprint"].get("final_positions", {})
                        # Convert format: {1: "Verstappen"} -> {"Verstappen": 1}
                        extra_kwargs["grid_positions"] = {
                            driver: int(pos) for pos, driver in sprint_positions.items()
                        }
                        print(f"  Using Sprint Race results for main race grid")
                    elif (
                        "qualifying" in results
                        and results["qualifying"].get("status") == "completed"
                    ):
                        # Use Saturday's Qualifying for main race grid
                        extra_kwargs["grid_positions"] = results["qualifying"].get(
                            "grid_positions", {}
                        )
                        print(f"  Using Qualifying results for main race grid")
                elif session_key == "sprint":
                    # Sprint Race - get grid positions from Sprint Qualifying if available
                    if (
                        "sprint_qualifying" in results
                        and results["sprint_qualifying"].get("status") == "completed"
                    ):
                        extra_kwargs["grid_positions"] = results["sprint_qualifying"].get(
                            "grid_positions", {}
                        )
                        print(f"  Using Sprint Qualifying results for Sprint Race grid")
                elif session_key == "sprint_qualifying":
                    # Sprint Qualifying (SQ1/SQ2/SQ3) on Friday
                    # This determines the Sprint Race grid, NOT the main race grid
                    print(f"  Sprint Qualifying determines Sprint Race grid only")
                    # Pass FP1 setup tuning deltas for sprint weekends (FP1 → SQ)
                    fp1_key = None
                    if "fp1" in results:
                        fp1_key = "fp1"
                    elif "practice1" in results:
                        fp1_key = "practice1"

                    if fp1_key:
                        fp1_setup_results = results[fp1_key].get("setup_results", {})
                        if fp1_setup_results:
                            extra_kwargs["setup_tuning_deltas"] = fp1_setup_results
                            print(
                                f"  Passing {len(fp1_setup_results)} FP1 setup tuning results to Sprint Qualifying"
                            )
                elif session_key == "qualifying":
                    # Normal Qualifying (Q1/Q2/Q3) on Saturday for sprint weekends
                    # This determines the main race grid (when sprint is not used)
                    if track_name in SPRINT_TRACKS:
                        print(
                            f"  Qualifying determines main race grid (sprint weekend)"
                        )
                    else:
                        print(f"  Qualifying determines main race grid")

            result = session_map[session_key](
                track_name,
                seed=seed,
                **kwargs,
                **extra_kwargs,
            )
            results[session_key] = result
        else:
            print(f"Warning: Unknown session type '{session}'")

    # Generate final race weekend report only for full weekend
    if is_full_weekend and output_base_dir:
        report_path = generate_race_weekend_report(
            track_name, sessions, results, output_base_dir
        )
        print(f"\nRace weekend report: {report_path}")
        results["_output_dir"] = output_base_dir
        results["_report_path"] = report_path

    return results


def run_multi_track_simulation(
    tracks: List[str],
    sessions: Optional[List[str]] = None,
    seed: Optional[int] = None,
    **kwargs,
) -> dict:
    """
    Run simulations for multiple tracks.

    Args:
        tracks: List of track names
        sessions: List of sessions to run
        seed: Random seed for reproducibility

    Returns:
        Dictionary with simulation results for all tracks
    """
    print(f"\n{'#' * 70}")
    print(f"# F1 MULTI-TRACK SIMULATION")
    print(f"# Tracks: {', '.join(tracks)}")
    print(f"{'#' * 70}")

    all_results = {}
    for track in tracks:
        print(f"\n>>> Processing: {track}")
        results = run_race_weekend(track, sessions, seed, **kwargs)
        all_results[track] = results

    return all_results


def run_test_suite(seed: Optional[int] = None) -> dict:
    """
    Run the test suite with distinctive tracks.

    This runs simulations on at least 4 distinctive tracks:
    - Monaco (street circuit)
    - Monza (high speed)
    - Spain (technical)
    - Japan (high downforce)

    Args:
        seed: Random seed for reproducibility

    Returns:
        Dictionary with simulation results
    """
    test_tracks = ["Monaco", "Monza", "Spain", "Japan"]

    # Add more tracks if available
    for track in ["Australia", "Bahrain", "China", "Italy"]:
        if track in AVAILABLE_TRACKS:
            test_tracks.append(track)

    print(f"\n{'#' * 70}")
    print(f"# F1 TEST SUITE - DISTINCTIVE TRACKS")
    print(f"# Running {len(test_tracks)} tracks: {', '.join(test_tracks)}")
    print(f"{'#' * 70}")

    return run_multi_track_simulation(test_tracks, sessions=["race"], seed=seed)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main(argv=None):
    """Main entry point for the F1 Race Weekend Simulator."""

    parser = argparse.ArgumentParser(
        description="F1 Race Weekend Simulator - Complete race weekend simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a full race weekend for Monaco
  %(prog)s --gp-name Monaco
  
  # Run only the race for Monza
  %(prog)s --gp-name Monza --sessions race
  
  # Run qualifying and race
  %(prog)s --gp-name Spain --sessions qualifying,race
  
  # Run multiple tracks
  %(prog)s --tracks Monaco,Spain,Monza
  
  # Run test suite
  %(prog)s --test-suite

Available tracks:
  Monaco, Spain, Monza, Italy, Australia, Bahrain, China, Japan, Austria
        """,
    )

    parser.add_argument(
        "--gp-name", type=str, help="Grand Prix name (single track simulation)"
    )

    parser.add_argument(
        "--track", type=str, dest="gp_name", help="Alternative flag for gp-name"
    )

    parser.add_argument(
        "--tracks",
        type=str,
        help="Comma-separated list of tracks for multi-track simulation",
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="(Deprecated - no longer needed, kept for backward compatibility)",
    )

    parser.add_argument(
        "--sessions",
        type=str,
        help="Comma-separated list of sessions to run (fp1,fp2,fp3,qualifying,race)",
    )

    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    parser.add_argument(
        "--test-suite",
        action="store_true",
        help="Run test suite with distinctive tracks",
    )

    args = parser.parse_args(argv)

    # Parse sessions if provided
    sessions = None
    if args.sessions:
        sessions = [s.strip().lower() for s in args.sessions.split(",")]

    # Determine what to run
    if args.test_suite:
        # Run test suite
        results = run_test_suite(seed=args.seed)

    elif args.tracks:
        # Multi-track simulation
        tracks = [t.strip() for t in args.tracks.split(",")]
        results = run_multi_track_simulation(tracks, sessions=sessions, seed=args.seed)

    elif args.gp_name:
        # Single track simulation
        results = run_race_weekend(args.gp_name, sessions=sessions, seed=args.seed)

    else:
        parser.print_help()
        print("\nError: Please specify --gp-name, --tracks, or --test-suite")
        return 1

    print(f"\n{'#' * 70}")
    print(f"{'#' * 70}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
