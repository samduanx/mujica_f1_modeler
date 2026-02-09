#!/usr/bin/env python3
"""
Multi-Track F1 Simulation Calibration System

This system tests the F1 race simulation against FastF1 real data for ALL F1 tracks.
It uses the same driver ratings (DR/R values from Spain) for all tracks and compares
the simulated race pace against real FastF1 data to identify calibration issues.

Usage:
    python src/debug/multi_track_calibration.py --all-tracks --runs 5 --compare-fastf1
    python src/debug/multi_track_calibration.py --tracks Spain Monaco Monza --runs 10
    python src/debug/multi_track_calibration.py --single-track Bahrain --runs 5
"""

import argparse
import sys
import os
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from statistics import mean, stdev, median
import itertools

# Third-party imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend

# Suppress warnings
warnings.filterwarnings("ignore")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import simulation modules
from src.simulation.long_dist_sim_with_box import (
    read_driver_data,
    simulate_race_with_pit_stops,
    calculate_base_lap_time,
    get_track_base_lap,
    load_pit_stop_data,
    load_pitlane_time_data,
    get_track_characteristics,
    DEFAULT_LAP_COUNTS,
    TRACK_BASE_LAP_TIMES,
)
import fastf1


# =============================================================================
# TRACK CONFIGURATION
# =============================================================================

# F1 2022-2025 Season Tracks with current calibration values
# Note: Las Vegas added 2023, China returned in 2024
TRACK_CONFIG = {
    # Track: (FastF1 name, year, laps, current_base_lap, difficulty)
    # Updated years for better calibration data
    "Spain": ("Spain", 2022, 66, 89.0, "medium"),
    "Bahrain": ("Bahrain", 2024, 57, 91.0, "medium"),  # Using 2024 for calibration
    "Monaco": ("Monaco", 2024, 78, 76.0, "high"),
    "Monza": ("Italy", 2022, 53, 84.0, "low"),
    "Silverstone": ("Great Britain", 2022, 52, 88.0, "medium"),
    "Austria": ("Austria", 2022, 71, 68.0, "medium"),
    "Hungary": ("Hungary", 2022, 70, 80.0, "high"),
    "Netherlands": ("Netherlands", 2022, 72, 74.0, "medium"),
    "Singapore": ("Singapore", 2022, 61, 88.0, "high"),
    "Japan": ("Japan", 2022, 53, 91.0, "medium"),
    "Brazil": ("Brazil", 2022, 71, 74.0, "medium"),
    "Abu Dhabi": ("Abu Dhabi", 2022, 58, 90.0, "low"),
    "Canada": ("Canada", 2022, 70, 80.0, "medium"),
    "Azerbaijan": ("Azerbaijan", 2024, 51, 88.0, "high"),
    "Belgium": ("Belgium", 2022, 44, 102.0, "low"),
    "France": ("France", 2022, 53, 91.0, "medium"),
    "Mexico": ("Mexico", 2024, 71, 84.0, "medium"),
    "Miami": ("Miami", 2024, 57, 92.0, "high"),
    "Saudi Arabia": ("Saudi Arabia", 2024, 50, 90.0, "high"),
    "China": ("China", 2024, 56, 88.0, "medium"),  # China returned in 2024
    "Qatar": ("Qatar", 2023, 57, 88.0, "medium"),
    "Las Vegas": ("Las Vegas", 2024, 50, 92.0, "high"),  # Using 2024 for calibration
}

# Multi-year data fetching for tracks with multiple seasons
MULTI_YEAR_TRACKS = {
    "Las Vegas": [2023, 2024],  # Fetch 2 years for better calibration
    "China": [2024, 2025],      # China returned in 2024, use 2024-2025
    "Bahrain": [2023, 2024],   # Better calibration with 2 years
    "Saudi Arabia": [2023, 2024],  # High-speed track, multi-year helps
    "Miami": [2023, 2024],      # Street circuit, multi-year helps
    "Japan": [2023, 2024],      # Suzuka consistency check
    "Singapore": [2022, 2023],   # High variance due to safety cars
    "Monaco": [2023, 2024],     # Street circuit consistency check
}

# Output directories
OUTPUT_BASE = Path("outputs/multi_track_calibration")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SimulationResult:
    """Results from a single simulation run"""
    track_name: str
    run_number: int
    winner: str
    winner_time: float
    total_race_time: float
    avg_lap_time: float
    lap_time_std: float
    num_pitstops: int
    positions: Dict[str, int]  # driver -> final position
    lap_times: Dict[str, List[float]]  # driver -> list of lap times


@dataclass
class TrackCalibrationResult:
    """Calibration analysis for a single track"""
    track_name: str
    fastf1_name: str
    year: int
    laps: int
    
    # Simulation statistics (from multi-run)
    sim_avg_race_pace: float
    sim_std_race_pace: float
    sim_min_race_pace: float
    sim_max_race_pace: float
    
    # Real data from FastF1
    real_race_pace: Optional[float]
    real_pole_time: Optional[float]
    real_winner_time: Optional[float]
    
    # Calibration analysis
    pace_error_percent: Optional[float]
    calibration_status: str  # "good", "needs_adjustment", "unknown"
    suggested_base_lap: Optional[float]
    
    # Driver positions comparison
    sim_top5_positions: List[str]
    real_top5_positions: List[str]
    position_match_rate: float
    
    # Additional metrics
    num_runs: int
    comparison_available: bool


@dataclass
class MultiTrackReport:
    """Summary report for all tracks"""
    timestamp: str
    tracks_tested: List[str]
    calibration_issues: List[Dict]
    good_calibration_tracks: List[str]
    needs_adjustment_tracks: List[str]
    summary_stats: Dict
    recommendations: List[str]


# =============================================================================
# SPREADSHEET DATA LOADER
# =============================================================================

def get_spain_driver_data() -> Dict[str, Dict]:
    """
    Get driver data from Spain CSV to use as baseline for all tracks.
    Returns dictionary of driver_name -> {Team, R_Value, DR_Value}
    """
    csv_file = Path("outputs/tables/Spain.csv")
    
    if not csv_file.exists():
        raise FileNotFoundError(
            f"Spain driver data not found at {csv_file}. "
            "Please ensure outputs/tables/Spain.csv exists with driver ratings."
        )
    
    driver_data = {}
    df = pd.read_csv(csv_file)
    
    for _, row in df.iterrows():
        driver_name = row["Driver"]
        team_name = row["Team"]
        dr_value = row["DR"]
        ro_value = row["RO"]
        
        if pd.notna(driver_name) and pd.notna(dr_value) and pd.notna(ro_value):
            driver_data[driver_name] = {
                "Team": team_name,
                "R_Value": float(ro_value),
                "DR_Value": float(dr_value),
                "PR_Value": float(ro_value),  # PR = R_Value (performance rating)
                "grid_position": 1,  # Will be randomized per run
            }
    
    return driver_data


def create_track_driver_data(track_name: str) -> Dict[str, Dict]:
    """
    Create driver data for a specific track using Spain ratings.
    Returns driver data with randomized grid positions.
    """
    spain_data = get_spain_driver_data()
    
    # Create a copy with randomized grid positions
    import numpy as np
    
    drivers = list(spain_data.keys())
    np.random.shuffle(drivers)
    
    track_driver_data = {}
    for i, driver_name in enumerate(drivers):
        driver_info = spain_data[driver_name].copy()
        driver_info["grid_position"] = i + 1
        track_driver_data[driver_name] = driver_info
    
    return track_driver_data


# =============================================================================
# FASTF1 DATA FETCHER
# =============================================================================

def setup_fastf1_cache():
    """Setup FastF1 cache directory"""
    cache_dir = OUTPUT_BASE / "f1_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    fastf1.set_log_level("ERROR")


def fetch_fastf1_race_pace(track_name: str, year: int) -> Optional[float]:
    """
    Fetch real race pace from FastF1 for a given track.
    Returns average lap time in seconds for the race winner (clean laps only).
    """
    try:
        fastf1_name, _, _, _, _ = TRACK_CONFIG[track_name]
        
        # Load session data
        session = fastf1.get_session(year, fastf1_name, "R")
        session.load()
        
        # Get race results
        results = session.results
        
        if results is None or len(results) == 0:
            print(f"    ⚠ No race results for {track_name} {year}")
            return None
        
        # Get fastest lap times for each driver
        # Filter out laps with incidents (time > 115% of median)
        all_laps = session.laps
        if all_laps is None or len(all_laps) == 0:
            print(f"    ⚠ No lap data for {track_name} {year}")
            return None
        
        # Calculate race pace (median lap time, excluding first lap and in-laps)
        race_laps = all_laps[
            (all_laps["LapNumber"] > 1) & 
            (all_laps["PitOutTime"].isna()) &
            (all_laps["PitInTime"].isna())
        ]
        
        if len(race_laps) == 0:
            print(f"    ⚠ No valid race laps for {track_name} {year}")
            return None
        
        # Get lap times and filter outliers (>15% from median)
        lap_times = race_laps["LapTime"].dt.total_seconds()
        median_time = lap_times.median()
        
        # Filter out anomalous laps (incidents, yellow flags, etc.)
        clean_laps = lap_times[
            (lap_times > median_time * 0.85) & 
            (lap_times < median_time * 1.15)
        ]
        
        if len(clean_laps) == 0:
            print(f"    ⚠ All laps filtered as anomalous for {track_name} {year}")
            return None
        
        avg_pace = clean_laps.mean()
        print(f"    ✓ FastF1 race pace: {avg_pace:.3f}s (from {len(clean_laps)} clean laps)")
        
        return avg_pace
        
    except Exception as e:
        print(f"    ⚠ Error fetching FastF1 data for {track_name}: {e}")
        return None


def fetch_fastf1_race_pace_multi_year(track_name: str, years: List[int]) -> Tuple[Optional[float], Dict]:
    """
    Fetch real race pace from FastF1 for a track across multiple years.
    Returns average pace and year-by-year data.
    """
    all_paces = []
    year_data = {}
    
    for year in years:
        print(f"    Fetching {year} data...")
        pace = fetch_fastf1_race_pace(track_name, year)
        if pace is not None:
            all_paces.append(pace)
            year_data[year] = pace
    
    if all_paces:
        avg_pace = np.mean(all_paces)
        print(f"    📊 Multi-year average: {avg_pace:.3f}s (years: {list(year_data.keys())})")
        return avg_pace, year_data
    
    return None, year_data


def fetch_fastf1_pole_time(track_name: str, year: int) -> Optional[float]:
    """Fetch pole position time from FastF1"""
    try:
        fastf1_name, _, _, _, _ = TRACK_CONFIG[track_name]
        
        session = fastf1.get_session(year, fastf1_name, "Q")
        session.load()
        
        results = session.results
        if results is None or len(results) == 0:
            return None
        
        # Get pole time (first position)
        pole_time = results.iloc[0]["Q3"] if "Q3" in results.columns else None
        if pd.isna(pole_time):
            pole_time = results.iloc[0]["Q2"] if "Q2" in results.columns else None
        if pd.isna(pole_time):
            pole_time = results.iloc[0]["Q1"] if "Q1" in results.columns else None
            
        if pole_time is not None:
            pole_seconds = pole_time.total_seconds()
            print(f"    ✓ FastF1 pole time: {pole_seconds:.3f}s")
            return pole_seconds
            
    except Exception as e:
        print(f"    ⚠ Error fetching pole time for {track_name}: {e}")
        return None
    
    return None


def fetch_fastf1_top_positions(track_name: str, year: int) -> List[str]:
    """Fetch top 5 finishing positions from FastF1"""
    try:
        fastf1_name, _, _, _, _ = TRACK_CONFIG[track_name]
        
        session = fastf1.get_session(year, fastf1_name, "R")
        session.load()
        
        results = session.results
        if results is None or len(results) == 0:
            return []
        
        top5 = results.head(5)["Abbreviation"].tolist()
        print(f"    ✓ FastF1 top 5: {', '.join(top5[:3])}...")
        return top5
        
    except Exception as e:
        print(f"    ⚠ Error fetching positions for {track_name}: {e}")
        return []


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_single_simulation(track_name: str, seed: int) -> SimulationResult:
    """
    Run a single race simulation for a track.
    Uses Spain driver data with randomized grid positions.
    """
    fastf1_name, year, num_laps, base_lap, difficulty = TRACK_CONFIG[track_name]
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Create driver data for this track
    driver_data = create_track_driver_data(track_name)
    
    # Get track characteristics
    track_chars = get_track_characteristics()
    track_key = track_name.lower().replace(" ", "").replace("_", "")
    
    # Map track name to characteristics key
    track_mapping = {
        "saudiarabia": "saudi_arabia",
        "greatbritain": "britain",
        "abudhabi": "abudhabi",
    }
    track_key = track_mapping.get(track_key, track_key)
    
    if track_key not in track_chars:
        track_key = "spain"  # Fallback
    
    current_track_chars = track_chars[track_key]
    
    # Load pit stop data
    pit_data = load_pit_stop_data()
    pitlane_data = load_pitlane_time_data()
    
    # Calculate R and DR min/max
    r_values = [d["R_Value"] for d in driver_data.values()]
    dr_values = [d["DR_Value"] for d in driver_data.values()]
    r_max = max(r_values)
    r_min = min(r_values)
    dr_max = max(dr_values)
    dr_min = min(dr_values)
    
    # Simulate race for each driver
    results = {}
    for driver_name, driver_info in driver_data.items():
        # Assign team strategy
        team_name = driver_info.get("Team", "Unknown")
        
        # Simple strategy assignment (2-stop default)
        strategy = "2"
        tyre_sequence = ["C2", "C3", "C2"]
        
        # Create team strategy mapping
        team_strategies = {driver_name: {"strategy": strategy, "tyre_compounds_set": tyre_sequence}}
        
        result = simulate_race_with_pit_stops(
            driver_name=driver_name,
            driver_info=driver_info,
            num_laps=num_laps,
            track_name=track_name,
            track_chars=current_track_chars,
            r_max=r_max,
            dr_min=dr_min,
            dr_max=dr_max,
            pit_data=pit_data,
            team_strategies=team_strategies,
        )
        
        # Simplify result to only what we need
        results[driver_name] = {
            "total_time": result["total_time"],
            "lap_times": result["lap_times"],
            "strategy": result["strategy"],
        }
    
    # Sort by total time to get final positions
    sorted_results = sorted(results.items(), key=lambda x: x[1]["total_time"])
    
    # Extract winner info
    winner = sorted_results[0][0]
    winner_time = sorted_results[0][1]["total_time"]
    
    # Calculate average lap time (excluding first lap)
    all_lap_times = []
    for driver_name, result in results.items():
        lap_times = result["lap_times"][1:]  # Exclude first lap (formation lap)
        all_lap_times.extend(lap_times)
    
    avg_lap_time = np.mean(all_lap_times)
    lap_time_std = np.std(all_lap_times)
    
    # Count total pitstops
    num_pitstops = sum(
        len(result.get("lap_times", [])) - num_laps 
        for result in results.values()
    )
    
    # Create position mapping
    positions = {
        driver_name: i + 1 
        for i, (driver_name, _) in enumerate(sorted_results)
    }
    
    return SimulationResult(
        track_name=track_name,
        run_number=seed,
        winner=winner,
        winner_time=winner_time,
        total_race_time=winner_time,
        avg_lap_time=avg_lap_time,
        lap_time_std=lap_time_std,
        num_pitstops=num_pitstops,
        positions=positions,
        lap_times={d: r["lap_times"] for d, r in results.items()},
    )


def run_multi_track_simulation(
    track_name: str, 
    num_runs: int, 
    seeds: Optional[List[int]] = None
) -> Tuple[SimulationResult, ...]:
    """
    Run multiple simulations for a track to get statistical distribution.
    """
    if seeds is None:
        seeds = list(range(num_runs))
    
    results = []
    for seed in seeds:
        print(f"  Running simulation {seed + 1}/{num_runs}...")
        result = run_single_simulation(track_name, seed)
        results.append(result)
    
    return tuple(results)


# =============================================================================
# CALIBRATION ANALYSIS
# =============================================================================

def analyze_track_calibration(
    track_name: str,
    simulation_results: Tuple[SimulationResult, ...],
    real_race_pace: Optional[float],
    real_top5: List[str]
) -> TrackCalibrationResult:
    """
    Analyze calibration for a single track by comparing simulation vs real data.
    """
    fastf1_name, year, laps, current_base, difficulty = TRACK_CONFIG[track_name]
    
    # Calculate simulation statistics
    avg_lap_times = [r.avg_lap_time for r in simulation_results]
    sim_avg_race_pace = np.mean(avg_lap_times)
    sim_std_race_pace = np.std(avg_lap_times)
    sim_min_race_pace = np.min(avg_lap_times)
    sim_max_race_pace = np.max(avg_lap_times)
    
    # Get simulation top 5 from first run (for consistency)
    sim_top5 = sorted(
        simulation_results[0].positions.keys(),
        key=lambda x: simulation_results[0].positions[x]
    )[:5]
    
    # Calculate position match rate
    real_top5_set = set(real_top5[:5])
    sim_top5_set = set(sim_top5[:5])
    overlap = len(real_top5_set & sim_top5_set)
    position_match_rate = overlap / 5.0 * 100  # percentage
    
    # Calculate calibration error
    if real_race_pace is not None:
        pace_error_percent = (sim_avg_race_pace - real_race_pace) / real_race_pace * 100
        
        # Determine calibration status
        if abs(pace_error_percent) < 2.0:
            calibration_status = "good"
            suggested_base_lap = None
        elif abs(pace_error_percent) < 5.0:
            calibration_status = "needs_adjustment"
            # Suggest new base lap time
            suggested_base_lap = current_base * (1 - pace_error_percent / 100)
        else:
            calibration_status = "needs_adjustment"
            suggested_base_lap = current_base * (1 - pace_error_percent / 100)
    else:
        pace_error_percent = None
        calibration_status = "unknown"
        suggested_base_lap = None
    
    return TrackCalibrationResult(
        track_name=track_name,
        fastf1_name=fastf1_name,
        year=year,
        laps=laps,
        sim_avg_race_pace=sim_avg_race_pace,
        sim_std_race_pace=sim_std_race_pace,
        sim_min_race_pace=sim_min_race_pace,
        sim_max_race_pace=sim_max_race_pace,
        real_race_pace=real_race_pace,
        real_pole_time=None,
        real_winner_time=None,
        pace_error_percent=pace_error_percent,
        calibration_status=calibration_status,
        suggested_base_lap=suggested_base_lap,
        sim_top5_positions=sim_top5,
        real_top5_positions=real_top5[:5],
        position_match_rate=position_match_rate,
        num_runs=len(simulation_results),
        comparison_available=real_race_pace is not None,
    )


def run_full_calibration_analysis(
    tracks: List[str],
    num_runs: int = 5,
    fetch_real_data: bool = True
) -> Dict[str, TrackCalibrationResult]:
    """
    Run full calibration analysis for multiple tracks.
    """
    results = {}
    
    for track_name in tracks:
        print(f"\n{'='*60}")
        print(f"  ANALYZING: {track_name}")
        print(f"{'='*60}")
        
        fastf1_name, year, laps, base_lap, difficulty = TRACK_CONFIG[track_name]
        print(f"  Track: {fastf1_name}, Year: {year}, Laps: {laps}")
        print(f"  Current calibration: {base_lap}s base lap time")
        
        # Fetch real FastF1 data if requested
        real_race_pace = None
        real_top5 = []
        if fetch_real_data:
            print(f"\n  Fetching FastF1 data...")
            
            # Check if this track needs multi-year data
            if track_name in MULTI_YEAR_TRACKS:
                years_to_fetch = MULTI_YEAR_TRACKS[track_name]
                print(f"  Fetching multi-year data for {track_name}: {years_to_fetch}")
                real_race_pace, year_data = fetch_fastf1_race_pace_multi_year(track_name, years_to_fetch)
                # Use most recent year for top positions
                real_top5 = fetch_fastf1_top_positions(track_name, years_to_fetch[-1])
            else:
                real_race_pace = fetch_fastf1_race_pace(track_name, year)
                real_top5 = fetch_fastf1_top_positions(track_name, year)
        
        # Run simulations
        print(f"\n  Running {num_runs} simulation(s)...")
        simulation_results = run_multi_track_simulation(track_name, num_runs)
        
        # Analyze calibration
        calibration = analyze_track_calibration(
            track_name,
            simulation_results,
            real_race_pace,
            real_top5
        )
        
        results[track_name] = calibration
        
        # Print summary
        print(f"\n  📊 Calibration Results:")
        print(f"     Simulated race pace: {calibration.sim_avg_race_pace:.3f}s ±{calibration.sim_std_race_pace:.3f}s")
        if calibration.real_race_pace:
            print(f"     Real FastF1 pace:    {calibration.real_race_pace:.3f}s")
            print(f"     Pace error:          {calibration.pace_error_percent:+.2f}%")
        print(f"     Calibration status:   {calibration.calibration_status}")
        if calibration.suggested_base_lap:
            print(f"     Suggested base lap:   {calibration.suggested_base_lap:.2f}s")
        print(f"     Position match rate: {calibration.position_match_rate:.0f}%")
    
    return results


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_calibration_report(
    results: Dict[str, TrackCalibrationResult],
    output_file: Path
):
    """Generate detailed calibration report"""
    
    good_tracks = []
    needs_adjustment = {}  # Dict to track suggested values
    unknown_tracks = []
    
    for track_name, cal in results.items():
        if cal.calibration_status == "good":
            good_tracks.append(track_name)
        elif cal.calibration_status == "needs_adjustment":
            needs_adjustment[track_name] = cal
        else:
            unknown_tracks.append(track_name)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# F1 Simulation Multi-Track Calibration Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary table
        f.write("## 📊 Summary\n\n")
        f.write("| Track | Sim Pace | Real Pace | Error | Status |\n")
        f.write("|-------|----------|-----------|-------|--------|\n")
        
        for track_name in sorted(results.keys()):
            cal = results[track_name]
            pace_str = f"{cal.sim_avg_race_pace:.3f}s"
            
            if cal.real_race_pace:
                real_str = f"{cal.real_race_pace:.3f}s"
                error_str = f"{cal.pace_error_percent:+.2f}%" if cal.pace_error_percent else "N/A"
            else:
                real_str = "N/A"
                error_str = "N/A"
            
            status_icon = "✅" if cal.calibration_status == "good" else "⚠️"
            f.write(f"| {track_name} | {pace_str} | {real_str} | {error_str} | {status_icon} |\n")
        
        f.write("\n")
        
        # Good calibration tracks
        if good_tracks:
            f.write("## ✅ Well-Calibrated Tracks\n\n")
            f.write("These tracks have simulation pace within 2% of real FastF1 data:\n\n")
            for track_name in good_tracks:
                cal = results[track_name]
                f.write(f"- **{track_name}**: {cal.sim_avg_race_pace:.3f}s vs {cal.real_race_pace:.3f}s real "
                        f"({cal.pace_error_percent:+.2f}% error)\n")
            f.write("\n")
        
        # Needs adjustment
        if needs_adjustment:
            f.write("## ⚠️ Tracks Needing Adjustment\n\n")
            f.write("These tracks need calibration tuning:\n\n")
            f.write("| Track | Current Base | Suggested Base | Reason |\n")
            f.write("|-------|-------------|---------------|--------|\n")
            
            for track_name in needs_adjustment:
                cal = results[track_name]
                reason = []
                if cal.pace_error_percent and cal.pace_error_percent > 0:
                    reason.append(f"Simulation {cal.pace_error_percent:.1f}% too slow")
                elif cal.pace_error_percent:
                    reason.append(f"Simulation {abs(cal.pace_error_percent):.1f}% too fast")
                if cal.position_match_rate < 60:
                    reason.append(f"Only {cal.position_match_rate:.0f}% position match")
                
                f.write(f"| {track_name} | {TRACK_CONFIG[track_name][3]:.1f}s | "
                        f"{cal.suggested_base_lap:.2f}s | {', '.join(reason)} |\n")
            
            f.write("\n")
            
            # Calibration suggestions
            f.write("### Recommended Calibrations\n\n")
            f.write("Add these to `TRACK_BASE_LAP_TIMES` in `src/simulation/long_dist_sim_with_box.py`:\n\n")
            f.write("```python\n")
            f.write("TRACK_BASE_LAP_TIMES = {\n")
            for track_name in sorted(needs_adjustment.keys()):
                cal = results[track_name]
                if cal.suggested_base_lap:
                    f.write(f'    "{track_name}": ({cal.suggested_base_lap:.1f}, 300),\n')
            f.write("}\n")
            f.write("```\n\n")
        
        # Unknown tracks
        if unknown_tracks:
            f.write("## ❓ Tracks Without Real Data Comparison\n\n")
            f.write("These tracks couldn't be compared due to missing FastF1 data:\n\n")
            for track_name in unknown_tracks:
                cal = results[track_name]
                f.write(f"- **{track_name}**: Simulated pace {cal.sim_avg_race_pace:.3f}s\n")
            f.write("\n")
        
        # Detailed statistics
        f.write("## 📈 Detailed Statistics\n\n")
        
        for track_name in sorted(results.keys()):
            cal = results[track_name]
            f.write(f"### {track_name}\n\n")
            
            f.write(f"- **Configuration**: {cal.fastf1_name} {cal.year}, {cal.laps} laps\n")
            f.write(f"- **Simulated Pace**: {cal.sim_avg_race_pace:.3f}s ±{cal.sim_std_race_pace:.3f}s\n")
            f.write(f"  - Range: {cal.sim_min_race_pace:.3f}s - {cal.sim_max_race_pace:.3f}s\n")
            
            if cal.real_race_pace:
                f.write(f"- **Real Pace**: {cal.real_race_pace:.3f}s\n")
                f.write(f"- **Error**: {cal.pace_error_percent:+.2f}%\n")
            
            f.write(f"- **Position Match Rate**: {cal.position_match_rate:.0f}%\n")
            f.write(f"- **Simulated Top 5**: {', '.join(cal.sim_top5_positions[:3])}...\n")
            if cal.real_top5_positions:
                f.write(f"- **Real Top 5**: {', '.join(cal.real_top5_positions[:3])}...\n")
            
            f.write("\n")
    
    print(f"\n📄 Report saved to: {output_file}")


def generate_calibration_summary_plot(
    results: Dict[str, TrackCalibrationResult],
    output_file: Path
):
    """Generate visualization comparing simulation vs real data"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Pace comparison bar chart
    ax1 = axes[0, 0]
    tracks = sorted(results.keys())
    sim_paces = [results[t].sim_avg_race_pace for t in tracks]
    real_paces = [results[t].real_race_pace if results[t].real_race_pace else 0 for t in tracks]
    
    x = np.arange(len(tracks))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, sim_paces, width, label='Simulation', color='steelblue', alpha=0.8)
    bars2 = ax1.bar(x + width/2, real_paces, width, label='FastF1 Real', color='coral', alpha=0.8)
    
    ax1.set_ylabel('Race Pace (seconds)')
    ax1.set_title('Simulated vs Real Race Pace by Track')
    ax1.set_xticks(x)
    ax1.set_xticklabels(tracks, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot 2: Pace error percentage
    ax2 = axes[0, 1]
    errors = []
    valid_tracks = []
    for t in tracks:
        if results[t].pace_error_percent is not None:
            errors.append(results[t].pace_error_percent)
            valid_tracks.append(t)
    
    colors = ['green' if abs(e) < 2 else 'orange' if abs(e) < 5 else 'red' for e in errors]
    ax2.barh(valid_tracks, errors, color=colors, alpha=0.8)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax2.axvline(x=-2, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axvline(x=2, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axvline(x=-5, color='orange', linestyle='--', linewidth=1, alpha=0.5)
    ax2.axvline(x=5, color='orange', linestyle='--', linewidth=1, alpha=0.5)
    
    ax2.set_xlabel('Pace Error (%)')
    ax2.set_title('Simulation Pace Error by Track')
    ax2.grid(axis='x', alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', alpha=0.8, label='<2% (Good)'),
        Patch(facecolor='orange', alpha=0.8, label='2-5% (Needs tuning)'),
        Patch(facecolor='red', alpha=0.8, label='>5% (Poor)'),
    ]
    ax2.legend(handles=legend_elements, loc='lower right')
    
    # Plot 3: Position match rate
    ax3 = axes[1, 0]
    match_rates = [results[t].position_match_rate for t in tracks]
    colors3 = ['green' if r >= 60 else 'orange' if r >= 40 else 'red' for r in match_rates]
    ax3.bar(tracks, match_rates, color=colors3, alpha=0.8)
    ax3.axhline(y=60, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax3.axhline(y=40, color='orange', linestyle='--', linewidth=1, alpha=0.5)
    
    ax3.set_ylabel('Match Rate (%)')
    ax3.set_title('Position Match Rate (Sim vs Real Top 5)')
    ax3.set_xticks(range(len(tracks)))
    ax3.set_xticklabels(tracks, rotation=45, ha='right')
    ax3.grid(axis='y', alpha=0.3)
    
    # Plot 4: Calibration summary pie chart
    ax4 = axes[1, 1]
    good = sum(1 for r in results.values() if r.calibration_status == "good")
    needs_adj = sum(1 for r in results.values() if r.calibration_status == "needs_adjustment")
    unknown = sum(1 for r in results.values() if r.calibration_status == "unknown")
    
    if good + needs_adj + unknown > 0:
        sizes = [good, needs_adj, unknown]
        labels = [f'Good ({good})', f'Needs Tuning ({needs_adj})', f'Unknown ({unknown})']
        colors4 = ['green', 'orange', 'gray']
        explode = (0.05, 0.05, 0)
        
        ax4.pie(sizes, explode=explode, labels=labels, colors=colors4, autopct='%1.0f%%',
                shadow=True, startangle=90)
        ax4.set_title('Overall Calibration Status')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Summary plot saved to: {output_file}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Multi-track F1 simulation calibration system"
    )
    
    parser.add_argument(
        "--tracks",
        nargs="+",
        help="Specific tracks to test (e.g., Spain Monaco Monza)"
    )
    parser.add_argument(
        "--all-tracks",
        action="store_true",
        help="Test all configured tracks"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of simulation runs per track (default: 3)"
    )
    parser.add_argument(
        "--compare-fastf1",
        action="store_true",
        help="Fetch real FastF1 data for comparison"
    )
    parser.add_argument(
        "--no-fastf1",
        action="store_true",
        help="Skip FastF1 data fetching"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/multi_track_calibration",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Determine tracks to test
    if args.all_tracks:
        tracks_to_test = list(TRACK_CONFIG.keys())
    elif args.tracks:
        tracks_to_test = args.tracks
    else:
        # Default: test a few key tracks
        tracks_to_test = ["Spain", "Monaco", "Monza", "Bahrain"]
    
    print(f"\n{'='*70}")
    print(f"  F1 SIMULATION MULTI-TRACK CALIBRATION SYSTEM")
    print(f"{'='*70}")
    print(f"\nConfiguration:")
    print(f"  - Tracks: {len(tracks_to_test)} ({', '.join(tracks_to_test[:5])}{'...' if len(tracks_to_test) > 5 else ''})")
    print(f"  - Runs per track: {args.runs}")
    print(f"  - Compare with FastF1: {not args.no_fastf1 and args.compare_fastf1}")
    
    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup FastF1 cache
    if not args.no_fastf1:
        setup_fastf1_cache()
    
    # Run calibration analysis
    fetch_real = not args.no_fastf1 and args.compare_fastf1
    results = run_full_calibration_analysis(
        tracks_to_test,
        num_runs=args.runs,
        fetch_real_data=fetch_real
    )
    
    # Generate reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Markdown report
    report_file = output_dir / f"calibration_report_{timestamp}.md"
    generate_calibration_report(results, report_file)
    
    # Summary plot
    plot_file = output_dir / f"calibration_summary_{timestamp}.png"
    generate_calibration_summary_plot(results, plot_file)
    
    # Print final summary
    print(f"\n{'='*70}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*70}")
    
    good = sum(1 for r in results.values() if r.calibration_status == "good")
    needs_adj = sum(1 for r in results.values() if r.calibration_status == "needs_adjustment")
    unknown = sum(1 for r in results.values() if r.calibration_status == "unknown")
    
    print(f"\n  ✅ Well-calibrated: {good} tracks")
    print(f"  ⚠️  Needs adjustment: {needs_adj} tracks")
    print(f"  ❓ Unknown (no real data): {unknown} tracks")
    
    if needs_adj > 0:
        print(f"\n  Tracks needing calibration updates:")
        for track_name, cal in sorted(results.items(), key=lambda x: abs(x[1].pace_error_percent or 0), reverse=True):
            if cal.calibration_status == "needs_adjustment" and cal.suggested_base_lap:
                print(f"    - {track_name}: {TRACK_CONFIG[track_name][3]:.1f}s → {cal.suggested_base_lap:.1f}s "
                      f"({cal.pace_error_percent:+.1f}% error)")
    
    print(f"\n  📁 Output files:")
    print(f"    - Report: {report_file}")
    print(f"    - Plot: {plot_file}")
    print(f"\n{'='*70}")
    
    return results


if __name__ == "__main__":
    main()
