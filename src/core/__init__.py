"""Core module for F1 lap time modelling.

This module contains the basic lap modelling functionality:
- Fastest lap emulation
- Lap time calculations
- R-value and performance metrics
- Narrative assistance for story-driven simulations
"""

# Import fastest_lap_emu functions with error handling
try:
    from .fastest_lap_emu import (
        calculate_base_lap_time,
        calculate_degradation,
        calculate_lap_time,
        simulate_race,
    )
    _has_fastest_lap_emu = True
except ImportError:
    _has_fastest_lap_emu = False

# Import narrative assistance
from .narrative_assist import (
    NarrativeAssistConfig,
    ProbabilityBalancer,
    get_balancer,
    is_narrative_assist_enabled,
)

# Build __all__ dynamically
__all__ = [
    "NarrativeAssistConfig",
    "ProbabilityBalancer",
    "get_balancer",
    "is_narrative_assist_enabled",
]

if _has_fastest_lap_emu:
    __all__.extend([
        "calculate_base_lap_time",
        "calculate_degradation",
        "calculate_lap_time",
        "simulate_race",
    ])
