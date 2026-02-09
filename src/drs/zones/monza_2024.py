"""
Monza Grand Prix 2024 DRS Configuration.

Monza is a high-speed power track with maximum DRS benefit.
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
    """Get Monza 2024 DRS configuration"""

    # DRS zones for Monza 2024
    # Zone 1: Start finish to Curva Grande (very long DRS zone)
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=650,  # After first chicane
        end_distance=1600,  # Before Curva Grande
        detection_point=450,  # Detection before Lesmo
        base_time_gain=0.15,  # High DRS benefit
        activation_probability=0.90,
    )

    # Zone 2: Curva Alboreto
    drs_zone_2 = DRSZone(
        zone_id=2,
        start_distance=3400,  # After Ascari
        end_distance=4200,  # Before Roggia
        detection_point=3200,  # Detection after first chicane
        base_time_gain=0.12,  # High DRS benefit
        activation_probability=0.90,
    )

    # Updated sectors based on FastF1 2024 data:
    # S1: 26.4s, S2: 27.0s, S3: 26.7s, Total: 80.3s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1600,
        base_time=26.4,  # Updated from 25.0
        drs_zones=[drs_zone_1],
        corner_complexity="low",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1600,
        end_distance=3600,
        base_time=27.0,  # Updated from 34.0
        drs_zones=[drs_zone_2],
        corner_complexity="medium",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=3600,
        end_distance=5793,
        base_time=26.7,  # Updated from 25.0
        drs_zones=[],
        corner_complexity="low",
    )

    # DRS settings
    drs_settings = DRSSettings(
        enabled_after_lap=2,
        gain_variation=0.08,  # More variation at high speeds
        minimum_gap_for_drs=1.0,
        drs_disabled_first_lap=True,
    )

    return TrackDRSConfig(
        track_name="Monza",
        year=2024,
        total_distance=5793,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.HIGH.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Monza"""
    return {
        "avg_lap_time_target": 80.3,  # Updated from 84.0
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.45,
        "expected_overtakes": "8-15",
        "track_difficulty": "high",
    }


# Create the configuration instance
monza_2024_config = get_config()
