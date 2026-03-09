"""
Configuration Loader Module

This module provides centralized loading and access to all JSON configuration files
used by the F1 Race Weekend Simulator. It handles loading tracks, sessions, drivers,
and lap time configurations from the data/ directory.
"""

import json
import os
from typing import Dict, List, Any, Optional


# =============================================================================
# CONFIGURATION PATHS
# =============================================================================

# Base configuration directory (data/ folder)
CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)

# Configuration file paths
TRACKS_CONFIG_PATH = os.path.join(CONFIG_DIR, "tracks.json")
SESSIONS_CONFIG_PATH = os.path.join(CONFIG_DIR, "sessions.json")
DRIVERS_CONFIG_PATH = os.path.join(CONFIG_DIR, "drivers.json")
LAP_TIMES_CONFIG_PATH = os.path.join(CONFIG_DIR, "track_lap_times.json")


# =============================================================================
# CACHE FOR LOADED CONFIGURATIONS
# =============================================================================

_config_cache: Dict[str, Any] = {}


def _load_json_config(path: str) -> Dict[str, Any]:
    """
    Load a JSON configuration file with caching.

    Args:
        path: Path to the JSON file

    Returns:
        Dictionary containing the configuration data

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if path in _config_cache:
        return _config_cache[path]

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configuration file not found: {path}\n"
            f"Please ensure the data/ directory contains all required JSON files:\n"
            f"  - tracks.json\n"
            f"  - sessions.json\n"
            f"  - drivers.json\n"
            f"  - track_lap_times.json"
        ) from None
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in configuration file: {path}\nError: {e.msg}",
            e.doc,
            e.pos,
        ) from None

    _config_cache[path] = config
    return config


def clear_config_cache() -> None:
    """Clear the configuration cache. Useful for testing or when configs are modified."""
    _config_cache.clear()


# =============================================================================
# TRACKS CONFIGURATION
# =============================================================================


def get_available_tracks() -> Dict[str, Dict[str, Any]]:
    """
    Get the available tracks configuration.

    Returns:
        Dictionary mapping track names to their configurations
    """
    config = _load_json_config(TRACKS_CONFIG_PATH)
    return config.get("available_tracks", {})


def get_sprint_tracks() -> Dict[str, Dict[str, Any]]:
    """
    Get the sprint tracks configuration.

    Returns:
        Dictionary mapping sprint track names to their configurations
    """
    config = _load_json_config(TRACKS_CONFIG_PATH)
    return config.get("sprint_tracks", {})


def get_all_tracks() -> Dict[str, Dict[str, Any]]:
    """
    Get all tracks (both regular and sprint tracks).

    Returns:
        Dictionary mapping all track names to their configurations
    """
    tracks = get_available_tracks().copy()
    tracks.update(get_sprint_tracks())
    return tracks


def get_track_config(track_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific track.

    Args:
        track_name: Name of the track

    Returns:
        Track configuration dictionary, or None if not found
    """
    return get_all_tracks().get(track_name)


def is_sprint_track(track_name: str) -> bool:
    """
    Check if a track is a sprint track.

    Args:
        track_name: Name of the track

    Returns:
        True if the track is a sprint track, False otherwise
    """
    return track_name in get_sprint_tracks()


# =============================================================================
# SESSIONS CONFIGURATION
# =============================================================================


def get_session_types() -> List[str]:
    """
    Get the list of available session types.

    Returns:
        List of session type strings (fp1, fp2, fp3, qualifying, sprint, race)
    """
    config = _load_json_config(SESSIONS_CONFIG_PATH)
    return config.get(
        "session_types", ["fp1", "fp2", "fp3", "qualifying", "sprint", "race"]
    )


def get_output_base_dir() -> str:
    """
    Get the base output directory for race weekend outputs.

    Returns:
        Path to the base output directory
    """
    config = _load_json_config(SESSIONS_CONFIG_PATH)
    return config.get("output_base_dir", "outputs/race_weekend")


def get_qualifying_config(is_sprint_weekend: bool = False) -> Dict[str, Any]:
    """
    Get qualifying session configuration.

    Args:
        is_sprint_weekend: If True, return sprint qualifying config (SQ1/SQ2/SQ3)
                          If False, return standard qualifying config (Q1/Q2/Q3)

    Returns:
        Qualifying configuration dictionary
    """
    config = _load_json_config(SESSIONS_CONFIG_PATH)
    qualifying = config.get("qualifying_config", {})

    if is_sprint_weekend:
        return qualifying.get("sprint", {})
    return qualifying.get("standard", {})


def get_qualifying_sessions_config(
    is_sprint_weekend: bool = False,
    num_drivers: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Get the list of qualifying session configurations.

    Args:
        is_sprint_weekend: If True, return sprint qualifying sessions
        num_drivers: Number of drivers in the session (affects elimination count)
            - 22 drivers: Q1 eliminates 6, Q2 eliminates 6
            - 20 drivers: Q1 eliminates 5, Q2 eliminates 5

    Returns:
        List of session configuration dictionaries with dynamic elimination counts
    """
    config = get_qualifying_config(is_sprint_weekend)
    sessions = config.get("sessions", [])

    if num_drivers is None:
        return sessions

    # Calculate dynamic elimination counts based on number of drivers
    # F1 rules: Eliminate until 15 remain for Q2, then 10 for Q3
    # Q1: Eliminate (num_drivers - 15) drivers (positions 16-20 or 17-22)
    # Q2: Eliminate 5 drivers (positions 11-15)
    adjusted_sessions = []
    for session in sessions:
        session_copy = dict(session)
        session_name = session.get("name", "")

        if session_name in ["Q1", "SQ1"]:
            # Q1 elimination based on driver count
            # 22 drivers: eliminate 6 (positions 17-22)
            # 20 drivers: eliminate 5 (positions 16-20)
            elimination_count = 6 if num_drivers >= 22 else 5
            session_copy["elimination_count"] = elimination_count
            start_pos = num_drivers - elimination_count + 1
            session_copy["description"] = (
                f"Eliminate slowest {elimination_count} (P{start_pos}-{num_drivers} determined)"
            )

        elif session_name in ["Q2", "SQ2"]:
            # Q2 elimination based on driver count
            # 22 drivers: eliminate 6 (positions 11-16)
            # 20 drivers: eliminate 5 (positions 11-15)
            elimination_count = 6 if num_drivers >= 22 else 5
            session_copy["elimination_count"] = elimination_count
            start_pos = 16 if num_drivers >= 22 else 15
            session_copy["description"] = (
                f"Eliminate slowest {elimination_count} (P11-{start_pos} determined)"
            )

        # Q3/SQ3 has elimination_count = 0 (no elimination, just pole position)

        adjusted_sessions.append(session_copy)

    return adjusted_sessions


def get_practice_config(session: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a practice session.

    Args:
        session: Session name (fp1, fp2, or fp3)

    Returns:
        Practice session configuration, or None if not found
    """
    config = _load_json_config(SESSIONS_CONFIG_PATH)
    practice_config = config.get("practice_config", {})
    return practice_config.get(session.lower())


def get_sprint_config() -> Dict[str, Any]:
    """
    Get sprint race configuration.

    Returns:
        Sprint race configuration dictionary
    """
    config = _load_json_config(SESSIONS_CONFIG_PATH)
    return config.get(
        "sprint_config", {"distance_km": 100, "description": "Sprint race format"}
    )


# =============================================================================
# DRIVERS CONFIGURATION
# =============================================================================


def get_drivers() -> List[str]:
    """
    Get the list of all driver names.

    Returns:
        List of driver name strings
    """
    config = _load_json_config(DRIVERS_CONFIG_PATH)
    return config.get("drivers", [])


def get_teams() -> Dict[str, str]:
    """
    Get the mapping of drivers to their teams.

    Returns:
        Dictionary mapping driver names to team names
    """
    config = _load_json_config(DRIVERS_CONFIG_PATH)
    return config.get("teams", {})


def get_driver_team(driver: str) -> Optional[str]:
    """
    Get the team for a specific driver.

    Args:
        driver: Driver name

    Returns:
        Team name, or None if driver not found
    """
    return get_teams().get(driver)


def get_top_tier_drivers() -> List[str]:
    """
    Get the list of top-tier drivers (faster skill level).

    Returns:
        List of top-tier driver names
    """
    config = _load_json_config(DRIVERS_CONFIG_PATH)
    tiers = config.get("driver_skill_tiers", {})
    return tiers.get("top_tier", [])


def get_bottom_tier_drivers() -> List[str]:
    """
    Get the list of bottom-tier drivers (slower skill level).

    Returns:
        List of bottom-tier driver names
    """
    config = _load_json_config(DRIVERS_CONFIG_PATH)
    tiers = config.get("driver_skill_tiers", {})
    return tiers.get("bottom_tier", [])


def get_team_pr(team_name: str, track_name: str = "spain") -> float:
    """
    Get the PR (Performance Rating) for a team on a specific track.

    PR is loaded from team CSV file (e.g., data/spain_team.csv).

    Args:
        team_name: Team name (English, e.g., "Red Bull", "Williams")
        track_name: Track name for track-specific PR values

    Returns:
        PR value (float), or default 300.0 if not found
    """
    import pandas as pd
    import os

    # Default PR if not found
    default_pr = 300.0

    # Map English team names to CSV format
    team_name_map = {
        "Red Bull": "Red Bull",
        "Ferrari": "Ferrari",
        "Mercedes": "Mercedes",
        "AlphaTauri": "AlphaTauri",
        "Aston Martin": "Aston Martin",
        "Alpine": "Alpine",
        "Alfa Romeo": "Alfa Romeo",
        "McLaren": "McLaren",
        "Haas": "Haas",
        "Williams": "Williams",
        "Andretti": "Andretti",
        "马丁": "Aston Martin",
        "小红牛": "AlphaTauri",
        "阿罗": "Alfa Romeo",
        "迈凯轮": "McLaren",
    }

    csv_name = f"data/{track_name.lower()}_team.csv"
    if not os.path.exists(csv_name):
        csv_name = "data/spain_team.csv"  # Fallback to spain

    try:
        df = pd.read_csv(csv_name, encoding="utf-8-sig")
        # Find the row with matching team name
        team_en = team_name_map.get(team_name, team_name)
        team_row = df[df["Teams"] == team_en]
        if not team_row.empty:
            pr_value = team_row["PR"].values[0]
            # Remove any non-numeric characters and convert to float
            if isinstance(pr_value, str):
                pr_value = float(pr_value.replace(",", "").strip())
            return float(pr_value)
    except Exception as e:
        print(f"Warning: Could not load PR for team {team_name}: {e}")

    return default_pr


def get_all_teams_pr(track_name: str = "spain") -> dict:
    """
    Get PR values for all teams.

    Returns:
        Dictionary mapping team names to PR values
    """
    import pandas as pd
    import os

    pr_dict = {}
    csv_name = f"data/{track_name.lower()}_team.csv"
    if not os.path.exists(csv_name):
        csv_name = "data/spain_team.csv"

    try:
        df = pd.read_csv(csv_name, encoding="utf-8-sig")
        for _, row in df.iterrows():
            team_name = row["Teams"]
            pr_value = row["PR"]
            if isinstance(pr_value, str):
                pr_value = float(pr_value.replace(",", "").strip())
            pr_dict[team_name] = float(pr_value)
    except Exception as e:
        print(f"Warning: Could not load team PR values: {e}")

    return pr_dict


# =============================================================================
# LAP TIMES CONFIGURATION
# =============================================================================


def get_track_lap_times() -> Dict[str, float]:
    """
    Get base lap times for all tracks.

    Returns:
        Dictionary mapping track names to base lap times in seconds
    """
    config = _load_json_config(LAP_TIMES_CONFIG_PATH)
    return config.get("tracks", {})


def get_track_lap_time(track_name: str, default: float = 80.0) -> float:
    """
    Get the base lap time for a specific track.

    Args:
        track_name: Name of the track
        default: Default lap time if track not found

    Returns:
        Base lap time in seconds
    """
    lap_times = get_track_lap_times()
    return lap_times.get(track_name, default)


def get_default_lap_time() -> float:
    """
    Get the default lap time for unknown tracks.

    Returns:
        Default lap time in seconds
    """
    config = _load_json_config(LAP_TIMES_CONFIG_PATH)
    return config.get("default_lap_time", 80.0)


# =============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# =============================================================================

# These exports maintain compatibility with code that expects
# the old constant-style access to configuration data


def load_all_configs() -> Dict[str, Any]:
    """
    Load all configurations at once.

    Returns:
        Dictionary containing all configuration data
    """
    return {
        "AVAILABLE_TRACKS": get_available_tracks(),
        "SPRINT_TRACKS": get_sprint_tracks(),
        "SESSION_TYPES": get_session_types(),
        "OUTPUT_BASE_DIR": get_output_base_dir(),
        "DRIVERS": get_drivers(),
        "TEAMS": get_teams(),
        "TRACK_LAP_TIMES": get_track_lap_times(),
    }
