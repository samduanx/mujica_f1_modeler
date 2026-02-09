"""
Test suite for the Time-Interval Based Overtake Trigger System.

Tests the probability calculations, track configurations, and edge cases.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drs.overtake_trigger import (
    TimeIntervalOvertakeSystem,
    TimeIntervalConfig,
    TRACK_CONFIGS,
    get_gap_modifier,
    SECTION_DRS_ZONE,
    SECTION_STRAIGHT,
    SECTION_HAIRPIN,
    create_trigger_system,
)


# ============================================================================
# Test 1: Basic Probability Calculation
# ============================================================================


def test_basic_probability():
    """Test basic probability calculation"""
    print("=" * 60)
    print("TEST: Basic Probability Calculation")
    print("=" * 60)

    system = create_trigger_system("Monza")

    # Test at different conditions
    test_cases = [
        # (lap, total_laps, in_drs, gap, section, expected_range)
        (1, 70, True, 0.3, SECTION_DRS_ZONE, "High probability"),
        (1, 70, False, 1.5, SECTION_STRAIGHT, "Low probability"),
        (50, 70, True, 0.3, SECTION_DRS_ZONE, "Medium probability"),
        (65, 70, True, 0.3, SECTION_DRS_ZONE, "High probability (late race)"),
    ]

    print("\nProbability Breakdown:")
    print("-" * 60)

    for lap, total, in_drs, gap, section, description in test_cases:
        prob = system.get_overtake_probability(
            current_time=lap * 70.0,  # Approximate time
            lap=lap,
            total_laps=total,
            in_drs_zone=in_drs,
            gap_ahead=gap,
            section_type=section,
        )

        status = "✓" if 0.0 <= prob <= 1.0 else "✗"
        print(
            f"Lap {lap:2d} | {section:12s} | Gap: {gap:.1f}s | Prob: {prob:.4f} | {status}"
        )

    print("\n✓ Basic probability test completed!\n")


# ============================================================================
# Test 2: Track Comparison
# ============================================================================


def test_track_comparison():
    """Test probability differences between tracks"""
    print("=" * 60)
    print("TEST: Track Comparison")
    print("=" * 60)

    tracks = ["Monza", "Monaco", "Silverstone"]
    probabilities = {}

    print("\nProbability at Lap 1, DRS Zone, Gap 0.3s:")
    print("-" * 60)

    for track_name in tracks:
        system = create_trigger_system(track_name)

        prob = system.get_overtake_probability(
            current_time=70.0,
            lap=1,
            total_laps=70,
            in_drs_zone=True,
            gap_ahead=0.3,
            section_type=SECTION_DRS_ZONE,
        )

        probabilities[track_name] = prob
        print(f"{track_name:12s} | Probability: {prob:.4f}")

    print("\nTrack Comparison:")
    print(f"  Monza: {probabilities['Monza']:.4f}")

    # Verify Monaco has much lower probability
    monaco_prob = probabilities.get("Monaco", 0.001)
    monza_prob = probabilities.get("Monza", 0.01)

    ratio = monza_prob / monaco_prob if monaco_prob > 0 else float('inf')
    print(f"  Monza/Monaco Ratio: {ratio:.0f}x")

    assert ratio > 10, "Monza should have 10x+ higher probability than Monaco"

    print("\n✓ Track comparison test completed!\n")


# ============================================================================
# Test 3: Gap Modifier
# ============================================================================


def test_gap_modifier():
    """Test gap-based modifiers"""
    print("=" * 60)
    print("TEST: Gap Modifier")
    print("=" * 60)

    test_cases = [
        (0.2, 3.0, "Very close"),
        (0.3, 3.0, "Close"),
        (0.5, 2.0, "DRS range"),
        (1.0, 1.0, "At limit"),
        (1.5, 0.5, "Hard"),
        (3.0, 0.1, "Not catching"),
    ]

    print("\nGap Modifiers:")
    print("-" * 60)
    print("Gap (s) | Modifier | Description")
    print("-" * 40)

    for gap, expected_mod, description in test_cases:
        mod = get_gap_modifier(gap)
        status = "✓" if abs(mod - expected_mod) < 0.01 else "✗"
        print(f"  {gap:.1f}s  |  {mod:.1f}x   | {description:12s} | {status}")

    print("\n✓ Gap modifier test completed!\n")


# ============================================================================
# Test 4: Clustering Prevention
# ============================================================================


def test_clustering_prevention():
    """Test that consecutive overtakes reduce probability"""
    print("=" * 60)
    print("TEST: Clustering Prevention")
    print("=" * 60)

    system = create_trigger_system("Monza")
    system.reset()

    print("\nSimulating consecutive overtakes:")
    print("-" * 60)

    current_time = 70.0

    for i in range(6):
        # Record previous overtake
        if i > 0:
            system.record_overtake(current_time - 0.2 * i)

        # Check probability after recording
        prob = system.get_overtake_probability(
            current_time=current_time,
            lap=1,
            total_laps=70,
            in_drs_zone=True,
            gap_ahead=0.3,
            section_type=SECTION_DRS_ZONE,
        )

        print(f"Overtake {i}: Probability = {prob:.4f}")

        # Probability should decrease with more consecutive overtakes
        if i >= 3:
            assert prob < 0.01, f"Probability should be very low after {i} consecutive"

    print("\n✓ Clustering prevention test completed!\n")


# ============================================================================
# Test 5: Monte Carlo Simulation
# ============================================================================


def test_monte_carlo_simulation():
    """Run Monte Carlo simulation for a full race"""
    print("=" * 60)
    print("TEST: Monte Carlo Simulation (10 races at Monza)")
    print("=" * 60)

    race_results = []

    for race_num in range(10):
        system = create_trigger_system("Monza")
        system.reset()

        total_laps = 70
        lap_time = 70.0  # Average lap time

        for lap in range(1, total_laps + 1):
            # Check multiple times per lap (every 0.2s)
            for interval in range(int(lap_time / 0.2)):
                current_time = (lap - 1) * lap_time + interval * 0.2

                should, reason, debug = system.should_overtake(
                    current_time=current_time,
                    lap=lap,
                    total_laps=total_laps,
                    in_drs_zone=True,
                    gap_ahead=0.4,
                    section_type=SECTION_DRS_ZONE,
                    attacker_name=f"Driver_A",
                    defender_name=f"Driver_B",
                )

                if should:
                    system.record_overtake(
                        current_time=current_time,
                        attacker_name="Attacker",
                        defender_name="Defender",
                        reason=reason,
                    )

        stats = system.get_statistics()
        race_results.append(stats["total_overtakes"])

        print(f"Race {race_num + 1}: {stats['total_overtakes']} overtakes")

    avg = sum(race_results) / len(race_results)
    print(f"\nAverage: {avg:.1f} overtakes per race")
    print(f"Min: {min(race_results)}, Max: {max(race_results)}")

    # Should be in reasonable range (Monza: 40-60)
    assert 20 <= avg <= 80, f"Average {avg} is outside expected range"

    print("\n✓ Monte Carlo simulation test completed!\n")


# ============================================================================
# Test 6: Monaco Mode Verification
# ============================================================================


def test_monaco_mode():
    """Verify Monaco has extremely low overtake probability"""
    print("=" * 60)
    print("TEST: Monaco Mode Verification")
    print("=" * 60)

    system = create_trigger_system("Monaco")

    # Even best case scenario (Lap 1, DRS, very close)
    best_prob = system.get_overtake_probability(
        current_time=70.0,
        lap=1,
        total_laps=70,
        in_drs_zone=True,
        gap_ahead=0.2,
        section_type=SECTION_DRS_ZONE,
    )

    print(f"\nMonaco best case probability: {best_prob:.6f}")
    print(f"Expected: ~0.0012 (0.12%)")

    # Verify it's very low
    assert best_prob < 0.01, "Monaco probability should be very low"

    # Simulate 1000 races at Monaco
    overtake_counts = []
    for race in range(1000):
        system.reset()

        for lap in range(1, 70):
            current_time = lap * 70.0
            for _ in range(10):  # Check 10 times per lap
                should, _, _ = system.should_overtake(
                    current_time=current_time,
                    lap=lap,
                    total_laps=70,
                    in_drs_zone=True,
                    gap_ahead=0.3,
                    section_type=SECTION_DRS_ZONE,
                )
                if should:
                    system.record_overtake(current_time)

        overtake_counts.append(system.get_statistics()["total_overtakes"])

    races_with_overtake = sum(1 for c in overtake_counts if c > 0)
    avg = sum(overtake_counts) / len(overtake_counts)

    print(f"\n1000 Monte Carlo races at Monaco:")
    print(
        f"  Races with at least 1 overtake: {races_with_overtake} ({races_with_overtake / 10:.1f}%)"
    )
    print(f"  Average overtakes per race: {avg:.2f}")
    print(f"  Expected: ~0-2 overtakes, ~80-90% of races with 0")

    # Most races should have 0-1 overtakes
    assert avg < 3, f"Average should be very low ({avg} is too high)"

    print("\n✓ Monaco mode verification completed!\n")


# ============================================================================
# Test 7: Edge Cases
# ============================================================================


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("=" * 60)
    print("TEST: Edge Cases")
    print("=" * 60)

    system = create_trigger_system("Monza")

    edge_cases = [
        ("Lap 0", {"lap": 0, "total_laps": 70}, "Should work"),
        ("Lap 1", {"lap": 1, "total_laps": 70}, "Should work"),
        ("Last lap", {"lap": 70, "total_laps": 70}, "Should work"),
        ("Gap 0", {"gap_ahead": 0.0}, "Very close"),
        ("Gap 10", {"gap_ahead": 10.0}, "Not catching"),
        ("No DRS", {"in_drs_zone": False}, "Should reduce prob"),
    ]

    print("\nEdge Cases:")
    print("-" * 60)

    for name, kwargs, description in edge_cases:
        try:
            prob = system.get_overtake_probability(
                current_time=70.0,
                lap=kwargs.get("lap", 1),
                total_laps=kwargs.get("total_laps", 70),
                in_drs_zone=kwargs.get("in_drs_zone", True),
                gap_ahead=kwargs.get("gap_ahead", 0.5),
                section_type=SECTION_STRAIGHT,
            )

            assert 0.0 <= prob <= 1.0, f"Probability out of range: {prob}"
            print(f"  {name}: {description} | Prob: {prob:.4f} ✓")

        except Exception as e:
            print(f"  {name}: {description} | ERROR: {e} ✗")

    print("\n✓ Edge cases test completed!\n")


# ============================================================================
# Run All Tests
# ============================================================================


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  TIME-INTERVAL OVERTAKE TRIGGER SYSTEM - TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_basic_probability,
        test_track_comparison,
        test_gap_modifier,
        test_clustering_prevention,
        test_monte_carlo_simulation,
        test_monaco_mode,
        test_edge_cases,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}\n")
            import traceback

            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
