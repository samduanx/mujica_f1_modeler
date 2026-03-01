"""
Enhanced F1 Race Simulation with Full Incident and DRS Integration.

This simulation integrates:
- Incident system (driver errors, vehicle faults, overtakes, VSC/SC, etc.)
- DRS system for overtakes
- Standing start mechanics (F1 standard for clear weather)
- Full dice rolling logging to CSV
- Detailed race reports
- Driver personality model

Usage:
    uv run python src/simulation/enhanced_long_dist_sim.py --gp-name Spain
"""

import argparse
import sys
import os

# Handle PYTHONPATH for module imports
# The project uses 'incidents' and 'drs' as top-level module names within src/
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Also ensure PYTHONPATH from environment is respected
_env_pythonpath = os.environ.get("PYTHONPATH", "")
if _env_pythonpath:
    for _path in _env_pythonpath.split(os.pathsep):
        if _path and _path not in sys.path:
            sys.path.insert(0, _path)

import fastf1
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import csv
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Import incident system modules (using src prefix)
from incidents import (
    IncidentManager,
    IncidentType,
    IncidentSeverity,
    TeamStability,
    VehicleFaultResolver,
    DriverErrorProbability,
    OvertakeIncidentProbability,
    BlueFlagManager,
    BlueFlagState,
    ResistanceLevel,
    LappingDetectionConfig,
    DriverPersonality,
    VSCManager,
    VSCConfig,
    SafetyCarManager,
    SafetyCarConfig,
    SafetyResponseManager,
    SafetyCarState,
    RollingStartManager,
    RollingStartConfig,
    RedFlagManager,
    UnlappingManager,
    LappingOvertake,
    roll_d6,
    roll_d10,
    roll_d100,
    DiceRoller,
)

# Import DRS system modules
from drs.driver_state import DriverRaceState
from drs.base_config import TrackDRSConfig, DRSZone
from drs.zones import TRACKS as DRS_TRACKS

# =============================================================================
# STUB IMPLEMENTATIONS FOR MIGRATED FUNCTIONS
# These were previously in long_dist_sim_with_box.py
# =============================================================================

import csv
import json
from pathlib import Path

# Track base lap times (seconds)
TRACK_BASE_LAP_TIMES = {
    "spain": (89.0, 300),
    "monaco": (76.0, 300),
    "monza": (84.0, 300),
    "bahrain": (91.0, 300),
    "australia": (86.0, 300),
    "japan": (91.0, 300),
    "china": (87.0, 300),
    "united states": (94.0, 300),
    "mexico": (84.0, 300),
    "brazil": (74.0, 300),
    "singapore": (88.0, 300),
    "abu dhabi": (90.0, 300),
    "canada": (80.0, 300),
    "silverstone": (88.0, 300),
    "hungary": (80.0, 300),
    "belgium": (102.0, 300),
    "netherlands": (74.0, 300),
    "italy": (84.0, 300),
    "austria": (68.0, 300),
    "france": (91.0, 300),
    "azerbaijan": (88.0, 300),
}

# Default lap counts per track
DEFAULT_LAP_COUNTS = {
    "spain": 66,
    "monaco": 78,
    "monza": 53,
    "bahrain": 57,
    "australia": 58,
    "japan": 53,
    "china": 56,
    "united states": 56,
    "mexico": 71,
    "brazil": 71,
    "singapore": 61,
    "abu dhabi": 58,
    "canada": 70,
    "silverstone": 52,
    "hungary": 70,
    "belgium": 44,
    "netherlands": 72,
    "italy": 53,
    "austria": 71,
    "france": 53,
    "azerbaijan": 51,
}

# Tyre compounds for 2022 season
TYRE_COMPOUNDS_2022 = ["SOFT", "MEDIUM", "HARD"]

# Track aliases for different naming conventions
TRACK_ALIASES = {
    "united states": ["usa", "austin", "us"],
    "united kingdom": ["silverstone", "great britain", "britain"],
    "italy": ["monza"],
}


def read_driver_data(csv_file: str) -> dict:
    """Read driver data from CSV file."""
    driver_data = {}
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                driver_name = row.get("Driver", "")
                if driver_name:
                    driver_data[driver_name] = {
                        "Team": row.get("Team", ""),
                        "R_Value": float(row.get("R_Value", 300)),
                        "DR_Value": float(row.get("DR_Value", 0)),
                    }
    except FileNotFoundError:
        print(f"Warning: Driver data file not found: {csv_file}")
    return driver_data


def load_pit_stop_data() -> dict:
    """Load pit stop data from CSV."""
    pit_data = {}
    try:
        with open("docs/pit_stop_strategies_2022_2024.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                track = row.get("Track", "").lower()
                pit_data[track] = {
                    "strategy_1_stop": row.get("Strategy_1_Stop", "HARD-MEDIUM"),
                    "strategy_2_stop": row.get("Strategy_2_Stop", "HARD-MEDIUM-SOFT"),
                }
    except FileNotFoundError:
        print("Warning: Pit stop data file not found, using defaults")
    return pit_data


def load_pitlane_time_data():
    """Load pitlane time data."""
    import pandas as pd

    # Try new location in docs first, then fall back to legacy location
    for filepath in ["docs/pitlane_time.csv", "outputs/tables/pitlane_time.csv"]:
        try:
            df = pd.read_csv(filepath)
            return df
        except FileNotFoundError:
            continue
    print("Warning: pitlane_time.csv not found, using default values")
    return None


def get_track_characteristics() -> dict:
    """Get track characteristics data."""
    return {
        "spain": {"abrasion": 0.8, "grip": 0.7},
        "monaco": {"abrasion": 0.4, "grip": 0.9},
        "monza": {"abrasion": 0.5, "grip": 0.6},
    }


def assign_team_strategies(
    driver_data: dict, gp_name: str, num_laps: int, pit_data: dict
) -> tuple:
    """Assign team strategies."""
    team_strategies = {}
    driver_teams = {}
    for driver, info in driver_data.items():
        team = info.get("Team", "")
        driver_teams[driver] = team
        if team not in team_strategies:
            team_strategies[team] = {
                "strategy": 1,
                " tyre_compounds_set": ["HARD", "MEDIUM"],
            }
    return team_strategies, driver_teams


def generate_pit_laps(track_name: str, strategy: int, pit_data: dict) -> list:
    """Generate pit stop laps based on strategy."""
    track = track_name.lower()
    num_laps = DEFAULT_LAP_COUNTS.get(track, 66)
    num_stops = strategy
    if num_stops == 1:
        return [int(num_laps * 0.6)]
    elif num_stops == 2:
        return [int(num_laps * 0.35), int(num_laps * 0.7)]
    return [int(num_laps * 0.3), int(num_laps * 0.55), int(num_laps * 0.8)]


def generate_individual_tyre_sequence(compounds: list) -> list:
    """Generate individual tyre sequence."""
    return compounds if compounds else ["HARD", "MEDIUM"]


def determine_pit_strategy(track_name: str, pit_data: dict) -> int:
    """Determine pit strategy (number of stops)."""
    return 1


def roll_tyre_for_track(track_name: str) -> str:
    """Roll random tyre compound for track."""
    return "MEDIUM"


def get_available_compounds_for_track(track_name: str) -> list:
    """Get available tyre compounds for track."""
    return ["SOFT", "MEDIUM", "HARD"]


def get_race_tyre_for_track(track_name: str) -> str:
    """Get race tyre for track (typically medium or hard)."""
    return "MEDIUM"


def get_track_tyre_weights(track_name: str) -> dict:
    """Get tyre weight preferences for track."""
    return {"SOFT": 0.2, "MEDIUM": 0.5, "HARD": 0.3}


def smart_tyre_selection(track_name: str, lap_count: int) -> str:
    """Smart tyre selection based on lap count."""
    if lap_count < 20:
        return "SOFT"
    elif lap_count < 40:
        return "MEDIUM"
    return "HARD"


def ensure_f1_tyre_compliance(compound: str) -> str:
    """Ensure tyre compound is F1 compliant."""
    compound = compound.upper()
    if compound in ["SOFT", "MEDIUM", "HARD"]:
        return compound
    return "MEDIUM"


def calculate_start_lap_delta(
    grid_position: int,
    driver: str = None,
    r_value: float = None,
    track_name: str = None,
    track_chars: dict = None,
) -> tuple:
    """Calculate start lap delta based on grid position."""
    base_delta = grid_position * 0.15
    return base_delta, 0.5


def calculate_base_lap_time(r_value: float, track_name: str) -> float:
    """Calculate base lap time based on R value and track."""
    base_time = TRACK_BASE_LAP_TIMES.get(track_name.lower(), (88.0, 300))[0]
    adjustment = (r_value - 300) * 0.01
    return base_time + adjustment


def calculate_degradation_with_cliff(
    lap_number: int,
    tyre_compound: str,
    r_value: float,
    r_max: float,
    track_chars: dict,
    pit_lap_count: int,
) -> float:
    """Calculate tire degradation with cliff effect."""
    tyre_params = get_universal_tyre_params_with_cliff()
    compound_params = tyre_params.get(tyre_compound, tyre_params["MEDIUM"])

    # Non-linear scaling
    scaled_lap = nonlinear_scaling(r_value, compound_params["base_lap"], r_max)

    # Track characteristics compensation
    abrasion = track_chars.get("abrasion", 5) if isinstance(track_chars, dict) else 5
    wear_factor = calculate_wear_compensation(abrasion)

    # Base degradation rate
    base_degradation = compound_params["base_degradation"] * wear_factor

    # Cliff effect
    cliff_lap = compound_params["cliff_lap"]
    cliff_severity = compound_params["cliff_severity"]

    if lap_number > cliff_lap:
        cliff_factor = 1 + cliff_severity * ((lap_number - cliff_lap) / cliff_lap)
    else:
        cliff_factor = 1.0

    # Calculate cumulative degradation
    degradation = base_degradation * (lap_number / scaled_lap) * cliff_factor

    return degradation


def calculate_dr_based_std(
    dr_value: float, dr_min: float, dr_max: float, base_std: float = 0.45
) -> float:
    """Calculate DR-based standard deviation."""
    if dr_max == dr_min:
        return base_std
    dr_normalized = (dr_value - dr_min) / (dr_max - dr_min)
    return base_std * (1.0 - dr_normalized * 0.3)


def nonlinear_scaling(r_value: float, base_lap: float, r_max: float) -> float:
    """Non-linear scaling function."""
    return base_lap * (
        1 + 0.65 * (1 - r_value / r_max) * np.exp(-2.5 * (1 - r_value / r_max))
    )


def calculate_wear_compensation(abrasion_level: float) -> float:
    """Calculate compensation factor based on track wear level."""
    normalized_abrasion = (abrasion_level - 3) / 2.0
    wear_factor = 1 + 0.2 * normalized_abrasion
    return wear_factor


def roll_pit_stop_time() -> float:
    """Roll random pit stop time."""
    return 22.0


def build_arg_parser():
    """Build argument parser for CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced F1 Race Simulation")
    parser.add_argument("--gp-name", type=str, default="Spain", help="Grand Prix name")
    parser.add_argument("--year", type=int, default=2022, help="Season year")
    parser.add_argument("--laps", type=int, default=None, help="Number of laps")
    return parser


def generate_team_tyre_compounds(track_name: str, strategy: int) -> list:
    """Generate tyre compounds for a team's strategy."""
    if strategy == 1:
        return ["HARD", "MEDIUM"]
    elif strategy == 2:
        return ["HARD", "MEDIUM", "SOFT"]
    return ["HARD", "MEDIUM", "HARD"]


def get_universal_tyre_params_with_cliff():
    """Get tire parameters based on Pirelli technical documentation."""
    return {
        "C1": {
            "base_lap": 30,
            "base_degradation": 0.025,
            "cliff_lap": 28,
            "cliff_severity": 0.15,
        },
        "C2": {
            "base_lap": 25,
            "base_degradation": 0.030,
            "cliff_lap": 23,
            "cliff_severity": 0.12,
        },
        "C3": {
            "base_lap": 20,
            "base_degradation": 0.035,
            "cliff_lap": 18,
            "cliff_severity": 0.10,
        },
        "C4": {
            "base_lap": 15,
            "base_degradation": 0.045,
            "cliff_lap": 13,
            "cliff_severity": 0.08,
        },
        "C5": {
            "base_lap": 12,
            "base_degradation": 0.060,
            "cliff_lap": 10,
            "cliff_severity": 0.06,
        },
        # Also support compound names
        "SOFT": {
            "base_lap": 15,
            "base_degradation": 0.045,
            "cliff_lap": 13,
            "cliff_severity": 0.08,
        },
        "MEDIUM": {
            "base_lap": 20,
            "base_degradation": 0.035,
            "cliff_lap": 18,
            "cliff_severity": 0.10,
        },
        "HARD": {
            "base_lap": 25,
            "base_degradation": 0.030,
            "cliff_lap": 23,
            "cliff_severity": 0.12,
        },
    }


def get_track_base_lap(track_name: str) -> float:
    """Get base lap time for a track."""
    return TRACK_BASE_LAP_TIMES.get(track_name.lower(), (88.0, 300))[0]


def simulate_race_with_pit_stops(
    track_name: str,
    year: int,
    num_laps: int,
    driver_data: dict,
    pit_data: dict,
    team_strategies: dict = None,
    random_seed: int = None,
) -> dict:
    """
    Simulate a race with pit stops - wrapper for EnhancedRaceSimulator.

    This is a compatibility function that wraps the enhanced RaceSimulator.
    """
    if random_seed is not None:
        import random

        random.seed(random_seed)

    # Create simulator
    sim = EnhancedRaceSimulator(
        track_name=track_name,
        year=year,
        num_laps=num_laps,
        driver_data=driver_data,
    )

    # Run simulation
    results = sim.run()

    return results


# =============================================================================
# OUTPUT DIRECTORY SETUP
# =============================================================================

OUTPUT_BASE_DIR = os.path.join("outputs", "enhanced_sim")

# =============================================================================
# ANDRETTI TEAM CONFIGURATION
# =============================================================================
# Andretti team participates in these Grand Prix (22 drivers total):
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


def filter_andretti_drivers(
    driver_data: Dict[str, Dict], gp_name: str
) -> Dict[str, Dict]:
    """
    Filter out Andretti drivers if they don't participate in this GP.

    Returns a new driver_data dict with Andretti drivers removed if not attending.
    """
    if is_andretti_participating(gp_name):
        # Andretti participates - return all drivers
        return driver_data

    # Filter out Andretti drivers
    filtered_data = {}
    for driver_name, driver_info in driver_data.items():
        team = driver_info.get("Team", "")
        if team != "Andretti":
            filtered_data[driver_name] = driver_info

    return filtered_data


def get_race_output_dir(track_name: str, runtime_datetime: datetime) -> str:
    """
    Get output directory for a specific race run.

    Folder structure: {location}_{runtime_datetime}
    Example: Monaco_2024-02-23_19-53-14

    The folder will contain:
    - race_results_{track}.csv
    - dice_rolls_{track}.csv
    - race_report_{track}.md
    """
    # Format datetime for folder name: YYYY-MM-DD_HH-MM-SS
    datetime_str = runtime_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{track_name}_{datetime_str}"
    race_output_dir = os.path.join(OUTPUT_BASE_DIR, folder_name)
    os.makedirs(race_output_dir, exist_ok=True)
    return race_output_dir


def save_dice_rolls(
    dice_logger: "DiceRollingLogger",
    track_name: str,
    output_dir: str,
):
    """Save dice rolls to CSV in the specified output directory."""
    if not dice_logger.rolls:
        return

    filename = f"dice_rolls_{track_name.lower()}.csv"
    filepath = os.path.join(output_dir, filename)

    df = pd.DataFrame(dice_logger.rolls)
    df.to_csv(filepath, index=False)
    print(f"Dice rolling results saved to: {filepath}")


# Ensure cache directory exists before enabling FastF1 cache
os.makedirs("outputs/f1_cache", exist_ok=True)
fastf1.Cache.enable_cache("outputs/f1_cache")
fastf1.set_log_level("ERROR")


# =============================================================================
# DICE ROLLING LOGGER
# =============================================================================


class DiceRollingLogger:
    """Records all dice rolling results to CSV files."""

    def __init__(self, track_name: str):
        self.track_name = track_name
        self.rolls: List[Dict[str, Any]] = []

    def log_roll(
        self,
        lap: int,
        driver: str,
        incident_type: str,
        dice_type: str,
        dice_result: int,
        outcome: str,
        race_time: float = 0.0,
        details: Optional[Dict] = None,
    ):
        """Log a dice roll result."""
        roll_record = {
            "timestamp": f"{race_time:.3f}s",
            "lap": lap,
            "driver": driver,
            "incident_type": incident_type,
            "dice_type": dice_type,
            "dice_result": dice_result,
            "outcome": outcome,
        }
        if details:
            for key, value in details.items():
                roll_record[key] = str(value)
        self.rolls.append(roll_record)

    def save_to_csv(self, output_dir: Optional[str] = None):
        """Save all dice rolls to CSV file."""
        if not self.rolls:
            return

        if output_dir is None:
            output_dir = OUTPUT_BASE_DIR

        filename = f"dice_rolls_{self.track_name.lower()}.csv"
        filepath = os.path.join(output_dir, filename)

        df = pd.DataFrame(self.rolls)
        df.to_csv(filepath, index=False)
        print(f"Dice rolling results saved to: {filepath}")

    def get_summary(self) -> Dict[str, int]:
        """Get summary of dice roll outcomes."""
        summary = defaultdict(int)
        for roll in self.rolls:
            summary[roll["incident_type"]] += 1
        return dict(summary)


# =============================================================================
# VEHICLE FAULT SYSTEM - MODERN F1 REALISM
# =============================================================================
# Modern F1 cars have very low mechanical failure rates (~0.1-0.5% per lap)
# Faults now cause SPEED DEGRADATION instead of DNF:
# - Minor fault: 0.1-0.5% speed reduction
# - Moderate fault: 0.5-1.5% speed reduction
# - Major fault: 1.5-3% speed reduction
# - Catastrophic: 3-5% speed reduction (but still finish)
# Faults accumulate over the race


def get_fault_probability_per_lap(team_stability: TeamStability) -> float:
    """
    Get the per-lap fault probability based on team stability.

    Modern F1: Top teams ~0.1%, Mid-tier ~0.3%, Backmarker ~0.5%
    This replaces the old ~10% per lap probability.
    """
    # Base fault probability by stability tier
    if team_stability.base_stability >= 97.5:
        # Top teams (Red Bull, Ferrari, Mercedes, McLaren)
        return 0.001  # 0.1% per lap
    elif team_stability.base_stability >= 95.0:
        # Mid-tier teams (Aston Martin, Alpine, Williams)
        return 0.003  # 0.3% per lap
    else:
        # Backmarker teams (Alfa Romeo, Haas, AlphaTauri)
        return 0.005  # 0.5% per lap


def get_speed_degradation_from_fault(severity: str) -> float:
    """
    Get speed degradation percentage based on fault severity.
    Values are multipliers applied to lap time (higher = slower).
    Note: catastrophic and terminal severity cause DNF, not degradation.
    """
    degradation_map = {
        "minor": random.uniform(0.001, 0.005),  # 0.1-0.5%
        "moderate": random.uniform(0.005, 0.015),  # 0.5-1.5%
        "major": random.uniform(0.015, 0.03),  # 1.5-3%
        "catastrophic": random.uniform(0.03, 0.05),  # 3-5% (causes DNF)
        "terminal": 0.0,  # Certain DNF, no degradation
    }
    return degradation_map.get(severity, 0.001)


# Track if this is Monaco (for special handling)
MONACO_TRACK_NAMES = ["monaco", "monaco_2024", "monaco_gp"]


def is_monaco_track(track_name: str) -> bool:
    """Check if the track is Monaco."""
    return track_name.lower() in MONACO_TRACK_NAMES


def get_monaco_overtake_probability() -> float:
    """
    Monaco has almost no overtakes - reduce probability to near zero.
    Real Monaco: ~1-3 overtakes per race typically.
    """
    return 0.01  # 1% of normal overtake probability


def get_monaco_pit_stop_penalty(extra_stops: int) -> float:
    """
    Calculate pit stop penalty for Monaco.
    Each pit stop beyond 1 adds a time penalty.
    This is NOT a penalty - it's a strategic disadvantage.
    Real F1: 1-stop is optimal, extra stops hurt significantly.
    """
    return extra_stops * 5.0  # +5 seconds per extra stop


def get_team_stabilities() -> Dict[str, TeamStability]:
    """Get team stability configurations."""
    return {
        "Red Bull Racing": TeamStability(
            team_name="Red Bull Racing",
            base_stability=98.0,
            engine_reliability=9,
            hybrid_reliability=9,
            battery_reliability=8,
            chassis_reliability=9,
            suspension_reliability=9,
            tyre_reliability=9,
            brake_reliability=9,
            aero_reliability=9,
        ),
        "Ferrari": TeamStability(
            team_name="Ferrari",
            base_stability=96.5,
            engine_reliability=8,
            hybrid_reliability=8,
            battery_reliability=8,
            chassis_reliability=8,
            suspension_reliability=8,
            tyre_reliability=8,
            brake_reliability=8,
            aero_reliability=8,
        ),
        "Mercedes": TeamStability(
            team_name="Mercedes",
            base_stability=97.0,
            engine_reliability=8,
            hybrid_reliability=9,
            battery_reliability=8,
            chassis_reliability=8,
            suspension_reliability=8,
            tyre_reliability=8,
            brake_reliability=8,
            aero_reliability=8,
        ),
        "McLaren": TeamStability(
            team_name="McLaren",
            base_stability=95.5,
            engine_reliability=7,
            hybrid_reliability=8,
            battery_reliability=7,
            chassis_reliability=8,
            suspension_reliability=8,
            tyre_reliability=8,
            brake_reliability=8,
            aero_reliability=8,
        ),
        "Aston Martin": TeamStability(
            team_name="Aston Martin",
            base_stability=95.0,
            engine_reliability=7,
            hybrid_reliability=7,
            battery_reliability=7,
            chassis_reliability=7,
            suspension_reliability=7,
            tyre_reliability=8,
            brake_reliability=7,
            aero_reliability=8,
        ),
        "Alpine": TeamStability(
            team_name="Alpine",
            base_stability=94.5,
            engine_reliability=7,
            hybrid_reliability=7,
            battery_reliability=6,
            chassis_reliability=7,
            suspension_reliability=7,
            tyre_reliability=7,
            brake_reliability=7,
            aero_reliability=7,
        ),
        "Williams": TeamStability(
            team_name="Williams",
            base_stability=94.0,
            engine_reliability=7,
            hybrid_reliability=7,
            battery_reliability=6,
            chassis_reliability=7,
            suspension_reliability=7,
            tyre_reliability=7,
            brake_reliability=7,
            aero_reliability=7,
        ),
        "AlphaTauri": TeamStability(
            team_name="AlphaTauri",
            base_stability=93.5,
            engine_reliability=7,
            hybrid_reliability=7,
            battery_reliability=6,
            chassis_reliability=6,
            suspension_reliability=6,
            tyre_reliability=7,
            brake_reliability=7,
            aero_reliability=6,
        ),
        "Alfa Romeo": TeamStability(
            team_name="Alfa Romeo",
            base_stability=93.0,
            engine_reliability=6,
            hybrid_reliability=6,
            battery_reliability=6,
            chassis_reliability=6,
            suspension_reliability=6,
            tyre_reliability=7,
            brake_reliability=6,
            aero_reliability=6,
        ),
        "Haas": TeamStability(
            team_name="Haas",
            base_stability=92.5,
            engine_reliability=6,
            hybrid_reliability=6,
            battery_reliability=5,
            chassis_reliability=6,
            suspension_reliability=6,
            tyre_reliability=6,
            brake_reliability=6,
            aero_reliability=6,
        ),
    }


# =============================================================================
# DRIVER PERSONALITY MODEL
# =============================================================================


def get_driver_personalities() -> Dict[str, Dict]:
    """
    Get driver personality parameters based on professional F1 analysis.

    Attributes:
    - aggression: 1-10, higher = more aggressive racing style
    - consistency: 1-10, higher = more consistent performance
    - battle_escalation: 1-10, higher = more likely to escalate wheel-to-wheel battles
    - error_in_clean_air: 1-10, lower = less error in clean air (1=best, 10=worst)
    """
    return {
        # Max Verstappen: High aggression, High consistency, High battle escalation, Low error in clean air
        "Max Verstappen": {
            "aggression": 9,
            "consistency": 9,
            "battle_escalation": 8,
            "error_in_clean_air": 2,
        },
        "VERSTAPPEN": {
            "aggression": 9,
            "consistency": 9,
            "battle_escalation": 8,
            "error_in_clean_air": 2,
        },
        # Lewis Hamilton: Medium aggression, High consistency, Medium battle escalation, Low error in clean air
        "Lewis Hamilton": {
            "aggression": 6,
            "consistency": 8,
            "battle_escalation": 5,
            "error_in_clean_air": 3,
        },
        "HAMILTON": {
            "aggression": 6,
            "consistency": 8,
            "battle_escalation": 5,
            "error_in_clean_air": 3,
        },
        # Charles Leclerc: Medium aggression, Medium consistency, High battle escalation, Medium error in clean air
        "Charles Leclerc": {
            "aggression": 7,
            "consistency": 6,
            "battle_escalation": 7,
            "error_in_clean_air": 5,
        },
        "LECLERC": {
            "aggression": 7,
            "consistency": 6,
            "battle_escalation": 7,
            "error_in_clean_air": 5,
        },
        # Lando Norris: Medium aggression, High consistency, Medium battle escalation, Low error in clean air
        "Lando Norris": {
            "aggression": 6,
            "consistency": 7,
            "battle_escalation": 5,
            "error_in_clean_air": 4,
        },
        "NORRIS": {
            "aggression": 6,
            "consistency": 7,
            "battle_escalation": 5,
            "error_in_clean_air": 4,
        },
        # Oscar Piastri: Medium aggression, High consistency, Low battle escalation, Low error in clean air
        "Oscar Piastri": {
            "aggression": 5,
            "consistency": 7,
            "battle_escalation": 4,
            "error_in_clean_air": 4,
        },
        "PIASTRI": {
            "aggression": 5,
            "consistency": 7,
            "battle_escalation": 4,
            "error_in_clean_air": 4,
        },
        # George Russell: Medium aggression, High consistency, High battle escalation, Medium error in clean air
        "George Russell": {
            "aggression": 6,
            "consistency": 7,
            "battle_escalation": 6,
            "error_in_clean_air": 5,
        },
        "RUSSELL": {
            "aggression": 6,
            "consistency": 7,
            "battle_escalation": 6,
            "error_in_clean_air": 5,
        },
        # Sergio Perez: Medium aggression, Medium consistency, Medium battle escalation, Medium error in clean air
        "Sergio Perez": {
            "aggression": 6,
            "consistency": 5,
            "battle_escalation": 6,
            "error_in_clean_air": 6,
        },
        "PEREZ": {
            "aggression": 6,
            "consistency": 5,
            "battle_escalation": 6,
            "error_in_clean_air": 6,
        },
        # Carlos Sainz: Medium aggression, High consistency, Medium battle escalation, Low error in clean air
        "Carlos Sainz": {
            "aggression": 5,
            "consistency": 7,
            "battle_escalation": 4,
            "error_in_clean_air": 4,
        },
        "SAINZ": {
            "aggression": 5,
            "consistency": 7,
            "battle_escalation": 4,
            "error_in_clean_air": 4,
        },
        # Fernando Alonso: High aggression, High consistency, Medium battle escalation, Low error in clean air
        "Fernando Alonso": {
            "aggression": 7,
            "consistency": 8,
            "battle_escalation": 5,
            "error_in_clean_air": 3,
        },
        "ALONSO": {
            "aggression": 7,
            "consistency": 8,
            "battle_escalation": 5,
            "error_in_clean_air": 3,
        },
    }


def get_driver_personality(driver_name: str) -> Dict:
    """Get personality for a driver, with default values for unknown drivers."""
    personalities = get_driver_personalities()

    # Try exact match first
    if driver_name in personalities:
        return personalities[driver_name]

    # Try to match by first name or last name
    driver_first_name = driver_name.split()[0] if driver_name else ""
    for known_name, personality in personalities.items():
        if driver_first_name == known_name.split()[0]:
            return personality

    # Default personality for unknown drivers (medium values)
    return {
        "aggression": 5,
        "consistency": 5,
        "battle_escalation": 5,
        "error_in_clean_air": 5,
    }


def calculate_driver_error_probability(
    driver_name: str,
    position: int,
    is_fighting: bool = False,
    is_leading: bool = False,
) -> float:
    """
    Calculate driver error probability based on personality and position.

    The error probability considers:
    1. Base error rate (from clean air performance)
    2. Aggression multiplier (higher when fighting)
    3. Battle escalation (increases errors in wheel-to-wheel)
    4. Position pressure (leading vs chasing vs midpack)
    """
    personality = get_driver_personality(driver_name)

    # Base error rate: 10 - error_in_clean_air (so higher error_in_clean_air = more errors)
    base_error_rate = personality["error_in_clean_air"]

    # Convert to probability (0-20% range)
    error_prob = base_error_rate * 2.0  # 2-20% range

    # Aggression multiplier when fighting
    if is_fighting:
        aggression = personality["aggression"]
        error_prob += (aggression - 5) * 0.5  # +/- 2% based on aggression

    # Battle escalation factor
    if is_fighting:
        battle_escalation = personality["battle_escalation"]
        error_prob += (
            battle_escalation - 5
        ) * 0.3  # +/- 1.5% based on battle escalation

    # Position pressure: leaders have less pressure, chasers have more
    if is_leading:
        error_prob -= 1.0  # Less pressure when leading
    elif position <= 3:  # Fighting for podium
        error_prob += 0.5  # More pressure
    elif position >= 15:  # Back of grid
        error_prob += 0.5  # May take more risks

    # Clamp to reasonable range
    return max(1.0, min(25.0, error_prob))


# =============================================================================
# RACE STATE MANAGEMENT
# =============================================================================


class RaceState:
    """Manages the overall race state including safety cars, incidents, etc."""

    def __init__(
        self,
        num_laps: int,
        drivers: Dict[str, Dict],
        dice_logger: DiceRollingLogger,
    ):
        self.num_laps = num_laps
        self.current_lap = 1
        self.drivers = drivers  # driver_name -> driver_info
        self.dice_logger = dice_logger

        # Position tracking
        self.positions: Dict[str, int] = {}  # driver_name -> position
        self.lap_times: Dict[str, List[float]] = {}  # driver_name -> [lap_times]
        self.cumulative_times: Dict[str, float] = {}  # driver_name -> cumulative_time

        # Race control states
        self.vsc_active = False
        self.sc_active = False
        self.red_flag_active = False
        self.vsc_laps_remaining = 0
        self.sc_laps_remaining = 0

        # Incident tracking
        self.active_incidents: List[Dict] = []
        self.penalties: Dict[str, List[Dict]] = defaultdict(list)

        # Blue flag states
        self.blue_flag_states: Dict[str, BlueFlagState] = {}

        # Lapped cars tracking
        self.lapped_cars: Dict[str, int] = {}  # driver_name -> num_laps_ahead
        self.lead_lap = set()  # Drivers on the lead lap

        # FAULT DEGRADATION TRACKING - MODERN F1
        # Faults accumulate and degrade speed over the race
        self.driver_fault_degradation: Dict[str, float] = defaultdict(float)

        # DNF (Did Not Finish) TRACKING
        # Tracks drivers who retired from the race
        # driver_name -> lap_dnfed
        self.dnf_drivers: Dict[str, int] = {}
        # driver_name -> retirement_reason
        self.retirement_reasons: Dict[str, str] = {}

    def update_positions(self, driver_times: Dict[str, float]):
        """Update driver positions based on cumulative times."""
        sorted_drivers = sorted(driver_times.items(), key=lambda x: x[1])
        for position, (driver, _) in enumerate(sorted_drivers, 1):
            self.positions[driver] = position

    def get_position(self, driver: str) -> int:
        """Get driver's current position."""
        return self.positions.get(driver, len(self.drivers))

    def is_lead_lap(self, driver: str) -> bool:
        """Check if driver is on the lead lap."""
        return driver in self.lead_lap

    def add_lap_time(self, driver: str, lap_time: float):
        """Add lap time for a driver."""
        if driver not in self.lap_times:
            self.lap_times[driver] = []
        self.lap_times[driver].append(lap_time)

        if driver not in self.cumulative_times:
            self.cumulative_times[driver] = 0.0
        self.cumulative_times[driver] += lap_time

    def is_dnf(self, driver: str) -> bool:
        """Check if driver has DNFed (Did Not Finish)."""
        return driver in self.dnf_drivers

    def add_dnf(self, driver: str, lap: int, reason: str):
        """Mark a driver as DNFed (Did Not Finish)."""
        if driver not in self.dnf_drivers:
            self.dnf_drivers[driver] = lap
            self.retirement_reasons[driver] = reason
            print(f"\n*** DNF: {driver} retired on lap {lap} - {reason} ***")

    def get_dnf_info(self, driver: str) -> Optional[Tuple[int, str]]:
        """Get DNF info for a driver (lap, reason) or None if not DNFed."""
        if driver in self.dnf_drivers:
            return (self.dnf_drivers[driver], self.retirement_reasons[driver])
        return None


# =============================================================================
# ENHANCED RACE SIMULATOR
# =============================================================================


class EnhancedRaceSimulator:
    """
    Enhanced race simulator with full incident and DRS integration.
    """

    def __init__(
        self,
        track_name: str,
        num_laps: int,
        driver_data: Dict[str, Dict],
        team_stabilities: Dict[str, TeamStability],
        driver_teams: Dict[str, str],
        pit_data: pd.DataFrame,
        track_chars: Dict,
        dice_logger: DiceRollingLogger,
        random_seed: Optional[int] = None,
    ):
        self.track_name = track_name
        self.num_laps = num_laps
        self.driver_data = driver_data
        self.team_stabilities = team_stabilities
        self.driver_teams = driver_teams
        self.pit_data = pit_data
        self.track_chars = track_chars
        self.dice_logger = dice_logger

        # Set random seed if specified
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        # Get base lap time for this track
        self.base_lap_time = TRACK_BASE_LAP_TIMES.get(track_name, (88.0, 300))[0]

        # Initialize race state
        self.race_state = RaceState(num_laps, driver_data, dice_logger)

        # Initialize incident manager
        self.incident_manager = IncidentManager(
            team_stabilities=team_stabilities,
        )

        # Initialize VSC and Safety Car managers (need base_lap_time)
        self.vsc_manager = VSCManager(self.base_lap_time, VSCConfig())
        self.sc_manager = SafetyCarManager(self.base_lap_time, SafetyCarConfig())
        self.safety_response = SafetyResponseManager(
            self.base_lap_time, VSCConfig(), SafetyCarConfig()
        )

        # Initialize rolling start manager
        self.rolling_start_manager = RollingStartManager(
            total_race_laps=num_laps, config=RollingStartConfig()
        )

        # Initialize blue flag manager
        self.blue_flag_manager = BlueFlagManager(config=LappingDetectionConfig())

        # Initialize unlapping manager
        self.unlapping_manager = UnlappingManager()

        # Initialize DRS config if available
        self.drs_config = self._get_drs_config(track_name)

        # Pit stop data
        self.pitlane_data = load_pitlane_time_data()

        # Track simulation start time for relative timestamps
        self.simulation_start_time: Optional[datetime] = None

        # Vehicle fault check scheduling - dice roll determines next check lap
        # Initial check at lap 3, then dice determines next check interval
        self._next_vehicle_fault_check_lap: int = 3

    def _get_drs_config(self, track_name: str) -> Optional[TrackDRSConfig]:
        """Get DRS configuration for the track."""
        # Try to get track config from DRS zones
        track_getter = DRS_TRACKS.get(track_name)
        if track_getter:
            return track_getter()
        return None

    def get_relative_time(self) -> float:
        """Get estimated race time in seconds (time into the race)."""
        # Use cumulative race time if available, otherwise estimate
        if (
            self.race_state.cumulative_times
            and len(self.race_state.cumulative_times) > 0
        ):
            # Get the minimum cumulative time (leader)
            leader_time = min(self.race_state.cumulative_times.values())
            if leader_time > 0:
                return leader_time
        # Estimate based on current lap and base lap time
        # This is used at race start before cumulative times are populated
        current_lap = self.race_state.current_lap
        if current_lap > 0:
            # Estimate: (current_lap - 1) * base_lap_time
            # This gives approximate time at start of current lap
            return (current_lap - 1) * self.base_lap_time
        return 0.0

    def simulate_start(self, grid_positions: Dict[str, int]) -> Dict[str, float]:
        """
        Simulate race start (standing start - F1 standard for clear weather).

        Standing start procedure:
        1. Formation lap completed before grid formation
        2. Drivers in starting positions on grid
        3. 5-second countdown with board signals
        4. All lights go out simultaneously - drivers can go
        5. Reaction time roll determines launch quality
        6. Position changes possible on the run to turn 1
        """
        print("\n=== Simulating Race Start (Standing Start) ===")

        start_deltas = {}

        for driver, grid_pos in grid_positions.items():
            driver_info = self.driver_data[driver]
            personality = get_driver_personality(driver)

            # Get reaction time based on driver personality
            # More aggressive drivers tend to have slightly faster reactions but more variance
            aggression = personality["aggression"]
            consistency = personality["consistency"]

            # Roll for reaction time (d10):
            # 1 = Extremely slow (>0.5s) - possible jump start risk
            # 2-3 = Slow (0.3-0.5s)
            # 4-7 = Average (0.2-0.3s)
            # 8-9 = Good (0.15-0.2s)
            # 10 = Excellent (<0.15s)
            reaction_roll = roll_d10()

            # Calculate reaction time delta based on roll
            reaction_time = 0.0
            if reaction_roll == 1:
                reaction_time = random.uniform(0.4, 0.6)
                start_outcome = "extremely_slow"
            elif reaction_roll <= 3:
                reaction_time = random.uniform(0.25, 0.4)
                start_outcome = "slow"
            elif reaction_roll <= 7:
                reaction_time = random.uniform(0.15, 0.25)
                start_outcome = "average"
            elif reaction_roll <= 9:
                reaction_time = random.uniform(0.1, 0.15)
                start_outcome = "good"
            else:  # 10
                reaction_time = random.uniform(0.05, 0.1)
                start_outcome = "excellent"

            # Consistency affects variance - more consistent = less variance
            variance_factor = 1.0 - (consistency * 0.05)  # 0.5 to 0.95
            reaction_time *= variance_factor

            # Calculate base start delta from grid position
            # Pole position starts at 0, others have natural spacing
            base_delta, _ = calculate_start_lap_delta(
                grid_pos,
                driver,
                driver_info["R_Value"],
                self.track_name,
                self.track_chars,
            )

            # Apply reaction time to delta (positive = slower)
            start_delta = base_delta + reaction_time

            # Roll for launch incident (poor launch or wheelspin)
            launch_roll = roll_d10()

            # Check for poor start (wheelspin or mistakes)
            if launch_roll == 1:  # Major mistake - significant time loss
                start_delta += random.uniform(1.5, 3.0)
                start_outcome = "major_mistake"
                self.dice_logger.log_roll(
                    lap=0,
                    driver=driver,
                    incident_type="standing_start",
                    dice_type="d10",
                    dice_result=launch_roll,
                    outcome="major_mistake",
                    race_time=self.get_relative_time(),
                    details={
                        "grid_position": grid_pos,
                        "reaction_roll": reaction_roll,
                        "reaction_time": reaction_time,
                    },
                )
            elif launch_roll == 2:  # Minor wheelspin
                start_delta += random.uniform(0.5, 1.5)
                start_outcome = "wheelspin"
                self.dice_logger.log_roll(
                    lap=0,
                    driver=driver,
                    incident_type="standing_start",
                    dice_type="d10",
                    dice_result=launch_roll,
                    outcome="wheelspin",
                    race_time=self.get_relative_time(),
                    details={
                        "grid_position": grid_pos,
                        "reaction_roll": reaction_roll,
                    },
                )
            elif launch_roll >= 9:  # Excellent launch - gaining positions
                start_delta -= random.uniform(0.3, 0.8)
                start_outcome = "excellent_launch"
                self.dice_logger.log_roll(
                    lap=0,
                    driver=driver,
                    incident_type="standing_start",
                    dice_type="d10",
                    dice_result=launch_roll,
                    outcome="excellent_launch",
                    race_time=self.get_relative_time(),
                    details={
                        "grid_position": grid_pos,
                        "reaction_roll": reaction_roll,
                    },
                )
            else:
                # Normal start - log reaction time
                self.dice_logger.log_roll(
                    lap=0,
                    driver=driver,
                    incident_type="standing_start",
                    dice_type="d10",
                    dice_result=reaction_roll,
                    outcome=start_outcome,
                    race_time=self.get_relative_time(),
                    details={
                        "grid_position": grid_pos,
                        "reaction_time": round(reaction_time, 3),
                    },
                )

            # Grid position affects starting delta - back of grid starts faster
            # This simulates the fact that front runners have more to lose
            if grid_pos > 10:
                # Back of grid gets slight boost (towing effect on formation lap)
                start_delta -= 0.2
            elif grid_pos <= 3:
                # Front row has more pressure
                start_delta += (grid_pos - 1) * 0.1

            start_deltas[driver] = start_delta

        return start_deltas

    def check_for_incidents(self, lap: int, drivers: List[str]) -> List[Dict]:
        """Check for race incidents at the start of a lap."""
        incidents = []

        for driver in drivers:
            # Skip DNFed drivers - they no longer participate in the race
            if self.race_state.is_dnf(driver):
                continue

            team = self.driver_teams.get(driver, "Unknown")
            team_stability = self.team_stabilities.get(team)

            # Get driver position for personality-based error calculation
            driver_position = (
                self.race_state.get_position(driver)
                if hasattr(self.race_state, "positions")
                else 20
            )
            is_fighting = driver_position <= 5  # Top 5 are fighting
            is_leading = driver_position == 1

            # Roll for vehicle fault (MODERN F1 - LOW PROBABILITY)
            # Using dice system to control check frequency
            if team_stability and lap == self._next_vehicle_fault_check_lap:
                fault_prob = get_fault_probability_per_lap(team_stability)
                fault_roll = random.random()  # 0-1 float

                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type="vehicle_fault_check",
                    dice_type="probability",
                    dice_result=int(fault_roll * 1000),
                    outcome="fault_occurred" if fault_roll < fault_prob else "no_fault",
                    race_time=self.get_relative_time(),
                    details={
                        "team": team,
                        "stability": team_stability.base_stability,
                        "fault_prob": fault_prob,
                    },
                )

                if fault_roll < fault_prob:
                    # Fault occurred - determine severity
                    severity_roll = roll_d100()
                    if severity_roll <= 50:
                        severity = "minor"
                    elif severity_roll <= 80:
                        severity = "moderate"
                    elif severity_roll <= 95:
                        severity = "major"
                    elif severity_roll <= 99:
                        severity = "catastrophic"  # ~4% of faults = DNF
                    else:
                        severity = "terminal"  # ~1% of faults = certain DNF

                    # Check if this is a DNF-causing fault (catastrophic or terminal)
                    if severity in ("catastrophic", "terminal"):
                        # Catastrophic/terminal fault causes retirement
                        reason = f"Catastrophic {severity} fault - mechanical failure"
                        self.race_state.add_dnf(driver, lap, reason)
                        # Log the DNF event
                        self.dice_logger.log_roll(
                            lap=lap,
                            driver=driver,
                            incident_type="vehicle_fault_dnf",
                            dice_type="d100",
                            dice_result=severity_roll,
                            outcome="dnf",
                            race_time=self.get_relative_time(),
                            details={
                                "team": team,
                                "severity": severity,
                                "reason": reason,
                            },
                        )
                        continue  # Skip adding the fault as an incident since driver DNFed

                    # Get speed degradation (not time loss)
                    speed_degradation = get_speed_degradation_from_fault(severity)

                    incidents.append(
                        {
                            "type": "vehicle_fault",
                            "driver": driver,
                            "lap": lap,
                            "severity": severity,
                            "speed_degradation": speed_degradation,  # Percentage multiplier
                            "time_loss": 0.0,  # No immediate time loss
                        }
                    )

                    # After a fault, schedule next check sooner (more likely to have issues)
                    # Use d6: 1-3 laps
                    next_check = roll_d6()
                    self._next_vehicle_fault_check_lap = lap + next_check

            # Schedule next vehicle fault check using dice if we've reached the check lap
            # and no fault occurred this lap
            if lap == self._next_vehicle_fault_check_lap:
                # Use d10 to determine next check interval (1-10 laps)
                next_check_interval = roll_d10()
                self._next_vehicle_fault_check_lap = lap + next_check_interval

            # Roll for driver error using personality-based probability
            error_roll = roll_d100()
            error_threshold = calculate_driver_error_probability(
                driver,
                position=driver_position,
                is_fighting=is_fighting,
                is_leading=is_leading,
            )

            self.dice_logger.log_roll(
                lap=lap,
                driver=driver,
                incident_type="driver_error_check",
                dice_type="d100",
                dice_result=error_roll,
                outcome="no_error"
                if error_roll > error_threshold
                else "error_occurred",
                race_time=self.get_relative_time(),
                details={
                    "position": driver_position,
                    "error_threshold": round(error_threshold, 2),
                },
            )

            if error_roll <= error_threshold:
                error_type_roll = roll_d6()
                incidents.append(
                    {
                        "type": "driver_error",
                        "driver": driver,
                        "lap": lap,
                        "error_type": "locking_brakes"
                        if error_type_roll <= 2
                        else "off_track"
                        if error_type_roll <= 4
                        else "mistake",
                        "time_loss": random.uniform(0.5, 3.0),
                    }
                )

        return incidents

    def check_for_overtake_incident(
        self, lap: int, driver_a: str, driver_b: str, position_a: int, position_b: int
    ) -> Optional[Dict]:
        """Check for overtake incident between two drivers."""
        # Determine if this is a legitimate overtake attempt
        overtake_roll = roll_d10()

        self.dice_logger.log_roll(
            lap=lap,
            driver=f"{driver_a}_vs_{driver_b}",
            incident_type="overtake_attempt",
            dice_type="d10",
            dice_result=overtake_roll,
            outcome="clean_overtake" if overtake_roll <= 6 else "incident",
            race_time=self.get_relative_time(),
            details={
                "attacker": driver_a,
                "defender": driver_b,
                "position_a": position_a,
                "position_b": position_b,
            },
        )

        if overtake_roll >= 9:  # Collision
            collision_roll = roll_d6()
            severity = (
                "minor"
                if collision_roll <= 2
                else "moderate"
                if collision_roll <= 4
                else "major"
            )

            time_loss = (
                5.0 if severity == "minor" else 15.0 if severity == "moderate" else 30.0
            )

            # Check for major accident causing DNF
            # ~0.1% per overtake attempt (requirement)
            # Major ~0.1 accident from overtake:% per overtake attempt
            is_dnf = False
            if severity == "major":
                dnf_roll = random.random()  # 0-1
                if dnf_roll < 0.001:  # 0.1% chance
                    is_dnf = True

            return {
                "type": "overtake_collision",
                "lap": lap,
                "driver_a": driver_a,
                "driver_b": driver_b,
                "severity": severity,
                "time_loss": time_loss,
                "is_dnf": is_dnf,  # Flag for major accident DNF
            }

        # Check for driver error on failed overtake (roll 7-8: incident but not collision)
        if overtake_roll >= 7:
            # Roll for driver error on failed overtake attempt
            # This applies to both the attacker and defender
            return self._check_driver_error_for_overtake(
                lap, driver_a, driver_b, position_a, position_b
            )

        return None

    def _check_driver_error_for_overtake(
        self,
        lap: int,
        driver_a: str,
        driver_b: str,
        position_a: int,
        position_b: int,
    ) -> Optional[Dict]:
        """
        Check for driver error on failed overtake attempt.

        When an overtake fails (roll 7-8), there's a chance the attacker
        or defender makes a mistake trying to complete or defend the overtake.
        """
        # Check attacker error
        attacker_error_roll = roll_d100()
        attacker_info = self.driver_data.get(driver_a, {})
        attacker_team = attacker_info.get("Team", "Unknown")
        attacker_stability = self.team_stabilities.get(attacker_team)

        attacker_error_threshold = calculate_driver_error_probability(
            driver_a,
            position=position_a,
            is_fighting=True,
            is_leading=False,
        )

        self.dice_logger.log_roll(
            lap=lap,
            driver=driver_a,
            incident_type="overtake_failed_driver_error",
            dice_type="d100",
            dice_result=attacker_error_roll,
            outcome="attacker_error"
            if attacker_error_roll <= attacker_error_threshold
            else "attacker_clean",
            race_time=self.get_relative_time(),
            details={
                "overtake_type": "failed_attempt",
                "position": position_a,
                "error_threshold": round(attacker_error_threshold, 2),
            },
        )

        # Check defender error
        defender_error_roll = roll_d100()
        defender_info = self.driver_data.get(driver_b, {})
        defender_team = defender_info.get("Team", "Unknown")

        defender_error_threshold = calculate_driver_error_probability(
            driver_b,
            position=position_b,
            is_fighting=True,
            is_leading=False,
        )

        self.dice_logger.log_roll(
            lap=lap,
            driver=driver_b,
            incident_type="overtake_defend_driver_error",
            dice_type="d100",
            dice_result=defender_error_roll,
            outcome="defender_error"
            if defender_error_roll <= defender_error_threshold
            else "defender_clean",
            race_time=self.get_relative_time(),
            details={
                "overtake_type": "failed_defend",
                "position": position_b,
                "error_threshold": round(defender_error_threshold, 2),
            },
        )

        # If either made an error, create an incident
        if attacker_error_roll <= attacker_error_threshold:
            return {
                "type": "driver_error",
                "lap": lap,
                "driver": driver_a,
                "cause": "overtake_attempt_failed",
                "time_loss": 3.0,  # Small time loss for mistake
            }
        elif defender_error_roll <= defender_error_threshold:
            return {
                "type": "driver_error",
                "lap": lap,
                "driver": driver_b,
                "cause": "overtake_defend_failed",
                "time_loss": 3.0,
            }

        return None

    def handle_safety_car(self, lap: int, reason: str) -> Dict:
        """Handle safety car deployment."""
        print(f"\n*** Safety Car deployed at lap {lap}: {reason} ***")

        # Roll for SC duration
        sc_laps = roll_d6()  # 1-6 laps
        self.dice_logger.log_roll(
            lap=lap,
            driver="RACE_CONTROL",
            incident_type="safety_car",
            dice_type="d6",
            dice_result=sc_laps,
            outcome=f"sc_for_{sc_laps}_laps",
            race_time=self.get_relative_time(),
            details={"reason": reason},
        )

        self.race_state.sc_active = True
        self.race_state.sc_laps_remaining = sc_laps

        return {
            "type": "safety_car",
            "lap": lap,
            "duration": sc_laps,
            "reason": reason,
        }

    def handle_vsc(self, lap: int, reason: str) -> Dict:
        """Handle Virtual Safety Car."""
        print(f"\n*** Virtual Safety Car at lap {lap}: {reason} ***")

        # Roll for VSC duration (d3 = 1-3)
        vsc_laps = random.randint(1, 3)

        self.dice_logger.log_roll(
            lap=lap,
            driver="RACE_CONTROL",
            incident_type="vsc",
            dice_type="d3",
            dice_result=vsc_laps,
            outcome=f"vsc_for_{vsc_laps}_laps",
            race_time=self.get_relative_time(),
            details={"reason": reason},
        )

        self.race_state.vsc_active = True
        self.race_state.vsc_laps_remaining = vsc_laps

        return {
            "type": "vsc",
            "lap": lap,
            "duration": vsc_laps,
            "reason": reason,
        }

    def apply_safety_car_effects(self, lap_times: Dict[str, float]) -> Dict[str, float]:
        """Apply safety car effects to lap times (typically slows everyone down)."""
        if self.race_state.sc_active:
            # Under SC, lap times are significantly slower
            for driver in lap_times:
                lap_times[driver] += random.uniform(15.0, 25.0)  # SC delta
        elif self.race_state.vsc_active:
            # Under VSC, lap times are moderately slower
            for driver in lap_times:
                lap_times[driver] += random.uniform(8.0, 15.0)  # VSC delta

        return lap_times

    def simulate_lap(
        self,
        lap: int,
        driver: str,
        driver_info: Dict,
        current_tyre: str,
        lap_count_on_tyre: int,
        pit_laps: List[int],
        tyre_sequence: List[str],
        current_tyre_index: int,
        start_delta: float = 0.0,
    ) -> Dict:
        """Simulate a single lap for a driver."""

        # Check for pit stop
        pit_time = 0.0
        new_tyre = current_tyre
        if lap in pit_laps:
            tire_change_time = roll_pit_stop_time()
            track_pit_time = 25.0  # Default

            if self.pitlane_data is not None:
                # Handle case-insensitive track matching
                pitlane_copy = self.pitlane_data.copy()
                pitlane_copy["Track_lower"] = pitlane_copy["Track"].str.lower()
                track_row = pitlane_copy[
                    pitlane_copy["Track_lower"] == self.track_name.lower()
                ]
                if len(track_row) > 0:
                    track_pit_time_val = track_row["Pit Time"]
                    if len(track_pit_time_val) > 0:
                        track_pit_time = float(track_pit_time_val.iloc[0])

            pit_time = track_pit_time + tire_change_time

            # Determine new tyre
            if current_tyre_index + 1 < len(tyre_sequence):
                new_tyre = tyre_sequence[current_tyre_index + 1]

            self.dice_logger.log_roll(
                lap=lap,
                driver=driver,
                incident_type="pit_stop",
                dice_type="pit_dice",
                dice_result=int(tire_change_time * 10),
                outcome="completed",
                race_time=self.get_relative_time(),
                details={
                    "pit_time": pit_time,
                    "track_pit_time": track_pit_time,
                    "new_tyre": new_tyre,
                },
            )

        # Calculate base lap time
        base_lap_time = calculate_base_lap_time(driver_info["R_Value"], self.track_name)

        # Calculate degradation
        r_max = max(d["R_Value"] for d in self.driver_data.values())
        degradation = calculate_degradation_with_cliff(
            lap_count_on_tyre,
            current_tyre,
            driver_info["R_Value"],
            r_max,
            self.track_chars,
            len(pit_laps),
        )

        # Calculate DR-based noise
        dr_values = [d["DR_Value"] for d in self.driver_data.values()]
        dr_min = min(dr_values)
        dr_max = max(dr_values)
        noise_std = calculate_dr_based_std(
            driver_info["DR_Value"], dr_min, dr_max, 0.45
        )

        # Add lap 1 start delta
        lap_time = base_lap_time + degradation * 10 + np.random.normal(0, noise_std)

        if lap == 1:
            lap_time += start_delta

        # Add pit time if pitting
        lap_time += pit_time

        # Apply any active incidents
        for incident in self.race_state.active_incidents:
            if incident.get("driver") == driver:
                # Check if this is a fault with speed degradation
                if (
                    incident.get("type") == "vehicle_fault"
                    and "speed_degradation" in incident
                ):
                    # Accumulate fault degradation (faults compound)
                    self.race_state.driver_fault_degradation[driver] += incident[
                        "speed_degradation"
                    ]
                else:
                    lap_time += incident.get("time_loss", 0.0)

        # Apply accumulated fault degradation (MODERN F1)
        fault_degradation = self.race_state.driver_fault_degradation.get(driver, 0.0)
        if fault_degradation > 0:
            lap_time *= 1.0 + fault_degradation  # Apply as percentage slowdown

        # Apply Monaco-specific pit stop penalty (Fix 2b)
        if is_monaco_track(self.track_name):
            num_pits = len([pl for pl in pit_laps if pl < lap])
            if num_pits > 1:
                extra_stops = num_pits - 1
                penalty = get_monaco_pit_stop_penalty(extra_stops)
                lap_time += penalty

        return {
            "lap_time": lap_time,
            "pit_time": pit_time,
            "degradation": degradation,
            "base_lap_time": base_lap_time,
            "new_tyre": new_tyre,
            "fault_degradation": fault_degradation,
        }

    def run_simulation(self) -> Dict[str, Dict]:
        """Run the complete race simulation."""
        print(f"\n=== Enhanced Race Simulation ===")
        print(f"Track: {self.track_name}, Laps: {self.num_laps}")

        # Record simulation start time for relative timestamps
        self.simulation_start_time = datetime.now()

        # Initialize driver results
        results = {}

        # Get pitlane time
        track_pit_time = 25.0
        if self.pitlane_data is not None:
            # Handle case-insensitive track matching
            pitlane_copy = self.pitlane_data.copy()
            pitlane_copy["Track_lower"] = pitlane_copy["Track"].str.lower()
            track_row = pitlane_copy[
                pitlane_copy["Track_lower"] == self.track_name.lower()
            ]
            if len(track_row) > 0:
                track_pit_time = float(track_row.iloc[0]["Pit Time"])

        # Generate team strategies
        team_strategies = {}
        is_monaco = is_monaco_track(self.track_name)

        for team in set(self.driver_teams.values()):
            if team != "Unknown":
                # Monaco-specific: Force 1-stop strategy (Fix 2c)
                # Real F1: Almost all teams use 1-stop at Monaco due to low tire wear
                if is_monaco:
                    # 85% chance of 1-stop, 15% chance of 2-stop (very rare)
                    strategy = random.choices(["1", "2"], weights=[0.85, 0.15])[0]
                else:
                    strategy = determine_pit_strategy(self.track_name, self.pit_data)

                pit_laps = generate_pit_laps(self.track_name, strategy, self.pit_data)
                # Convert strategy to int for tyre count
                strategy_int = (
                    int(strategy)
                    if isinstance(strategy, (int, str))
                    else int(strategy)
                    if strategy
                    else 1
                )
                tyre_compounds_set = [
                    roll_tyre_for_track(self.track_name)
                    for _ in range(strategy_int + 1)
                ]
                team_strategies[team] = {
                    "strategy": strategy,
                    "pit_laps": pit_laps,
                    " tyre_compounds_set": tyre_compounds_set,
                }

        # Initialize driver states
        for driver in self.driver_data:
            results[driver] = {
                "lap_times": [],
                "cumulative_time": 0.0,
                "pit_laps": [],
                "pit_events": [],
                "incidents": [],
                "position": self.driver_data[driver].get("grid_position", 20),
            }

            # Get team strategy
            team = self.driver_teams.get(driver, "Unknown")
            if team in team_strategies:
                results[driver]["pit_laps"] = generate_pit_laps(
                    self.track_name, team_strategies[team]["strategy"], self.pit_data
                )
                results[driver][" tyre_sequence"] = generate_individual_tyre_sequence(
                    team_strategies[team][" tyre_compounds_set"]
                )
            else:
                strategy = determine_pit_strategy(self.track_name, self.pit_data)
                strategy_int = (
                    int(strategy)
                    if isinstance(strategy, (int, str))
                    else int(strategy)
                    if strategy
                    else 1
                )
                results[driver]["pit_laps"] = generate_pit_laps(
                    self.track_name, strategy, self.pit_data
                )
                results[driver][" tyre_sequence"] = [
                    roll_tyre_for_track(self.track_name)
                    for _ in range(strategy_int + 1)
                ]

        # Get initial grid positions
        grid_positions = {
            driver: self.driver_data[driver].get("grid_position", i + 1)
            for i, driver in enumerate(self.driver_data.keys())
        }

        # Simulate start
        start_deltas = self.simulate_start(grid_positions)

        # Main race loop
        print(f"\n=== Starting Race (Lap 1 to {self.num_laps}) ===")

        for lap in range(1, self.num_laps + 1):
            self.race_state.current_lap = lap

            if lap % 10 == 0:
                print(f"  Lap {lap}/{self.num_laps}...")

            # Check for random VSC/SC deployment (except first few laps)
            if (
                lap > 3
                and not self.race_state.sc_active
                and not self.race_state.vsc_active
            ):
                sc_roll = roll_d100()
                if sc_roll >= 98:  # 2% chance of SC
                    reason = "debris" if sc_roll == 98 else "incident"
                    self.handle_safety_car(lap, reason)
                elif sc_roll >= 95:  # 3% chance of VSC
                    self.handle_vsc(lap, "debris")

            # Process safety car laps
            if self.race_state.sc_active:
                self.race_state.sc_laps_remaining -= 1
                if self.race_state.sc_laps_remaining <= 0:
                    self.race_state.sc_active = False
                    print(f"  *** Safety Car ends at lap {lap} ***")

            if self.race_state.vsc_active:
                self.race_state.vsc_laps_remaining -= 1
                if self.race_state.vsc_laps_remaining <= 0:
                    self.race_state.vsc_active = False

            # Check for incidents every lap
            if lap > 2:
                incidents = self.check_for_incidents(lap, list(self.driver_data.keys()))
                for incident in incidents:
                    results[incident["driver"]]["incidents"].append(incident)

            # Simulate each driver
            lap_times_this_lap = {}

            for driver in self.driver_data:
                # Skip DNFed drivers - they have retired from the race
                if self.race_state.is_dnf(driver):
                    continue

                driver_result = results[driver]

                # Get current tyre info
                current_tyre_index = sum(
                    1 for pl in driver_result["pit_laps"] if pl < lap
                )
                current_tyre = (
                    driver_result[" tyre_sequence"][current_tyre_index]
                    if current_tyre_index < len(driver_result[" tyre_sequence"])
                    else "UNKNOWN"
                )
                lap_count_on_tyre = lap - sum(
                    1 for pl in driver_result["pit_laps"] if pl < lap
                )

                # Calculate lap time
                lap_result = self.simulate_lap(
                    lap=lap,
                    driver=driver,
                    driver_info=self.driver_data[driver],
                    current_tyre=current_tyre,
                    lap_count_on_tyre=lap_count_on_tyre,
                    pit_laps=driver_result["pit_laps"],
                    tyre_sequence=driver_result[" tyre_sequence"],
                    current_tyre_index=current_tyre_index,
                    start_delta=start_deltas.get(driver, 0.0),
                )

                lap_time = lap_result["lap_time"]

                # Apply safety car effects
                if self.race_state.sc_active:
                    lap_time += random.uniform(15.0, 25.0)
                elif self.race_state.vsc_active:
                    lap_time += random.uniform(8.0, 15.0)

                # Track cumulative time
                driver_result["cumulative_time"] += lap_time
                driver_result["lap_times"].append(lap_time)
                lap_times_this_lap[driver] = driver_result["cumulative_time"]

                # Record pit events
                if lap in driver_result["pit_laps"]:
                    driver_result["pit_events"].append(
                        {
                            "lap": lap,
                            "pit_time": lap_result["pit_time"],
                            "lap_time": lap_time,
                        }
                    )

            # Update positions
            sorted_drivers = sorted(lap_times_this_lap.items(), key=lambda x: x[1])

            # Monaco-specific: Add overtake resistance (Fix 2a)
            # At Monaco, it's very hard to overtake, so we add a small bonus
            # to drivers who are already ahead based on their position
            if is_monaco_track(self.track_name):
                # Apply position-based defense bonus for Monaco
                # The further ahead you are, the harder it is to pass
                monaco_defense_factor = {}
                for driver, cum_time in lap_times_this_lap.items():
                    current_pos = results[driver]["position"]
                    # Add small time bonus for drivers ahead (makes it harder to catch up)
                    defense_bonus = (
                        20 - current_pos
                    ) * 0.02  # Up to 0.38s bonus for leader
                    monaco_defense_factor[driver] = cum_time - defense_bonus
                sorted_drivers = sorted(
                    monaco_defense_factor.items(), key=lambda x: x[1]
                )

            for position, (driver, _) in enumerate(sorted_drivers, 1):
                results[driver]["position"] = position

        # Finalize results
        print(f"\n=== Race Complete ===")

        # Sort by final position
        final_results = sorted(results.items(), key=lambda x: x[1]["position"])

        for position, (driver, result) in enumerate(final_results, 1):
            print(f"  P{position}: {driver} - {result['cumulative_time']:.3f}s")

        return results


# =============================================================================
# RACE RESULTS EXPORT
# =============================================================================


def save_race_results(
    results: Dict[str, Dict],
    track_name: str,
    driver_data: Dict[str, Dict],
    output_dir: str,
    fault_degradation: Optional[Dict[str, float]] = None,
    dnf_drivers: Optional[Dict[str, int]] = None,
    retirement_reasons: Optional[Dict[str, str]] = None,
):
    """Save race results to CSV, sorted by finished position."""
    rows = []

    # Default to empty dicts if not provided
    if dnf_drivers is None:
        dnf_drivers = {}
    if retirement_reasons is None:
        retirement_reasons = {}

    for driver, result in results.items():
        team = driver_data.get(driver, {}).get("Team", "Unknown")

        # Get accumulated fault degradation
        degradation = 0.0
        if fault_degradation and driver in fault_degradation:
            degradation = fault_degradation[driver]

        # Check if driver DNFed
        is_dnf = driver in dnf_drivers
        lap_dnfed = dnf_drivers.get(driver, "")
        reason = retirement_reasons.get(driver, "")

        row = {
            "position": result["position"],
            "driver": driver,
            "team": team,
            "total_time": result["cumulative_time"],
            "num_pits": len(result["pit_laps"]),
            "pit_laps": ",".join(map(str, result["pit_laps"]))
            if result["pit_laps"]
            else "",
            "num_incidents": len(result["incidents"]),
            "incidents": ",".join(
                [i.get("type", "unknown") for i in result["incidents"]]
            ),
            "fault_degradation": f"{degradation:.4f}",  # Percentage
            "dnf": "DNF" if is_dnf else "",
            "lap_dnfed": str(lap_dnfed) if lap_dnfed else "",
            "retirement_reason": reason,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Separate finishers from DNFs
    finishers = df[df["dnf"] == ""].copy()
    dnfs = df[df["dnf"] == "DNF"].copy()

    # Sort finishers by position (ascending)
    finishers = finishers.sort_values(by="position", ascending=True)

    # Sort DNFs by lap_dnfed (descending - those who lasted longer get better positions)
    # Convert lap_dnfed to numeric for sorting
    if len(dnfs) > 0:
        dnfs["lap_dnfed_num"] = pd.to_numeric(
            dnfs["lap_dnfed"], errors="coerce"
        ).fillna(0)
        dnfs = dnfs.sort_values(by="lap_dnfed_num", ascending=False)
        # Drop the temporary column
        dnfs = dnfs.drop(columns=["lap_dnfed_num"])

    # Reassign positions: finishers get 1 to N, then DNFs continue from there
    # First, update finisher positions to be sequential
    finisher_positions = list(range(1, len(finishers) + 1))
    finishers["position"] = finisher_positions

    # Then, assign DNF positions to continue after finishers
    if len(dnfs) > 0:
        dnf_start_position = len(finishers) + 1
        dnf_positions = list(range(dnf_start_position, dnf_start_position + len(dnfs)))
        dnfs["position"] = dnf_positions

    # Combine: finishers first, then DNFs
    df = pd.concat([finishers, dnfs], ignore_index=True)

    filename = f"race_results_{track_name.lower()}.csv"
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    print(f"Race results saved to: {filepath}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================


def main(argv=None):
    """Run the enhanced simulation."""

    parser = argparse.ArgumentParser(
        description="Enhanced F1 Race Simulation with Incident and DRS Integration"
    )
    parser.add_argument(
        "--gp-name",
        default="Spain",
        help="Grand Prix name (default: Spain)",
    )
    parser.add_argument(
        "--csv-file",
        help="Path to driver data CSV file",
    )
    parser.add_argument(
        "--num-laps",
        type=int,
        help="Number of race laps (auto-detected if not specified)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--no-drs",
        action="store_true",
        help="Disable DRS system",
    )
    parser.add_argument(
        "--no-incidents",
        action="store_true",
        help="Disable incident system",
    )

    args = parser.parse_args(argv)

    # Set random seed
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    gp_name = args.gp_name

    # Resolve number of laps
    num_laps = args.num_laps
    if num_laps is None:
        track_key = gp_name.lower()
        if track_key in DEFAULT_LAP_COUNTS:
            num_laps = DEFAULT_LAP_COUNTS[track_key]
        else:
            num_laps = 66  # Default

    print("=" * 60)
    print("ENHANCED F1 RACE SIMULATION")
    print("=" * 60)
    print(f"Track: {gp_name}")
    print(f"Laps: {num_laps}")
    print(f"DRS Enabled: {not args.no_drs}")
    print(f"Incidents Enabled: {not args.no_incidents}")
    if args.seed:
        print(f"Random Seed: {args.seed}")
    print("=" * 60)

    # Load driver data
    csv_file = args.csv_file or os.path.join("outputs/tables", f"{gp_name}.csv")
    csv_file = os.path.normpath(csv_file)

    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        return

    driver_data = read_driver_data(csv_file)
    print(f"\nLoaded {len(driver_data)} drivers")

    # Filter Andretti drivers based on GP attendance
    driver_data = filter_andretti_drivers(driver_data, gp_name)
    print(
        f"Running with {len(driver_data)} drivers (Andretti: {'attending' if is_andretti_participating(gp_name) else 'not attending'})"
    )

    # Load pit stop data
    pit_data = load_pit_stop_data()
    if pit_data is None:
        print("Error: Could not load pit stop data")
        return

    # Get track characteristics
    track_chars = get_track_characteristics()
    track_key = gp_name.lower()
    if track_key not in track_chars:
        print(f"Error: Track {gp_name} not found in track characteristics")
        return

    current_track_chars = track_chars[track_key]

    # Assign teams
    team_strategies_data, driver_teams = assign_team_strategies(
        driver_data, gp_name, num_laps, pit_data
    )

    # Assign grid positions
    all_drivers = list(driver_data.keys())
    random.shuffle(all_drivers)
    for i, driver in enumerate(all_drivers):
        driver_data[driver]["grid_position"] = i + 1

    print("\nGrid Positions:")
    for driver in sorted(all_drivers, key=lambda x: driver_data[x]["grid_position"]):
        print(f"  P{driver_data[driver]['grid_position']}: {driver}")

    # Initialize dice logger
    dice_logger = DiceRollingLogger(gp_name)

    # Get team stabilities
    team_stabilities = get_team_stabilities()

    # Create and run simulation
    simulator = EnhancedRaceSimulator(
        track_name=gp_name,
        num_laps=num_laps,
        driver_data=driver_data,
        team_stabilities=team_stabilities,
        driver_teams=driver_teams,
        pit_data=pit_data,
        track_chars=current_track_chars,
        dice_logger=dice_logger,
        random_seed=args.seed,
    )

    results = simulator.run_simulation()

    # Create output directory for this race run
    runtime_datetime = datetime.now()
    race_output_dir = get_race_output_dir(gp_name, runtime_datetime)

    print(f"\nRace output directory: {race_output_dir}")

    # Get fault degradation data
    fault_degradation = dict(simulator.race_state.driver_fault_degradation)

    # Get DNF data
    dnf_drivers = dict(simulator.race_state.dnf_drivers)
    retirement_reasons = dict(simulator.race_state.retirement_reasons)

    # Save results
    save_race_results(
        results,
        gp_name,
        driver_data,
        race_output_dir,
        fault_degradation,
        dnf_drivers,
        retirement_reasons,
    )
    dice_logger.save_to_csv(race_output_dir)

    # Generate markdown report (Fix 3)
    try:
        from simulation.report_generator import generate_report

        race_results_path = os.path.join(
            race_output_dir, f"race_results_{gp_name.lower()}.csv"
        )
        dice_rolls_path = os.path.join(
            race_output_dir, f"dice_rolls_{gp_name.lower()}.csv"
        )
        report_path = os.path.join(race_output_dir, f"race_report_{gp_name.lower()}.md")

        generate_report(
            race_results_path=race_results_path,
            dice_rolls_path=dice_rolls_path,
            track_name=gp_name,
            output_path=report_path,
        )
    except Exception as e:
        print(f"Warning: Could not generate report: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)
    print(f"\nDice Roll Summary:")
    for incident_type, count in dice_logger.get_summary().items():
        print(f"  {incident_type}: {count}")

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
