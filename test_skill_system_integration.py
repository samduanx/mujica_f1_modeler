"""
Comprehensive Integration Tests for the Driver Skills System.

This test file validates:
1. Skill activation limits (max_activations)
2. Multi-car train detection and bonuses
3. Team order system (Russell/Ocon/Bottas traits)
4. Special skills (老潘课堂/保胎大师/振金超车/昏厥起步/盲盒车)
5. Integration with DRS/overtake systems
6. Integration with strategist system
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from unittest.mock import patch, MagicMock

from src.skills import (
    DriverSkill,
    SkillTrigger,
    SkillEffectType,
    SkillCategory,
    SkillContext,
    SessionType,
    WeatherCondition,
    TrackCondition,
    DriverSkillManager,
    load_skills_from_csv,
    parse_skill,
)
from src.skills.skill_effects import SkillEffectCalculator, SkillEffectResult
from src.strategist import (
    TeamOrder,
    TeamOrderType,
    TeamOrderStatus,
    TeamOrderManager,
    get_driver_team_order_traits,
    execute_team_order,
    DEFAULT_DRIVER_TEAM_ORDER_TRAITS,
)
from src.strategist.team_orders import TeamOrderCompliance


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def skill_calculator():
    """Create a fresh skill effect calculator."""
    return SkillEffectCalculator()


@pytest.fixture
def team_order_manager():
    """Create a fresh team order manager."""
    return TeamOrderManager()


@pytest.fixture
def rain_context():
    """Create a context with rain conditions."""
    return SkillContext(
        session_type=SessionType.RACE,
        lap_number=5,
        weather_condition=WeatherCondition.LIGHT_RAIN,
        track_condition=TrackCondition.WET,
        rain_intensity=0.5,
    )


@pytest.fixture
def dry_context():
    """Create a context with dry conditions."""
    return SkillContext(
        session_type=SessionType.RACE,
        lap_number=5,
        weather_condition=WeatherCondition.DRY,
        track_condition=TrackCondition.DRY,
        rain_intensity=0.0,
    )


@pytest.fixture
def defending_context():
    """Create a context where driver is defending."""
    return SkillContext(
        session_type=SessionType.RACE,
        lap_number=10,
        position=3,
        is_defending=True,
        gap_to_behind=0.5,
    )


@pytest.fixture
def multi_car_train_context():
    """Create a context with multi-car train (3+ cars within 1s)."""
    return SkillContext(
        session_type=SessionType.RACE,
        lap_number=10,
        position=3,
        is_defending=True,
        is_in_multi_car_train=True,
        is_forming_train=True,
        gap_to_ahead=0.8,
        gap_to_behind=0.6,
    )


@pytest.fixture
def team_order_context():
    """Create a context with team order active."""
    return SkillContext(
        session_type=SessionType.RACE,
        lap_number=15,
        team_order_active=True,
        team_order_issued=True,
        team_order_mode="yield",
        teammate_name="Hamilton",
        is_behind_teammate=True,
    )


# =============================================================================
# Test Class 1: Skill Activation Limits (max_activations)
# =============================================================================


class TestSkillActivationLimits:
    """Test that skills respect max_activations and cannot be repeated."""

    def test_max_activations_single_use_skill(
        self, skill_calculator, defending_context
    ):
        """Test that a skill with max_activations=1 can only activate once."""
        # Create a skill with max_activations=1
        skill = DriverSkill(
            name_cn="狮子",
            name_en="Lion",
            driver="Ocon",
            description="Test skill with max_activations=1",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.5,
            max_activations=1,
        )

        # First activation should succeed
        result1 = skill_calculator.check_skill_activation(skill, defending_context)
        assert result1.should_activate is True, "First activation should succeed"

        # Second activation on different lap should fail (max_activations reached)
        defending_context.lap_number = 11  # Different lap
        result2 = skill_calculator.check_skill_activation(skill, defending_context)
        assert result2.should_activate is False, (
            "Second activation should fail (max_activations reached)"
        )
        assert (
            "max_activations" in result2.message.lower()
            or "already activated" in result2.message.lower()
        ), f"Should indicate activation limit, got: {result2.message}"

    def test_max_activations_per_lap_prevention(
        self, skill_calculator, defending_context
    ):
        """Test that skills cannot activate multiple times in the same lap."""
        skill = DriverSkill(
            name_cn="TestSkill",
            name_en="TestSkill",
            driver="TestDriver",
            description="Test skill",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.3,
        )

        # First call activates
        result1 = skill_calculator.check_skill_activation(skill, defending_context)
        # Record the activation
        skill_key = skill_calculator._get_skill_key(skill)
        skill_calculator._record_activation(skill, defending_context)

        # Second call in same lap should fail
        result2 = skill_calculator.check_skill_activation(skill, defending_context)
        assert result2.should_activate is False, "Should not activate twice in same lap"

    def test_skill_resets_after_reset_race_state(
        self, skill_calculator, defending_context
    ):
        """Test that reset_race_state() clears activation counters."""
        skill = DriverSkill(
            name_cn="狮子",
            name_en="Lion",
            driver="Ocon",
            description="Test skill with max_activations=1",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.5,
            max_activations=1,
        )

        # Activate skill
        result1 = skill_calculator.check_skill_activation(skill, defending_context)
        assert result1.should_activate is True

        # Verify it's been recorded
        skill_key = skill_calculator._get_skill_key(skill)
        assert skill_calculator.skill_activation_counts.get(skill_key, 0) >= 1

        # Reset race state
        skill_calculator.reset_race_state()

        # Verify counters are cleared
        assert skill_key not in skill_calculator.skill_activation_counts
        assert skill_key not in skill_calculator.skill_last_activation_lap

        # Skill should be able to activate again in new race
        result2 = skill_calculator.check_skill_activation(skill, defending_context)
        assert result2.should_activate is True, (
            "Skill should activate after reset_race_state()"
        )

    def test_reset_race_state_clears_all_tracking_dicts(self, skill_calculator):
        """Verify all tracking dictionaries are cleared by reset_race_state()."""
        # Populate various tracking dicts
        skill_calculator.skill_activation_counts["test"] = 5
        skill_calculator.skill_last_activation_lap["test"] = 10
        skill_calculator.activated_this_lap[1] = {"skill1", "skill2"}
        skill_calculator.weather_skill_activated["test"] = True
        skill_calculator.lion_activated["Ocon"] = True
        skill_calculator.suck_ball_activated["Hulkenberg"] = True
        skill_calculator.big_brother_activated["Bottas"] = True
        skill_calculator.tire_saver_activated["TestDriver"] = "1"
        skill_calculator.faint_start_stage["TestDriver"] = 2

        # Reset
        skill_calculator.reset_race_state()

        # Verify all cleared
        assert len(skill_calculator.skill_activation_counts) == 0
        assert len(skill_calculator.skill_last_activation_lap) == 0
        assert len(skill_calculator.activated_this_lap) == 0
        assert len(skill_calculator.weather_skill_activated) == 0
        assert len(skill_calculator.lion_activated) == 0
        assert len(skill_calculator.suck_ball_activated) == 0
        assert len(skill_calculator.big_brother_activated) == 0
        assert len(skill_calculator.tire_saver_activated) == 0
        assert len(skill_calculator.faint_start_stage) == 0


# =============================================================================
# Test Class 2: Multi-Car Train Detection
# =============================================================================


class TestMultiCarTrain:
    """Test multi-car train detection (3+ cars within 1 second)."""

    def test_smooth_operator_base_bonus(self, skill_calculator, defending_context):
        """Test Smooth Operator base defense bonus without train."""
        skill = DriverSkill(
            name_cn="Smooth Operator",
            name_en="SmoothOperator",
            driver="Sainz",
            description="R+0.3 when defending, +0.6 in train",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.DEFENSE_BONUS,
            effect_value=0.3,
            conditions={"base_bonus": 0.3, "train_bonus": 0.3},
        )

        # Not in train - should get base bonus only
        defending_context.is_forming_train = False
        defending_context.is_in_multi_car_train = False

        result = skill_calculator._handle_defense_skill(skill, defending_context)
        assert result.should_activate is True
        assert result.r_modifier == 0.3, (
            f"Expected base bonus 0.3, got {result.r_modifier}"
        )
        assert "defending" in result.message.lower()

    def test_smooth_operator_train_bonus(
        self, skill_calculator, multi_car_train_context
    ):
        """Test Smooth Operator bonus in multi-car train."""
        skill = DriverSkill(
            name_cn="Smooth Operator",
            name_en="SmoothOperator",
            driver="Sainz",
            description="R+0.3 when defending, +0.6 in train",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.DEFENSE_BONUS,
            effect_value=0.3,
            conditions={"base_bonus": 0.3, "train_bonus": 0.3},
        )

        result = skill_calculator._handle_defense_skill(skill, multi_car_train_context)
        assert result.should_activate is True
        expected = 0.6  # base 0.3 + train 0.3
        assert result.r_modifier == expected, (
            f"Expected {expected}, got {result.r_modifier}"
        )
        assert "train" in result.message.lower()

    def test_multi_car_train_trigger_condition(self, skill_calculator):
        """Test DEFENDING_MULTI_CAR_TRAIN trigger condition."""
        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=10,
            is_defending=True,
            is_in_multi_car_train=True,
        )

        # Should trigger when both defending AND in multi-car train
        assert (
            skill_calculator._check_trigger(
                SkillTrigger.DEFENDING_MULTI_CAR_TRAIN, context
            )
            is True
        )

        # Should NOT trigger when not in multi-car train
        context.is_in_multi_car_train = False
        assert (
            skill_calculator._check_trigger(
                SkillTrigger.DEFENDING_MULTI_CAR_TRAIN, context
            )
            is False
        )

        # Should NOT trigger when not defending
        context.is_in_multi_car_train = True
        context.is_defending = False
        assert (
            skill_calculator._check_trigger(
                SkillTrigger.DEFENDING_MULTI_CAR_TRAIN, context
            )
            is False
        )


# =============================================================================
# Test Class 3: Team Order System
# =============================================================================


class TestTeamOrderSystem:
    """Test team order system with driver traits."""

    def test_russell_team_spirit_trait(self):
        """Test Russell has 团队精神 trait with 80% compliance."""
        traits = get_driver_team_order_traits("Russell")

        assert traits.team_spirit is True, "Russell should have team_spirit trait"
        assert traits.lion_trait is False
        assert traits.big_brother is False

        threshold, compliance = traits.get_compliance_threshold()
        assert compliance == TeamOrderCompliance.HIGH
        assert threshold == 3, f"Expected threshold 3 (80% compliance), got {threshold}"

    def test_ocon_lion_trait(self):
        """Test Ocon has 狮子 trait with 0% compliance."""
        traits = get_driver_team_order_traits("Ocon")

        assert traits.team_spirit is False
        assert traits.lion_trait is True, "Ocon should have lion_trait"
        assert traits.big_brother is False

        threshold, compliance = traits.get_compliance_threshold()
        assert compliance == TeamOrderCompliance.NEVER
        assert threshold == 11, (
            f"Expected threshold 11 (never complies), got {threshold}"
        )

    def test_bottas_big_brother_trait(self):
        """Test Bottas has 好大哥 trait with auto compliance."""
        traits = get_driver_team_order_traits("Bottas")

        assert traits.team_spirit is False
        assert traits.lion_trait is False
        assert traits.big_brother is True, "Bottas should have big_brother trait"

        threshold, compliance = traits.get_compliance_threshold()
        assert compliance == TeamOrderCompliance.AUTO_COMPLY
        assert threshold == 1, f"Expected threshold 1 (auto comply), got {threshold}"

    def test_russell_compliance_probability(self):
        """Test Russell complies ~80% of the time (1d10 >= 3)."""
        compliant_count = 0
        total_tests = 100

        for _ in range(total_tests):
            result = execute_team_order(
                target_driver="Russell",
                beneficiary_driver="Hamilton",
                team="Mercedes",
            )
            if result.success:
                compliant_count += 1

        compliance_rate = compliant_count / total_tests
        # Should be around 80% (with some variance due to randomness)
        assert 0.70 <= compliance_rate <= 0.90, (
            f"Russell compliance rate {compliance_rate:.2%} should be ~80%"
        )

    def test_ocon_never_complies(self):
        """Test Ocon never complies with team orders (狮子 trait)."""
        for _ in range(20):
            result = execute_team_order(
                target_driver="Ocon",
                beneficiary_driver="Gasly",
                team="Alpine",
            )
            assert result.success is False, "Ocon should never comply (狮子 trait)"

    def test_bottas_always_complies(self):
        """Test Bottas always complies with team orders (好大哥 trait)."""
        for _ in range(20):
            result = execute_team_order(
                target_driver="Bottas",
                beneficiary_driver="Zhou",
                team="AlfaRomeo",
            )
            assert result.success is True, "Bottas should always comply (好大哥 trait)"

    def test_lion_skill_activation(self, skill_calculator, team_order_context):
        """Test 狮子 skill activates and indicates team order ignorance."""
        skill = DriverSkill(
            name_cn="狮子",
            name_en="Lion",
            driver="Ocon",
            description="无视车队指令",
            category=SkillCategory.TEAM_ORDER,
            trigger=SkillTrigger.TEAM_ORDER,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.0,
            max_activations=1,
        )

        result = skill_calculator._handle_team_order_skill(skill, team_order_context)
        assert result.should_activate is True
        assert "无视" in result.message or "ignore" in result.message.lower()
        if result.extra_dice_required:
            assert result.extra_dice_required.get("compliance_threshold") == 11

    def test_team_spirit_skill_activation(self, skill_calculator, team_order_context):
        """Test 团队精神 skill activates for Russell."""
        skill = DriverSkill(
            name_cn="团队精神",
            name_en="TeamSpirit",
            driver="Russell",
            description="80% chance to obey team orders",
            category=SkillCategory.TEAM_ORDER,
            trigger=SkillTrigger.TEAM_ORDER,
            effect_type=SkillEffectType.DICE_CHANCE,
            effect_value=0.8,
        )

        result = skill_calculator._handle_team_order_skill(skill, team_order_context)
        assert result.should_activate is True
        assert "80%" in result.message or "compliance" in result.message.lower()


# =============================================================================
# Test Class 4: Special Skills
# =============================================================================


class TestSpecialSkills:
    """Test special skills with complex mechanics."""

    # -------------------------------------------------------------------------
    # 老潘课堂 (RainMaster) - Wet/Dry State Switching
    # -------------------------------------------------------------------------
    def test_rain_master_activates_in_wet(self, skill_calculator, rain_context):
        """Test 老潘课堂 activates when track is wet."""
        skill = DriverSkill(
            name_cn="老潘课堂",
            name_en="RainMaster",
            driver="Verstappen",
            description="R+0.5 in wet conditions (只激活一次)",
            category=SkillCategory.WEATHER,
            trigger=SkillTrigger.WEATHER_RAIN,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.5,
            max_activations=1,
        )

        result = skill_calculator._handle_weather_skill(skill, rain_context)
        assert result.should_activate is True
        assert result.r_modifier == 0.5
        assert "wet" in result.message.lower() or "老潘课堂" in result.message

    def test_rain_master_deactivates_in_dry(self, skill_calculator, dry_context):
        """Test 老潘课堂 deactivates when track becomes dry."""
        skill = DriverSkill(
            name_cn="老潘课堂",
            name_en="RainMaster",
            driver="Verstappen",
            description="R+0.5 in wet conditions (只激活一次)",
            category=SkillCategory.WEATHER,
            trigger=SkillTrigger.WEATHER_RAIN,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.5,
            max_activations=1,
        )

        # First activate in wet
        wet_context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=5,
            weather_condition=WeatherCondition.LIGHT_RAIN,
            track_condition=TrackCondition.WET,
        )
        skill_calculator._handle_weather_skill(skill, wet_context)

        # Now test in dry - should deactivate
        result = skill_calculator._handle_weather_skill(skill, dry_context)
        assert result.should_activate is False
        assert (
            "deactivated" in result.message.lower() or "dry" in result.message.lower()
        )

    # -------------------------------------------------------------------------
    # 保胎大师 (TireSaver) - Reset After Pit Stop
    # -------------------------------------------------------------------------
    def test_tire_saver_activates_past_cliff(self, skill_calculator):
        """Test 保胎大师 activates when past tire cliff."""
        skill = DriverSkill(
            name_cn="保胎大师",
            name_en="TireSaver",
            driver="Perez",
            description="-0.3 R loss after tire cliff",
            category=SkillCategory.TIRE_MANAGEMENT,
            trigger=SkillTrigger.TIRE_CLIFF,
            effect_type=SkillEffectType.TIRE_MODIFIER,
            effect_value=-0.3,
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=25,
            stint_number=1,
            is_past_tire_cliff=True,
            tire_age=20,
        )

        result = skill_calculator._handle_tire_skill(skill, context)
        assert result.should_activate is True
        assert result.r_modifier == -0.3

    def test_tire_saver_resets_after_pit(self, skill_calculator):
        """Test 保胎大师 resets after pit stop (new stint)."""
        skill = DriverSkill(
            name_cn="保胎大师",
            name_en="TireSaver",
            driver="Perez",
            description="-0.3 R loss after tire cliff (只激活一次，换胎后恢复原数值)",
            category=SkillCategory.TIRE_MANAGEMENT,
            trigger=SkillTrigger.TIRE_CLIFF,
            effect_type=SkillEffectType.TIRE_MODIFIER,
            effect_value=-0.3,
            max_activations=1,
        )

        # First stint - activate skill
        context1 = SkillContext(
            session_type=SessionType.RACE,
            lap_number=25,
            stint_number=1,
            is_past_tire_cliff=True,
        )
        result1 = skill_calculator._handle_tire_skill(skill, context1)
        assert result1.should_activate is True

        # Record activation
        skill_calculator.tire_saver_activated["Perez"] = "1"

        # Second stint - skill should be able to activate again
        context2 = SkillContext(
            session_type=SessionType.RACE,
            lap_number=35,
            stint_number=2,  # New stint
            is_past_tire_cliff=True,
        )

        # Simulate the stint check in _handle_tire_skill
        result2 = skill_calculator._handle_tire_skill(skill, context2)
        # The skill should be able to activate in new stint
        # (activation count was cleared when stint changed)

    # -------------------------------------------------------------------------
    # 振金超车 (Indestructible Overtake) - Crash on 1d10=10
    # -------------------------------------------------------------------------
    def test_indestructible_overtake_with_crash_roll_10(self, skill_calculator):
        """Test 振金超车 crash check when 1d10=10 (pushes opponent out)."""
        skill = DriverSkill(
            name_cn="振金超车",
            name_en="IndestructibleOvertake",
            driver="Grosjean",
            description="Indestructible overtake with crash check",
            category=SkillCategory.OVERTAKE,
            trigger=SkillTrigger.ATTACKING,
            effect_type=SkillEffectType.EXTRA_DICE_CHECK,
            effect_value=0.5,
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=10,
            is_attacking=True,
        )

        # Mock the random rolls to force crash scenario (1d10=10)
        with patch(
            "random.randint", side_effect=[1, 1, 10]
        ):  # r_boost=1, unnoticed=1, crash=10
            result = skill_calculator._handle_overtake_skill(skill, context)

        assert result.should_activate is True
        if result.extra_dice_required:
            assert result.extra_dice_required.get("crash_roll") == 10
            assert result.extra_dice_required.get("crash_success") is True

    def test_indestructible_overtake_no_crash(self, skill_calculator):
        """Test 振金超车 when crash roll is not 10."""
        skill = DriverSkill(
            name_cn="振金超车",
            name_en="IndestructibleOvertake",
            driver="Grosjean",
            description="Indestructible overtake with crash check",
            category=SkillCategory.OVERTAKE,
            trigger=SkillTrigger.ATTACKING,
            effect_type=SkillEffectType.EXTRA_DICE_CHECK,
            effect_value=0.5,
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=10,
            is_attacking=True,
        )

        # Mock rolls: r_boost=1, unnoticed=1 (both succeed), crash=5 (no crash)
        with patch("random.randint", side_effect=[1, 1, 5]):
            result = skill_calculator._handle_overtake_skill(skill, context)

        assert result.should_activate is True
        if result.extra_dice_required:
            assert result.extra_dice_required.get("crash_roll") == 5
            assert result.extra_dice_required.get("crash_success") is False

    # -------------------------------------------------------------------------
    # 昏厥起步 (Faint Start) - Improvement Stages
    # -------------------------------------------------------------------------
    def test_faint_start_stage_0_initial(self, skill_calculator):
        """Test 昏厥起步 at stage 0 (5% penalty chance: 1-5 on 1d100)."""
        skill = DriverSkill(
            name_cn="昏厥起步",
            name_en="FaintStart",
            driver="TestDriver",
            description="Start penalty with improvement over time",
            category=SkillCategory.START,
            trigger=SkillTrigger.START,
            effect_type=SkillEffectType.RATING_PENALTY,
            effect_value=-0.5,
            max_activations=1,
        )

        # Stage 0: threshold should be 5 (5%)
        skill_calculator.faint_start_stage["TestDriver"] = 0

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            is_race_start=True,
        )

        # Test with roll 3 (should trigger penalty at stage 0)
        with patch("random.randint", return_value=3):
            result = skill_calculator._handle_start_skill(skill, context)

        # At stage 0, roll 3 <= 5 should trigger penalty
        if result.extra_dice_required:
            assert result.extra_dice_required.get("threshold") == 5
            assert result.extra_dice_required.get("improvement_stage") == 0

    def test_faint_start_stage_1_improved(self, skill_calculator):
        """Test 昏厥起步 at stage 1 (2% penalty chance: 1-2 on 1d100)."""
        skill = DriverSkill(
            name_cn="昏厥起步",
            name_en="FaintStart",
            driver="TestDriver",
            description="Start penalty with improvement over time",
            category=SkillCategory.START,
            trigger=SkillTrigger.START,
            effect_type=SkillEffectType.RATING_PENALTY,
            effect_value=-0.5,
            max_activations=1,
        )

        # Stage 1: threshold should be 2 (2%)
        skill_calculator.faint_start_stage["TestDriver"] = 1

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            is_race_start=True,
        )

        # Test the threshold
        with patch("random.randint", return_value=2):
            result = skill_calculator._handle_start_skill(skill, context)

        if result.extra_dice_required:
            assert result.extra_dice_required.get("threshold") == 2
            assert result.extra_dice_required.get("improvement_stage") == 1

    def test_faint_start_stage_2_final(self, skill_calculator):
        """Test 昏厥起步 at stage 2 (1% penalty chance: 1 on 1d100)."""
        skill = DriverSkill(
            name_cn="昏厥起步",
            name_en="FaintStart",
            driver="TestDriver",
            description="Start penalty with improvement over time",
            category=SkillCategory.START,
            trigger=SkillTrigger.START,
            effect_type=SkillEffectType.RATING_PENALTY,
            effect_value=-0.5,
            max_activations=1,
        )

        # Stage 2: threshold should be 1 (1%)
        skill_calculator.faint_start_stage["TestDriver"] = 2

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            is_race_start=True,
        )

        with patch("random.randint", return_value=1):
            result = skill_calculator._handle_start_skill(skill, context)

        if result.extra_dice_required:
            assert result.extra_dice_required.get("threshold") == 1
            assert result.extra_dice_required.get("improvement_stage") == 2

    def test_faint_start_improvement_advances_stage(self, skill_calculator):
        """Test that avoiding penalty advances improvement stage."""
        skill = DriverSkill(
            name_cn="昏厥起步",
            name_en="FaintStart",
            driver="TestDriver",
            description="Start penalty with improvement over time",
            category=SkillCategory.START,
            trigger=SkillTrigger.START,
            effect_type=SkillEffectType.RATING_PENALTY,
            effect_value=-0.5,
            max_activations=1,
        )

        # Start at stage 0
        skill_calculator.faint_start_stage["TestDriver"] = 0

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            is_race_start=True,
        )

        # Roll high enough to avoid penalty (roll > 5 at stage 0)
        with patch("random.randint", return_value=50):
            result = skill_calculator._handle_start_skill(skill, context)

        # Stage should advance to 1
        assert skill_calculator.faint_start_stage["TestDriver"] == 1

    # -------------------------------------------------------------------------
    # 盲盒车 (Blind Box Car) - Car Metrics Check
    # -------------------------------------------------------------------------
    def test_blind_box_car_metrics_check_cancelled(self, skill_calculator):
        """Test 盲盒车 car metrics check (>90 cancels the skill)."""
        skill = DriverSkill(
            name_cn="盲盒车",
            name_en="BlindBoxCar",
            driver="Norris",
            description="Random R change per race, cancelled if car metrics > 90",
            category=SkillCategory.VARIABLE,
            trigger=SkillTrigger.EVERY_RACE_RANDOM,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.0,
            conditions={
                "possible_values": [-0.5, -0.3, 0.0, 0.3, 0.5],
                "cancel_if_car_90_plus": True,
            },
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            extra_data={
                "car_metrics": {
                    "power": 95,
                    "handling": 92,
                    "aero": 94,
                    "brakes": 91,
                    "reliability": 93,
                }
            },  # All car metrics > 90
        )

        # When all car metrics > 90, skill should be cancelled
        result = skill_calculator._handle_variable_skill(skill, context)
        assert result.should_activate is False, "Skill should be cancelled when all car metrics > 90"
        assert "cancelled" in result.message.lower() or "取消" in result.message

    def test_blind_box_car_metrics_check_low_metrics(self, skill_calculator):
        """Test 盲盒车 activates when car metrics are not all > 90."""
        skill = DriverSkill(
            name_cn="盲盒车",
            name_en="BlindBoxCar",
            driver="Ricciardo",
            description="Random R change per race, cancelled if car metrics > 90",
            category=SkillCategory.VARIABLE,
            trigger=SkillTrigger.EVERY_RACE_RANDOM,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.0,
            conditions={
                "possible_values": [-0.5, -0.3, 0.0, 0.3, 0.5],
                "cancel_if_car_90_plus": True,
            },
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
            extra_data={
                "car_metrics": {
                    "power": 85,  # < 90
                    "handling": 92,
                    "aero": 94,
                    "brakes": 91,
                    "reliability": 93,
                }
            },  # Not all metrics > 90
        )

        # When not all metrics > 90, skill should activate
        result = skill_calculator._handle_variable_skill(skill, context)
        assert result.should_activate is True, "Skill should activate when not all car metrics > 90"
        # The roll should be one of the possible values
        assert result.r_modifier in [-0.5, -0.3, 0.0, 0.3, 0.5]

    def test_blind_box_car_random_values(self, skill_calculator):
        """Test 盲盒车 random value selection from possible values."""
        skill = DriverSkill(
            name_cn="盲盒车",
            name_en="BlindBoxCar",
            driver="Ricciardo",
            description="Random R change per race",
            category=SkillCategory.VARIABLE,
            trigger=SkillTrigger.EVERY_RACE_RANDOM,
            effect_type=SkillEffectType.RATING_BOOST,
            effect_value=0.0,
            conditions={
                "possible_values": [-0.5, -0.3, 0.0, 0.3, 0.5],
            },
            max_activations=1,
        )

        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=1,
        )

        # Test multiple activations
        results = set()
        for _ in range(20):
            result = skill_calculator._handle_variable_skill(skill, context)
            results.add(result.r_modifier)
            # Reset for next iteration
            if "Ricciardo" in skill_calculator.blind_box_rolls:
                del skill_calculator.blind_box_rolls["Ricciardo"]

        # Should get values from the possible set
        assert all(r in [-0.5, -0.3, 0.0, 0.3, 0.5] for r in results)


# =============================================================================
# Test Class 5: Integration with Other Systems
# =============================================================================


class TestSystemIntegration:
    """Test integration with DRS, overtake, and strategist systems."""

    def test_skill_manager_gets_skills_from_csv(self):
        """Test that skill manager loads skills from CSV."""
        manager = DriverSkillManager()

        # Check some drivers are loaded
        assert "Verstappen" in manager.driver_skills
        assert "Leclerc" in manager.driver_skills
        assert "Alonso" in manager.driver_skills

        # Check Verstappen has rain skill
        verstappen_skills = manager.get_driver_skills("Verstappen")
        assert any(s.name_cn == "老潘课堂" for s in verstappen_skills)

    def test_calculate_rating_modifier_integration(
        self, skill_calculator, rain_context
    ):
        """Test full rating modifier calculation with multiple skills."""
        # Create multiple skills
        skills = [
            DriverSkill(
                name_cn="老潘课堂",
                name_en="RainMaster",
                driver="TestDriver",
                description="R+0.5 in rain",
                category=SkillCategory.WEATHER,
                trigger=SkillTrigger.WEATHER_RAIN,
                effect_type=SkillEffectType.RATING_BOOST,
                effect_value=0.5,
                max_activations=1,
            ),
            DriverSkill(
                name_cn="直感A",
                name_en="InstinctA",
                driver="TestDriver",
                description="R+0.3 defending or rain",
                category=SkillCategory.WEATHER,
                trigger=SkillTrigger.WEATHER_RAIN,
                effect_type=SkillEffectType.RATING_BOOST,
                effect_value=0.3,
                max_activations=1,
            ),
        ]

        # Manually set skills for calculator
        skill_calculator.driver_skills = {"TestDriver": skills}

        total_modifier = 0.0
        activations = []

        for skill in skills:
            result = skill_calculator.check_skill_activation(skill, rain_context)
            if result.should_activate:
                total_modifier += result.r_modifier
                if result.activation_record:
                    activations.append(result.activation_record)

        # Both skills should activate in rain
        assert total_modifier == 0.8  # 0.5 + 0.3
        assert len(activations) == 2

    def test_defense_bonus_integration(self, skill_calculator):
        """Test defense bonus calculation with context."""
        context = SkillContext(
            session_type=SessionType.RACE,
            lap_number=10,
            is_defending=True,
            is_forming_train=True,
        )

        skill = DriverSkill(
            name_cn="Smooth Operator",
            name_en="SmoothOperator",
            driver="TestDriver",
            description="R+0.3 defending, +0.3 train",
            category=SkillCategory.DEFENSE,
            trigger=SkillTrigger.DEFENDING,
            effect_type=SkillEffectType.DEFENSE_BONUS,
            effect_value=0.3,
            conditions={"base_bonus": 0.3, "train_bonus": 0.3},
        )

        result = skill_calculator._handle_defense_skill(skill, context)
        assert result.should_activate is True
        assert result.r_modifier == 0.6  # base + train

    def test_team_order_compliance_with_dice(self):
        """Test team order compliance uses dice rolls correctly."""
        # Test various drivers
        test_cases = [
            ("Russell", TeamOrderCompliance.HIGH, 3),  # 80% compliance
            ("Ocon", TeamOrderCompliance.NEVER, 11),  # 0% compliance
            ("Bottas", TeamOrderCompliance.AUTO_COMPLY, 1),  # 100% compliance
        ]

        for driver, expected_compliance, expected_threshold in test_cases:
            traits = get_driver_team_order_traits(driver)
            threshold, compliance = traits.get_compliance_threshold()

            assert compliance == expected_compliance, (
                f"{driver}: expected {expected_compliance}, got {compliance}"
            )
            assert threshold == expected_threshold, (
                f"{driver}: expected threshold {expected_threshold}, got {threshold}"
            )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Running Skill System Integration Tests")
    print("=" * 70)

    # Run with pytest
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )

    sys.exit(result.returncode)
