"""
F1 Free Practice System

Simulates F1 practice sessions (FP1, FP2, FP3) with setup tuning dice mechanics
and parc fermé management according to 2022 FIA Sporting Regulations.

Key Features:
- Setup tuning dice rolling (5 categories × 1d6)
- Parc fermé state management (normal and 2022 sprint weekends)
- Lap time simulation with run types (long runs, quali sims)
- R rating export for qualifying and race integration

Example Usage:
    from src.practice import PracticeWeekendSimulator, WeekendType

    # Run a normal weekend
    simulator = PracticeWeekendSimulator(
        track="Monaco",
        track_base_time=72.5,
        weekend_type=WeekendType.NORMAL,
        drivers=["Verstappen", "Leclerc", "Hamilton"],
        driver_ratings={"Verstappen": 100.5, "Leclerc": 99.8, "Hamilton": 99.5},
    )
    results = simulator.run_all_sessions()

    # Export R ratings for qualifying
    r_ratings = simulator.get_all_final_r_ratings()

    # Generate report
    simulator.print_full_report()
"""

# Core types
from .types import (
    PracticeSessionType,
    WeekendType,
    RunType,
    SetupCategory,
    PracticeLap,
    SetupTuningResult,
    PracticeSessionResult,
    PracticeIncident,
    ParcFermeState,
    WeekendResults,
    RRatingExport,
    PracticeReport,
)

# Setup tuning
from .setup_tuning import (
    SetupDiceRoller,
    SetupEffectCalculator,
    SetupTuningManager,
    DICE_MODIFIER_MAP,
)

# Parc fermé
from .parc_ferme import (
    ParcFermeManager,
    ParcFermeCoordinator,
)

# Lap simulation
from .lap_simulator import (
    PracticeLapSimulator,
    LapTimeFactors,
)

# Session management
from .session import (
    PracticeSessionManager,
    DriverSessionState,
)

# Weekend simulation
from .weekend_simulator import (
    PracticeWeekendSimulator,
    RRatingConnector,
)

__version__ = "1.0.0"

__all__ = [
    # Types
    "PracticeSessionType",
    "WeekendType",
    "RunType",
    "SetupCategory",
    "PracticeLap",
    "SetupTuningResult",
    "PracticeSessionResult",
    "PracticeIncident",
    "ParcFermeState",
    "WeekendResults",
    "RRatingExport",
    "PracticeReport",
    # Setup tuning
    "SetupDiceRoller",
    "SetupEffectCalculator",
    "SetupTuningManager",
    "DICE_MODIFIER_MAP",
    # Parc fermé
    "ParcFermeManager",
    "ParcFermeCoordinator",
    # Lap simulation
    "PracticeLapSimulator",
    "LapTimeFactors",
    # Session management
    "PracticeSessionManager",
    "DriverSessionState",
    # Weekend simulation
    "PracticeWeekendSimulator",
    "RRatingConnector",
]
