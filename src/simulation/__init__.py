"""Simulation module for F1 race simulation.

This module contains the long-distance race simulation functionality:
- Race simulation with pit stops
- Strategy modelling
- Position progression analysis
"""

from .long_dist_sim_with_box import (
    simulate_race_with_pit_stops,
    determine_pit_strategy,
    generate_pit_laps,
    main,
)

__all__ = [
    "simulate_race_with_pit_stops",
    "determine_pit_strategy",
    "generate_pit_laps",
    "main",
]
