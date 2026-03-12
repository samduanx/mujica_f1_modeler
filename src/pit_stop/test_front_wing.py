"""
Test script for front wing replacement mechanism.

Tests:
1. Front wing damage creation from different incident types
2. Replacement decision logic (first dice roll)
3. Extra time calculation (second dice roll)
4. Integration with pit stop timing
"""

import sys
import os

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pit_stop.front_wing_replacement import (
    FrontWingManager,
    FrontWingSeverity,
    FRONT_WING_REPLACEMENT_CONFIG,
    FRONT_WING_TIME_BASE,
    FRONT_WING_TIME_PER_D10,
)


def test_front_wing_damage_creation():
    """Test creating front wing damage from incidents"""
    print("=== Test: Front Wing Damage Creation ===")

    manager = FrontWingManager()

    # Test driver_error damage
    damage1 = manager.create_damage_from_incident(
        driver="Verstappen",
        incident_type="driver_error",
        incident_severity="moderate",
        lap=15,
    )
    assert damage1 is not None
    assert damage1.driver == "Verstappen"
    assert damage1.severity == FrontWingSeverity.MODERATE
    assert damage1.source == "driver_error"
    print(f"[OK] Driver error damage created: {damage1.to_dict()}")

    # Test overtake_collision damage
    damage2 = manager.create_damage_from_incident(
        driver="Hamilton",
        incident_type="overtake_collision",
        incident_severity="major",
        lap=23,
    )
    assert damage2 is not None
    assert damage2.severity == FrontWingSeverity.MAJOR
    print(f"[OK] Overtake collision damage created: {damage2.to_dict()}")

    # Test invalid severity
    damage3 = manager.create_damage_from_incident(
        driver="Leclerc",
        incident_type="driver_error",
        incident_severity="invalid",
        lap=10,
    )
    assert damage3 is None
    print("[OK] Invalid severity handled correctly (returns None)")

    print()


def test_replacement_decision():
    """Test replacement decision logic (first dice roll)"""
    print("=== Test: Replacement Decision Logic ===")

    manager = FrontWingManager()

    # Add severe damage (should always replace)
    manager.add_damage(
        driver="Verstappen",
        severity=FrontWingSeverity.SEVERE,
        source="driver_error",
        lap=10,
    )

    # Test with forced dice roll
    result = manager.attempt_replacement("Verstappen", lap=20, dice_roll=1)
    assert result.replaced is True
    assert result.severity == FrontWingSeverity.SEVERE
    print(f"[OK] Severe damage always replaced: {result.message}")

    # Add minor damage (20% chance, threshold 9)
    manager.add_damage(
        driver="Hamilton",
        severity=FrontWingSeverity.MINOR,
        source="driver_error",
        lap=10,
    )

    # Test with high roll (should replace)
    result = manager.attempt_replacement("Hamilton", lap=20, dice_roll=10)
    assert result.replaced is True
    print(f"[OK] Minor damage with high roll replaced: {result.message}")

    # Add another minor damage
    manager.add_damage(
        driver="Leclerc",
        severity=FrontWingSeverity.MINOR,
        source="driver_error",
        lap=10,
    )

    # Test with low roll (should not replace)
    result = manager.attempt_replacement("Leclerc", lap=20, dice_roll=5)
    assert result.replaced is False
    print(f"[OK] Minor damage with low roll skipped: {result.message}")

    print()


def test_extra_time_calculation():
    """Test extra time calculation (second dice roll)"""
    print("=== Test: Extra Time Calculation ===")

    manager = FrontWingManager()

    # Add damage and replace with known dice rolls
    manager.add_damage(
        driver="Verstappen",
        severity=FrontWingSeverity.MODERATE,
        source="driver_error",
        lap=10,
    )

    # The extra time is calculated as: 4.5 + 0.1 * d10_roll
    # d10_roll ranges from 1-10, so extra time ranges from 4.6 to 5.5
    result = manager.attempt_replacement("Verstappen", lap=20, dice_roll=10)

    assert result.replaced is True
    assert (
        FRONT_WING_TIME_BASE
        <= result.total_time
        <= FRONT_WING_TIME_BASE + 0.1 * 10 + 0.01
    )
    print(
        f"[OK] Extra time calculated: {result.extra_time:.2f}s (base: {FRONT_WING_TIME_BASE}s)"
    )

    # Verify the formula
    expected_min = FRONT_WING_TIME_BASE + 0.1 * 1  # 4.6
    expected_max = FRONT_WING_TIME_BASE + 0.1 * 10  # 5.5
    print(f"  Expected range: {expected_min:.1f}s - {expected_max:.1f}s")

    print()


def test_configuration():
    """Test configuration values"""
    print("=== Test: Configuration Values ===")

    print("Replacement probabilities:")
    for severity, config in FRONT_WING_REPLACEMENT_CONFIG.items():
        print(
            f"  {severity.value}: {config['probability'] * 100:.0f}% (threshold d10 >= {config['threshold_d10']})"
        )

    print(f"\nTime calculation:")
    print(f"  Base time: {FRONT_WING_TIME_BASE}s")
    print(f"  Per d10: {FRONT_WING_TIME_PER_D10}s")
    print(
        f"  Range: {FRONT_WING_TIME_BASE + 0.1 * 1:.1f}s - {FRONT_WING_TIME_BASE + 0.1 * 10:.1f}s"
    )

    print()


def test_no_damage():
    """Test behavior when no damage exists"""
    print("=== Test: No Damage Behavior ===")

    manager = FrontWingManager()

    # Try to replace when no damage
    result = manager.attempt_replacement("Verstappen", lap=20)

    assert result.replaced is False
    assert result.total_time == 0.0
    assert "No front wing damage" in result.message
    print(f"[OK] No damage case handled: {result.message}")

    print()


def test_widelonso_skill_excluded():
    """Test that WIDELONSO skill damage does NOT create front wing damage"""
    print("=== Test: WIDELONSO Skill Excluded ===")

    manager = FrontWingManager()

    # Test WIDELONSO skill damage - should NOT create front wing damage
    damage = manager.create_damage_from_incident(
        driver="Alonso",
        incident_type="widelonso",
        incident_severity="moderate",
        lap=15,
    )
    assert damage is None
    print("[OK] WIDELONSO skill damage correctly excluded (returns None)")

    # Test widelonso_skill variant
    damage2 = manager.create_damage_from_incident(
        driver="Alonso",
        incident_type="widelonso_skill",
        incident_severity="major",
        lap=20,
    )
    assert damage2 is None
    print("[OK] WIDELONSO skill variant correctly excluded")

    # Verify Alonso CAN still get front wing damage from normal overtake_collision
    damage3 = manager.create_damage_from_incident(
        driver="Alonso",
        incident_type="overtake_collision",
        incident_severity="moderate",
        lap=25,
    )
    assert damage3 is not None
    assert damage3.severity == FrontWingSeverity.MODERATE
    print(f"[OK] Alonso normal overtake collision creates damage: {damage3.to_dict()}")

    print()


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FRONT WING REPLACEMENT SYSTEM TESTS")
    print("=" * 60 + "\n")

    try:
        test_configuration()
        test_front_wing_damage_creation()
        test_replacement_decision()
        test_extra_time_calculation()
        test_no_damage()
        test_widelonso_skill_excluded()

        print("=" * 60)
        print("ALL TESTS PASSED [OK]")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
