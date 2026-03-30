"""
Incident System for F1 Race Simulation.

This module provides comprehensive incident handling including:
- Overtaking incidents and collisions
- Driver errors
- Vehicle faults
- Double-attack scenarios
"""

from .incident_types import (
    IncidentType,
    Incident,
    IncidentSeverity,
)
from .incident_manager import IncidentManager
from .vehicle_fault import (
    TeamStability,
    ComponentFault,
    VehicleFaultResolver,
)
from .driver_error import (
    DriverErrorType,
    DriverError,
    DriverErrorProbability,
    DriverErrorResolver,
)
from .overtake_incident import (
    OvertakeIncidentProbability,
    OvertakeCollision,
)
from .double_attack import (
    DoubleAttackSystem,
    DoubleAttackConfrontation,
)
from .sector_flags import (
    SectorFlag,
    SectorFlagState,
    SectorFlagManager,
    YellowFlagImpact,
)
from .vsc_sc import (
    VSCConfig,
    SafetyCarConfig,
    VSCManager,
    SafetyCarManager,
    SafetyResponseManager,
    SafetyCarState,
)
from .unlapping import (
    UnlappingManager,
    UnlappingState,
    RaceControlDecision,
    LappedCar,
    IncidentResponseUnlappingManager,
    check_f1_article_55_compliance,
)
from .blue_flag import (
    BlueFlagState,
    ResistanceLevel,
    LappingDetectionConfig,
    DriverPersonality,
    BlueFlagComplianceRoller,
    BlueFlagManager,
    LappingPair,
    BlueFlagViolation,
)
from .lapping_overtake import (
    LappingOvertake,
    LappingResult,
    SECTION_SUITABILITY,
)
from .dice_roller import (
    roll_d10,
    roll_d100,
    roll_d6,
    DiceRoller,
)
from .red_flag import (
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
from .rolling_start import (
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
