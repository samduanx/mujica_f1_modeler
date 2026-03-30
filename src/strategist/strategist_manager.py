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

from src.strategist.strategist_types import (
    StrategistProfile,
    TeamStrategyDecision,
    DecisionType,
    TrackSpecificRules,
    get_track_rules,
)


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

        # Team-level strategy sharing
        self._team_decisions: Dict[
            str, List[TeamStrategyDecision]
        ] = {}  # team -> decisions
        self._team_drivers: Dict[str, List[str]] = {}  # team -> list of driver names

        # Track-specific rules
        self._track_rules: Dict[str, TrackSpecificRules] = {}

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

    # ============== Team-Level Strategy Sharing ==============

    def register_team_drivers(self, team: str, drivers: List[str]) -> None:
        """
        Register the drivers for a team.

        Args:
            team: Team name
            drivers: List of driver names in the team
        """
        self._team_drivers[team] = drivers

    def get_teammates(self, team: str, driver: str) -> List[str]:
        """
        Get the teammates for a driver.

        Args:
            team: Team name
            driver: Driver name

        Returns:
            List of teammates (excluding the driver)
        """
        team_drivers = self._team_drivers.get(team, [])
        return [d for d in team_drivers if d != driver]

    def record_team_decision(
        self,
        team: str,
        decision_type: DecisionType,
        decision: any,
        primary_driver: str,
        current_lap: int,
    ) -> TeamStrategyDecision:
        """
        Record a team-level strategy decision.

        When a strategist makes a decision for one driver, it should be
        recorded so the same decision can be applied to the teammate.

        Args:
            team: Team name
            decision_type: Type of decision made
            decision: The actual strategy decision
            primary_driver: Driver for whom the decision was originally made
            current_lap: Current race lap

        Returns:
            The recorded team strategy decision
        """
        team_decision = TeamStrategyDecision(
            team=team,
            decision_type=decision_type,
            decision=decision,
            primary_driver=primary_driver,
            lap_decided=current_lap,
            applied_to=[primary_driver],
        )

        if team not in self._team_decisions:
            self._team_decisions[team] = []

        self._team_decisions[team].append(team_decision)

        return team_decision

    def get_pending_team_decisions(
        self,
        team: str,
        driver: str,
        current_lap: int,
    ) -> List[TeamStrategyDecision]:
        """
        Get pending team decisions that should be applied to a driver.

        Args:
            team: Team name
            driver: Driver name
            current_lap: Current race lap

        Returns:
            List of pending team decisions for this driver
        """
        if team not in self._team_decisions:
            return []

        pending = []
        for decision in self._team_decisions[team]:
            # Check if decision hasn't expired
            if decision.is_expired(current_lap):
                continue
            # Check if decision hasn't been applied to this driver yet
            if decision.is_applied_to(driver):
                continue
            # Check if decision is from teammate (not self)
            if decision.primary_driver == driver:
                continue

            pending.append(decision)

        return pending

    def apply_team_decision(
        self,
        team: str,
        decision: TeamStrategyDecision,
        driver: str,
    ) -> None:
        """
        Mark a team decision as applied to a driver.

        Args:
            team: Team name
            decision: The team decision to mark as applied
            driver: Driver who the decision was applied to
        """
        decision.apply_to_driver(driver)

    def clear_expired_team_decisions(self, current_lap: int) -> None:
        """
        Remove expired team decisions.

        Args:
            current_lap: Current race lap
        """
        for team in self._team_decisions:
            self._team_decisions[team] = [
                d for d in self._team_decisions[team]
                if not d.is_expired(current_lap)
            ]

    def reset_team_decisions(self) -> None:
        """Clear all team decisions (for new race)."""
        self._team_decisions.clear()
        self._team_drivers.clear()

    # ============== Track-Specific Rules ==============

    def get_track_rules(self, track_name: str) -> TrackSpecificRules:
        """
        Get track-specific rules for a track.

        Args:
            track_name: Name of the track

        Returns:
            TrackSpecificRules for the track
        """
        if track_name not in self._track_rules:
            self._track_rules[track_name] = get_track_rules(track_name)
        return self._track_rules[track_name]

    def is_pit_allowed(
        self,
        track_name: str,
        current_lap: int,
        last_pit_lap: int,
        pit_stops_completed: int,
        is_weather_related: bool = False,
        weather_pits_count: int = 0,
    ) -> tuple[bool, str]:
        """
        Check if a pit stop is allowed based on track rules.

        Args:
            track_name: Name of the track
            current_lap: Current race lap
            last_pit_lap: Lap of last pit stop
            pit_stops_completed: Number of pit stops already completed
            is_weather_related: Whether this is a weather-triggered pit
            weather_pits_count: Number of weather pits already done

        Returns:
            Tuple of (allowed, reason)
        """
        rules = self.get_track_rules(track_name)
        return rules.is_pit_allowed(
            current_lap=current_lap,
            last_pit_lap=last_pit_lap,
            pit_stops_completed=pit_stops_completed,
            is_weather_related=is_weather_related,
            weather_pits_count=weather_pits_count,
        )


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
