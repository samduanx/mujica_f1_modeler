#!/usr/bin/env python3
"""
Calculate F1 Track Coefficients using FastF1 data.

C(M) - Mechanical (Braking demand):
- Count corners where max brake G > 4G vs corners where brake G > 2G
- ratio = corners_gt_4G / corners_gt_2G
- if pct < 35%: C(M) = 1.0
- if 35% <= pct <= 40%: C(M) = 1.05
- if pct > 40%: C(M) = 1.1

C(P) - Power (Full throttle percentage):
- Full throttle = throttle >= 0.98
- full_throttle_pct = (count of throttle >= 0.98) / total_samples * 100
- if full_throttle_pct <= 70%: C(P) = 1.0
- if 70% < full_throttle_pct < 80%: C(P) = 1.05
- if full_throttle_pct >= 80%: C(P) = 1.1
"""

import os
import csv
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import fastf1
from fastf1 import Cache
from tqdm import tqdm

warnings.filterwarnings("ignore")

# Configure FastF1 caching
CACHE_DIR = Path.home() / "fastf1_cache"
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

# Track mapping: Display name -> FastF1 event name
TRACKS = {
    "Bahrain": "Bahrain Grand Prix",
    "Saudi Arabia": "Saudi Arabian Grand Prix",
    "Australia": "Australian Grand Prix",
    "Italy (Imola)": "Emilia Romagna Grand Prix",
    "Miami": "Miami Grand Prix",
    "Spain": "Spanish Grand Prix",
    "Monaco": "Monaco Grand Prix",
    "Azerbaijan": "Azerbaijan Grand Prix",
    "Canada": "Canadian Grand Prix",
    "UK (Silverstone)": "British Grand Prix",
    "Austria": "Austrian Grand Prix",
    "France": "French Grand Prix",
    "Hungary": "Hungarian Grand Prix",
    "Belgium": "Belgian Grand Prix",
    "Netherlands": "Dutch Grand Prix",
    "Italy (Monza)": "Italian Grand Prix",
    "Singapore": "Singapore Grand Prix",
    "Japan": "Japanese Grand Prix",
    "USA": "United States Grand Prix",
    "Mexico": "Mexican Grand Prix",
    "Brazil": "Brazilian Grand Prix",
    "Abu Dhabi": "Abu Dhabi Grand Prix",
    "Qatar": "Qatar Grand Prix",
    "China": "Chinese Grand Prix",
}

YEARS = [2022, 2023, 2024, 2025]


def get_session(year: int, event_name: str):
    """Get a race session for the given year and event."""
    try:
        schedule = fastf1.get_event_schedule(year)
        event = schedule[schedule["EventName"] == event_name]
        if event.empty:
            print(f"  Warning: Event '{event_name}' not found in {year}")
            return None
        event = event.iloc[0]
        session = event.get_session("Race")
        session.load()
        return session
    except Exception as e:
        print(f"  Warning: Could not load {event_name} {year}: {e}")
        return None


def get_median_lap_telemetry(session):
    """Get telemetry from the median lap (by lap time)."""
    if session is None:
        return None

    try:
        laps = session.laps
        laps = laps.dropna(subset=["LapTime"])

        if laps.empty:
            return None

        # Get median lap time
        median_lap_time = laps["LapTime"].median()
        median_lap = laps[laps["LapTime"] == median_lap_time].iloc[0]

        # Get telemetry for this lap
        car_data = median_lap.get_car_data()

        if car_data.empty:
            return None

        return car_data
    except Exception as e:
        print(f"  Warning: Could not get telemetry: {e}")
        return None


def calculate_brake_g(telemetry: pd.DataFrame) -> np.ndarray:
    """
    Calculate brake G-forces from speed derivative.
    G = |dV/dt| / 9.81
    """
    if telemetry is None or telemetry.empty:
        return np.array([])

    # Get speed in m/s
    speed_ms = telemetry["Speed"].values / 3.6  # Convert km/h to m/s

    # Get time in seconds
    time_s = telemetry["Time"].dt.total_seconds().values

    if len(speed_ms) < 2:
        return np.array([])

    # Calculate derivative dV/dt
    dv_dt = np.gradient(speed_ms, time_s)

    # Calculate G-forces (absolute value of deceleration)
    brake_g = np.abs(dv_dt) / 9.81

    return brake_g


def identify_braking_corners(telemetry: pd.DataFrame, brake_g: np.ndarray) -> dict:
    """
    Identify corners based on braking zones.
    """
    if telemetry is None or len(brake_g) == 0:
        return {"gt_2g": 0, "gt_4g": 0}

    # Find braking zones where brake G > 2G
    braking_2g = brake_g > 2.0
    braking_4g = brake_g > 4.0

    # Use a simple threshold approach - count sustained braking events
    # A corner is identified where brake pressure is high
    brake_pressure = (
        telemetry["Brake"].values
        if "Brake" in telemetry.columns
        else np.zeros(len(brake_g))
    )

    # Count corners: look for sustained braking (brake pressure > 0 and brake G > threshold)
    # Use a simple algorithm: find local maxima in brake G above thresholds
    from scipy.signal import find_peaks

    # Find peaks in braking above 2G
    peaks_2g, _ = find_peaks(brake_g, height=2.0, distance=20)
    corners_gt_2g = len(peaks_2g)

    # Find peaks in braking above 4G
    peaks_4g, _ = find_peaks(brake_g, height=4.0, distance=20)
    corners_gt_4g = len(peaks_4g)

    return {"gt_2g": corners_gt_2g, "gt_4g": corners_gt_4g}


def calculate_cm(cm_metrics: dict) -> float:
    """
    Calculate C(M) from brake corner counts.
    """
    corners_gt_2g = cm_metrics.get("gt_2g", 0)
    corners_gt_4g = cm_metrics.get("gt_4g", 0)

    if corners_gt_2g == 0:
        return 1.0  # Default if no data

    ratio = corners_gt_4g / corners_gt_2g

    if ratio < 0.35:
        return 1.0
    elif ratio <= 0.40:
        return 1.05
    else:
        return 1.1


def calculate_cp(telemetry: pd.DataFrame) -> float:
    """
    Calculate C(P) from full throttle percentage.
    Full throttle = throttle >= 0.98
    """
    if telemetry is None or telemetry.empty:
        return 1.0

    if "Throttle" not in telemetry.columns:
        return 1.0

    throttle = telemetry["Throttle"].values
    total_samples = len(throttle)

    if total_samples == 0:
        return 1.0

    full_throttle_count = np.sum(throttle >= 0.98)
    full_throttle_pct = (full_throttle_count / total_samples) * 100

    if full_throttle_pct <= 70:
        return 1.0
    elif full_throttle_pct < 80:
        return 1.05
    else:
        return 1.1


def process_track(track_name: str, event_name: str, years: list) -> dict:
    """
    Process a single track across multiple years and return averaged metrics.
    """
    all_braking_metrics = []
    all_full_throttle_pcts = []
    years_data = []

    for year in years:
        session = get_session(year, event_name)
        if session is None:
            continue

        telemetry = get_median_lap_telemetry(session)
        if telemetry is None or telemetry.empty:
            continue

        # Calculate brake G
        brake_g = calculate_brake_g(telemetry)
        braking_metrics = identify_braking_corners(telemetry, brake_g)

        # Calculate full throttle percentage
        if "Throttle" in telemetry.columns:
            throttle = telemetry["Throttle"].values
            ft_count = np.sum(throttle >= 0.98)
            ft_pct = (ft_count / len(throttle)) * 100
            all_full_throttle_pcts.append(ft_pct)

        all_braking_metrics.append(braking_metrics)
        years_data.append(year)

    if not all_braking_metrics:
        return None

    # Average across years
    avg_gt_2g = np.mean([m["gt_2g"] for m in all_braking_metrics])
    avg_gt_4g = np.mean([m["gt_4g"] for m in all_braking_metrics])

    avg_ft_pct = np.mean(all_full_throttle_pcts) if all_full_throttle_pcts else 0

    # Calculate final metrics
    cm_metrics = {"gt_2g": avg_gt_2g, "gt_4g": avg_gt_4g}
    cm = calculate_cm(cm_metrics)
    cp = calculate_cp_from_pct(avg_ft_pct)

    return {
        "track": track_name,
        "cm": cm,
        "cp": cp,
        "ca": 1.0,  # Placeholder - would need Pirelli data
        "years_analyzed": years_data,
        "corners_gt_2g": avg_gt_2g,
        "corners_gt_4g": avg_gt_4g,
        "full_throttle_pct": avg_ft_pct,
    }


def calculate_cp_from_pct(ft_pct: float) -> float:
    """Calculate C(P) from full throttle percentage."""
    if ft_pct <= 70:
        return 1.0
    elif ft_pct < 80:
        return 1.05
    else:
        return 1.1


def main():
    """Main function to calculate track coefficients."""
    print("=" * 60)
    print("F1 Track Coefficient Calculator using FastF1")
    print("=" * 60)
    print(f"Cache directory: {CACHE_DIR}")
    print(f"Years: {YEARS}")
    print(f"Tracks: {len(TRACKS)}")
    print("=" * 60)

    results = []

    for track_name, event_name in tqdm(TRACKS.items(), desc="Processing tracks"):
        print(f"\n{track_name}:")

        result = process_track(track_name, event_name, YEARS)

        if result:
            results.append(result)
            print(f"  Years: {result['years_analyzed']}")
            print(
                f"  C(M): {result['cm']} (corners >2G: {result['corners_gt_2g']:.1f}, >4G: {result['corners_gt_4g']:.1f})"
            )
            print(
                f"  C(P): {result['cp']} (full throttle: {result['full_throttle_pct']:.1f}%)"
            )
        else:
            print(f"  No data available")
            # Add with default values
            results.append(
                {
                    "track": track_name,
                    "cm": 1.0,
                    "cp": 1.0,
                    "ca": 1.0,
                    "years_analyzed": [],
                    "corners_gt_2g": 0,
                    "corners_gt_4g": 0,
                    "full_throttle_pct": 0,
                }
            )

    # Write results to CSV
    output_path = Path("docs/track_coefficients_fastf1.csv")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Track",
                "C(M)",
                "C(P)",
                "C(A)",
                "Years_Analyzed",
                "Corners_gt_2G",
                "Corners_gt_4G",
                "Full_Throttle_Pct",
            ]
        )

        for r in results:
            writer.writerow(
                [
                    r["track"],
                    r["cm"],
                    r["cp"],
                    r["ca"],
                    ", ".join(map(str, r["years_analyzed"])),
                    f"{r['corners_gt_2g']:.1f}",
                    f"{r['corners_gt_4g']:.1f}",
                    f"{r['full_throttle_pct']:.1f}",
                ]
            )

    print(f"\n{'=' * 60}")
    print(f"Results written to: {output_path}")
    print(f"Total tracks processed: {len(results)}")
    print(f"{'=' * 60}")

    # Print summary table
    print("\nSummary:")
    print("-" * 50)
    print(f"{'Track':<20} {'C(M)':<8} {'C(P)':<8} {'C(A)':<8}")
    print("-" * 50)
    for r in results:
        print(f"{r['track']:<20} {r['cm']:<8.2f} {r['cp']:<8.2f} {r['ca']:<8.2f}")


if __name__ == "__main__":
    main()
