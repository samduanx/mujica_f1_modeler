"""
Dice Mechanics Module

Implements the dice rolling system for the Strategist System.
Handles all strategic decision dice rolls with modifiers and outcomes.
"""

import random
from typing import Optional, Dict, Any

from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    OutcomeLevel,
    determine_outcome,
    TRACK_UNDERCUT_DIFFICULTY,
)


class StrategistDiceRoller:
    """
    Handles all dice rolling for strategy decisions.

    This class provides methods for making various strategic decisions
    with appropriate modifiers based on the strategist's profile and
    the current race context.
    """

    def __init__(self, strategist: StrategistProfile):
        """
        Initialize the dice roller with a strategist profile.

        Args:
            strategist: The StrategistProfile to use for decisions
        """
        self.strategist = strategist

    def roll_d20(self) -> int:
        """Roll a 20-sided die."""
        return random.randint(1, 20)

    def roll_d10(self) -> int:
        """Roll a 10-sided die."""
        return random.randint(1, 10)

    def roll_d6(self) -> int:
        """Roll a 6-sided die."""
        return random.randint(1, 6)

    def roll_d100(self) -> int:
        """Roll a 100-sided die (percentile)."""
        return random.randint(1, 100)

    def calculate_modifiers(
        self,
        decision_type: DecisionType,
        context: RaceContext,
        base_tn: int = 12,
    ) -> Dict[str, Any]:
        """
        Calculate all modifiers for a decision.

        Args:
            decision_type: Type of decision being made
            context: Current race context
            base_tn: Base target number for the decision

        Returns:
            Dictionary with modifier details
        """
        modifiers = {
            "experience": self.strategist.get_experience_modifier(),
            "attributes": {},
            "track_familiarity": 0,
            "special": 0,
            "difficulty": 0,
            "total": 0,
        }

        # Add attribute modifiers based on decision type
        if decision_type == DecisionType.PIT_TIMING:
            modifiers["attributes"]["pit_timing"] = (
                self.strategist.get_pit_timing_modifier()
            )
            modifiers["attributes"]["tire_management"] = (
                self.strategist.get_tire_management_modifier()
            )
            modifiers["attributes"]["aggression"] = (
                self.strategist.get_aggression_modifier()
            )

        elif decision_type == DecisionType.TYRE_COMPOUND:
            modifiers["attributes"]["tire_management"] = (
                self.strategist.get_tire_management_modifier()
            )
            modifiers["attributes"]["analytical"] = (
                self.strategist.get_analytical_modifier()
            )
            modifiers["attributes"]["intuition"] = (
                self.strategist.get_intuition_modifier()
            )

        elif decision_type == DecisionType.RACING_PACE:
            modifiers["attributes"]["aggression"] = (
                self.strategist.get_aggression_modifier()
            )
            modifiers["attributes"]["conservatism"] = (
                self.strategist.get_conservatism_modifier()
            )
            modifiers["attributes"]["analytical"] = (
                self.strategist.get_analytical_modifier()
            )

        elif decision_type == DecisionType.WEATHER_RESPONSE:
            modifiers["attributes"]["wet_weather"] = (
                self.strategist.get_wet_weather_modifier()
            )
            modifiers["attributes"]["intuition"] = (
                self.strategist.get_intuition_modifier()
            )
            modifiers["attributes"]["adaptability"] = (
                self.strategist.get_adaptability_modifier()
            )

        elif decision_type == DecisionType.SAFETY_CAR_RESPONSE:
            modifiers["attributes"]["analytical"] = (
                self.strategist.get_analytical_modifier()
            )
            modifiers["attributes"]["adaptability"] = (
                self.strategist.get_adaptability_modifier()
            )
            modifiers["attributes"]["aggression"] = (
                self.strategist.get_aggression_modifier()
            )

        elif decision_type == DecisionType.UNDERCUT_ATTEMPT:
            # Experience capped at +2 for undercut
            modifiers["experience"] = min(modifiers["experience"], 2)
            modifiers["attributes"]["undercut"] = (
                self.strategist.get_undercut_modifier()
            )
            modifiers["attributes"]["pit_timing"] = (
                self.strategist.get_pit_timing_modifier()
            )
            modifiers["attributes"]["aggression"] = (
                self.strategist.get_aggression_modifier()
            )

        # Track familiarity bonus
        modifiers["track_familiarity"] = self.strategist.get_track_familiarity_bonus(
            context.track_name
        )

        # Special modifiers
        # Previous success/failure this race
        if self.strategist.successful_decisions > 0:
            success_bonus = min(self.strategist.successful_decisions, 3)
            modifiers["special"] += success_bonus
        if self.strategist.failed_decisions > 0:
            failure_penalty = -min(self.strategist.failed_decisions, 3)
            modifiers["special"] += failure_penalty

        # Driver trust modifier
        if context.driver_trust >= 0.8:
            modifiers["special"] += 1
        elif context.driver_trust <= 0.2:
            modifiers["special"] -= 1

        # Pressure situation modifier
        if context.pressure_level >= 3:
            modifiers["difficulty"] -= 3
        elif context.pressure_level == 2:
            modifiers["difficulty"] -= 2
        elif context.pressure_level == 1:
            modifiers["difficulty"] -= 1

        # Championship implications
        if context.championship_leading:
            modifiers["difficulty"] -= 1

        # Calculate total
        modifiers["total"] = (
            modifiers["experience"]
            + sum(modifiers["attributes"].values())
            + modifiers["track_familiarity"]
            + modifiers["special"]
            + modifiers["difficulty"]
        )

        return modifiers

    def roll_decision(
        self,
        decision_type: DecisionType,
        context: RaceContext,
        base_tn: int = 12,
    ) -> StrategyDecision:
        """
        Roll for a strategic decision.

        Args:
            decision_type: Type of decision to make
            context: Current race context
            base_tn: Base target number

        Returns:
            StrategyDecision with outcome
        """
        # Calculate modifiers
        modifiers = self.calculate_modifiers(decision_type, context, base_tn)

        # Roll the die
        roll = self.roll_d20()

        # Calculate final value
        final_value = roll + modifiers["total"]

        # Determine outcome
        outcome = determine_outcome(roll, final_value)

        # Generate description based on outcome
        description = self._generate_description(decision_type, outcome, modifiers)

        # Calculate impacts based on decision type
        time_impact, position_impact = self._calculate_impacts(
            decision_type, outcome, roll, final_value
        )

        return StrategyDecision(
            decision_type=decision_type,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=description,
            time_impact=time_impact,
            position_impact=position_impact,
            special_effects={},
        )

    def _generate_description(
        self,
        decision_type: DecisionType,
        outcome: OutcomeLevel,
        modifiers: Dict[str, Any],
    ) -> str:
        """Generate a human-readable description of the decision."""
        outcome_descriptions = {
            OutcomeLevel.CRITICAL_FAILURE: "Disastrous outcome - worst possible result",
            OutcomeLevel.FAILURE: "Decision backfired with negative consequences",
            OutcomeLevel.PARTIAL_SUCCESS: "Works but with complications",
            OutcomeLevel.SUCCESS: "Decision works as intended",
            OutcomeLevel.GREAT_SUCCESS: "Better than expected outcome",
            OutcomeLevel.CRITICAL_SUCCESS: "Exceptional result with maximum benefit",
        }

        decision_names = {
            DecisionType.PIT_TIMING: "pit stop timing",
            DecisionType.TYRE_COMPOUND: " tyre compound selection",
            DecisionType.RACING_PACE: "racing pace",
            DecisionType.WEATHER_RESPONSE: "weather response",
            DecisionType.SAFETY_CAR_RESPONSE: "Safety Car response",
            DecisionType.UNDERCUT_ATTEMPT: "undercut attempt",
            DecisionType.TEAM_ORDER: "team order",
        }

        desc = f"{decision_names.get(decision_type, 'decision')}: {outcome_descriptions.get(outcome, 'Unknown')}"

        # Add modifier info
        if modifiers["total"] >= 3:
            desc += " (strong modifier)"
        elif modifiers["total"] <= -3:
            desc += " (weak modifier)"

        return desc

    def _calculate_impacts(
        self,
        decision_type: DecisionType,
        outcome: OutcomeLevel,
        roll: int,
        final_value: int,
    ) -> tuple[float, int]:
        """Calculate time and position impacts based on outcome."""
        time_impact = 0.0
        position_impact = 0

        # Time impacts (seconds added to pit stop time)
        if decision_type == DecisionType.PIT_TIMING:
            if outcome == OutcomeLevel.CRITICAL_SUCCESS:
                time_impact = -3.0  # Perfect
            elif outcome == OutcomeLevel.GREAT_SUCCESS:
                time_impact = -1.5  # Optimal
            elif outcome == OutcomeLevel.SUCCESS:
                time_impact = 0.0  # Good
            elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
                time_impact = 1.0  # Slightly off
            elif outcome == OutcomeLevel.FAILURE:
                time_impact = 3.0  # Poor
            elif outcome == OutcomeLevel.CRITICAL_FAILURE:
                time_impact = 6.0  # Disastrous

        # Position impacts for various decisions
        elif decision_type == DecisionType.UNDERCUT_ATTEMPT:
            if outcome == OutcomeLevel.CRITICAL_SUCCESS:
                position_impact = 2
            elif outcome == OutcomeLevel.GREAT_SUCCESS:
                position_impact = 1
            elif outcome == OutcomeLevel.SUCCESS:
                position_impact = 0
            elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
                position_impact = -1
            elif outcome == OutcomeLevel.FAILURE:
                position_impact = -2
            elif outcome == OutcomeLevel.CRITICAL_FAILURE:
                position_impact = -3

        elif decision_type == DecisionType.WEATHER_RESPONSE:
            if outcome == OutcomeLevel.CRITICAL_SUCCESS:
                position_impact = 3
            elif outcome == OutcomeLevel.GREAT_SUCCESS:
                position_impact = 2
            elif outcome == OutcomeLevel.SUCCESS:
                position_impact = 0
            elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
                position_impact = -1
            elif outcome == OutcomeLevel.FAILURE:
                position_impact = -2
            elif outcome == OutcomeLevel.CRITICAL_FAILURE:
                position_impact = -4

        return time_impact, position_impact

    def roll_undercut(
        self,
        context: RaceContext,
        track_difficulty: Optional[int] = None,
    ) -> StrategyDecision:
        """
        Roll for an undercut attempt.

        Args:
            context: Current race context
            track_difficulty: Track-specific difficulty penalty (optional)

        Returns:
            StrategyDecision for the undercut attempt
        """
        # Base TN is 15 for undercut
        base_tn = 15

        # Calculate base modifiers
        modifiers = self.calculate_modifiers(
            DecisionType.UNDERCUT_ATTEMPT, context, base_tn
        )

        # Add track difficulty if provided
        if track_difficulty is None:
            track_difficulty = TRACK_UNDERCUT_DIFFICULTY.get(context.track_name, 0)
        modifiers["difficulty"] += track_difficulty
        modifiers["total"] = (
            modifiers["experience"]
            + sum(modifiers["attributes"].values())
            + modifiers["track_familiarity"]
            + modifiers["special"]
            + modifiers["difficulty"]
        )

        # Roll
        roll = self.roll_d20()
        final_value = roll + modifiers["total"]

        # Determine outcome
        outcome = determine_outcome(roll, final_value)

        # Generate description
        desc = self._generate_description(
            DecisionType.UNDERCUT_ATTEMPT, outcome, modifiers
        )

        # Calculate impacts
        time_impact, position_impact = self._calculate_impacts(
            DecisionType.UNDERCUT_ATTEMPT, outcome, roll, final_value
        )

        return StrategyDecision(
            decision_type=DecisionType.UNDERCUT_ATTEMPT,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=desc,
            time_impact=time_impact,
            position_impact=position_impact,
            special_effects={"track_difficulty": track_difficulty},
        )

    def roll_pit_timing(
        self,
        context: RaceContext,
        is_undercut: bool = False,
        is_stacked: bool = False,
    ) -> StrategyDecision:
        """
        Roll for pit stop timing decision.

        Args:
            context: Current race context
            is_undercut: Whether this is an undercut attempt
            is_stacked: Whether pit stops are stacked (Monaco-style)

        Returns:
            StrategyDecision for pit timing
        """
        # Base TN is 12
        base_tn = 12

        # Calculate modifiers
        modifiers = self.calculate_modifiers(DecisionType.PIT_TIMING, context, base_tn)

        # Add difficulty modifiers
        if is_undercut:
            modifiers["difficulty"] -= 3  # -3 for undercut (TN 15)
        if is_stacked:
            modifiers["difficulty"] -= 2  # -2 for stacked stops
        if context.is_wet:
            modifiers["difficulty"] -= 2  # Wet weather uncertainty

        # Recalculate total
        modifiers["total"] = (
            modifiers["experience"]
            + sum(modifiers["attributes"].values())
            + modifiers["track_familiarity"]
            + modifiers["special"]
            + modifiers["difficulty"]
        )

        # Roll
        roll = self.roll_d20()
        final_value = roll + modifiers["total"]

        # Determine outcome
        outcome = determine_outcome(roll, final_value)

        # Generate description
        desc = self._generate_description(DecisionType.PIT_TIMING, outcome, modifiers)

        # Calculate time impact
        time_impact, position_impact = self._calculate_impacts(
            DecisionType.PIT_TIMING, outcome, roll, final_value
        )

        return StrategyDecision(
            decision_type=DecisionType.PIT_TIMING,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=desc,
            time_impact=time_impact,
            position_impact=position_impact,
            special_effects={"is_undercut": is_undercut, "is_stacked": is_stacked},
        )

    def roll_weather_response(
        self,
        context: RaceContext,
        forecast_certainty: int = 0,  # 0=certain, 3=very uncertain
    ) -> StrategyDecision:
        """
        Roll for weather response decision.

        Args:
            context: Current race context
            forecast_certainty: Forecast certainty (0=certain, 3=very uncertain)

        Returns:
            StrategyDecision for weather response
        """
        # Base TN is 14 for weather
        base_tn = 14

        # Calculate modifiers
        modifiers = self.calculate_modifiers(
            DecisionType.WEATHER_RESPONSE, context, base_tn
        )

        # Add forecast uncertainty penalty
        modifiers["difficulty"] -= forecast_certainty

        # Recalculate total
        modifiers["total"] = (
            modifiers["experience"]
            + sum(modifiers["attributes"].values())
            + modifiers["track_familiarity"]
            + modifiers["special"]
            + modifiers["difficulty"]
        )

        # Roll
        roll = self.roll_d20()
        final_value = roll + modifiers["total"]

        # Determine outcome
        outcome = determine_outcome(roll, final_value)

        # Generate description
        desc = self._generate_description(
            DecisionType.WEATHER_RESPONSE, outcome, modifiers
        )

        # Calculate time and position impacts
        # Weather response impacts are measured in lap timing difference
        time_impact = 0.0
        position_impact = 0

        if outcome == OutcomeLevel.CRITICAL_SUCCESS:
            time_impact = -2.0  # Anticipatory
            position_impact = 3
        elif outcome == OutcomeLevel.GREAT_SUCCESS:
            time_impact = -1.0  # Early
            position_impact = 2
        elif outcome == OutcomeLevel.SUCCESS:
            time_impact = 0.0  # Optimal
            position_impact = 0
        elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
            time_impact = 1.0  # Reactive
            position_impact = -1
        elif outcome == OutcomeLevel.FAILURE:
            time_impact = 3.0  # Late
            position_impact = -2
        elif outcome == OutcomeLevel.CRITICAL_FAILURE:
            time_impact = 5.0  # Disastrous
            position_impact = -4

        return StrategyDecision(
            decision_type=DecisionType.WEATHER_RESPONSE,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=desc,
            time_impact=time_impact,
            position_impact=position_impact,
            special_effects={"forecast_certainty": forecast_certainty},
        )

    def roll_sc_response(
        self,
        context: RaceContext,
        is_vsc: bool = False,
        is_end_of_race: bool = False,
    ) -> StrategyDecision:
        """
        Roll for Safety Car / VSC response decision.

        Args:
            context: Current race context
            is_vsc: Whether this is a VSC (not full SC)
            is_end_of_race: Whether this is late in the race

        Returns:
            StrategyDecision for SC/VSC response
        """
        # Base TN is 13 for SC/VSC
        base_tn = 13

        # Calculate modifiers
        modifiers = self.calculate_modifiers(
            DecisionType.SAFETY_CAR_RESPONSE, context, base_tn
        )

        # Add situation complexity penalties
        if is_vsc:
            modifiers["difficulty"] -= 1  # VSC has shorter window
        if is_end_of_race:
            modifiers["difficulty"] -= 2  # Unknown duration
        if context.pressure_level >= 2:
            modifiers["difficulty"] -= 1  # Championship implications

        # Add aggression preference
        if self.strategist.aggression > 0.6:
            modifiers["attributes"]["aggression_preference"] = -1  # Prefer stay out
        elif self.strategist.conservatism > 0.6:
            modifiers["attributes"]["aggression_preference"] = 1  # Prefer pit

        # Recalculate total
        modifiers["total"] = (
            modifiers["experience"]
            + sum(modifiers["attributes"].values())
            + modifiers["track_familiarity"]
            + modifiers["special"]
            + modifiers["difficulty"]
        )

        # Roll
        roll = self.roll_d20()
        final_value = roll + modifiers["total"]

        # Determine outcome
        outcome = determine_outcome(roll, final_value)

        # Generate description
        desc = self._generate_description(
            DecisionType.SAFETY_CAR_RESPONSE, outcome, modifiers
        )

        return StrategyDecision(
            decision_type=DecisionType.SAFETY_CAR_RESPONSE,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=desc,
            time_impact=0.0,
            position_impact=0,
            special_effects={"is_vsc": is_vsc, "is_end_of_race": is_end_of_race},
        )

    def determine_outcome(
        self,
        decision_type: DecisionType,
        base_tn: int,
        context: RaceContext,
        include_momentum: bool = True,
    ) -> StrategyDecision:
        """
        Determine outcome for any decision type.

        This is a convenience method that routes to the appropriate
        decision-specific roll method.

        Args:
            decision_type: Type of decision
            base_tn: Base target number
            context: Current race context
            include_momentum: Whether to apply momentum modifiers

        Returns:
            StrategyDecision with outcome
        """
        if decision_type == DecisionType.PIT_TIMING:
            return self.roll_pit_timing(context)
        elif decision_type == DecisionType.UNDERCUT_ATTEMPT:
            return self.roll_undercut(context)
        elif decision_type == DecisionType.WEATHER_RESPONSE:
            return self.roll_weather_response(context)
        elif decision_type == DecisionType.SAFETY_CAR_RESPONSE:
            return self.roll_sc_response(context)
        else:
            # Generic decision
            return self.roll_decision(decision_type, context, base_tn)
