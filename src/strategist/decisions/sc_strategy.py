"""
Safety Car Strategy Decision Module

Handles Safety Car and Virtual Safety Car (VSC) response decisions:
- decide_sc_response(): How to respond to SC/VSC situations
"""

from typing import Tuple, Optional
from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    OutcomeLevel,
)
from src.strategist.dice_mechanics import StrategistDiceRoller
from src.strategist.decisions.pit_strategy import get_pit_loss_time


# SC/VSC Decision outcomes
SC_DECISION_QUALITY = {
    OutcomeLevel.CRITICAL_SUCCESS: "perfect",
    OutcomeLevel.GREAT_SUCCESS: "excellent",
    OutcomeLevel.SUCCESS: "good",
    OutcomeLevel.PARTIAL_SUCCESS: "questionable",
    OutcomeLevel.FAILURE: "poor",
    OutcomeLevel.CRITICAL_FAILURE: "disastrous",
}

# Recommended actions based on outcome
SC_RECOMMENDED_ACTIONS = {
    OutcomeLevel.CRITICAL_SUCCESS: "PIT_NOW_BONUS",  # Pit and gain position
    OutcomeLevel.GREAT_SUCCESS: "PIT_NOW",  # Pit now
    OutcomeLevel.SUCCESS: "PIT_OR_STAY",  # Either works
    OutcomeLevel.PARTIAL_SUCCESS: "EVALUATE",  # 50/50 chance
    OutcomeLevel.FAILURE: "STAY_OUT",  # Don't pit
    OutcomeLevel.CRITICAL_FAILURE: "WRONG_CALL",  # Completely wrong
}


def decide_sc_response(
    strategist: StrategistProfile,
    context: RaceContext,
    is_vsc: bool = False,
    laps_until_end: Optional[int] = None,
    opponent_action: Optional[str] = None,
) -> Tuple[StrategyDecision, str, bool]:
    """
    Decide how to respond to a Safety Car or VSC situation.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        is_vsc: Whether this is a VSC (not full SC)
        laps_until_end: Laps remaining in the race (None if not applicable)
        opponent_action: What opponent ahead is doing (None, "pit", "stay")

    Returns:
        Tuple of (StrategyDecision, recommended_action, should_pit)
    """
    roller = StrategistDiceRoller(strategist)

    # Determine if this is end of race scenario
    is_end_of_race = laps_until_end is not None and laps_until_end <= 10

    # Roll for SC response
    decision = roller.roll_sc_response(context, is_vsc, is_end_of_race)

    # Get base pit loss times
    pit_loss_normal = get_pit_loss_time(context.track_name, is_sc=False, is_vsc=False)
    if is_vsc:
        pit_loss_sc = get_pit_loss_time(context.track_name, is_sc=False, is_vsc=True)
    else:
        pit_loss_sc = get_pit_loss_time(context.track_name, is_sc=True, is_vsc=False)

    # Determine recommended action based on outcome and context
    recommended_action = determine_sc_action(
        decision.outcome,
        context,
        is_vsc,
        is_end_of_race,
        laps_until_end,
        opponent_action,
    )

    # Determine if should pit based on action
    should_pit = recommended_action in ["PIT_NOW", "PIT_NOW_BONUS", "PIT_OR_STAY"]

    # Generate description
    quality = SC_DECISION_QUALITY.get(decision.outcome, "unknown")
    description = f"SC/VSC Response ({quality}): {recommended_action}"
    if opponent_action:
        description += f" - Opponent: {opponent_action}"

    decision.description = description

    # Add special effects
    decision.special_effects = {
        "is_vsc": is_vsc,
        "pit_loss_normal": pit_loss_normal,
        "pit_loss_under_sc": pit_loss_sc,
        "recommended_action": recommended_action,
    }

    return decision, recommended_action, should_pit


def determine_sc_action(
    outcome: OutcomeLevel,
    context: RaceContext,
    is_vsc: bool,
    is_end_of_race: bool,
    laps_until_end: Optional[int],
    opponent_action: Optional[str],
) -> str:
    """
    Determine the recommended SC/VSC action.

    Args:
        outcome: Decision outcome
        context: Race context
        is_vsc: Whether VSC is active
        is_end_of_race: Whether late in race
        laps_until_end: Laps remaining
        opponent_action: Opponent's action

    Returns:
        Recommended action string
    """
    # Base action on outcome
    base_action = SC_RECOMMENDED_ACTIONS.get(outcome, "EVALUATE")

    # Adjust based on race situation

    # If opponent is pitting, we might want to stay out (or vice versa)
    if opponent_action == "pit" and base_action == "PIT_OR_STAY":
        return "STAY_OUT"  # Counter their move
    elif opponent_action == "stay" and base_action == "PIT_OR_STAY":
        return "PIT_NOW"  # Gain advantage

    # End of race adjustments
    if is_end_of_race and laps_until_end is not None:
        if laps_until_end <= 3:
            # Too late to pit
            return "STAY_OUT"
        elif laps_until_end <= 5:
            if base_action == "PIT_NOW" or base_action == "PIT_NOW_BONUS":
                return "PIT_NOW"  # Last chance
            else:
                return "STAY_OUT"

    # VSC adjustments - window is shorter
    if is_vsc:
        if base_action == "PIT_OR_STAY":
            return "PIT_NOW"  # Under VSC, commit to decision
        elif base_action == "EVALUATE":
            return "STAY_OUT"  # Too risky under VSC

    # Pressure situation - be more conservative
    if context.pressure_level >= 2:
        if "PIT" in base_action:
            return "PIT_OR_STAY"  # More cautious
        else:
            return base_action

    return base_action


def calculate_sc_pit_advantage(
    context: RaceContext,
    is_vsc: bool,
    is_first_pit: bool = True,
) -> float:
    """
    Calculate the potential advantage from pitting under SC/VSC.

    Args:
        context: Race context
        is_vsc: Whether VSC is active
        is_first_pit: Whether this is the first car to pit

    Returns:
        Advantage in seconds (positive = gaining time)
    """
    pit_loss_normal = get_pit_loss_time(context.track_name, is_sc=False, is_vsc=False)

    if is_vsc:
        pit_loss_caution = get_pit_loss_time(
            context.track_name, is_sc=False, is_vsc=True
        )
    else:
        pit_loss_caution = get_pit_loss_time(
            context.track_name, is_sc=True, is_vsc=False
        )

    # Advantage = normal pit loss - caution pit loss
    advantage = pit_loss_normal - pit_loss_caution

    # First pitter gets extra advantage
    if is_first_pit:
        advantage += 2.0  # Clean air

    return advantage


def should_pit_under_sc(
    context: RaceContext,
    tyre_life_remaining: int,
    laps_until_end: int,
    is_vsc: bool,
) -> Tuple[bool, str]:
    """
    Determine if pitting under SC/VSC is the right call.

    Uses simplified logic based on tyre life and race position.

    Args:
        context: Race context
        tyre_life_remaining: Laps remaining on current tyre
        laps_until_end: Laps remaining in race
        is_vsc: Whether VSC is active

    Returns:
        Tuple of (should_pit, reason)
    """
    # If tyre is about to die, must pit
    if tyre_life_remaining <= 3:
        return True, "TIRE_LIFE"

    # If race is almost over, stay out
    if laps_until_end <= 5:
        return False, "TOO_LATE"

    # If in points position and tyre is okay, stay out
    if context.race_position <= 10 and tyre_life_remaining >= 10:
        return False, "POINTS_POSITION"

    # If outside points and need track position, pit
    if context.race_position > 10 and tyre_life_remaining <= 15:
        return True, "GAIN_POSITION"

    # VSC makes pitting more attractive (lower pit loss)
    if is_vsc and tyre_life_remaining <= 12:
        return True, "VSC_WINDOW"

    # Default: evaluate based on pit loss comparison
    advantage = calculate_sc_pit_advantage(context, is_vsc)

    if advantage > 0:
        return True, "PIT_ADVANTAGE"
    else:
        return False, "NO_ADVANTAGE"
