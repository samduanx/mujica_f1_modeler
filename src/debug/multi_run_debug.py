#!/usr/bin/env python3
"""
F1 Multi-Run Simulation Debug System

This module provides a comprehensive debugging framework for F1 race simulations:
1. Multi-run simulations with statistical analysis
2. FastF1 data comparison (qualifying times, race pace)
3. Outlier detection and anomaly reporting
4. Parameter sensitivity analysis
5. Track-by-track calibration recommendations

Key Features:
- Runs N simulations per track to reduce random variance
- Compares simulation metrics against FastF1 real data
- Identifies systematic biases in simulation parameters
- Generates detailed debug reports
- Provides calibration recommendations

Usage:
    python -m debug.multi_run_debug --tracks Spain Bahrain Monaco --runs 10
    python -m debug.multi_run_debug --all-tracks --runs 5 --compare-fastf1
"""

import argparse
import os
import sys
import json
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import simulation components
from src.simulation.long_dist_sim_with_box import (
    simulate_race_with_pit_stops,
    read_driver_data,
    load_pit_stop_data,
    get_track_characteristics,
    DEFAULT_LAP_COUNTS,
    calculate_degradation_with_cliff,
    get_universal_tyre_params_with_cliff,
    get_available_compounds_for_track,
    get_track_tyre_weights,
    generate_team_tyre_compounds,
    generate_individual_tyre_sequence,
    determine_pit_strategy,
    generate_pit_laps,
    ensure_f1_tyre_compliance,
    load_pitlane_time_data,
    roll_pit_stop_time,
)

# Import FastF1 integration
try:
    import fastf1
    from fastf1 import get_session
    fastf1.Cache.enable_cache("outputs/f1_cache")
    fastf1.set_log_level("ERROR")
    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False
    print("Warning: FastF1 not available. Will use cached data only.")


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("outputs/multi_run_debug")
COMPARISON_DIR = OUTPUT_DIR / "comparisons"
STATS_DIR = OUTPUT_DIR / "statistics"
PLOTS_DIR = OUTPUT_DIR / "plots"

for directory in [OUTPUT_DIR, COMPARISON_DIR, STATS_DIR, PLOTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# TRACK CONFIGURATION
# =============================================================================

# F1 2022-2023 Season Tracks with current calibration values
TRACK_CONFIG = {
    # Track: (FastF1 name, year, laps, current_base_lap, difficulty)
    "Spain": ("Spain", 2022, 66, 89.0, "medium"),
    "Bahrain": ("Bahrain", 2022, 57, 91.0, "medium"),
    "Monaco": ("Monaco", 2022, 78, 76.0, "high"),
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
    "Azerbaijan": ("Azerbaijan", 2022, 51, 88.0, "high"),
    "Belgium": ("Belgium", 2022, 44, 102.0, "low"),
    "France": ("France", 2022, 53, 91.0, "medium"),
    "Mexico": ("Mexico", 2022, 71, 84.0, "medium"),
    "Miami": ("Miami", 2022, 57, 92.0, "high"),
    "Saudi Arabia": ("Saudi Arabia", 2022, 50, 90.0, "high"),
    "China": ("China", 2023, 56, 88.0, "medium"),
    "Qatar": ("Qatar", 2023, 57, 88.0, "medium"),
    "Las Vegas": ("Las Vegas", 2023, 50, 92.0, "high"),
}

ALL_TRACKS = list(TRACK_CONFIG.keys())


# =============================================================================
# FASTF1 DATA FETCHER
# =============================================================================

class FastF1DataFetcher:
    """
    Fetches real F1 data from FastF1 API for comparison.
    
    Key Metrics:
    - Qualifying fastest laps (pole position time)
    - Race pace (average lap times during race)
    - Pit stop data
    - Tyre strategies used
    
    Note: Real race data may contain incidents - these should be filtered
    when comparing for clean racing scenarios.
    """
    
    def __init__(self, year: int = 2022):
        self.year = year
        self._cache = {}
    
    def get_qualifying_fastest_lap(self, gp_name: str) -> Optional[float]:
        """Get pole position time for a Grand Prix."""
        if gp_name not in self._cache:
            self._cache[gp_name] = {}
        
        if "quali" in self._cache[gp_name]:
            return self._cache[gp_name]["quali"]
        
        if not FASTF1_AVAILABLE:
            return None
        
        try:
            session = get_session(self.year, gp_name, 'Q')
            session.load()
            
            # Get all drivers' qualifying times
            laps = session.laps
            qualifying_laps = laps[
                (laps['IsPersonalBest'] == True) & 
                (laps['PitOutTime'].isna()) & 
                (laps['PitInTime'].isna())
            ]
            
            if len(qualifying_laps) > 0:
                fastest = qualifying_laps['LapTime'].min().total_seconds()
                self._cache[gp_name]["quali"] = fastest
                return fastest
            
        except Exception as e:
            print(f"  Warning: Could not fetch qualifying data for {gp_name}: {e}")
        
        return None
    
    def get_race_pace_data(self, gp_name: str) -> Dict[str, Any]:
        """
        Get race pace data with incident filtering.
        
        Returns:
            Dict with:
            - avg_lap_time: Mean lap time (excluding slow laps)
            - pace_std: Standard deviation of lap times
            - min_lap: Fastest lap
            - max_lap: Slowest lap (excluding obvious incidents)
            - num_incidents: Count of anomalous laps detected
        """
        if gp_name not in self._cache:
            self._cache[gp_name] = {}
        
        if "race_pace" in self._cache[gp_name]:
            return self._cache[gp_name]["race_pace"]
        
        if not FASTF1_AVAILABLE:
            return None
        
        try:
            session = get_session(self.year, gp_name, 'R')
            session.load()
            
            laps = session.laps
            
            # Filter out laps with obvious incidents
            # Criteria: lap times > 110% of median or < 85% of median
            lap_times = laps['LapTime'].dropna()
            median_time = lap_times.median()
            
            # Clean laps: within 15% of median
            clean_mask = (
                (laps['LapTime'] >= median_time * 0.85) &
                (laps['LapTime'] <= median_time * 1.15) &
                (laps['PitOutTime'].isna()) &
                (laps['PitInTime'].isna())
            )
            
            clean_laps = laps[clean_mask]
            
            if len(clean_laps) > 0:
                avg_time = clean_laps['LapTime'].mean().total_seconds()
                pace_std = clean_laps['LapTime'].std().total_seconds()
                min_lap = clean_laps['LapTime'].min().total_seconds()
                max_lap = clean_laps['LapTime'].max().total_seconds()
                num_incidents = len(laps) - len(clean_laps)
                
                result = {
                    "avg_lap_time": avg_time,
                    "pace_std": pace_std,
                    "min_lap": min_lap,
                    "max_lap": max_lap,
                    "num_incidents": num_incidents,
                    "total_laps": len(laps),
                    "clean_laps": len(clean_laps)
                }
                
                self._cache[gp_name]["race_pace"] = result
                return result
        
        except Exception as e:
            print(f"  Warning: Could not fetch race data for {gp_name}: {e}")
        
        return None
    
    def get_pit_stop_data(self, gp_name: str) -> Dict[str, Any]:
        """Get pit stop statistics for a Grand Prix."""
        if gp_name not in self._cache:
            self._cache[gp_name] = {}
        
        if "pit_stops" in self._cache[gp_name]:
            return self._cache[gp_name]["pit_stops"]
        
        if not FASTF1_AVAILABLE:
            return None
        
        try:
            session = get_session(self.year, gp_name, 'R')
            session.load()
            
            # Get pit stops
            pit_stops = session.pit_stops
            
            if len(pit_stops) > 0:
                avg_pit_time = pit_stops['Duration'].mean().total_seconds()
                min_pit_time = pit_stops['Duration'].min().total_seconds()
                max_pit_time = pit_stops['Duration'].max().total_seconds()
                num_stops = len(pit_stops)
                
                result = {
                    "avg_pit_time": avg_pit_time,
                    "min_pit_time": min_pit_time,
                    "max_pit_time": max_pit_time,
                    "num_stops": num_stops
                }
                
                self._cache[gp_name]["pit_stops"] = result
                return result
        
        except Exception as e:
            print(f"  Warning: Could not fetch pit stop data for {gp_name}: {e}")
        
        return None


# =============================================================================
# MULTI-RUN SIMULATOR
# =============================================================================

class MultiRunSimulator:
    """
    Runs multiple race simulations and collects statistical data.
    
    Purpose:
    - Reduce variance from random components (dice rolls)
    - Establish confidence intervals for simulation outputs
    - Detect systematic biases in model parameters
    """
    
    def __init__(self, num_runs: int = 10, seed: Optional[int] = None):
        self.num_runs = num_runs
        self.seed = seed
        self.results = []
        self.stats = {}
    
    def run_track_simulation(
        self, 
        track_name: str, 
        csv_file: str,
        num_laps: int,
        track_chars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run multiple simulations for a single track.
        
        Returns:
            Comprehensive statistics including:
            - Mean, std, CI for total times per driver
            - Position distribution across runs
            - Pit strategy breakdown
            - Lap time distribution
        """
        print(f"\n{'='*60}")
        print(f"Running {self.num_runs} simulations for {track_name}")
        print(f"{'='*60}")
        
        # Load driver data
        driver_data = read_driver_data(csv_file)
        if not driver_data:
            print(f"Error: No driver data for {track_name}")
            return None
        
        # Calculate R/DR ranges
        r_values = [d["R_Value"] for d in driver_data.values()]
        dr_values = [d["DR_Value"] for d in driver_data.values()]
        r_max = max(r_values)
        r_min = min(r_values)
        dr_max = max(dr_values)
        dr_min = min(dr_values)
        
        # Load pit stop data
        pit_data = load_pit_stop_data()
        
        # Collect results from all runs
        all_race_results = []
        all_lap_times = defaultdict(list)
        all_positions = defaultdict(list)
        all_pit_events = []
        
        for run_idx in range(self.num_runs):
            if self.seed:
                seed = self.seed + run_idx
                random.seed(seed)
                np.random.seed(seed)
            else:
                random.seed()
                np.random.seed()
            
            print(f"  Run {run_idx + 1}/{self.num_runs}...")
            
            # Assign random grid positions for each run
            run_driver_data = driver_data.copy()
            driver_names = list(run_driver_data.keys())
            np.random.shuffle(driver_names)
            
            for i, driver in enumerate(driver_names):
                run_driver_data[driver]["grid_position"] = i + 1
            
            # Generate team strategies
            team_strategies_data = {}
            for team_name in set(d["Team"] for d in run_driver_data.values()):
                if team_name != "Unknown":
                    strategy = determine_pit_strategy(track_name, pit_data)
                    # Convert strategy string to int for generate_team_tyre_compounds
                    num_stops = int(strategy)
                    team_strategies_data[team_name] = {
                        "strategy": strategy,
                        "tyre_compounds_set": generate_team_tyre_compounds(
                            track_name, num_stops, num_laps
                        )
                    }
            
            # Map drivers to strategies
            driver_strategies = {}
            for driver, info in run_driver_data.items():
                team = info.get("Team", "Unknown")
                if team in team_strategies_data:
                    driver_strategies[driver] = team_strategies_data[team]
            
            # Run race simulation for each driver
            race_result = {}
            for driver_name, driver_info in run_driver_data.items():
                result = simulate_race_with_pit_stops(
                    driver_name,
                    driver_info,
                    num_laps,
                    track_name,
                    track_chars,
                    r_max,
                    dr_min,
                    dr_max,
                    pit_data,
                    team_strategies=driver_strategies
                )
                race_result[driver_name] = result
            
            # Sort by total time to get positions
            sorted_results = sorted(
                race_result.items(), 
                key=lambda x: x[1]["total_time"]
            )
            
            # Record positions and lap times
            for pos, (driver, result) in enumerate(sorted_results, 1):
                all_positions[driver].append(pos)
                all_lap_times[driver].extend(result["lap_times"])
                all_race_results.append({
                    "driver": driver,
                    "position": pos,
                    "total_time": result["total_time"],
                    "run": run_idx
                })
            
            # Collect pit events
            for driver, result in race_result.items():
                for event in result.get("pit_events", []):
                    event["driver"] = driver
                    event["run"] = run_idx
                    all_pit_events.append(event)
        
        # Calculate statistics
        driver_stats = {}
        for driver in driver_data.keys():
            positions = all_positions.get(driver, [])
            lap_times = all_lap_times.get(driver, [])
            
            if positions:
                driver_stats[driver] = {
                    "avg_position": np.mean(positions),
                    "position_std": np.std(positions),
                    "position_ci_95": (
                        np.mean(positions) - 1.96 * np.std(positions) / np.sqrt(len(positions)),
                        np.mean(positions) + 1.96 * np.std(positions) / np.sqrt(len(positions))
                    ),
                    "avg_lap_time": np.mean(lap_times) if lap_times else None,
                    "lap_time_std": np.std(lap_times) if lap_times else None,
                    "min_lap_time": np.min(lap_times) if lap_times else None,
                    "max_lap_time": np.max(lap_times) if lap_times else None,
                    "num_runs": len(positions),
                }
        
        # Overall statistics
        total_times = [r["total_time"] for r in all_race_results]
        
        overall_stats = {
            "num_runs": self.num_runs,
            "total_simulations": len(all_race_results),
            "avg_total_time": np.mean(total_times),
            "total_time_std": np.std(total_times),
            "min_total_time": np.min(total_times),
            "max_total_time": np.max(total_times),
        }
        
        return {
            "track": track_name,
            "num_laps": num_laps,
            "num_runs": self.num_runs,
            "driver_stats": driver_stats,
            "overall_stats": overall_stats,
            "all_positions": dict(all_positions),
            "all_lap_times": {k: v for k, v in all_lap_times.items()},
            "pit_events": all_pit_events,
            "race_results": all_race_results
        }


# =============================================================================
# SIMULATION COMPARATOR
# =============================================================================

class SimulationComparator:
    """
    Compares simulation outputs against real FastF1 data.
    
    Key Comparisons:
    1. Base lap times (qualifying pace)
    2. Race pace (average lap times)
    3. Total race time
    4. Position changes (overtaking)
    5. Pit stop times
    
    Ignores:
    - Incidents in real data (safety cars, crashes, etc.)
    - Unusual strategies (weather, equipment failures)
    """
    
    def __init__(self, year: int = 2022):
        self.year = year
        self.fastf1_fetcher = FastF1DataFetcher(year)
        self.comparisons = []
    
    def compare_track(
        self, 
        track_name: str, 
        sim_stats: Dict[str, Any],
        real_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare simulation statistics against real data.
        
        Returns:
            Comparison results with:
            - Time differences (base pace, race pace)
            - Position accuracy
            - Parameter adjustments needed
        """
        track_config = TRACK_CONFIG.get(track_name, {})
        base_lap_time = track_config.get("base_lap_time", 85.0)
        
        comparison = {
            "track": track_name,
            "year": self.year,
            "simulation": {},
            "real_data": {},
            "differences": {},
            "issues": [],
            "recommendations": []
        }
        
        # Get simulation statistics
        sim_avg_lap = []
        for driver, stats in sim_stats.get("driver_stats", {}).items():
            if stats.get("avg_lap_time"):
                sim_avg_lap.append(stats["avg_lap_time"])
        
        if sim_avg_lap:
            comparison["simulation"]["avg_lap_time"] = np.mean(sim_avg_lap)
            comparison["simulation"]["lap_time_std"] = np.std(sim_avg_lap)
        
        comparison["simulation"]["base_lap_reference"] = base_lap_time
        comparison["simulation"]["num_runs"] = sim_stats.get("num_runs", 0)
        
        # Get real data
        if real_data:
            if "avg_lap_time" in real_data:
                comparison["real_data"]["race_pace"] = real_data["avg_lap_time"]
            if "pace_std" in real_data:
                comparison["real_data"]["pace_std"] = real_data["pace_std"]
            
            quali_time = self.fastf1_fetcher.get_qualifying_fastest_lap(
                track_config.get("fastf1_name", track_name)
            )
            if quali_time:
                comparison["real_data"]["pole_time"] = quali_time
        
        # Calculate differences
        if "avg_lap_time" in comparison["simulation"] and "race_pace" in comparison["real_data"]:
            sim_pace = comparison["simulation"]["avg_lap_time"]
            real_pace = comparison["real_data"]["race_pace"]
            
            diff = sim_pace - real_pace
            diff_pct = (diff / real_pace) * 100 if real_pace else 0
            
            comparison["differences"]["race_pace"] = {
                "absolute": diff,
                "percentage": diff_pct,
                "status": "good" if abs(diff_pct) < 3 else "warning" if abs(diff_pct) < 10 else "error"
            }
            
            if abs(diff_pct) > 3:
                comparison["issues"].append(
                    f"Race pace off by {diff_pct:.1f}% ({diff:+.2f}s)"
                )
        
        # Check base lap time calibration
        sim_base = comparison["simulation"]["avg_lap_time"]
        ref_base = comparison["simulation"]["base_lap_reference"]
        
        if sim_base and ref_base:
            base_diff = sim_base - ref_base
            base_diff_pct = (base_diff / ref_base) * 100 if ref_base else 0
            
            comparison["differences"]["base_lap"] = {
                "absolute": base_diff,
                "percentage": base_diff_pct,
                "status": "good" if abs(base_diff_pct) < 5 else "warning" if abs(base_diff_pct) < 15 else "error"
            }
        
        # Position spread analysis
        position_stds = [
            stats["position_std"] 
            for stats in sim_stats.get("driver_stats", {}).values()
            if "position_std" in stats
        ]
        
        if position_stds:
            comparison["simulation"]["avg_position_std"] = np.mean(position_stds)
        
        # Generate recommendations
        comparison["recommendations"] = self._generate_recommendations(
            comparison, track_config
        )
        
        self.comparisons.append(comparison)
        return comparison
    
    def _generate_recommendations(
        self, 
        comparison: Dict[str, Any], 
        track_config: Dict[str, Any]
    ) -> List[str]:
        """Generate parameter adjustment recommendations."""
        recs = []
        
        # Check race pace
        if "race_pace" in comparison["differences"]:
            diff_pct = comparison["differences"]["race_pace"]["percentage"]
            
            if abs(diff_pct) > 10:
                if diff_pct > 0:
                    recs.append(
                        f"SIMULATION TOO SLOW: Increase base speed by ~{diff_pct:.1f}%"
                    )
                    recs.append("  - Reduce base_lap_time formula multiplier")
                    recs.append("  - Check tyre degradation rates")
                else:
                    recs.append(
                        f"SIMULATION TOO FAST: Decrease base speed by ~{abs(diff_pct):.1f}%"
                    )
                    recs.append("  - Increase base_lap_time formula multiplier")
                    recs.append("  - Consider adding more degradation")
        
        # Check base lap calibration
        if "base_lap" in comparison["differences"]:
            diff_pct = comparison["differences"]["base_lap"]["percentage"]
            
            if abs(diff_pct) > 10:
                if diff_pct > 0:
                    recs.append(
                        f"BASE LAP HIGH: Increase reference lap time by ~{diff_pct:.1f}%"
                    )
                else:
                    recs.append(
                        f"BASE LAP LOW: Decrease reference lap time by ~{abs(diff_pct):.1f}%"
                    )
        
        # Track-specific recommendations
        difficulty = track_config.get("difficulty", "medium")
        if difficulty == "high":
            recs.append("High difficulty track: Consider increased tyre degradation")
        elif difficulty == "low":
            recs.append("Low difficulty track: Reduced degradation expected")
        
        return recs


# =============================================================================
# DEBUG REPORT GENERATOR
# =============================================================================

class DebugReportGenerator:
    """
    Generates comprehensive debug reports with visualizations.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.reports = []
    
    def generate_track_report(
        self, 
        track_name: str,
        comparison: Dict[str, Any],
        sim_stats: Dict[str, Any]
    ) -> Path:
        """Generate a detailed debug report for a track."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{track_name.lower()}_debug_report_{timestamp}.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {track_name} Simulation Debug Report\n")
            f.write(f"Generated: {timestamp}\n\n")
            
            # 1. Summary
            f.write("## 1. Executive Summary\n\n")
            num_runs = sim_stats.get("num_runs", 0)
            f.write(f"- **Number of simulations:** {num_runs}\n")
            f.write(f"- **Track configuration:** {TRACK_CONFIG.get(track_name, {}).get('description', 'Unknown')}\n")
            f.write(f"- **Difficulty:** {TRACK_CONFIG.get(track_name, {}).get('difficulty', 'unknown')}\n\n")
            
            # 2. Simulation Statistics
            f.write("## 2. Simulation Statistics\n\n")
            
            # Overall stats
            overall = sim_stats.get("overall_stats", {})
            f.write("### Overall Race Statistics\n\n")
            f.write(f"- **Average total race time:** {overall.get('avg_total_time', 0):.1f}s\n")
            f.write(f"- **Total time std dev:** {overall.get('total_time_std', 0):.1f}s\n")
            f.write(f"- **Min total time:** {overall.get('min_total_time', 0):.1f}s\n")
            f.write(f"- **Max total time:** {overall.get('max_total_time', 0):.1f}s\n\n")
            
            # Driver stats
            f.write("### Driver Performance Statistics\n\n")
            f.write("| Driver | Avg Position | Position Std | Avg Lap Time | Lap Time Std | Min Lap | Max Lap |\n")
            f.write("|--------|-------------|--------------|--------------|--------------|---------|---------|\n")
            
            for driver, stats in sorted(
                sim_stats.get("driver_stats", {}).items(),
                key=lambda x: x[1].get("avg_position", 999)
            ):
                pos = stats.get("avg_position", "N/A")
                pos_std = stats.get("position_std", 0)
                avg_lap = stats.get("avg_lap_time", "N/A")
                lap_std = stats.get("lap_time_std", 0)
                min_lap = stats.get("min_lap_time", "N/A")
                max_lap = stats.get("max_lap_time", "N/A")
                
                pos_str = f"{pos:.1f}" if isinstance(pos, float) else str(pos)
                lap_str = f"{avg_lap:.2f}" if isinstance(avg_lap, float) else str(avg_lap)
                
                f.write(f"| {driver} | {pos_str} ± {pos_std:.1f} | {lap_str} ± {lap_std:.2f} | {min_lap:.2f} | {max_lap:.2f} |\n")
            
            # 3. Comparison with Real Data
            f.write("\n## 3. Comparison with Real Data (FastF1)\n\n")
            
            if comparison.get("real_data"):
                f.write("### Real Data Metrics\n\n")
                for key, value in comparison["real_data"].items():
                    if isinstance(value, float):
                        f.write(f"- **{key}:** {value:.3f}s\n")
                    else:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")
            
            if comparison.get("simulation"):
                f.write("### Simulation Metrics\n\n")
                for key, value in comparison["simulation"].items():
                    if isinstance(value, float):
                        f.write(f"- **{key}:** {value:.3f}s\n")
                    else:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")
            
            if comparison.get("differences"):
                f.write("### Differences\n\n")
                f.write("| Metric | Absolute Diff | Percentage | Status |\n")
                f.write("|--------|---------------|------------|--------|\n")
                
                for metric, diff_data in comparison["differences"].items():
                    abs_diff = diff_data.get("absolute", 0)
                    pct = diff_data.get("percentage", 0)
                    status = diff_data.get("status", "unknown")
                    status_emoji = "✅" if status == "good" else "⚠️" if status == "warning" else "❌"
                    
                    f.write(f"| {metric} | {abs_diff:+.2f}s | {pct:+.1f}% | {status_emoji} |\n")
                
                f.write("\n")
            
            # 4. Issues Found
            if comparison.get("issues"):
                f.write("## 4. Issues Detected\n\n")
                for i, issue in enumerate(comparison["issues"], 1):
                    f.write(f"{i}. {issue}\n")
                f.write("\n")
            
            # 5. Recommendations
            if comparison.get("recommendations"):
                f.write("## 5. Calibration Recommendations\n\n")
                for i, rec in enumerate(comparison["recommendations"], 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")
            
            # 6. Position Distribution
            f.write("## 6. Position Distribution Analysis\n\n")
            
            all_positions = sim_stats.get("all_positions", {})
            if all_positions:
                f.write("| Driver | Position Distribution (Top 3 Finishes) |\n")
                f.write("|--------|---------------------------------------|\n")
                
                for driver, positions in sorted(
                    all_positions.items(),
                    key=lambda x: np.mean(x[1])
                ):
                    pos_counts = defaultdict(int)
                    for p in positions:
                        pos_counts[p] += 1
                    
                    top3 = sum(pos_counts.get(i, 0) for i in [1, 2, 3])
                    pct = (top3 / len(positions)) * 100 if positions else 0
                    
                    f.write(f"| {driver} | {top3}/{len(positions)} ({pct:.0f}%) |\n")
                
                f.write("\n")
            
            # 7. Pit Stop Analysis
            f.write("## 7. Pit Stop Analysis\n\n")
            
            pit_events = sim_stats.get("pit_events", [])
            if pit_events:
                pit_times = [e.get("pit_time", 0) for e in pit_events if "pit_time" in e]
                
                if pit_times:
                    f.write(f"- **Total pit stops:** {len(pit_times)}\n")
                    f.write(f"- **Average pit time:** {np.mean(pit_times):.2f}s\n")
                    f.write(f"- **Min pit time:** {np.min(pit_times):.2f}s\n")
                    f.write(f"- **Max pit time:** {np.max(pit_times):.2f}s\n")
                    f.write(f"- **Pit time std dev:** {np.std(pit_times):.2f}s\n\n")
                    
                    # By lap
                    laps = defaultdict(list)
                    for e in pit_events:
                        if "lap" in e:
                            laps[e["lap"]].append(e.get("pit_time", 0))
                    
                    if laps:
                        f.write("### Pit Stops by Lap\n\n")
                        f.write("| Lap | Number of Stops | Avg Time |\n")
                        f.write("|-----|-----------------|----------|\n")
                        
                        for lap in sorted(laps.keys()):
                            f.write(f"| {lap} | {len(laps[lap])} | {np.mean(laps[lap]):.2f}s |\n")
                        
                        f.write("\n")
            else:
                f.write("No pit stop data available.\n\n")
        
        self.reports.append(filepath)
        return filepath
    
    def generate_summary_report(
        self, 
        all_comparisons: List[Dict[str, Any]],
        output_name: str = "multi_run_summary.md"
    ) -> Path:
        """Generate a summary report across all tracks."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / output_name
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Multi-Run Simulation Debug Summary\n")
            f.write(f"Generated: {timestamp}\n\n")
            
            f.write("## Track-by-Track Summary\n\n")
            
            for comp in all_comparisons:
                track = comp.get("track", "Unknown")
                f.write(f"### {track}\n\n")
                
                if "differences" in comp:
                    f.write("| Metric | Diff | Status |\n")
                    f.write("|--------|------|--------|\n")
                    
                    for metric, diff_data in comp["differences"].items():
                        abs_diff = diff_data.get("absolute", 0)
                        pct = diff_data.get("percentage", 0)
                        status = diff_data.get("status", "unknown")
                        status_emoji = "✅" if status == "good" else "⚠️" if status == "warning" else "❌"
                        
                        f.write(f"| {metric} | {pct:+.1f}% | {status_emoji} |\n")
                
                f.write("\n")
                
                if comp.get("issues"):
                    f.write("**Issues:**\n")
                    for issue in comp["issues"]:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                
                if comp.get("recommendations"):
                    f.write("**Recommendations:**\n")
                    for rec in comp["recommendations"]:
                        f.write(f"- {rec}\n")
                    f.write("\n")
            
            # Overall statistics
            f.write("\n## Overall Performance\n\n")
            
            good_count = 0
            warning_count = 0
            error_count = 0
            
            for comp in all_comparisons:
                for diff_data in comp.get("differences", {}).values():
                    status = diff_data.get("status", "unknown")
                    if status == "good":
                        good_count += 1
                    elif status == "warning":
                        warning_count += 1
                    elif status == "error":
                        error_count += 1
            
            total = good_count + warning_count + error_count
            
            f.write(f"- **Good matches:** {good_count}/{total} ({100*good_count/total:.0f}%)\n")
            f.write(f"- **Warnings:** {warning_count}/{total} ({100*warning_count/total:.0f}%)\n")
            f.write(f"- **Errors:** {error_count}/{total} ({100*error_count/total:.0f}%)\n")
        
        return filepath


# =============================================================================
# VISUALIZATION
# =============================================================================

class DebugVisualizer:
    """
    Creates debug visualizations for simulation analysis.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def plot_position_distribution(
        self, 
        all_positions: Dict[str, List[int]], 
        track_name: str
    ) -> Path:
        """Plot position distribution for each driver."""
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        drivers = list(all_positions.keys())
        positions_data = [all_positions[d] for d in drivers]
        
        # Create violin plot
        parts = ax.violinplot(positions_data, positions=range(1, len(drivers) + 1), 
                             showmeans=True, showmedians=True)
        
        # Customize colors
        for pc in parts['bodies']:
            pc.set_facecolor('steelblue')
            pc.set_alpha(0.7)
        
        ax.set_xticks(range(1, len(drivers) + 1))
        ax.set_xticklabels(drivers, rotation=45, ha='right')
        ax.set_ylabel('Position')
        ax.set_title(f'{track_name} - Position Distribution (Multi-Run)')
        ax.invert_yaxis()  # Position 1 at top
        ax.grid(True, alpha=0.3)
        
        filepath = self.output_dir / f"{track_name.lower()}_position_dist.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_lap_time_distribution(
        self, 
        all_lap_times: Dict[str, List[float]], 
        track_name: str
    ) -> Path:
        """Plot lap time distribution by driver."""
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        drivers = list(all_lap_times.keys())
        lap_data = [all_lap_times[d] for d in drivers]
        
        # Create box plot
        bp = ax.boxplot(lap_data, labels=drivers, patch_artist=True)
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(drivers)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel('Lap Time (seconds)')
        ax.set_title(f'{track_name} - Lap Time Distribution (Multi-Run)')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
        
        filepath = self.output_dir / f"{track_name.lower()}_laptime_dist.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_comparison_heatmap(
        self, 
        comparisons: List[Dict[str, Any]], 
        track_names: List[str]
    ) -> Path:
        """Create a heatmap comparing all tracks."""
        
        # Build data matrix
        data = []
        for comp in comparisons:
            row = []
            for metric in ["race_pace", "base_lap"]:
                if metric in comp.get("differences", {}):
                    row.append(abs(comp["differences"][metric].get("percentage", 0)))
                else:
                    row.append(0)
            data.append(row)
        
        if not data:
            return None
        
        df = pd.DataFrame(data, 
                         index=track_names, 
                         columns=["Race Pace Error %", "Base Lap Error %"])
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        sns.heatmap(df, annot=True, fmt='.1f', cmap='RdYlGn_r', 
                   ax=ax, cbar_kws={'label': 'Error %'})
        
        ax.set_title('Multi-Track Simulation Error Heatmap')
        ax.set_ylabel('Track')
        ax.set_xlabel('Metric')
        
        filepath = self.output_dir / "comparison_heatmap.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def plot_track_comparison_bar(
        self, 
        comparisons: List[Dict[str, Any]], 
        track_names: List[str]
    ) -> Path:
        """Create a bar chart comparing race pace errors across tracks."""
        
        errors = []
        for comp in comparisons:
            if "race_pace" in comp.get("differences", {}):
                errors.append(comp["differences"]["race_pace"].get("percentage", 0))
            else:
                errors.append(0)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = ['green' if abs(e) < 3 else 'orange' if abs(e) < 10 else 'red' for e in errors]
        bars = ax.bar(track_names, errors, color=colors, alpha=0.7)
        
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=3, color='green', linestyle='--', linewidth=1, alpha=0.5, label='±3% target')
        ax.axhline(y=-3, color='green', linestyle='--', linewidth=1, alpha=0.5)
        
        ax.set_ylabel('Race Pace Error (%)')
        ax.set_title('Race Pace Error by Track (Simulation vs FastF1)')
        ax.tick_params(axis='x', rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar, error in zip(bars, errors):
            height = bar.get_height()
            ax.annotate(f'{error:+.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
        
        filepath = self.output_dir / "track_comparison_bar.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath


# =============================================================================
# MAIN DEBUG RUNNER
# =============================================================================

def run_multi_run_debug(
    tracks: List[str] = None,
    num_runs: int = 10,
    compare_fastf1: bool = True,
    seed: int = None,
    generate_plots: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for multi-run debug simulations.
    
    Args:
        tracks: List of track names to simulate (default: all)
        num_runs: Number of simulations per track
        compare_fastf1: Whether to fetch real data for comparison
        seed: Random seed for reproducibility
        generate_plots: Whether to generate visualization plots
    
    Returns:
        Dictionary with all results and file paths
    """
    
    print("\n" + "="*70)
    print("F1 MULTI-RUN SIMULATION DEBUG SYSTEM")
    print("="*70)
    
    if tracks is None:
        tracks = ALL_TRACKS
    
    print(f"\nConfiguration:")
    print(f"  - Tracks: {', '.join(tracks)}")
    print(f"  - Runs per track: {num_runs}")
    print(f"  - Compare with FastF1: {compare_fastf1}")
    print(f"  - Random seed: {seed or 'random'}")
    print(f"  - Output directory: {OUTPUT_DIR}")
    
    # Initialize components
    simulator = MultiRunSimulator(num_runs=num_runs, seed=seed)
    comparator = SimulationComparator()
    report_gen = DebugReportGenerator(OUTPUT_DIR)
    
    if generate_plots:
        visualizer = DebugVisualizer(PLOTS_DIR)
    
    all_results = {}
    all_comparisons = []
    all_stats = {}
    
    for track_name in tracks:
        print(f"\n{'='*60}")
        print(f"Processing: {track_name}")
        print(f"{'='*60}")
        
        # Get track configuration
        config = TRACK_CONFIG.get(track_name, {})
        year = config.get("year", 2022)
        laps = config.get("laps", 66)
        csv_file = f"outputs/tables/{track_name}.csv"
        
        # Check if CSV exists
        if not os.path.exists(csv_file):
            print(f"  Warning: CSV file not found: {csv_file}")
            # Try alternative naming
            alt_files = [
                f"outputs/tables/{config.get('fastf1_name', track_name)}.csv",
                f"outputs/tables/{track_name.lower()}.csv"
            ]
            for alt in alt_files:
                if os.path.exists(alt):
                    csv_file = alt
                    print(f"  Using alternative: {csv_file}")
                    break
            else:
                print(f"  Error: No valid CSV file found for {track_name}")
                continue
        
        # Get track characteristics
        track_chars = get_track_characteristics()
        track_key = track_name.lower()
        if track_key not in track_chars:
            print(f"  Warning: Track characteristics not found for {track_key}")
            # Use default
            track_chars[track_key] = {
                "abrasion": 3, "stress": 3, "evolution": 3,
                "pressure": {"C1": 22.0, "C2": 21.5, "C3": 21.0, "C4": 20.5, "C5": 20.0}
            }
        
        current_track_chars = track_chars[track_key]
        
        # Run multi-run simulation
        sim_stats = simulator.run_track_simulation(
            track_name, csv_file, laps, current_track_chars
        )
        
        if not sim_stats:
            print(f"  Error: Simulation failed for {track_name}")
            continue
        
        all_stats[track_name] = sim_stats
        
        # Get real data if requested
        real_data = None
        if compare_fastf1:
            print(f"\nFetching FastF1 data for {track_name}...")
            fastf1_fetcher = FastF1DataFetcher(year)
            real_data = fastf1_fetcher.get_race_pace_data(
                config.get("fastf1_name", track_name)
            )
            
            if real_data:
                print(f"  Real race pace: {real_data.get('avg_lap_time', 'N/A'):.3f}s")
                print(f"  Clean laps analyzed: {real_data.get('clean_laps', 'N/A')}")
            else:
                print("  No real data available (will use reference values only)")
        
        # Compare with real data
        comparison = comparator.compare_track(track_name, sim_stats, real_data)
        all_comparisons.append(comparison)
        
        # Generate report
        report_path = report_gen.generate_track_report(track_name, comparison, sim_stats)
        print(f"  Report: {report_path}")
        
        # Generate visualizations
        if generate_plots:
            # Position distribution
            pos_path = visualizer.plot_position_distribution(
                sim_stats.get("all_positions", {}), track_name
            )
            print(f"  Position plot: {pos_path}")
            
            # Lap time distribution
            lap_path = visualizer.plot_lap_time_distribution(
                sim_stats.get("all_lap_times", {}), track_name
            )
            print(f"  Lap time plot: {lap_path}")
    
    # Generate summary report
    print(f"\n{'='*60}")
    print("Generating Summary Report...")
    print(f"{'='*60}")
    
    summary_path = report_gen.generate_summary_report(all_comparisons)
    print(f"  Summary: {summary_path}")
    
    # Generate overall comparison plots
    if generate_plots and all_comparisons:
        heatmap_path = visualizer.plot_comparison_heatmap(
            all_comparisons, list(all_stats.keys())
        )
        if heatmap_path:
            print(f"  Heatmap: {heatmap_path}")
        
        bar_path = visualizer.plot_track_comparison_bar(
            all_comparisons, list(all_stats.keys())
        )
        if bar_path:
            print(f"  Comparison bar: {bar_path}")
    
    # Save results to JSON
    results_json = OUTPUT_DIR / "debug_results.json"
    with open(results_json, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "tracks": tracks,
                "num_runs": num_runs,
                "compare_fastf1": compare_fastf1,
                "seed": seed
            },
            "comparisons": all_comparisons,
            "statistics": {
                k: {
                    "overall_stats": v.get("overall_stats", {}),
                    "num_runs": v.get("num_runs", 0),
                    "num_drivers": len(v.get("driver_stats", {}))
                }
                for k, v in all_stats.items()
            }
        }, f, indent=2, default=str)
    
    print(f"  Results JSON: {results_json}")
    
    # Print summary
    print(f"\n{'='*70}")
    print("DEBUG RUN COMPLETE")
    print(f"{'='*70}")
    
    print("\nKey Findings:")
    for comp in all_comparisons:
        track = comp.get("track", "Unknown")
        print(f"\n  {track}:")
        
        for metric, diff_data in comp.get("differences", {}).items():
            pct = diff_data.get("percentage", 0)
            status = diff_data.get("status", "unknown")
            status_emoji = "✅" if status == "good" else "⚠️" if status == "warning" else "❌"
            
            print(f"    {metric}: {pct:+.1f}% {status_emoji}")
        
        if comp.get("issues"):
            print("    Issues:")
            for issue in comp["issues"]:
                print(f"      - {issue}")
    
    return {
        "tracks": tracks,
        "num_runs": num_runs,
        "comparisons": all_comparisons,
        "statistics": all_stats,
        "reports": report_gen.reports,
        "summary_path": summary_path
    }


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main(argv=None):
    """Command-line interface for the debug system."""
    
    parser = argparse.ArgumentParser(
        description="F1 Multi-Run Simulation Debug System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 10 simulations for Spain and Bahrain
  python -m debug.multi_run_debug --tracks Spain Bahrain --runs 10
  
  # Run 5 simulations for all tracks
  python -m debug.multi_run_debug --all-tracks --runs 5
  
  # Run with FastF1 comparison
  python -m debug.multi_run_debug --tracks Spain Monaco --runs 10 --compare-fastf1
  
  # Reproducible run with specific seed
  python -m debug.multi_run_debug --tracks Spain --runs 20 --seed 42
  
  # Generate plots only (no comparison)
  python -m debug.multi_run_debug --all-tracks --runs 3 --no-plots
        """
    )
    
    parser.add_argument(
        "--tracks", "-t",
        nargs="+",
        help="List of tracks to simulate"
    )
    parser.add_argument(
        "--all-tracks", "-a",
        action="store_true",
        help="Run all available tracks"
    )
    parser.add_argument(
        "--runs", "-r",
        type=int,
        default=10,
        help="Number of simulations per track (default: 10)"
    )
    parser.add_argument(
        "--compare-fastf1", "-c",
        action="store_true",
        help="Fetch and compare with FastF1 real data"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating visualization plots"
    )
    
    args = parser.parse_args(argv)
    
    # Determine tracks
    if args.all_tracks:
        tracks = None  # Use all tracks
    elif args.tracks:
        tracks = args.tracks
    else:
        tracks = ["Spain", "Bahrain", "Monaco"]  # Default tracks
    
    # Run debug
    results = run_multi_run_debug(
        tracks=tracks,
        num_runs=args.runs,
        compare_fastf1=args.compare_fastf1,
        seed=args.seed,
        generate_plots=not args.no_plots
    )
    
    return results


if __name__ == "__main__":
    main(sys.argv[1:])
