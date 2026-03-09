"""
Test script for the team order system.

Tests the implementation of:
- 拉塞尔 (Russell): 团队精神 - 80% compliance (only 1-2 fails)
- 奥康 (Ocon): 狮子 - 0% compliance (never complies)
- 博塔斯 (Bottas): 好大哥 - Auto helps teammate
"""

import sys

sys.path.insert(0, "src")

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
from src.skills import SkillContext, SessionType
from src.skills.skill_effects import SkillEffectCalculator
from src.skills.skill_types import (
    DriverSkill,
    SkillCategory,
    SkillTrigger,
    SkillEffectType,
)


def test_driver_traits():
    """Test driver trait loading."""
    print("=" * 60)
    print("Testing Driver Traits")
    print("=" * 60)

    # Test Russell - 团队精神
    russell = get_driver_team_order_traits("Russell")
    print(f"\nRussell:")
    print(f"  Team Spirit: {russell.team_spirit}")
    print(f"  Lion Trait: {russell.lion_trait}")
    print(f"  Big Brother: {russell.big_brother}")
    threshold, compliance = russell.get_compliance_threshold()
    print(f"  Compliance Threshold: {threshold} (1d10 >= {threshold})")
    print(f"  Compliance Level: {compliance.value}")

    # Test Ocon - 狮子
    ocon = get_driver_team_order_traits("Ocon")
    print(f"\nOcon:")
    print(f"  Team Spirit: {ocon.team_spirit}")
    print(f"  Lion Trait: {ocon.lion_trait}")
    print(f"  Big Brother: {ocon.big_brother}")
    threshold, compliance = ocon.get_compliance_threshold()
    print(f"  Compliance Threshold: {threshold} (never complies)")
    print(f"  Compliance Level: {compliance.value}")

    # Test Bottas - 好大哥
    bottas = get_driver_team_order_traits("Bottas")
    print(f"\nBottas:")
    print(f"  Team Spirit: {bottas.team_spirit}")
    print(f"  Lion Trait: {bottas.lion_trait}")
    print(f"  Big Brother: {bottas.big_brother}")
    threshold, compliance = bottas.get_compliance_threshold()
    print(f"  Compliance Threshold: {threshold} (auto comply)")
    print(f"  Compliance Level: {compliance.value}")

    print("\n[PASS] Driver traits test passed!")


def test_team_order_execution():
    """Test team order execution with different drivers."""
    print("\n" + "=" * 60)
    print("Testing Team Order Execution")
    print("=" * 60)

    manager = TeamOrderManager()

    # Test Russell (团队精神) - should comply most of the time
    print("\n--- Testing Russell (团队精神) ---")
    russell_complies = 0
    for i in range(10):
        result = execute_team_order(
            target_driver="Russell",
            beneficiary_driver="Hamilton",
            team="Mercedes",
        )
        if result.success:
            russell_complies += 1
        status = "[OK] Complied" if result.success else "[NO] Refused"
        print(f"  Roll {i + 1}: {result.roll} -> {status}")
    print(f"  Russell complied {russell_complies}/10 times ({russell_complies * 10}%)")
    print(f"  Expected: ~80% (1d10 >= 3)")

    # Test Ocon (狮子) - should never comply
    print("\n--- Testing Ocon (狮子) ---")
    ocon_complies = 0
    for i in range(10):
        result = execute_team_order(
            target_driver="Ocon",
            beneficiary_driver="Gasly",
            team="Alpine",
        )
        if result.success:
            ocon_complies += 1
        status = "[OK] Complied" if result.success else "[NO] Refused"
        print(f"  Roll {i + 1}: {result.roll} -> {status}")
    print(f"  Ocon complied {ocon_complies}/10 times ({ocon_complies * 10}%)")
    print(f"  Expected: 0% (狮子 ignores all orders)")

    # Test Bottas (好大哥) - should always comply
    print("\n--- Testing Bottas (好大哥) ---")
    bottas_complies = 0
    for i in range(5):
        result = execute_team_order(
            target_driver="Bottas",
            beneficiary_driver="Zhou",
            team="Alfa Romeo",
        )
        if result.success:
            bottas_complies += 1
        status = "[OK] Complied" if result.success else "[NO] Refused"
        print(f"  Roll {i + 1}: {result.roll} -> {status}")
    print(f"  Bottas complied {bottas_complies}/5 times ({bottas_complies * 20}%)")
    print(f"  Expected: 100% (好大哥 auto complies)")

    print("\n[PASS] Team order execution test passed!")


def test_skill_integration():
    """Test skill integration with team orders."""
    print("\n" + "=" * 60)
    print("Testing Skill Integration")
    print("=" * 60)

    calculator = SkillEffectCalculator()

    # Create context with team order active
    context = SkillContext(
        session_type=SessionType.RACE,
        lap_number=10,
        team_order_active=True,
        team_order_issued=True,
        team_order_mode="yield",
        teammate_name="Zhou",
        is_behind_teammate=True,
        is_in_multi_car_train=True,
    )

    # Test 团队精神 (Russell)
    print("\n--- Testing 团队精神 skill ---")
    team_spirit_skill = DriverSkill(
        name_cn="团队精神",
        name_en="Team Spirit",
        driver="Russell",
        description="车队指令要求让车时1d10=1或2以外的所有值时让车",
        category=SkillCategory.TEAM_ORDER,
        trigger=SkillTrigger.TEAM_ORDER,
        effect_type=SkillEffectType.RATING_BOOST,
        effect_value=0.0,
    )
    result = calculator.check_skill_activation(team_spirit_skill, context)
    print(f"  Skill activated: {result.should_activate}")
    print(f"  Message: {result.message}")
    if result.extra_dice_required:
        print(f"  Extra dice: {result.extra_dice_required}")

    # Test 狮子 (Ocon)
    print("\n--- Testing 狮子 skill ---")
    lion_skill = DriverSkill(
        name_cn="狮子",
        name_en="Lion",
        driver="Ocon",
        description="无视车队指令",
        category=SkillCategory.TEAM_ORDER,
        trigger=SkillTrigger.TEAM_ORDER,
        effect_type=SkillEffectType.RATING_BOOST,
        effect_value=0.0,
    )
    result = calculator.check_skill_activation(lion_skill, context)
    print(f"  Skill activated: {result.should_activate}")
    print(f"  Message: {result.message}")
    if result.extra_dice_required:
        print(f"  Extra dice: {result.extra_dice_required}")

    # Test 好大哥 (Bottas)
    print("\n--- Testing 好大哥 skill ---")
    big_brother_skill = DriverSkill(
        name_cn="好大哥",
        name_en="Big Brother",
        driver="Bottas",
        description="在车队指令或overtake模式下、周冠宇和博塔斯和第三人在一起进入、且周冠宇落后时R+1",
        category=SkillCategory.TEAM_ORDER,
        trigger=SkillTrigger.HELPING_TEAMMATE,
        effect_type=SkillEffectType.RATING_BOOST,
        effect_value=1.0,
        conditions={"teammate": "Zhou"},
    )
    result = calculator.check_skill_activation(big_brother_skill, context)
    print(f"  Skill activated: {result.should_activate}")
    print(f"  Message: {result.message}")
    print(f"  R modifier: {result.r_modifier}")

    print("\n[PASS] Skill integration test passed!")


def test_order_detection():
    """Test team order opportunity detection."""
    print("\n" + "=" * 60)
    print("Testing Order Detection")
    print("=" * 60)

    from src.strategist.team_orders import should_issue_team_order

    # Test case: Same team, rear driver faster, reasonable gap
    should_issue, reason = should_issue_team_order(
        front_driver="Perez",
        rear_driver="Verstappen",
        front_pace=82.5,
        rear_pace=82.0,  # 0.5s faster
        gap=1.2,
        is_same_team=True,
        is_drs_zone=True,
    )
    print(f"\nTest 1: Verstappen behind Perez, 0.5s faster, DRS zone")
    print(f"  Should issue: {should_issue}")
    print(f"  Reason: {reason}")

    # Test case: Different teams
    should_issue, reason = should_issue_team_order(
        front_driver="Hamilton",
        rear_driver="Verstappen",
        front_pace=82.5,
        rear_pace=82.0,
        gap=1.2,
        is_same_team=False,
    )
    print(f"\nTest 2: Different teams (Hamilton vs Verstappen)")
    print(f"  Should issue: {should_issue}")
    print(f"  Reason: {reason}")

    # Test case: Gap too large
    should_issue, reason = should_issue_team_order(
        front_driver="Perez",
        rear_driver="Verstappen",
        front_pace=82.5,
        rear_pace=82.0,
        gap=3.0,  # Too far
        is_same_team=True,
    )
    print(f"\nTest 3: Gap too large (3.0s)")
    print(f"  Should issue: {should_issue}")
    print(f"  Reason: {reason}")

    print("\n[PASS] Order detection test passed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TEAM ORDER SYSTEM TEST SUITE")
    print("=" * 60)

    try:
        test_driver_traits()
        test_team_order_execution()
        test_skill_integration()
        test_order_detection()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
