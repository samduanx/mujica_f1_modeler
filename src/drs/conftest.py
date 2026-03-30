import pytest
from typing import Dict

# Build a minimal TrackDRSConfig object expected by the simulator
from drs.base_config import TrackDRSConfig, SectorConfig, DRSZone, DRSSettings
import importlib.util
import os

# Load the test module by file path to avoid module resolution issues
_this_dir = os.path.dirname(__file__)
_test_module_path = os.path.join(_this_dir, "test_integration_real_data.py")
spec = importlib.util.spec_from_file_location("drs_test_integration", _test_module_path)
drs_test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drs_test_module)

run_integrated_simulation = drs_test_module.run_integrated_simulation
get_reference_driver_data = drs_test_module.get_reference_driver_data
IntegratedSimulationConfig = drs_test_module.IntegratedSimulationConfig


def _build_minimal_track_config() -> TrackDRSConfig:
    # Create simple sectors that sum to a reasonable lap time
    drs_zone = DRSZone(
        zone_id=1,
        start_distance=2500.0,
        end_distance=2700.0,
        detection_point=2450.0,
        base_time_gain=0.3,
        activation_probability=0.95,
    )

    s1 = SectorConfig(
        sector_number=1,
        start_distance=0.0,
        end_distance=1800.0,
        base_time=25.0,
        drs_zones=[],
    )
    s2 = SectorConfig(
        sector_number=2,
        start_distance=1800.0,
        end_distance=3600.0,
        base_time=27.0,
        drs_zones=[drs_zone],
    )
    s3 = SectorConfig(
        sector_number=3,
        start_distance=3600.0,
        end_distance=5793.0,
        base_time=27.0,
        drs_zones=[],
    )

    sectors = {1: s1, 2: s2, 3: s3}

    config = TrackDRSConfig(
        track_name="Monza",
        year=2024,
        total_distance=5793.0,
        sectors=sectors,
        drs_settings=DRSSettings(
            enabled_after_lap=2,
            gain_variation=0.03,
            minimum_gap_for_drs=1.0,
            drs_disabled_first_lap=True,
        ),
        difficulty="high",
    )

    return config


@pytest.fixture(scope="module")
def results() -> Dict:
    track_config = _build_minimal_track_config()
    driver_data = get_reference_driver_data()
    config = IntegratedSimulationConfig(
        num_laps=20,
        random_seed=42,
        enable_drs=True,
        enable_overtakes=True,
        verbose=False,
    )

    return run_integrated_simulation(track_config, driver_data, config)
