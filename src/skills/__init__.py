"""
Driver Skills System for F1 Simulation.

This module provides a comprehensive skills system for F1 drivers based on
data/driver_ratings.csv. Each driver has 1-2 unique skills that modify their
R rating under specific conditions.

Basic Usage:
    from src.skills import get_skill_manager, SkillContext

    # Get the skill manager
    skill_mgr = get_skill_manager()

    # Create context for skill check
    context = SkillContext(
        session_type=SessionType.RACE,
        lap_number=10,
        is_defending=True,
        weather_condition=WeatherCondition.LIGHT_RAIN,
    )

    # Get adjusted R value
    adjusted_r, modifier, activations = skill_mgr.get_adjusted_r_value(
        driver="Verstappen",
        base_r=100.5,
        context=context,
    )
"""

from .skill_types import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillCategory,
    DiceRequirement,
    ActiveSkillEffect,
    SkillActivation,
    SKILL_NAME_MAPPINGS,
    is_skill_pending,
    PENDING_DRIVERS,
)

from .skill_context import (
    SkillContext,
    SessionType,
    WeatherCondition,
    TrackCondition,
)

from .skill_effects import (
    SkillEffectResult,
    SkillEffectCalculator,
)

from .skill_parser import (
    parse_skill,
    load_skills_from_csv,
    DRIVER_NAME_MAP,
    SKILL_DEFINITIONS,
)

from .driver_skill_manager import (
    DriverSkillManager,
    get_skill_manager,
    reset_skill_manager,
)

__all__ = [
    # Types
    "DriverSkill",
    "SkillTrigger",
    "SkillEffectType",
    "SkillCategory",
    "DiceRequirement",
    "ActiveSkillEffect",
    "SkillActivation",
    # Context
    "SkillContext",
    "SessionType",
    "WeatherCondition",
    "TrackCondition",
    # Effects
    "SkillEffectResult",
    "SkillEffectCalculator",
    # Parser
    "parse_skill",
    "load_skills_from_csv",
    "DRIVER_NAME_MAP",
    "SKILL_DEFINITIONS",
    "SKILL_NAME_MAPPINGS",
    # Manager
    "DriverSkillManager",
    "get_skill_manager",
    "reset_skill_manager",
    "is_skill_pending",
    "PENDING_DRIVERS",
]

__version__ = "1.0.0"
