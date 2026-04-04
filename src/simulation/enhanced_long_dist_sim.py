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
import json
import glob
import math

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
import matplotlib

# Force non-interactive backend to avoid GUI windows interrupting simulation runs.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import random
import csv
from bisect import bisect_right
from collections import defaultdict, deque
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Rating compensation functions (embedded to avoid import issues)
# These are duplicated from core/rating_compensator.py
from collections import defaultdict as _dd

TEAM_TIERS = {
    "TOP": {
        "teams": {"red_bull", "ferrari", "mercedes", "mclaren", "aston_martin"},
        "max_compensation": 0.35,
    },
    "MID": {"teams": {"alpine", "williams"}, "max_compensation": 0.25},
    "BACK": {"teams": {"alphatauri", "alfa_romeo", "haas"}, "max_compensation": 0.15},
}

FERRARI_NARRATIVE_MODE = True
_FERRARI_NARRATIVE_CACHE: Dict[str, Tuple[float, float]] = {}

STRATEGIST_TEAM_ALIASES = {
    "Red Bull": "Red Bull Racing",
}


def _get_team_tier(team_id):
    team_id_lower = team_id.lower()
    for tier, config in TEAM_TIERS.items():
        if team_id_lower in config["teams"]:
            return tier
    return "MID"


def _calculate_compensated_r_core(
    base_r, team_leader_r, team_tier, is_number_2, driver_id
):
    if not is_number_2:
        return 0.0, 0.0
    gap_to_leader = team_leader_r - base_r
    if gap_to_leader <= 0:
        return 0.0, 0.0
    tier_config = TEAM_TIERS.get(team_tier, TEAM_TIERS["MID"])
    max_comp = tier_config["max_compensation"]
    compensation = min(gap_to_leader * 0.5, max_comp)
    # Special handling for Tsunoda
    if driver_id.upper() == "TSUNODA":
        compensation *= 0.5
    return max(0.0, compensation), gap_to_leader


def _get_team_leader_r_values_embedded(driver_data):
    """Calculate each team's leader R value."""
    teams = _dd(list)
    for driver_name, data in driver_data.items():
        team = data.get("Team", "Unknown")
        dr = data.get("DR_Value", data.get("dr_value", 100.0))
        pr = data.get("PR_Value", data.get("team_pr", 300.0))
        r_value = dr * pr / 100.0
        teams[team].append((driver_name, r_value))

    team_leaders = {}
    for team, drivers in teams.items():
        drivers_sorted = sorted(drivers, key=lambda x: x[1], reverse=True)
        team_leaders[team] = drivers_sorted[0][1]
    return team_leaders


def _is_number_2_driver_embedded(driver_name, driver_data):
    """Check if driver is #2 based on R value."""
    if driver_name not in driver_data:
        return False

    team = driver_data[driver_name].get("Team", "Unknown")

    team_drivers = [
        (
            d,
            data.get("DR_Value", data.get("dr_value", 100.0))
            * data.get("PR_Value", data.get("team_pr", 300.0))
            / 100.0,
        )
        for d, data in driver_data.items()
        if data.get("Team") == team
    ]

    if len(team_drivers) < 2:
        return False

    team_drivers_sorted = sorted(team_drivers, key=lambda x: x[1], reverse=True)
    return driver_name != team_drivers_sorted[0][0]


def get_team_leader_r_values(driver_data):
    """Calculate each team's leader R value."""
    teams = defaultdict(list)
    for driver_name, data in driver_data.items():
        team = data.get("Team", "Unknown")
        dr = data.get("DR_Value", data.get("dr_value", 100.0))
        pr = data.get("PR_Value", data.get("team_pr", 300.0))
        r_value = dr * pr / 100.0
        teams[team].append((driver_name, r_value))

    team_leaders = {}
    for team, drivers in teams.items():
        drivers_sorted = sorted(drivers, key=lambda x: x[1], reverse=True)
        team_leaders[team] = drivers_sorted[0][1]

    return team_leaders


def is_number_2_driver(driver_name, driver_data):
    """Check if driver is #2 based on R value."""
    if driver_name not in driver_data:
        return False

    team = driver_data[driver_name].get("Team", "Unknown")

    team_drivers = [
        (
            d,
            data.get("DR_Value", data.get("dr_value", 100.0))
            * data.get("PR_Value", data.get("team_pr", 300.0))
            / 100.0,
        )
        for d, data in driver_data.items()
        if data.get("Team") == team
    ]

    if len(team_drivers) < 2:
        return False

    team_drivers_sorted = sorted(team_drivers, key=lambda x: x[1], reverse=True)
    return driver_name != team_drivers_sorted[0][0]


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

# Import weather system modules
from weather.integrators.enhanced_sim_weather import (
    SimWeatherIntegration,
    WeatherLapData,
    RaceWeatherLog,
)
from weather.weather_types import (
    WeatherType,
    TrackCondition,
    RaceControlState,
    RainIntensity,
    get_track_info,
)

# Import DRS system modules
from drs.driver_state import DriverRaceState
from drs.zones import TRACKS as DRS_TRACKS

# Import Strategist system modules
from src.strategist import (
    StrategistManager,
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    DriverComplianceLevel,
    PaceMode,
    get_manager,
    get_track_rules,
)
from src.strategist.integrators.race_sim_integration import (
    StrategistIntegration,
)

# Import Driver Skills System
from src.skills import (
    DriverSkillManager,
    SkillContext,
    SessionType,
    WeatherCondition,
    get_skill_manager,
)
from src.core.narrative_assist import NarrativeAssistConfig, ProbabilityBalancer

# =============================================================================
# STUB IMPLEMENTATIONS FOR MIGRATED FUNCTIONS
# These were previously in long_dist_sim_with_box.py
# =============================================================================

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
                    driver_info = {
                        "Team": row.get("Team", ""),
                        "R_Value": float(row.get("R_Value", 300)),
                        "DR_Value": float(row.get("DR", 0)),
                    }
                    # Read GridPosition if present (from qualifying/sprint results)
                    grid_pos = row.get("GridPosition")
                    if grid_pos:
                        try:
                            driver_info["grid_position"] = int(grid_pos)
                        except (ValueError, TypeError):
                            pass
                    driver_data[driver_name] = driver_info
    except FileNotFoundError:
        print(f"Warning: Driver data file not found: {csv_file}")
    return driver_data


def load_pit_stop_data() -> dict:
    """Load pit stop data from CSV."""
    pit_data = {}
    try:
        with open("data/pit_stop_strategies_2022_2024.csv", "r", encoding="utf-8") as f:
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
    for filepath in ["data/pitlane_time.csv", "outputs/tables/pitlane_time.csv"]:
        try:
            df = pd.read_csv(filepath)
            return df
        except FileNotFoundError:
            continue
    print("Warning: pitlane_time.csv not found, using default values")
    return None


def get_track_characteristics() -> dict:
    """Get track characteristics data from CSV file."""
    import pandas as pd

    # Try to load from CSV
    try:
        df = pd.read_csv("data/track_characteristics.csv")
        track_chars = {}
        for _, row in df.iterrows():
            track_name = row["Track"].lower()
            # Convert C(M), C(A), C(P) to abrasion/grip values
            cm = row.get("C(M)", 1.0)
            ca = row.get("C(A)", 1.0)
            # Map to abrasion and grip (higher C(P) = more degradation = lower grip)
            # C(P) typically ranges from 1.0 to 1.15
            cp = row.get("C(P)", 1.0)

            # Calculate abrasion (higher C(M) = more mechanical degradation)
            # and grip (higher C(A) = more aerodynamic degradation affects grip)
            # Use simplified mapping
            abrasion = min(1.0, (cm - 0.9) * 10 + 0.3) if cm else 0.5
            grip = max(0.3, 1.0 - (ca - 1.0) * 5) if ca else 0.7

            track_chars[track_name] = {
                "abrasion": round(abrasion, 2),
                "grip": round(grip, 2),
            }
        return track_chars
    except FileNotFoundError as e:
        print(f"Warning: Could not load track_characteristics.csv: {e}")
    except pd.errors.ParserError as e:
        print(f"Warning: Could not parse track_characteristics.csv: {e}")
    except Exception as e:
        print(f"Warning: Unexpected error loading track_characteristics.csv: {e}")
        # Fallback to hardcoded values
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
                "tyre_compounds_set": ["HARD", "MEDIUM"],
            }
    return team_strategies, driver_teams


def generate_pit_laps(track_name: str, strategy, pit_data: dict) -> list:
    """Generate pit stop laps based on strategy."""
    track = track_name.lower()
    num_laps = DEFAULT_LAP_COUNTS.get(track, 66)
    # Convert strategy to int (handles both int and string inputs)
    num_stops = int(strategy) if strategy is not None else 3
    if num_stops == 1:
        return [int(num_laps * 0.6)]
    elif num_stops == 2:
        return [int(num_laps * 0.35), int(num_laps * 0.7)]
    return [int(num_laps * 0.3), int(num_laps * 0.55), int(num_laps * 0.8)]


def generate_individual_tyre_sequence(compounds: list) -> list:
    """Generate individual tyre sequence."""
    return compounds if compounds else ["HARD", "MEDIUM"]


def determine_pit_strategy(track_name: str, pit_data: dict) -> int:
    """Determine pit strategy (number of stops) via initial dice control.

    Default baseline:
    - 1 stop: 50%
    - 2 stops: 50%

    Ferrari narrative mode:
    - Uses historical simulation outcomes to bias 1/2-stop split toward
      the strategy with the highest observed win likelihood.
    """
    return determine_pit_strategy_with_feedback(track_name, pit_data)


def determine_pit_strategy_with_feedback(
    track_name: str,
    pit_data: dict,
    team: Optional[str] = None,
) -> int:
    one_stop_weight = 0.5
    two_stop_weight = 0.5
    config = NarrativeAssistConfig.get_config()
    balancer = ProbabilityBalancer()

    if team:
        one_stop_weight, two_stop_weight = get_team_narrative_weights(track_name, team)
    elif FERRARI_NARRATIVE_MODE:
        one_stop_weight, two_stop_weight = get_ferrari_narrative_weights(track_name)

    if config.enabled and team:
        one_stop_weight, two_stop_weight = balancer.shape_strategy_weights(
            team, one_stop_weight, two_stop_weight
        )

        preferred_strategy = 1 if one_stop_weight >= two_stop_weight else 2

        if config.is_ultra() and config.strategy_lock:
            return preferred_strategy

        strategy_bias = config.strategy_bias

        if config.is_target_team(team):
            force_optimal_prob = min(0.92, 0.55 + strategy_bias * 0.55)
            if random.random() < force_optimal_prob:
                return preferred_strategy
        else:
            force_suboptimal_prob = min(0.75, 0.18 + config.opponent_debuff * 1.1)
            if random.random() < force_suboptimal_prob:
                return 2 if preferred_strategy == 1 else 1

    roll = roll_d100()
    threshold = int(round(one_stop_weight * 100))
    return 1 if roll <= threshold else 2


def get_team_narrative_weights(track_name: str, team_name: str) -> Tuple[float, float]:
    """Build team strategy weights from historical outputs using smoothed score model."""
    config = NarrativeAssistConfig.get_config()
    cache_key = f"{track_name.lower()}::{team_name.lower()}"
    if cache_key in _FERRARI_NARRATIVE_CACHE:
        return _FERRARI_NARRATIVE_CACHE[cache_key]

    base_dir = "outputs"
    track_token = track_name.lower()
    race_weekend_pattern = os.path.join(
        base_dir,
        "race_weekend",
        f"{track_name}_*",
        "race",
        f"race_results_{track_token}.csv",
    )
    enhanced_pattern = os.path.join(
        base_dir,
        "enhanced_sim",
        f"{track_name}_*",
        f"race_results_{track_token}.csv",
    )

    files = glob.glob(race_weekend_pattern) + glob.glob(enhanced_pattern)
    files = list(dict.fromkeys(files))

    score_sum_by_stops = {1: 0.0, 2: 0.0}
    samples_by_stops = {1: 0, 2: 0}

    for filepath in files:
        try:
            df = pd.read_csv(filepath)
        except Exception:
            continue

        if "team" not in df.columns or "num_pits" not in df.columns:
            continue

        rows = df[df["team"].astype(str).str.lower() == team_name.lower()]
        for _, row in rows.iterrows():
            try:
                stops = int(str(row.get("num_pits", -1)))
                position = int(str(row.get("position", 99)))
            except Exception:
                continue

            if stops not in (1, 2):
                continue

            base_score = max(0, 26 - position)
            podium_bonus = 0
            if position == 1:
                podium_bonus = 12
            elif position == 2:
                podium_bonus = 8
            elif position == 3:
                podium_bonus = 6
            elif position <= 10:
                podium_bonus = 2

            score_sum_by_stops[stops] += float(base_score + podium_bonus)
            samples_by_stops[stops] += 1

    total_samples = samples_by_stops[1] + samples_by_stops[2]
    if total_samples < 8:
        if config.is_ultra() and config.is_target_team(team_name):
            _FERRARI_NARRATIVE_CACHE[cache_key] = (0.82, 0.18)
            return (0.82, 0.18)
        _FERRARI_NARRATIVE_CACHE[cache_key] = (0.5, 0.5)
        return (0.5, 0.5)

    ultra_mode = config.is_ultra()
    prior_samples = 2.0 if ultra_mode else 3.0
    prior_score = 15.5 if ultra_mode else 14.0
    mean1 = (score_sum_by_stops[1] + prior_score * prior_samples) / (
        samples_by_stops[1] + prior_samples
    )
    mean2 = (score_sum_by_stops[2] + prior_score * prior_samples) / (
        samples_by_stops[2] + prior_samples
    )

    beta = 0.22 if ultra_mode else 0.14
    p1 = math.exp(beta * mean1)
    p2 = math.exp(beta * mean2)
    norm = max(1e-9, p1 + p2)
    one_stop_weight = p1 / norm

    if ultra_mode:
        one_stop_weight = max(0.08, min(0.92, one_stop_weight))
    else:
        one_stop_weight = max(0.12, min(0.88, one_stop_weight))
    two_stop_weight = 1.0 - one_stop_weight

    _FERRARI_NARRATIVE_CACHE[cache_key] = (one_stop_weight, two_stop_weight)
    return (one_stop_weight, two_stop_weight)


def get_ferrari_narrative_weights(track_name: str) -> Tuple[float, float]:
    """Build Ferrari narrative strategy weights from historical simulation outputs."""
    return get_team_narrative_weights(track_name, "Ferrari")


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


def calculate_base_lap_time(
    dr_value: float,
    team_pr: float,
    track_name: str,
) -> float:
    """Calculate base lap time based on R = DR * PR / 100 formula.

    R value determines the base lap time. Higher R = faster lap.

    Args:
        dr_value: Driver DR value (driver rating)
        team_pr: Team PR value (car performance rating)
        track_name: Track name
    """
    base_time, _ = TRACK_BASE_LAP_TIMES.get(track_name.lower(), (88.0, 300))

    # Calculate R value using the formula: R = DR * PR / 100
    r_value = dr_value * team_pr / 100.0

    # Calculate lap time based on R value
    # Reference R value of 300 gives base_time
    # Higher R = faster time (lower lap_time)
    factor = 0.01  # Coefficient for adjustments
    adjustment = (r_value - 300.0) * factor
    lap_time = base_time - adjustment

    return lap_time


def calculate_degradation_with_cliff(
    lap_number: int,
    tyre_compound: str,
    r_value: float,
    r_max: float,
    track_chars: dict,
    pit_lap_count: int,
    team_pr: float = None,
    pr_min: float = None,
    pr_max: float = None,
) -> float:
    """Calculate tire degradation with cliff effect.

    PR (car performance) affects tire management - better cars manage tires better.
    """
    tyre_params = get_universal_tyre_params_with_cliff()
    compound_params = tyre_params.get(tyre_compound, tyre_params["MEDIUM"])

    # Non-linear scaling based on R value (driver skill)
    scaled_lap = nonlinear_scaling(r_value, compound_params["base_lap"], r_max)

    # Track characteristics compensation
    abrasion = track_chars.get("abrasion", 5) if isinstance(track_chars, dict) else 5
    wear_factor = calculate_wear_compensation(abrasion)

    # Base degradation rate
    base_degradation = compound_params["base_degradation"] * wear_factor

    # PR (car) affects tire management - better car = slower degradation
    pr_factor = 1.0
    if (
        team_pr is not None
        and pr_min is not None
        and pr_max is not None
        and pr_max > pr_min
    ):
        pr_normalized = (team_pr - pr_min) / (pr_max - pr_min)  # 0 to 1
        # Better car (higher PR) reduces degradation by up to 20%
        pr_factor = 1.0 - pr_normalized * 0.2

    # Cliff effect
    cliff_lap = compound_params["cliff_lap"]
    cliff_severity = compound_params["cliff_severity"]

    if lap_number > cliff_lap:
        cliff_factor = 1 + cliff_severity * ((lap_number - cliff_lap) / cliff_lap)
    else:
        cliff_factor = 1.0

    # Calculate cumulative degradation with PR factor
    degradation = (
        base_degradation * (lap_number / scaled_lap) * cliff_factor * pr_factor
    )

    return degradation


def calculate_dr_based_std(
    dr_value: float,
    dr_min: float,
    dr_max: float,
    base_std: float = 0.08,
    previous_bias: float = 0.0,
    markov_factor: float = 0.6,
    team_pr: Optional[float] = None,
    pr_min: Optional[float] = None,
    pr_max: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate noise standard deviation based on DR (driver stability).

    DR represents driver consistency - higher DR means more stable lap times.

    Args:
        dr_value: Driver DR value (stability/consistency rating)
        dr_min, dr_max: Range of DR values
        base_std: Base standard deviation
        previous_bias: Previous lap's noise bias (for Markov process)
        markov_factor: How much previous bias carries over (0-1)

    Returns:
        Tuple of (std_deviation, new_bias) for Markov chain
    """
    # DR determines noise level: higher DR = lower noise (more consistent)
    if dr_max != dr_min:
        dr_normalized = (dr_value - dr_min) / (dr_max - dr_min)
    else:
        dr_normalized = 0.5

    # DR tiers for noise levels:
    # High DR (>=99.5): Very consistent, low noise (0.01-0.02s)
    # Mid DR (99.0-99.5): Moderate consistency (0.02-0.04s)
    # Low DR (<99.0): Less consistent, higher noise (0.04-0.08s)
    if dr_normalized >= 0.75:  # Top 25% - elite consistency
        effective_base = 0.01 + (1 - dr_normalized) * 0.04  # 0.01-0.02s
    elif dr_normalized >= 0.4:  # Mid 35% - good consistency
        effective_base = 0.02 + (0.75 - dr_normalized) * 0.057  # 0.02-0.04s
    else:  # Bottom 40% - variable consistency
        effective_base = 0.04 + (0.4 - dr_normalized) * 0.133  # 0.04-0.08s

    # PR-sensitive intra-session variability:
    # lower-PR cars tend to be less stable lap-to-lap, but keep changes moderate.
    if (
        team_pr is not None
        and pr_min is not None
        and pr_max is not None
        and pr_max > pr_min
    ):
        pr_normalized = (team_pr - pr_min) / (pr_max - pr_min)
        # Top PR: ~0.92x variance, Low PR: ~1.18x variance
        pr_variance_factor = 1.18 - 0.26 * pr_normalized
        effective_base *= pr_variance_factor

    # Cap at reasonable limits
    effective_base = max(0.006, min(effective_base, 0.11))

    # Markov process: bias carries over from previous lap
    # Driver's "form" persists - consistent drivers maintain form better
    consistency_factor = 0.5 + dr_normalized * 0.3  # 0.5-0.8 based on DR
    new_bias = previous_bias * markov_factor * consistency_factor + np.random.normal(
        0, effective_base * 0.3
    )
    # Decay bias over time
    new_bias *= 0.95

    # Final std
    final_std = effective_base * 0.9

    return final_std, new_bias


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
    """Get tire parameters with optional FastF1/Pirelli-informed calibration."""
    defaults = {
        "C1": {
            "base_lap": 29,
            "base_degradation": 0.028,
            "cliff_lap": 30,
            "cliff_severity": 0.14,
        },
        "C2": {
            "base_lap": 24,
            "base_degradation": 0.032,
            "cliff_lap": 24,
            "cliff_severity": 0.15,
        },
        "C3": {
            "base_lap": 20,
            "base_degradation": 0.036,
            "cliff_lap": 19,
            "cliff_severity": 0.16,
        },
        "C4": {
            "base_lap": 16,
            "base_degradation": 0.041,
            "cliff_lap": 15,
            "cliff_severity": 0.17,
        },
        "C5": {
            "base_lap": 13,
            "base_degradation": 0.046,
            "cliff_lap": 13,
            "cliff_severity": 0.19,
        },
        # Also support compound names
        "SOFT": {
            "base_lap": 16,
            "base_degradation": 0.041,
            "cliff_lap": 15,
            "cliff_severity": 0.17,
        },
        "MEDIUM": {
            "base_lap": 20,
            "base_degradation": 0.036,
            "cliff_lap": 19,
            "cliff_severity": 0.16,
        },
        "HARD": {
            "base_lap": 24,
            "base_degradation": 0.032,
            "cliff_lap": 24,
            "cliff_severity": 0.15,
        },
    }

    calibration_path = os.path.join("data", "tyre_fastf1_calibration.json")
    if not os.path.exists(calibration_path):
        return defaults

    try:
        with open(calibration_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        calibrated = payload.get("tyre_params", {})
        for compound, values in calibrated.items():
            if compound not in defaults or not isinstance(values, dict):
                continue
            for key in ["base_lap", "base_degradation", "cliff_lap", "cliff_severity"]:
                if key in values:
                    defaults[compound][key] = values[key]
    except Exception:
        return defaults

    return defaults


def get_tyre_pace_delta_seconds(tyre_compound: str) -> float:
    """Return compound pace offset in seconds (negative = faster)."""
    defaults = {
        "HARD": 0.26,
        "MEDIUM": 0.0,
        "SOFT": -0.34,
        "C1": 0.42,
        "C2": 0.24,
        "C3": 0.0,
        "C4": -0.22,
        "C5": -0.44,
    }

    calibration_path = os.path.join("data", "tyre_fastf1_calibration.json")
    if os.path.exists(calibration_path):
        try:
            with open(calibration_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            calibrated = payload.get("pace_delta_seconds", {})
            if isinstance(calibrated, dict):
                defaults.update(calibrated)
        except Exception:
            pass

    return float(defaults.get(tyre_compound.upper(), defaults["MEDIUM"]))


def roll_driver_error_impact() -> Dict[str, Any]:
    """Roll driver-error impact with strong skew toward very small mistakes."""
    roll = roll_d100()

    if roll == 1:
        # Single major failure bucket (>1s), very rare
        return {
            "impact_class": "major_failure",
            "time_loss": round(random.uniform(1.1, 2.3), 3),
            "error_type": "wall_brush" if roll_d10() <= 4 else "major_lockup",
            "damage_severity": "major",
            "major_failure": True,
            "dice": roll,
        }

    if roll <= 10:
        # Larger but still bounded error: 0.25-0.50s
        return {
            "impact_class": "large_error",
            "time_loss": round(random.uniform(0.25, 0.5), 3),
            "error_type": "lockup" if roll_d6() <= 3 else "wide_line",
            "damage_severity": "moderate",
            "major_failure": False,
            "dice": roll,
        }

    if roll <= 30:
        # Small/moderate: 0.10-0.25s
        return {
            "impact_class": "small_error",
            "time_loss": round(random.uniform(0.1, 0.25), 3),
            "error_type": "minor_lockup" if roll_d6() <= 3 else "momentum_loss",
            "damage_severity": "minor",
            "major_failure": False,
            "dice": roll,
        }

    # Dominant bucket: tiny errors (<0.1s)
    return {
        "impact_class": "micro_error",
        "time_loss": round(random.uniform(0.02, 0.09), 3),
        "error_type": "small_correction",
        "damage_severity": "minor",
        "major_failure": False,
        "dice": roll,
    }


def get_track_base_lap(track_name: str) -> float:
    """Get base lap time for a track."""
    return TRACK_BASE_LAP_TIMES.get(track_name.lower(), (88.0, 300))[0]


def simulate_race_with_pit_stops(
    track_name: str,
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
        random.seed(random_seed)

    # Create simulator
    sim = EnhancedRaceSimulator(
        track_name=track_name,
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
    r_value: Optional[float] = None,
    team_pr: Optional[float] = None,
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

    # Convert to probability (moderately reduced baseline)
    error_prob = base_error_rate * 1.7  # ~1.7-17% baseline range

    # Better overall package (higher R) should reduce mistakes
    if r_value is not None:
        r_norm = max(0.0, min(1.0, (r_value - 250.0) / 100.0))
        error_prob *= 1.0 - (0.18 * r_norm)

    # Higher team level (PR) should further reduce mistakes
    if team_pr is not None:
        pr_norm = max(0.0, min(1.0, (team_pr - 290.0) / 25.0))
        error_prob *= 1.0 - (0.12 * pr_norm)

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
    return max(0.8, min(22.0, error_prob))


# =============================================================================
# REAL-TIME LAPPING DETECTOR
# =============================================================================


@dataclass
class LappingEvent:
    """Event representing a lapping occurrence."""

    leader: str  # Driver doing the lapping
    lapped_driver: str  # Driver being lapped
    lap: int  # Lap when lapping occurred
    laps_down: int  # Number of laps down
    time_gap: float  # Time gap between drivers
    avg_lap_time: float  # Average lap time for reference


class RealTimeLappingDetector:
    """
    Real-time lapping detector following FIA regulations.

    FIA Rules:
    - A driver is lapped when the leader completes a full lap more than them
    - Lapped cars must not interfere with leading cars
    - At race end, lapped cars are ranked behind all cars that completed more laps
    """

    def __init__(self, base_lap_time: float = 90.0):
        self.base_lap_time = base_lap_time
        self.lapping_history: List[LappingEvent] = []
        self.driver_laps_down: Dict[str, int] = {}  # driver -> laps down

    def detect_lapping(
        self,
        results: Dict[str, Dict],
        current_lap: int,
        safety_car_active: bool = False,
    ) -> List[LappingEvent]:
        """
        Detect lapping situations in real-time.

        Args:
            results: Dictionary of driver results with cumulative_time and laps_completed
            current_lap: Current lap number
            safety_car_active: Whether safety car is currently active

        Returns:
            List of LappingEvent for any new lapping situations
        """
        events = []

        # Skip lapping detection during safety car (per FIA rules)
        if safety_car_active:
            return events

        if not results:
            return events

        # Find the current leader (most laps completed, then lowest cumulative time)
        active_results = {
            d: r for d, r in results.items() if r.get("laps_completed", 0) > 0
        }

        if not active_results:
            return events

        # Find leader: most laps completed, then lowest cumulative time
        leader = min(
            active_results.items(),
            key=lambda x: (-x[1]["laps_completed"], x[1]["cumulative_time"]),
        )[0]

        leader_result = active_results[leader]
        leader_laps = leader_result["laps_completed"]
        leader_time = leader_result["cumulative_time"]

        # Calculate average lap time from leader
        avg_lap_time = (
            leader_time / leader_laps if leader_laps > 0 else self.base_lap_time
        )

        # Check each driver for lapping
        for driver, result in active_results.items():
            if driver == leader:
                continue

            driver_laps = result["laps_completed"]
            driver_time = result["cumulative_time"]

            # Calculate time gap
            time_gap = driver_time - leader_time

            # FIA-compliant lapping classification:
            # A car is lapped when it has completed fewer laps than the leader.
            # Time gap is metadata only and must not determine laps_down directly.
            calculated_laps_down = max(0, leader_laps - driver_laps)

            # Get previous laps down for this driver
            previous_laps_down = self.driver_laps_down.get(driver, 0)

            # Check if this is a new lapping or increased laps down
            if calculated_laps_down > previous_laps_down:
                # New lapping event detected
                event = LappingEvent(
                    leader=leader,
                    lapped_driver=driver,
                    lap=current_lap,
                    laps_down=calculated_laps_down,
                    time_gap=time_gap,
                    avg_lap_time=avg_lap_time,
                )
                events.append(event)
                self.driver_laps_down[driver] = calculated_laps_down

        return events

    def get_laps_down(self, driver: str) -> int:
        """Get the number of laps a driver is down."""
        return self.driver_laps_down.get(driver, 0)

    def is_lapped(self, driver: str) -> bool:
        """Check if a driver has been lapped."""
        return self.driver_laps_down.get(driver, 0) > 0

    def get_effective_laps(self, driver: str, actual_laps: int) -> int:
        """
        Calculate effective laps for classification.

        FIA rule: Lapped cars are classified with reduced lap counts.
        """
        laps_down = self.driver_laps_down.get(driver, 0)
        return max(0, actual_laps - laps_down)


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
        self.vsc_activation_lap: Optional[int] = None
        self.sc_activation_lap: Optional[int] = None

        # Incident tracking
        self.active_incidents: List[Dict] = []
        self.penalties: Dict[str, List[Dict]] = defaultdict(list)

        # Blue flag states
        self.blue_flag_states: Dict[str, BlueFlagState] = {}

        # Lapped cars tracking
        self.lapped_cars: Dict[str, int] = {}  # driver_name -> num_laps_ahead
        self.lead_lap = set()  # Drivers on the lead lap

        # CHEQUERED FLAG - race finish tracking
        self.chequered_flag_shown = False
        self.chequered_flag_lap = None  # Lap when leader finished
        self.leader_finished = False
        self.driver_lap_deficit: Dict[
            str, int
        ] = {}  # driver_name -> laps behind leader at finish

        # FAULT DEGRADATION TRACKING - MODERN F1
        # Faults accumulate and degrade speed over the race
        self.driver_fault_degradation: Dict[str, float] = defaultdict(float)

        # MARKOV NOISE BIAS TRACKING - For driver "form" persistence
        # Drivers have good/bad form that carries over laps (Point 3 of noise control)
        self.driver_noise_bias: Dict[str, float] = defaultdict(float)

        # DNF (Did Not Finish) TRACKING
        # Tracks drivers who retired from the race
        # driver_name -> lap_dnfed
        self.dnf_drivers: Dict[str, int] = {}
        # driver_name -> retirement_reason
        self.retirement_reasons: Dict[str, str] = {}

        # WEATHER TRACKING
        # Weather integration state
        self.weather_integration: Optional[SimWeatherIntegration] = None
        self.current_weather_state: Optional[Any] = None
        self.weather_events: List[Dict] = []
        self.drs_enabled: bool = True  # DRS enabled by default
        self.last_weather_pit_decision: Dict[
            str, int
        ] = {}  # driver -> lap of last weather pit
        self.weather_pits_count: Dict[
            str, int
        ] = {}  # driver -> number of weather-triggered pit stops
        self.weather_pit_cooldown_laps: int = 8  # Minimum laps between weather pits
        self.max_weather_pits_per_race: int = (
            3  # Maximum weather-related pit stops per race
        )
        self.track_water_level: float = 0.0  # 0.0 (dry) -> 1.0 (flooded)
        self.track_water_history: List[Dict[str, Any]] = []

        # WEATHER VSC/SC TRACKING - Fix: track if weather VSC/SC has already been triggered
        # This prevents multiple triggers for the same weather event
        self.weather_vsc_triggered: bool = False
        self.weather_sc_triggered: bool = False
        self.last_weather_trigger_lap: int = 0  # Track lap of last weather trigger
        self.weather_trigger_cooldown: int = 5  # Minimum laps between weather triggers

        # RED FLAG DAMAGE TRACKING - For car repair mechanic
        # Tracks damage per driver for red flag repair calculations
        # Format: {"Verstappen": {"total_damage": 0.45, "type": "incident"}, ...}
        self.driver_damage: Dict[str, Dict] = {}

        # Red Flag Repair Manager
        from incidents.red_flag import RedFlagRepairManager

        self.red_flag_repair_manager = RedFlagRepairManager()

        # FRONT WING REPLACEMENT - Tracks front wing damage per driver
        # Format: {"Verstappen": {"damage": 0.35, "severity": "moderate", "source": "driver_error"}, ...}
        self.front_wing_damage: Dict[str, Dict] = {}

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
        self.narrative_config = NarrativeAssistConfig.get_config()
        self.narrative_balancer = ProbabilityBalancer()

        # Runtime narrative scaling (keeps intensity-respecting bounds)
        intensity = self.narrative_config.intensity or ""
        self._target_pace_boost = {
            "subtle": 0.0015,
            "moderate": 0.0032,
            "strong": 0.0052,
        }.get(intensity, 0.0)
        self._opponent_pace_penalty = {
            "subtle": 0.0009,
            "moderate": 0.0020,
            "strong": 0.0036,
        }.get(intensity, 0.0)
        self._target_pit_bonus_sec = {
            "subtle": 0.35,
            "moderate": 0.75,
            "strong": 1.25,
        }.get(intensity, 0.0)
        self._opponent_pit_penalty_sec = {
            "subtle": 0.15,
            "moderate": 0.35,
            "strong": 0.65,
        }.get(intensity, 0.0)

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

        # Initialize real-time lapping detector (FIA-compliant)
        self.lapping_detector = RealTimeLappingDetector(
            base_lap_time=self.base_lap_time
        )

        # Initialize unlapping manager
        self.unlapping_manager = UnlappingManager()

        # Initialize weather integration
        self.weather_integration = SimWeatherIntegration(
            gp_name=track_name,
            seed=random_seed,
        )
        self.race_state.weather_integration = self.weather_integration

        # Pit stop data
        self.pitlane_data = load_pitlane_time_data()

        # Load team PR values for race performance calculation
        from src.utils.config_loader import get_all_teams_pr

        self.team_pr_values = get_all_teams_pr(track_name)

        # Initialize front wing replacement manager
        from src.pit_stop.front_wing_replacement import FrontWingManager

        self.front_wing_manager = FrontWingManager()

        # Track simulation start time for relative timestamps
        self.simulation_start_time: Optional[datetime] = None

        # Vehicle fault check scheduling - dice roll determines next check lap
        # Initial check at lap 3, then per-driver dice determines next check interval
        self._next_vehicle_fault_check_lap_by_driver: Dict[str, int] = {
            driver: 3 for driver in self.driver_data.keys()
        }
        # Driver error check interval - per driver to avoid order bias in loop
        self._next_driver_error_check_lap_by_driver: Dict[str, int] = {
            driver: 3 for driver in self.driver_data.keys()
        }

        # =======================================================================
        # STRATEGIST SYSTEM INTEGRATION
        # =======================================================================
        # Get Strategist Manager (loads from JSON automatically)
        self.strategist_manager = get_manager()

        # Create Strategist Integration for Ferrari (protagonist team)
        self.strategist_integration = StrategistIntegration(
            team="Ferrari",
            seed=random_seed,
        )

        # Track strategic decisions for this race
        self.strategic_decisions: List[Dict[str, Any]] = []
        self.current_pace_mode: PaceMode = PaceMode.RACE
        self.last_strategist_lap_check: int = 0

        # Pit strategy tracking for dynamic pit decisions
        self.last_pit_decision_lap: int = 0
        self.ferrari_pit_strategy: Dict[
            str, List[int]
        ] = {}  # driver -> list of planned pit laps

        # Strategist integrations for all teams (not just Ferrari)
        self.team_strategist_integrations: Dict[str, StrategistIntegration] = {}
        self.team_last_pit_decision_lap: Dict[str, int] = {}

        # Initialize strategist for each team
        for team in set(self.driver_teams.values()):
            if team and team != "Unknown":
                try:
                    strategist_team = STRATEGIST_TEAM_ALIASES.get(team, team)
                    self.team_strategist_integrations[team] = StrategistIntegration(
                        team=strategist_team,
                        seed=random_seed,
                    )
                    self.team_last_pit_decision_lap[team] = 0
                except ValueError:
                    # No strategist found for this team
                    pass

        # =======================================================================
        # DRIVER SKILLS SYSTEM INTEGRATION
        # =======================================================================
        self.skill_manager: Optional[DriverSkillManager] = None
        self.skill_activations: deque[Dict[str, Any]] = deque(maxlen=1000)
        try:
            self.skill_manager = get_skill_manager()
            self.skill_manager.reset_for_new_race()
        except Exception as e:
            # Log warning and continue without skills - race can still run
            # Log warning using dice_logger if available, fallback to stderr
            if hasattr(self, "dice_logger") and self.dice_logger:
                self.dice_logger.log_roll(
                    lap=0,
                    driver="SYSTEM",
                    incident_type="initialization",
                    dice_type="warning",
                    dice_result=None,
                    outcome="skill_manager_init_failed",
                    race_time=0.0,
                    details={"error": str(e)},
                )
            else:
                import sys

                print(
                    f"Warning: Failed to initialize skill manager: {e}", file=sys.stderr
                )
            self.skill_manager = None

        # Verify that skills were loaded from CSV
        if self.skill_manager and not self.skill_manager.driver_skills:
            csv_path = getattr(
                self.skill_manager, "csv_path", "data/driver_ratings.csv"
            )
            import sys

            print(
                f"Warning: No driver skills loaded from {csv_path} - skills disabled",
                file=sys.stderr,
            )
            self.skill_manager = None

    def _get_drs_config(self, track_name: str) -> Optional[Dict[str, Any]]:
        """Get DRS configuration for the track."""
        # Try to get track config from DRS zones
        track_getter = DRS_TRACKS.get(track_name)
        if track_getter:
            return track_getter()
        return None

    def _apply_driver_skills(
        self,
        driver: str,
        base_r: float,
        lap: int,
        is_raining: bool = False,
        position: Optional[int] = None,
        results: Optional[Dict] = None,
    ) -> tuple[float, List[Dict[str, Any]]]:
        """
        Apply driver skills to modify R value for lap time calculation.

        Args:
            driver: Driver name
            base_r: Base R value
            lap: Current lap number
            is_raining: Whether it's raining
            position: Current race position (from previous lap)
            results: Race results dict for calculating gaps

        Returns:
            Tuple of (adjusted_r, skill_activations)
        """
        # Return base R if skill manager is not available
        if self.skill_manager is None:
            return base_r, []

        try:
            # Calculate gaps if position and results are available
            gap_to_ahead: Optional[float] = None
            gap_to_behind: Optional[float] = None
            if position is not None and results is not None:
                # Find driver ahead and behind
                sorted_drivers = sorted(
                    results.items(),
                    key=lambda x: (
                        -x[1].get("laps_completed", 0),
                        x[1].get("cumulative_time", float("inf")),
                    ),
                )
                for idx, (d, r) in enumerate(sorted_drivers):
                    if d == driver:
                        if idx > 0:
                            gap_to_ahead = r.get("cumulative_time", 0) - sorted_drivers[
                                idx - 1
                            ][1].get("cumulative_time", 0)
                        if idx < len(sorted_drivers) - 1:
                            gap_to_behind = sorted_drivers[idx + 1][1].get(
                                "cumulative_time", 0
                            ) - r.get("cumulative_time", 0)
                        break

            # Create skill context with available information
            context = SkillContext(
                session_type=SessionType.RACE,
                lap_number=lap,
                total_laps=self.num_laps if hasattr(self, "num_laps") else None,
                weather_condition=WeatherCondition.LIGHT_RAIN
                if is_raining
                else WeatherCondition.DRY,
                position=position,
                gap_to_ahead=gap_to_ahead,
                gap_to_behind=gap_to_behind,
                is_first_lap=(lap == 1),
                is_race_start=(lap <= 2),
            )

            # Get adjusted R value from skill manager
            adjusted_r, modifier, activations = self.skill_manager.get_adjusted_r_value(
                driver, base_r, context, self.get_relative_time()
            )

            # Convert activations to dict format for logging
            activation_dicts = [a.to_dict() for a in activations]

            return adjusted_r, activation_dicts
        except Exception as e:
            # Log error and return base R value gracefully
            import sys

            print(
                f"Warning: Failed to apply skills for {driver} on lap {lap}: {e}",
                file=sys.stderr,
            )
            return base_r, []

    def _create_driver_incident_from_skill(
        self,
        driver: str,
        lap: int,
        roll_result: int,
    ):
        """
        Create an incident caused by driver's skill (e.g., 总导演 skill).

        Args:
            driver: Driver who caused the incident
            lap: Current lap number
            roll_result: The dice roll result that triggered the incident
        """
        # Mark driver as DNF due to skill-triggered incident
        reason = (
            f"总导演 (The Director): Skill-triggered incident (roll: {roll_result})"
        )
        self.race_state.add_dnf(driver, lap, reason)

        # Log the incident
        self.dice_logger.log_roll(
            lap=lap,
            driver=driver,
            incident_type="skill_triggered_dnf",
            dice_type="d10",
            dice_result=roll_result,
            outcome="dnf",
            race_time=self.get_relative_time(),
            details={
                "skill_name": "总导演",
                "skill_name_en": "ChiefDirector",
                "reason": "Latifi's skill triggered an incident",
            },
        )

        print(
            f"\n*** INCIDENT: {driver} caused an incident due to 总导演 skill (roll: {roll_result}) ***"
        )

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

    def determine_starting_weather_dice_roll(self) -> Tuple[Any, str]:
        """
        Determine starting weather using dice rolls based on track precipitation rates.

        Uses d100 roll against track-specific rain probability to determine if race
        starts in wet conditions. Different tracks have different base rain chances
        (e.g., Silverstone/Britain ~18%, Spain ~15%, Singapore ~50%).

        Returns:
            Tuple of (initial_weather_state, weather_description)
        """
        # Get track info for precipitation data (month + climate aware)
        track_info = get_track_info(self.track_name)
        base_rain_chance = self._calculate_starting_rain_chance(track_info)

        # Convert to percentage for dice roll (0-100)
        rain_threshold = int(base_rain_chance * 100)

        # Roll d100 for weather determination
        weather_roll = roll_d100()

        # Determine if it's raining based on track-specific probability
        is_raining = weather_roll <= rain_threshold

        if is_raining:
            # Roll for rain intensity (d10)
            intensity_roll = roll_d10()
            if intensity_roll <= 4:
                rain_intensity = RainIntensity.LIGHT
                weather_desc = "Light rain at race start"
            elif intensity_roll <= 7:
                rain_intensity = RainIntensity.MODERATE
                weather_desc = "Moderate rain at race start"
            elif intensity_roll <= 9:
                rain_intensity = RainIntensity.HEAVY
                weather_desc = "Heavy rain at race start"
            else:
                rain_intensity = RainIntensity.TORRENTIAL
                weather_desc = "Torrential rain at race start - considering red flag"
        else:
            rain_intensity = RainIntensity.NONE
            # Roll for dry weather variation (d10)
            dry_roll = roll_d10()
            if dry_roll <= 6:
                weather_desc = "Clear skies at race start"
            elif dry_roll <= 9:
                weather_desc = "Partly cloudy at race start"
            else:
                weather_desc = "Overcast but dry at race start"

        # Log the dice roll
        self.dice_logger.log_roll(
            lap=0,
            driver="WEATHER_SYSTEM",
            incident_type="starting_weather_determination",
            dice_type="d100",
            dice_result=weather_roll,
            outcome="rain" if is_raining else "dry",
            race_time=0.0,
            details={
                "track": self.track_name,
                "base_rain_chance": base_rain_chance,
                "rain_threshold": rain_threshold,
                "weather_description": weather_desc,
                "rain_intensity": rain_intensity.name if is_raining else "NONE",
            },
        )

        # Initialize weather integration for the race
        race_duration_estimate = (self.num_laps * self.base_lap_time) / 60.0  # minutes
        weather_log = self.weather_integration.initialize_race(race_duration_estimate)

        # Get the initial weather from the generator
        initial_weather = weather_log.initial_weather

        # Override with dice-determined rain state for consistency
        if is_raining:
            initial_weather.rain_intensity = rain_intensity
            initial_weather.weather_type = self._map_rain_to_weather_type(
                rain_intensity
            )
            initial_weather.track_condition = TrackCondition.WET
            initial_weather.precipitation_probability = max(
                15.0, base_rain_chance * 100
            )
        else:
            initial_weather.rain_intensity = RainIntensity.NONE
            initial_weather.track_condition = TrackCondition.DRY
            initial_weather.precipitation_probability = base_rain_chance * 100

        self.race_state.current_weather_state = initial_weather
        self.race_state.track_water_level = {
            RainIntensity.NONE: 0.02,
            RainIntensity.LIGHT: 0.18,
            RainIntensity.MODERATE: 0.35,
            RainIntensity.HEAVY: 0.60,
            RainIntensity.TORRENTIAL: 0.85,
        }.get(initial_weather.rain_intensity, 0.02)

        return initial_weather, weather_desc

    def _calculate_starting_rain_chance(self, track_info: Dict[str, Any]) -> float:
        """Calculate effective starting rain chance with seasonal and climate adjustments."""
        base_chance = float(track_info.get("rain_chance", 0.25))
        climate = str(track_info.get("climate", "temperate")).lower()
        rainy_months = track_info.get("rainy_months", []) or []

        race_month = 5
        race_date = track_info.get("date")
        if isinstance(race_date, str):
            try:
                race_month = datetime.strptime(race_date, "%Y-%m-%d").month
            except ValueError:
                race_month = 5

        # Baseline dampening for race-start weather to avoid over-triggering wet starts
        chance = base_chance * 0.80

        # Seasonal adjustment: mild up in rainy season, down otherwise
        if race_month in rainy_months:
            chance *= 1.08
        else:
            chance *= 0.82

        # Mediterranean tracks are typically much drier in late spring/summer
        if climate == "mediterranean" and race_month in [5, 6, 7, 8, 9]:
            chance *= 0.50

        # Clamp to realistic bounds for race-start probability
        return max(0.005, min(0.45, chance))

    def _map_rain_to_weather_type(self, intensity: RainIntensity) -> WeatherType:
        """Map rain intensity to weather type."""
        mapping = {
            RainIntensity.NONE: WeatherType.CLEAR,
            RainIntensity.LIGHT: WeatherType.LIGHT_RAIN,
            RainIntensity.MODERATE: WeatherType.MODERATE_RAIN,
            RainIntensity.HEAVY: WeatherType.HEAVY_RAIN,
            RainIntensity.TORRENTIAL: WeatherType.TORRENTIAL_RAIN,
        }
        return mapping.get(intensity, WeatherType.CLEAR)

    def update_weather_for_lap(self, lap: int, race_time_minutes: float) -> Dict:
        """
        Update weather for the current lap and return weather effects.

        Args:
            lap: Current lap number
            race_time_minutes: Race time in minutes

        Returns:
            Dictionary with weather effects and state
        """
        if self.weather_integration is None:
            return {
                "lap_time_modifier": 0.0,
                "drs_enabled": True,
                "pit_for_weather": False,
            }

        # Get current weather from integration
        current_weather = self.weather_integration.get_current_weather(
            lap, race_time_minutes
        )
        self.race_state.current_weather_state = current_weather

        # Log weather for this lap
        lap_weather_data = self.weather_integration.log_lap_weather(
            lap, race_time_minutes
        )

        # Get lap time modifier
        lap_time_modifier = self.weather_integration.get_lap_time_modifier(
            current_weather
        )

        # Determine DRS availability
        drs_enabled = self._is_drs_enabled_in_weather(current_weather)
        self.race_state.drs_enabled = drs_enabled

        # Check for race control response
        rc_state = self.weather_integration.get_race_control_state(current_weather)

        # Determine if pit stop is recommended for weather
        recommended_tyre, pit_reason = self.weather_integration.get_recommended_tyre(
            current_weather
        )
        pit_for_weather = (
            recommended_tyre != "dry"
            and current_weather.track_condition != TrackCondition.DRY
        )

        # Check for significant weather changes
        weather_changed = False
        if len(self.race_state.weather_events) > 0:
            last_event = self.race_state.weather_events[-1]
            if last_event.get("weather_type") != current_weather.weather_type.value:
                weather_changed = True

        # Log weather event if significant change
        if weather_changed or lap == 1:
            self.race_state.weather_events.append(
                {
                    "lap": lap,
                    "race_time": race_time_minutes,
                    "weather_type": current_weather.weather_type.value,
                    "track_condition": current_weather.track_condition.value,
                    "rain_intensity": current_weather.rain_intensity.name,
                    "drs_enabled": drs_enabled,
                    "rc_state": rc_state.value,
                }
            )

            # Print weather update for significant changes
            if weather_changed:
                print(
                    f"\n*** Weather Change at Lap {lap}: {current_weather.weather_type.value} ***"
                )
                print(
                    f"    Track: {current_weather.track_condition.value}, DRS: {'Enabled' if drs_enabled else 'Disabled'}"
                )

        return {
            "lap_time_modifier": lap_time_modifier,
            "drs_enabled": drs_enabled,
            "pit_for_weather": pit_for_weather,
            "recommended_tyre": recommended_tyre,
            "rc_state": rc_state,
            "weather_type": current_weather.weather_type,
            "track_condition": current_weather.track_condition,
            "rain_intensity": current_weather.rain_intensity,
            "rain_probability": current_weather.precipitation_probability,
        }

    def _get_driver_current_tyre(self, driver_result: Dict[str, Any], lap: int) -> str:
        """Get driver's current tyre compound at the start of this lap."""
        pit_laps = driver_result.get("pit_laps", [])
        tyre_sequence = driver_result.get("tyre_sequence", [])
        if not tyre_sequence:
            return "MEDIUM"

        tyre_idx = sum(1 for pit_lap in pit_laps if pit_lap < lap)
        if tyre_idx >= len(tyre_sequence):
            tyre_idx = len(tyre_sequence) - 1
        return tyre_sequence[tyre_idx]

    def _apply_track_water_model(
        self,
        lap: int,
        weather_effects: Dict[str, Any],
        results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply track water accumulation + sweeping model.

        This models water build-up from rainfall and water clearing from drainage + cars
        repeatedly running through the racing line (扫水 effect).
        """
        adjusted = dict(weather_effects)
        rain_intensity = adjusted.get("rain_intensity", RainIntensity.NONE)

        rain_input_per_lap = {
            RainIntensity.NONE: 0.00,
            RainIntensity.LIGHT: 0.040,
            RainIntensity.MODERATE: 0.080,
            RainIntensity.HEAVY: 0.140,
            RainIntensity.TORRENTIAL: 0.220,
        }.get(rain_intensity, 0.00)

        active_drivers = [d for d in results if not self.race_state.is_dnf(d)]
        dry_count = 0
        intermediate_count = 0
        wet_count = 0
        for driver in active_drivers:
            tyre = self._get_driver_current_tyre(results[driver], lap)
            if tyre in {"SOFT", "MEDIUM", "HARD"}:
                dry_count += 1
            elif tyre == "INTERMEDIATE":
                intermediate_count += 1
            elif tyre == "WET":
                wet_count += 1

        natural_drainage = 0.015
        sweeping = dry_count * 0.003 + intermediate_count * 0.002 + wet_count * 0.0015
        if rain_intensity != RainIntensity.NONE:
            sweeping *= 0.55

        water_level = self.race_state.track_water_level
        water_level += rain_input_per_lap
        water_level -= natural_drainage
        water_level -= sweeping
        water_level = max(0.0, min(1.0, water_level))
        self.race_state.track_water_level = water_level

        if water_level < 0.08:
            modeled_track = TrackCondition.DRY
            modeled_recommended = "dry"
        elif water_level < 0.22:
            modeled_track = TrackCondition.DAMP
            modeled_recommended = "intermediate"
        elif water_level < 0.60:
            modeled_track = TrackCondition.WET
            modeled_recommended = "intermediate"
        else:
            modeled_track = TrackCondition.FLOODED
            modeled_recommended = "wet"

        # Hysteresis: avoid immediate flip-flop off rain tyres after one dry-ish lap
        if modeled_recommended == "dry" and water_level >= 0.12:
            modeled_recommended = "intermediate"

        adjusted["track_condition"] = modeled_track
        adjusted["recommended_tyre"] = modeled_recommended
        adjusted["pit_for_weather"] = modeled_recommended != "dry"
        adjusted["lap_time_modifier"] = adjusted.get("lap_time_modifier", 0.0) + (
            0.06 * water_level
        )

        self.race_state.track_water_history.append(
            {
                "lap": lap,
                "water_level": water_level,
                "rain_intensity": getattr(rain_intensity, "name", str(rain_intensity)),
                "track_condition": modeled_track.value,
                "recommended_tyre": modeled_recommended,
            }
        )

        return adjusted

    def _apply_fia_final_classification(
        self,
        results: Dict[str, Dict[str, Any]],
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Apply FIA-style final classification using leader chequered time."""
        if not results:
            return []

        # Leader = shortest cumulative race time among non-DNF cars
        non_dnf = [
            (driver, result)
            for driver, result in results.items()
            if not self.race_state.is_dnf(driver)
        ]
        if not non_dnf:
            non_dnf = list(results.items())

        leader_driver, leader_result = min(
            non_dnf, key=lambda item: item[1]["cumulative_time"]
        )
        leader_finish_time = float(leader_result["cumulative_time"])
        leader_laps = int(leader_result.get("laps_completed", 0))

        for driver, result in results.items():
            lap_times = result.get("lap_times", [])
            cumulative_checkpoints: List[float] = []
            running = 0.0
            for lap_time in lap_times:
                running += float(lap_time)
                cumulative_checkpoints.append(running)

            laps_crossed_at_flag = bisect_right(
                cumulative_checkpoints, leader_finish_time + 1e-9
            )
            actual_laps = int(result.get("laps_completed", len(cumulative_checkpoints)))
            cumulative_time = float(result.get("cumulative_time", float("inf")))

            # Estimate laps-at-flag from time delta vs representative lap time.
            # This prevents near-finish same-lap cars (who cross just after the leader)
            # from being incorrectly classified as +1 lap.
            representative_window = [float(t) for t in lap_times[-5:] if float(t) > 0]
            representative_lap = (
                sum(representative_window) / len(representative_window)
                if representative_window
                else 90.0
            )
            time_after_flag = max(0.0, cumulative_time - leader_finish_time)
            estimated_laps_behind = int(time_after_flag // max(1.0, representative_lap))
            laps_estimated_at_flag = max(0, actual_laps - estimated_laps_behind)
            laps_at_flag = max(laps_crossed_at_flag, laps_estimated_at_flag)

            if driver == leader_driver:
                laps_at_flag = leader_laps
            elif self.race_state.is_dnf(driver):
                laps_at_flag = min(laps_at_flag, actual_laps)

            classification_time = (
                cumulative_checkpoints[laps_at_flag - 1]
                if laps_at_flag > 0 and laps_at_flag <= len(cumulative_checkpoints)
                else float("inf")
            )

            laps_down = max(0, leader_laps - laps_at_flag)
            result["actual_laps"] = actual_laps
            result["effective_laps"] = laps_at_flag
            result["laps_down"] = laps_down
            result["is_lapped"] = laps_down > 0
            result["classification_time"] = classification_time

        final_results = sorted(
            results.items(),
            key=lambda item: (
                -item[1].get("effective_laps", 0),
                item[1].get("cumulative_time", float("inf")),
                item[1].get("classification_time", float("inf")),
            ),
        )

        # FIA-style interval: same-lap cars get time gap, lapped cars get lap deficit marker in print.
        leader_total_time = float(final_results[0][1].get("cumulative_time", 0.0))
        for position, (driver, result) in enumerate(final_results, 1):
            result["position"] = position
            if position == 1:
                result["interval"] = 0.0
            elif result.get("effective_laps", 0) == leader_laps:
                result["interval"] = (
                    float(result.get("cumulative_time", 0.0)) - leader_total_time
                )
            else:
                result["interval"] = float("nan")

        return final_results

    def _is_drs_enabled_in_weather(self, weather: Any) -> bool:
        """
        Determine if DRS should be enabled based on weather conditions.

        DRS is disabled when:
        - Rain intensity is MODERATE or higher
        - Track condition is WET or FLOODED
        - Race control has deployed VSC, SC, or Red Flag

        Returns:
            True if DRS is enabled, False otherwise
        """
        # Disable DRS in moderate or heavier rain
        if weather.rain_intensity in [
            RainIntensity.MODERATE,
            RainIntensity.HEAVY,
            RainIntensity.TORRENTIAL,
        ]:
            return False

        # Disable DRS on wet or flooded track
        if weather.track_condition in [TrackCondition.WET, TrackCondition.FLOODED]:
            return False

        return True

    def handle_weather_race_control(
        self, lap: int, weather_effects: Dict
    ) -> Optional[Dict]:
        """
        Handle race control responses to weather conditions.

        Returns race control event if VSC/SC/Red Flag should be deployed.

        FIX: Added tracking to prevent multiple triggers for the same weather event.
        Only triggers when weather changes from dry to wet, not continuously.
        """
        rc_state = weather_effects.get("rc_state", RaceControlState.GREEN)

        # Check if we already have active safety car periods
        if self.race_state.sc_active or self.race_state.vsc_active:
            return None

        # FIX: Check cooldown period between weather triggers
        # This prevents multiple triggers for the same weather event
        if (
            lap - self.race_state.last_weather_trigger_lap
            < self.race_state.weather_trigger_cooldown
        ):
            return None

        # Deploy safety car for heavy rain
        if rc_state == RaceControlState.SAFETY_CAR and weather_effects[
            "weather_type"
        ] in [WeatherType.HEAVY_RAIN, WeatherType.TORRENTIAL_RAIN]:
            if not self.race_state.weather_sc_triggered:
                self.race_state.weather_sc_triggered = True
                self.race_state.last_weather_trigger_lap = lap
                return self.handle_safety_car(lap, "Heavy rain conditions")

        # Deploy VSC for moderate rain with wet track
        if rc_state == RaceControlState.VSC:
            if not self.race_state.weather_vsc_triggered:
                self.race_state.weather_vsc_triggered = True
                self.race_state.last_weather_trigger_lap = lap
                return self.handle_vsc(lap, "Rain - wet track conditions")

        # Red flag for torrential rain
        if rc_state == RaceControlState.RED_FLAG:
            print(f"\n*** RED FLAG at Lap {lap}: Torrential rain conditions ***")
            self.race_state.red_flag_active = True
            self.race_state.last_weather_trigger_lap = lap

            # Handle car repairs during red flag
            self.handle_red_flag_repairs(lap)

            return {
                "type": "red_flag",
                "lap": lap,
                "reason": "Torrential rain - unsafe conditions",
            }

        # Reset trigger flags when weather clears (returns to GREEN)
        if rc_state == RaceControlState.GREEN:
            self.race_state.weather_vsc_triggered = False
            self.race_state.weather_sc_triggered = False

        return None

    def should_pit_for_weather(
        self, driver: str, lap: int, current_tyre: str, weather_effects: Dict
    ) -> Tuple[bool, str]:
        """
        Determine if a driver should pit for weather-related tyre change.

        Implements improved weather pit stop restrictions:
        - Cooldown period between weather pits (default 5 laps)
        - Maximum weather pits per race (default 3)
        - Track-specific rules for Monaco/Singapore

        Args:
            driver: Driver name
            lap: Current lap
            current_tyre: Current tyre compound
            weather_effects: Weather effects dictionary

        Returns:
            Tuple of (should_pit, reason)
        """
        recommended_tyre = weather_effects.get("recommended_tyre", "dry")
        track_condition = weather_effects.get("track_condition", TrackCondition.DRY)

        # Check track-specific rules for Monaco/Singapore
        track_rules = get_track_rules(self.track_name)
        team = self.driver_teams.get(driver, "")
        is_target = (
            self.narrative_config.enabled and self.narrative_config.is_target_team(team)
        )
        is_opponent = self.narrative_config.enabled and team and not is_target
        weather_pits_done = self.race_state.weather_pits_count.get(driver, 0)
        last_pit_lap = self.race_state.last_weather_pit_decision.get(driver, 0)
        laps_since_last_pit = lap - last_pit_lap

        # Skip if already on suitable tyre for current recommendation
        if recommended_tyre == "wet" and current_tyre == "WET":
            return False, ""
        if recommended_tyre == "intermediate" and current_tyre == "INTERMEDIATE":
            return False, ""
        if recommended_tyre == "dry" and current_tyre in ["SOFT", "MEDIUM", "HARD"]:
            return False, ""

        # Enforce minimum stint in rain tyres to avoid unrealistic back-to-back swaps
        min_stint_on_weather_tyre = 0
        if current_tyre == "INTERMEDIATE":
            min_stint_on_weather_tyre = 8
        elif current_tyre == "WET":
            min_stint_on_weather_tyre = 10

        if is_target:
            intensity_factor = self.narrative_config.strategy_bias
            if min_stint_on_weather_tyre > 0:
                min_stint_on_weather_tyre = max(
                    4,
                    int(
                        round(
                            min_stint_on_weather_tyre * (1.0 - 0.45 * intensity_factor)
                        )
                    ),
                )
        elif is_opponent:
            intensity_factor = self.narrative_config.opponent_debuff
            if min_stint_on_weather_tyre > 0:
                min_stint_on_weather_tyre = int(
                    round(min_stint_on_weather_tyre * (1.0 + 0.25 * intensity_factor))
                )

        if self.narrative_config.is_ultra():
            if is_target and min_stint_on_weather_tyre > 0:
                min_stint_on_weather_tyre = max(
                    2, int(round(min_stint_on_weather_tyre * 0.35))
                )
            elif is_opponent and min_stint_on_weather_tyre > 0:
                min_stint_on_weather_tyre = int(round(min_stint_on_weather_tyre * 1.4))

        if (
            min_stint_on_weather_tyre > 0
            and laps_since_last_pit < min_stint_on_weather_tyre
        ):
            emergency_switch = (
                track_condition == TrackCondition.FLOODED
                and current_tyre == "INTERMEDIATE"
            ) or (
                track_condition == TrackCondition.DRY
                and current_tyre == "WET"
                and laps_since_last_pit >= 6
            )
            if not emergency_switch:
                return False, ""

        # Check cooldown period (track-specific or default)
        cooldown_laps = max(
            self.race_state.weather_pit_cooldown_laps,
            track_rules.weather_pit_cooldown_laps,
        )
        if is_target:
            cooldown_laps = max(
                2,
                cooldown_laps - int(round(3 * self.narrative_config.strategy_bias)),
            )
        elif is_opponent:
            cooldown_laps = cooldown_laps + int(
                round(2 * self.narrative_config.opponent_debuff)
            )
        if self.narrative_config.is_ultra():
            if is_target:
                cooldown_laps = 1
            elif is_opponent:
                cooldown_laps += 3
        if laps_since_last_pit < cooldown_laps:
            return False, f""

        # Check maximum weather pits (track-specific or default)
        max_weather_pits = min(
            self.race_state.max_weather_pits_per_race, track_rules.max_weather_pits
        )
        if is_target:
            max_weather_pits += int(round(1.0 + self.narrative_config.strategy_bias))
        elif is_opponent:
            max_weather_pits = max(
                1,
                max_weather_pits
                - int(round(1 + self.narrative_config.opponent_debuff)),
            )
        if self.narrative_config.is_ultra():
            if is_target:
                max_weather_pits += 2
            elif is_opponent:
                max_weather_pits = max(1, max_weather_pits - 2)
        if weather_pits_done >= max_weather_pits:
            return False, f""

        # Check max pit stops limit for track (e.g., Monaco = 1)
        total_pits_done = len(
            [
                pl
                for pl in self.race_state.lap_times.get(driver, [])
                if isinstance(pl, dict) and pl.get("is_pit_lap", False)
            ]
        )
        if track_rules.max_pit_stops is not None:
            if total_pits_done >= track_rules.max_pit_stops:
                # Only allow in emergency (heavy rain on slicks)
                if not (
                    track_condition in [TrackCondition.WET, TrackCondition.FLOODED]
                    and current_tyre in ["SOFT", "MEDIUM", "HARD"]
                ):
                    return False, ""

        # Dry tyres on wet track - should pit for inters or wets
        if track_condition in [
            TrackCondition.WET,
            TrackCondition.FLOODED,
        ] and current_tyre in ["SOFT", "MEDIUM", "HARD"]:
            if is_opponent and track_condition == TrackCondition.WET:
                hesitation = min(0.65, 0.2 + self.narrative_config.opponent_debuff)
                if self.narrative_config.is_ultra():
                    hesitation = 0.85
                if random.random() < hesitation:
                    return False, ""

            if recommended_tyre == "wet":
                return (
                    True,
                    f"Pitting for Full Wet tyres - heavy rain (weather pit {weather_pits_done + 1}/{max_weather_pits})",
                )
            elif recommended_tyre == "intermediate":
                return (
                    True,
                    f"Pitting for Intermediate tyres - light rain (weather pit {weather_pits_done + 1}/{max_weather_pits})",
                )

        # Wet tyres on drying track - consider switching to dry
        if track_condition == TrackCondition.DRY and current_tyre in [
            "INTERMEDIATE",
            "WET",
        ]:
            if is_opponent:
                hold_chance = min(0.55, 0.1 + self.narrative_config.opponent_debuff)
                if self.narrative_config.is_ultra():
                    hold_chance = 0.8
                if random.random() < hold_chance:
                    return False, ""
            return (
                True,
                f"Pitting for dry tyres - track drying (weather pit {weather_pits_done + 1}/{max_weather_pits})",
            )

        return False, ""

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
            # Norris保持原始起步失误比例，其余车手适度下调
            start_mistake_gate_roll = None
            start_mistake_gate = True
            if driver != "Norris" and launch_roll in (1, 2):
                start_mistake_gate_roll = roll_d10()
                start_mistake_gate = start_mistake_gate_roll <= 5

            # 限制起步骰子的位置变化幅度：最多上升/下降2-3位
            # 每位差距约0.15秒，所以限制时间变化范围
            if launch_roll == 1 and start_mistake_gate:  # Major mistake - 最多下降2-3位
                start_delta += random.uniform(0.3, 0.5)  # 限制损失，约2-3位
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
                        "max_positions_lost": "2-3",
                        "mistake_gate_roll": start_mistake_gate_roll,
                    },
                )
            elif (
                launch_roll == 2 and start_mistake_gate
            ):  # Minor wheelspin - 最多下降1-2位
                start_delta += random.uniform(0.15, 0.3)  # 限制损失，约1-2位
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
                        "max_positions_lost": "1-2",
                        "mistake_gate_roll": start_mistake_gate_roll,
                    },
                )
            elif launch_roll >= 9:  # Excellent launch - 最多上升2-3位
                start_delta -= random.uniform(0.3, 0.45)  # 限制收益，约2-3位
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
            next_vehicle_fault_lap = self._next_vehicle_fault_check_lap_by_driver.get(
                driver, 3
            )
            if team_stability and lap == next_vehicle_fault_lap:
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

                    # Create front wing damage for moderate+ aerodynamic-related faults
                    # Roll d6 to determine if it's an aero fault (1-2 = aero)
                    component_roll = roll_d6()
                    if component_roll <= 2 and severity in (
                        "moderate",
                        "major",
                        "catastrophic",
                    ):
                        damage = self.front_wing_manager.create_damage_from_incident(
                            driver=driver,
                            incident_type="vehicle_fault",
                            incident_severity=severity,
                            lap=lap,
                        )
                        if damage:
                            self.race_state.front_wing_damage[driver] = damage.to_dict()

                    # After a fault, schedule next check sooner (more likely to have issues)
                    # Use d6: 1-3 laps
                    next_check = roll_d6()
                    self._next_vehicle_fault_check_lap_by_driver[driver] = (
                        lap + next_check
                    )

            # Schedule next vehicle fault check using dice if we've reached the check lap
            # and no fault occurred this lap
            if lap == self._next_vehicle_fault_check_lap_by_driver.get(driver, 3):
                # Use d10 to determine next check interval (1-10 laps)
                next_check_interval = roll_d10()
                self._next_vehicle_fault_check_lap_by_driver[driver] = (
                    lap + next_check_interval
                )

            # Driver error check - only check at intervals to avoid excessive errors
            if lap == self._next_driver_error_check_lap_by_driver.get(driver, 3):
                # Roll for driver error using personality-based probability
                error_roll = roll_d100()
                team = self.driver_teams.get(driver, "Unknown")
                team_pr = self.team_pr_values.get(team, 300.0)
                dr_value = float(
                    self.driver_data.get(driver, {}).get("DR_Value", 100.0)
                )
                driver_r_value = dr_value * team_pr / 100.0
                error_threshold = calculate_driver_error_probability(
                    driver,
                    position=driver_position,
                    is_fighting=is_fighting,
                    is_leading=is_leading,
                    r_value=driver_r_value,
                    team_pr=team_pr,
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
                    error_impact = roll_driver_error_impact()
                    error_severity = error_impact["damage_severity"]
                    incidents.append(
                        {
                            "type": "driver_error",
                            "driver": driver,
                            "lap": lap,
                            "error_type": error_impact["error_type"],
                            "severity": error_severity,
                            "impact_class": error_impact["impact_class"],
                            "major_failure": error_impact["major_failure"],
                            "impact_dice": error_impact["dice"],
                            "time_loss": error_impact["time_loss"],
                        }
                    )

                    # Create front wing damage from driver error
                    from src.pit_stop.front_wing_replacement import (
                        FrontWingManager,
                        FrontWingSeverity,
                    )

                    severity_map = {
                        "minor": FrontWingSeverity.MINOR,
                        "moderate": FrontWingSeverity.MODERATE,
                        "major": FrontWingSeverity.MAJOR,
                    }
                    front_wing_severity = severity_map.get(
                        error_severity, FrontWingSeverity.MINOR
                    )

                    damage = self.front_wing_manager.create_damage_from_incident(
                        driver=driver,
                        incident_type="driver_error",
                        incident_severity=error_severity,
                        lap=lap,
                    )

                    # Sync with race_state
                    if damage:
                        self.race_state.front_wing_damage[driver] = damage.to_dict()

                # Schedule next driver error check (every 4-6 laps to reduce frequency)
                next_error_check = random.randint(4, 6)
                self._next_driver_error_check_lap_by_driver[driver] = (
                    lap + next_error_check
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

            # Create front wing damage for both drivers involved in collision
            if not is_dnf:  # Only if not a DNF-causing collision
                for collision_driver in [driver_a, driver_b]:
                    damage = self.front_wing_manager.create_damage_from_incident(
                        driver=collision_driver,
                        incident_type="overtake_collision",
                        incident_severity=severity,
                        lap=lap,
                    )
                    if damage:
                        self.race_state.front_wing_damage[collision_driver] = (
                            damage.to_dict()
                        )

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
        attacker_team_pr = self.team_pr_values.get(attacker_team, 300.0)
        attacker_dr = float(attacker_info.get("DR_Value", 100.0))
        attacker_r_value = attacker_dr * attacker_team_pr / 100.0

        attacker_error_threshold = calculate_driver_error_probability(
            driver_a,
            position=position_a,
            is_fighting=True,
            is_leading=False,
            r_value=attacker_r_value,
            team_pr=attacker_team_pr,
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
        defender_team_pr = self.team_pr_values.get(defender_team, 300.0)
        defender_dr = float(defender_info.get("DR_Value", 100.0))
        defender_r_value = defender_dr * defender_team_pr / 100.0

        defender_error_threshold = calculate_driver_error_probability(
            driver_b,
            position=position_b,
            is_fighting=True,
            is_leading=False,
            r_value=defender_r_value,
            team_pr=defender_team_pr,
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
            attacker_impact = roll_driver_error_impact()
            return {
                "type": "driver_error",
                "lap": lap,
                "driver": driver_a,
                "cause": "overtake_attempt_failed",
                "impact_class": attacker_impact["impact_class"],
                "major_failure": attacker_impact["major_failure"],
                "time_loss": attacker_impact["time_loss"],
            }
        elif defender_error_roll <= defender_error_threshold:
            defender_impact = roll_driver_error_impact()
            return {
                "type": "driver_error",
                "lap": lap,
                "driver": driver_b,
                "cause": "overtake_defend_failed",
                "impact_class": defender_impact["impact_class"],
                "major_failure": defender_impact["major_failure"],
                "time_loss": defender_impact["time_loss"],
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
        self.race_state.sc_activation_lap = lap

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
        self.race_state.vsc_activation_lap = lap

        return {
            "type": "vsc",
            "lap": lap,
            "duration": vsc_laps,
            "reason": reason,
        }

    def handle_red_flag_repairs(self, lap: int) -> List[Dict]:
        """
        Handle car repairs during red flag period.

        Teams can attempt repairs on damaged cars while in the pits.
        The repair amount is determined by dice rolls based on damage severity.

        Args:
            lap: Current lap number

        Returns:
            List of repair results for drivers who were repaired
        """
        if not self.race_state.driver_damage:
            return []

        print(f"\n*** RED FLAG REPAIRS at Lap {lap} ***")
        print("Teams are working on damaged cars in the pits...")

        # Get repair manager from race state
        repair_manager = self.race_state.red_flag_repair_manager

        # Attempt repairs for all drivers with damage
        repair_results = repair_manager.repair_all_drivers(
            driver_damage=self.race_state.driver_damage,
            lap=lap,
        )

        # Log repairs to dice logger
        for result in repair_results:
            if result.get("repaired", False):
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=result["driver"],
                    incident_type="red_flag_repair",
                    dice_type="d100",
                    dice_result=result["dice_roll"],
                    outcome="repaired"
                    if result["fully_repaired"]
                    else "partially_repaired",
                    race_time=self.get_relative_time(),
                    details={
                        "damage_before": result["damage_before"],
                        "damage_after": result["damage_after"],
                        "actual_repair": result["actual_repair"],
                        "damage_tier": result["damage_tier"],
                    },
                )

                # Update driver damage state
                driver = result["driver"]
                if result["fully_repaired"]:
                    # Remove damage if fully repaired
                    if driver in self.race_state.driver_damage:
                        del self.race_state.driver_damage[driver]
                    # Also clear fault degradation
                    if driver in self.race_state.driver_fault_degradation:
                        self.race_state.driver_fault_degradation[driver] = 0.0
                else:
                    # Update damage amount
                    if driver in self.race_state.driver_damage:
                        self.race_state.driver_damage[driver]["total_damage"] = result[
                            "damage_after"
                        ]

                # Print repair info
                repair_msg = (
                    f"  {driver}: Rolled {result['dice_roll']}/100, "
                    f"repaired {result['actual_repair']:.1%} "
                    f"({result['damage_before']:.1%} -> {result['damage_after']:.1%})"
                )
                if result["fully_repaired"]:
                    repair_msg += " [FULLY REPAIRED]"
                print(repair_msg)

        # Print summary
        if repair_results:
            summary = repair_manager.get_repair_summary()
            print(
                f"\nRepair Summary: {summary['fully_repaired']} fully repaired, "
                f"{summary['partially_repaired']} partially repaired "
                f"(avg roll: {summary['average_dice_roll']})"
            )
        else:
            print("  No cars required repairs")

        return repair_results

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

    def _count_completed_pits(self, driver_result: Dict[str, Any], lap: int) -> int:
        pit_laps = driver_result.get("pit_laps", [])
        return sum(1 for pit_lap in pit_laps if pit_lap < lap)

    def _apply_immediate_team_pit(self, team: str, lap: int, results: Dict[str, Dict]):
        """Apply immediate SC/VSC pit response for all active drivers in a team."""
        track_rules = get_track_rules(self.track_name)
        max_bring_forward_laps = 10

        for driver_name, driver_team in self.driver_teams.items():
            if driver_team != team or driver_name not in results:
                continue
            if self.race_state.is_dnf(driver_name):
                continue

            pit_laps = results[driver_name].get("pit_laps", [])
            if lap in pit_laps:
                continue

            future_pits = sorted([pl for pl in pit_laps if pl >= lap])
            if not future_pits:
                continue

            next_planned_pit = future_pits[0]
            if next_planned_pit - lap > max_bring_forward_laps:
                continue

            last_pit_lap = max([pl for pl in pit_laps if pl < lap], default=0)
            completed_pits = self._count_completed_pits(results[driver_name], lap)
            is_allowed, _ = track_rules.is_pit_allowed(
                current_lap=lap,
                last_pit_lap=last_pit_lap,
                pit_stops_completed=completed_pits,
                is_weather_related=False,
                weather_pits_count=0,
            )
            if not is_allowed:
                continue

            idx = pit_laps.index(next_planned_pit)
            pit_laps[idx] = lap

            results[driver_name]["pit_laps"] = sorted(set(pit_laps))

    def _apply_sc_pack_tightening(
        self,
        sorted_drivers: List[Tuple[str, float]],
        results: Dict[str, Dict],
    ) -> List[Tuple[str, float]]:
        """Apply SC field compression so the pack reforms behind the leader."""
        if not self.race_state.sc_active or not sorted_drivers:
            return sorted_drivers

        leader, leader_time = sorted_drivers[0]
        adjusted = [(leader, leader_time)]
        previous_time = leader_time

        for driver, _ in sorted_drivers[1:]:
            raw_time = results[driver]["cumulative_time"]
            target_gap = max(0.2, 0.8 + random.uniform(-0.15, 0.15))
            tightened_time = min(raw_time, previous_time + target_gap)
            if tightened_time <= previous_time:
                tightened_time = previous_time + 0.2

            results[driver]["cumulative_time"] = tightened_time
            adjusted.append((driver, tightened_time))
            previous_time = tightened_time

        return adjusted

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
        results: Optional[Dict] = None,
    ) -> Dict:
        """Simulate a single lap for a driver."""

        # Check for pit stop
        pit_time = 0.0
        new_tyre = current_tyre
        front_wing_replacement_time = 0.0
        front_wing_replaced = False

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

            # SC/VSC pit benefit: pit-lane time loss is reduced during neutralized periods.
            if self.race_state.sc_active:
                track_pit_time = max(8.0, track_pit_time - 10.0)
            elif self.race_state.vsc_active:
                track_pit_time = max(8.0, track_pit_time - 6.0)

            pit_time = track_pit_time + tire_change_time

            # Check for front wing replacement
            front_wing_result = self.front_wing_manager.attempt_replacement(driver, lap)

            if front_wing_result.replaced:
                front_wing_replacement_time = front_wing_result.total_time
                front_wing_replaced = True
                pit_time += front_wing_replacement_time

                # Log front wing replacement decision (first dice roll)
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type="front_wing_replacement",
                    dice_type="d10",
                    dice_result=front_wing_result.d10_roll,
                    outcome="replaced",
                    race_time=self.get_relative_time(),
                    details={
                        "severity": front_wing_result.severity.value,
                        "threshold": front_wing_result.threshold,
                        "extra_time": round(front_wing_replacement_time, 2),
                    },
                )

                # Also sync with race_state front_wing_damage
                if driver in self.race_state.front_wing_damage:
                    self.race_state.front_wing_damage[driver]["replaced"] = True
                    self.race_state.front_wing_damage[driver]["replacement_lap"] = lap
            elif (
                front_wing_result.severity.value != "minor"
            ):  # Log skipped replacement for moderate+
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type="front_wing_replacement",
                    dice_type="d10",
                    dice_result=front_wing_result.d10_roll,
                    outcome="skipped",
                    race_time=self.get_relative_time(),
                    details={
                        "severity": front_wing_result.severity.value,
                        "threshold": front_wing_result.threshold,
                        "reason": "roll_below_threshold",
                    },
                )

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
                    "front_wing_replaced": front_wing_replaced,
                    "front_wing_time": round(front_wing_replacement_time, 2)
                    if front_wing_replaced
                    else 0.0,
                },
            )

        # ===================================================================
        # APPLY DRIVER SKILLS
        # ===================================================================
        # Get weather condition for skill context
        is_raining = False
        current_weather = getattr(self.race_state, "current_weather_state", None)
        if current_weather is not None:
            try:
                is_raining = current_weather.rain_intensity != RainIntensity.NONE
            except Exception:
                is_raining = False

        # Get current race position from race_state
        position = (
            self.race_state.get_position(driver)
            if hasattr(self.race_state, "get_position")
            else None
        )

        # Apply skills to get adjusted R value (returns base R if skills disabled)
        adjusted_r, skill_activations = self._apply_driver_skills(
            driver, driver_info["R_Value"], lap, is_raining, position, results
        )

        # Log skill activations and handle extra_dice_required
        if skill_activations:
            for activation in skill_activations:
                self.skill_activations.append(activation)
                self.dice_logger.log_roll(
                    lap=lap,
                    driver=driver,
                    incident_type="skill_activation",
                    # Use "skill_effect" to indicate this is not a dice roll
                    dice_type="skill_effect",
                    # No dice roll for passive skill effects - magnitude is direct effect value
                    dice_result=None,
                    outcome=activation.get("skill_name_cn", "unknown"),
                    race_time=self.get_relative_time(),
                    details={
                        "skill_name_en": activation.get("skill_name_en"),
                        "effect_description": activation.get("effect_description"),
                        "r_modifier": activation.get("r_modifier"),
                        "is_passive_effect": True,
                    },
                )

                # Handle extra_dice_required (e.g., incident creation)
                extra_dice = activation.get("extra_dice_required")
                if extra_dice and extra_dice.get("type") == "incident_caused":
                    # Create an incident for the driver (总导演 skill)
                    self._create_driver_incident_from_skill(
                        driver, lap, extra_dice.get("result", 0)
                    )
                elif extra_dice and extra_dice.get("type") == "chief_director_incident":
                    # Handle 总导演 incident - only affect specified drivers
                    will_interfere = extra_dice.get("will_interfere", False)
                    affected_drivers = extra_dice.get("affected_drivers", [driver])

                    if will_interfere:
                        # Only create incidents for affected drivers (Latifi + overtaking/blue flag)
                        for affected_driver in affected_drivers:
                            if affected_driver in self.driver_data:
                                self._create_driver_incident_from_skill(
                                    affected_driver,
                                    lap,
                                    extra_dice.get("interference_roll", 0),
                                )

        # Calculate base lap time using R = DR * PR / 100 formula
        team = self.driver_teams.get(driver, "Unknown")
        team_pr = self.team_pr_values.get(team, 300.0)  # Default PR if not found

        # Get driver's DR value
        dr_value = driver_info.get("DR_Value", 100.0)

        # Apply hidden R compensation for #2 drivers
        # Calculate team leader R values once per race
        if not hasattr(self, "_team_leader_r_values"):
            self._team_leader_r_values = _get_team_leader_r_values_embedded(
                self.driver_data
            )

        team_leader_r = self._team_leader_r_values.get(team, dr_value * team_pr / 100.0)
        is_num2 = _is_number_2_driver_embedded(driver, self.driver_data)

        base_r = dr_value * team_pr / 100.0
        team_tier = _get_team_tier(team)
        compensation_value, gap_to_leader = _calculate_compensated_r_core(
            base_r, team_leader_r, team_tier, is_num2, driver
        )

        r_for_laptime = base_r + compensation_value
        r_for_degradation = base_r  # Original R for degradation

        if compensation_value > 0:
            print(
                f"  [Compensation] {driver}: +{compensation_value:.3f} R ({team_tier} tier)"
            )

        # Calculate lap time using compensated R value
        # R for lap time = compensated DR * PR / 100
        compensated_dr_for_laptime = r_for_laptime * 100.0 / team_pr
        base_lap_time = calculate_base_lap_time(
            compensated_dr_for_laptime, team_pr, self.track_name
        )

        # Calculate degradation - PR (car) affects tire management
        # Better car = better tire management = slower degradation
        r_max = max(d["R_Value"] for d in self.driver_data.values())

        # Get PR range for degradation calculation
        if self.team_pr_values:
            pr_min_val = min(self.team_pr_values.values())
            pr_max_val = max(self.team_pr_values.values())
        else:
            pr_min_val, pr_max_val = 290, 310

        degradation = calculate_degradation_with_cliff(
            lap_count_on_tyre,
            current_tyre,
            driver_info["R_Value"],
            r_max,
            self.track_chars,
            len(pit_laps),
            team_pr,
            pr_min_val,
            pr_max_val,
        )

        # Calculate noise based on DR (driver stability/consistency)
        dr_values = [d["DR_Value"] for d in self.driver_data.values()]
        dr_min = min(dr_values)
        dr_max = max(dr_values)

        # Get previous bias for this driver (Markov process state)
        previous_bias = self.race_state.driver_noise_bias.get(driver, 0.0)

        # Calculate noise std based on DR - higher DR = more consistent = lower noise
        noise_std, new_bias = calculate_dr_based_std(
            driver_info["DR_Value"],
            dr_min,
            dr_max,
            0.08,
            previous_bias,
            markov_factor=0.6,
            team_pr=team_pr,
            pr_min=pr_min_val,
            pr_max=pr_max_val,
        )

        # Update bias for next lap (Markov chain state)
        self.race_state.driver_noise_bias[driver] = new_bias

        # Generate lap time with Markov bias as mean shift
        # Top drivers maintain consistency better due to lower variance
        lap_noise = np.random.normal(new_bias, noise_std)
        compound_pace_delta = get_tyre_pace_delta_seconds(current_tyre)
        lap_time = base_lap_time + compound_pace_delta + degradation * 10 + lap_noise

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
                # Monaco-specific: 1-stop strategy dominant (Fix 2c)
                # Real F1: Almost all teams use 1-stop at Monaco due to low tire wear
                # and long pit lane (~18 seconds). Two stops are extremely rare but possible.
                if is_monaco:
                    # 95% chance of 1-stop, 5% chance of 2-stop (rare but interesting scenarios)
                    strategy = random.choices(["1", "2"], weights=[0.95, 0.05])[0]
                else:
                    strategy = determine_pit_strategy_with_feedback(
                        self.track_name,
                        self.pit_data,
                        team=team,
                    )

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
                    "tyre_compounds_set": tyre_compounds_set,
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
                "laps_completed": 0,
                "interval": 0.0,
                # FIA Lapping fields (real-time tracking)
                "laps_down": 0,  # Number of laps behind the leader
                "is_lapped": False,  # Whether driver has been lapped
                "actual_laps": 0,  # Actual physical laps completed
                "effective_laps": 0,  # Effective laps for classification
            }

            # Get team strategy
            team = self.driver_teams.get(driver, "Unknown")
            if team in team_strategies:
                results[driver]["pit_laps"] = generate_pit_laps(
                    self.track_name, team_strategies[team]["strategy"], self.pit_data
                )
                results[driver]["tyre_sequence"] = generate_individual_tyre_sequence(
                    team_strategies[team]["tyre_compounds_set"]
                )
            else:
                strategy = determine_pit_strategy_with_feedback(
                    self.track_name,
                    self.pit_data,
                    team=team,
                )
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
                results[driver]["tyre_sequence"] = [
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

        # Initialize weather with dice-based determination
        initial_weather, weather_desc = self.determine_starting_weather_dice_roll()
        print(f"\n=== Weather: {weather_desc} ===")
        print(
            f"    Track: {self.track_name}, Rain Chance: {get_track_info(self.track_name).get('rain_chance', 0.25) * 100:.1f}%"
        )

        # Main race loop
        print(f"\n=== Starting Race (Lap 1 to {self.num_laps}) ===")

        lap = 1
        while lap <= self.num_laps:
            self.race_state.current_lap = lap

            # Get Ferrari driver (protagonist) for strategist decisions
            ferrari_drivers = [
                d for d, t in self.driver_teams.items() if t == "Ferrari"
            ]

            if lap % 10 == 0:
                print(f"  Lap {lap}/{self.num_laps}...")

            # Update weather for this lap
            race_time_minutes = self.get_relative_time() / 60.0
            weather_effects = self.update_weather_for_lap(lap, race_time_minutes)
            weather_effects = self._apply_track_water_model(
                lap, weather_effects, results
            )

            # Handle race control responses to weather
            weather_rc_event = self.handle_weather_race_control(lap, weather_effects)
            if weather_rc_event:
                print(f"  Weather-triggered: {weather_rc_event['reason']}")

            # ===================================================================
            # STRATEGIST HOOK: Weather Response Decision
            # ===================================================================
            # Check if it's raining using rain_intensity enum from weather_effects
            rain_intensity = weather_effects.get("rain_intensity", RainIntensity.NONE)
            if ferrari_drivers and rain_intensity != RainIntensity.NONE:
                # Update strategist context with current race state
                ferrari_driver = ferrari_drivers[0]
                ferrari_pos = (
                    self.race_state.get_position(ferrari_driver)
                    if hasattr(self.race_state, "get_position")
                    else results[ferrari_driver].get("position", 10)
                )

                # Get tyre life for Ferrari driver
                ferrari_tyre_life = lap_count_on_tyre = (
                    lap
                    - sum(1 for pl in results[ferrari_driver]["pit_laps"] if pl < lap)
                    if ferrari_driver in results
                    else 0
                )

                is_wet = rain_intensity != RainIntensity.NONE
                rain_prob = weather_effects.get("rain_probability", 0.0)
                rain_eta = None  # Not currently available from weather system

                # Create race context for strategist
                self.strategist_integration.update_context(
                    track_name=self.track_name,
                    current_lap=lap,
                    total_laps=self.num_laps,
                    race_position=ferrari_pos,
                    pit_stops_completed=self._count_completed_pits(
                        results[ferrari_driver], lap
                    )
                    if ferrari_driver in results
                    else 0,
                    tyre_life=ferrari_tyre_life,
                    current_tyre=results[ferrari_driver]["tyre_sequence"][
                        min(
                            sum(
                                1
                                for pl in results[ferrari_driver]["pit_laps"]
                                if pl < lap
                            ),
                            len(results[ferrari_driver]["tyre_sequence"]) - 1,
                        )
                    ]
                    if ferrari_driver in results
                    else "UNKNOWN",
                    is_wet=is_wet,
                    rain_eta=rain_eta,
                    is_sc_active=self.race_state.sc_active,
                    is_vsc_active=self.race_state.vsc_active,
                )

                # Make weather decision
                weather_decision = self.strategist_integration.on_weather_decision(
                    self.strategist_integration.state.current_context,
                    rain_probability=rain_prob,
                    rain_eta=rain_eta,
                )

                if weather_decision:
                    self.strategic_decisions.append(
                        {
                            "lap": lap,
                            "decision_type": "weather_response",
                            "roll": weather_decision.get("roll"),
                            "outcome": weather_decision.get("outcome"),
                            "recommended_action": weather_decision.get(
                                "recommended_action"
                            ),
                            "timing_offset": weather_decision.get("timing_offset"),
                        }
                    )
                    print(
                        f"  [STRATEGIST] Weather decision: {weather_decision.get('recommended_action')} (roll: {weather_decision.get('roll')}, outcome: {weather_decision.get('outcome')})"
                    )

            # Check for random VSC/SC deployment (except first few laps and not during weather events)
            if (
                lap > 3
                and not self.race_state.sc_active
                and not self.race_state.vsc_active
                and not weather_rc_event
            ):
                sc_roll = roll_d100()
                if sc_roll >= 98:  # 2% chance of SC
                    reason = "debris" if sc_roll == 98 else "incident"
                    self.handle_safety_car(lap, reason)
                elif sc_roll >= 95:  # 3% chance of VSC
                    self.handle_vsc(lap, "debris")

            # ===================================================================
            # STRATEGIST HOOK: SC/VSC Response Decision
            # ===================================================================
            # Check if SC or VSC was just deployed or is ending
            sc_deployed = self.race_state.sc_active
            vsc_deployed = self.race_state.vsc_active

            is_sc_response_window = (
                sc_deployed and self.race_state.sc_activation_lap == lap
            )
            is_vsc_response_window = (
                vsc_deployed and self.race_state.vsc_activation_lap == lap
            )

            if (is_sc_response_window or is_vsc_response_window) and ferrari_drivers:
                ferrari_driver = ferrari_drivers[0]
                ferrari_pos = (
                    results[ferrari_driver].get("position", 10)
                    if ferrari_driver in results
                    else 10
                )
                laps_until_end = self.num_laps - lap

                # Update context and make SC decision
                self.strategist_integration.update_context(
                    track_name=self.track_name,
                    current_lap=lap,
                    total_laps=self.num_laps,
                    race_position=ferrari_pos,
                    pit_stops_completed=self._count_completed_pits(
                        results[ferrari_driver], lap
                    )
                    if ferrari_driver in results
                    else 0,
                    tyre_life=lap
                    - sum(1 for pl in results[ferrari_driver]["pit_laps"] if pl < lap)
                    if ferrari_driver in results
                    else 0,
                    current_tyre=results[ferrari_driver]["tyre_sequence"][
                        min(
                            sum(
                                1
                                for pl in results[ferrari_driver]["pit_laps"]
                                if pl < lap
                            ),
                            len(results[ferrari_driver]["tyre_sequence"]) - 1,
                        )
                    ]
                    if ferrari_driver in results
                    else "UNKNOWN",
                    is_wet=False,
                    rain_eta=None,
                    is_sc_active=sc_deployed,
                    is_vsc_active=vsc_deployed,
                )

                sc_decision = self.strategist_integration.on_sc_decision(
                    self.strategist_integration.state.current_context,
                    is_vsc=vsc_deployed,
                    laps_until_end=laps_until_end,
                )

                if sc_decision:
                    self.strategic_decisions.append(
                        {
                            "lap": lap,
                            "decision_type": "sc_response"
                            if not vsc_deployed
                            else "vsc_response",
                            "roll": sc_decision.get("roll"),
                            "outcome": sc_decision.get("outcome"),
                            "recommended_action": sc_decision.get("recommended_action"),
                        }
                    )
                    print(
                        f"  [STRATEGIST] {'SC' if sc_deployed else 'VSC'} response: {sc_decision.get('recommended_action')} (roll: {sc_decision.get('roll')})"
                    )

                    if sc_decision.get("pit_recommendation", False) and sc_decision.get(
                        "recommended_action"
                    ) in {"PIT_NOW", "PIT_NOW_BONUS", "PIT_OR_STAY"}:
                        self._apply_immediate_team_pit("Ferrari", lap, results)

            # Apply SC/VSC response for all strategist-enabled teams
            if is_sc_response_window or is_vsc_response_window:
                for team, strategist in self.team_strategist_integrations.items():
                    if team == "Ferrari":
                        continue

                    team_driver = None
                    for driver_name, driver_team in self.driver_teams.items():
                        if driver_team == team and driver_name in results:
                            team_driver = driver_name
                            break

                    if not team_driver:
                        continue

                    driver_result = results[team_driver]
                    completed_pits = self._count_completed_pits(driver_result, lap)
                    current_idx = min(
                        completed_pits,
                        max(0, len(driver_result.get("tyre_sequence", [])) - 1),
                    )

                    strategist.update_context(
                        track_name=self.track_name,
                        current_lap=lap,
                        total_laps=self.num_laps,
                        race_position=driver_result.get("position", 10),
                        pit_stops_completed=completed_pits,
                        tyre_life=lap
                        - sum(1 for pl in driver_result["pit_laps"] if pl < lap),
                        current_tyre=driver_result["tyre_sequence"][current_idx]
                        if driver_result.get("tyre_sequence")
                        else "MEDIUM",
                        is_wet=False,
                        rain_eta=None,
                        is_sc_active=sc_deployed,
                        is_vsc_active=vsc_deployed,
                    )

                    team_sc_decision = strategist.on_sc_decision(
                        strategist.state.current_context,
                        is_vsc=vsc_deployed,
                        laps_until_end=self.num_laps - lap,
                    )

                    if (
                        team_sc_decision
                        and team_sc_decision.get("pit_recommendation", False)
                        and team_sc_decision.get("recommended_action")
                        in {
                            "PIT_NOW",
                            "PIT_NOW_BONUS",
                            "PIT_OR_STAY",
                        }
                    ):
                        self._apply_immediate_team_pit(team, lap, results)

            # Process safety car laps
            if self.race_state.sc_active:
                self.race_state.sc_laps_remaining -= 1
                if self.race_state.sc_laps_remaining <= 0:
                    self.race_state.sc_active = False
                    self.race_state.sc_activation_lap = None
                    print(f"  *** Safety Car ends at lap {lap} ***")

            if self.race_state.vsc_active:
                self.race_state.vsc_laps_remaining -= 1
                if self.race_state.vsc_laps_remaining <= 0:
                    self.race_state.vsc_active = False
                    self.race_state.vsc_activation_lap = None

            # Check for incidents every lap
            if lap > 2:
                incidents = self.check_for_incidents(lap, list(self.driver_data.keys()))
                for incident in incidents:
                    results[incident["driver"]]["incidents"].append(incident)

            # Simulate each driver
            lap_times_this_lap = {}

            # ===================================================================
            # STRATEGIST HOOK: Periodic Pace Management (every 5 laps)
            # ===================================================================
            if lap - self.last_strategist_lap_check >= 5 and ferrari_drivers:
                self.last_strategist_lap_check = lap

                ferrari_driver = ferrari_drivers[0]
                ferrari_pos = (
                    results[ferrari_driver].get("position", 10)
                    if ferrari_driver in results
                    else 10
                )

                self.strategist_integration.update_context(
                    track_name=self.track_name,
                    current_lap=lap,
                    total_laps=self.num_laps,
                    race_position=ferrari_pos,
                    pit_stops_completed=self._count_completed_pits(
                        results[ferrari_driver], lap
                    )
                    if ferrari_driver in results
                    else 0,
                    tyre_life=lap
                    - sum(1 for pl in results[ferrari_driver]["pit_laps"] if pl < lap)
                    if ferrari_driver in results
                    else 0,
                    current_tyre=results[ferrari_driver]["tyre_sequence"][
                        min(
                            sum(
                                1
                                for pl in results[ferrari_driver]["pit_laps"]
                                if pl < lap
                            ),
                            len(results[ferrari_driver]["tyre_sequence"]) - 1,
                        )
                    ]
                    if ferrari_driver in results
                    else "UNKNOWN",
                    is_wet=False,
                    rain_eta=None,
                    is_sc_active=self.race_state.sc_active,
                    is_vsc_active=self.race_state.vsc_active,
                )

                # Decide pace mode
                pace_decision = self.strategist_integration.on_pace_decision(
                    self.strategist_integration.state.current_context,
                    requested_mode=PaceMode.RACE,
                )

                if pace_decision:
                    self.strategic_decisions.append(
                        {
                            "lap": lap,
                            "decision_type": "pace_management",
                            "roll": pace_decision.get("roll"),
                            "outcome": pace_decision.get("outcome"),
                            "selected_mode": pace_decision.get("selected_mode"),
                            "speed_modifier": pace_decision.get("speed_modifier"),
                        }
                    )
                    # Store pace mode for lap time calculations
                    self.current_pace_mode = PaceMode(
                        pace_decision.get("selected_mode", "race")
                    )
                    print(
                        f"  [STRATEGIST] Pace decision: {pace_decision.get('selected_mode')} (roll: {pace_decision.get('roll')})"
                    )

            # ===================================================================
            # STRATEGIST HOOK: Dynamic Pit Stop Decision (when approaching pit window)
            # ===================================================================
            # Process pit decisions for ALL teams that have strategist integrations
            for team, strategist in self.team_strategist_integrations.items():
                # Find the first driver from this team
                team_driver = None
                for driver_name, driver_team in self.driver_teams.items():
                    if driver_team == team and driver_name in results:
                        team_driver = driver_name
                        break

                if not team_driver:
                    continue

                driver_result = results[team_driver]
                planned_pits = driver_result.get("pit_laps", [])

                # Find the next planned pit lap
                next_pit_lap = None
                for pit_lap in planned_pits:
                    if pit_lap > lap:
                        next_pit_lap = pit_lap
                        break

                # Check if we're approaching pit window (within 3 laps)
                if next_pit_lap and lap >= next_pit_lap - 3:
                    # Check if we already made a pit decision recently for this team
                    last_decision = self.team_last_pit_decision_lap.get(team, 0)
                    if lap - last_decision >= 3:
                        driver_pos = driver_result.get("position", 10)

                        # Update context for pit decision
                        strategist.update_context(
                            track_name=self.track_name,
                            current_lap=lap,
                            total_laps=self.num_laps,
                            race_position=driver_pos,
                            pit_stops_completed=self._count_completed_pits(
                                driver_result, lap
                            ),
                            tyre_life=lap - sum(1 for pl in planned_pits if pl < lap),
                            current_tyre=driver_result["tyre_sequence"][
                                min(
                                    sum(1 for pl in planned_pits if pl < lap),
                                    len(driver_result["tyre_sequence"]) - 1,
                                )
                            ],
                            is_wet=weather_effects.get(
                                "track_condition", TrackCondition.DRY
                            )
                            != TrackCondition.DRY,
                            rain_eta=None,
                            is_sc_active=self.race_state.sc_active,
                            is_vsc_active=self.race_state.vsc_active,
                        )

                        # Make pit stop decision
                        pit_decision = strategist.on_pit_stop_decision(
                            strategist.state.current_context,
                            is_undercut=False,
                        )

                        if pit_decision:
                            self.strategic_decisions.append(
                                {
                                    "lap": lap,
                                    "decision_type": f"pit_timing_{team}",
                                    "roll": pit_decision.get("roll"),
                                    "outcome": pit_decision.get("outcome"),
                                    "optimal_pit_lap": pit_decision.get(
                                        "optimal_pit_lap"
                                    ),
                                    "modifier_total": pit_decision.get(
                                        "modifier_total"
                                    ),
                                }
                            )

                            # Get the recommended pit lap from strategist
                            recommended_pit_lap = pit_decision.get("optimal_pit_lap")

                            # Adjust the pit lap if it's different from planned
                            if (
                                recommended_pit_lap
                                and recommended_pit_lap != next_pit_lap
                            ):
                                # Modify the pit_laps list for this driver
                                pit_idx = planned_pits.index(next_pit_lap)
                                planned_pits[pit_idx] = recommended_pit_lap
                                print(
                                    f"  [STRATEGIST - {team}] Pit decision: Modified next pit from lap {next_pit_lap} to {recommended_pit_lap} (roll: {pit_decision.get('roll')}, outcome: {pit_decision.get('outcome')})"
                                )
                            else:
                                print(
                                    f"  [STRATEGIST - {team}] Pit decision: Stay with planned pit lap {next_pit_lap} (roll: {pit_decision.get('roll')}, outcome: {pit_decision.get('outcome')})"
                                )

                            self.team_last_pit_decision_lap[team] = lap

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
                    driver_result["tyre_sequence"][current_tyre_index]
                    if current_tyre_index < len(driver_result["tyre_sequence"])
                    else "UNKNOWN"
                )
                lap_count_on_tyre = lap - sum(
                    1 for pl in driver_result["pit_laps"] if pl < lap
                )

                # Check for weather-triggered pit stop
                should_pit_weather, pit_reason = self.should_pit_for_weather(
                    driver, lap, current_tyre, weather_effects
                )
                if should_pit_weather and lap not in driver_result["pit_laps"]:
                    # Add this as an extra pit stop
                    driver_result["pit_laps"].append(lap)
                    # Determine wet weather tyre
                    recommended_tyre = weather_effects.get(
                        "recommended_tyre", "intermediate"
                    )
                    if recommended_tyre == "wet":
                        wet_tyre = "WET"
                    elif recommended_tyre == "intermediate":
                        wet_tyre = "INTERMEDIATE"
                    else:
                        wet_tyre = "MEDIUM"
                    driver_result["tyre_sequence"].append(wet_tyre)
                    self.race_state.last_weather_pit_decision[driver] = lap
                    # Increment weather pit count
                    self.race_state.weather_pits_count[driver] = (
                        self.race_state.weather_pits_count.get(driver, 0) + 1
                    )
                    print(f"    {driver} pits for {wet_tyre} tyres - {pit_reason}")
                    # Recalculate current tyre after weather pit
                    current_tyre_index = sum(
                        1 for pl in driver_result["pit_laps"] if pl < lap
                    )
                    current_tyre = (
                        driver_result["tyre_sequence"][current_tyre_index]
                        if current_tyre_index < len(driver_result["tyre_sequence"])
                        else "UNKNOWN"
                    )

                # Calculate lap time
                lap_result = self.simulate_lap(
                    lap=lap,
                    driver=driver,
                    driver_info=self.driver_data[driver],
                    current_tyre=current_tyre,
                    lap_count_on_tyre=lap_count_on_tyre,
                    pit_laps=driver_result["pit_laps"],
                    tyre_sequence=driver_result["tyre_sequence"],
                    current_tyre_index=current_tyre_index,
                    start_delta=start_deltas.get(driver, 0.0),
                    results=results,
                )

                lap_time = lap_result["lap_time"]

                # Apply weather lap time modifier
                weather_modifier = weather_effects.get("lap_time_modifier", 0.0)
                if weather_modifier > 0:
                    lap_time *= 1 + weather_modifier

                # Apply safety car effects
                if self.race_state.sc_active:
                    lap_time += random.uniform(15.0, 25.0)
                elif self.race_state.vsc_active:
                    lap_time += random.uniform(8.0, 15.0)

                # Narrative pacing assist/debuff (intensity-bounded)
                if self.narrative_config.enabled:
                    team = self.driver_teams.get(driver, "")
                    if self.narrative_config.is_target_team(team):
                        if self.narrative_config.is_ultra():
                            lap_time *= 0.94
                            if lap_result.get("pit_time", 0.0) > 0:
                                lap_time = max(
                                    1.0,
                                    lap_time
                                    - max(self._target_pit_bonus_sec * 2.0, 1.5),
                                )
                        else:
                            lap_time *= max(0.96, 1.0 - self._target_pace_boost)
                            if lap_result.get("pit_time", 0.0) > 0:
                                lap_time = max(
                                    1.0, lap_time - self._target_pit_bonus_sec
                                )
                    elif team:
                        if self.narrative_config.is_ultra():
                            lap_time *= 1.03
                            if lap_result.get("pit_time", 0.0) > 0:
                                lap_time += max(
                                    self._opponent_pit_penalty_sec * 1.8, 2.0
                                )
                        else:
                            lap_time *= 1.0 + self._opponent_pace_penalty
                            if lap_result.get("pit_time", 0.0) > 0:
                                lap_time += self._opponent_pit_penalty_sec

                # Track cumulative time
                driver_result["cumulative_time"] += lap_time
                driver_result["lap_times"].append(lap_time)
                driver_result["laps_completed"] += 1
                driver_result["actual_laps"] += 1  # Physical laps completed
                # effective_laps will be calculated based on lapping status
                driver_result["effective_laps"] = (
                    driver_result["actual_laps"] - driver_result["laps_down"]
                )
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

            # Check for chequered flag: Leader has finished final lap
            if (
                lap == self.num_laps
                and not self.race_state.chequered_flag_shown
                and sorted_drivers
            ):
                leader_driver = sorted_drivers[0][0]
                leader_laps = results[leader_driver]["laps_completed"]
                if leader_laps >= self.num_laps:
                    # Leader has completed final lap - show chequered flag
                    self.race_state.chequered_flag_shown = True
                    self.race_state.chequered_flag_lap = lap
                    self.race_state.leader_finished = True
                    print(f"\n[CHEQUERED FLAG] {leader_driver} wins the race!")

            # Monaco-specific: Add overtake resistance (Fix 2a)
            # At Monaco, it's very hard to overtake, so we add a small bonus
            # to drivers who are already ahead based on their position
            if is_monaco_track(self.track_name) and not self.race_state.sc_active:
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

            # Safety Car pack tightening / reformation
            if self.race_state.sc_active:
                sorted_drivers = self._apply_sc_pack_tightening(sorted_drivers, results)

            for position, (driver, _) in enumerate(sorted_drivers, 1):
                results[driver]["position"] = position

            # REAL-TIME LAPPING DETECTION (FIA-compliant)
            # Check for lapping situations after all drivers have completed this lap
            if not self.race_state.sc_active:  # Skip during safety car
                lapping_events = self.lapping_detector.detect_lapping(
                    results=results,
                    current_lap=lap,
                    safety_car_active=self.race_state.sc_active,
                )

                # Process any lapping events
                for event in lapping_events:
                    # Update results with lapping information
                    results[event.lapped_driver]["laps_down"] = event.laps_down
                    results[event.lapped_driver]["is_lapped"] = True

                    # Update race state
                    self.race_state.driver_lap_deficit[event.lapped_driver] = (
                        event.laps_down
                    )
                    if event.laps_down > 0:
                        self.race_state.lapped_cars[event.lapped_driver] = (
                            event.laps_down
                        )

                    # Print lapping notification
                    print(
                        f"  [LAPPING - Lap {lap}] {event.leader} laps {event.lapped_driver} "
                        f"(+{event.laps_down} Lap{'s' if event.laps_down > 1 else ''})"
                    )

            # Increment lap counter for next iteration
            lap += 1

        # Finalize results
        print(f"\n=== Race Complete ===")

        # Print Strategic Decisions Summary
        if self.strategic_decisions:
            print(f"\n=== Strategic Decisions Summary ===")
            print(f"  Total decisions: {len(self.strategic_decisions)}")

            # Count by type
            decision_types: Dict[str, int] = {}
            successful = 0
            failed = 0
            partial = 0

            for decision in self.strategic_decisions:
                dec_type = decision.get("decision_type", "unknown")
                decision_types[dec_type] = decision_types.get(dec_type, 0) + 1

                outcome = decision.get("outcome", "")
                if "success" in outcome.lower():
                    successful += 1
                elif "failure" in outcome.lower():
                    failed += 1
                elif "partial" in outcome.lower():
                    partial += 1

            print(f"  Decision Types:")
            for dec_type, count in decision_types.items():
                print(f"    - {dec_type}: {count}")

            print(f"\n  Outcomes:")
            print(f"    - Success: {successful}")
            print(f"    - Partial Success: {partial}")
            print(f"    - Failure: {failed}")

            if successful + partial + failed > 0:
                success_rate = (
                    (successful + partial * 0.5) / (successful + partial + failed) * 100
                )
                print(f"\n  Overall Success Rate: {success_rate:.1f}%")

            # Print key decisions
            print(f"\n  Key Decisions:")
            for decision in self.strategic_decisions[:10]:  # Show first 10
                lap = decision.get("lap", "?")
                dec_type = decision.get("decision_type", "unknown")
                roll = decision.get("roll", "?")
                outcome = decision.get("outcome", "unknown")
                action = decision.get(
                    "recommended_action", decision.get("selected_mode", "")
                )
                print(
                    f"    Lap {lap}: {dec_type} - {action} (roll: {roll}, outcome: {outcome})"
                )
        else:
            print(f"\n=== Strategic Decisions Summary ===")
            print("  No strategic decisions recorded.")

        # FIA-style final classification based on leader chequered time
        final_results = self._apply_fia_final_classification(results)

        # Print final results (FIA-compliant format)
        print("\n=== Final Race Results ===")
        print("  (Sorted by effective laps, then cumulative time)")
        for position, (driver, result) in enumerate(final_results, 1):
            interval_str = ""
            laps_down_str = ""

            actual_laps = result.get("actual_laps", result["laps_completed"])
            effective_laps = result.get("effective_laps", actual_laps)
            laps_down = result.get("laps_down", 0)

            # Show lap deficit for lapped cars
            if laps_down > 0:
                laps_down_str = f" [+{laps_down} Lap{'s' if laps_down > 1 else ''}]"
            elif position > 1:
                # Only show time gap if not lapped
                interval_str = f" (+{result['interval']:.3f}s)"

            print(
                f"  P{position}: {driver} - {result['cumulative_time']:.3f}s{interval_str} "
                f"({effective_laps}/{actual_laps} laps){laps_down_str}"
            )

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

        # Get lapping information (FIA-compliant)
        actual_laps = result.get("actual_laps", result.get("laps_completed", 0))
        effective_laps = result.get("effective_laps", actual_laps)
        laps_down = result.get("laps_down", 0)
        is_lapped = result.get("is_lapped", False)

        # Format interval: numeric for same-lap gaps, textual "+N Lap(s)" for lapped cars
        interval_val = result.get("interval", None)
        if pd.isna(interval_val) or interval_val is None:
            if laps_down and int(laps_down) > 0:
                ld = int(laps_down)
                interval_field = f"+{ld} Lap" if ld == 1 else f"+{ld} Laps"
            else:
                interval_field = ""
        else:
            try:
                interval_field = float(interval_val)
            except (ValueError, TypeError):
                interval_field = interval_val

        # Use effective/classification laps for `laps_completed` to reflect classified lap count
        laps_completed_field = int(effective_laps) if effective_laps is not None else int(actual_laps)

        row = {
            "position": result["position"],
            "driver": driver,
            "team": team,
            "total_time": result["cumulative_time"],
            "interval": interval_field,
            # FIA-compliant lapping fields
            "effective_laps": effective_laps,  # Laps for classification
            "actual_laps": actual_laps,  # Physical laps completed
            "laps_down": laps_down,  # Laps behind leader
            "is_lapped": "Yes" if is_lapped else "No",
            # Legacy field adjusted to show classified laps
            "laps_completed": laps_completed_field,
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


def save_lap_times_to_csv(
    results: Dict[str, Dict],
    track_name: str,
    output_dir: str,
) -> None:
    """
    Save per-lap times to CSV for fastest lap calculation.

    Args:
        results: Dictionary with driver results containing lap_times
        track_name: Track name for filename
        output_dir: Output directory
    """
    rows = []
    max_laps = max(len(r["lap_times"]) for r in results.values())

    for driver, result in results.items():
        lap_times = result["lap_times"]
        fastest = min(lap_times) if lap_times else 0
        fastest_idx = lap_times.index(fastest) + 1 if lap_times else 0

        row = {
            "driver": driver,
            "fastest_lap": round(fastest, 3),
            "fastest_lap_num": fastest_idx,
        }

        # Add each lap time
        for i, lt in enumerate(lap_times, 1):
            row[f"lap_{i}"] = round(lt, 3)

        # Pad missing laps with empty strings
        for i in range(len(lap_times) + 1, max_laps + 1):
            row[f"lap_{i}"] = ""

        rows.append(row)

    df = pd.DataFrame(rows)
    filepath = os.path.join(output_dir, f"lap_times_{track_name.lower()}.csv")
    df.to_csv(filepath, index=False)
    print(f"Lap times saved to: {filepath}")


def calculate_fastest_laps(results: Dict[str, Dict]) -> List[Dict]:
    """
    Calculate and rank fastest laps for all drivers.

    Returns:
        List of dicts: [{driver, fastest_lap, lap_number}, ...]
        Sorted by fastest_lap (ascending)
    """
    fastest_laps = []

    for driver, result in results.items():
        lap_times = result.get("lap_times", [])
        if lap_times:
            fastest = min(lap_times)
            lap_num = lap_times.index(fastest) + 1
            fastest_laps.append(
                {"driver": driver, "fastest_lap": fastest, "lap_number": lap_num}
            )

    return sorted(fastest_laps, key=lambda x: x["fastest_lap"])


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
    parser.add_argument(
        "--output-dir",
        help="Output directory for race results (default: auto-generated in outputs/enhanced_sim/)",
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

    # Check if GridPosition was loaded from CSV (create_driver_csv sets this)
    has_grid_positions = any(
        driver_data[d].get("grid_position") is not None for d in all_drivers
    )

    if has_grid_positions:
        # Use GridPosition from CSV - already set by read_driver_data
        # Sort drivers by their grid position
        all_drivers = sorted(
            all_drivers, key=lambda x: driver_data[x].get("grid_position", 99)
        )
    else:
        # No grid positions provided - shuffle for random starting order
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
    if args.output_dir:
        # Use provided output directory
        race_output_dir = args.output_dir
        os.makedirs(race_output_dir, exist_ok=True)
    else:
        # Use default auto-generated directory
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

    # Save lap times for fastest lap calculation
    save_lap_times_to_csv(
        results=results,
        track_name=gp_name,
        output_dir=race_output_dir,
    )

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
