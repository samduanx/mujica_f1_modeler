"""
Driver Skill Manager.

Central manager for loading, tracking, and applying driver skills.
Integrates with the simulation to provide skill-based modifiers.
"""

from typing import Dict, List, Optional, Any
import random

from .skill_types import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillActivation,
    is_skill_pending,
)
from .skill_context import SkillContext, SessionType, WeatherCondition
from .skill_effects import SkillEffectCalculator, SkillEffectResult
from .skill_parser import load_skills_from_csv, DRIVER_NAME_MAP


class DriverSkillManager:
    """
        Manages all driver skills and their activation during races.

        This is the main interface for the simulation to interact with
    the skills system.
    """

    def __init__(self, csv_path: str = "data/driver_ratings.csv"):
        """
        Initialize the skill manager.

        Args:
            csv_path: Path to driver ratings CSV file
        """
        self.driver_skills: Dict[str, List[DriverSkill]] = {}
        self.effect_calculator = SkillEffectCalculator()
        self.csv_path = csv_path

        # Load skills from CSV
        self._load_skills()

        # Track active effects per driver
        self.active_effects: Dict[str, List[SkillEffectResult]] = {}

    def _load_skills(self):
        """Load skills from CSV file."""
        self.driver_skills = load_skills_from_csv(self.csv_path)

    def reload_skills(self):
        """Reload skills from CSV (useful for hot-reloading)."""
        self._load_skills()

    def get_driver_skills(self, driver: str) -> List[DriverSkill]:
        """
        Get all skills for a driver.

        Args:
            driver: Driver name (English)

        Returns:
            List of DriverSkill objects
        """
        return self.driver_skills.get(driver, [])

    def has_skill(self, driver: str, skill_name: str) -> bool:
        """
        Check if a driver has a specific skill.

        Args:
            driver: Driver name
            skill_name: Skill name (Chinese or English)

        Returns:
            True if driver has the skill
        """
        skills = self.driver_skills.get(driver, [])
        for skill in skills:
            if skill.name_cn == skill_name or skill.name_en == skill_name:
                return True
        return False

    def calculate_rating_modifier(
        self,
        driver: str,
        base_r: float,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> tuple[float, List[SkillActivation]]:
        """
        Calculate total R value modifier from active skills.

        Args:
            driver: Driver name
            base_r: Base R value
            context: Current race context
            race_time: Current race time

        Returns:
            Tuple of (total_r_modifier, list_of_activations)
        """
        skills = self.driver_skills.get(driver, [])
        if not skills:
            return 0.0, []

        total_modifier = 0.0
        activations: List[SkillActivation] = []

        for skill in skills:
            result = self.effect_calculator.check_skill_activation(
                skill, context, race_time
            )

            if result.should_activate:
                total_modifier += result.r_modifier

                if result.activation_record:
                    activations.append(result.activation_record)

        return total_modifier, activations

    def get_adjusted_r_value(
        self,
        driver: str,
        base_r: float,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> tuple[float, float, List[SkillActivation]]:
        """
        Get adjusted R value after applying skills.

        Args:
            driver: Driver name
            base_r: Base R value
            context: Current race context
            race_time: Current race time

        Returns:
            Tuple of (adjusted_r, modifier, activations)
        """
        modifier, activations = self.calculate_rating_modifier(
            driver, base_r, context, race_time
        )

        adjusted_r = base_r + modifier

        return adjusted_r, modifier, activations

    def get_defense_bonus(
        self,
        driver: str,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> tuple[float, Optional[SkillActivation]]:
        """
        Get defense bonus for a driver.

        Args:
            driver: Driver name
            context: Current race context
            race_time: Current race time

        Returns:
            Tuple of (bonus, activation_record)
        """
        if not context.is_defending:
            return 0.0, None

        # Create defense-specific context
        defense_context = SkillContext(
            session_type=context.session_type,
            lap_number=context.lap_number,
            position=context.position,
            is_defending=True,
            is_forming_train=context.is_forming_train,
            weather_condition=context.weather_condition,
            teammate_name=context.teammate_name,
            teammate_position=context.teammate_position,
        )

        modifier, activations = self.calculate_rating_modifier(
            driver, 0.0, defense_context, race_time
        )

        activation = activations[0] if activations else None
        return modifier, activation

    def get_attack_bonus(
        self,
        driver: str,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> tuple[float, Optional[SkillActivation]]:
        """
        Get attack/overtake bonus for a driver.

        Args:
            driver: Driver name
            context: Current race context
            race_time: Current race time

        Returns:
            Tuple of (bonus, activation_record)
        """
        # Create attack-specific context
        attack_context = SkillContext(
            session_type=context.session_type,
            lap_number=context.lap_number,
            position=context.position,
            is_attacking=True,
            is_in_drs_zone=context.is_in_drs_zone,
            drs_zone_consecutive_laps=context.drs_zone_consecutive_laps,
            opponent_name=context.opponent_name,
        )

        modifier, activations = self.calculate_rating_modifier(
            driver, 0.0, attack_context, race_time
        )

        activation = activations[0] if activations else None
        return modifier, activation

    def get_start_modifier(
        self,
        driver: str,
        context: SkillContext,
        race_time: float = 0.0,
    ) -> tuple[float, Optional[SkillActivation]]:
        """
        Get start/launch modifier for a driver.

        Args:
            driver: Driver name
            context: Current race context
            race_time: Current race time

        Returns:
            Tuple of (modifier, activation_record)
        """
        start_context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            is_race_start=True,
            is_first_lap=True,
        )

        modifier, activations = self.calculate_rating_modifier(
            driver, 0.0, start_context, race_time
        )

        activation = activations[0] if activations else None
        return modifier, activation

    def get_weather_modifier(
        self,
        driver: str,
        is_rain: bool,
        is_heavy_rain: bool = False,
    ) -> tuple[float, Optional[SkillActivation]]:
        """
        Get weather-related modifier.

        Args:
            driver: Driver name
            is_rain: Whether it's raining
            is_heavy_rain: Whether it's heavy rain

        Returns:
            Tuple of (modifier, activation_record)
        """
        if not is_rain:
            return 0.0, None

        weather = (
            WeatherCondition.HEAVY_RAIN
            if is_heavy_rain
            else WeatherCondition.LIGHT_RAIN
        )

        context = SkillContext(
            weather_condition=weather,
        )

        modifier, activations = self.calculate_rating_modifier(driver, 0.0, context)

        activation = activations[0] if activations else None
        return modifier, activation

    def get_qualifying_modifier(
        self,
        driver: str,
        q_stage: str,  # "Q1", "Q2", "Q3"
        is_in_danger: bool = False,
    ) -> tuple[float, List[SkillActivation]]:
        """
        Get qualifying session modifier.

        Args:
            driver: Driver name
            q_stage: Qualifying stage (Q1/Q2/Q3)
            is_in_danger: Whether driver is in elimination zone

        Returns:
            Tuple of (modifier, activations)
        """
        session_map = {
            "Q1": SessionType.QUALIFYING_Q1,
            "Q2": SessionType.QUALIFYING_Q2,
            "Q3": SessionType.QUALIFYING_Q3,
        }

        context = SkillContext(
            session_type=session_map.get(q_stage, SessionType.QUALIFYING_Q1),
            is_in_danger_zone=is_in_danger,
        )

        return self.calculate_rating_modifier(driver, 0.0, context)

    def get_tire_cliff_modifier(
        self,
        driver: str,
        is_past_cliff: bool,
    ) -> tuple[float, Optional[SkillActivation]]:
        """
        Get tire cliff modifier.

        Args:
            driver: Driver name
            is_past_cliff: Whether past tire degradation cliff

        Returns:
            Tuple of (modifier, activation_record)
        """
        if not is_past_cliff:
            return 0.0, None

        context = SkillContext(
            is_past_tire_cliff=True,
        )

        modifier, activations = self.calculate_rating_modifier(driver, 0.0, context)

        activation = activations[0] if activations else None
        return modifier, activation

    def check_recovery_skill(
        self,
        driver: str,
    ) -> tuple[bool, Optional[SkillActivation]]:
        """
        Check if driver can recover from control loss.

        Args:
            driver: Driver name

        Returns:
            Tuple of (can_recover, activation_record)
        """
        context = SkillContext(
            is_losing_control=True,
        )

        modifier, activations = self.calculate_rating_modifier(driver, 0.0, context)

        # Recovery skills don't modify R, they just activate
        can_recover = len(activations) > 0
        activation = activations[0] if activations else None

        return can_recover, activation

    def check_team_order_compliance(
        self,
        driver: str,
        team_order_issued: bool,
    ) -> tuple[bool, Optional[SkillActivation]]:
        """
        Check if driver will comply with team order.

        Args:
            driver: Driver name
            team_order_issued: Whether a team order was issued

        Returns:
            Tuple of (will_comply, activation_record)
        """
        if not team_order_issued:
            return True, None

        context = SkillContext(
            team_order_issued=True,
        )

        modifier, activations = self.calculate_rating_modifier(driver, 0.0, context)

        # Look for team spirit skill activation
        for activation in activations:
            if "团队精神" in activation.skill_name_cn:
                # Success means they complied (dice roll succeeded)
                return activation.success, activation

        return True, None

    def roll_blind_box_car(self, driver: str) -> float:
        """
        Roll the blind box car effect for Norris/Ricciardo.

        This should be called once per race at the start.
        Randomly selects a modifier value for this race.

        Args:
            driver: Driver name

        Returns:
            R modifier for this race
        """
        # Check if driver has blind box car skill
        if not self.has_skill(driver, "盲盒车"):
            return 0.0

        # Roll for blind box effect: random modifier between -1.0 and +1.0
        # This is a "blind box" - you don't know what you'll get until the race starts
        roll = random.random()  # 0.0 to 1.0

        # 25% chance for each tier: -1.0, -0.5, +0.5, +1.0
        if roll < 0.25:
            modifier = -1.0  # Bad car
        elif roll < 0.50:
            modifier = -0.5  # Slightly bad
        elif roll < 0.75:
            modifier = 0.5  # Slightly good
        else:
            modifier = 1.0  # Good car

        # Store the roll for reference during the race
        if not hasattr(self, "blind_box_rolls"):
            self.blind_box_rolls = {}
        self.blind_box_rolls[driver] = modifier

        return modifier

    def get_all_pending_skills(self) -> Dict[str, List[str]]:
        """
        Get all pending skills grouped by driver.

        Returns:
            Dictionary mapping driver names to list of pending skill names
        """
        pending = {}

        for driver, skills in self.driver_skills.items():
            for skill in skills:
                if skill.trigger == SkillTrigger.PENDING:
                    if driver not in pending:
                        pending[driver] = []
                    pending[driver].append(skill.name_cn)

        return pending

    def reset_for_new_race(self):
        """Reset state for a new race."""
        self.effect_calculator.reset_race_state()
        self.active_effects.clear()

    def get_activation_history(
        self, driver: Optional[str] = None
    ) -> List[SkillActivation]:
        """
        Get skill activation history.

        Args:
            driver: Optional driver name to filter by

        Returns:
            List of skill activations
        """
        if driver:
            return self.effect_calculator.activation_history.get(driver, [])

        all_activations = []
        for activations in self.effect_calculator.activation_history.values():
            all_activations.extend(activations)

        return all_activations

    def get_driver_with_skill(self, skill_name_cn: str) -> List[str]:
        """
        Find all drivers with a specific skill.

        Args:
            skill_name_cn: Skill name in Chinese

        Returns:
            List of driver names
        """
        drivers = []

        for driver, skills in self.driver_skills.items():
            for skill in skills:
                if skill.name_cn == skill_name_cn:
                    drivers.append(driver)
                    break

        return drivers


# Global skill manager instance (singleton pattern)
_skill_manager: Optional[DriverSkillManager] = None


def get_skill_manager(csv_path: str = "data/driver_ratings.csv") -> DriverSkillManager:
    """
    Get the global skill manager instance.

    Args:
        csv_path: Path to driver ratings CSV

    Returns:
        DriverSkillManager instance
    """
    global _skill_manager

    if _skill_manager is None:
        _skill_manager = DriverSkillManager(csv_path)

    return _skill_manager


def reset_skill_manager():
    """Reset the global skill manager (useful for testing)."""
    global _skill_manager
    _skill_manager = None
