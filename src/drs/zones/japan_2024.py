"""
Japan Grand Prix 2024 DRS Configuration.

Suzuka - The legendary figure-8 circuit.
High-speed sections with DRS opportunities.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get Japan 2024 DRS configuration"""

    # DRS zones - Suzuka has 2 DRS zones
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=600,  # After T1-T2
        end_distance=1000,
        detection_point=400,
        base_time_gain=0.08,
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=2900,  # After 130R
        end_distance=3400,
        detection_point=2700,
        base_time_gain=0.08,
        activation_probability=0.85,
    )

    # Sectors - Suzuka is balanced
    # S1: 23.5s, S2: 28.5s, S3: 27.5s, Total: 79.5s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1200,
        base_time=23.5,
        drs_zones=[drs_zone_1],
        corner_complexity="high",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1200,
        end_distance=3100,
        base_time=28.5,
        drs_zones=[drs_zone_2],
        corner_complexity="high",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3100,
        end_distance=5300,
        base_time=27.5,
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
        track_name="Japan",
        year=2024,
        total_distance=5300,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Japan"""
    return {
        "avg_lap_time_target": 79.5,
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.16,
        "track_difficulty": "medium",
    }
