"""
Bahrain Grand Prix 2024 DRS Configuration.

Bahrain is a balanced track with good DRS opportunities.
Updated to match FastF1 2024 sector times.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get Bahrain 2024 DRS configuration"""

    # DRS zones for Bahrain 2024
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=750,
        end_distance=1470,
        detection_point=550,
        base_time_gain=0.18,
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=3250,
        end_distance=4050,
        detection_point=3050,
        base_time_gain=0.20,
        activation_probability=0.85,
    )

    # Updated sectors based on FastF1 2024 data:
    # S1: 28.9s, S2: 38.6s, S3: 22.5s, Total: 90.0s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1500,
        base_time=28.9,  # Updated from 30.0
        drs_zones=[drs_zone_1],
        corner_complexity="medium",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1500,
        end_distance=3600,
        base_time=38.6,  # Updated from 32.0
        drs_zones=[drs_zone_2],
        corner_complexity="medium",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3600,
        end_distance=5412,
        base_time=22.5,  # Updated from 30.0
        drs_zones=[],
        corner_complexity="medium",
    )

    drs_settings = DRSSettings(
        enabled_after_lap=2,
        gain_variation=0.05,
        minimum_gap_for_drs=1.0,
        drs_disabled_first_lap=True,
    )

    return TrackDRSConfig(
        track_name="Bahrain",
        year=2024,
        total_distance=5412,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Bahrain"""
    return {
        "avg_lap_time_target": 90.0,
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.75,
        "track_difficulty": "medium",
    }
