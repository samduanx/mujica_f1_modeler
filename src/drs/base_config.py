"""
Base configuration classes for DRS simulation.

Provides abstract base classes for track configurations,
sector definitions, and DRS zone specifications.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class TrackDifficulty(Enum):
    """Track classification for DRS effectiveness"""

    LOW = "low"  # Technical tracks (Monaco)
    MEDIUM = "medium"  # Balanced tracks
    HIGH = "high"  # Power tracks (Monza)


@dataclass
class DRSZone:
    """
    Defines a DRS zone on the track.

    Attributes:
        zone_id: Unique identifier for the zone
        start_distance: Distance from start line where zone begins (meters)
        end_distance: Distance from start line where zone ends (meters)
        detection_point: Distance from start line for DRS detection (meters)
        base_time_gain: Expected time gain when DRS is active (seconds)
        activation_probability: Probability of DRS activation when conditions are met
    """

    zone_id: int
    start_distance: float
    end_distance: float
    detection_point: float
    base_time_gain: float
    activation_probability: float = 0.85

    @property
    def length(self) -> float:
        """Calculate zone length in meters"""
        return self.end_distance - self.start_distance

    def contains(self, distance: float) -> bool:
        """Check if a distance is within this DRS zone"""
        return self.start_distance <= distance < self.end_distance

    def is_detection_point(self, distance: float, tolerance: float = 10.0) -> bool:
        """Check if at detection point (with tolerance)"""
        return abs(distance - self.detection_point) < tolerance


@dataclass
class SectorConfig:
    """
    Configuration for one sector of the track.

    Attributes:
        sector_number: 1, 2, or 3
        start_distance: Distance from start line where sector begins (meters)
        end_distance: Distance from start line where sector ends (meters)
        base_time: Expected base time for this sector (seconds)
        drs_zones: List of DRS zones within this sector
        corner_complexity: Complexity level of corners in this sector
    """

    sector_number: int
    start_distance: float
    end_distance: float
    base_time: float
    drs_zones: List[DRSZone] = field(default_factory=list)
    corner_complexity: str = "medium"

    @property
    def length(self) -> float:
        """Calculate sector length in meters"""
        return self.end_distance - self.start_distance

    @property
    def has_drs(self) -> bool:
        """Check if this sector has any DRS zones"""
        return len(self.drs_zones) > 0

    def get_drs_zone_at_distance(self, distance: float) -> Optional[DRSZone]:
        """Get DRS zone at specific distance, if any"""
        for zone in self.drs_zones:
            if zone.contains(distance):
                return zone
        return None


@dataclass
class DRSSettings:
    """
    Global DRS settings for the race.

    Attributes:
        enabled_after_lap: DRS is enabled after this lap
        gain_variation: Random variation in DRS gain (seconds)
        minimum_gap_for_drs: Minimum gap to car ahead for DRS (seconds)
        drs_disabled_first_lap: Disable DRS on first lap of race
    """

    enabled_after_lap: int = 2
    gain_variation: float = 0.05
    minimum_gap_for_drs: float = 1.0
    drs_disabled_first_lap: bool = True


@dataclass
class TrackDRSConfig:
    """
    Complete DRS configuration for a track.

    Attributes:
        track_name: Name of the track (e.g., "Monaco", "Monza")
        year: F1 season year (e.g., 2024)
        total_distance: Total track length (meters)
        sectors: Dictionary of sector configurations
        drs_settings: Global DRS settings
        difficulty: Track difficulty classification
    """

    track_name: str
    year: int
    total_distance: float
    sectors: Dict[int, SectorConfig]
    drs_settings: DRSSettings = field(default_factory=DRSSettings)
    difficulty: str = TrackDifficulty.MEDIUM.value

    def get_sector_at_distance(self, distance: float) -> Optional[SectorConfig]:
        """Get the sector at a specific distance"""
        for sector in self.sectors.values():
            if sector.start_distance <= distance < sector.end_distance:
                return sector
        return None

    def get_drs_zone_at_distance(self, distance: float) -> Optional[DRSZone]:
        """Get DRS zone at specific distance, if any"""
        for sector in self.sectors.values():
            zone = sector.get_drs_zone_at_distance(distance)
            if zone:
                return zone
        return None

    def get_detection_zones(self) -> List[DRSZone]:
        """Get all DRS zones sorted by detection point"""
        all_zones = []
        for sector in self.sectors.values():
            all_zones.extend(sector.drs_zones)
        return sorted(all_zones, key=lambda z: z.detection_point)

    def calculate_base_lap_time(self) -> float:
        """Calculate total base lap time from sector times"""
        return sum(sector.base_time for sector in self.sectors.values())

    def get_drs_zones_in_sector(self, sector_num: int) -> List[DRSZone]:
        """Get all DRS zones in a specific sector"""
        if sector_num in self.sectors:
            return self.sectors[sector_num].drs_zones
        return []
