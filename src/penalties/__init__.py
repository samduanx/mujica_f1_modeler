"""
F1 Penalty System.

Centralized system for managing all race penalties including:
- Time penalties (5s, 10s, 15s)
- Drive-through penalties
- Stop-and-go penalties
- Grid penalties for future races
- Reprimands
- Penalty points tracking (Super Licence)
"""

from src.penalties.penalty_types import (
    PenaltyType,
    Penalty,
    TimeLoss,
)
from src.penalties.penalty_manager import PenaltyManager
from src.penalties.penalty_points import PenaltyPoints
from src.penalties.penalty_service import PenaltyService
from src.penalties.grid_penalty import GridPenaltyTracker
from src.penalties.reprimand import ReprimandTracker

__all__ = [
    "PenaltyType",
    "Penalty",
    "TimeLoss",
    "PenaltyManager",
    "PenaltyPoints",
    "PenaltyService",
    "GridPenaltyTracker",
    "ReprimandTracker",
]
