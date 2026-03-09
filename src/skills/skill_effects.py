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
        # Track activation counts and cooldowns per skill
        self.skill_activation_counts: Dict[str, int] = {}  # key: "driver|skill_name_cn"
        self.skill_last_activation_lap: Dict[
            str, int
        ] = {}  # key: "driver|skill_name_cn"
        # Track skills activated this lap to prevent multiple activations in same lap
        self.activated_this_lap: Dict[
            int, set
        ] = {}  # key: lap_number, value: set of skill_keys
        # Track weather-based skills state (e.g., 老潘课堂)
        self.weather_skill_activated: Dict[
            str, bool
        ] = {}  # key: "driver|skill_name_cn"
        # Track consecutive DRS laps for 极限哥's Ra upgrade
        self.drs_consecutive_laps: Dict[str, int] = {}  # key: driver
        # Track consecutive defense success for WIDELONSO
        self.consecutive_defense_success: Dict[str, int] = {}  # key: driver
        # Track overtake mode activations (for per-OT-mode skills)
        self.ot_mode_activations: Dict[
            str, int
        ] = {}  # key: "driver|skill_name_cn|ot_session_id"
        # Track current overtake session ID
        self.current_ot_session: Dict[str, int] = {}  # key: driver
        # Track vehicle damage from WIDELONSO
        self.widelonso_damage: Dict[str, float] = {}  # key: driver
        # Track 总导演 incident caused state
        self.chief_director_incident_caused: Dict[str, bool] = {}  # key: driver
        # Track 总导演 incident lap (when the incident will happen)
        self.chief_director_incident_lap: Dict[str, int] = {}  # key: driver
        # Track 抽象怪 godfather selection
        self.abstract_godfather_selected: Dict[str, bool] = {}  # key: driver
        self.abstract_godfather: Dict[
            str, str
        ] = {}  # key: driver, value: godfather name
        # Track driver_error integration for 拉力传承
        self.rally_heritage_dice_result: Dict[str, Optional[int]] = {}  # key: driver
        # Track 振金超车 crash dice results
        self.indestructible_crash_roll: Dict[str, Optional[int]] = {}  # key: driver
        # Track if car metrics > 90 for 盲盒车 cancellation
        self.blind_box_cancelled: Dict[str, bool] = {}  # key: driver
        # Track 最强代打 roll value (1d10 * 0.1)
        self.best_substitute_roll: Dict[str, float] = {}  # key: driver
        # Track 极限哥 deformation check state
        self.limit_master_drs_start_lap: Dict[str, int] = {}  # key: driver
        self.limit_master_in_drs_count: Dict[str, int] = {}  # key: driver
        # Track 武士道 mistake dice
        self.bushido_mistake_roll: Dict[str, Optional[int]] = {}  # key: driver
        # Track 我也是舒马赫 mistake dice
        self.schumacher_mistake_roll: Dict[str, Optional[int]] = {}  # key: driver
        # Track 盲盒车 car metrics check
        self.blind_box_car_metrics_checked: Dict[str, bool] = {}  # key: driver
        # Track 昏厥起步 initial roll (for 1d100 range)
        self.faint_start_roll: Dict[str, int] = {}  # key: driver
        # Track 皮亚斯特里 冰人继承人 incident immunity
        self.iceman_incident_immunity: Dict[str, bool] = {}  # key: driver
        # Track 画龙高手 double line change penalty state
        self.dragon_painter_penalty_active: Dict[str, bool] = {}  # key: driver
        # Track 车手都是自私的 activation (max 1)
        self.selfish_driver_activated: Dict[str, bool] = {}  # key: driver
        # Track 嗦球队 activation (max 1)
        self.suck_ball_activated: Dict[str, bool] = {}  # key: driver
        # Track 狮子 activation (max 1)
        self.lion_activated: Dict[str, bool] = {}  # key: driver
        # Track 直感A activation per OT mode
        self.instinct_a_ot_session: Dict[str, int] = {}  # key: driver
        # Track 车手Error概率 (for 米克/马格努森)
        self.driver_error_multiplier: Dict[str, float] = {}  # key: driver
        # Track 塞恩斯 specific opponent (Leclerc) detection
        self.sainz_vs_leclerc_active: Dict[str, bool] = {}  # key: driver
        # Track 好大哥 activation (max 1)
        self.big_brother_activated: Dict[str, bool] = {}  # key: driver
        # Track WIDEZHOU activation (max 1)
        self.widezhou_activated: Dict[str, bool] = {}  # key: driver
        # Track Smooth Operator activation (max 1)
        self.smooth_operator_activated: Dict[str, bool] = {}  # key: driver
        # Track 画龙高手 activation (max 1)
        self.dragon_painter_activated: Dict[str, bool] = {}  # key: driver
        # Track 昏厥起步 improvement stage (0=initial, 1=improved, 2=final)
        self.faint_start_stage: Dict[str, int] = {}  # key: driver
        # Track 保胎大师 activation per stint
        self.tire_saver_activated: Dict[
            str, str
        ] = {}  # key: driver, value: "stint_number"

    def _get_skill_key(self, skill: DriverSkill) -> str:
        """Generate unique key for tracking skill activations."""
        return f"{skill.driver}|{skill.name_cn}"

    def _check_activation_limits(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if skill can activate based on max_activations and cooldown_laps.

        Returns:
            Tuple of (can_activate, reason_if_blocked)
        """
        skill_key = self._get_skill_key(skill)

        # Check if already activated this lap (prevent multiple activations in same lap)
        lap_activations = self.activated_this_lap.get(context.lap_number, set())
        if skill_key in lap_activations:
            return False, "already activated this lap"

        # Check max_activations
        if skill.max_activations is not None:
            current_count = self.skill_activation_counts.get(skill_key, 0)
            if current_count >= skill.max_activations:
                return (
                    False,
                    f"max_activations reached ({current_count}/{skill.max_activations})",
                )

        # Check cooldown_laps
        if skill.cooldown_laps > 0:
            last_activation_lap = self.skill_last_activation_lap.get(skill_key)
            if last_activation_lap is not None:
                laps_since = context.lap_number - last_activation_lap
                if laps_since < skill.cooldown_laps:
                    return (
                        False,
                        f"cooldown active ({laps_since}/{skill.cooldown_laps} laps)",
                    )

        return True, None

    def _record_activation(self, skill: DriverSkill, context: SkillContext):
        """Record skill activation for tracking limits."""
        skill_key = self._get_skill_key(skill)

        # Increment activation count
        current_count = self.skill_activation_counts.get(skill_key, 0)
        self.skill_activation_counts[skill_key] = current_count + 1

        # Record last activation lap
        self.skill_last_activation_lap[skill_key] = context.lap_number

        # Record activation for this lap
        if context.lap_number not in self.activated_this_lap:
            self.activated_this_lap[context.lap_number] = set()
        self.activated_this_lap[context.lap_number].add(skill_key)

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

        # Check activation limits (max_activations and cooldown_laps)
        can_activate, limit_reason = self._check_activation_limits(skill, context)
        if not can_activate:
            return SkillEffectResult(
                should_activate=False,
                message=f"Skill blocked: {limit_reason}",
            )

        # Calculate effect based on skill type
        result = self._calculate_effect(skill, context)

        if result.should_activate:
            # Record activation for limit tracking
            self._record_activation(skill, context)

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

    def _check_trigger(
        self, trigger: SkillTrigger, context: Optional[SkillContext]
    ) -> bool:
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

        if trigger == SkillTrigger.DEFENDING_MULTI_CAR_TRAIN:
            return bool(context.is_defending) and bool(context.is_in_multi_car_train)

        if trigger == SkillTrigger.ATTACKING:
            return bool(context.is_attacking)

        if trigger == SkillTrigger.IN_DRS_ZONE:
            return bool(context.is_in_drs_zone)

        if trigger == SkillTrigger.DRS_ZONE_EXTENDED:
            return (
                bool(context.is_in_drs_zone) and context.drs_zone_consecutive_laps >= 3
            )

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
            return bool(
                context.team_order_to_defend
                or (
                    context.teammate_name
                    and context.team_order_issued
                    and context.teammate_gap is not None
                    and context.teammate_gap > 0
                )
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
        skill_key = self._get_skill_key(skill)

        # 直感A - Stroll's defense OR rain skill (每次处于ot模式只激活一次)
        if skill.name_cn == "直感A":
            # Track per-OT-mode activation
            driver = skill.driver
            ot_session = self.current_ot_session.get(driver, 0)
            ot_key = f"{skill_key}|{ot_session}"

            # Check if already activated in this OT mode
            if ot_key in self.ot_mode_activations:
                return SkillEffectResult(should_activate=False)

            if context.is_defending or context.is_raining():
                # Mark as activated for this OT mode
                self.ot_mode_activations[ot_key] = 1
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"直感A activates: R+0.3 ({'defending' if context.is_defending else 'rain'})",
                )

        # 老潘课堂 - Verstappen's rain skill (仅赛道wet时启动，dry时停止，只激活一次)
        if skill.name_cn == "老潘课堂":
            # Check if track is wet
            is_wet = (
                context.track_condition.name in ["WET", "FLOODED"]
                or context.is_raining()
            )

            if is_wet:
                # Only activate if not already activated
                if not self.weather_skill_activated.get(skill_key, False):
                    self.weather_skill_activated[skill_key] = True
                    return SkillEffectResult(
                        should_activate=True,
                        r_modifier=skill.effect_value,
                        message="老潘课堂 activates: R+0.5 in wet conditions",
                    )
                else:
                    # Already activated, stay active in wet
                    return SkillEffectResult(
                        should_activate=True,
                        r_modifier=skill.effect_value,
                        message="老潘课堂 active: R+0.5 in wet conditions",
                    )
            else:
                # Track is dry - deactivate if was active
                if self.weather_skill_activated.get(skill_key, False):
                    self.weather_skill_activated[skill_key] = False
                    return SkillEffectResult(
                        should_activate=False,
                        message="老潘课堂 deactivated: Track is now dry",
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

        # Smooth Operator - base + train bonus (只激活一次)
        if skill.name_cn == "Smooth Operator":
            driver = skill.driver

            # Check if already activated (max_activations=1)
            if self.smooth_operator_activated.get(driver, False):
                return SkillEffectResult(should_activate=False)

            base_bonus = skill.conditions.get("base_bonus", 0.3)

            # Check if in multi-car train (3+ cars within 1 second)
            is_multi_car_train = (
                context.is_in_multi_car_train or context.is_forming_train
            )
            train_bonus = (
                skill.conditions.get("train_bonus", 0.3) if is_multi_car_train else 0
            )
            total = base_bonus + train_bonus

            # Determine message based on train type
            if context.is_in_multi_car_train:
                train_msg = "multi-car train"
            elif context.is_forming_train:
                train_msg = "forming train"
            else:
                train_msg = "defending"

            # Mark as activated
            self.smooth_operator_activated[driver] = True

            return SkillEffectResult(
                should_activate=True,
                r_modifier=total,
                message=f"Smooth Operator: R+{total:.1f} ({train_msg}) (只激活一次)",
            )

        # WIDELONSO - track consecutive defenses and vehicle damage
        # overtake时处于防守位（每次处于ot模式只激活一次）
        # 若防守连续成功10次则骰子确认车辆性能损耗
        if skill.name_cn == "WIDELONSO":
            driver = skill.driver
            skill_key = self._get_skill_key(skill)

            # Track per-OT-mode activation
            ot_session = self.current_ot_session.get(driver, 0)
            ot_key = f"{skill_key}|{ot_session}"

            # Check if already activated in this OT mode
            if ot_key in self.ot_mode_activations:
                return SkillEffectResult(should_activate=False)

            # Mark as activated for this OT mode
            self.ot_mode_activations[ot_key] = 1

            # Track consecutive defenses
            if driver not in self.consecutive_defense_success:
                self.consecutive_defense_success[driver] = 0
            self.consecutive_defense_success[driver] += 1

            threshold = skill.conditions.get("consecutive_defenses_threshold", 10)
            consecutive = self.consecutive_defense_success[driver]

            message = f"WIDELONSO: R+0.8 (defense #{consecutive})"

            # Check for vehicle damage after 10 consecutive defenses
            extra_dice = None
            if consecutive >= threshold:
                # Roll for vehicle damage (1d10, damage on 1-3 for example)
                damage_roll = random.randint(1, 10)
                damage_threshold = 3  # 30% chance of damage
                damage_occurred = damage_roll <= damage_threshold

                # Store damage state
                if damage_occurred:
                    self.widelonso_damage[driver] = (
                        self.widelonso_damage.get(driver, 0) + 0.1
                    )

                message += f" - Vehicle damage check: {damage_roll}/10 ({'DAMAGE!' if damage_occurred else 'OK'})"

                extra_dice = {
                    "type": "vehicle_damage_check",
                    "dice_type": "d10",
                    "result": damage_roll,
                    "threshold": damage_threshold,
                    "damage_occurred": damage_occurred,
                    "total_damage": self.widelonso_damage.get(driver, 0),
                }

            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=message,
            )

            if extra_dice:
                result.extra_dice_required = extra_dice

            return result

        # 画龙高手 - defense with penalty risk (只激活一次)
        if skill.name_cn == "画龙高手":
            driver = skill.driver

            # Check if already activated (max_activations=1)
            if self.dragon_painter_activated.get(driver, False):
                return SkillEffectResult(should_activate=False)

            # Mark as activated
            self.dragon_painter_activated[driver] = True

            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message="画龙高手: R+0.8 defending (只激活一次)",
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

        # WIDEZHOU - Zhou's defense skill
        # overtake判定下防守位置时R+0.5（只激活一次）
        if skill.name_cn == "WIDEZHOU":
            driver = skill.driver

            # Check if already activated (max_activations=1)
            if self.widezhou_activated.get(driver, False):
                return SkillEffectResult(should_activate=False)

            if context.is_defending:
                self.widezhou_activated[driver] = True
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"WIDEZHOU: R+{skill.effect_value} defending (只激活一次)",
                    extra_dice_required={
                        "type": "widezhou_defense",
                        "max_activations": 1,
                    },
                )

        # Simple defense skills (其他简单防守技能)
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
        # overtake判定时骰子控制R值增点，成功则R+0.5（只激活一次，退出及后续判定失败时关闭）
        # 超车成功时再1d10=10时把对方撞出去，自己判定为无损
        if skill.name_cn == "振金超车":
            driver = skill.driver
            conditions = skill.conditions
            r_boost_chance = conditions.get("r_boost_chance", 0.10)
            r_boost_value = conditions.get("r_boost_value", 0.5)

            # Roll for R boost (d10, 10% = roll 1)
            r_boost_roll = random.randint(1, 10)
            r_boost_success = r_boost_roll == 1

            # Roll for opponent not noticing (d10, 10% = roll 1) - for indestructible effect
            unnoticed_roll = random.randint(1, 10)
            unnoticed_success = unnoticed_roll == 1

            # Both must succeed for indestructible overtake (1% total)
            indestructible_active = r_boost_success and unnoticed_success

            # Roll for crash check (1d10=10时把对方撞出去)
            crash_roll = random.randint(1, 10)
            crash_success = crash_roll == 10  # 10% chance to push opponent out

            # Store crash roll result
            self.indestructible_crash_roll[driver] = crash_roll

            if indestructible_active:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_boost_value,
                    message=f"振金超车 ACTIVATED! R+{r_boost_value} (rolls: {r_boost_roll}, {unnoticed_roll}) - Opponent pushed out, self unharmed! Crash roll: {crash_roll}",
                    extra_dice_required={
                        "type": "indestructible_overtake",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "crash_roll": crash_roll,
                        "crash_success": crash_success,
                        "r_boost_success": r_boost_success,
                        "unnoticed_success": unnoticed_success,
                        "pushes_opponent_out": crash_success,  # Only if crash_roll=10
                        "self_unharmed": True,
                    },
                )
            elif r_boost_success:
                # Only R boost succeeded - check for crash
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_boost_value,
                    message=f"振金超车 partial: R+{r_boost_value} (r_boost roll: {r_boost_roll}, unnoticed roll: {unnoticed_roll}) Crash roll: {crash_roll}",
                    extra_dice_required={
                        "type": "indestructible_overtake_partial",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "crash_roll": crash_roll,
                        "crash_success": crash_success,
                        "r_boost_success": True,
                        "unnoticed_success": False,
                        "pushes_opponent_out": crash_success,
                    },
                )
            else:
                # Neither succeeded - skill didn't activate
                return SkillEffectResult(
                    should_activate=False,
                    message=f"振金超车 failed (rolls: {r_boost_roll}, {unnoticed_roll})",
                )

        # 极限哥 - Leclerc's DRS skill
        # 三圈及以上在其他车手DRS区，或其他车手在自己DRS区时，R+0.5（只激活一次）
        # 但每圈增加Ra10判定会不会操作变形，Ra10成功时R在基础值上倒扣0.5，该状态20圈后提升至Ra20
        if skill.name_cn == "极限哥":
            driver = skill.driver
            min_laps = skill.conditions.get("min_drs_laps", 3)

            # Track DRS state
            if context.drs_zone_consecutive_laps >= min_laps:
                # Initialize tracking if needed
                if driver not in self.limit_master_drs_start_lap:
                    self.limit_master_drs_start_lap[driver] = context.lap_number
                    self.limit_master_in_drs_count[driver] = 0

                # Increment DRS lap count
                self.limit_master_in_drs_count[driver] += 1
                drs_lap_count = self.limit_master_in_drs_count[driver]

                # Determine Ra threshold: Ra10 for first 20 laps, Ra20 after
                if drs_lap_count <= 20:
                    ra_threshold = 10  # Ra10
                    ra_type = "Ra10"
                else:
                    ra_threshold = 20  # Upgraded to Ra20 after 20 laps
                    ra_type = "Ra20"

                # Roll for deformation check (1d10 for Ra10, 1d20 for Ra20)
                dice_max = 10 if drs_lap_count <= 20 else 20
                deformation_roll = random.randint(1, dice_max)

                # Success = roll <= threshold
                success = deformation_roll <= ra_threshold

                # R modifier: +0.5 on success, -0.5 from base on failure
                r_mod = skill.effect_value if success else -0.5

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=r_mod,
                    message=f"极限哥: {'R+0.5' if success else 'R-0.5 (deformation)'} ({ra_type} roll: {deformation_roll}/{dice_max}, DRS lap #{drs_lap_count})",
                    extra_dice_required={
                        "type": "deformation_check",
                        "result": deformation_roll,
                        "threshold": ra_threshold,
                        "dice_max": dice_max,
                        "ra_type": ra_type,
                        "drs_lap_count": drs_lap_count,
                    },
                )
            else:
                # Reset DRS tracking if not in DRS zone
                if driver in self.limit_master_drs_start_lap:
                    del self.limit_master_drs_start_lap[driver]
                    del self.limit_master_in_drs_count[driver]
                return SkillEffectResult(should_activate=False)

        # 武士道！ - Tsunoda's skill: overtake判定下R+1，但多一个骰子1d10=(1-5)算失误
        if skill.name_cn == "武士道！":
            driver = skill.driver

            # Roll for mistake check (1d10, 1-5 = mistake)
            mistake_roll = random.randint(1, 10)
            is_mistake = 1 <= mistake_roll <= 5

            # Store the roll result
            self.bushido_mistake_roll[driver] = mistake_roll

            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"武士道！: R+{skill.effect_value} (mistake check: {mistake_roll}/10)",
            )

            # Add extra dice check for mistake (1-5 = failure)
            result.extra_dice_required = {
                "type": "overtake_mistake_check",
                "dice_type": "d10",
                "result": mistake_roll,
                "threshold": 5,  # 1-5 = mistake (50% chance)
                "is_mistake": is_mistake,
                "failure_result": "overtake_mistake" if is_mistake else None,
            }

            return result

        # 我也是舒马赫 - Mick's skill: ot判定下防守位R+1，多一个骰子判断下个超车点是否失误
        if skill.name_cn == "我也是舒马赫":
            driver = skill.driver

            # Only activate when defending
            if not context.is_defending:
                return SkillEffectResult(should_activate=False)

            # Roll for next overtake point mistake check
            mistake_roll = random.randint(1, 10)
            is_mistake = mistake_roll <= 3  # 30% chance of mistake

            # Store the roll result
            self.schumacher_mistake_roll[driver] = mistake_roll

            result = SkillEffectResult(
                should_activate=True,
                r_modifier=skill.effect_value,
                message=f"我也是舒马赫: R+{skill.effect_value} defending (next OT point check: {mistake_roll}/10)",
            )

            # Add extra dice check for next overtake point mistake
            result.extra_dice_required = {
                "type": "next_overtake_mistake_check",
                "dice_type": "d10",
                "result": mistake_roll,
                "threshold": 3,  # 1-3 = mistake at next overtake point
                "is_mistake": is_mistake,
                "failure_result": "next_overtake_mistake" if is_mistake else None,
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
        skill_key = self._get_skill_key(skill)
        driver = skill.driver

        # 保胎大师 - Reduced R loss after cliff (只激活一次，换胎后恢复原数值)
        if skill.name_cn == "保胎大师":
            # Check if we're in a new stint (reset tracking)
            current_stint = f"{context.stint_number}"
            last_stint = self.tire_saver_activated.get(driver)

            if last_stint is not None and last_stint != current_stint:
                # New stint - reset activation count for this skill
                if skill_key in self.skill_activation_counts:
                    del self.skill_activation_counts[skill_key]
                if skill_key in self.skill_last_activation_lap:
                    del self.skill_last_activation_lap[skill_key]

            # Now check if past tire cliff and can activate
            if context.is_past_tire_cliff:
                # Check activation limits (respects max_activations=1)
                can_activate, _ = self._check_activation_limits(skill, context)
                if can_activate:
                    self.tire_saver_activated[driver] = current_stint
                    return SkillEffectResult(
                        should_activate=True,
                        r_modifier=skill.effect_value,  # Negative value reduces loss
                        message=f"保胎大师: {skill.effect_value:+.1f} R loss after cliff (stint {current_stint})",
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
        # 只在起步时判定，1d100=1到5时R值-0.5，后期稳定性上升后削减至（1-5）-（1-2）-1%
        if skill.name_cn == "昏厥起步":
            conditions = skill.conditions

            # Get improvement stage (0 = initial 1-5, 1 = improved 1-2, 2 = final 1%)
            improvement_stage = self.faint_start_stage.get(driver, 0)

            # Define ranges based on improvement stage
            # Stage 0: 1d100 = 1-5 (5%)
            # Stage 1: 1d100 = 1-2 (2%)
            # Stage 2: 1d100 = 1 (1%)
            if improvement_stage == 0:
                threshold = 5  # 1-5 = penalty
                chance_desc = "5% (1-5)"
            elif improvement_stage == 1:
                threshold = 2  # 1-2 = penalty
                chance_desc = "2% (1-2)"
            else:
                threshold = 1  # 1 = penalty
                chance_desc = "1% (1)"

            # Roll 1d100 for penalty
            roll = random.randint(1, 100)
            penalty_active = roll <= threshold

            # Store roll result
            self.faint_start_roll[driver] = roll

            if penalty_active:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,  # Negative (-0.5)
                    message=f"昏厥起步: R{skill.effect_value:+.1f} (rolled {roll}/100 <= {threshold}, {chance_desc})",
                    extra_dice_required={
                        "type": "faint_start_penalty",
                        "dice_type": "d100",
                        "result": roll,
                        "threshold": threshold,
                        "improvement_stage": improvement_stage,
                    },
                )
            else:
                # Improvement occurred - advance stage for next race (max stage 2)
                new_stage = min(improvement_stage + 1, 2)
                self.faint_start_stage[driver] = new_stage
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"昏厥起步 avoided (rolled {roll}/100, stage {improvement_stage} -> {new_stage})",
                )

        return SkillEffectResult(should_activate=False)

    def _handle_team_order_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle team order skills."""

        # 团队精神 - Russell's team spirit (affects team order compliance)
        if skill.name_cn == "团队精神":
            # This skill affects team order execution, not direct R value
            # It modifies the compliance check in team_orders.py
            # When active, driver only disobeys on 1-2 (80% compliance)
            if context.team_order_active or context.team_order_issued:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,  # No direct R boost, affects compliance
                    message="团队精神 active: High team order compliance (80%)",
                    extra_dice_required={
                        "type": "team_order_compliance",
                        "trait": "team_spirit",
                        "compliance_threshold": 3,  # 1d10 >= 3 to comply
                        "driver": "Russell",
                    },
                )

        # 狮子 - Ocon's lion trait (ignores team orders)
        # overtake判定时在防守位下，无论进攻位是否是队友R值+0.5（只激活一次），无视车队指令
        if skill.name_cn == "狮子":
            driver = skill.driver

            # Check if already activated (max_activations=1)
            if self.lion_activated.get(driver, False):
                # Still ignore team orders even if R boost is consumed
                if context.team_order_active or context.team_order_issued:
                    return SkillEffectResult(
                        should_activate=True,
                        r_modifier=0.0,
                        message="狮子 active: Ignores all team orders! (R boost already used)",
                        extra_dice_required={
                            "type": "team_order_compliance",
                            "trait": "lion",
                            "compliance_threshold": 11,
                            "driver": "Ocon",
                        },
                    )
                return SkillEffectResult(should_activate=False)

            # This skill makes driver ignore team orders completely
            if context.team_order_active or context.team_order_issued:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,  # No R boost, just ignores orders
                    message="狮子 active: Ignores all team orders!",
                    extra_dice_required={
                        "type": "team_order_compliance",
                        "trait": "lion",
                        "compliance_threshold": 11,  # Never complies (1d10 max 10)
                        "driver": "Ocon",
                    },
                )

            # Also gives defense bonus during overtake (只激活一次)
            if context.is_defending:
                self.lion_activated[driver] = True
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"狮子: R+{skill.effect_value} defending (vs anyone, 只激活一次)",
                    extra_dice_required={
                        "type": "lion_defense",
                        "max_activations": 1,
                    },
                )

        # 好大哥 - Bottas helping Zhou
        if skill.name_cn == "好大哥":
            teammate = skill.conditions.get("teammate", "Zhou")

            # Check the full scenario: team order/overtake mode + multi-car train + teammate behind
            if context.is_helping_teammate_scenario(teammate):
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"好大哥: R+{skill.effect_value} helping {teammate} in multi-car train",
                    extra_dice_required={
                        "type": "big_brother_scenario",
                        "teammate": teammate,
                        "in_train": context.is_in_multi_car_train,
                        "teammate_behind": context.is_behind_teammate,
                    },
                )

            # Fallback: basic team order check
            if context.teammate_name == teammate and (
                context.team_order_issued or context.team_order_to_defend
            ):
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"好大哥: R+{skill.effect_value} helping {teammate}",
                )

        # 车手都是自私的 - Sainz behind Leclerc
        # overtake判定时对手是Leclerc时R+0.5（只启动一次，退出时关闭）
        if skill.name_cn == "车手都是自私的":
            driver = skill.driver
            skill_key = self._get_skill_key(skill)
            teammate = skill.conditions.get("teammate", "Leclerc")

            # Check if already activated (max_activations=1)
            if self.selfish_driver_activated.get(driver, False):
                return SkillEffectResult(should_activate=False)

            # Check if opponent is Leclerc in overtake situation
            if context.is_attacking and context.opponent_name == teammate:
                # Mark as activated
                self.selfish_driver_activated[driver] = True
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"车手都是自私的: R+{skill.effect_value} vs {teammate} (只激活一次)",
                    extra_dice_required={
                        "type": "selfish_driver_bonus",
                        "opponent": teammate,
                        "max_activations": 1,
                    },
                )

            return SkillEffectResult(should_activate=False)

        # 大旗 - Grosjean team compensation
        # 默认团队精神，队友落后三个名次及以上或退赛时，Rating补偿+0.5（只激活一次）
        if skill.name_cn == "大旗":
            driver = skill.driver
            skill_key = self._get_skill_key(skill)
            threshold = skill.conditions.get("position_gap_threshold", 3)

            # Check if already activated (max_activations=1)
            current_count = self.skill_activation_counts.get(skill_key, 0)
            if current_count >= 1:
                return SkillEffectResult(should_activate=False)

            # Check if teammate is 3+ positions behind or retired
            teammate_behind = context.teammate_gap and context.teammate_gap >= threshold
            teammate_retired = context.extra_data.get("teammate_retired", False)

            if teammate_behind or teammate_retired:
                reason = (
                    "teammate_retired"
                    if teammate_retired
                    else f"teammate_behind_{threshold}+"
                )
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"大旗: R+{skill.effect_value} compensating for teammate ({reason}, 只激活一次)",
                    extra_dice_required={
                        "type": "team_compensation",
                        "teammate_gap": context.teammate_gap,
                        "teammate_retired": teammate_retired,
                        "max_activations": 1,
                    },
                )

        return SkillEffectResult(should_activate=False)

    def _handle_vehicle_control_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle vehicle control skills."""

        # 拉力传承 - Recovery from control loss
        # 失控救车骰，90%成功；即driver_error判定时加一个1d10，只有=1才会启动判定
        if skill.name_cn == "拉力传承":
            driver = skill.driver

            # This skill activates during driver_error check
            # First roll 1d10 - only roll = 1 triggers the skill check
            trigger_roll = random.randint(1, 10)
            self.rally_heritage_dice_result[driver] = trigger_roll

            if trigger_roll == 1:
                # Skill triggered - now roll for recovery (90% success)
                recovery_chance = skill.conditions.get("recovery_chance", 0.9)
                recovery_roll = random.random()
                recovery_success = recovery_roll < recovery_chance

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"拉力传承 TRIGGERED (d10={trigger_roll}): Recovery {'success' if recovery_success else 'failed'} (90% check: {recovery_roll:.1%})",
                    extra_dice_required={
                        "type": "recovery_check",
                        "trigger_dice": trigger_roll,
                        "trigger_dice_type": "d10",
                        "trigger_threshold": 1,  # Must roll 1 to trigger
                        "recovery_result": int(recovery_roll * 100),
                        "recovery_threshold": int(recovery_chance * 100),
                        "recovery_success": recovery_success,
                    },
                )
            else:
                # Skill not triggered (d10 != 1)
                return SkillEffectResult(
                    should_activate=False,
                    message=f"拉力传承 not triggered (d10={trigger_roll}, need 1)",
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
        # 每站骰子决定R值变化，分为-0.5, -0.3, 0, +0.3, +0.5五个档
        # 车所有指标过90即取消（只激活一次）
        if skill.name_cn == "盲盒车":
            driver = skill.driver

            # Check if already cancelled due to car metrics
            if self.blind_box_cancelled.get(driver, False):
                return SkillEffectResult(
                    should_activate=False,
                    message="盲盒车: Cancelled (all car metrics > 90)",
                )

            # Check car metrics once per race (from context)
            if not self.blind_box_car_metrics_checked.get(driver, False):
                self.blind_box_car_metrics_checked[driver] = True

                # Get car metrics from context
                car_metrics = context.extra_data.get("car_metrics", {})
                if car_metrics:
                    # Check if all metrics are > 90
                    all_metrics = [
                        car_metrics.get("power", 0),
                        car_metrics.get("handling", 0),
                        car_metrics.get("aero", 0),
                        car_metrics.get("brakes", 0),
                        car_metrics.get("reliability", 0),
                    ]
                    all_above_90 = all(m > 90 for m in all_metrics if m > 0)

                    if all_above_90:
                        self.blind_box_cancelled[driver] = True
                        return SkillEffectResult(
                            should_activate=False,
                            message="盲盒车: Cancelled (all car metrics > 90)",
                        )

            # Roll once per race (store result)
            if driver not in self.blind_box_rolls:
                possible = skill.conditions.get(
                    "possible_values", [-0.5, -0.3, 0.0, 0.3, 0.5]
                )
                self.blind_box_rolls[driver] = random.choice(possible)

            roll_value = self.blind_box_rolls[driver]

            return SkillEffectResult(
                should_activate=True,
                r_modifier=roll_value,
                message=f"盲盒车: R{roll_value:+.1f} this race",
            )

        # 总导演 - Latifi's incident causing skill
        # 每站一个骰子确定1d10>7会整活（降低概率：30% chance），发生圈数由骰点决定（1-66圈）
        # 撞出去后再一个骰子确认是否干涉比赛进程（仅影响Latifi自己和超车/让车相关车手）
        # 技能只激活一次：比赛开始时判定，事故发生时执行
        if skill.name_cn == "总导演":
            driver = skill.driver
            skill_key = self._get_skill_key(skill)

            # Check if already decided this race (only process on first lap)
            if driver in self.chief_director_incident_caused:
                # Already decided - check if incident should happen on current lap
                incident_lap = self.chief_director_incident_lap.get(driver)
                if incident_lap and context.lap_number == incident_lap:
                    # Incident happens now - check for interference
                    # Only affect drivers in overtake/blue flag situation with Latifi
                    interference_roll = random.randint(1, 10)
                    interference_threshold = 7  # 70% threshold (reduced impact)
                    will_interfere = interference_roll >= interference_threshold

                    # Get affected drivers (Latifi + any in overtake/blue flag situation)
                    # For now, only Latifi himself is affected
                    affected_drivers = [driver]

                    return SkillEffectResult(
                        should_activate=True,
                        r_modifier=0.0,
                        message=f"总导演: INCIDENT on lap {incident_lap}! Interference check: {interference_roll}/10 ({'Affects: ' + ', '.join(affected_drivers) if will_interfere else 'No interference'})",
                        extra_dice_required={
                            "type": "chief_director_incident",
                            "dice_type": "d10",
                            "interference_roll": interference_roll,
                            "interference_threshold": interference_threshold,
                            "will_interfere": will_interfere,
                            "incident_type": "major_driver_error",
                            "incident_lap": incident_lap,
                            "affected_drivers": affected_drivers,
                        },
                    )
                # Not the incident lap - skill already activated (counted once)
                return SkillEffectResult(should_activate=False)

            # First time processing - must be first lap to decide
            if not context.is_first_lap:
                # Missed the decision window - no incident this race
                self.chief_director_incident_caused[driver] = False
                return SkillEffectResult(should_activate=False)

            # First lap - roll to decide if will cause incident (1d10 > 7 = 整活)
            # Reduced probability: 30% chance instead of 50%
            activity_roll = random.randint(1, 10)
            will_cause_incident = activity_roll > 7  # 8-10 = 30% chance (was 50%)

            # Store the decision
            self.chief_director_incident_caused[driver] = will_cause_incident

            if will_cause_incident:
                # Incident will happen - determine which lap (1-66, based on dice rolls)
                # First d10 determines tens digit (0-6), second d10 determines ones digit (0-9)
                tens_roll = random.randint(0, 6)  # 0-6 (allows laps 1-66)
                ones_roll = random.randint(0, 9)  # 0-9
                incident_lap = tens_roll * 10 + ones_roll
                # Ensure valid lap number (1-66)
                incident_lap = max(1, min(66, incident_lap))
                # Avoid lap 1 (start) and final lap for drama
                if incident_lap == 1:
                    incident_lap = 2
                elif incident_lap >= 66:
                    incident_lap = 65

                self.chief_director_incident_lap[driver] = incident_lap

                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.0,
                    message=f"总导演: Will cause incident on lap {incident_lap}! (trigger roll: {activity_roll}, lap roll: {tens_roll}{ones_roll})",
                    extra_dice_required={
                        "type": "chief_director_plan",
                        "dice_type": "d10",
                        "result": activity_roll,
                        "will_cause_incident": True,
                        "incident_lap": incident_lap,
                        "incident_type": "major_driver_error",
                    },
                )
            else:
                # No incident this race
                self.chief_director_incident_lap[driver] = 0  # Mark as no incident
                return SkillEffectResult(
                    should_activate=False,
                    message=f"总导演: No incident planned (roll: {activity_roll}, need >7)",
                )

        return SkillEffectResult(should_activate=False)

    def _handle_special_skill(
        self,
        skill: DriverSkill,
        context: SkillContext,
    ) -> SkillEffectResult:
        """Handle special/miscellaneous skills."""

        # 嗦球队 - Hulkenberg vs Magnussen
        # 在overtake判定下对手是马格努森时R值+0.5（只激活一次，退出ot时关闭）
        if skill.name_cn == "嗦球队":
            driver = skill.driver
            target = skill.conditions.get("target_driver", "Magnussen")

            # Check if already activated (max_activations=1)
            if self.suck_ball_activated.get(driver, False):
                return SkillEffectResult(should_activate=False)

            # Check if in overtake mode and opponent is Magnussen
            if context.is_attacking and context.opponent_name == target:
                # Mark as activated
                self.suck_ball_activated[driver] = True
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=skill.effect_value,
                    message=f"嗦球队: R+{skill.effect_value} vs {target}! (只激活一次)",
                    extra_dice_required={
                        "type": "vs_specific_driver",
                        "target": target,
                        "max_activations": 1,
                    },
                )

            return SkillEffectResult(should_activate=False)

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
        # R+0.1*1d10（只激活一次）= +0.1到+1.0
        if skill.name_cn == "（疑似）最强代打":
            driver = skill.driver

            # Roll once per race (1d10 * 0.1)
            if driver not in self.best_substitute_roll:
                dice_roll = random.randint(1, 10)
                self.best_substitute_roll[driver] = dice_roll * 0.1

            r_boost = self.best_substitute_roll[driver]

            return SkillEffectResult(
                should_activate=True,
                r_modifier=r_boost,
                message=f"最强代打: R+{r_boost:.1f} (1d10={int(r_boost * 10)}) as substitute",
                extra_dice_required={
                    "type": "substitute_bonus",
                    "dice_type": "d10",
                    "result": int(r_boost * 10),
                    "r_boost": r_boost,
                },
            )

        # 车斗术 - Grosjean's indestructible car (same as 振金超车)
        if skill.name_cn == "车斗术":
            driver = skill.driver
            # This is the same as 振金超车 - use same logic
            # Roll for R boost (d10, 10% = roll 1)
            r_boost_roll = random.randint(1, 10)
            r_boost_success = r_boost_roll == 1

            # Roll for opponent not noticing (d10, 10% = roll 1)
            unnoticed_roll = random.randint(1, 10)
            unnoticed_success = unnoticed_roll == 1

            # Both must succeed for indestructible overtake (1% total)
            indestructible_active = r_boost_success and unnoticed_success

            # Roll for crash check (1d10=10时把对方撞出去)
            crash_roll = random.randint(1, 10)
            crash_success = crash_roll == 10

            if indestructible_active:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.5,  # R+0.5
                    message=f"车斗术 ACTIVATED! R+0.5 (rolls: {r_boost_roll}, {unnoticed_roll}) - Crash roll: {crash_roll}",
                    extra_dice_required={
                        "type": "car_fighting_overtake",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "crash_roll": crash_roll,
                        "crash_success": crash_success,
                        "pushes_opponent_out": crash_success,
                        "self_unharmed": True,
                    },
                )
            elif r_boost_success:
                return SkillEffectResult(
                    should_activate=True,
                    r_modifier=0.5,
                    message=f"车斗术 partial: R+0.5 (rolls: {r_boost_roll}, {unnoticed_roll}) Crash roll: {crash_roll}",
                    extra_dice_required={
                        "type": "car_fighting_partial",
                        "r_boost_roll": r_boost_roll,
                        "unnoticed_roll": unnoticed_roll,
                        "crash_roll": crash_roll,
                        "crash_success": crash_success,
                    },
                )
            else:
                return SkillEffectResult(
                    should_activate=False,
                    message=f"车斗术 failed (rolls: {r_boost_roll}, {unnoticed_roll})",
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
        self.skill_activation_counts.clear()
        self.skill_last_activation_lap.clear()
        self.activated_this_lap.clear()
        # Reset weather skill activation tracking
        self.weather_skill_activated.clear()
        # Reset DRS tracking for 极限哥
        self.drs_consecutive_laps.clear()
        self.limit_master_drs_start_lap.clear()
        self.limit_master_in_drs_count.clear()
        # Reset WIDELONSO tracking
        self.consecutive_defense_success.clear()
        self.widelonso_damage.clear()
        # Reset OT mode tracking
        self.ot_mode_activations.clear()
        self.current_ot_session.clear()
        # Reset 总导演
        self.chief_director_incident_caused.clear()
        self.chief_director_incident_lap.clear()
        # Reset 抽象怪 (per race selection)
        self.abstract_godfather_selected.clear()
        self.abstract_godfather.clear()
        # Reset driver error tracking
        self.rally_heritage_dice_result.clear()
        # Reset 振金超车 crash tracking
        self.indestructible_crash_roll.clear()
        # Reset 盲盒车 cancellation
        self.blind_box_cancelled.clear()
        self.blind_box_car_metrics_checked.clear()
        # Reset 最强代打
        self.best_substitute_roll.clear()
        # Reset 武士道 mistake tracking
        self.bushido_mistake_roll.clear()
        # Reset 我也是舒马赫 mistake tracking
        self.schumacher_mistake_roll.clear()
        # Reset 昏厥起步 rolls
        self.faint_start_roll.clear()
        # Reset 冰人继承人 immunity
        self.iceman_incident_immunity.clear()
        # Reset 画龙高手 penalty tracking
        self.dragon_painter_penalty_active.clear()
        # Reset 车手都是自私的 activation
        self.selfish_driver_activated.clear()
        # Reset 嗦球队 activation
        self.suck_ball_activated.clear()
        # Reset 狮子 activation
        self.lion_activated.clear()
        # Reset 直感A OT session tracking
        self.instinct_a_ot_session.clear()
        # Reset driver error multiplier
        self.driver_error_multiplier.clear()
        # Reset 塞恩斯 vs Leclerc tracking
        self.sainz_vs_leclerc_active.clear()
        # Reset 好大哥 activation
        self.big_brother_activated.clear()
        # Reset WIDEZHOU activation
        self.widezhou_activated.clear()
        # Reset Smooth Operator activation
        self.smooth_operator_activated.clear()
        # Reset 画龙高手 activation
        self.dragon_painter_activated.clear()
        # Reset 昏厥起步 stage (starts at 0)
        self.faint_start_stage.clear()
        # Reset 保胎大师 activation per stint
        self.tire_saver_activated.clear()
        # Note: start_improvement persists across races (driver development)
