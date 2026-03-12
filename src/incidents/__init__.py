"""
Incident System for F1 Race Simulation.

This module provides comprehensive incident handling including:
- Overtaking incidents and collisions
- Driver errors
- Vehicle faults
- Double-attack scenarios
"""

from incidents.incident_types import (
    IncidentType,
    Incident,
    IncidentSeverity,
)
from incidents.incident_manager import IncidentManager
from incidents.vehicle_fault import (
    TeamStability,
    ComponentFault,
    VehicleFaultResolver,
)
from incidents.driver_error import (
    DriverErrorType,
    DriverError,
    DriverErrorProbability,
    DriverErrorResolver,
)
from incidents.overtake_incident import (
    OvertakeIncidentProbability,
    OvertakeCollision,
)
from incidents.double_attack import (
    DoubleAttackSystem,
    DoubleAttackConfrontation,
)
from incidents.sector_flags import (
    SectorFlag,
    SectorFlagState,
    SectorFlagManager,
    YellowFlagImpact,
)
from incidents.vsc_sc import (
    VSCConfig,
    SafetyCarConfig,
    VSCManager,
    SafetyCarManager,
    SafetyResponseManager,
    SafetyCarState,
)
from incidents.unlapping import (
    UnlappingManager,
    UnlappingState,
    RaceControlDecision,
    LappedCar,
    IncidentResponseUnlappingManager,
    check_f1_article_55_compliance,
)
from incidents.blue_flag import (
    BlueFlagState,
    ResistanceLevel,
    LappingDetectionConfig,
    DriverPersonality,
    BlueFlagComplianceRoller,
    BlueFlagManager,
    LappingPair,
    BlueFlagViolation,
)
from incidents.lapping_overtake import (
    LappingOvertake,
    LappingResult,
    SECTION_SUITABILITY,
)
from incidents.dice_roller import (
    roll_d10,
    roll_d100,
    roll_d6,
    DiceRoller,
)
from incidents.red_flag import (
    RaceEndReason,
    RaceCompletionStatus,
    RedFlagOutcome,
    RestartType,
    RedFlagRaceDistanceRules,
    RedFlagTrigger,
    RedFlagManager,
    RedFlagRestart,
    RedFlagRepairManager,
)
from incidents.rolling_start import (
    RollingStartPhase,
    RollingStartConfig,
    RollingStartManager,
    RollingStartTrigger,
    RedFlagRollingRestart,
    RollingStartOvertakingRules,
    DEFAULT_ROLLING_START_CONFIG,
)

__all__ = [
    # Types
    "IncidentType",
    "Incident",
    "IncidentSeverity",
    "DriverErrorType",
    "ComponentFault",
    # Core
    "IncidentManager",
    # Sub-systems
    "TeamStability",
    "VehicleFaultResolver",
    "DriverErrorProbability",
    "DriverErrorResolver",
    "OvertakeIncidentProbability",
    "OvertakeCollision",
    "DoubleAttackSystem",
    "DoubleAttackConfrontation",
    # Sector Flags
    "SectorFlag",
    "SectorFlagState",
    "SectorFlagManager",
    "YellowFlagImpact",
    # VSC/SC
    "VSCConfig",
    "SafetyCarConfig",
    "VSCManager",
    "SafetyCarManager",
    "SafetyResponseManager",
    "SafetyCarState",
    # Unlapping
    "UnlappingManager",
    "UnlappingState",
    "RaceControlDecision",
    "LappedCar",
    "IncidentResponseUnlappingManager",
    "check_f1_article_55_compliance",
    # Blue Flag
    "BlueFlagState",
    "ResistanceLevel",
    "LappingDetectionConfig",
    "DriverPersonality",
    "BlueFlagComplianceRoller",
    "BlueFlagManager",
    "LappingPair",
    "BlueFlagViolation",
    # Lapping Overtake
    "LappingOvertake",
    "LappingResult",
    "SECTION_SUITABILITY",
    # Utilities
    "roll_d10",
    "roll_d100",
    "roll_d6",
    "DiceRoller",
    # Red Flag
    "RaceEndReason",
    "RaceCompletionStatus",
    "RedFlagOutcome",
    "RestartType",
    "RedFlagRaceDistanceRules",
    "RedFlagTrigger",
    "RedFlagManager",
    "RedFlagRestart",
    "RedFlagRepairManager",
    # Rolling Start
    "RollingStartPhase",
    "RollingStartConfig",
    "RollingStartManager",
    "RollingStartTrigger",
    "RedFlagRollingRestart",
    "RollingStartOvertakingRules",
    "DEFAULT_ROLLING_START_CONFIG",
]
