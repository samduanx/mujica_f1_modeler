"""
Strategist Manager Module

Manages all strategists in the game including:
- Loading strategist profiles from JSON
- Managing team strategists
- Retrieving strategists by name or team
- Saving changes back to JSON
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List

from src.strategist.strategist_types import StrategistProfile


class StrategistManager:
    """
    Central manager for all strategists in the game.

    Handles creation, retrieval, and management of strategist profiles.
    Loads from JSON on initialization.
    """

    def __init__(self, json_path: Optional[str | Path] = None):
        """
        Initialize the strategist manager.

        Args:
            json_path: Optional path to JSON file. Defaults to data/strategists/strategists.json
        """
        self._strategists: Dict[str, StrategistProfile] = {}
        self._team_strategists: Dict[str, str] = {}  # team -> strategist name

        # Determine JSON path
        if json_path is None:
            # Get the project root directory
            project_root = Path(__file__).parent.parent.parent
            json_path = project_root / "data" / "strategists" / "strategists.json"

        # Convert to Path if needed
        if isinstance(json_path, str):
            json_path = Path(json_path)

        self._json_path: Path = json_path
        self._load_from_json()

    def _load_from_json(self) -> None:
        """Load strategist profiles from JSON file."""
        if not self._json_path.exists():
            raise FileNotFoundError(
                f"Strategist JSON file not found: {self._json_path}"
            )

        with open(self._json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for strategist_data in data.get("strategists", []):
            # Convert track_familiarity from dict to proper type
            track_fam = strategist_data.get("track_familiarity", {})
            if track_fam is None:
                track_fam = {}

            strategist = StrategistProfile(
                name=strategist_data["name"],
                team=strategist_data["team"],
                experience=strategist_data.get("experience", 0),
                aggression=strategist_data.get("aggression", 0.5),
                conservatism=strategist_data.get("conservatism", 0.5),
                intuition=strategist_data.get("intuition", 0.5),
                adaptability=strategist_data.get("adaptability", 0.5),
                analytical=strategist_data.get("analytical", 0.5),
                communication=strategist_data.get("communication", 0.5),
                wet_weather_skill=strategist_data.get("wet_weather_skill", 0.5),
                tire_management=strategist_data.get("tire_management", 0.5),
                undercut_skill=strategist_data.get("undercut_skill", 0.5),
                pit_timing=strategist_data.get("pit_timing", 0.5),
                track_familiarity=track_fam,
            )
            self._strategists[strategist.name] = strategist
            self._team_strategists[strategist.team] = strategist.name

    def save_to_json(self) -> None:
        """Save all strategist profiles back to JSON file."""
        strategists_data = []

        for strategist in self._strategists.values():
            strategist_dict = {
                "name": strategist.name,
                "team": strategist.team,
                "experience": strategist.experience,
                "aggression": strategist.aggression,
                "conservatism": strategist.conservatism,
                "intuition": strategist.intuition,
                "adaptability": strategist.adaptability,
                "analytical": strategist.analytical,
                "communication": strategist.communication,
                "wet_weather_skill": strategist.wet_weather_skill,
                "tire_management": strategist.tire_management,
                "undercut_skill": strategist.undercut_skill,
                "pit_timing": strategist.pit_timing,
                "track_familiarity": strategist.track_familiarity,
            }
            strategists_data.append(strategist_dict)

        # Ensure directory exists
        self._json_path.parent.mkdir(parents=True, exist_ok=True)

        data = {"strategists": strategists_data}

        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_strategist(self, strategist: StrategistProfile) -> None:
        """
        Add a strategist to the manager.

        Args:
            strategist: The strategist profile to add
        """
        self._strategists[strategist.name] = strategist
        self._team_strategists[strategist.team] = strategist.name

    def get_strategist(self, name: str) -> Optional[StrategistProfile]:
        """
        Get a strategist by name.

        Args:
            name: Strategist's name

        Returns:
            StrategistProfile if found, None otherwise
        """
        return self._strategists.get(name)

    def get_strategist_by_team(self, team: str) -> Optional[StrategistProfile]:
        """
        Get the strategist for a specific team.

        Args:
            team: Team name

        Returns:
            StrategistProfile for the team, None if not found
        """
        strategist_name = self._team_strategists.get(team)
        if strategist_name:
            return self._strategists.get(strategist_name)
        return None

    def list_strategists(self) -> List[str]:
        """
        Get list of all strategist names.

        Returns:
            List of strategist names
        """
        return list(self._strategists.keys())

    def list_teams(self) -> List[str]:
        """
        Get list of all team names that have strategists.

        Returns:
            List of team names
        """
        return list(self._team_strategists.keys())

    def update_strategist_stats(
        self,
        name: str,
        successful: int = 0,
        failed: int = 0,
    ) -> None:
        """
        Update strategist's successful/failed decision counts.

        Args:
            name: Strategist's name
            successful: Number of successful decisions to add
            failed: Number of failed decisions to add
        """
        strategist = self.get_strategist(name)
        if strategist:
            strategist.successful_decisions += successful
            strategist.failed_decisions += failed

    def add_track_familiarity(
        self,
        name: str,
        track_name: str,
        races: int = 1,
    ) -> None:
        """
        Add track familiarity to a strategist.

        Args:
            name: Strategist's name
            track_name: Name of the track
            races: Number of races to add (default 1)
        """
        strategist = self.get_strategist(name)
        if strategist:
            current = strategist.track_familiarity.get(track_name, 0)
            strategist.track_familiarity[track_name] = current + races


# Global strategist manager instance
_manager: Optional[StrategistManager] = None


def get_manager() -> StrategistManager:
    """
    Get the global strategist manager instance.

    Returns:
        The global StrategistManager
    """
    global _manager
    if _manager is None:
        _manager = StrategistManager()
    return _manager


def reset_manager() -> None:
    """Reset the global manager (useful for testing)."""
    global _manager
    _manager = None
