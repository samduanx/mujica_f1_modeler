"""
Test suite for the Confronting Dice Overtake System.

Tests the OvertakeConfrontation class and narrative generation.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drs.overtake import OvertakeConfrontation, OvertakeSituation, ConfrontationResult
from drs.driver_state import DriverRaceState
from drs.narrative import generate_confrontation_narrative


def create_test_driver(
    name: str,
    r_value: float,
    dr_value: int,
    position: int = 1,
    drs_available: bool = False,
) -> DriverRaceState:
    """Create a test driver for overtake testing"""
    driver = DriverRaceState(
        name=name,
        r_value=r_value,
        dr_value=dr_value,
        grid_position=position,
        position=position,
        drs_available=drs_available,
    )
    driver.tyre_degradation = 1.0  # Fresh tires by default
    return driver


def test_drs_zone_confrontation():
    """Test DRS zone confrontation"""
    print("=" * 60)
    print("TEST: DRS Zone Confrontation")
    print("=" * 60)

    # Create test drivers
    attacker = create_test_driver("Verstappen", 310.0, 92, 1, drs_available=True)
    defender = create_test_driver("Norris", 308.0, 88, 2, drs_available=False)

    # Resolve confrontation
    confrontation = OvertakeConfrontation()
    result = confrontation.resolve(
        attacker=attacker, defender=defender, situation=OvertakeSituation.IN_DRS_ZONE
    )

    # Generate narrative
    narrative = generate_confrontation_narrative(
        result, "Verstappen", "Norris", "DRS Zone Battle"
    )

    print(narrative)
    print()

    # Verify structure
    assert isinstance(result, ConfrontationResult)
    assert result.winner in ["attacker", "defender", "tie"]
    assert result.attacker_roll >= 1 and result.attacker_roll <= 10
    assert result.defender_roll >= 1 and result.defender_roll <= 10
    assert "DR" in result.attacker_modifiers
    assert "DRS_Bonus" in result.attacker_modifiers

    print("✓ Test passed!\n")


def test_end_of_drs_zone_confrontation():
    """Test end of DRS zone confrontation (corner entry)"""
    print("=" * 60)
    print("TEST: End of DRS Zone - Corner Entry")
    print("=" * 60)

    # Create test drivers
    attacker = create_test_driver("Leclerc", 305.2, 85, 3)
    defender = create_test_driver("Sainz", 304.5, 82, 5)

    # Resolve confrontation
    confrontation = OvertakeConfrontation()
    result = confrontation.resolve(
        attacker=attacker,
        defender=defender,
        situation=OvertakeSituation.END_OF_DRS_ZONE,
    )

    # Generate narrative
    narrative = generate_confrontation_narrative(
        result, "Leclerc", "Sainz", "Monaco Hairpin Battle"
    )

    print(narrative)
    print()

    # Verify structure
    assert isinstance(result, ConfrontationResult)
    assert "DR" in result.attacker_modifiers
    assert "Corner_Exit" in result.attacker_modifiers or "Corner" in str(
        result.attacker_modifiers
    )
    assert "Line" in result.defender_modifiers

    print("✓ Test passed!\n")


def test_elsewhere_confrontation():
    """Test non-DRS confrontation"""
    print("=" * 60)
    print("TEST: Elsewhere - Non-DRS Battle")
    print("=" * 60)

    # Create test drivers
    attacker = create_test_driver("Hamilton", 307.5, 88, 4)
    defender = create_test_driver("Russell", 305.8, 84, 6)

    # Resolve confrontation
    confrontation = OvertakeConfrontation()
    result = confrontation.resolve(
        attacker=attacker, defender=defender, situation=OvertakeSituation.ELSEWHERE
    )

    # Generate narrative
    narrative = generate_confrontation_narrative(
        result, "Hamilton", "Russell", "Midfield Battle"
    )

    print(narrative)
    print()

    # Verify structure
    assert isinstance(result, ConfrontationResult)
    assert "DR" in result.attacker_modifiers
    assert (
        "Precision" in result.attacker_modifiers
        or "Experience" in result.attacker_modifiers
    )

    print("✓ Test passed!\n")


def test_push_mechanic():
    """Test push mechanic after near-miss"""
    print("=" * 60)
    print("TEST: Push Mechanic")
    print("=" * 60)

    # Create test drivers - make it close
    attacker = create_test_driver("Alonso", 302.0, 90, 8)
    defender = create_test_driver("Piastri", 303.5, 80, 7)

    # Force close battle by setting up conditions
    confrontation = OvertakeConfrontation()

    # First confrontation
    result = confrontation.resolve(
        attacker=attacker, defender=defender, situation=OvertakeSituation.IN_DRS_ZONE
    )

    print(f"Initial Result: {result.winner} wins by {result.margin:.1f}")
    print(f"Push available: {result.push_available}")

    if result.push_available:
        # Execute push
        push_result = confrontation.execute_push(result)

        push_narrative = f"""
        ════════════════════════════════════════════════════════
        PUSH EXECUTED!
        ════════════════════════════════════════════════════════
        Push Roll: {push_result.push_roll}
        New Total: {push_result.attacker_total:.1f} (was {result.attacker_total:.1f})
        Result: {push_result.push_result.upper() if push_result.push_result else 'N/A'}
        Tyre Penalty Applied: {push_result.tyre_penalty_applied}
        """
        print(push_narrative)

    print("✓ Push test completed!\n")


def test_dr_modifier_calculation():
    """Test DR modifier calculations"""
    print("=" * 60)
    print("TEST: DR Modifier Calculations")
    print("=" * 60)

    confrontation = OvertakeConfrontation()

    # Test various DR values
    test_cases = [
        (80, -5.0),  # Novice
        (82, -4.0),  # Below Average
        (84, -2.0),  # Average-
        (86, 0.0),  # Average
        (88, 2.0),  # Good
        (90, 4.0),  # Excellent
        (92, 6.0),  # Elite
    ]

    print("DR Value | Modifier | Expected | Match")
    print("-" * 50)

    for dr, expected in test_cases:
        modifier = confrontation._get_dr_modifier(dr)
        match = "✓" if abs(modifier - expected) < 0.01 else "✗"
        print(f"   {dr}    |  {modifier:+.1f}   |   {expected:+.1f}    | {match}")

    print("\n✓ DR modifier test completed!\n")


def test_multiple_confrontations():
    """Run multiple confrontations to test randomness"""
    print("=" * 60)
    print("TEST: Multiple Confrontations (Monte Carlo)")
    print("=" * 60)

    attacker = create_test_driver("Verstappen", 310.0, 92, 1, drs_available=True)
    defender = create_test_driver("Norris", 308.0, 88, 2, drs_available=False)

    confrontation = OvertakeConfrontation()

    # Run 20 confrontations
    wins = {"attacker": 0, "defender": 0, "tie": 0}

    for i in range(20):
        result = confrontation.resolve(
            attacker=attacker,
            defender=defender,
            situation=OvertakeSituation.IN_DRS_ZONE,
        )
        wins[result.winner] += 1

    print("Results over 20 confrontations:")
    print(f"  Attacker wins: {wins['attacker']} ({wins['attacker'] / 20 * 100:.0f}%)")
    print(f"  Defender wins: {wins['defender']} ({wins['defender'] / 20 * 100:.0f}%)")
    print(f"  Ties:          {wins['tie']} ({wins['tie'] / 20 * 100:.0f}%)")
    print()

    # Attacker should win most with DR 92 vs DR 88 and DRS
    assert wins["attacker"] >= 10, "Attacker should win most confrontations"

    print("✓ Monte Carlo test passed!\n")


def test_full_confrontation_scenario():
    """Test a full race scenario with multiple overtake attempts"""
    print("=" * 60)
    print("TEST: Full Race Scenario")
    print("=" * 60)

    # Create a grid of drivers
    drivers = [
        ("Verstappen", 310.0, 92, 1, True),  # P1 with DRS
        ("Norris", 308.0, 88, 2, False),  # P2 no DRS
        ("Leclerc", 305.2, 85, 3, True),  # P3 with DRS
        ("Hamilton", 307.5, 88, 4, False),  # P4 no DRS
        ("Sainz", 304.5, 82, 5, True),  # P5 with DRS
        ("Russell", 305.8, 84, 6, False),  # P6 no DRS
    ]

    driver_objs = {}
    for name, r, dr, pos, drs in drivers:
        driver_objs[name] = create_test_driver(name, r, dr, pos, drs)

    confrontation = OvertakeConfrontation()

    print("Overtake Attempts:")
    print("-" * 60)

    # Test various matchups
    matchups = [
        ("Verstappen", "Norris", OvertakeSituation.IN_DRS_ZONE, "DRS Zone Battle"),
        ("Leclerc", "Hamilton", OvertakeSituation.END_OF_DRS_ZONE, "Corner Entry"),
        ("Sainz", "Russell", OvertakeSituation.ELSEWHERE, "Midfield Battle"),
        ("Hamilton", "Sainz", OvertakeSituation.IN_DRS_ZONE, "Pursuit Battle"),
    ]

    for attacker_name, defender_name, situation, desc in matchups:
        attacker = driver_objs[attacker_name]
        defender = driver_objs[defender_name]

        result = confrontation.resolve(
            attacker=attacker, defender=defender, situation=situation
        )

        print(f"\n{desc}")
        print(
            f"  {attacker_name} ({result.attacker_total:.1f}) vs {defender_name} ({result.defender_total:.1f})"
        )
        print(f"  Winner: {result.winner.upper()} (margin: {result.margin:.1f})")

    print("\n✓ Full scenario test passed!\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  CONFRONTING DICE OVERTAKE SYSTEM - TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_dr_modifier_calculation,
        test_drs_zone_confrontation,
        test_end_of_drs_zone_confrontation,
        test_elsewhere_confrontation,
        test_push_mechanic,
        test_multiple_confrontations,
        test_full_confrontation_scenario,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}\n")
            return False

    print("=" * 60)
    print("  ALL TESTS PASSED!")
    print("=" * 60 + "\n")

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
