"""
China Grand Prix 2024 DRS Configuration.

Shanghai International Circuit.
Long back straight with excellent DRS opportunity.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get China 2024 DRS configuration"""

    # DRS zones - Shanghai has 2 DRS zones
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=1200,  # After T1
        end_distance=1800,
        detection_point=1000,
        base_time_gain=0.12,
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=4000,  # The long back straight
        end_distance=4600,
        detection_point=3800,
        base_time_gain=0.20,  # Excellent DRS on long straight
        activation_probability=0.85,
    )

    # Sectors - Shanghai
    # S1: 26.5s, S2: 30.5s, S3: 28.0s, Total: 85.0s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=2000,
        base_time=26.5,
        drs_zones=[drs_zone_1],
        corner_complexity="medium",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=2000,
        end_distance=4200,
        base_time=30.5,
        drs_zones=[drs_zone_2],
        corner_complexity="medium",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=4200,
        end_distance=5450,
        base_time=28.0,
        drs_zones=[],
        corner_complexity="high",
    )

    drs_settings = DRSSettings(
        enabled_after_lap=2,
        gain_variation=0.03,
        minimum_gap_for_drs=1.0,
        drs_disabled_first_lap=True,
    )

    return TrackDRSConfig(
        track_name="China",
        year=2024,
        total_distance=5450,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for China"""
    return {
        "avg_lap_time_target": 85.0,
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.32,
        "track_difficulty": "medium",
    }
