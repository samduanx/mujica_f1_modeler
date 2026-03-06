"""
DRS Zone configurations for F1 2024 tracks.

All configurations are now loaded from data/drs_zones.json.
This module provides backward compatibility with the old function-based API
by reading from the JSON configuration file.
"""

import json
import os
from pathlib import Path

# Path to the JSON configuration file
# Use pathlib for robust path resolution across different environments
_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "drs_zones.json"
)

# Cache for loaded configurations
_config_cache = None


def _load_config() -> dict:
    """Load DRS configuration from JSON file."""
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, "r") as f:
            _config_cache = json.load(f)
    return _config_cache


def get_track_names() -> list:
    """Get list of all available track names."""
    config = _load_config()
    return list(config.keys())


def get_track_config(track_name: str) -> dict:
    """Get DRS configuration for a specific track.

    Args:
        track_name: Name of the track (e.g., "Imola", "Austria", "Brazil")

    Returns:
        Dictionary containing track DRS configuration

    Raises:
        KeyError: If track name is not found
    """
    config = _load_config()
    if track_name not in config:
        # Try with underscores replaced
        track_name_alt = track_name.replace(" ", "_")
        if track_name_alt in config:
            return config[track_name_alt]
        raise KeyError(f"Track '{track_name}' not found in DRS configuration")
    return config[track_name]


# Legacy function compatibility - these return the track config
def get_monaco_config() -> dict:
    """Get Monaco DRS configuration."""
    return get_track_config("Monaco")


def get_monza_config() -> dict:
    """Get Monza DRS configuration."""
    return get_track_config("Italy")  # Italy = Monza


def get_spain_config() -> dict:
    """Get Spain DRS configuration."""
    return get_track_config("Spain")


def get_bahrain_config() -> dict:
    """Get Bahrain DRS configuration."""
    return get_track_config("Bahrain")


def get_australia_config() -> dict:
    """Get Australia DRS configuration."""
    return get_track_config("Australia")


def get_japan_config() -> dict:
    """Get Japan DRS configuration."""
    return get_track_config("Japan")


def get_china_config() -> dict:
    """Get China DRS configuration."""
    return get_track_config("China")


def get_italy_config() -> dict:
    """Get Italy (Monza) DRS configuration."""
    return get_track_config("Italy")


def get_imola_config() -> dict:
    """Get Imola DRS configuration."""
    return get_track_config("Imola")


def get_austria_config() -> dict:
    """Get Austria DRS configuration."""
    return get_track_config("Austria")


def get_brazil_config() -> dict:
    """Get Brazil (Sao Paulo) DRS configuration."""
    return get_track_config("Brazil")


def get_great_britain_config() -> dict:
    """Get Great Britain DRS configuration."""
    return get_track_config("Great_Britain")


def get_hungary_config() -> dict:
    """Get Hungary DRS configuration."""
    return get_track_config("Hungary")


def get_belgium_config() -> dict:
    """Get Belgium DRS configuration."""
    return get_track_config("Belgium")


def get_netherlands_config() -> dict:
    """Get Netherlands DRS configuration."""
    return get_track_config("Netherlands")


def get_singapore_config() -> dict:
    """Get Singapore DRS configuration."""
    return get_track_config("Singapore")


def get_qatar_config() -> dict:
    """Get Qatar DRS configuration."""
    return get_track_config("Qatar")


def get_united_states_config() -> dict:
    """Get United States DRS configuration."""
    return get_track_config("United_States")


def get_mexico_config() -> dict:
    """Get Mexico DRS configuration."""
    return get_track_config("Mexico")


def get_las_vegas_config() -> dict:
    """Get Las Vegas DRS configuration."""
    return get_track_config("Las_Vegas")


def get_abu_dhabi_config() -> dict:
    """Get Abu Dhabi DRS configuration."""
    return get_track_config("Abu_Dhabi")


# All available track configurations - maps track names to config getter functions
TRACKS = {
    "Monaco": get_monaco_config,
    "Monza": get_monza_config,
    "Italy": get_italy_config,
    "Spain": get_spain_config,
    "Bahrain": get_bahrain_config,
    "Australia": get_australia_config,
    "Japan": get_japan_config,
    "China": get_china_config,
    "Imola": get_imola_config,
    "Austria": get_austria_config,
    "Brazil": get_brazil_config,
    "Great_Britain": get_great_britain_config,
    "Hungary": get_hungary_config,
    "Belgium": get_belgium_config,
    "Netherlands": get_netherlands_config,
    "Singapore": get_singapore_config,
    "Qatar": get_qatar_config,
    "United_States": get_united_states_config,
    "Mexico": get_mexico_config,
    "Las_Vegas": get_las_vegas_config,
    "Abu_Dhabi": get_abu_dhabi_config,
}

__all__ = [
    "get_monaco_config",
    "get_monza_config",
    "get_spain_config",
    "get_bahrain_config",
    "get_australia_config",
    "get_japan_config",
    "get_china_config",
    "get_italy_config",
    "get_imola_config",
    "get_austria_config",
    "get_brazil_config",
    "get_great_britain_config",
    "get_hungary_config",
    "get_belgium_config",
    "get_netherlands_config",
    "get_singapore_config",
    "get_qatar_config",
    "get_united_states_config",
    "get_mexico_config",
    "get_las_vegas_config",
    "get_abu_dhabi_config",
    "get_track_config",
    "get_track_names",
    "TRACKS",
]
