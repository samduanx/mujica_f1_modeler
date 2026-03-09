"""
F1 Race Report Generator.

Generates comprehensive markdown reports from race simulation results.
Reads race results CSV and dice rolls CSV to create detailed analysis.

Usage:
    python -m simulation.report_generator --track-name Monaco --output-dir outputs/enhanced_sim/Monaco_2024-02-23_19-53-14
"""

import argparse
import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict


def read_csv_file(filepath: str) -> List[Dict[str, Any]]:
    """Read a CSV file and return a list of dictionaries."""
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_race_results(csv_path: str) -> List[Dict[str, Any]]:
    """Parse race results CSV file."""
    return read_csv_file(csv_path)


def parse_dice_rolls(csv_path: str) -> List[Dict[str, Any]]:
    """Parse dice rolls CSV file."""
    return read_csv_file(csv_path)


def generate_race_summary(race_results: List[Dict[str, Any]]) -> str:
    """Generate race summary section with gap to car ahead."""
    lines = ["## Race Summary\n"]

    if not race_results:
        lines.append("No race results available.\n")
        return "\n".join(lines)

    lines.append(
        "| Position | Driver | Team | Gap | Total Time | Pit Stops | Fault Degradation | Notes |"
    )
    lines.append(
        "|----------|--------|------|-----|------------|-----------|-------------------|-------|"
    )

    # Track info for gap calculation
    prev_laps_completed = None
    prev_total_time = None
    leader_laps_completed = None
    leader_total_time = None

    for i, result in enumerate(race_results):
        pos = result.get("position", "N/A")
        driver = result.get("driver", "Unknown")
        team = result.get("team", "Unknown")
        total_time = result.get("total_time", "N/A")
        num_pits = result.get("num_pits", "0")
        degradation = result.get("fault_degradation", "0")

        # Check for DNF
        dnf = result.get("dnf", "")
        notes = dnf if dnf else ""

        # Format time
        try:
            time_val = float(total_time)
            time_str = f"{time_val:.3f}s"
        except (ValueError, TypeError):
            time_str = str(total_time)

        # Calculate gap to car ahead
        gap_str = ""
        if i == 0:
            # Winner has no gap
            gap_str = "-"
            try:
                leader_laps_completed = int(result.get("laps_completed", 0))
                leader_total_time = float(total_time)
            except (ValueError, TypeError):
                leader_laps_completed = 0
                leader_total_time = 0.0
        else:
            try:
                current_laps = int(result.get("laps_completed", 0))
                current_time = float(total_time)

                # Check if this is a lapped car
                if leader_laps_completed and current_laps < leader_laps_completed:
                    laps_down = leader_laps_completed - current_laps
                    gap_str = f"+{laps_down} Lap" if laps_down == 1 else f"+{laps_down} Laps"
                elif prev_laps_completed and current_laps < prev_laps_completed:
                    # Lapped compared to car ahead but not leader
                    laps_down = prev_laps_completed - current_laps
                    gap_str = f"+{laps_down} Lap" if laps_down == 1 else f"+{laps_down} Laps"
                elif prev_total_time is not None:
                    # Same lap - calculate time gap to car ahead
                    gap_seconds = current_time - prev_total_time
                    gap_str = f"+{gap_seconds:.3f}s"
                else:
                    gap_str = "—"
            except (ValueError, TypeError):
                gap_str = "—"

        # Update previous car info for next iteration
        try:
            prev_laps_completed = int(result.get("laps_completed", 0))
            prev_total_time = float(total_time)
        except (ValueError, TypeError):
            prev_laps_completed = 0
            prev_total_time = 0.0

        lines.append(
            f"| {pos} | {driver} | {team} | {gap_str} | {time_str} | {num_pits} | {degradation} | {notes} |"
        )

    lines.append("")
    return "\n".join(lines)


def generate_pit_stop_analysis(race_results: List[Dict[str, Any]]) -> str:
    """Generate pit stop analysis section."""
    lines = ["## Pit Stop Analysis\n"]

    # Group by number of pit stops
    pit_counts = defaultdict(int)
    for result in race_results:
        pits = result.get("num_pits", "0")
        try:
            pit_counts[int(pits)] += 1
        except ValueError:
            pass

    lines.append("### Pit Stop Distribution\n")
    lines.append("| Number of Stops | Count |")
    lines.append("|-----------------|-------|")

    for num_stops in sorted(pit_counts.keys()):
        lines.append(f"| {num_stops} | {pit_counts[num_stops]} |")

    lines.append("")
    return "\n".join(lines)


def generate_dice_rolling_statistics(dice_rolls: List[Dict[str, Any]]) -> str:
    """Generate dice rolling statistics section."""
    lines = ["## Dice Rolling Statistics\n"]

    if not dice_rolls:
        lines.append("No dice rolling data available.\n")
        return "\n".join(lines)

    # Count by incident type
    incident_counts = defaultdict(int)
    outcome_counts = defaultdict(int)

    for roll in dice_rolls:
        incident_type = roll.get("incident_type", "unknown")
        outcome = roll.get("outcome", "unknown")
        incident_counts[incident_type] += 1
        outcome_counts[outcome] += 1

    lines.append("### Rolls by Incident Type\n")
    lines.append("| Incident Type | Count |")
    lines.append("|---------------|-------|")

    for incident_type, count in sorted(incident_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {incident_type} | {count} |")

    lines.append("")
    lines.append("### Rolls by Outcome\n")
    lines.append("| Outcome | Count |")
    lines.append("|---------|-------|")

    for outcome, count in sorted(outcome_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {outcome} | {count} |")

    lines.append("")

    # Vehicle fault analysis
    fault_rolls = [
        r for r in dice_rolls if r.get("incident_type") == "vehicle_fault_check"
    ]
    if fault_rolls:
        lines.append("### Vehicle Fault Analysis\n")

        fault_outcomes = defaultdict(int)
        for roll in fault_rolls:
            outcome = roll.get("outcome", "unknown")
            fault_outcomes[outcome] += 1

        lines.append("| Outcome | Count |")
        lines.append("|---------|-------|")
        for outcome, count in fault_outcomes.items():
            lines.append(f"| {outcome} | {count} |")

        lines.append("")

    return "\n".join(lines)


def generate_safety_car_analysis(dice_rolls: List[Dict[str, Any]]) -> str:
    """Generate Safety Car/VSC periods analysis."""
    lines = ["## Safety Car and VSC Analysis\n"]

    # Find SC and VSC events
    sc_events = [r for r in dice_rolls if r.get("incident_type") == "safety_car"]
    vsc_events = [r for r in dice_rolls if r.get("incident_type") == "vsc"]

    if not sc_events and not vsc_events:
        lines.append("No Safety Car or VSC periods during this race.\n")
        return "\n".join(lines)

    if sc_events:
        lines.append("### Safety Car Periods\n")
        lines.append("| Lap | Duration | Reason |")
        lines.append("|-----|----------|--------")

        for event in sc_events:
            lap = event.get("lap", "N/A")
            dice_result = event.get("dice_result", "N/A")
            reason = (
                event.get("details", {}).get("reason", "N/A")
                if event.get("details")
                else "N/A"
            )
            lines.append(f"| {lap} | {dice_result} laps | {reason} |")

        lines.append("")

    if vsc_events:
        lines.append("### Virtual Safety Car Periods\n")
        lines.append("| Lap | Duration | Reason |")
        lines.append("|-----|----------|--------")

        for event in vsc_events:
            lap = event.get("lap", "N/A")
            dice_result = event.get("dice_result", "N/A")
            reason = (
                event.get("details", {}).get("reason", "N/A")
                if event.get("details")
                else "N/A"
            )
            lines.append(f"| {lap} | {dice_result} laps | {reason} |")

        lines.append("")

    return "\n".join(lines)


def generate_standing_start_analysis(dice_rolls: List[Dict[str, Any]]) -> str:
    """Generate standing start analysis."""
    lines = ["## Standing Start Analysis\n"]

    # Find standing start events (lap 0)
    start_rolls = [r for r in dice_rolls if r.get("lap") == "0" or r.get("lap") == 0]

    if not start_rolls:
        lines.append("No standing start data available.\n")
        return "\n".join(lines)

    # Categorize outcomes
    outcome_counts = defaultdict(int)
    driver_outcomes = defaultdict(dict)

    for roll in start_rolls:
        outcome = roll.get("outcome", "unknown")
        driver = roll.get("driver", "Unknown")
        outcome_counts[outcome] += 1
        driver_outcomes[driver]["outcome"] = outcome

        # Get reaction time if available
        details = roll.get("details", {})
        if details and "reaction_time" in details:
            try:
                driver_outcomes[driver]["reaction_time"] = float(
                    details["reaction_time"]
                )
            except (ValueError, TypeError):
                pass

    lines.append("### Start Outcome Distribution\n")
    lines.append("| Outcome | Count |")
    lines.append("|---------|-------|")

    for outcome, count in sorted(outcome_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {outcome} | {count} |")

    lines.append("")

    # Best starts
    good_starts = [
        (d, info)
        for d, info in driver_outcomes.items()
        if info.get("outcome") in ["excellent_launch", "good"]
    ]

    if good_starts:
        lines.append("### Notable Starts\n")
        lines.append("| Driver | Outcome |")
        lines.append("|--------|---------|")

        for driver, info in good_starts:
            lines.append(f"| {driver} | {info.get('outcome', 'N/A')} |")

        lines.append("")

    return "\n".join(lines)


def generate_driver_incident_counts(
    race_results: List[Dict], dice_rolls: List[Dict]
) -> str:
    """Generate driver incident counts."""
    lines = ["## Driver Incident Counts\n"]

    # From race results
    if race_results:
        lines.append("### Incidents from Race Results\n")
        lines.append("| Driver | Team | Incidents |")
        lines.append("|--------|------|-----------|")

        for result in race_results:
            driver = result.get("driver", "Unknown")
            team = result.get("team", "Unknown")
            incidents = result.get("num_incidents", "0")
            lines.append(f"| {driver} | {team} | {incidents} |")

        lines.append("")

    # From dice rolls - detailed breakdown
    if dice_rolls:
        # Group by driver
        driver_incidents = defaultdict(lambda: defaultdict(int))

        for roll in dice_rolls:
            driver = roll.get("driver", "Unknown")
            incident_type = roll.get("incident_type", "unknown")
            outcome = roll.get("outcome", "unknown")

            # Only count actual incidents (not checks that resulted in no incident)
            if (
                outcome != "no_fault"
                and outcome != "no_error"
                and incident_type != "standing_start"
            ):
                driver_incidents[driver][incident_type] += 1

        if driver_incidents:
            lines.append("### Detailed Incident Breakdown\n")
            lines.append("| Driver | ")

            # Get all incident types
            all_types = set()
            for incidents in driver_incidents.values():
                all_types.update(incidents.keys())

            # Header
            header = ["| Driver |"]
            for itype in sorted(all_types):
                header.append(f" {itype} |")
            lines.append("".join(header))

            # Separator
            sep = ["|--------|"]
            for _ in sorted(all_types):
                sep.append("--------|")
            lines.append("".join(sep))

            # Data rows
            for driver in sorted(driver_incidents.keys()):
                row = [f"| {driver} |"]
                for itype in sorted(all_types):
                    count = driver_incidents[driver].get(itype, 0)
                    row.append(f" {count} |")
                lines.append("".join(row))

            lines.append("")

    return "\n".join(lines)


def generate_dnf_summary(race_results: List[Dict]) -> str:
    """Generate DNF (Did Not Finish) summary section."""
    lines = ["## DNF (Did Not Finish) Summary\n"]

    # Find drivers who DNFed
    dnf_drivers = []

    for result in race_results:
        dnf = result.get("dnf", "")
        if dnf and dnf.upper() == "DNF":
            dnf_drivers.append(
                {
                    "driver": result.get("driver", "Unknown"),
                    "team": result.get("team", "Unknown"),
                    "lap_dnfed": result.get("lap_dnfed", "N/A"),
                    "retirement_reason": result.get("retirement_reason", "Unknown"),
                    "position": result.get("position", "N/A"),
                }
            )

    if not dnf_drivers:
        lines.append("No retirements occurred during this race.\n")
        return "\n".join(lines)

    lines.append("### Retired Drivers\n")
    lines.append("| Position | Driver | Team | Lap Retired | Reason |")
    lines.append("|----------|--------|------|-------------|--------|")

    for entry in sorted(dnf_drivers, key=lambda x: x["position"]):
        lines.append(
            f"| {entry['position']} | {entry['driver']} | {entry['team']} | {entry['lap_dnfed']} | {entry['retirement_reason']} |"
        )

    lines.append("")

    return "\n".join(lines)


def generate_fault_degradation_summary(race_results: List[Dict]) -> str:
    """Generate fault degradation summary."""
    lines = ["## Fault Degradation Summary\n"]

    # Find drivers with fault degradation
    drivers_with_degradation = []

    for result in race_results:
        degradation = result.get("fault_degradation", "0")
        try:
            deg_value = float(degradation)
            if deg_value > 0:
                drivers_with_degradation.append(
                    {
                        "driver": result.get("driver", "Unknown"),
                        "team": result.get("team", "Unknown"),
                        "degradation": deg_value,
                        "position": result.get("position", "N/A"),
                    }
                )
        except (ValueError, TypeError):
            pass

    if not drivers_with_degradation:
        lines.append("No vehicle faults occurred during this race.\n")
        return "\n".join(lines)

    lines.append("### Drivers with Performance Degradation\n")
    lines.append("| Position | Driver | Team | Degradation |")
    lines.append("|----------|--------|------|-------------|")

    for entry in sorted(drivers_with_degradation, key=lambda x: x["position"]):
        lines.append(
            f"| {entry['position']} | {entry['driver']} | {entry['team']} | {entry['degradation'] * 100:.2f}% |"
        )

    lines.append("")

    return "\n".join(lines)


def generate_track_info(track_name: str) -> str:
    """Generate track information header."""
    lines = ["# F1 Race Simulation Report\n"]
    lines.append(f"**Track:** {track_name}")
    lines.append(f"**Data Source:** Parallel World (outputs/tables/)")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    return "\n".join(lines)


def generate_report(
    race_results_path: str,
    dice_rolls_path: str,
    track_name: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate comprehensive markdown report from race results.

    Args:
        race_results_path: Path to race results CSV
        dice_rolls_path: Path to dice rolls CSV
        track_name: Name of the track
        output_path: Optional output path for the report

    Returns:
        Generated markdown report as string
    """
    # Parse data
    race_results = parse_race_results(race_results_path)
    dice_rolls = parse_dice_rolls(dice_rolls_path)

    # Build report sections
    report_sections = []

    # Header
    report_sections.append(generate_track_info(track_name))

    # Race summary
    report_sections.append(generate_race_summary(race_results))

    # DNF summary
    report_sections.append(generate_dnf_summary(race_results))

    # Pit stop analysis
    report_sections.append(generate_pit_stop_analysis(race_results))

    # Fault degradation summary
    report_sections.append(generate_fault_degradation_summary(race_results))

    # Dice rolling statistics
    report_sections.append(generate_dice_rolling_statistics(dice_rolls))

    # Safety car analysis
    report_sections.append(generate_safety_car_analysis(dice_rolls))

    # Standing start analysis
    report_sections.append(generate_standing_start_analysis(dice_rolls))

    # Driver incident counts
    report_sections.append(generate_driver_incident_counts(race_results, dice_rolls))

    # Join all sections
    full_report = "\n".join(report_sections)

    # Save to file if output path provided
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"Report saved to: {output_path}")

    return full_report


def main(argv=None):
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Generate F1 Race Simulation Report")
    parser.add_argument(
        "--track-name", default="Monaco", help="Track name (default: Monaco)"
    )
    parser.add_argument("--output-dir", help="Output directory containing CSV files")
    parser.add_argument(
        "--race-results", help="Path to race results CSV (overrides output-dir)"
    )
    parser.add_argument(
        "--dice-rolls", help="Path to dice rolls CSV (overrides output-dir)"
    )
    parser.add_argument("--output", help="Output path for the report")

    args = parser.parse_args(argv)

    # Determine file paths
    if args.race_results and args.dice_rolls:
        race_results_path = args.race_results
        dice_rolls_path = args.dice_rolls
    elif args.output_dir:
        track_lower = args.track_name.lower()
        race_results_path = os.path.join(
            args.output_dir, f"race_results_{track_lower}.csv"
        )
        dice_rolls_path = os.path.join(args.output_dir, f"dice_rolls_{track_lower}.csv")
    else:
        print(
            "Error: Either provide both --race-results and --dice-rolls, or --output-dir"
        )
        return

    # Determine output path
    output_path = args.output
    if not output_path and args.output_dir:
        output_path = os.path.join(
            args.output_dir, f"race_report_{args.track_name.lower()}.md"
        )

    # Generate report
    generate_report(
        race_results_path=race_results_path,
        dice_rolls_path=dice_rolls_path,
        track_name=args.track_name,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
