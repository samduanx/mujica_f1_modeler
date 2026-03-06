"""
F1 Sprint Race Simulation Module.

This module provides sprint race simulation capabilities for the 2022 sprint race
tracks: Imola, Austria, and Sao Paulo (Brazil).

Sprint races are 100km short races that determine the starting grid for the main Grand Prix.
"""

from sprint.sprint_simulator import SprintRaceSimulator, run_sprint_race
from sprint.starting_grid_connector import StartingGridConnector, GridSourceType

__all__ = [
    "SprintRaceSimulator",
    "run_sprint_race",
    "StartingGridConnector",
    "GridSourceType",
]
