"""
Driver Skill Types and Data Models.

This module defines the core types for the driver skills system,
including skill triggers, effect types, and the DriverSkill dataclass.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime


class SkillTrigger(Enum):
    """When a skill can activate."""

    # Weather conditions
    WEATHER_RAIN = auto()  # Rain conditions (any intensity)
    WEATHER_HEAVY_RAIN = auto()  # Heavy rain specifically
    WEATHER_DRY = auto()  # Dry conditions

    # Session types
    QUALIFYING_Q1 = auto()  # Q1 specifically
    QUALIFYING_Q2 = auto()  # Q2 specifically
    QUALIFYING_Q3 = auto()  # Q3 specifically
    QUALIFYING_ANY = auto()  # Any qualifying session
    RACE = auto()  # Race session

    # Race situations
    DEFENDING = auto()  # Defending position
    DEFENDING_TRAIN = auto()  # Defending with train forming
    ATTACKING = auto()  # Attacking/overtaking
    IN_DRS_ZONE = auto()  # In DRS zone
    DRS_ZONE_EXTENDED = auto()  # In DRS zone for 3+ laps
    START = auto()  # Race start/launch
    START_LATER_LAPS = auto()  # Start (after improvement)

    # Tire conditions
    TIRE_CLIFF = auto()  # After tire degradation cliff
    TIRE_FRESH = auto()  # With fresh tires

    # Team dynamics
    TEAM_ORDER = auto()  # Team order situation
    TEAM_ORDER_FOLLOW = auto()  # Following team order
    TEAM_ORDER_IGNORE = auto()  # Ignoring team order
    HELPING_TEAMMATE = auto()  # Helping teammate (Bottas helping Zhou)
    BEHIND_TEAMMATE = auto()  # Behind teammate (Sainz behind Leclerc)

    # Special conditions
    EVERY_RACE = auto()  # Applied every race (constant)
    EVERY_RACE_RANDOM = auto()  # Random per race
    VS_SPECIFIC_DRIVER = auto()  # Against specific driver
    CONTROL_LOSS = auto()  # When losing control
    INCIDENT_NEAR = auto()  # When incident ahead

    # Not implemented (awaiting further orders)
    PENDING = auto()  # Skill pending implementation


class SkillEffectType(Enum):
    """Types of skill effects."""

    RATING_BOOST = auto()  # Direct R value boost (+)
    RATING_PENALTY = auto()  # R value penalty (-)
    DICE_MODIFIER = auto()  # Modify dice roll result
    DICE_CHANCE = auto()  # Chance-based activation (percentage)
    EXTRA_DICE_CHECK = auto()  # Requires extra dice roll
    PREVENT_INCIDENT = auto()  # Prevent certain incidents
    CAUSE_INCIDENT = auto()  # Can cause incidents (Latifi)
    TIRE_MODIFIER = auto()  # Modify tire degradation
    DEFENSE_BONUS = auto()  # Specific defense bonus
    ATTACK_BONUS = auto()  # Specific attack bonus


class SkillCategory(Enum):
    """Categories for organizing skills."""

    WEATHER = "weather"
    QUALIFYING = "qualifying"
    DEFENSE = "defense"
    OVERTAKE = "overtake"
    TIRE_MANAGEMENT = "tire_management"
    START = "start"
    TEAM_ORDER = "team_order"
    VEHICLE_CONTROL = "vehicle_control"
    VARIABLE = "variable"
    SPECIAL = "special"


@dataclass
class DiceRequirement:
    """Dice roll requirement for skill activation or check."""

    dice_type: str  # "d6", "d10", "d20", "d100"
    threshold: int  # Roll <= threshold for success
    success_effect: Optional[str] = None  # Effect on success
    failure_effect: Optional[str] = None  # Effect on failure
    modifier: int = 0  # Modifier to dice roll


@dataclass
class DriverSkill:
    """
    Represents a driver skill.

    Attributes:
        name_cn: Chinese skill name (from CSV)
        name_en: English skill name (for code)
        driver: Driver name (English)
        description: Skill description
        category: Skill category
        trigger: When the skill activates
        effect_type: Type of effect
        effect_value: Magnitude of effect (e.g., +0.5 R)
        conditions: Additional conditions (dict)
        dice_requirement: Dice roll requirement (if any)
        applies_to: What the skill applies to ("self", "opponent", "both")
        is_passive: Whether skill is always active when conditions met
        cooldown_laps: Number of laps before skill can reactivate
        max_activations: Maximum times skill can activate per race
    """

    name_cn: str
    name_en: str
    driver: str
    description: str
    category: SkillCategory
    trigger: SkillTrigger
    effect_type: SkillEffectType
    effect_value: float = 0.0
    conditions: Dict[str, Any] = field(default_factory=dict)
    dice_requirement: Optional[DiceRequirement] = None
    applies_to: str = "self"  # "self", "opponent", "both"
    is_passive: bool = True
    cooldown_laps: int = 0
    max_activations: Optional[int] = None

    def __hash__(self):
        return hash((self.name_cn, self.driver))

    def __eq__(self, other):
        if not isinstance(other, DriverSkill):
            return False
        return self.name_cn == other.name_cn and self.driver == other.driver


@dataclass
class ActiveSkillEffect:
    """
    Represents an active skill effect in the current context.

    This is created when a skill's conditions are met and it activates.
    """

    skill: DriverSkill
    activation_time: datetime
    lap: int
    context_description: str
    r_modifier: float = 0.0
    dice_modifier: int = 0
    extra_dice_required: Optional[DiceRequirement] = None
    duration_laps: Optional[int] = None

    def is_expired(self, current_lap: int) -> bool:
        """Check if the effect has expired."""
        if self.duration_laps is None:
            return False
        return current_lap >= self.lap + self.duration_laps


@dataclass
class SkillActivation:
    """Record of a skill activation for logging/reporting."""

    driver: str
    skill_name_cn: str
    skill_name_en: str
    lap: int
    race_time: float
    context: str
    effect_description: str
    r_modifier: float
    dice_result: Optional[int] = None
    dice_threshold: Optional[int] = None
    success: bool = True
    extra_dice_required: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "driver": self.driver,
            "skill_name_cn": self.skill_name_cn,
            "skill_name_en": self.skill_name_en,
            "lap": self.lap,
            "race_time": self.race_time,
            "context": self.context,
            "effect_description": self.effect_description,
            "r_modifier": self.r_modifier,
            "dice_result": self.dice_result,
            "dice_threshold": self.dice_threshold,
            "success": self.success,
            "extra_dice_required": self.extra_dice_required,
        }


# Skill name mappings (Chinese to English)
# This helps with parsing the CSV file
SKILL_NAME_MAPPINGS = {
    # Weather skills
    "老潘课堂": "RainMaster",
    "直感A": "InstinctA",
    # Qualifying skills
    "勒一圈": "LeclercOneLap",
    "刘一圈": "HamiltonOneLap",
    "排位神车": "QualifyingGodCar",
    # Defense skills
    "Smooth Operator": "SmoothOperator",
    "WIDELONSO": "WideAlonso",
    "狮子": "Lion",
    "WIDEZHOU": "WideZhou",
    "画龙高手": "DragonPainter",
    # Overtake skills (awaiting further orders)
    "振金超车": "IndestructibleOvertake",  # PENDING
    "极限哥": "LimitMaster",
    "斗小牛士": "BullFighter",
    "武士道！": "Bushido",
    "我也是舒马赫": "AlsoSchumacher",
    # Tire management
    "保胎大师": "TireSaver",
    # Start skills
    "昏厥起步": "FaintStart",
    # Team order skills (partial pending)
    "团队精神": "TeamSpirit",  # PENDING
    "好大哥": "GoodBigBrother",
    "车手都是自私的": "SelfishDriver",
    # Vehicle control
    "拉力传承": "RallyHeritage",
    "全能老农": "VeteranFarmer",
    "冰人继承人": "IcemanInheritor",  # PENDING
    # Variable/random
    "盲盒车": "BlindBoxCar",
    "嗦球队": "SuckBallTeam",
    "总导演": "ChiefDirector",
    "抽象怪": "Abstract",
    # Other
    "大旗": "BigFlag",
    "车斗术": "CarFighting",
    "（疑似）最强代打": "BestSubstitute",
}


# Drivers awaiting further orders (their skills won't be implemented yet)
# Piastri now implemented - see 抽象怪 skill with Alonso as godfather after Spain
PENDING_DRIVERS = set()  # All drivers now implemented!


def is_skill_pending(driver: str, skill_name_cn: str) -> bool:
    """
    Check if a skill is pending implementation.

    Args:
        driver: Driver name (English)
        skill_name_cn: Skill name in Chinese

    Returns:
        True if skill is pending, False otherwise
    """
    if driver in PENDING_DRIVERS:
        return True
    return False
