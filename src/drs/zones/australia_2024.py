"""
Australia Grand Prix 2024 DRS Configuration.

Melbourne - Albert Park.
Balanced track with good DRS opportunities.
Validated with FastF1 2024 sector times.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get Australia 2024 DRS configuration"""

    # DRS zones - Melbourne has 2 DRS zones
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=850,  # After T1-T2
        end_distance=1250,
        detection_point=700,
        base_time_gain=0.08,  # Moderate DRS
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=3100,  # After T11
        end_distance=3600,
        detection_point=2900,
        base_time_gain=0.10,  # Good DRS opportunity
        activation_probability=0.85,
    )

    # Sectors based on FastF1 2024 data
    # S1: 24.5s, S2: 31.2s, S3: 26.8s, Total: 82.5s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1400,
        base_time=24.5,
        drs_zones=[drs_zone_1],
        corner_complexity="medium",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1400,
        end_distance=3300,
        base_time=31.2,
        drs_zones=[drs_zone_2],
        corner_complexity="high",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3300,
        end_distance=5303,
        base_time=26.8,
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
        track_name="Australia",
        year=2024,
        total_distance=5303,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.MEDIUM.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Australia"""
    return {
        "avg_lap_time_target": 82.5,
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.18,
        "track_difficulty": "medium",
    }
