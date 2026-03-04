"""
Pace Strategy Decision Module

Handles racing pace mode decisions:
- decide_racing_pace(): Select appropriate pace mode
"""

from typing import Tuple, Dict
from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    OutcomeLevel,
    PaceMode,
)
from src.strategist.dice_mechanics import StrategistDiceRoller


# Pace mode effectiveness multipliers
PACE_MODE_EFFECTIVENESS = {
    OutcomeLevel.CRITICAL_SUCCESS: 1.30,
    OutcomeLevel.GREAT_SUCCESS: 1.15,
    OutcomeLevel.SUCCESS: 1.00,
    OutcomeLevel.PARTIAL_SUCCESS: 0.85,
    OutcomeLevel.FAILURE: 0.65,
    OutcomeLevel.CRITICAL_FAILURE: 0.40,
}

# Base pace mode parameters
PACE_MODE_PARAMS = {
    PaceMode.PUSH: {"speed": 1.00, "tire_wear": 1.50, "fuel_use": 1.20, "risk": "high"},
    PaceMode.RACE: {
        "speed": 0.95,
        "tire_wear": 1.00,
        "fuel_use": 1.00,
        "risk": "normal",
    },
    PaceMode.MANAGE: {
        "speed": 0.90,
        "tire_wear": 0.70,
        "fuel_use": 0.85,
        "risk": "low",
    },
    PaceMode.SAVE: {
        "speed": 0.85,
        "tire_wear": 0.50,
        "fuel_use": 0.70,
        "risk": "very_low",
    },
    PaceMode.LIFT_AND_COAST: {
        "speed": 0.80,
        "tire_wear": 0.40,
        "fuel_use": 0.50,
        "risk": "minimal",
    },
}


def decide_racing_pace(
    strategist: StrategistProfile,
    context: RaceContext,
    requested_mode: PaceMode = PaceMode.RACE,
) -> Tuple[StrategyDecision, PaceMode, Dict[str, float]]:
    """
    Decide on racing pace mode.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        requested_mode: The pace mode being requested

    Returns:
        Tuple of (StrategyDecision, selected_mode, effectiveness_params)
    """
    roller = StrategistDiceRoller(strategist)

    # Determine which attribute to use based on requested mode
    if requested_mode == PaceMode.PUSH:
        attribute_key = "aggression"
    elif requested_mode in [PaceMode.MANAGE, PaceMode.SAVE]:
        attribute_key = "conservatism"
    else:  # RACE or LIFT_AND_COAST
        attribute_key = "analytical"

    # Base TN is 10 for pace decisions
    base_tn = 10

    # Calculate modifiers
    modifiers = roller.calculate_modifiers(DecisionType.RACING_PACE, context, base_tn)

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

    # Get effectiveness multiplier
    effectiveness = PACE_MODE_EFFECTIVENESS.get(outcome, 1.0)

    # Determine if we should stick with requested mode or adjust
    # based on outcome
    if outcome in [OutcomeLevel.CRITICAL_SUCCESS, OutcomeLevel.GREAT_SUCCESS]:
        selected_mode = requested_mode  # Execute as planned
    elif outcome == OutcomeLevel.SUCCESS:
        selected_mode = requested_mode  # Execute as planned
    elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
        # May need to adjust
        selected_mode = adjust_mode_for_partial_success(requested_mode)
    elif outcome == OutcomeLevel.FAILURE:
        # Failed execution, need to adjust
        selected_mode = adjust_mode_for_failure(requested_mode)
    else:  # Critical failure
        # Completely backfires
        selected_mode = get_alternative_mode(requested_mode)

    # Get pace parameters
    params = PACE_MODE_PARAMS.get(selected_mode, PACE_MODE_PARAMS[PaceMode.RACE])

    # Apply effectiveness multiplier
    adjusted_params = {
        "speed": params["speed"] * effectiveness,
        "tire_wear": params["tire_wear"],
        "fuel_use": params["fuel_use"],
        "risk": params["risk"],
        "effectiveness": effectiveness,
    }

    # Generate description
    description = f"Pace mode {selected_mode.value}: {outcome.value} (effectiveness: {effectiveness:.0%})"

    return (
        StrategyDecision(
            decision_type=DecisionType.RACING_PACE,
            roll=roll,
            modifier=modifiers["total"],
            final_value=final_value,
            outcome=outcome,
            description=description,
            special_effects={
                "requested_mode": requested_mode.value,
                "selected_mode": selected_mode.value,
                "effectiveness": effectiveness,
            },
        ),
        selected_mode,
        adjusted_params,
    )


def adjust_mode_for_partial_success(requested: PaceMode) -> PaceMode:
    """
    Adjust pace mode when outcome is partial success.

    If pushing too hard, back off slightly.
    If managing too much, push slightly.
    """
    if requested == PaceMode.PUSH:
        return PaceMode.RACE
    elif requested == PaceMode.MANAGE:
        return PaceMode.RACE
    elif requested == PaceMode.SAVE:
        return PaceMode.MANAGE
    else:
        return requested


def adjust_mode_for_failure(requested: PaceMode) -> PaceMode:
    """
    Adjust pace mode when outcome is failure.

    If pushing, need to back off significantly.
    If managing, try to balance.
    """
    if requested == PaceMode.PUSH:
        return PaceMode.MANAGE
    elif requested == PaceMode.RACE:
        return PaceMode.MANAGE
    elif requested == PaceMode.MANAGE:
        return PaceMode.SAVE
    elif requested == PaceMode.SAVE:
        return PaceMode.LIFT_AND_COAST
    else:
        return requested


def get_alternative_mode(requested: PaceMode) -> PaceMode:
    """
    Get completely different mode when outcome is critical failure.

    The strategy completely backfires.
    """
    if requested == PaceMode.PUSH:
        return PaceMode.SAVE  # Backfires, ends up saving
    elif requested == PaceMode.RACE:
        return PaceMode.SAVE
    elif requested == PaceMode.MANAGE:
        return PaceMode.PUSH  # Backfires into pushing
    elif requested == PaceMode.SAVE:
        return PaceMode.PUSH  # Backfires into pushing
    else:
        return PaceMode.RACE


def calculate_lap_time_modifier(
    mode: PaceMode,
    base_lap_time: float,
    effectiveness: float = 1.0,
) -> float:
    """
    Calculate modified lap time based on pace mode.

    Args:
        mode: Selected pace mode
        base_lap_time: Base lap time in seconds
        effectiveness: Effectiveness multiplier from decision

    Returns:
        Adjusted lap time in seconds
    """
    params = PACE_MODE_PARAMS.get(mode, PACE_MODE_PARAMS[PaceMode.RACE])
    speed_factor = params["speed"] * effectiveness
    return base_lap_time / speed_factor


def estimate_tire_degradation(
    mode: PaceMode,
    base_degradation: float,
    laps: int,
) -> float:
    """
    Estimate tire degradation over a stint.

    Args:
        mode: Selected pace mode
        base_degradation: Base degradation rate per lap
        laps: Number of laps in the stint

    Returns:
        Total degradation over the stint
    """
    params = PACE_MODE_PARAMS.get(mode, PACE_MODE_PARAMS[PaceMode.RACE])
    wear_factor = params["tire_wear"]
    return base_degradation * wear_factor * laps
