"""
F1 Qualification System

Simulates F1 qualifying sessions (Q1/Q2/Q3 for standard races, SQ1/SQ2/SQ3 for sprint races).
Integrates with existing Strategist, Weather, and Incident systems.
"""

from src.qualifying.types import (
    QualifyingSessionType,
    QualifyingLap,
    QualifyingResult,
    QualifyingResults,
    QualifyingSessionConfig,
    QualifyingSessionState,
    QualifyingIncident,
    TyreAllocation,
    QualifyingWeatherState,
    FlagState,
)

from src.qualifying.tyre_allocation import TyreAllocationManager
from src.qualifying.session import QualifyingSessionManager
from src.qualifying.incident_handler import QualifyingIncidentHandler
from src.qualifying.weather_handler import QualifyingWeatherHandler

__all__ = [
    # Types
    "QualifyingSessionType",
    "QualifyingLap",
    "QualifyingResult",
    "QualifyingResults",
    "QualifyingSessionConfig",
    "QualifyingSessionState",
    "QualifyingIncident",
    "TyreAllocation",
    "QualifyingWeatherState",
    "FlagState",
    # Managers
    "TyreAllocationManager",
    "QualifyingSessionManager",
    "QualifyingIncidentHandler",
    "QualifyingWeatherHandler",
]
