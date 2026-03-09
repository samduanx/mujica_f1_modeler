"""
Test full race weekend simulation with the updated skill system.
Tests both sprint weekends and normal weekends.
"""

import sys
import traceback
from main import run_race_weekend


def test_normal_weekend():
    """Test a normal weekend (no sprint) - Monaco"""
    print("\n" + "=" * 80)
    print("TEST 1: NORMAL WEEKEND (Monaco - No Sprint)")
    print("=" * 80)

    try:
        result = run_race_weekend(
            track_name="Monaco",
            seed=42,
        )

        print("\n" + "=" * 40)
        print("SESSION RESULTS SUMMARY:")
        print("=" * 40)

        for session_name, session_result in result.items():
            status = session_result.get("status", "unknown")
            print(f"\n{session_name.upper()}: {status}")

            if status == "completed":
                # Print key results
                if "race_result" in session_result:
                    race = session_result["race_result"]
                    if "final_positions" in race:
                        positions = race["final_positions"][:5]
                        print(f"  Top 5: {positions}")
                elif "qualifying_result" in session_result:
                    qual = session_result["qualifying_result"]
                    if "final_positions" in qual:
                        positions = qual["final_positions"][:5]
                        print(f"  Top 5: {positions}")

        print("\n" + "=" * 40)
        print("NORMAL WEEKEND TEST: PASSED")
        print("=" * 40)
        return True

    except Exception as e:
        print(f"\nERROR in normal weekend test: {e}")
        traceback.print_exc()
        return False


def test_sprint_weekend():
    """Test a sprint weekend - Austria"""
    print("\n" + "=" * 80)
    print("TEST 2: SPRINT WEEKEND (Austria - With Sprint)")
    print("=" * 80)

    try:
        result = run_race_weekend(
            track_name="Austria",
            seed=42,
        )

        print("\n" + "=" * 40)
        print("SESSION RESULTS SUMMARY:")
        print("=" * 40)

        for session_name, session_result in result.items():
            status = session_result.get("status", "unknown")
            print(f"\n{session_name.upper()}: {status}")

            if status == "completed":
                # Print key results
                if "race_result" in session_result:
                    race = session_result["race_result"]
                    if "final_positions" in race:
                        positions = race["final_positions"][:5]
                        print(f"  Top 5: {positions}")
                elif "sprint_result" in session_result:
                    sprint = session_result["sprint_result"]
                    if "final_positions" in sprint:
                        positions = sprint["final_positions"][:5]
                        print(f"  Top 5: {positions}")
                elif "qualifying_result" in session_result:
                    qual = session_result["qualifying_result"]
                    if "final_positions" in qual:
                        positions = qual["final_positions"][:5]
                        print(f"  Top 5: {positions}")

        print("\n" + "=" * 40)
        print("SPRINT WEEKEND TEST: PASSED")
        print("=" * 40)
        return True

    except Exception as e:
        print(f"\nERROR in sprint weekend test: {e}")
        traceback.print_exc()
        return False


def main():
    print("\n" + "#" * 80)
    print("# FULL WEEKEND SIMULATION TEST")
    print("# Testing skill activation fixes with complete race weekends")
    print("#" * 80)

    # Test 1: Normal weekend (no sprint)
    normal_passed = test_normal_weekend()

    # Test 2: Sprint weekend
    sprint_passed = test_sprint_weekend()

    # Summary
    print("\n" + "#" * 80)
    print("# TEST SUMMARY")
    print("#" * 80)
    print(f"Normal Weekend (Monaco): {'PASSED' if normal_passed else 'FAILED'}")
    print(f"Sprint Weekend (Austria): {'PASSED' if sprint_passed else 'FAILED'}")

    if normal_passed and sprint_passed:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
