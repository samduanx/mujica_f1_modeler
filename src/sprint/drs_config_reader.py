"""
DRS Configuration Reader

Reads DRS zone configurations from JSON file (data/drs_zones.json)
and provides them to the sprint simulator.
"""

import json
import os
from typing import Dict, Any, Optional


def load_drs_config(track_name: str) -> Optional[Dict[str, Any]]:
    """
    Load DRS configuration for a track from JSON file.

    Args:
        track_name: Name of the track (Imola, Austria, Brazil)

    Returns:
        Dictionary containing DRS configuration or None if not found
    """
    json_path = os.path.join("data", "drs_zones.json")

    try:
        with open(json_path, "r") as f:
            all_configs = json.load(f)

        # Map track names to config keys
        track_key = track_name
        if track_name.lower() in ["sao_paulo", "saopaulo", "brazil"]:
            track_key = "Brazil"
        elif track_name.lower() == "imola":
            track_key = "Imola"
        elif track_name.lower() == "austria":
            track_key = "Austria"

        config = all_configs.get(track_key)
        if config:
            print(f"  Loaded DRS config for {track_key}")
            return config
        else:
            print(f"  Warning: No DRS config found for {track_name}")
            return None

    except FileNotFoundError:
        print(f"  Warning: DRS config file not found: {json_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"  Warning: Error parsing DRS config: {e}")
        return None


def get_track_drs_summary(track_name: str) -> str:
    """
    Get a summary of DRS zones for a track.

    Args:
        track_name: Name of the track

    Returns:
        String summary of DRS configuration
    """
    config = load_drs_config(track_name)

    if not config:
        return "No DRS config available"

    num_zones = sum(
        len(sector.get("drs_zones", []))
        for sector in config.get("sectors", {}).values()
    )

    return f"{num_zones} DRS zones, {config.get('total_distance')}m track"


if __name__ == "__main__":
    # Test the reader
    for track in ["Imola", "Austria", "Brazil"]:
        config = load_drs_config(track)
        if config:
            print(f"{track}: {get_track_drs_summary(track)}")
