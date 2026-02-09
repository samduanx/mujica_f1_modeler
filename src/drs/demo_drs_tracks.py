#!/usr/bin/env python3
"""
Demo script to showcase the DRS simulation system with multiple tracks.

This demonstrates:
1. How to use track configurations
2. DRS zone detection and timing
3. Simulating a simple race with DRS
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from dataclasses import dataclass, field
import random

from drs.base_config import (
    TrackDRSConfig,
    DRSSettings,
    DRSZone,
    SectorConfig,
    TrackDifficulty,
)


@dataclass
class SimpleCar:
    """Simple car representation for demo"""

    name: str
    base_pace: float  # seconds per lap slower than fastest
    drs_skill: float = 0.0  # How well they use DRS (0-1)

    def get_lap_time(self, track: TrackDRSConfig, use_drs: bool = False) -> float:
        """Calculate lap time for this car on this track"""
        base_time = track.calculate_base_lap_time()
        time = base_time + self.base_pace

        if use_drs:
            # Add DRS gain
            zones = track.get_detection_zones()
            drs_gain = sum(zone.base_time_gain for zone in zones)
            time -= drs_gain * (
                0.8 + self.drs_skill * 0.4
            )  # Skill affects effectiveness

        return time


def list_available_tracks() -> List[str]:
    """List all available track configurations"""
    # Import all track configurations
    from drs.zones import TRACKS

    return list(TRACKS.keys())


def get_track_info(track_name: str) -> Dict:
    """Get detailed information about a track"""
    from drs.zones import TRACKS

    if track_name not in TRACKS:
        available = ", ".join(sorted(TRACKS.keys()))
        raise ValueError(f"Unknown track: {track_name}. Available: {available}")

    config = TRACKS[track_name]()
    zones = config.get_detection_zones()

    return {
        "name": config.track_name,
        "year": config.year,
        "total_distance": config.total_distance,
        "base_lap_time": config.calculate_base_lap_time(),
        "difficulty": config.difficulty,
        "drs_zones": [
            {
                "id": z.zone_id,
                "start": z.start_distance,
                "end": z.end_distance,
                "detection": z.detection_point,
                "gain": z.base_time_gain,
                "length": z.length,
            }
            for z in zones
        ],
        "sectors": [
            {
                "number": s.sector_number,
                "time": s.base_time,
                "distance": s.length,
                "has_drs": s.has_drs,
            }
            for s in sorted(config.sectors.values(), key=lambda x: x.sector_number)
        ],
    }


def demo_track_comparison():
    """Demo: Compare DRS effectiveness across different tracks"""
    from drs.zones import TRACKS

    print("=" * 60)
    print("DRS SIMULATION SYSTEM - TRACK COMPARISON")
    print("=" * 60)
    print()

    # Create some demo cars
    cars = [
        SimpleCar("Verstappen", base_pace=0.0, drs_skill=0.9),
        SimpleCar("Norris", base_pace=0.3, drs_skill=0.85),
        SimpleCar("Leclerc", base_pace=0.5, drs_skill=0.8),
        SimpleCar("Hamilton", base_pace=0.8, drs_skill=0.7),
        SimpleCar("Russell", base_pace=0.9, drs_skill=0.75),
    ]

    # Compare all tracks
    for track_name in sorted(TRACKS.keys()):
        print(f"\n{track_name} Grand Prix")
        print("-" * 40)

        info = get_track_info(track_name)

        # Show track info
        print(f"  Base lap time: {info['base_lap_time']:.1f}s")
        print(f"  Total distance: {info['total_distance']}m")
        print(f"  Difficulty: {info['difficulty']}")
        print(f"  DRS zones: {len(info['drs_zones'])}")

        for zone in info["drs_zones"]:
            print(
                f"    Zone {zone['id']}: {zone['start']}-{zone['end']}m "
                f"(gain: {zone['gain']:.2f}s, length: {zone['length']}m)"
            )

        # Simulate a lap for each car (with and without DRS)
        print(f"\n  Lap times (5 lap simulation):")
        print(
            f"  {'Driver':<15} {'Lap 1':>8} {'Lap 2':>8} {'Lap 3':>8} {'Lap 4':>8} {'Lap 5':>8}"
        )
        print(f"  {'-' * 15} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")

        for car in cars:
            lap_times = []
            for lap in range(1, 6):
                use_drs = lap > 1  # DRS enabled from lap 2
                lap_time = car.get_lap_time(TRACKS[track_name](), use_drs=use_drs)
                lap_times.append(lap_time)

            print(
                f"  {car.name:<15} {lap_times[0]:>8.2f} {lap_times[1]:>8.2f} "
                f"{lap_times[2]:>8.2f} {lap_times[3]:>8.2f} {lap_times[4]:>8.2f}"
            )


def demo_sector_timing():
    """Demo: Show how sector timing works with DRS"""
    from drs.zones import TRACKS

    print("\n" + "=" * 60)
    print("SECTOR TIMING DEMONSTRATION")
    print("=" * 60)

    track = TRACKS["Monza"]()

    print(f"\n{track.track_name} Sector Breakdown:")
    print("-" * 50)

    for sector_num in sorted(track.sectors.keys()):
        sector = track.sectors[sector_num]
        zone_info = ", ".join([f"Zone {z.zone_id}" for z in sector.drs_zones]) or "None"

        print(f"\n  Sector {sector_num}:")
        print(
            f"    Distance: {sector.start_distance}-{sector.end_distance}m ({sector.length}m)"
        )
        print(f"    Base time: {sector.base_time:.2f}s")
        print(f"    DRS zones: {zone_info}")
        print(f"    Corner complexity: {sector.corner_complexity}")

        # Calculate average speed
        avg_speed = sector.length / sector.base_time * 3.6  # km/h
        print(f"    Average speed: {avg_speed:.1f} km/h")


def demo_drs_detection():
    """Demo: Show how DRS detection works"""
    from drs.zones import TRACKS

    print("\n" + "=" * 60)
    print("DRS DETECTION ZONE DEMONSTRATION")
    print("=" * 60)

    track = TRACKS["Monza"]()

    print(f"\n{track.track_name} DRS Detection Points:")
    print("-" * 50)

    zones = track.get_detection_zones()

    for zone in zones:
        print(f"\n  DRS Zone {zone.zone_id}:")
        print(f"    Detection point: {zone.detection_point}m")
        print(f"    Zone start: {zone.start_distance}m")
        print(f"    Zone end: {zone.end_distance}m")
        print(f"    Zone length: {zone.length}m")
        print(f"    Expected time gain: {zone.base_time_gain:.2f}s")
        print(f"    Activation probability: {zone.activation_probability:.0%}")

        # Show what happens at different distances
        test_distances = [
            zone.detection_point - 50,
            zone.detection_point,
            zone.start_distance + 50,
            zone.end_distance - 50,
        ]

        print(f"    Distance checks:")
        for dist in test_distances:
            in_zone = zone.contains(dist)
            is_detection = zone.is_detection_point(dist)
            status = (
                "IN ZONE" if in_zone else ("DETECTION" if is_detection else "Normal")
            )
            print(f"      {dist}m: {status}")


def main():
    """Main demo function"""
    print("F1 DRS Simulation System Demo")
    print("=" * 60)

    # List available tracks
    print("\nAvailable tracks:")
    for track in list_available_tracks():
        print(f"  - {track}")

    # Run demonstrations
    demo_track_comparison()
    demo_sector_timing()
    demo_drs_detection()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
