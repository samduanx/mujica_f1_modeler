"""
Monaco Grand Prix 2024 DRS Configuration.

Monaco is a technical street circuit with minimal DRS benefit.
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
    """Get Monaco 2024 DRS configuration"""

    # DRS zones for Monaco 2024 - Monaco has ONLY ONE DRS zone!
    drs_zone_1 = DRSZone(
        zone_id=1,
        start_distance=450,  # After Sainte Dévote
        end_distance=700,  # Before Fairmont Hairpin
        detection_point=280,  # Detection before zone
        base_time_gain=0.03,  # Minimal DRS benefit due to short zone
        activation_probability=0.80,
    )

    # Updated sectors based on FastF1 2024 data:
    # S1: 18.6s, S2: 33.6s, S3: 19.0s, Total: 71.3s
    sector_1 = SectorConfig(
        sector_number=1,
        start_distance=0,
        end_distance=1100,
        base_time=18.6,  # Updated from 25.5
        drs_zones=[drs_zone_1],
        corner_complexity="high",
    )

    sector_2 = SectorConfig(
        sector_number=2,
        start_distance=1100,
        end_distance=2100,
        base_time=33.6,  # Updated from 24.0
        drs_zones=[],  # NO DRS zone in Sector 2
        corner_complexity="high",
    )

    sector_3 = SectorConfig(
        sector_number=3,
        start_distance=2100,
        end_distance=3337,
        base_time=19.0,  # Updated from 28.5
        drs_zones=[],
        corner_complexity="medium",
    )

    # DRS settings
    drs_settings = DRSSettings(
        enabled_after_lap=2,
        gain_variation=0.03,  # Less variation due to limited DRS
        minimum_gap_for_drs=1.0,
        drs_disabled_first_lap=True,
    )

    return TrackDRSConfig(
        track_name="Monaco",
        year=2024,
        total_distance=3337,
        sectors={1: sector_1, 2: sector_2, 3: sector_3},
        drs_settings=drs_settings,
        difficulty=TrackDifficulty.LOW.value,
    )


def get_validation_targets() -> dict:
    """Get validation targets for Monaco"""
    return {
        "avg_lap_time_target": 71.3,  # Updated from 76.0
        "lap_time_tolerance": 1.0,
        "drs_gain_target": 0.03,  # Only ONE DRS zone!
        "expected_overtakes": "0-2",
        "track_difficulty": "low",
        "drs_zones_count": 1,
    }


# Create the configuration instance
monaco_2024_config = get_config()
