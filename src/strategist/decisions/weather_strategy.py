"""
Weather Strategy Decision Module

Handles weather-related strategy decisions:
- decide_weather_response(): How to respond to changing weather
- predict_rain_arrival(): Predict when rain will arrive
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


# Weather timing quality results (laps vs optimal)
WEATHER_TIMING = {
    OutcomeLevel.CRITICAL_SUCCESS: -2,  # 2 laps early
    OutcomeLevel.GREAT_SUCCESS: -1,  # 1 lap early
    OutcomeLevel.SUCCESS: 0,  # Optimal
    OutcomeLevel.PARTIAL_SUCCESS: 1,  # 1 lap late
    OutcomeLevel.FAILURE: 3,  # 3 laps late
    OutcomeLevel.CRITICAL_FAILURE: 5,  # 5 laps late
}

# Position impact from weather decisions
WEATHER_POSITION_IMPACT = {
    OutcomeLevel.CRITICAL_SUCCESS: 3,
    OutcomeLevel.GREAT_SUCCESS: 2,
    OutcomeLevel.SUCCESS: 0,
    OutcomeLevel.PARTIAL_SUCCESS: -1,
    OutcomeLevel.FAILURE: -2,
    OutcomeLevel.CRITICAL_FAILURE: -4,
}


def decide_weather_response(
    strategist: StrategistProfile,
    context: RaceContext,
    rain_probability: float,
    rain_eta: Optional[int],
    forecast_variance: float = 0.2,  # 20% variance by default
) -> Tuple[StrategyDecision, str, int]:
    """
    Decide how to respond to weather conditions.

    Args:
        strategist: The strategist making the decision
        context: Current race context
        rain_probability: Probability of rain (0.0-1.0)
        rain_eta: Estimated laps until rain (None if no rain expected)
        forecast_variance: Forecast certainty (0.0=certain, 1.0=very uncertain)

    Returns:
        Tuple of (StrategyDecision, recommended_action, timing_offset)
    """
    roller = StrategistDiceRoller(strategist)

    # Determine forecast certainty penalty
    if forecast_variance < 0.10:
        certainty_penalty = 0  # Certain
    elif forecast_variance < 0.25:
        certainty_penalty = 1  # Likely
    elif forecast_variance < 0.50:
        certainty_penalty = 2  # Uncertain
    else:
        certainty_penalty = 3  # Very uncertain

    # Roll for weather response
    decision = roller.roll_weather_response(context, certainty_penalty)

    # Determine timing offset (laps from optimal)
    timing_offset = WEATHER_TIMING.get(decision.outcome, 0)

    # Determine recommended action based on rain probability and outcome
    action = determine_weather_action(
        rain_probability,
        rain_eta,
        decision.outcome,
        context.current_lap,
        context.total_laps,
    )

    # Generate description
    timing_desc = (
        "early" if timing_offset < 0 else ("late" if timing_offset > 0 else "optimal")
    )
    description = f"Weather response: {action} - {timing_offset:+d} laps ({timing_desc}) - {decision.outcome.value}"

    decision.description = description

    return decision, action, timing_offset


def determine_weather_action(
    rain_probability: float,
    rain_eta: Optional[int],
    outcome: OutcomeLevel,
    current_lap: int,
    total_laps: int,
) -> str:
    """
    Determine the recommended weather action.

    Args:
        rain_probability: Probability of rain
        rain_eta: Estimated laps until rain
        outcome: Decision outcome
        current_lap: Current race lap
        total_laps: Total race laps

    Returns:
        Recommended action string
    """
    # Base action on rain probability
    if rain_probability > 0.8:
        base_action = "BOX_FOR_WETS"
    elif rain_probability > 0.5:
        base_action = "BOX_FOR_INTERS"
    elif rain_probability > 0.3:
        base_action = "PREPARE_FOR_WETS"
    else:
        base_action = "STAY_OUT"

    # Adjust based on outcome
    if outcome == OutcomeLevel.CRITICAL_SUCCESS:
        # Perfect prediction - act early
        if rain_probability > 0.5:
            return "BOX_NOW"
        else:
            return base_action

    elif outcome == OutcomeLevel.GREAT_SUCCESS:
        # Good prediction - slightly early
        return base_action

    elif outcome == OutcomeLevel.SUCCESS:
        # Optimal timing
        return base_action

    elif outcome == OutcomeLevel.PARTIAL_SUCCESS:
        # Reactive - slightly late
        if base_action == "BOX_NOW":
            return "BOX_NEXT_LAP"
        elif base_action == "BOX_FOR_WETS":
            return "BOX_FOR_INTERS"
        else:
            return "WAIT_AND_SEE"

    elif outcome == OutcomeLevel.FAILURE:
        # Late reaction
        if rain_probability > 0.7:
            return "BOX_EMERGENCY"
        else:
            return "STAY_OUT_LONGER"

    else:  # Critical failure
        # Completely wrong
        return "WRONG_COMPOUND"  # Likely the wrong call


def predict_rain_arrival(
    strategist: StrategistProfile,
    context: RaceContext,
    predicted_eta: int,
    certainty: float = 0.5,
) -> Tuple[int, str]:
    """
    Predict when rain will arrive.

    Args:
        strategist: The strategist making the prediction
        context: Current race context
        predicted_eta: Predicted laps until rain
        certainty: How certain the prediction is (0.0-1.0)

    Returns:
        Tuple of (adjusted_eta, confidence_level)
    """
    roller = StrategistDiceRoller(strategist)

    # Roll a d20 to see how accurate our prediction is
    roll = roller.roll_d20()

    # Calculate modifier based on wet weather skill
    wet_mod = strategist.get_wet_weather_modifier()
    intuition_mod = strategist.get_intuition_modifier()
    adaptability_mod = strategist.get_adaptability_modifier()

    modifier = wet_mod + intuition_mod + adaptability_mod
    final_value = roll + modifier

    # Determine confidence level
    if roll == 20:  # Critical success
        confidence = "perfect"
        adjusted_eta = predicted_eta
    elif final_value >= 18:
        confidence = "high"
        adjusted_eta = predicted_eta - 1 if predicted_eta > 1 else 1
    elif final_value >= 14:
        confidence = "good"
        adjusted_eta = predicted_eta
    elif final_value >= 10:
        confidence = "moderate"
        # Add some uncertainty
        import random

        variance = random.randint(-1, 1)
        adjusted_eta = max(1, predicted_eta + variance)
    elif final_value >= 6:
        confidence = "low"
        # Larger uncertainty
        import random

        variance = random.randint(-2, 2)
        adjusted_eta = max(1, predicted_eta + variance)
    else:  # Critical failure or very poor
        confidence = "very_low"
        # Completely off
        import random

        variance = random.randint(-3, 3)
        adjusted_eta = max(1, predicted_eta + variance)

    return adjusted_eta, confidence


def calculate_rain_intensity_prediction(
    strategist: StrategistProfile,
    expected_intensity: int,
) -> Tuple[int, str]:
    """
    Calculate rain intensity prediction accuracy.

    Uses d10 roll per STRATEGIST_DICE_RULES.md:
    - 1-2: Underestimated (need full wets, got inters)
    - 3-4: Slightly underestimated
    - 5-6: Accurate
    - 7-8: Slightly overestimated
    - 9-10: Overestimated (got wets, only needed inters)

    Args:
        strategist: The strategist making the prediction
        expected_intensity: Expected rain intensity (0-100)

    Returns:
        Tuple of (adjusted_intensity, accuracy)
    """
    roller = StrategistDiceRoller(strategist)
    roll = roller.roll_d10()

    if roll <= 2:
        # Underestimated
        adjusted = min(100, expected_intensity + 30)
        accuracy = "underestimated"
    elif roll <= 4:
        # Slightly underestimated
        adjusted = min(100, expected_intensity + 15)
        accuracy = "slightly_underestimated"
    elif roll <= 6:
        # Accurate
        adjusted = expected_intensity
        accuracy = "accurate"
    elif roll <= 8:
        # Slightly overestimated
        adjusted = max(0, expected_intensity - 15)
        accuracy = "slightly_overestimated"
    else:
        # Overestimated
        adjusted = max(0, expected_intensity - 30)
        accuracy = "overestimated"

    return adjusted, accuracy


def get_tyre_recommendation(
    is_wet: bool,
    rain_intensity: int,
    track_condition: str = "drying",
) -> str:
    """
    Get recommended tyre compound based on conditions.

    Args:
        is_wet: Whether track is wet
        rain_intensity: Rain intensity (0-100)
        track_condition: Track condition (dry, damp, wet, drying)

    Returns:
        Recommended tyre compound
    """
    if not is_wet and track_condition == "dry":
        return "DRY_COMPOUND"  # Let caller decide based on stint

    if track_condition == "drying":
        if rain_intensity < 20:
            return "INTER"
        else:
            return "WET"

    if rain_intensity < 30:
        return "INTER"
    elif rain_intensity < 70:
        return "WET"
    else:
        return "WET"  # Full wet
