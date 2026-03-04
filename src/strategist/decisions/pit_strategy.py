"""
Pit Strategy Decision Module

Handles all pit stop related strategy decisions:
- decide_pit_timing(): When to pit
- select_tyre_compound(): Which tyre to use
- decide_undercut_attempt(): Whether to attempt an undercut
"""

from typing import Optional, Tuple
from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    OutcomeLevel,
    TRACK_PIT_LOSS,
)
from src.strategist.dice_mechanics import StrategistDiceRoller


# Standard tyre compounds available
TYRE_COMPOUNDS = ["SOFT", "MEDIUM", "HARD", "INTER", "WET"]


def decide_pit_timing(
    strategist: StrategistProfile,
    context: RaceContext,
    is_undercut: bool = False,
    is_stacked: bool = False,
) -> Tuple[StrategyDecision, Optional[int]]:
    """
    Decide when to make a pit stop.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        is_undercut: Whether this is an undercut attempt
        is_stacked: Whether pit stops are stacked

    Returns:
        Tuple of (StrategyDecision, optimal_pit_lap)
    """
    roller = StrategistDiceRoller(strategist)
    decision = roller.roll_pit_timing(context, is_undercut, is_stacked)

    # Calculate optimal pit lap based on decision outcome
    # Optimal window is typically around lap 20-25 for softs, 35-40 for mediums, etc.
    tyre_stint_length = context.tyre_life if context.tyre_life > 0 else 20

    # Adjust based on outcome
    if decision.outcome == OutcomeLevel.CRITICAL_SUCCESS:
        optimal_lap = context.current_lap - 2  # Earlier
    elif decision.outcome == OutcomeLevel.GREAT_SUCCESS:
        optimal_lap = context.current_lap - 1
    elif decision.outcome == OutcomeLevel.SUCCESS:
        optimal_lap = context.current_lap
    elif decision.outcome == OutcomeLevel.PARTIAL_SUCCESS:
        optimal_lap = context.current_lap + 1
    elif decision.outcome == OutcomeLevel.FAILURE:
        optimal_lap = context.current_lap + 3
    else:  # Critical failure
        optimal_lap = context.current_lap + 5

    return decision, optimal_lap


def select_tyre_compound(
    strategist: StrategistProfile,
    context: RaceContext,
    rain_probability: float = 0.0,
) -> Tuple[StrategyDecision, str]:
    """
    Select the tyre compound for the next stint.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        rain_probability: Probability of rain (0.0-1.0)

    Returns:
        Tuple of (StrategyDecision, selected_compound)
    """
    roller = StrategistDiceRoller(strategist)

    # Determine weather uncertainty penalty
    if rain_probability <= 0.20:
        weather_penalty = 0
    elif rain_probability <= 0.40:
        weather_penalty = 1
    elif rain_probability <= 0.60:
        weather_penalty = 2
    elif rain_probability <= 0.80:
        weather_penalty = 3
    else:
        weather_penalty = -1  # Certainty returns at 80%+

    # Base TN is 12
    base_tn = 12

    # Calculate modifiers
    modifiers = roller.calculate_modifiers(DecisionType.TYRE_COMPOUND, context, base_tn)
    modifiers["difficulty"] -= weather_penalty

    # Experience capped at +2 for tyre selection
    modifiers["experience"] = min(modifiers["experience"], 2)

    # Recalculate total
    modifiers["total"] = (
        modifiers["experience"]
        + sum(modifiers["attributes"].values())
        + modifiers["track_familiarity"]
        + modifiers["special"]
        + modifiers["difficulty"]
    )

    # Roll
    roll = roller.roll_d20()
    final_value = roll + modifiers["total"]

    # Determine outcome
    from src.strategist.strategist_types import determine_outcome

    outcome = determine_outcome(roll, final_value)

    # Determine compound based on outcome and conditions
    if context.is_wet or rain_probability > 0.5:
        compound = select_wet_compound(outcome, rain_probability)
    else:
        compound = select_dry_compound(outcome, context)

    # Generate description
    description = f"Tyre compound selection: {compound} - {outcome.value}"

    return StrategyDecision(
        decision_type=DecisionType.TYRE_COMPOUND,
        roll=roll,
        modifier=modifiers["total"],
        final_value=final_value,
        outcome=outcome,
        description=description,
        special_effects={
            "compound": compound,
            "rain_probability": rain_probability,
        },
    ), compound


def select_dry_compound(outcome: OutcomeLevel, context: RaceContext) -> str:
    """
    Select appropriate dry compound based on race situation.

    Args:
        outcome: Decision outcome
        context: Race context

    Returns:
        Tyre compound string
    """
    laps_remaining = context.total_laps - context.current_lap

    # Determine base compound based on race length
    if laps_remaining > 50:
        # Long stint possible
        if outcome == OutcomeLevel.CRITICAL_SUCCESS:
            return "MEDIUM"  # Optimal
        elif outcome == OutcomeLevel.GREAT_SUCCESS:
            return "MEDIUM"
        elif outcome == OutcomeLevel.SUCCESS:
            return "HARD"
        elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
            return "HARD"
        elif outcome == OutcomeLevel.FAILURE:
            return "SOFT"  # Wrong choice
        else:
            return "SOFT"  # Disaster
    else:
        # Shorter stint
        if outcome == OutcomeLevel.CRITICAL_SUCCESS:
            return "SOFT"
        elif outcome == OutcomeLevel.GREAT_SUCCESS:
            return "SOFT"
        elif outcome == OutcomeLevel.SUCCESS:
            return "MEDIUM"
        elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
            return "HARD"
        elif outcome == OutcomeLevel.FAILURE:
            return "HARD"
        else:
            return "MEDIUM"


def select_wet_compound(outcome: OutcomeLevel, rain_probability: float) -> str:
    """
    Select appropriate wet weather compound.

    Args:
        outcome: Decision outcome
        rain_probability: Probability of rain

    Returns:
        Tyre compound string (INTER or WET)
    """
    if rain_probability > 0.8:
        if outcome.value in ["critical_success", "great_success", "success"]:
            return "WET"
        else:
            return "INTER"
    else:
        return "INTER"


def decide_undercut_attempt(
    strategist: StrategistProfile,
    context: RaceContext,
    opponent_ahead_laps: int,
    track_difficulty: Optional[int] = None,
) -> Tuple[StrategyDecision, bool]:
    """
    Decide whether to attempt an undercut.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        opponent_ahead_laps: Laps since opponent ahead pitted
        track_difficulty: Track-specific undercut difficulty

    Returns:
        Tuple of (StrategyDecision, should_attempt_undercut)
    """
    roller = StrategistDiceRoller(strategist)
    decision = roller.roll_undercut(context, track_difficulty)

    # Determine if should attempt based on outcome
    # Great success or better = attempt, Failure or worse = don't
    if decision.outcome in [
        OutcomeLevel.CRITICAL_SUCCESS,
        OutcomeLevel.GREAT_SUCCESS,
    ]:
        should_attempt = True
    elif decision.outcome in [
        OutcomeLevel.FAILURE,
        OutcomeLevel.CRITICAL_FAILURE,
    ]:
        should_attempt = False
    else:
        # Partial success or success - use context to decide
        # If opponent just pitted, more likely to attempt
        should_attempt = opponent_ahead_laps <= 2

    return decision, should_attempt


def get_pit_loss_time(
    track_name: str, is_sc: bool = False, is_vsc: bool = False
) -> float:
    """
    Get the standard pit loss time for a track.

    Args:
        track_name: Name of the track
        is_sc: Whether Safety Car is active
        is_vsc: Whether VSC is active

    Returns:
        Pit loss time in seconds
    """
    base_loss = TRACK_PIT_LOSS.get(track_name, 22.0)

    if is_sc:
        return base_loss - 10.0  # ~12s under SC
    elif is_vsc:
        return base_loss - 14.0  # ~8s under VSC
    else:
        return base_loss


def calculate_pit_advantage(
    our_pit_lap: int,
    opponent_pit_lap: int,
    pit_loss: float,
    tyre_delta: float = 0.5,
) -> float:
    """
    Calculate the potential advantage from an undercut.

    Args:
        our_pit_lap: Our pit lap
        opponent_pit_lap: Opponent's pit lap
        pit_loss: Base pit loss time
        tyre_delta: Expected pace advantage from fresher tyres

    Returns:
        Net advantage in seconds (positive = we gain time)
    """
    lap_difference = opponent_pit_lap - our_pit_lap
    return (lap_difference * tyre_delta) - pit_loss
