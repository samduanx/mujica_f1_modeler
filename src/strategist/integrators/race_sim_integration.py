"""
Race Simulation Integration Module

Provides integration hooks for the Strategist System with the enhanced_long_dist_sim.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.strategist.strategist_types import (
    StrategistProfile,
    RaceContext,
    DecisionType,
    PaceMode,
    OutcomeLevel,
)
from src.strategist.strategist_manager import get_manager
from src.strategist.dice_mechanics import StrategistDiceRoller
from src.strategist.decisions.pit_strategy import (
    decide_pit_timing,
    select_tyre_compound,
    decide_undercut_attempt,
)
from src.strategist.decisions.pace_strategy import decide_racing_pace
from src.strategist.decisions.weather_strategy import decide_weather_response
from src.strategist.decisions.sc_strategy import decide_sc_response
from src.strategist.driver_interaction import DriverComplianceRoller, get_driver_profile


@dataclass
class StrategistState:
    """
    Current state of the strategist in a race.

    Tracks decisions made and their outcomes.
    """

    strategist_name: str
    team: str
    decisions_made: List[Dict[str, Any]]
    current_context: Optional[RaceContext]

    def add_decision(self, decision: Any) -> None:
        """Add a decision to the history."""
        self.decisions_made.append(
            {
                "decision_type": decision.decision_type.value
                if hasattr(decision, "decision_type")
                else str(decision),
                "outcome": decision.outcome.value
                if hasattr(decision, "outcome")
                else "unknown",
                "roll": decision.roll if hasattr(decision, "roll") else None,
                "modifier": decision.modifier
                if hasattr(decision, "modifier")
                else None,
            }
        )


class StrategistIntegration:
    """
    Integration class for connecting Strategist System with race simulation.

    This class provides hooks that can be called from the race simulation
    to make strategic decisions at key moments.
    """

    def __init__(self, team: str = "Ferrari", seed: Optional[int] = None):
        """
        Initialize the strategist integration.

        Args:
            team: Team name (default: Ferrari for protagonist)
            seed: Random seed for reproducibility
        """
        self.team = team

        # Get strategist for this team from the manager (loads from JSON)
        self.manager = get_manager()
        self.strategist = self.manager.get_strategist_by_team(team)

        if self.strategist is None:
            raise ValueError(f"No strategist found for team: {team}")

        # Initialize state
        self.state = StrategistState(
            strategist_name=self.strategist.name,
            team=team,
            decisions_made=[],
            current_context=None,
        )

        # Set random seed if provided
        if seed is not None:
            import random

            random.seed(seed)

    def update_context(
        self,
        current_lap: int,
        total_laps: int,
        race_position: int,
        tyre_life: int,
        current_tyre: str,
        is_wet: bool = False,
        rain_eta: Optional[int] = None,
        is_sc_active: bool = False,
        is_vsc_active: bool = False,
    ) -> None:
        """
        Update the race context for strategist decisions.

        Args:
            current_lap: Current race lap
            total_laps: Total race laps
            race_position: Current race position
            tyre_life: Laps remaining on current tyre
            current_tyre: Current tyre compound
            is_wet: Whether track is wet
            rain_eta: Estimated laps until rain
            is_sc_active: Whether Safety Car is active
            is_vsc_active: Whether VSC is active
        """
        # Determine pressure level based on race position and laps
        pressure_level = 0
        if race_position <= 3 and total_laps - current_lap <= 20:
            pressure_level = 3  # Championship contention
        elif race_position <= 5 and total_laps - current_lap <= 15:
            pressure_level = 2  # High stakes
        elif total_laps - current_lap <= 10:
            pressure_level = 1  # End of race

        self.state.current_context = RaceContext(
            track_name="Unknown",  # Set by simulation
            current_lap=current_lap,
            total_laps=total_laps,
            is_wet=is_wet,
            rain_eta=rain_eta,
            is_sc_active=is_sc_active,
            is_vsc_active=is_vsc_active,
            race_position=race_position,
            current_tyre=current_tyre,
            tyre_life=tyre_life,
            pressure_level=pressure_level,
            driver_trust=0.7,  # Default trust level
        )

    def on_pit_stop_decision(
        self,
        context: RaceContext,
        is_undercut: bool = False,
    ) -> Dict[str, Any]:
        """
        Hook for pit stop timing decisions.

        Called when making a pit stop decision.

        Args:
            context: Current race context
            is_undercut: Whether this is an undercut attempt

        Returns:
            Decision result dictionary
        """
        decision, optimal_lap = decide_pit_timing(
            self.strategist,
            context,
            is_undercut=is_undercut,
        )

        self.state.add_decision(decision)

        return {
            "decision": decision,
            "optimal_pit_lap": optimal_lap,
            "modifier_total": decision.modifier,
            "roll": decision.roll,
            "outcome": decision.outcome.value,
        }

    def on_tyre_selection(
        self,
        context: RaceContext,
        rain_probability: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Hook for tyre compound selection.

        Args:
            context: Current race context
            rain_probability: Probability of rain

        Returns:
            Decision result dictionary
        """
        decision, compound = select_tyre_compound(
            self.strategist,
            context,
            rain_probability,
        )

        self.state.add_decision(decision)

        return {
            "decision": decision,
            "selected_compound": compound,
            "modifier_total": decision.modifier,
            "roll": decision.roll,
            "outcome": decision.outcome.value,
        }

    def on_pace_decision(
        self,
        context: RaceContext,
        requested_mode: PaceMode = PaceMode.RACE,
    ) -> Dict[str, Any]:
        """
        Hook for racing pace decisions.

        Args:
            context: Current race context
            requested_mode: Requested pace mode

        Returns:
            Decision result dictionary
        """
        decision, mode, params = decide_racing_pace(
            self.strategist,
            context,
            requested_mode,
        )

        self.state.add_decision(decision)

        return {
            "decision": decision,
            "selected_mode": mode.value,
            "effectiveness": params.get("effectiveness", 1.0),
            "speed_modifier": params.get("speed", 1.0),
            "roll": decision.roll,
            "outcome": decision.outcome.value,
        }

    def on_weather_decision(
        self,
        context: RaceContext,
        rain_probability: float,
        rain_eta: Optional[int],
    ) -> Dict[str, Any]:
        """
        Hook for weather response decisions.

        Args:
            context: Current race context
            rain_probability: Probability of rain
            rain_eta: Estimated laps until rain

        Returns:
            Decision result dictionary
        """
        decision, action, timing = decide_weather_response(
            self.strategist,
            context,
            rain_probability,
            rain_eta,
        )

        self.state.add_decision(decision)

        return {
            "decision": decision,
            "recommended_action": action,
            "timing_offset": timing,
            "roll": decision.roll,
            "outcome": decision.outcome.value,
        }

    def on_sc_decision(
        self,
        context: RaceContext,
        is_vsc: bool = False,
        laps_until_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Hook for Safety Car response decisions.

        Args:
            context: Current race context
            is_vsc: Whether VSC is active
            laps_until_end: Laps remaining in race

        Returns:
            Decision result dictionary
        """
        decision, action, pit_recommendation = decide_sc_response(
            self.strategist,
            context,
            is_vsc=is_vsc,
            laps_until_end=laps_until_end,
        )

        self.state.add_decision(decision)

        return {
            "decision": decision,
            "recommended_action": action,
            "pit_recommendation": pit_recommendation,
            "roll": decision.roll,
            "outcome": decision.outcome.value,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get strategist statistics.

        Returns:
            Dictionary with decision statistics
        """
        total = len(self.state.decisions_made)
        if total == 0:
            return {
                "total_decisions": 0,
                "success_rate": 0.0,
            }

        successes = sum(
            1
            for d in self.state.decisions_made
            if "success" in d.get("outcome", "").lower()
        )
        failures = sum(
            1
            for d in self.state.decisions_made
            if "failure" in d.get("outcome", "").lower()
        )

        return {
            "total_decisions": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0.0,
            "decisions_by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Count decisions by type."""
        counts: Dict[str, int] = {}
        for decision in self.state.decisions_made:
            dec_type = decision.get("decision_type", "unknown")
            counts[dec_type] = counts.get(dec_type, 0) + 1
        return counts
