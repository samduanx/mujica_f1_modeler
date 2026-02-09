"""
Spain Grand Prix 2024 DRS Configuration.

Barcelona is a balanced track with medium DRS effectiveness.
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
    """Get Spain 2024 DRS configuration"""

    # DRS zones for Spain 2024
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=700,  # After T1-T3 chicane
        end_distance=1000,
        detection_point=600,
        base_time_gain=0.12,  # Medium DRS
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=2900,  # After T10
        end_distance=3600,
        detection_point=2800,
        base_time_gain=0.15,  # Medium DRS
        activation_probability=0.85,
    )

    # Updated sectors based on FastF1 2024 data:
    # S1: 21.6s, S2: 28.8s, S3: 21.8s, Total: 72.3s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1200,
        base_time=21.6,  # Updated from 28.0
        drs_zones=[drs_zone_1],
        corner_complexity="medium",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1200,
        end_distance=3000,
        base_time=28.8,  # Updated from 30.0
        drs_zones=[drs_zone_2],
        corner_complexity="high",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3000,
        end_distance=4657,
        base_time=21.8,  # Updated from 28.0
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
        track_name="Spain",
        year=2024,
        total_distance=4657,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Spain"""
    return {
        "avg_lap_time_target": 72.3,  # Updated from 86.0
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.55,
        "track_difficulty": "medium",
    }
