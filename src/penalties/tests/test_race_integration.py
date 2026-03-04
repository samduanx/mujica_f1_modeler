"""
Race Simulation Integration Test.

Tests the penalty system integrated with a simplified race scenario.
"""

import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import unittest

from src.penalties.integrators.race_simulation_integration import RacePenaltyIntegration
from src.incidents.incident_types import IncidentSeverity
from src.incidents.blue_flag import ResistanceLevel


class TestRacePenaltyIntegration(unittest.TestCase):
    """Test penalty integration with race simulation."""

    def setUp(self):
        self.integration = RacePenaltyIntegration("Spain", 2024)

    def test_overtake_collision_during_race(self):
        """Test handling overtake collision during race."""
        # Simulate an overtake collision at lap 10
        result = self.integration.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MODERATE,
            race_time=600.0,
            lap=10,
        )

        # Should have assessed penalty
        self.assertIsNotNone(result)
        self.assertEqual(result["driver_penalized"], "Verstappen")
        self.assertEqual(result["penalty"].points, 2)  # Moderate = 2 points

        # Check penalty points were tracked
        self.assertEqual(self.integration.penalty_points.get_points("Verstappen"), 2)

        # Check pending penalties
        pending = self.integration.penalty_manager.get_pending_penalties("Verstappen")
        self.assertEqual(len(pending), 1)

    def test_pit_stop_with_penalty_serving(self):
        """Test serving penalty at pit stop."""
        # First give a penalty
        self.integration.handle_overtake_collision(
            attacker="Leclerc",
            defender="Norris",
            severity=IncidentSeverity.MINOR,
            race_time=300.0,
            lap=5,
        )

        # Now simulate pit stop at lap 15
        base_pit_time = 22.0
        total_time, served = self.integration.handle_pit_stop_with_penalties(
            driver="Leclerc",
            lap=15,
            base_pit_time=base_pit_time,
            has_more_pit_stops=True,
        )

        # Should include penalty time (5s + overhead)
        self.assertGreater(total_time, base_pit_time + 5.0)
        self.assertLess(total_time, base_pit_time + 5.5)  # Max overhead 0.5s

        # Should have served the penalty
        self.assertEqual(len(served), 1)
        self.assertTrue(served[0].is_served)

        # No more pending penalties
        self.assertEqual(
            len(self.integration.penalty_manager.get_pending_penalties("Leclerc")), 0
        )

    def test_post_race_penalty_application(self):
        """Test penalties applied after race when not served."""
        # Give penalty
        self.integration.handle_overtake_collision(
            attacker="Russell",
            defender="Piastri",
            severity=IncidentSeverity.MINOR,
            race_time=400.0,
            lap=20,
        )

        # Don't serve at pit - simulate end of race
        post_race_time = self.integration.get_post_race_penalty_time("Russell")

        # Should have 5s penalty to add
        self.assertEqual(post_race_time, 5.0)

    def test_unsafe_release_during_race(self):
        """Test unsafe release gives time loss not penalty."""
        result = self.integration.handle_unsafe_release(
            involved_drivers=["Norris", "Piastri", "Sainz"],
            severity="moderate",
            race_time=500.0,
            lap=25,
        )

        # Should have time losses
        self.assertEqual(len(result["time_losses"]), 3)

        # Should have time losses in manager
        self.assertEqual(len(self.integration.penalty_manager.time_losses), 3)

        # But NO penalties (no points)
        self.assertEqual(
            len(self.integration.penalty_manager.get_pending_penalties("Norris")), 0
        )

        # No penalty points
        self.assertEqual(self.integration.penalty_points.get_points("Norris"), 0)

    def test_multiple_penalties_accumulate(self):
        """Test multiple penalties accumulate correctly."""
        # Give multiple penalties to same driver
        self.integration.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MINOR,
            race_time=300.0,
            lap=5,
        )

        self.integration.handle_overtake_collision(
            attacker="Verstappen",
            defender="Russell",
            severity=IncidentSeverity.MINOR,
            race_time=600.0,
            lap=10,
        )

        # Should have 2 pending penalties
        pending = self.integration.penalty_manager.get_pending_penalties("Verstappen")
        self.assertEqual(len(pending), 2)

        # Should have 2 penalty points (1 each)
        self.assertEqual(self.integration.penalty_points.get_points("Verstappen"), 2)

    def test_race_ban_threshold(self):
        """Test race ban at 12 points."""
        # Give lots of penalties
        for i in range(12):
            self.integration.handle_overtake_collision(
                attacker="TestDriver",
                defender=f"Driver{i}",
                severity=IncidentSeverity.MINOR,
                race_time=float(i * 100),
                lap=i + 1,
            )

        # Should trigger race ban
        banned = self.integration.check_race_bans()
        self.assertIn("TestDriver", banned)

    def test_penalties_summary(self):
        """Test getting penalties summary."""
        # Add various penalties
        self.integration.handle_overtake_collision(
            attacker="Hamilton",
            defender="Verstappen",
            severity=IncidentSeverity.MINOR,
            race_time=300.0,
            lap=5,
        )

        self.integration.handle_blue_flag_violation(
            driver="Sainz",
            resistance_level=ResistanceLevel.STRONG,
            offense_count=1,
            race_time=500.0,
            lap=15,
        )

        self.integration.handle_unsafe_release(
            involved_drivers=["Norris", "Piastri"],
            severity="minor",
            race_time=400.0,
            lap=12,
        )

        # Get summary
        summary = self.integration.get_penalties_summary()

        # Should have 2 penalties + 2 time losses
        self.assertEqual(summary["total_penalties"], 2)
        self.assertEqual(summary["total_time_losses"], 2)

        # Should have pending penalties
        self.assertEqual(summary["pending"], 2)

    def test_full_race_scenario(self):
        """Test a complete race scenario with multiple incidents."""
        # Lap 5: Overtake collision
        self.integration.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MODERATE,
            race_time=300.0,
            lap=5,
        )

        # Lap 10: Pit stop (serve penalty)
        pit_time, served = self.integration.handle_pit_stop_with_penalties(
            driver="Verstappen",
            lap=10,
            base_pit_time=22.0,
            has_more_pit_stops=True,
        )
        self.assertEqual(len(served), 1)

        # Lap 15: Unsafe release
        self.integration.handle_unsafe_release(
            involved_drivers=["Leclerc", "Norris"],
            severity="minor",
            race_time=900.0,
            lap=15,
        )

        # Lap 20: Another overtake collision
        self.integration.handle_overtake_collision(
            attacker="Russell",
            defender="Piastri",
            severity=IncidentSeverity.MINOR,
            race_time=1200.0,
            lap=20,
        )

        # Lap 25: Blue flag violation
        self.integration.handle_blue_flag_violation(
            driver="Gasly",
            resistance_level=ResistanceLevel.STRONG,
            offense_count=1,
            race_time=1500.0,
            lap=25,
        )

        # Verify final state
        # Verstappen: penalty served
        self.assertEqual(
            len(self.integration.penalty_manager.get_pending_penalties("Verstappen")), 0
        )

        # Russell: 1 pending penalty
        self.assertEqual(
            len(self.integration.penalty_manager.get_pending_penalties("Russell")), 1
        )

        # Gasly: 1 pending penalty
        self.assertEqual(
            len(self.integration.penalty_manager.get_pending_penalties("Gasly")), 1
        )

        # Time losses exist for Leclerc and Norris
        self.assertEqual(self.integration.get_total_time_loss("Leclerc") > 0, True)
        self.assertEqual(self.integration.get_total_time_loss("Norris") > 0, True)

        # Post-race penalties for Russell and Gasly
        self.assertEqual(self.integration.get_post_race_penalty_time("Russell"), 5.0)
        self.assertEqual(self.integration.get_post_race_penalty_time("Gasly"), 5.0)


def run_tests():
    """Run all race integration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestRacePenaltyIntegration,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
