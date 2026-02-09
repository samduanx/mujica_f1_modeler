"""Core module for F1 lap time modelling.

This module contains the basic lap modelling functionality:
- Fastest lap emulation
- Lap time calculations
- R-value and performance metrics
"""

from .fastest_lap_emu import (
    load_driver_data,
    calculate_base_lap_time,
    calculate_degradation,
    calculate_lap_time,
    simulate_race,
)

__all__ = [
    "load_driver_data",
    "calculate_base_lap_time",
    "calculate_degradation",
    "calculate_lap_time",
    "simulate_race",
]
