"""
Skill Parser Module.

Parses Chinese skill descriptions from data/driver_ratings.csv and converts
them to structured DriverSkill objects.
"""

import re
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

from .skill_types import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillCategory,
    DiceRequirement,
    SKILL_NAME_MAPPINGS,
    is_skill_pending,
)


# Driver name mapping (Chinese to English)
DRIVER_NAME_MAP = {
    "维斯塔潘": "Verstappen",
    "佩雷兹": "Perez",
    "勒克莱尔": "Leclerc",
    "塞恩斯": "Sainz",
    "汉密尔顿": "Hamilton",
    "拉塞尔": "Russell",
    "加斯利": "Gasly",
    "角田裕毅": "Tsunoda",
    "维特尔": "Vettel",
    "斯特罗尔": "Stroll",
    "阿隆索": "Alonso",
    "奥康": "Ocon",
    "博塔斯": "Bottas",
    "周冠宇": "Zhou",
    "诺里斯": "Norris",
    "里卡多": "Ricciardo",
    "马格努森": "Magnussen",
    "米克": "Schumacher",
    "阿尔本": "Albon",
    "拉提菲": "Latifi",
    "霍肯伯格": "Hulkenberg",
    "菲蒂帕尔迪": "Fittipaldi",
    "德弗里斯": "DeVries",
    "皮亚斯特里": "Piastri",
    "施瓦茨曼": "Schwartzman",
    "格罗斯让": "Grosjean",
}

# Skill definitions based on parsing CSV descriptions
# Each skill has a parser function and metadata
SKILL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Weather skills
    "老潘课堂": {
        "name_en": "RainMaster",
        "category": SkillCategory.WEATHER,
        "trigger": SkillTrigger.WEATHER_RAIN,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "R+0.5 in rainy conditions",
        "parser": "parse_rain_boost",
    },
    "直感A": {
        "name_en": "InstinctA",
        "category": SkillCategory.WEATHER,
        "trigger": SkillTrigger.WEATHER_RAIN,  # Also DEFENDING - handled specially
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.3,
        "description": "R+0.3 when defending or in rain",
        "parser": "parse_defense_or_weather",
        "conditions": {"defense_bonus": 0.3, "rain_bonus": 0.3},
    },
    # Qualifying skills
    "勒一圈": {
        "name_en": "LeclercOneLap",
        "category": SkillCategory.QUALIFYING,
        "trigger": SkillTrigger.QUALIFYING_ANY,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "R+0.5 in qualifying (Q3/Q1/Q2 danger only)",
        "parser": "parse_qualifying_with_danger",
        "conditions": {"requires_danger": True},
    },
    "刘一圈": {
        "name_en": "HamiltonOneLap",
        "category": SkillCategory.QUALIFYING,
        "trigger": SkillTrigger.PENDING,  # Still pending
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "[PENDING] R+0.5 in qualifying (Q3/Q1/Q2 danger only)",
        "parser": "parse_qualifying_with_danger",
        "conditions": {"requires_danger": True},
    },
    "排位神车": {
        "name_en": "QualifyingGodCar",
        "category": SkillCategory.QUALIFYING,
        "trigger": SkillTrigger.QUALIFYING_ANY,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.8,
        "description": "R+0.8 in qualifying",
        "parser": "parse_simple_boost",
    },
    # Defense skills
    "Smooth Operator": {
        "name_en": "SmoothOperator",
        "category": SkillCategory.DEFENSE,
        "trigger": SkillTrigger.DEFENDING,
        "effect_type": SkillEffectType.DEFENSE_BONUS,
        "effect_value": 0.3,
        "description": "R+0.3 when defending, additional +0.3 in train",
        "parser": "parse_defense_with_train",
        "conditions": {"base_bonus": 0.3, "train_bonus": 0.3},
    },
    "WIDELONSO": {
        "name_en": "WideAlonso",
        "category": SkillCategory.DEFENSE,
        "trigger": SkillTrigger.DEFENDING,
        "effect_type": SkillEffectType.DEFENSE_BONUS,
        "effect_value": 0.8,
        "description": "R+0.8 when defending, check vehicle damage after 10 consecutive defenses",
        "parser": "parse_defense_with_dice_check",
        "conditions": {"consecutive_defenses_threshold": 10},
    },
    "狮子": {
        "name_en": "Lion",
        "category": SkillCategory.DEFENSE,
        "trigger": SkillTrigger.DEFENDING,
        "effect_type": SkillEffectType.DEFENSE_BONUS,
        "effect_value": 0.5,
        "description": "R+0.5 when defending, ignores team orders",
        "parser": "parse_simple_defense",
    },
    "WIDEZHOU": {
        "name_en": "WideZhou",
        "category": SkillCategory.DEFENSE,
        "trigger": SkillTrigger.DEFENDING,
        "effect_type": SkillEffectType.DEFENSE_BONUS,
        "effect_value": 0.5,
        "description": "R+0.5 when defending",
        "parser": "parse_simple_defense",
    },
    "画龙高手": {
        "name_en": "DragonPainter",
        "category": SkillCategory.DEFENSE,
        "trigger": SkillTrigger.DEFENDING,
        "effect_type": SkillEffectType.DEFENSE_BONUS,
        "effect_value": 0.8,
        "description": "R+0.8 when defending, risk of double line change penalty",
        "parser": "parse_defense_with_dice_check",
        "conditions": {"risk_penalty": True},
    },
    # Overtake skills
    "振金超车": {
        "name_en": "IndestructibleOvertake",
        "category": SkillCategory.OVERTAKE,
        "trigger": SkillTrigger.ATTACKING,
        "effect_type": SkillEffectType.EXTRA_DICE_CHECK,
        "effect_value": 0.5,
        "description": "振金流程: 10% dice for R boost + 10% dice opponent unaware = 1% indestructible overtake. R+0.5, pushes opponent out, self unharmed",
        "parser": "parse_indestructible_overtake",
        "conditions": {
            "r_boost_chance": 0.10,  # 10% for R boost dice
            "unnoticed_chance": 0.10,  # 10% for opponent not noticing
            "total_chance": 0.01,  # 1% total (both must succeed)
            "r_boost_value": 0.5,
            "pushes_opponent_out": True,
            "self_unharmed": True,
        },
    },
    "极限哥": {
        "name_en": "LimitMaster",
        "category": SkillCategory.OVERTAKE,
        "trigger": SkillTrigger.DRS_ZONE_EXTENDED,
        "effect_type": SkillEffectType.EXTRA_DICE_CHECK,
        "effect_value": 0.5,
        "description": "R+0.5 in DRS zone for 3+ laps, Ra10 check for deformation",
        "parser": "parse_drs_with_deformation_check",
        "conditions": {"min_drs_laps": 3, "deformation_check": "Ra10"},
    },
    "斗小牛士": {
        "name_en": "BullFighter",
        "category": SkillCategory.OVERTAKE,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "R+0.5 constant bonus",
        "parser": "parse_simple_boost",
    },
    "武士道！": {
        "name_en": "Bushido",
        "category": SkillCategory.OVERTAKE,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.EXTRA_DICE_CHECK,
        "effect_value": 1.0,
        "description": "R+1 but extra dice for next overtake point mistake",
        "parser": "parse_boost_with_extra_dice",
        "conditions": {"base_bonus": 1.0, "dice_check": "next_overtake"},
    },
    "我也是舒马赫": {
        "name_en": "AlsoSchumacher",
        "category": SkillCategory.OVERTAKE,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.EXTRA_DICE_CHECK,
        "effect_value": 1.0,
        "description": "R+1 but extra dice for next overtake point mistake",
        "parser": "parse_boost_with_extra_dice",
        "conditions": {"base_bonus": 1.0, "dice_check": "next_overtake"},
    },
    # Tire management
    "保胎大师": {
        "name_en": "TireSaver",
        "category": SkillCategory.TIRE_MANAGEMENT,
        "trigger": SkillTrigger.TIRE_CLIFF,
        "effect_type": SkillEffectType.TIRE_MODIFIER,
        "effect_value": -0.3,
        "description": "-0.3 R loss after tire cliff point",
        "parser": "parse_tire_cliff",
    },
    # Start skills
    "昏厥起步": {
        "name_en": "FaintStart",
        "category": SkillCategory.START,
        "trigger": SkillTrigger.START,
        "effect_type": SkillEffectType.RATING_PENALTY,
        "effect_value": -0.5,
        "description": "R-0.5 at start, 10% dice chance (improves over time)",
        "parser": "parse_start_penalty_with_improvement",
        "conditions": {
            "initial_chance": 0.10,
            "improvement_stages": [0.05, 0.02, 0.01],
        },
    },
    # Team order skills (some pending)
    "团队精神": {
        "name_en": "TeamSpirit",
        "category": SkillCategory.TEAM_ORDER,
        "trigger": SkillTrigger.TEAM_ORDER,
        "effect_type": SkillEffectType.DICE_CHANCE,
        "effect_value": 0.8,
        "description": "80% dice chance to obey team orders",
        "parser": "parse_team_order_dice",
        "conditions": {"obey_chance": 0.8},
        "pending": True,  # Pending further orders
    },
    "好大哥": {
        "name_en": "GoodBigBrother",
        "category": SkillCategory.TEAM_ORDER,
        "trigger": SkillTrigger.HELPING_TEAMMATE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 1.0,
        "description": "R+1 when helping Zhou or following team orders",
        "parser": "parse_help_teammate",
        "conditions": {"teammate": "Zhou"},
    },
    "车手都是自私的": {
        "name_en": "SelfishDriver",
        "category": SkillCategory.TEAM_ORDER,
        "trigger": SkillTrigger.BEHIND_TEAMMATE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "R+0.5 when behind Leclerc with direct threat",
        "parser": "parse_behind_teammate",
        "conditions": {"teammate": "Leclerc", "requires_threat": True},
    },
    # Vehicle control
    "拉力传承": {
        "name_en": "RallyHeritage",
        "category": SkillCategory.VEHICLE_CONTROL,
        "trigger": SkillTrigger.CONTROL_LOSS,
        "effect_type": SkillEffectType.DICE_CHANCE,
        "effect_value": 0.9,
        "description": "90% dice chance to recover from loss of control",
        "parser": "parse_recovery_dice",
        "conditions": {"recovery_chance": 0.9},
    },
    "全能老农": {
        "name_en": "VeteranFarmer",
        "category": SkillCategory.VEHICLE_CONTROL,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.8,
        "description": "R+0.8 from car synergy",
        "parser": "parse_simple_boost",
    },
    "冰人继承人": {
        "name_en": "IcemanInheritor",
        "category": SkillCategory.VEHICLE_CONTROL,
        "trigger": SkillTrigger.INCIDENT_NEAR,
        "effect_type": SkillEffectType.PREVENT_INCIDENT,
        "effect_value": 1.0,
        "description": "Immune to racing incidents, no damage when behind accidents",
        "parser": "parse_incident_immunity",
        "pending": True,  # Pending further orders
    },
    # Variable/random skills
    "盲盒车": {
        "name_en": "BlindBoxCar",
        "category": SkillCategory.VARIABLE,
        "trigger": SkillTrigger.EVERY_RACE_RANDOM,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.0,  # Variable: -0.5 to +0.5
        "description": "Random R change per race: -0.5, -0.3, 0, +0.3, +0.5",
        "parser": "parse_random_r_change",
        "conditions": {
            "possible_values": [-0.5, -0.3, 0.0, 0.3, 0.5],
            "cancel_if_car_90_plus": True,
        },
    },
    "嗦球队": {
        "name_en": "SuckBallTeam",
        "category": SkillCategory.SPECIAL,
        "trigger": SkillTrigger.VS_SPECIFIC_DRIVER,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "R+0.5 against Magnussen specifically",
        "parser": "parse_vs_driver",
        "conditions": {"target_driver": "Magnussen"},
    },
    "总导演": {
        "name_en": "ChiefDirector",
        "category": SkillCategory.VARIABLE,
        "trigger": SkillTrigger.EVERY_RACE_RANDOM,
        "effect_type": SkillEffectType.CAUSE_INCIDENT,
        "effect_value": 0.0,
        "description": "Dice chance to cause incidents",
        "parser": "parse_incident_causing",
    },
    "抽象怪": {
        "name_en": "Abstract",
        "category": SkillCategory.SPECIAL,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "After Spain GP, Piastri recognizes Leclerc as godfather. Both get R+0.5 and immunity to incidents/critical failures (not at Australian GP)",
        "parser": "parse_godfather_bonus",
        "conditions": {
            "activation_race": "Spain",  # Skill activates AFTER this race
            "godfather": "Leclerc",  # Selected via random dice rolls (d2=2 from 7 candidates)
            "r_boost": 0.5,
            "applies_to": ["Piastri", "Leclerc"],
            "immunity": ["incidents", "critical_failures"],
            "track_restriction": "NotAustralia",  # Doesn't work at Australian GP
        },
    },
    # Other skills
    "大旗": {
        "name_en": "BigFlag",
        "category": SkillCategory.TEAM_ORDER,
        "trigger": SkillTrigger.TEAM_ORDER,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 0.5,
        "description": "Default team spirit, +0.5 when teammate behind 3+ positions or retired",
        "parser": "parse_team_compensation",
        "conditions": {"position_gap_threshold": 3},
    },
    "车斗术": {
        "name_en": "CarFighting",
        "category": SkillCategory.VEHICLE_CONTROL,
        "trigger": SkillTrigger.ATTACKING,
        "effect_type": SkillEffectType.PREVENT_INCIDENT,
        "effect_value": 1.0,
        "description": "Indestructible car in fights",
        "parser": "parse_indestructible",
    },
    "（疑似）最强代打": {
        "name_en": "BestSubstitute",
        "category": SkillCategory.SPECIAL,
        "trigger": SkillTrigger.EVERY_RACE,
        "effect_type": SkillEffectType.RATING_BOOST,
        "effect_value": 1.0,
        "description": "R+1 as substitute driver",
        "parser": "parse_simple_boost",
    },
}


def parse_skill(
    skill_name_cn: str,
    driver_cn: str,
    description: str = "",
) -> Optional[DriverSkill]:
    """
    Parse a skill from its Chinese name and create a DriverSkill object.

    Args:
        skill_name_cn: Skill name in Chinese (may include description after colon)
        driver_cn: Driver name in Chinese
        description: Raw description from CSV

    Returns:
        DriverSkill object or None if skill not recognized
    """
    if not skill_name_cn or pd.isna(skill_name_cn):
        return None

    skill_name_cn = skill_name_cn.strip()
    driver_en = DRIVER_NAME_MAP.get(driver_cn, driver_cn)

    # Extract skill name from full description (e.g., "老潘课堂：雨天R值+0.5" -> "老潘课堂")
    if "：" in skill_name_cn:
        skill_name_cn = skill_name_cn.split("：")[0].strip()
    elif ":" in skill_name_cn:
        skill_name_cn = skill_name_cn.split(":")[0].strip()

    # Check if this skill is pending for this driver
    if is_skill_pending(driver_en, skill_name_cn):
        return _create_pending_skill(skill_name_cn, driver_en, description)

    # Get skill definition
    definition = SKILL_DEFINITIONS.get(skill_name_cn)
    if not definition:
        # Unknown skill - create generic
        return _create_generic_skill(skill_name_cn, driver_en, description)

    # Create DriverSkill from definition
    return DriverSkill(
        name_cn=skill_name_cn,
        name_en=definition.get("name_en", "Unknown"),
        driver=driver_en,
        description=definition.get("description", description),
        category=definition.get("category", SkillCategory.SPECIAL),
        trigger=definition.get("trigger", SkillTrigger.EVERY_RACE),
        effect_type=definition.get("effect_type", SkillEffectType.RATING_BOOST),
        effect_value=definition.get("effect_value", 0.0),
        conditions=definition.get("conditions", {}),
        dice_requirement=_parse_dice_requirement(definition),
    )


def _create_pending_skill(
    skill_name_cn: str,
    driver_en: str,
    description: str,
) -> DriverSkill:
    """Create a pending skill placeholder."""
    name_en = SKILL_NAME_MAPPINGS.get(skill_name_cn, "PendingSkill")
    return DriverSkill(
        name_cn=skill_name_cn,
        name_en=name_en,
        driver=driver_en,
        description=f"[PENDING] {description}",
        category=SkillCategory.SPECIAL,
        trigger=SkillTrigger.PENDING,
        effect_type=SkillEffectType.RATING_BOOST,
        effect_value=0.0,
        is_passive=True,
    )


def _create_generic_skill(
    skill_name_cn: str,
    driver_en: str,
    description: str,
) -> DriverSkill:
    """Create a generic skill for unknown skill names."""
    return DriverSkill(
        name_cn=skill_name_cn,
        name_en="UnknownSkill",
        driver=driver_en,
        description=description,
        category=SkillCategory.SPECIAL,
        trigger=SkillTrigger.EVERY_RACE,
        effect_type=SkillEffectType.RATING_BOOST,
        effect_value=0.0,
        is_passive=True,
    )


def _parse_dice_requirement(definition: Dict) -> Optional[DiceRequirement]:
    """Parse dice requirement from skill definition."""
    conditions = definition.get("conditions", {})

    # Check for various dice-related conditions
    if "recovery_chance" in conditions:
        return DiceRequirement(
            dice_type="d100",
            threshold=int(conditions["recovery_chance"] * 100),
        )

    if "obey_chance" in conditions:
        return DiceRequirement(
            dice_type="d100",
            threshold=int(conditions["obey_chance"] * 100),
        )

    if "dice_check" in conditions:
        return DiceRequirement(
            dice_type="d10",
            threshold=5,  # Default threshold
        )

    return None


def load_skills_from_csv(
    csv_path: str = "data/driver_ratings.csv",
) -> Dict[str, List[DriverSkill]]:
    """
    Load all driver skills from the ratings CSV file.

    Args:
        csv_path: Path to driver ratings CSV

    Returns:
        Dictionary mapping driver names to lists of skills
    """
    skills_by_driver: Dict[str, List[DriverSkill]] = {}

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        for _, row in df.iterrows():
            driver_cn = row.get("车手", "")
            if pd.isna(driver_cn) or not driver_cn:
                continue

            driver_cn = driver_cn.strip()
            driver_en = DRIVER_NAME_MAP.get(driver_cn, driver_cn)

            # Parse skills
            skills = []
            for skill_col in ["技能1", "技能2"]:
                if skill_col in df.columns and pd.notna(row[skill_col]):
                    skill_name = str(row[skill_col]).strip()
                    if skill_name:
                        skill = parse_skill(skill_name, driver_cn)
                        if skill:
                            skills.append(skill)

            if skills:
                skills_by_driver[driver_en] = skills

    except Exception as e:
        print(f"Error loading skills from CSV: {e}")

    return skills_by_driver


def get_skill_description(skill_name_cn: str) -> str:
    """Get English description for a skill."""
    definition = SKILL_DEFINITIONS.get(skill_name_cn)
    if definition:
        return definition.get("description", "")
    return ""
