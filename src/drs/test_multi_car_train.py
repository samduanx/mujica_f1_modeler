# -*- coding: utf-8 -*-
"""
Test script for multi-car train detection functionality.

This tests the detect_multi_car_train function and MultiCarTrainDetector class
that were added to overtake_trigger.py.
"""

import sys

sys.path.insert(0, "src")

from drs.overtake_trigger import (
    detect_multi_car_train,
    MultiCarTrain,
    MultiCarTrainDetector,
    TimeIntervalOvertakeSystem,
)
from skills.skill_context import SkillContext
from skills.skill_types import SkillTrigger


def test_detect_multi_car_train_basic():
    """Test basic train detection."""
    print("=" * 60)
    print("Test 1: Basic train detection")
    print("=" * 60)

    # Create a 3-car train
    positions = [
        ("Verstappen", 0.0),
        ("Norris", 0.8),  # gap = 0.8s (within threshold)
        ("Leclerc", 1.6),  # gap = 0.8s (within threshold)
        ("Hamilton", 3.0),  # gap = 1.4s (outside train)
    ]

    trains = detect_multi_car_train(positions)

    assert len(trains) == 1, f"Expected 1 train, got {len(trains)}"
    assert trains[0].size == 3, f"Expected train size 3, got {trains[0].size}"
    assert trains[0].drivers == ["Verstappen", "Norris", "Leclerc"]
    assert trains[0].leader == "Verstappen"
    assert trains[0].tail == "Leclerc"

    print(f"[PASS] Detected {len(trains)} train(s)")
    print(f"  Train size: {trains[0].size}")
    print(f"  Drivers: {trains[0].drivers}")
    print(f"  Gaps: {trains[0].gaps}")
    print()


def test_detect_multi_car_train_multiple():
    """Test detection of multiple trains."""
    print("=" * 60)
    print("Test 2: Multiple trains detection")
    print("=" * 60)

    # Two separate trains
    positions = [
        ("Verstappen", 0.0),
        ("Norris", 0.7),  # gap = 0.7s
        ("Leclerc", 1.4),  # gap = 0.7s - end of first train
        ("Hamilton", 3.0),  # gap = 1.6s - gap too large
        ("Sainz", 3.5),  # gap = 0.5s - start of second train
        ("Russell", 4.0),  # gap = 0.5s
        ("Piastri", 4.8),  # gap = 0.8s
    ]

    trains = detect_multi_car_train(positions)

    assert len(trains) == 2, f"Expected 2 trains, got {len(trains)}"
    assert trains[0].size == 3, f"Expected first train size 3, got {trains[0].size}"
    assert trains[1].size == 4, f"Expected second train size 4, got {trains[1].size}"

    print(f"[PASS] Detected {len(trains)} train(s)")
    print(f"  Train 1: {trains[0].drivers}")
    print(f"  Train 2: {trains[1].drivers}")
    print()


def test_detect_multi_car_train_no_train():
    """Test when no trains exist."""
    print("=" * 60)
    print("Test 3: No train detection (gaps too large)")
    print("=" * 60)

    positions = [
        ("Verstappen", 0.0),
        ("Norris", 1.5),  # gap = 1.5s (too large)
        ("Leclerc", 3.0),  # gap = 1.5s (too large)
    ]

    trains = detect_multi_car_train(positions)

    assert len(trains) == 0, f"Expected 0 trains, got {len(trains)}"
    print("[PASS] No trains detected (as expected)")
    print()


def test_multi_car_train_detector():
    """Test the MultiCarTrainDetector class with caching."""
    print("=" * 60)
    print("Test 4: MultiCarTrainDetector with caching")
    print("=" * 60)

    detector = MultiCarTrainDetector()

    positions = [
        ("Verstappen", 0.0),
        ("Norris", 0.8),
        ("Leclerc", 1.6),
        ("Hamilton", 3.0),
    ]

    # First detection (lap 1)
    trains = detector.detect_trains(positions, current_lap=1)
    assert len(trains) == 1
    print("[PASS] First detection on lap 1")

    # Check driver membership
    assert detector.is_driver_in_train("Norris") == True
    assert detector.is_driver_in_train("Hamilton") == False
    print("[PASS] Driver membership checks work")

    # Check overtake in train
    assert detector.is_overtake_in_train("Norris", "Verstappen") == True
    assert detector.is_overtake_in_train("Leclerc", "Norris") == True
    assert detector.is_overtake_in_train("Hamilton", "Leclerc") == False
    print("[PASS] Overtake-in-train detection works")

    # Check cached result (should return same without recomputing)
    trains_cached = detector.detect_trains(positions, current_lap=1)
    assert len(trains_cached) == 1
    print("[PASS] Cache works correctly")

    # New lap should recompute
    new_positions = [
        ("Verstappen", 0.0),
        ("Norris", 1.5),  # gap now larger
        ("Leclerc", 3.0),
    ]
    trains_new = detector.detect_trains(new_positions, current_lap=2)
    assert len(trains_new) == 0, "Should have no trains with larger gaps"
    print("[PASS] New lap triggers recomputation")
    print()


def test_train_with_detector_class():
    """Test MultiCarTrain class methods."""
    print("=" * 60)
    print("Test 5: MultiCarTrain class methods")
    print("=" * 60)

    train = MultiCarTrain(drivers=["A", "B", "C", "D"], gaps=[0.5, 0.8, 0.9])

    assert train.size == 4
    assert train.leader == "A"
    assert train.tail == "D"
    assert train.contains_driver("B") == True
    assert train.contains_driver("Z") == False

    # Check consecutive attacker-defender pairs
    assert train.is_attacker_in_train("B", "A") == True  # B attacking A
    assert train.is_attacker_in_train("C", "B") == True  # C attacking B
    assert train.is_attacker_in_train("A", "B") == False  # Wrong order
    assert train.is_attacker_in_train("D", "A") == False  # Not consecutive

    print("[PASS] MultiCarTrain class works correctly")
    print(f"  Train: {train.drivers}")
    print(f"  Gaps: {train.gaps}")
    print()


def test_integration_with_overtake_system():
    """Test integration with TimeIntervalOvertakeSystem."""
    print("=" * 60)
    print("Test 6: Integration with TimeIntervalOvertakeSystem")
    print("=" * 60)

    system = TimeIntervalOvertakeSystem("Silverstone")

    positions = [
        ("Verstappen", 0.0),
        ("Norris", 0.8),
        ("Leclerc", 1.6),
        ("Hamilton", 3.0),
    ]

    # Update train detection
    trains = system.update_train_detection(positions, current_lap=1)
    assert len(trains) == 1
    print("[PASS] update_train_detection works")

    # Check if overtake is in train
    assert system.is_overtake_in_multi_car_train("Norris", "Verstappen") == True
    assert system.is_overtake_in_multi_car_train("Hamilton", "Leclerc") == False
    print("[PASS] is_overtake_in_multi_car_train works")

    # Check should_overtake returns train info
    should_overtake, reason, debug_info = system.should_overtake(
        current_time=100.0,
        lap=5,
        total_laps=52,
        in_drs_zone=True,
        gap_ahead=0.8,
        section_type="drs_zone",
        drivers_in_range=2,
        attacker_name="Norris",
        defender_name="Verstappen",
    )

    assert "is_in_multi_car_train" in debug_info
    assert debug_info["is_in_multi_car_train"] == True
    assert "train_info" in debug_info
    assert debug_info["train_info"] is not None
    print("[PASS] should_overtake includes train info in debug_info")
    print(f"  is_in_multi_car_train: {debug_info['is_in_multi_car_train']}")
    print(f"  train_info: {debug_info['train_info']}")
    print()


def test_skill_context():
    """Test SkillContext with is_in_multi_car_train flag."""
    print("=" * 60)
    print("Test 7: SkillContext with is_in_multi_car_train")
    print("=" * 60)

    context = SkillContext()
    assert context.is_in_multi_car_train == False

    context.is_in_multi_car_train = True
    assert context.is_in_multi_car_train == True

    print("[PASS] SkillContext has is_in_multi_car_train attribute")
    print()


def test_skill_trigger():
    """Test the new DEFENDING_MULTI_CAR_TRAIN trigger."""
    print("=" * 60)
    print("Test 8: DEFENDING_MULTI_CAR_TRAIN trigger")
    print("=" * 60)

    from skills.skill_types import SkillTrigger

    # Verify the trigger exists
    assert hasattr(SkillTrigger, "DEFENDING_MULTI_CAR_TRAIN")
    print("[PASS] SkillTrigger.DEFENDING_MULTI_CAR_TRAIN exists")
    print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MULTI-CAR TRAIN DETECTION TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_detect_multi_car_train_basic,
        test_detect_multi_car_train_multiple,
        test_detect_multi_car_train_no_train,
        test_multi_car_train_detector,
        test_train_with_detector_class,
        test_integration_with_overtake_system,
        test_skill_context,
        test_skill_trigger,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__} ERROR: {e}")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
