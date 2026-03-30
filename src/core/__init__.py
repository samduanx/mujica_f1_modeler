"""Core module for F1 lap time modelling.

This module contains the basic lap modelling functionality:
- Fastest lap emulation
- Lap time calculations
- R-value and performance metrics
- Narrative assistance for story-driven simulations
"""


def _load_fastest_lap_emu():
    """Lazy-load fastest_lap_emu to avoid heavy side effects at package import time."""
    from . import fastest_lap_emu

    return fastest_lap_emu


def calculate_base_lap_time(*args, **kwargs):
    return _load_fastest_lap_emu().calculate_base_lap_time(*args, **kwargs)


def calculate_degradation(*args, **kwargs):
    return _load_fastest_lap_emu().calculate_degradation(*args, **kwargs)


def calculate_lap_time(*args, **kwargs):
    return _load_fastest_lap_emu().calculate_lap_time(*args, **kwargs)


def simulate_race(*args, **kwargs):
    return _load_fastest_lap_emu().simulate_race(*args, **kwargs)


# Import narrative assistance
from .narrative_assist import (
    NarrativeAssistConfig,
    ProbabilityBalancer,
    get_balancer,
    is_narrative_assist_enabled,
)

__all__ = [
    "NarrativeAssistConfig",
    "ProbabilityBalancer",
    "get_balancer",
    "is_narrative_assist_enabled",
    "calculate_base_lap_time",
    "calculate_degradation",
    "calculate_lap_time",
    "simulate_race",
]
