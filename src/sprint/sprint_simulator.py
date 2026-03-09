"""
F1 Sprint Race Simulator.

This module simulates sprint races for the 2022 sprint race tracks:
- Imola (Emilia Romagna GP): 21 laps, 4.909 km
- Austria (Red Bull Ring): 24 laps, 4.318 km
- Sao Paulo (Brazil): 24 laps, 4.309 km

Sprint races are 100km short races with no mandatory pit stops.
Results determine the starting grid for the main Grand Prix.

Usage:
    from sprint import run_sprint_race, StartingGridConnector

    # Run sprint race
    results = run_sprint_race("Imola", seed=42)

    # Create connector for main race
    connector = StartingGridConnector.from_sprint_results(results)
    grid_positions = connector.get_starting_grid()
"""

import argparse
import sys
import os
import csv
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Handle PYTHONPATH for module imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import numpy as np

# Import config loader for driver data
from src.utils.config_loader import get_drivers, get_teams

# Import from existing simulation modules
from simulation.enhanced_long_dist_sim import (
    EnhancedRaceSimulator,
    RaceState,
    DiceRollingLogger,
    get_team_stabilities,
    get_driver_personality,
    calculate_driver_error_probability,
    read_driver_data,
    load_pitlane_time_data,
    get_track_characteristics,
    calculate_base_lap_time,
    calculate_degradation_with_cliff,
    calculate_dr_based_std,
    roll_d6,
    roll_d10,
    roll_d100,
)

# Import DRS config reader
from sprint.drs_config_reader import load_drs_config, get_track_drs_summary
from sprint.starting_grid_connector import StartingGridConnector, GridSourceType

# =============================================================================
# SPRINT RACE CONFIGURATION
# =============================================================================

# Real-world track data for sprint races (100km distance)
SPRINT_TRACKS = {
    "Imola": {
        "gp_name": "Imola",  # Use Imola for track characteristics
        "track_length_km": 4.909,
        "sprint_laps": 21,  # 100km / 4.909km = 20.37 → 21 laps
        "base_lap_time": 82.0,  # Estimated base lap time
        "drs_zones": 2,
        "characteristics": "high_downforce, technical, narrow",
    },
    "Austria": {
        "gp_name": "Austria",
        "track_length_km": 4.318,
        "sprint_laps": 24,  # 100km / 4.318km = 23.16 → 24 laps
        "base_lap_time": 68.0,  # Short lap, fast track
        "drs_zones": 3,
        "characteristics": "high_speed, short_lap, multiple_drs",
    },
    "Sao_Paulo": {
        "gp_name": "Brazil",
        "track_length_km": 4.309,
        "sprint_laps": 24,  # 100km / 4.309km = 23.21 → 24 laps
        "base_lap_time": 72.0,  # Anti-clockwise, high altitude
        "drs_zones": 2,
        "characteristics": "high_altitude, anti_clockwise, overtaking_friendly",
    },
}

# Sprint race points (2022 format: 8-7-6-5-4-3-2-1)
SPRINT_POINTS = [8, 7, 6, 5, 4, 3, 2, 1]

# Output directory for sprint races
SPRINT_OUTPUT_DIR = os.path.join("outputs", "sprint_sim")


# =============================================================================
# SPRINT RACE SIMULATOR
# =============================================================================


class SprintRaceSimulator:
    """
    Sprint race simulator - simplified version of main race simulator.

    Key differences from main race:
    - Shorter distance (100km vs 300+km)
    - No mandatory pit stops
    - Simplified strategy
    """

    def __init__(
        self,
        track_name: str,
        driver_data: Dict[str, Dict],
        random_seed: Optional[int] = None,
        output_dir: Optional[str] = None,
        grid_positions: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize sprint race simulator.

        Args:
            track_name: Name of the track (Imola, Austria, Sao_Paulo)
            driver_data: Dictionary of driver data
            random_seed: Optional random seed for reproducibility
            output_dir: Optional output directory for saving results
            grid_positions: Optional dict mapping driver_name -> grid_position from Sprint Qualifying
        """
        self.track_name = track_name
        self.output_dir = output_dir
        self.track_config = SPRINT_TRACKS.get(track_name)
        if not self.track_config:
            raise ValueError(f"Unknown sprint track: {track_name}")

        self.num_laps = self.track_config["sprint_laps"]
        self.base_lap_time = self.track_config["base_lap_time"]
        self.driver_data = driver_data
        self.grid_positions = grid_positions or {}  # From Sprint Qualifying

        # Set random seed
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        # Initialize dice logger
        self.dice_logger = DiceRollingLogger(track_name)

        # Load team stabilities
        self.team_stabilities = get_team_stabilities()

        # Extract driver teams
        self.driver_teams = {
            driver: info.get("Team", "Unknown") for driver, info in driver_data.items()
        }

        # Load track characteristics
        all_track_chars = get_track_characteristics()
        gp_name = self.track_config["gp_name"].lower()
        self.track_chars = all_track_chars.get(gp_name, {"abrasion": 0.5, "grip": 0.7})

        # Initialize race state
        self.race_state = RaceState(self.num_laps, driver_data, self.dice_logger)

        # Sprint race has no mandatory pit stops
        self.pit_stops_disabled = True

        # Results storage
        self.results = {}
        self.lap_times = {driver: [] for driver in driver_data.keys()}
        self.cumulative_times = {driver: 0.0 for driver in driver_data.keys()}

    def simulate_sprint(self) -> Dict[str, Any]:
        """
        Run the sprint race simulation.

        Returns:
            Dictionary containing race results and metadata
        """
        print(f"\n{'=' * 60}")
        print(f"SPRINT RACE - {self.track_name}")
        print(f"Laps: {self.num_laps} | Distance: ~100km")
        print(f"{'=' * 60}")

        # Load and display DRS config
        drs_config = load_drs_config(self.track_name)
        if drs_config:
            print(f"\nDRS Config: {get_track_drs_summary(self.track_name)}")
            print(f"  Difficulty: {drs_config.get('difficulty', 'unknown')}")
            print(f"  Total Distance: {drs_config.get('total_distance')}m")

        # Initialize results for each driver
        for driver in self.driver_data.keys():
            self.results[driver] = {
                "Driver": driver,
                "Team": self.driver_teams.get(driver, "Unknown"),
                "Position": 0,
                "GridPosition": 0,  # Will be set based on qualifying (not implemented)
                "TotalTime": 0.0,
                "BestLap": float("inf"),
                "LapTimes": [],
                "Points": 0,
                "Incidents": [],
                "laps_completed": 0,
                "interval": 0.0,
            }

        # Set initial grid positions from Sprint Qualifying if available
        # Otherwise use random grid (fallback)
        if self.grid_positions:
            # Use grid positions from Sprint Qualifying
            print(f"  Using Sprint Qualifying grid positions")
            for driver in self.driver_data.keys():
                grid_pos = self.grid_positions.get(driver, 999)
                self.results[driver]["GridPosition"] = grid_pos
                self.results[driver]["Position"] = grid_pos
        else:
            # Fallback: random grid (should not happen in full weekend mode)
            print(f"  No Sprint Qualifying results - using random grid")
            drivers_list = list(self.driver_data.keys())
            random.shuffle(drivers_list)
            for i, driver in enumerate(drivers_list, 1):
                self.results[driver]["GridPosition"] = i
                self.results[driver]["Position"] = i

        # Simulate each lap
        for lap in range(1, self.num_laps + 1):
            self.race_state.current_lap = lap
            self._simulate_lap(lap)

            if lap % 5 == 0 or lap == self.num_laps:
                print(f"  Completed lap {lap}/{self.num_laps}")

        # Calculate final positions based on cumulative times
        self._calculate_final_results()

        # Award points
        self._award_sprint_points()

        # Generate output
        output_dir = self._save_results()

        return {
            "track": self.track_name,
            "laps": self.num_laps,
            "results": self.results,
            "final_positions": self._get_final_positions(),
            "output_dir": output_dir,
        }

    def _simulate_lap(self, lap: int) -> None:
        """Simulate a single lap for all drivers."""
        # Sort drivers by current cumulative time (race order)
        sorted_drivers = sorted(self.cumulative_times.items(), key=lambda x: x[1])

        for position, (driver, _) in enumerate(sorted_drivers, 1):
            driver_info = self.driver_data[driver]
            r_value = driver_info.get("R_Value", 300)
            dr_value = driver_info.get("DR_Value", 0)

            # Calculate base lap time
            base_time = calculate_base_lap_time(r_value, self.track_name.lower())

            # Add random variation based on DR value
            std = calculate_dr_based_std(dr_value, 0, 100, base_std=0.3)
            variation = np.random.normal(0, std)

            # Add track characteristics effect
            tyre_compound = "MEDIUM"  # Sprint races typically use medium tyres
            degradation = calculate_degradation_with_cliff(
                lap, tyre_compound, r_value, 320, self.track_chars, self.num_laps
            )

            # Calculate final lap time
            lap_time = base_time + variation + degradation

            # Store lap time
            self.lap_times[driver].append(lap_time)
            self.cumulative_times[driver] += lap_time
            self.results[driver]["LapTimes"].append(lap_time)
            self.results[driver]["laps_completed"] += 1

            # Update best lap
            if lap_time < self.results[driver]["BestLap"]:
                self.results[driver]["BestLap"] = lap_time

                # Log dice roll for best lap achievement
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type="best_lap",
                    dice_type="d100",
                    dice_result=roll_d100(),
                    outcome="new_best_lap",
                    race_time=self.cumulative_times[driver],
                    details={"lap_time": round(lap_time, 3)},
                )

            # Random dice roll for minor incidents (1% chance per lap)
            incident_roll = roll_d100()
            if incident_roll <= 1:
                incident_type = "minor_contact" if incident_roll == 1 else "off_track"
                time_loss = random.uniform(0.5, 2.0)
                self.cumulative_times[driver] += time_loss
                self.results[driver]["Incidents"].append(
                    {
                        "lap": lap,
                        "type": incident_type,
                        "time_loss": time_loss,
                    }
                )
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type=incident_type,
                    dice_type="d100",
                    dice_result=incident_roll,
                    outcome="incident_occurred",
                    race_time=self.cumulative_times[driver],
                    details={"time_loss": round(time_loss, 3)},
                )

        # Update positions based on cumulative times
        self._update_positions()

    def _update_positions(self) -> None:
        """Update race positions based on laps completed (desc) then cumulative times (asc)."""
        sorted_drivers = sorted(
            self.cumulative_times.items(),
            key=lambda x: (-self.results[x[0]]["laps_completed"], x[1]),
        )
        for position, (driver, _) in enumerate(sorted_drivers, 1):
            self.results[driver]["Position"] = position

    def _calculate_final_results(self) -> None:
        """Calculate final race results with intervals."""
        for driver in self.driver_data.keys():
            self.results[driver]["TotalTime"] = self.cumulative_times[driver]

        # Sort by laps_completed (desc), then cumulative_time (asc)
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (-x[1]["laps_completed"], x[1]["TotalTime"]),
        )

        # Calculate intervals (gap to leader)
        leader_time = None
        for position, (driver, result) in enumerate(sorted_results, 1):
            if position == 1:
                # Leader has no interval (or 0.0)
                result["interval"] = 0.0
                leader_time = result["TotalTime"]
            else:
                # Calculate gap to leader
                result["interval"] = result["TotalTime"] - leader_time

            # Update position
            result["Position"] = position

    def _get_final_positions(self) -> Dict[int, str]:
        """Get final positions as position -> driver mapping."""
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (-x[1]["laps_completed"], x[1]["TotalTime"]),
        )
        return {pos: driver for pos, (driver, _) in enumerate(sorted_results, 1)}

    def _award_sprint_points(self) -> None:
        """Award sprint race points to top 8 finishers."""
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (-x[1]["laps_completed"], x[1]["TotalTime"]),
        )

        for i, (driver, _) in enumerate(sorted_results[:8], 0):
            if i < len(SPRINT_POINTS):
                self.results[driver]["Points"] = SPRINT_POINTS[i]

    def _save_results(self) -> str:
        """Save race results to CSV and generate report."""
        # Use provided output_dir or create new one
        if self.output_dir:
            output_dir = self.output_dir
            os.makedirs(output_dir, exist_ok=True)
        else:
            # Create output directory
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_dir = os.path.join(
                SPRINT_OUTPUT_DIR, f"{self.track_name}_{timestamp}"
            )
            os.makedirs(output_dir, exist_ok=True)

        # Save results to CSV
        results_df = pd.DataFrame(
            [
                {
                    "Position": data["Position"],
                    "Driver": data["Driver"],
                    "Team": data["Team"],
                    "GridPosition": data["GridPosition"],
                    "TotalTime": f"{data['TotalTime']:.3f}",
                    "BestLap": f"{data['BestLap']:.3f}"
                    if data["BestLap"] != float("inf")
                    else "N/A",
                    "Points": data["Points"],
                    "LapsCompleted": data["laps_completed"],
                    "Interval": f"+{data['interval']:.3f}" if data["interval"] > 0 else "0.000",
                }
                for driver, data in sorted(
                    self.results.items(), key=lambda x: x[1]["Position"]
                )
            ]
        )

        csv_path = os.path.join(
            output_dir, f"sprint_results_{self.track_name.lower()}.csv"
        )
        results_df.to_csv(csv_path, index=False)

        # Save dice rolls
        self.dice_logger.save_to_csv(output_dir)

        # Generate report
        self._generate_report(output_dir)

        print(f"\nResults saved to: {output_dir}")
        return output_dir

    def _generate_report(self, output_dir: str) -> None:
        """Generate a human-readable race report."""
        lines = [
            f"# Sprint Race Report - {self.track_name}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Laps:** {self.num_laps}",
            f"**Distance:** ~100km",
            "",
            "## Final Results",
            "",
            "| Position | Driver | Team | Grid | Total Time | Interval | Laps | Best Lap | Points |",
            "|----------|--------|------|------|------------|----------|------|----------|--------|",
        ]

        for driver, data in sorted(
            self.results.items(), key=lambda x: x[1]["Position"]
        ):
            best_lap = (
                f"{data['BestLap']:.3f}" if data["BestLap"] != float("inf") else "N/A"
            )
            interval_str = f"+{data['interval']:.3f}s" if data["interval"] > 0 else "0.000s"
            lines.append(
                f"| {data['Position']} | {data['Driver']} | {data['Team']} | "
                f"{data['GridPosition']} | {data['TotalTime']:.3f}s | {interval_str} | "
                f"{data['laps_completed']} | {best_lap}s | {data['Points']} |"
            )

        lines.extend(
            [
                "",
                "## Sprint Race Points",
                "",
                "Points awarded to top 8 finishers: 8-7-6-5-4-3-2-1",
                "",
            ]
        )

        points_winners = [
            (d, data) for d, data in self.results.items() if data["Points"] > 0
        ]
        if points_winners:
            lines.append("### Points Scorers")
            lines.append("")
            for driver, data in sorted(points_winners, key=lambda x: x[1]["Position"]):
                lines.append(
                    f"- **P{data['Position']}** {driver}: {data['Points']} points"
                )

        lines.extend(
            [
                "",
                "---",
                "",
                "*Sprint race results determine the starting grid for the main Grand Prix*",
            ]
        )

        report_path = os.path.join(
            output_dir, f"sprint_report_{self.track_name.lower()}.md"
        )
        with open(report_path, "w") as f:
            f.write("\n".join(lines))


# =============================================================================
# PUBLIC API
# =============================================================================


def run_sprint_race(
    track_name: str,
    driver_data: Optional[Dict[str, Dict]] = None,
    seed: Optional[int] = None,
    output_dir: Optional[str] = None,
    grid_positions: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Run a sprint race simulation.

    Args:
        track_name: Name of the track (Imola, Austria, Sao_Paulo)
        driver_data: Optional driver data dictionary. If None, uses default Spain GP data.
        seed: Optional random seed for reproducibility
        output_dir: Optional output directory. If provided, saves results there.
        grid_positions: Optional dict mapping driver_name -> grid_position from Sprint Qualifying

    Returns:
        Dictionary containing race results
    """
    # Load default driver data if not provided
    if driver_data is None:
        # Use driver data from config loader (2022 grid + Andretti)
        drivers = get_drivers()
        teams = get_teams()

        # Create driver data dict with R_Value and DR_Value ratings
        # R_Value: overall race rating (base 300 + skill)
        # DR_Value: delta rating relative to teammate
        driver_data = {}
        for driver in drivers:
            team = teams.get(driver, "Unknown")
            # Assign R_Value based on driver tier
            # Top drivers get higher values
            if driver in ["Verstappen", "Leclerc", "Hamilton"]:
                r_value = 320.0
            elif driver in ["Norris", "Russell", "Alonso"]:
                r_value = 315.0
            elif driver in ["Sainz", "Ricciardo", "Gasly"]:
                r_value = 310.0
            elif driver in ["Perez", "Ocon", "Bottas"]:
                r_value = 305.0
            elif driver in ["Tsunoda", "Stroll", "Vettel"]:
                r_value = 300.0
            elif driver in ["Albon", "Magnussen", "Schumacher"]:
                r_value = 295.0
            elif driver in ["Latifi", "Zhou", "Grosjean", "Schwartzman"]:
                r_value = 290.0
            else:
                r_value = 300.0

            # DR_Value: delta to teammate (random but consistent)
            # Use deterministic hash (md5) of driver name for consistency
            import hashlib

            dr_hash = int(hashlib.md5(driver.encode()).hexdigest(), 16)
            dr_value = 25.0 + (dr_hash % 20)

            driver_data[driver] = {
                "Team": team,
                "R_Value": r_value,
                "DR_Value": dr_value,
            }

    # Create simulator and run race
    simulator = SprintRaceSimulator(
        track_name=track_name,
        driver_data=driver_data,
        random_seed=seed,
        output_dir=output_dir,
        grid_positions=grid_positions,
    )

    return simulator.simulate_sprint()


def main(args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Main entry point for sprint race simulation.

    Args:
        args: Command line arguments

    Returns:
        Race results dictionary
    """
    parser = argparse.ArgumentParser(description="F1 Sprint Race Simulator")
    parser.add_argument(
        "--track",
        type=str,
        required=True,
        choices=["Imola", "Austria", "Sao_Paulo"],
        help="Sprint race track",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--driver-csv",
        type=str,
        default=None,
        help="Path to driver data CSV file",
    )

    parsed_args = parser.parse_args(args)

    # Load driver data
    if parsed_args.driver_csv:
        driver_data = read_driver_data(parsed_args.driver_csv)
    else:
        driver_data = None

    # Run sprint race
    results = run_sprint_race(
        track_name=parsed_args.track,
        driver_data=driver_data,
        seed=parsed_args.seed,
    )

    return results


if __name__ == "__main__":
    main()
