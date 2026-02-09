"""
Italy Grand Prix 2024 DRS Configuration.

Monza - The Temple of Speed.
Highest DRS gains of the season.
"""

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)


def get_config() -> TrackDRSConfig:
    """Get Italy 2024 DRS configuration"""

    # DRS zones - Monza has 2 DRS zones with very high gains
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=600,  # After Rettifica a
        end_distance=1100,
        detection_point=400,
        base_time_gain=0.15,  # High speed DRS
        activation_probability=0.85,
    )

    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=3800,  # The main straight
        end_distance=4600,
        detection_point=3600,
        base_time_gain=0.20,  # Excellent DRS opportunity
        activation_probability=0.85,
    )

    # Sectors - Monza is very fast
    # S1: 22.0s, S2: 26.5s, S3: 22.5s, Total: 71.0s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1300,
        base_time=22.0,
        drs_zones=[drs_zone_1],
        corner_complexity="low",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1300,
        end_distance=4000,
        base_time=26.5,
        drs_zones=[drs_zone_2],
        corner_complexity="low",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=4000,
        end_distance=5793,
        base_time=22.5,
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
        track_name="Italy",
        year=2024,
        total_distance=5793,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.HIGH.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Italy"""
    return {
        "avg_lap_time_target": 71.0,
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.35,
        "track_difficulty": "easy",
    }
