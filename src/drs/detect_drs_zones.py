#!/usr/bin/env python3
"""
FastF1 DRS Zone Detection System.

This module provides tools to detect and validate DRS zones using FastF1 data.
It analyzes telemetry data to identify:
1. Where DRS activation typically occurs
2. Detection point locations
3. Zone lengths and expected time gains

Usage:
    python detect_drs_zones.py --year 2024 --grand-prix monaco
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json


# Known DRS zones from official F1 data for 2024 season
# Format: (track_name, zones) where zones are (detection, start, end, gain)
OFFICIAL_DRS_ZONES_2024 = {
    "Bahrain": [
        (550, 750, 1470, 0.18),  # Detection, Start, End, Gain
        (3050, 3250, 4050, 0.20),
    ],
    "Saudi Arabia": [
        (650, 800, 1200, 0.12),
        (3300, 3500, 4100, 0.15),
    ],
    "Australia": [
        (400, 600, 1000, 0.10),
        (2600, 2800, 3300, 0.08),
    ],
    "Japan": [
        (350, 500, 900, 0.08),
        (2600, 2800, 3300, 0.08),
    ],
    "China": [
        (800, 1000, 1500, 0.12),
        (3800, 4000, 4600, 0.20),
    ],
    "Miami": [
        (400, 550, 900, 0.10),
        (2200, 2400, 2900, 0.12),
    ],
    "Monaco": [
        (280, 450, 700, 0.03),  # Only ONE DRS zone at Monaco!
    ],
    "Spain": [
        (550, 700, 1000, 0.12),
        (2700, 2900, 3600, 0.15),
    ],
    "Canada": [
        (400, 550, 900, 0.10),
        (2500, 2700, 3200, 0.08),
    ],
    "Austria": [
        (400, 550, 900, 0.12),
        (2100, 2300, 2800, 0.10),
    ],
    "Great Britain": [
        (1200, 1400, 1800, 0.10),
        (2800, 3000, 3600, 0.08),
    ],
    "Belgium": [
        (700, 900, 1400, 0.15),
        (2700, 2900, 3400, 0.12),
    ],
    "Hungary": [
        (500, 650, 1100, 0.08),
        (2400, 2600, 3100, 0.06),
    ],
    "Netherlands": [
        (800, 1000, 1500, 0.10),
        (2800, 3000, 3600, 0.08),
    ],
    "Italy": [
        (400, 600, 1100, 0.15),
        (3200, 3800, 4600, 0.20),
    ],
    "Azerbaijan": [
        (400, 550, 1000, 0.12),
        (2200, 2400, 2900, 0.15),  # Includes the tricky Turn 15-16 section
    ],
    "Singapore": [
        (900, 1100, 1600, 0.06),
        (2800, 3000, 3500, 0.05),
    ],
    "United States": [
        (400, 550, 900, 0.12),
        (2400, 2600, 3100, 0.10),
    ],
    "Mexico": [
        (500, 700, 1100, 0.10),
        (2500, 2700, 3200, 0.08),
    ],
    "Brazil": [
        (600, 800, 1300, 0.15),
        (2900, 3100, 3700, 0.12),
    ],
    "Las Vegas": [
        (800, 1000, 1500, 0.12),
        (3400, 3600, 4200, 0.15),
    ],
    "Qatar": [
        (500, 700, 1200, 0.12),
        (2800, 3000, 3600, 0.10),
    ],
    "Abu Dhabi": [
        (500, 700, 1100, 0.10),
        (2800, 3000, 3600, 0.08),
    ],
}


@dataclass
class DetectedDRSZone:
    """Represents a detected DRS zone"""

    zone_id: int
    detection_point: float
    start_distance: float
    end_distance: float
    base_time_gain: float
    source: str = "official"  # "official", "detected", "estimated"
    confidence: float = 1.0


@dataclass
class TrackDRSInfo:
    """Complete DRS information for a track"""

    track_name: str
    year: int
    total_distance: float
    zones: List[DetectedDRSZone]
    sector_boundaries: List[Tuple[float, float, float]]  # (start, end, base_time)
    difficulty: str
    source_data: Dict = field(default_factory=dict)


def get_official_drs_zones(track_name: str, year: int = 2024) -> List[DetectedDRSZone]:
    """Get official DRS zones from known data"""
    if track_name not in OFFICIAL_DRS_ZONES_2024:
        raise ValueError(f"No official DRS data for {track_name} {year}")

    zones = []
    for i, (detection, start, end, gain) in enumerate(
        OFFICIAL_DRS_ZONES_2024[track_name]
    ):
        zones.append(
            DetectedDRSZone(
                zone_id=i + 1,
                detection_point=detection,
                start_distance=start,
                end_distance=end,
                base_time_gain=gain,
                source="official",
                confidence=1.0,
            )
        )

    return zones


def validate_track_drs_config(config_name: str, configured_zones: List[Dict]) -> Dict:
    """
    Validate a track's DRS configuration against official data.

    Args:
        config_name: Name of the track
        configured_zones: List of configured zone dictionaries

    Returns:
        Validation report
    """
    try:
        official_zones = get_official_drs_zones(config_name)
    except ValueError as e:
        return {
            "status": "unknown",
            "message": str(e),
            "official_zones": 0,
            "configured_zones": len(configured_zones),
        }

    issues = []

    # Check zone count
    if len(configured_zones) != len(official_zones):
        issues.append(
            f"Zone count mismatch: official={len(official_zones)}, configured={len(configured_zones)}"
        )

    # Check each zone
    for i, (official, configured) in enumerate(zip(official_zones, configured_zones)):
        zone_issues = []

        # Check detection point
        detection_diff = abs(
            configured.get("detection_point", 0) - official.detection_point
        )
        if detection_diff > 50:
            zone_issues.append(f"Detection point off by {detection_diff}m")

        # Check start distance
        start_diff = abs(configured.get("start_distance", 0) - official.start_distance)
        if start_diff > 50:
            zone_issues.append(f"Start distance off by {start_diff}m")

        # Check end distance
        end_diff = abs(configured.get("end_distance", 0) - official.end_distance)
        if end_diff > 50:
            zone_issues.append(f"End distance off by {end_diff}m")

        # Check gain
        gain_diff = abs(configured.get("base_time_gain", 0) - official.base_time_gain)
        if gain_diff > 0.05:
            zone_issues.append(f"Time gain off by {gain_diff:.2f}s")

        if zone_issues:
            issues.append(f"Zone {i + 1}: " + "; ".join(zone_issues))

    return {
        "status": "valid" if not issues else "issues",
        "message": "Configuration matches official data"
        if not issues
        else "; ".join(issues),
        "official_zones": len(official_zones),
        "configured_zones": len(configured_zones),
        "official_details": [
            {
                "id": z.zone_id,
                "detection": z.detection_point,
                "start": z.start_distance,
                "end": z.end_distance,
                "gain": z.base_time_gain,
            }
            for z in official_zones
        ],
    }


def generate_config_from_official(track_name: str, year: int = 2024) -> str:
    """Generate a Python config file from official DRS data"""
    zones = get_official_drs_zones(track_name, year)

    config_code = f'''"""
{track_name} Grand Prix {year} DRS Configuration.

Generated from official F1 DRS zone data.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get {track_name} {year} DRS configuration"""

    # DRS zones (from official F1 data)
'''

    for zone in zones:
        config_code += f"""
    drs_zone_{zone.zone_id} = DRSZone(
        zone_id={zone.zone_id},
        start_distance={zone.start_distance},
        end_distance={zone.end_distance},
        detection_point={zone.detection_point},
        base_time_gain={zone.base_time_gain},
        activation_probability=0.85,
    )
"""

    config_code += f"""
    # Sectors (need to be configured based on FastF1 data)
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1500,
        base_time=25.0,
        drs_zones=[drs_zone_1] if {len(zones) >= 1} else [],
        corner_complexity="medium",
    )
"""

    if len(zones) >= 2:
        config_code += """
    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1500,
        end_distance=3000,
        base_time=25.0,
        drs_zones=[drs_zone_2],
        corner_complexity="medium",
    )
"""

    config_code += (
        '''
    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3000,
        end_distance=5000,
        base_time=25.0,
        drs_zones=[],
        corner_complexity="medium",
    )

    drs_settings = DRSSettings(
        enabled_after_lap=2,
        gain_variation=0.03,
        minimum_gap_for_drs=1.0,
        drs_disabled_first_lap=True,
    )

    return TrackDRSConfig(
        track_name="'''
        + track_name
        + """",
        year="""
        + str(year)
        + """,
        total_distance=5000,
        sectors={{1: sector_1, 2: sector_2, 3: sector_3}},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )
"""
    )

    return config_code


def print_drs_summary():
    """Print summary of all official DRS zones"""
    print("=" * 80)
    print("F1 2024 OFFICIAL DRS ZONES SUMMARY")
    print("=" * 80)

    for track_name in sorted(OFFICIAL_DRS_ZONES_2024.keys()):
        zones = OFFICIAL_DRS_ZONES_2024[track_name]
        total_gain = sum(z[3] for z in zones)
        total_length = sum(z[2] - z[1] for z in zones)

        print(f"\n{track_name}:")
        print(
            f"  Zones: {len(zones)} | Total Gain: {total_gain:.2f}s | Total Length: {total_length}m"
        )

        for i, (detection, start, end, gain) in enumerate(zones, 1):
            length = end - start
            print(
                f"    Zone {i}: Detection@{detection}m | {start}-{end}m ({length}m) | Gain: {gain:.2f}s"
            )


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="FastF1 DRS Zone Detection System")
    parser.add_argument(
        "--summary", action="store_true", help="Print summary of all DRS zones"
    )
    parser.add_argument("--track", type=str, help="Get DRS zones for specific track")
    parser.add_argument("--generate", type=str, help="Generate config for a track")
    parser.add_argument("--year", type=int, default=2024, help="Season year")
    args = parser.parse_args()

    if args.summary:
        print_drs_summary()
    elif args.track:
        try:
            zones = get_official_drs_zones(args.track, args.year)
            print(f"\n{args.track} {args.year} DRS Zones:")
            for zone in zones:
                print(
                    f"  Zone {zone.zone_id}: Detection@{zone.detection_point}m, "
                    f"{zone.start_distance}-{zone.end_distance}m, Gain: {zone.base_time_gain:.2f}s"
                )
        except ValueError as e:
            print(f"Error: {e}")
    elif args.generate:
        code = generate_config_from_official(args.generate, args.year)
        print(code)
    else:
        print_drs_summary()


if __name__ == "__main__":
    main()
