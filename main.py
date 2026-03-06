"""
F1 Race Weekend Simulator - Main Entry Point

This module serves as the main entrance for simulating complete F1 race weekends,
including all sessions:
- FP1 (Free Practice 1) - placeholder, not yet implemented
- FP2 (Free Practice 2) - placeholder, not yet implemented
- FP3 (Free Practice 3) - placeholder, not yet implemented
- Qualifying (Q1, Q2, Q3) - placeholder, not yet implemented
- Sprint - 100km sprint race (Imola, Austria, Sao Paulo)
- Race - fully implemented using enhanced_long_dist_sim

Supported Tracks:
- Monaco, Spain, Monza, Italy, Australia, Bahrain, China, Japan

Sprint Race Tracks (2022):
- Imola (Emilia Romagna GP) - 21 laps, ~100km
- Austria (Red Bull Ring) - 24 laps, ~100km
- Sao_Paulo (Brazil GP) - 24 laps, ~100km

Usage:
    # Run a full race weekend (runs all sessions - FP1/FP2/FP3/Qualifying are placeholders)
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


# =============================================================================
# AVAILABLE TRACKS AND SESSIONS
# =============================================================================

# Track configurations available for simulation
# Note: year is not used since we're not simulating real-life races
AVAILABLE_TRACKS = {
    "Monaco": {
        "gp_name": "Monaco",
        "description": "Street circuit, low speed, high complexity",
        "characteristics": "low_speed, high_complexity, street_circuit",
    },
    "Spain": {
        "gp_name": "Spain",
        "description": "Technical, medium speed",
        "characteristics": "medium_speed, technical",
    },
    "Monza": {
        "gp_name": "Monza",  # Use Monza for track characteristics lookup
        "description": "High speed, low downforce",
        "characteristics": "high_speed, low_downforce",
    },
    "Italy": {
        "gp_name": "Spain",  # Use Spain as fallback for Imola-like tracks
        "description": "High speed, low downforce (Imola)",
        "characteristics": "high_speed, medium_downforce",
    },
    "Australia": {
        "gp_name": "Australia",
        "description": "Street circuit, medium speed",
        "characteristics": "street_circuit, medium_speed",
    },
    "Bahrain": {
        "gp_name": "Bahrain",
        "description": "Desert circuit, medium-high speed",
        "characteristics": "desert, medium_speed",
    },
    "China": {
        "gp_name": "China",
        "description": "Technical, medium speed",
        "characteristics": "technical, medium_speed",
    },
    "Japan": {
        "gp_name": "Japan",
        "description": "High downforce, technical",
        "characteristics": "high_downforce, technical",
    },
}

# Sprint race tracks (2022 format: Imola, Austria, Sao Paulo)
SPRINT_TRACKS = {
    "Imola": {
        "gp_name": "Imola",
        "description": "Emilia Romagna GP - High downforce, technical, narrow",
        "characteristics": "high_downforce, technical, narrow",
        "sprint_laps": 21,
    },
    "Austria": {
        "gp_name": "Austria",
        "description": "Red Bull Ring - High speed, short lap, 3 DRS zones",
        "characteristics": "high_speed, short_lap, overtaking",
        "sprint_laps": 24,
    },
    "Sao_Paulo": {
        "gp_name": "Brazil",
        "description": "Interlagos - Anti-clockwise, high altitude, overtaking friendly",
        "characteristics": "anti_clockwise, high_altitude, overtaking",
        "sprint_laps": 24,
    },
}

# Session types for race weekend
SESSION_TYPES = ["fp1", "fp2", "fp3", "qualifying", "sprint", "race"]


# =============================================================================
# OUTPUT DIRECTORY CONFIGURATION
# =============================================================================

# Base directory for race weekend outputs
OUTPUT_BASE_DIR = "outputs/race_weekend"


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
        if session == "fp1":
            summary_lines.extend(
                [
                    "- 60 minutes of practice running",
                    "- Driver and team data collection",
                    "- Tyre testing and setup work",
                ]
            )
        elif session == "fp2":
            summary_lines.extend(
                [
                    "- 60 minutes of practice running",
                    "- Qualifying simulation practice",
                    "- Race setup refinement",
                ]
            )
        elif session == "fp3":
            summary_lines.extend(
                [
                    "- 60 minutes of final practice",
                    "- Qualifying preparation",
                    "- Last minute setup changes",
                ]
            )
        elif session == "qualifying":
            summary_lines.extend(
                [
                    "- Q1: 18 minutes (eliminate slowest 5 drivers)",
                    "- Q2: 15 minutes (eliminate slowest 5 drivers)",
                    "- Q3: 12 minutes (top 10 battle for pole)",
                ]
            )
        elif session == "sprint":
            summary_lines.extend(
                [
                    "- 100km sprint race (~21-24 laps)",
                    "- No mandatory pit stops",
                    "- Points awarded to top 8 finishers (8-7-6-5-4-3-2-1)",
                    "- Results determine main race starting grid",
                ]
            )
    elif status == "completed":
        summary_lines.extend(
            [
                "## Results",
                "",
                "Race simulation completed successfully.",
                "",
                "See output files in this directory for details.",
            ]
        )
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

    with open(summary_path, "w") as f:
        f.write(summary_content)

    return summary_path


def generate_race_weekend_report(
    track_name: str,
    sessions: List[str],
    session_results: Dict[str, dict],
    output_dir: str,
) -> str:
    """
    Generate a race weekend report markdown file.

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
        f"# F1 Race Weekend Report",
        "",
        f"## Event Information",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Track | {track_name} |",
        f"| GP Name | {gp_name} |",
        f"| Sessions Run | {', '.join(sessions)} |",
        f"",
    ]

    # Session summaries
    lines.extend(
        [
            "## Session Summaries",
            "",
        ]
    )

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
                f"**Output Directory:** `{session}/`",
                "",
            ]
        )

        if session == "race" and status == "completed":
            # Link to race-specific report if available
            lines.extend(
                [
                    "**Race Results:**",
                    "",
                    f"- [Race Results CSV]({session}/race_results_{gp_name.lower()}.csv)",
                    f"- [Dice Rolls CSV]({session}/dice_rolls_{gp_name.lower()}.csv)",
                    f"- [Race Report]({session}/race_report_{gp_name.lower()}.md)",
                    "",
                ]
            )

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

    lines.extend(
        [
            "",
            "---",
            "",
            f"*Report generated by F1 Race Weekend Simulator*",
        ]
    )

    report_content = "\n".join(lines)
    report_path = os.path.join(output_dir, "race_weekend_report.md")

    with open(report_path, "w") as f:
        f.write(report_content)

    return report_path


# =============================================================================
# SESSION SIMULATION MODULES (PLACEHOLDERS FOR NOT-YET-IMPLEMENTED MODULES)
# =============================================================================


def simulate_fp1(track_name: str, output_dir: Optional[str] = None, **kwargs) -> dict:
    """
    Simulate Free Practice 1 session.

    Placeholder for FP1 module - not yet implemented.
    """
    print(f"\n{'=' * 60}")
    print(f"FP1 - Free Practice 1 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")
    print("Note: FP1 simulation not yet implemented.")
    print("This session would include:")
    print("  - 60 minutes of practice running")
    print("  - Driver and team data collection")
    print("  - Tyre testing and setup work")

    # Generate session summary if output directory provided
    if output_dir:
        generate_session_summary("fp1", track_name, "not_implemented", output_dir)

    return {
        "session": "fp1",
        "status": "not_implemented",
        "track": track_name,
    }


def simulate_fp2(track_name: str, output_dir: Optional[str] = None, **kwargs) -> dict:
    """
    Simulate Free Practice 2 session.

    Placeholder for FP2 module - not yet implemented.
    """
    print(f"\n{'=' * 60}")
    print(f"FP2 - Free Practice 2 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")
    print("Note: FP2 simulation not yet implemented.")
    print("This session would include:")
    print("  - 60 minutes of practice running")
    print("  - Qualifying simulation practice")
    print("  - Race setup refinement")

    # Generate session summary if output directory provided
    if output_dir:
        generate_session_summary("fp2", track_name, "not_implemented", output_dir)

    return {
        "session": "fp2",
        "status": "not_implemented",
        "track": track_name,
    }


def simulate_fp3(track_name: str, output_dir: Optional[str] = None, **kwargs) -> dict:
    """
    Simulate Free Practice 3 session.

    Placeholder for FP3 module - not yet implemented.
    """
    print(f"\n{'=' * 60}")
    print(f"FP3 - Free Practice 3 Session")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")
    print("Note: FP3 simulation not yet implemented.")
    print("This session would include:")
    print("  - 60 minutes of final practice")
    print("  - Qualifying preparation")
    print("  - Last minute setup changes")

    # Generate session summary if output directory provided
    if output_dir:
        generate_session_summary("fp3", track_name, "not_implemented", output_dir)

    return {
        "session": "fp3",
        "status": "not_implemented",
        "track": track_name,
    }


def simulate_qualifying(
    track_name: str, output_dir: Optional[str] = None, **kwargs
) -> dict:
    """
    Simulate Qualifying session (Q1, Q2, Q3).

    Placeholder for Qualifying module - not yet implemented.
    """
    print(f"\n{'=' * 60}")
    print(f"Qualifying Session - Q1, Q2, Q3")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")
    print("Note: Qualifying simulation not yet implemented.")
    print("This session would include:")
    print("  - Q1: 18 minutes (eliminate slowest 5 drivers)")
    print("  - Q2: 15 minutes (eliminate slowest 5 drivers)")
    print("  - Q3: 12 minutes (top 10 battle for pole)")

    # Generate session summary if output directory provided
    if output_dir:
        generate_session_summary(
            "qualifying", track_name, "not_implemented", output_dir
        )

    return {
        "session": "qualifying",
        "status": "not_implemented",
        "track": track_name,
    }


def simulate_sprint(
    track_name: str,
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
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

        # Run sprint race
        results = run_sprint_race(
            track_name=track_name,
            seed=seed,
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
            "output_dir": results.get("output_dir"),
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


def simulate_race(
    track_name: str,
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
    is_race_weekend: bool = False,
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
    """
    print(f"\n{'=' * 60}")
    print(f"RACE - Grand Prix")
    print(f"Track: {track_name}")
    print(f"{'=' * 60}")

    # Import the race simulation module
    import src.simulation.enhanced_long_dist_sim as elds
    from src.simulation.test_track_suite import create_driver_csv

    # Get the GP name for the track
    track_config = AVAILABLE_TRACKS.get(track_name, {})
    gp_name = track_config.get("gp_name", track_name)

    # Create driver CSV file for this track if it doesn't exist
    csv_path = create_driver_csv(gp_name)

    # Prepare arguments for the simulation
    sim_args = [f"--gp-name", gp_name, "--csv-file", csv_path]

    if seed is not None:
        sim_args.extend(["--seed", str(seed)])

    # Run the race simulation
    print(f"\nStarting race simulation for {gp_name}...")

    # Track where the race outputs are stored
    race_output_path = None
    original_output_dir = "outputs/enhanced_sim"

    try:
        result = elds.main(sim_args)

        # Check if simulation returned valid results
        if result is None:
            raise RuntimeError("Race simulation returned no results")

        # Find the most recent output directory for this track
        # The simulation creates: outputs/enhanced_sim/{track}_{datetime}
        if os.path.exists(original_output_dir):
            # Get all subdirectories matching the track name
            pattern = os.path.join(original_output_dir, f"{gp_name}_*")
            dirs = glob.glob(pattern)
            if dirs:
                # Sort by modification time, get most recent
                race_output_path = max(dirs, key=os.path.getmtime)

        # For race weekend mode, copy outputs to the race weekend directory
        copied_files = {}
        if is_race_weekend and output_dir and race_output_path:
            copied_files = copy_race_outputs_to_weekend(
                race_output_path, output_dir, gp_name
            )

        # Generate session summary if output directory provided
        if output_dir:
            generate_session_summary("race", track_name, "completed", output_dir)

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
    session_map = {
        "fp1": simulate_fp1,
        "fp2": simulate_fp2,
        "fp3": simulate_fp3,
        "qualifying": simulate_qualifying,
        "sprint": simulate_sprint,
        "race": simulate_race,
    }

    results = {}
    for session in sessions:
        if session.lower() in session_map:
            session_key = session.lower()
            session_output_dir = session_dirs.get(session_key)

            # Pass is_race_weekend=True only for full race weekend simulation
            extra_kwargs = {}
            if session_key == "race" and is_full_weekend:
                extra_kwargs["is_race_weekend"] = True
                extra_kwargs["output_dir"] = session_output_dir

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
  Monaco, Spain, Monza, Italy, Australia, Bahrain, China, Japan
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
    print(f"# SIMULATION COMPLETE")
    print(f"{'#' * 70}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
