"""
Test script for narrative assistance functionality.

Run this to verify the injection system is working correctly.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.narrative_assist import NarrativeAssistConfig, ProbabilityBalancer


def test_config():
    """Test configuration loading."""
    print("=== Testing NarrativeAssistConfig ===")

    # Test without environment variables
    config = NarrativeAssistConfig()
    config._initialized = False  # Reset for testing
    config._load_from_environment()

    print(f"Enabled: {config.enabled}")
    print(f"Target Team: {config.target_team}")

    # Test with environment variables
    os.environ["F1_NARRATIVE_ASSIST"] = "moderate"
    os.environ["F1_ASSIST_TARGET"] = "Ferrari"

    config._initialized = False
    config._load_from_environment()

    print(f"\nWith env vars:")
    print(f"Enabled: {config.enabled}")
    print(f"Intensity: {config.intensity}")
    print(f"Target Team: {config.target_team}")
    print(f"Probability Shift: {config.probability_shift}")
    print(f"Adversity Reduction: {config.adversity_reduction}")

    # Cleanup
    del os.environ["F1_NARRATIVE_ASSIST"]
    del os.environ["F1_ASSIST_TARGET"]

    print("\nConfig test PASSED\n")


def test_dice_distribution():
    """Test weighted dice distribution."""
    print("=== Testing Weighted Dice Distribution ===")

    # Enable assistance
    os.environ["F1_NARRATIVE_ASSIST"] = "moderate"
    os.environ["F1_ASSIST_TARGET"] = "Ferrari"

    balancer = ProbabilityBalancer()

    # Roll many times and count distribution
    rolls = []
    for _ in range(1000):
        roll = balancer.generate_weighted_d20("Ferrari")
        rolls.append(roll)

    # Count distribution
    distribution = {}
    for i in range(1, 21):
        distribution[i] = rolls.count(i)

    print("Roll distribution (1000 rolls for Ferrari with moderate assist):")
    print("-" * 50)

    for i in range(1, 21):
        count = distribution[i]
        percentage = count / 10
        bar = "█" * int(percentage / 2)
        print(f"{i:2d}: {count:4d} ({percentage:5.1f}%) {bar}")

    # Calculate averages
    avg_roll = sum(rolls) / len(rolls)
    print(f"\nAverage roll: {avg_roll:.2f}")
    print(f"Expected average (fair): 10.5")
    print(f"Expected average (moderate): ~12-13")

    # Cleanup
    del os.environ["F1_NARRATIVE_ASSIST"]
    del os.environ["F1_ASSIST_TARGET"]

    if avg_roll > 11:
        print("\nDice distribution test PASSED\n")
    else:
        print("\nDice distribution test FAILED - average too low\n")


def test_team_filtering():
    """Test that only target team gets assistance."""
    print("=== Testing Team Filtering ===")

    os.environ["F1_NARRATIVE_ASSIST"] = "strong"
    os.environ["F1_ASSIST_TARGET"] = "Ferrari"

    balancer = ProbabilityBalancer()

    # Ferrari should get assistance
    ferrari_rolls = [balancer.generate_weighted_d20("Ferrari") for _ in range(100)]
    ferrari_avg = sum(ferrari_rolls) / len(ferrari_rolls)

    # Mercedes should not get assistance
    mercedes_rolls = [balancer.generate_weighted_d20("Mercedes") for _ in range(100)]
    mercedes_avg = sum(mercedes_rolls) / len(mercedes_rolls)

    print(f"Ferrari average (should be high): {ferrari_avg:.2f}")
    print(f"Mercedes average (should be ~10.5): {mercedes_avg:.2f}")

    # Cleanup
    del os.environ["F1_NARRATIVE_ASSIST"]
    del os.environ["F1_ASSIST_TARGET"]

    if ferrari_avg > mercedes_avg + 1:
        print("\nTeam filtering test PASSED\n")
    else:
        print("\nTeam filtering test FAILED\n")


def test_error_reduction():
    """Test error probability reduction."""
    print("=== Testing Error Probability Reduction ===")

    os.environ["F1_NARRATIVE_ASSIST"] = "moderate"
    os.environ["F1_ASSIST_TARGET"] = "Ferrari"

    balancer = ProbabilityBalancer()

    base_prob = 0.05  # 5% error rate

    ferrari_prob = balancer.balance_error_probability(base_prob, "Ferrari")
    mercedes_prob = balancer.balance_error_probability(base_prob, "Mercedes")

    print(f"Base error probability: {base_prob:.3f}")
    print(f"Ferrari error probability: {ferrari_prob:.3f}")
    print(f"Mercedes error probability: {mercedes_prob:.3f}")
    print(f"Reduction for Ferrari: {(1 - ferrari_prob / base_prob) * 100:.1f}%")

    # Cleanup
    del os.environ["F1_NARRATIVE_ASSIST"]
    del os.environ["F1_ASSIST_TARGET"]

    if ferrari_prob < mercedes_prob:
        print("\nError reduction test PASSED\n")
    else:
        print("\nError reduction test FAILED\n")


if __name__ == "__main__":
    print("Narrative Assistance System Test Suite")
    print("=" * 50)
    print()

    test_config()
    test_dice_distribution()
    test_team_filtering()
    test_error_reduction()

    print("=" * 50)
    print("All tests completed!")
