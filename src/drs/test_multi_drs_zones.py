#!/usr/bin/env python3
"""
Multiple DRS Zone Scenario Test.

This script tests scenarios where drivers can use multiple DRS zones
in a single lap, showing cumulative DRS effects and detection mechanics.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass
from typing import List, Dict, Optional

from drs.base_config import (
    TrackDRSConfig,
    DRSSettings,
    DRSZone,
    SectorConfig,
    TrackDifficulty,
)


@dataclass
class CarState:
    """Represents a car's state during a lap"""

    name: str
    base_pace: float  # seconds slower than fastest
    drs_skill: float = 0.9  # How effectively they use DRS (0-1)

    def get_sector_time(self, sector_time: float, drs_gain: float = 0.0) -> float:
        """Calculate time for a sector with DRS gain"""
        adjusted_gain = drs_gain * self.drs_skill
        return sector_time + self.base_pace - adjusted_gain


def analyze_drs_zones_in_lap(track: TrackDRSConfig, car: CarState) -> Dict:
    """Analyze DRS zone usage for a single lap"""
    total_drs_gain = 0.0
    zone_details = []

    zones = track.get_detection_zones()
    for zone in zones:
        # Calculate effective gain for this car
        effective_gain = zone.base_time_gain * car.drs_skill
        total_drs_gain += effective_gain

        zone_details.append(
            {
                "zone_id": zone.zone_id,
                "detection_point": zone.detection_point,
                "zone_start": zone.start_distance,
                "zone_end": zone.end_distance,
                "zone_length": zone.length,
                "base_gain": zone.base_time_gain,
                "effective_gain": effective_gain,
            }
        )

    return {
        "car": car.name,
        "total_drs_zones": len(zones),
        "total_base_gain": sum(z.base_time_gain for z in zones),
        "total_effective_gain": total_drs_gain,
        "zone_details": zone_details,
    }


def simulate_lap_with_drs(
    track: TrackDRSConfig, car: CarState, gaps_ahead: List[float]
) -> Dict:
    """
    Simulate a complete lap with DRS eligibility check.

    Args:
        track: Track configuration
        car: Car being simulated
        gaps_ahead: Gap to car ahead at each detection point

    Returns detailed lap analysis
    """
    base_lap_time = track.calculate_base_lap_time()
    zones = track.get_detection_zones()

    # Track DRS usage
    drs_used = []
    drs_gains = []
    ineligible_zones = []

    for i, zone in enumerate(zones):
        gap = gaps_ahead[i] if i < len(gaps_ahead) else 99.0
        is_eligible = gap <= track.drs_settings.minimum_gap_for_drs

        if is_eligible:
            effective_gain = zone.base_time_gain * car.drs_skill
            drs_used.append(zone.zone_id)
            drs_gains.append(effective_gain)
        else:
            ineligible_zones.append(
                {
                    "zone_id": zone.zone_id,
                    "gap": gap,
                    "reason": f"Gap of {gap:.2f}s exceeds 1.0s threshold",
                }
            )

    total_drs_gain = sum(drs_gains)
    lap_time = base_lap_time + car.base_pace - total_drs_gain

    return {
        "car": car.name,
        "track": track.track_name,
        "base_lap_time": base_lap_time,
        "car_penalty": car.base_pace,
        "drs_zones_used": drs_used,
        "drs_gains": drs_gains,
        "total_drs_gain": total_drs_gain,
        "final_lap_time": lap_time,
        "ineligible_zones": ineligible_zones,
        "sector_times": [],
    }


def demo_multiple_drs_zones():
    """Demo: Test multiple DRS zone scenarios"""
    from drs.zones import TRACKS

    print("=" * 70)
    print("MULTIPLE DRS ZONE SCENARIO TEST")
    print("=" * 70)

    # Test tracks with multiple DRS zones
    test_tracks = ["Monza", "Bahrain", "Spain", "China"]

    for track_name in test_tracks:
        track = TRACKS[track_name]()
        zones = track.get_detection_zones()

        print(f"\n{'=' * 70}")
        print(f"TRACK: {track_name} Grand Prix")
        print(f"{'=' * 70}")

        # Show DRS zone layout
        print(f"\nDRS Zone Layout:")
        print(f"  Total zones: {len(zones)}")
        print(f"  Cumulative base gain: {sum(z.base_time_gain for z in zones):.2f}s")
        print(f"\n  Zone Details:")

        for zone in zones:
            print(f"\n    Zone {zone.zone_id}:")
            print(f"      Detection Point: {zone.detection_point}m")
            print(f"      Zone Start: {zone.start_distance}m")
            print(f"      Zone End: {zone.end_distance}m")
            print(f"      Zone Length: {zone.length}m")
            print(f"      Base Time Gain: {zone.base_time_gain:.2f}s")

            # Show what lap distance this corresponds to
            lap_fraction = zone.detection_point / track.total_distance
            print(f"      Detection at: ~{lap_fraction * 100:.0f}% of lap")

        # Simulate scenarios
        print(f"\n\nScenario Tests:")
        print("-" * 70)

        scenarios = [
            ("All zones eligible (clear air)", [0.5, 0.3]),
            ("One zone ineligible", [1.2, 0.4]),
            ("Both zones ineligible (traffic)", [1.5, 1.8]),
        ]

        for scenario_name, gaps in scenarios:
            print(f"\n  Scenario: {scenario_name}")
            print(f"    Gaps at detection: {gaps}s")

            for car_name, pace, skill in [
                ("Verstappen", 0.0, 0.9),
                ("Norris", 0.3, 0.85),
                ("Hamilton", 0.8, 0.7),
            ]:
                car = CarState(car_name, pace, skill)
                result = simulate_lap_with_drs(track, car, gaps)

                print(f"\n    {car_name}:")
                print(f"      DRS zones used: {result['drs_zones_used'] or 'None'}")
                if result["drs_gains"]:
                    print(
                        f"      DRS gains: {[f'{g:.2f}s' for g in result['drs_gains']]}"
                    )
                print(f"      Total DRS gain: {result['total_drs_gain']:.2f}s")
                print(f"      Lap time: {result['final_lap_time']:.2f}s")

                if result["ineligible_zones"]:
                    for iz in result["ineligible_zones"]:
                        print(f"      ❌ Zone {iz['zone_id']}: {iz['reason']}")


def demo_overtaking_scenario():
    """Demo: Simulate an overtaking scenario with DRS"""
    from drs.zones import TRACKS

    print("\n" + "=" * 70)
    print("OVERTAKING SCENARIO WITH DRS")
    print("=" * 70)

    track = TRACKS["Monza"]()
    zones = track.get_detection_zones()

    print(f"\nTrack: {track.track_name}")
    print(f"DRS Zones: {len(zones)}")
    print(f"\nSimulating a race scenario where Norris hunts down Verstappen...")

    # Initial state
    verstappen = CarState("Verstappen", 0.0, 0.9)
    norris = CarState("Norris", 0.3, 0.85)

    print(f"\n{'=' * 70}")
    print("LAP-BY-LAP ANALYSIS")
    print(f"{'=' * 70}")

    # Simulate 5 laps of pressure
    for lap in range(1, 6):
        print(f"\nLap {lap}:")

        # Gap decreases over time
        if lap == 1:
            gap_at_detection = [0.8, 0.6]
        elif lap == 2:
            gap_at_detection = [0.6, 0.4]
        elif lap == 3:
            gap_at_detection = [0.4, 0.2]  # Norris gets within DRS range
        else:
            gap_at_detection = [0.2, 0.1]

        # Analyze Verstappen's lap
        ver_result = simulate_lap_with_drs(track, verstappen, gap_at_detection)
        nor_result = simulate_lap_with_drs(track, norris, gap_at_detection)

        ver_time = ver_result["final_lap_time"]
        nor_time = nor_result["final_lap_time"]

        print(
            f"  Verstappen: {ver_time:.2f}s (DRS used: {ver_result['drs_zones_used']})"
        )
        print(
            f"  Norris:     {nor_time:.2f}s (DRS used: {nor_result['drs_zones_used']})"
        )
        print(f"  Gap closed: {ver_time - nor_time:.2f}s")

        if nor_result["drs_zones_used"] and len(nor_result["drs_zones_used"]) > len(
            ver_result["drs_zones_used"]
        ):
            print(f"  → Norris advantage: More DRS zones available!")


def demo_track_comparison():
    """Demo: Compare DRS effectiveness across tracks"""
    from drs.zones import TRACKS

    print("\n" + "=" * 70)
    print("TRACK DRS EFFECTIVENESS COMPARISON")
    print("=" * 70)

    print(
        f"\n{'Track':<15} {'Base Time':>12} {'DRS Zones':>10} {'Total Gain':>12} {'Gain %':>10}"
    )
    print("-" * 60)

    for track_name in sorted(TRACKS.keys()):
        track = TRACKS[track_name]()
        zones = track.get_detection_zones()
        base_time = track.calculate_base_lap_time()
        total_gain = sum(z.base_time_gain for z in zones)
        gain_pct = (total_gain / base_time) * 100

        print(
            f"{track_name:<15} {base_time:>10.1f}s {len(zones):>10} {total_gain:>10.2f}s {gain_pct:>9.2f}%"
        )


def demo_sector_drivers():
    """Demo: Show DRS effect by sector"""
    from drs.zones import TRACKS

    print("\n" + "=" * 70)
    print("SECTOR-BY-SECTOR DRS EFFECT")
    print("=" * 70)

    track = TRACKS["Monza"]()

    print(f"\n{track.track_name} - Sector Analysis")
    print("-" * 50)

    for sector_num in sorted(track.sectors.keys()):
        sector = track.sectors[sector_num]

        print(
            f"\nSector {sector_num} ({sector.start_distance}-{sector.end_distance}m):"
        )
        print(f"  Base time: {sector.base_time:.2f}s")
        print(f"  Has DRS: {'Yes' if sector.has_drs else 'No'}")

        if sector.has_drs:
            for zone in sector.drs_zones:
                print(
                    f"  DRS Zone {zone.zone_id}: {zone.length}m, {zone.base_time_gain:.2f}s gain"
                )


def main():
    """Main test function"""
    print("F1 DRS Multiple Zone Scenario Tests")
    print("=" * 70)

    demo_multiple_drs_zones()
    demo_overtaking_scenario()
    demo_track_comparison()
    demo_sector_drivers()

    print("\n" + "=" * 70)
    print("Tests Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
