"""
Calibrate tyre compound pace deltas and degradation trends from cached FastF1 race data.

Usage:
    uv run python scripts/calibrate_tyre_fastf1.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import fastf1


@dataclass
class CompoundStats:
    slopes: List[float]
    medians: List[float]


DEFAULT_PACE = {
    "HARD": 0.26,
    "MEDIUM": 0.0,
    "SOFT": -0.34,
    "C1": 0.42,
    "C2": 0.24,
    "C3": 0.0,
    "C4": -0.22,
    "C5": -0.44,
}

DEFAULT_TYRE_PARAMS = {
    "HARD": {
        "base_lap": 24,
        "base_degradation": 0.032,
        "cliff_lap": 24,
        "cliff_severity": 0.15,
    },
    "MEDIUM": {
        "base_lap": 20,
        "base_degradation": 0.036,
        "cliff_lap": 19,
        "cliff_severity": 0.16,
    },
    "SOFT": {
        "base_lap": 16,
        "base_degradation": 0.041,
        "cliff_lap": 15,
        "cliff_severity": 0.17,
    },
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
}

EVENT_CANDIDATES: List[Tuple[int, List[str]]] = [
    (2024, ["Bahrain", "Bahrain Grand Prix"]),
    (2024, ["Monaco", "Monaco Grand Prix"]),
    (2024, ["Spain", "Spanish Grand Prix"]),
    (2024, ["Italy", "Italian Grand Prix", "Monza"]),
]


def _find_cache_path() -> str:
    candidates = ["f1_cache", os.path.join("outputs", "f1_cache")]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return "f1_cache"


def _load_session(year: int, names: List[str]):
    for name in names:
        try:
            session = fastf1.get_session(year, name, "R")
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            return session, name
        except Exception:
            continue
    return None, None


def _fit_slope(tyre_life: np.ndarray, lap_time_s: np.ndarray) -> float | None:
    if len(tyre_life) < 6:
        return None
    if np.std(tyre_life) < 1e-6:
        return None
    slope, _ = np.polyfit(tyre_life, lap_time_s, 1)
    if slope <= 0 or slope > 0.15:
        return None
    return float(slope)


def main() -> int:
    cache_path = _find_cache_path()
    fastf1.Cache.enable_cache(cache_path)

    compound_data: Dict[str, CompoundStats] = {
        "HARD": CompoundStats([], []),
        "MEDIUM": CompoundStats([], []),
        "SOFT": CompoundStats([], []),
    }
    sessions_used: List[str] = []

    for year, candidates in EVENT_CANDIDATES:
        session, used_name = _load_session(year, candidates)
        if session is None:
            continue

        sessions_used.append(f"{year} {used_name}")
        laps = session.laps.copy()

        if laps.empty:
            continue

        laps = laps[laps["LapTime"].notna()]
        laps = laps[laps["Compound"].isin(["SOFT", "MEDIUM", "HARD"])]
        laps = laps[laps["IsAccurate"] == True]

        # Prefer green-flag style laps where available.
        if "TrackStatus" in laps.columns:
            laps = laps[laps["TrackStatus"].astype(str) == "1"]

        if "PitInTime" in laps.columns:
            laps = laps[laps["PitInTime"].isna()]
        if "PitOutTime" in laps.columns:
            laps = laps[laps["PitOutTime"].isna()]

        laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

        for (driver, stint, compound), group in laps.groupby(
            ["Driver", "Stint", "Compound"]
        ):
            if group.empty or len(group) < 6:
                continue

            group = group.sort_values("LapNumber")
            if "TyreLife" in group.columns and group["TyreLife"].notna().sum() >= 6:
                x = group["TyreLife"].to_numpy(dtype=float)
            else:
                x = np.arange(1, len(group) + 1, dtype=float)

            y = group["LapTimeSeconds"].to_numpy(dtype=float)
            slope = _fit_slope(x, y)
            if slope is None:
                continue

            compound_data[compound].slopes.append(slope)

            # Baseline pace indicator: median of best 30% laps in stint.
            top_n = max(2, int(round(len(group) * 0.3)))
            best_median = float(np.median(np.sort(y)[:top_n]))
            compound_data[compound].medians.append(best_median)

    pace_delta = dict(DEFAULT_PACE)

    if compound_data["MEDIUM"].medians:
        med_ref = float(np.median(compound_data["MEDIUM"].medians))
        for compound in ["HARD", "MEDIUM", "SOFT"]:
            medians = compound_data[compound].medians
            if medians:
                raw_delta = float(np.median(medians) - med_ref)
                if compound == "SOFT":
                    bounded = max(-0.45, min(-0.18, raw_delta))
                    pace_delta[compound] = round(
                        0.7 * DEFAULT_PACE[compound] + 0.3 * bounded, 3
                    )
                elif compound == "HARD":
                    bounded = max(0.14, min(0.45, raw_delta))
                    pace_delta[compound] = round(
                        0.7 * DEFAULT_PACE[compound] + 0.3 * bounded, 3
                    )
                else:
                    pace_delta[compound] = 0.0

    tyre_params = dict(DEFAULT_TYRE_PARAMS)

    # Convert observed sec/lap degradation slopes to model base_degradation.
    # Model approximation: slope ~= base_degradation/base_lap*10
    for compound in ["HARD", "MEDIUM", "SOFT"]:
        slopes = compound_data[compound].slopes
        if not slopes:
            continue
        slope_med = float(np.median(slopes))
        base_lap = float(tyre_params[compound]["base_lap"])
        calibrated_base_deg = slope_med * base_lap / 10.0
        default_deg = DEFAULT_TYRE_PARAMS[compound]["base_degradation"]
        blended_deg = 0.7 * default_deg + 0.3 * calibrated_base_deg

        if compound == "HARD":
            blended_deg = max(0.026, min(0.036, blended_deg))
        elif compound == "MEDIUM":
            blended_deg = max(0.030, min(0.042, blended_deg))
        else:  # SOFT
            blended_deg = max(0.035, min(0.048, blended_deg))

        tyre_params[compound]["base_degradation"] = round(blended_deg, 4)

    # Mirror C2/C3/C4 with dry compounds.
    tyre_params["C2"] = dict(tyre_params["HARD"])
    tyre_params["C3"] = dict(tyre_params["MEDIUM"])
    tyre_params["C4"] = dict(tyre_params["SOFT"])

    payload = {
        "source": "FastF1 cached race laps + Pirelli-informed defaults",
        "cache_path": cache_path,
        "sessions_used": sessions_used,
        "pace_delta_seconds": {
            key: round(float(value), 3) for key, value in pace_delta.items()
        },
        "tyre_params": tyre_params,
    }

    output_path = os.path.join("data", "tyre_fastf1_calibration.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Saved tyre calibration to: {output_path}")
    print(f"Sessions used: {len(sessions_used)}")
    for compound in ["HARD", "MEDIUM", "SOFT"]:
        print(
            f"{compound}: pace_delta={payload['pace_delta_seconds'][compound]:+.3f}s, "
            f"base_deg={payload['tyre_params'][compound]['base_degradation']:.4f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
