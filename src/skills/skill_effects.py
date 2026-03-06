"""
Skill Effects Module.

Defines how each skill type affects the simulation and applies skill effects
to various game systems (lap times, overtakes, starts, etc.).
"""

import random
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass

from .skill_types import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillCategory,
    ActiveSkillEffect,
    SkillActivation,
)
from .skill_context import SkillContext, SessionType, WeatherCondition


@dataclass
class SkillEffectResult:
    """Result of applying a skill effect."""

    r_modifier: float = 0.0
    dice_modifier: int = 0
    extra_dice_required: Optional[Dict] = None
    activation_record: Optional[SkillActivation] = None
    should_activate: bool = False
    message: str = ""


class SkillEffectCalculator:
    """
        Calculates the effects of skills based on context.

        This class determines if skills should activate and what effects
    they should have given the current race context.
    """

    def __init__(self):
        self.activation_history: Dict[str, List[SkillActivation]] = {}
        self.consecutive_defenses: Dict[str, int] = {}
        self.start_improvement: Dict[str, int] = {}  # Tracks start skill improvement
        self.blind_box_rolls: Dict[str, float] = {}  # Stores Norris/Ricardo rolls

    def check_skill_activation(
        self,
        skill: DriverSkill,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> SkillEffectResult:
        """
        Check if a skill should activate and calculate its effect.

        Args:
            skill: The skill to check
            context: Current race context
            race_time: Current race time in seconds

        Returns:
            SkillEffectResult with modifiers and activation info
        """
        # Check if trigger condition is met
        if not self._check_trigger(skill.trigger, context):
            return SkillEffectResult(should_activate=False)

        # Handle pending skills
        if skill.trigger.name == "PENDING":
            return SkillEffectResult(should_activate=False)

        # Calculate effect based on skill type
        result = self._calculate_effect(skill, context)

        if result.should_activate:
            # Record activation
            activation = SkillActivation(
                driver=skill.driver,
                skill_name_cn=skill.name_cn,
                skill_name_en=skill.name_en,
                lap=context.lap_number,
                race_time=race_time,
                context=self._describe_context(context),
                effect_description=result.message,
                r_modifier=result.r_modifier,
                dice_result=result.extra_dice_required.get("result")
                if result.extra_dice_required
                else None,
                dice_threshold=result.extra_dice_required.get("threshold")
                if result.extra_dice_required
                else None,
                success=True,
                extra_dice_required=result.extra_dice_required,
            )
            result.activation_record = activation

            # Store in history
            if skill.driver not in self.activation_history:
                self.activation_history[skill.driver] = []
            self.activation_history[skill.driver].append(activation)

        return result

    def _check_trigger(self, trigger: SkillTrigger, context: Optional[SkillContext]) -> bool:
        """Check if a trigger condition is met."""
        # Guard against None context
        if context is None:
            return False

        # Weather triggers
        if trigger == SkillTrigger.WEATHER_RAIN:
            return context.is_raining()

        if trigger == SkillTrigger.WEATHER_HEAVY_RAIN:
            return context.is_heavy_rain()

        if trigger == SkillTrigger.WEATHER_DRY:
            return context.weather_condition == WeatherCondition.DRY

        # Session triggers
        if trigger == SkillTrigger.QUALIFYING_ANY:
            return context.is_qualifying()

        if trigger == SkillTrigger.QUALIFYING_Q1:
            return context.session_type == SessionType.QUALIFYING_Q1

        if trigger == SkillTrigger.QUALIFYING_Q2:
            return context.session_type == SessionType.QUALIFYING_Q2

        if trigger == SkillTrigger.QUALIFYING_Q3:
            return context.session_type == SessionType.QUALIFYING_Q3

        if trigger == SkillTrigger.RACE:
            return context.session_type == SessionType.RACE

        # Race situation triggers
        if trigger == SkillTrigger.DEFENDING:
            return bool(context.is_defending)

        if trigger == SkillTrigger.DEFENDING_TRAIN:
            return bool(context.is_defending) and bool(context.is_forming_train)

        if trigger == SkillTrigger.ATTACKING:
            return bool(context.is_attacking)

        if trigger == SkillTrigger.IN_DRS_ZONE:
            return bool(context.is_in_drs_zone)

        if trigger == SkillTrigger.DRS_ZONE_EXTENDED:
            return bool(context.is_in_drs_zone) and context.drs_zone_consecutive_laps >= 3

        if trigger == SkillTrigger.START:
            return bool(context.is_race_start) or bool(context.is_first_lap)

        # Tire triggers
        if trigger == SkillTrigger.TIRE_CLIFF:
            return bool(context.is_past_tire_cliff)

        if trigger == SkillTrigger.TIRE_FRESH:
            return bool(context.has_fresh_tires)

        # Team order triggers
        if trigger == SkillTrigger.TEAM_ORDER:
            return bool(context.team_order_issued)

        if trigger == SkillTrigger.TEAM_ORDER_FOLLOW:
            return bool(context.team_order_issued) and not bool(context.is_defending)

        if trigger == SkillTrigger.HELPING_TEAMMATE:
            return bool(context.team_order_to_defend) or (
                context.teammate_name
                and bool(context.team_order_issued)
                and context.teammate_gap is not None
                and context.teammate_gap > 0
            )

        if trigger == SkillTrigger.BEHIND_TEAMMATE:
            return context.is_behind_teammate and context.teammate_has_direct_threat

        # Special triggers
        if trigger == SkillTrigger.EVERY_RACE:
            return True

        if trigger == SkillTrigger.EVERY_RACE_RANDOM:
            return True

        if trigger == SkillTrigger.VS_SPECIFIC_DRIVER:
            return context.opponent_is_specific_target

        if trigger == SkillTrigger.CONTROL_LOSS:
            return context.is_losing_control

        if trigger == SkillTrigger.INCIDENT_NEAR:
            return context.incident_ahead

        return False

    def _calculate_effect(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Calculate the effect of a skill."""

        # Handle special skill categories
        if skill.category == SkillCategory.WEATHER:
            return self._handle_weather_skill(skill, context)

        if skill.category == SkillCategory.QUALIFYING:
            return self._handle_qualifying_skill(skill, context)

        if skill.category == SkillCategory.DEFENSE:
            return self._handle_defense_skill(skill, context)

        if skill.category == SkillCategory.OVERTAKE:
            return self._handle_overtake_skill(skill, context)

        if skill.category == SkillCategory.TIRE_MANAGEMENT:
            return self._handle_tire_skill(skill, context)

        if skill.category == SkillCategory.START:
            return self._handle_start_skill(skill, context)

        if skill.category == SkillCategory.TEAM_ORDER:
            return self._handle_team_order_skill(skill, context)

        if skill.category == SkillCategory.VEHICLE_CONTROL:
            return self._handle_vehicle_control_skill(skill, context)

        if skill.category == SkillCategory.VARIABLE:
            return self._handle_variable_skill(skill, context)

        if skill.category == SkillCategory.SPECIAL:
            return self._handle_special_skill(skill, context)

        # Default: simple rating boost
        return SkillEffectResult(
            should_activate=True,
            r_modifier=skill.effect_value,
            message=f"{skill.name_cn}: R{skill.effect_value:+.1f}",
        )

    def _handle_weather_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle weather-related skills."""

        # 直感A - Stroll's defense OR rain skill
        if skill.name_cn == "直感A":
            if context.is_defending or context.is_raining():
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"直感A activates: R+0.3 ({'defending' if context.is_defending else 'rain'})",
                )

        # 老潘课堂 - Verstappen's rain skill
        if skill.name_cn == "老潘课堂":
            return SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"老潘课堂 activates: R+0.5 in rain",
            )

        return SkillEffectResult(should_activate=False)

    def _handle_qualifying_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle qualifying skills."""

        conditions = skill.conditions

        # Check for danger requirement (勒一圈, 刘一圈)
        if conditions.get("requires_danger"):
            if not context.is_in_danger():
                return SkillEffectResult(should_activate=False)

        # Check for Q3 specifically if needed
        if skill.trigger == SkillTrigger.QUALIFYING_Q3:
            if context.session_type != SessionType.QUALIFYING_Q3:
                return SkillEffectResult(should_activate=False)

        return SkillEffectResult(
            should_activate=True,
            r_modifier=skill.effect_value,
            message=f"{skill.name_cn} activates: R+{skill.effect_value} in {context.get_qualifying_stage()}",
        )

    def _handle_defense_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle defense skills."""

        if not context.is_defending:
            return SkillEffectResult(should_activate=False)

        # Smooth Operator - base + train bonus
        if skill.name_cn == "Smooth Operator":
            base_bonus = skill.conditions.get("base_bonus", 0.3)
            train_bonus = (
                skill.conditions.get("train_bonus", 0.3)
                if context.is_forming_train
                else 0
            )
            total = base_bonus + train_bonus

            return SkillEffectResult(
                should_activate=True,
                r_modifier=total,
                message=f"Smooth Operator: R+{total:.1f} ({'with train' if context.is_forming_train else 'defending'})",
            )

        # WIDELONSO - track consecutive defenses
        if skill.name_cn == "WIDELONSO":
            driver = skill.driver
            if driver not in self.consecutive_defenses:
                self.consecutive_defenses[driver] = 0
            self.consecutive_defenses[driver] += 1

            threshold = skill.conditions.get("consecutive_defenses_threshold", 10)
            consecutive = self.consecutive_defenses[driver]

            message = f"WIDELONSO: R+0.8 (defense #{consecutive})"

            # Check for damage after threshold
            if consecutive >= threshold:
                message += " - Vehicle damage check required!"

            return SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=message,
            )

        # 画龙高手 - defense with penalty risk
        if skill.name_cn == "画龙高手":
            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message="画龙高手: R+0.8 defending",
            )

            if skill.conditions.get("risk_penalty"):
                # Add extra dice check for penalty
                result.extra_dice_required = {
                    "type": "penalty_check",
                    "dice_type": "d10",
                    "threshold": 2,  # 20% chance
                    "failure_result": "double_line_change_penalty",
                }

            return result

        # Simple defense skills (狮子, WIDEZHOU)
        return SkillEffectResult(
            should_activate=True,
            r_modifier=skill.effect_value,
            message=f"{skill.name_cn}: R+{skill.effect_value} defending",
        )

    def _handle_overtake_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle overtake/attack skills."""

        # 振金超车 - Indestructible Overtake (Hamilton, Russell, Grosjean)
        if skill.name_cn == "振金超车":
            conditions = skill.conditions
            r_boost_chance = conditions.get("r_boost_chance", 0.10)
            unnoticed_chance = conditions.get("unnoticed_chance", 0.10)
            r_boost_value = conditions.get("r_boost_value", 0.5)

            # Roll for R boost (d10, 10% = roll 1)
            r_boost_roll = random.randint(1, 10)
            r_boost_success = r_boost_roll == 1

            # Roll for opponent not noticing (d10, 10% = roll 1)
            unnoticed_roll = random.randint(1, 10)
            unnoticed_success = unnoticed_roll == 1

            # Both must succeed for indestructible overtake (1% total)
            indestructible_active = r_boost_success and unnoticed_success

            if indestructible_active:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_boost_value,
                    message=f"振金超车 ACTIVATED! R+{r_boost_value} (rolls: {r_boost_roll}, {unnoticed_roll}) - Opponent pushed out, self unharmed!",
                    extra_dice_required={
                        "type": "indestructible_overtake",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "r_boost_success": r_boost_success,
                        "unnoticed_success": unnoticed_success,
                        "pushes_opponent_out": True,
                        "self_unharmed": True,
                    },
                )
            elif r_boost_success:
                # Only R boost succeeded
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_boost_value,
                    message=f"振金超车 partial: R+{r_boost_value} (r_boost roll: {r_boost_roll}, unnoticed roll: {unnoticed_roll})",
                    extra_dice_required={
                        "type": "indestructible_overtake_partial",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "r_boost_success": True,
                        "unnoticed_success": False,
                    },
                )
            else:
                # Neither succeeded - skill didn't activate
                return SkillEffectResult(
                    should_activate=False,
                    message=f"振金超车 failed (rolls: {r_boost_roll}, {unnoticed_roll})",
                )

        # 极限哥 - Leclerc's DRS skill
        if skill.name_cn == "极限哥":
            min_laps = skill.conditions.get("min_drs_laps", 3)

            if context.drs_zone_consecutive_laps >= min_laps:
                # Check for deformation (configurable threshold, defaults to 10)
                deformation_roll = random.randint(1, 10)
                deformation_threshold = skill.conditions.get(
                    "deformation_threshold", 10
                )

                success = deformation_roll <= deformation_threshold
                r_mod = skill.effect_value if success else -0.5

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_mod,
                    message=f"极限哥: {'R+0.5' if success else 'R-0.5 (deformation)'} (Ra{deformation_threshold} roll: {deformation_roll})",
                    extra_dice_required={
                        "type": "deformation_check",
                        "result": deformation_roll,
                        "threshold": deformation_threshold,
                    },
                )
            return SkillEffectResult(should_activate=False)

        # 武士道！, 我也是舒马赫 - Boost with extra dice check
        if skill.name_cn in ["武士道！", "我也是舒马赫"]:
            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"{skill.name_cn}: R+{skill.effect_value}",
            )

            # Add extra dice check for next overtake point
            result.extra_dice_required = {
                "type": "overtake_mistake_check",
                "dice_type": "d10",
                "threshold": 3,  # 30% chance of mistake
                "failure_result": "overtake_mistake",
            }

            return result

        # Simple constant boost (斗小牛士)
        return SkillEffectResult(
            should_activate=True,
            r_modifier=skill.effect_value,
            message=f"{skill.name_cn}: R+{skill.effect_value}",
        )

    def _handle_tire_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle tire management skills."""

        # 保胎大师 - Reduced R loss after cliff
        if context.is_past_tire_cliff:
            return SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,  # Negative value reduces loss
                message=f"保胎大师: {skill.effect_value:+.1f} R loss after cliff",
            )

        return SkillEffectResult(should_activate=False)

    def _handle_start_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle start/launch skills."""

        if not (context.is_race_start or context.is_first_lap):
            return SkillEffectResult(should_activate=False)

        driver = skill.driver

        # 昏厥起步 - Start penalty with improvement over time
        if skill.name_cn == "昏厥起步":
            conditions = skill.conditions

            # Get improvement stage (0 = initial, 1 = improved, etc.)
            improvement_stage = self.start_improvement.get(driver, 0)

            # Get chance based on improvement
            chances = conditions.get("improvement_stages", [0.05, 0.02, 0.01])
            initial_chance = conditions.get("initial_chance", 0.10)

            if improvement_stage == 0:
                current_chance = initial_chance
            elif improvement_stage <= len(chances):
                current_chance = chances[improvement_stage - 1]
            else:
                current_chance = chances[-1] if chances else 0.01

            # Roll for penalty activation
            roll = random.random()
            penalty_active = roll < current_chance

            if penalty_active:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,  # Negative
                    message=f"昏厥起步: R{skill.effect_value:+.1f} (rolled {roll:.2%} < {current_chance:.2%})",
                )
            else:
                # Improvement occurred - advance stage for next race
                self.start_improvement[driver] = improvement_stage + 1
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"昏厥起步 avoided (stage {improvement_stage + 1})",
                )

        return SkillEffectResult(should_activate=False)

    def _handle_team_order_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle team order skills."""

        # 好大哥 - Bottas helping Zhou
        if skill.name_cn == "好大哥":
            teammate = skill.conditions.get("teammate", "Zhou")

            if (
                context.teammate_name == teammate
                or context.team_order_issued
                or context.team_order_to_defend
            ):
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"好大哥: R+{skill.effect_value} helping {teammate}",
                )

        # 车手都是自私的 - Sainz behind Leclerc
        if skill.name_cn == "车手都是自私的":
            teammate = skill.conditions.get("teammate", "Leclerc")

            if (
                context.is_behind_teammate
                and context.teammate_has_direct_threat
                and context.teammate_name == teammate
            ):
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"车手都是自私的: R+{skill.effect_value} behind {teammate} with threat",
                )

        # 大旗 - Grosjean team compensation
        if skill.name_cn == "大旗":
            threshold = skill.conditions.get("position_gap_threshold", 3)

            if context.teammate_gap and context.teammate_gap > threshold:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"大旗: R+{skill.effect_value} compensating for teammate",
                )

        return SkillEffectResult(should_activate=False)

    def _handle_vehicle_control_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle vehicle control skills."""

        # 拉力传承 - Recovery from control loss
        if skill.name_cn == "拉力传承":
            if context.is_losing_control:
                recovery_chance = skill.conditions.get("recovery_chance", 0.9)
                roll = random.random()
                success = roll < recovery_chance

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"拉力传承: Recovery {'success' if success else 'failed'} ({roll:.1%})",
                    extra_dice_required={
                        "type": "recovery_check",
                        "result": int(roll * 100),
                        "threshold": int(recovery_chance * 100),
                    },
                )

        # 全能老农 - Constant car synergy
        if skill.name_cn == "全能老农":
            return SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"全能老农: R+{skill.effect_value} car synergy",
            )

        return SkillEffectResult(should_activate=False)

    def _handle_variable_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle variable/random skills."""

        # 盲盒车 - Norris/Ricciardo random R
        if skill.name_cn == "盲盒车":
            driver = skill.driver

            # Roll once per race (store result)
            if driver not in self.blind_box_rolls:
                possible = skill.conditions.get(
                    "possible_values", [-0.5, -0.3, 0.0, 0.3, 0.5]
                )
                self.blind_box_rolls[driver] = random.choice(possible)

            roll_value = self.blind_box_rolls[driver]

            # Check if cancelled (car metrics > 90)
            if skill.conditions.get("cancel_if_car_90_plus"):
                # This would need car data passed in context
                # For now, assume not cancelled
                pass

            return SkillEffectResult(
                should_activate=True,
                r_modifier=roll_value,
                message=f"盲盒车: R{roll_value:+.1f} this race",
            )

        # 总导演 - Latifi incident causing
        if skill.name_cn == "总导演":
            # Roll for incident
            roll = random.randint(1, 10)
            if roll <= 2:  # 20% chance per race
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"总导演: Incident triggered! (roll: {roll})",
                    extra_dice_required={
                        "type": "incident_caused",
                        "dice_type": "d10",
                        "result": roll,
                        "threshold": 2,
                    },
                )

        return SkillEffectResult(should_activate=False)

    def _handle_special_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle special/miscellaneous skills."""

        # 嗦球队 - Hulkenberg vs Magnussen
        if skill.name_cn == "嗦球队":
            target = skill.conditions.get("target_driver", "Magnussen")

            if context.opponent_name == target or context.is_vs_driver(target):
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"嗦球队: R+{skill.effect_value} vs {target}!",
                )

        # 抽象怪 - Piastri's godfather skill (Leclerc selected after Spain)
        if skill.name_cn == "抽象怪":
            conditions = skill.conditions
            godfather = conditions.get("godfather", "Leclerc")
            r_boost = conditions.get("r_boost", 0.5)
            track_restriction = conditions.get("track_restriction", "NotAustralia")

            # Check if track is Australian GP (skill doesn't work there)
            # For now, assume always active except at Australia
            is_australia = (
                "australia" in context.extra_data.get("track_name", "").lower()
            )
            if is_australia:
                return SkillEffectResult(
                    should_activate=False,
                    message="抽象怪: Not active at Australian GP (Piastri's actual home)",
                )

            # Check if driver is Piastri or the godfather
            is_piastri = skill.driver == "Piastri"
            is_godfather = skill.driver == godfather

            if is_piastri or is_godfather:
                other_driver = godfather if is_piastri else "Piastri"
                relationship = "father" if is_godfather else "son"

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_boost,
                    message=f"抽象怪 ({relationship}): R+{r_boost} with {other_driver} (incident immunity)",
                    extra_dice_required={
                        "type": "godfather_bonus",
                        "godfather": godfather,
                        "piastri": "Piastri",
                        "relationship": relationship,
                        "immunity": ["incidents", "critical_failures"],
                    },
                )

        # （疑似）最强代打 - De Vries substitute bonus
        if skill.name_cn == "（疑似）最强代打":
            return SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"最强代打: R+{skill.effect_value} as substitute",
            )

        return SkillEffectResult(should_activate=False)

    def _describe_context(self, context: SkillContext) -> str:
        """Create a string description of the current context."""
        parts = []

        if context.is_qualifying():
            parts.append(f"{context.get_qualifying_stage()}")
        else:
            parts.append(f"Lap {context.lap_number}")

        if context.is_raining():
            parts.append("rain")

        if context.is_defending:
            parts.append("defending")

        if context.is_attacking:
            parts.append("attacking")

        return ", ".join(parts) if parts else "race"

    def reset_race_state(self):
        """Reset per-race state (call at start of each race)."""
        self.activation_history.clear()
        self.consecutive_defenses.clear()
        self.blind_box_rolls.clear()
        # Note: start_improvement persists across races (driver development)
