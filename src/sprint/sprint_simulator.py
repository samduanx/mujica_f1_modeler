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
    RealTimeLappingDetector,
    LappingEvent,
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
    nonlinear_scaling,
    get_universal_tyre_params_with_cliff,
)

# Import DRS config reader
from sprint.drs_config_reader import load_drs_config, get_track_drs_summary
from sprint.starting_grid_connector import StartingGridConnector, GridSourceType

# =============================================================================
# SPRINT RACE CONFIGURATION
# =============================================================================

# Main race lap counts to calculate sprint laps (1/3 of main race)
MAIN_RACE_LAP_COUNTS = {
    "imola": 63,  # Emilia Romagna GP
    "austria": 71,  # Red Bull Ring
    "brazil": 71,  # Sao Paulo GP / Brazil
    "spain": 66,
    "monaco": 78,
    "monza": 53,
    "bahrain": 57,
    "australia": 58,
    "japan": 53,
    "china": 56,
    "united states": 56,
    "mexico": 71,
    "singapore": 61,
    "abu dhabi": 58,
    "canada": 70,
    "silverstone": 52,
    "hungary": 70,
    "belgium": 44,
    "netherlands": 72,
    "italy": 53,
    "france": 53,
    "azerbaijan": 51,
}


def calculate_sprint_laps(track_name: str) -> int:
    """
    Calculate sprint race laps as approximately 1/3 of main race laps.
    Sprint races are ~100km but should be scaled to main race distance.

    Args:
        track_name: Name of the track

    Returns:
        Number of laps for sprint race (min 15 laps, max 30 laps)
    """
    track_key = track_name.lower().replace(" ", "_").replace("sao_paulo", "brazil")
    main_laps = MAIN_RACE_LAP_COUNTS.get(track_key, 66)

    # Sprint laps = 1/3 of main race, rounded
    sprint_laps = max(15, min(30, round(main_laps / 3)))

    return sprint_laps


# Real-world track data for sprint races
# Sprint laps are now calculated dynamically as 1/3 of main race laps
SPRINT_TRACKS = {
    "Imola": {
        "gp_name": "Imola",
        "track_length_km": 4.909,
        "base_lap_time": 82.0,
        "drs_zones": 2,
        "characteristics": "high_downforce, technical, narrow",
    },
    "Austria": {
        "gp_name": "Austria",
        "track_length_km": 4.318,
        "base_lap_time": 68.0,
        "drs_zones": 3,
        "characteristics": "high_speed, short_lap, multiple_drs",
    },
    "Sao_Paulo": {
        "gp_name": "Brazil",
        "track_length_km": 4.309,
        "base_lap_time": 72.0,
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

        # Calculate sprint laps as 1/3 of main race laps
        self.num_laps = calculate_sprint_laps(track_name)
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

        # Initialize real-time lapping detector (FIA-compliant)
        self.lapping_detector = RealTimeLappingDetector(
            base_lap_time=self.base_lap_time
        )

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
        # Calculate approximate distance
        track_length_km = (
            self.track_config["track_length_km"] if self.track_config else 5.0
        )
        distance_km = round(self.num_laps * track_length_km)

        print(f"\n{'=' * 60}")
        print(f"SPRINT RACE - {self.track_name}")
        print(f"Laps: {self.num_laps} (~1/3 of main race) | Distance: ~{distance_km}km")
        print(f"Pit Stops: DISABLED (weather/safety car only)")
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
                # FIA Lapping fields (real-time tracking)
                "laps_down": 0,  # Number of laps behind the leader
                "is_lapped": False,  # Whether driver has been lapped
                "actual_laps": 0,  # Actual physical laps completed
                "effective_laps": 0,  # Effective laps for classification
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
        # Sort drivers by laps completed (desc), then cumulative time (asc)
        sorted_drivers = sorted(
            self.cumulative_times.items(),
            key=lambda x: (-self.results[x[0]]["laps_completed"], x[1]),
        )

        for position, (driver, _) in enumerate(sorted_drivers, 1):
            driver_info = self.driver_data[driver]
            dr_value = driver_info.get("DR_Value", 0)
            team_pr = driver_info.get("PR_Value", 300)
            r_value = dr_value * team_pr / 100.0  # Calculate R value

            # Calculate base lap time
            track_gp_key = (
                self.track_config["gp_name"].lower()
                if self.track_config and "gp_name" in self.track_config
                else self.track_name.lower()
            )
            base_time = calculate_base_lap_time(dr_value, team_pr, track_gp_key)

            # Add random variation based on DR value
            std_result = calculate_dr_based_std(
                dr_value,
                0,
                100,
                base_std=0.3,
                team_pr=team_pr,
                pr_min=285.0,
                pr_max=310.0,
            )
            std = std_result[0] if isinstance(std_result, tuple) else std_result
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

            # Update actual laps and effective laps
            self.results[driver]["actual_laps"] += 1
            self.results[driver]["effective_laps"] = (
                self.results[driver]["actual_laps"] - self.results[driver]["laps_down"]
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

        # Real-time lapping detection (FIA-compliant)
        # Create temporary results with cumulative_time for lapping detection
        temp_results = {}
        for driver in self.driver_data.keys():
            temp_results[driver] = {
                "cumulative_time": self.cumulative_times[driver],
                "laps_completed": self.results[driver]["laps_completed"],
            }

        lapping_events = self.lapping_detector.detect_lapping(
            results=temp_results,
            current_lap=lap,
            safety_car_active=False,  # Sprint races rarely have safety cars
        )

        # Process lapping events
        for event in lapping_events:
            # Update results with lapping information
            self.results[event.lapped_driver]["laps_down"] = event.laps_down
            self.results[event.lapped_driver]["is_lapped"] = True
            self.results[event.lapped_driver]["effective_laps"] = (
                self.results[event.lapped_driver]["actual_laps"] - event.laps_down
            )

            if event.laps_down > 0:
                print(
                    f"  [LAPPING - Lap {lap}] {event.leader} laps {event.lapped_driver} "
                    f"(+{event.laps_down} Lap{'s' if event.laps_down > 1 else ''})"
                )

        # Update positions based on cumulative times
        self._update_positions()

    def _update_positions(self) -> None:
        """Update race positions based on effective_laps (desc) then cumulative times (asc)."""
        # FIA-compliant: sort by effective_laps (desc), then cumulative_time (asc)
        sorted_drivers = sorted(
            self.cumulative_times.items(),
            key=lambda x: (
                -self.results[x[0]].get(
                    "effective_laps", self.results[x[0]]["laps_completed"]
                ),
                x[1],
            ),
        )
        for position, (driver, _) in enumerate(sorted_drivers, 1):
            self.results[driver]["Position"] = position

    def _calculate_final_results(self) -> None:
        """Calculate final race results with intervals."""
        for driver in self.driver_data.keys():
            self.results[driver]["TotalTime"] = self.cumulative_times[driver]
            # Ensure effective_laps is calculated correctly
            actual_laps = self.results[driver]["actual_laps"]
            laps_down = self.results[driver]["laps_down"]
            self.results[driver]["effective_laps"] = actual_laps - laps_down

        # FIA-compliant final ranking with real-time lapping detection
        # Use effective_laps (actual_laps - laps_down) for classification
        # This ensures drivers who completed more effective laps rank higher
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (
                -x[1].get("effective_laps", x[1]["laps_completed"]),  # Descending
                x[1]["TotalTime"],  # Ascending
            ),
        )

        # Calculate intervals (gap to leader)
        leader_time = None
        leader_effective_laps = None
        for position, (driver, result) in enumerate(sorted_results, 1):
            effective_laps = result.get("effective_laps", result["laps_completed"])

            if position == 1:
                # Leader has no interval (or 0.0)
                result["interval"] = 0.0
                leader_time = result["TotalTime"]
                leader_effective_laps = effective_laps
            else:
                # Check if this driver is lapped compared to leader
                if leader_effective_laps and effective_laps < leader_effective_laps:
                    laps_down = leader_effective_laps - effective_laps
                    result["interval"] = float("inf")  # Mark as lapped
                else:
                    # Calculate gap to leader
                    result["interval"] = result["TotalTime"] - leader_time

            # Update position
            result["Position"] = position

    def _get_final_positions(self) -> Dict[int, str]:
        """Get final positions as position -> driver mapping."""
        # FIA-compliant: sort by effective_laps (desc), then TotalTime (asc)
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (
                -x[1].get("effective_laps", x[1]["laps_completed"]),
                x[1]["TotalTime"],
            ),
        )
        return {pos: driver for pos, (driver, _) in enumerate(sorted_results, 1)}

    def _award_sprint_points(self) -> None:
        """Award sprint race points to top 8 finishers."""
        # FIA-compliant: sort by effective_laps (desc), then TotalTime (asc)
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (
                -x[1].get("effective_laps", x[1]["laps_completed"]),
                x[1]["TotalTime"],
            ),
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
                    "EffectiveLaps": data.get("effective_laps", data["laps_completed"]),
                    "ActualLaps": data.get("actual_laps", data["laps_completed"]),
                    "LapsDown": data.get("laps_down", 0),
                    "IsLapped": "Yes" if data.get("is_lapped", False) else "No",
                    "Interval": f"+{data['interval']:.3f}"
                    if data["interval"] > 0 and data["interval"] != float("inf")
                    else "0.000"
                    if data["interval"] == 0
                    else f"+{data.get('laps_down', 0)} Lap"
                    if data.get("laps_down", 0) == 1
                    else f"+{data.get('laps_down', 0)} Laps",
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
            "| Position | Driver | Team | Grid | Total Time | Interval | Laps | Effective | Laps Down | Best Lap | Points |",
            "|----------|--------|------|------|------------|----------|------|-----------|-----------|----------|--------|",
        ]

        for driver, data in sorted(
            self.results.items(), key=lambda x: x[1]["Position"]
        ):
            best_lap = (
                f"{data['BestLap']:.3f}" if data["BestLap"] != float("inf") else "N/A"
            )

            # Format interval string
            if data["interval"] == 0:
                interval_str = "0.000s"
            elif data["interval"] == float("inf") or data.get("laps_down", 0) > 0:
                laps_down = data.get("laps_down", 0)
                interval_str = (
                    f"+{laps_down} Lap" if laps_down == 1 else f"+{laps_down} Laps"
                )
            else:
                interval_str = f"+{data['interval']:.3f}s"

            effective_laps = data.get("effective_laps", data["laps_completed"])
            actual_laps = data.get("actual_laps", data["laps_completed"])
            laps_down = data.get("laps_down", 0)
            laps_down_str = f"+{laps_down}" if laps_down > 0 else "-"

            lines.append(
                f"| {data['Position']} | {data['Driver']} | {data['Team']} | "
                f"{data['GridPosition']} | {data['TotalTime']:.3f}s | {interval_str} | "
                f"{actual_laps} | {effective_laps} | {laps_down_str} | {best_lap}s | {data['Points']} |"
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

        # Load team PR values for this track (fallback handled in config loader)
        from src.utils.config_loader import get_all_teams_pr

        team_pr_values = get_all_teams_pr(track_name)

        # Driver DR baseline aligned with race-weekend pipeline
        dr_baseline = {
            "Verstappen": 100.5,
            "Perez": 99.925,
            "Hamilton": 100.4,
            "Russell": 100.0,
            "Leclerc": 100.4,
            "Sainz": 99.95,
            "Gasly": 100.1,
            "Tsunoda": 99.85,
            "Alonso": 100.5,
            "Ocon": 99.85,
            "Vettel": 100.3,
            "Stroll": 99.7,
            "Grosjean": 100.1,
            "Schwartzman": 99.6,
            "Norris": 100.1,
            "Ricciardo": 99.875,
            "Bottas": 100.2,
            "Zhou": 99.65,
            "Magnussen": 100.1,
            "Schumacher": 99.675,
            "Albon": 100.1,
            "Latifi": 99.625,
        }

        # Create driver data dict with DR and PR consistent with main race simulation
        driver_data = {}
        for driver in drivers:
            team = teams.get(driver, "Unknown")
            dr_value = dr_baseline.get(driver, 99.5)
            team_pr = team_pr_values.get(team, 300.0)
            r_value = dr_value * team_pr / 100.0

            driver_data[driver] = {
                "Team": team,
                "R_Value": r_value,
                "DR_Value": dr_value,
                "PR_Value": team_pr,
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
