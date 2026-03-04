"""
Penalty System Tests.

Comprehensive tests for the penalty system including:
- Penalty assessment and serving
- Penalty points tracking (Super Licence)
- Grid penalties
- Unsafe release time losses
- Integration with existing systems
"""

import sys
import os

# Add src to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import unittest
from datetime import datetime, timedelta

from src.penalties.penalty_types import (
    PenaltyType,
    PenaltyReason,
)
from src.penalties.penalty_manager import PenaltyManager
from src.penalties.penalty_points import PenaltyPoints, POINTS_FOR_RACE_BAN
from src.penalties.penalty_service import PenaltyService
from src.penalties.grid_penalty import GridPenaltyTracker
from src.penalties.reprimand import ReprimandTracker
from src.penalties.integrators.overtake_penalties import OvertakePenaltyHandler
from src.penalties.integrators.blue_flag_penalties import BlueFlagPenaltyHandler
from src.penalties.integrators.vsc_penalties import VSCViolationHandler
from src.penalties.integrators.incident_penalties import IncidentPenaltyHandler
from src.incidents.incident_types import IncidentSeverity
from src.incidents.blue_flag import ResistanceLevel


class TestPenaltyTypes(unittest.TestCase):
    """Test penalty type functionality."""

    def test_penalty_time_values(self):
        """Test that penalty types have correct time values."""
        self.assertEqual(PenaltyType.TIME_5S.time_seconds, 5.0)
        self.assertEqual(PenaltyType.TIME_10S.time_seconds, 10.0)
        self.assertEqual(PenaltyType.TIME_15S.time_seconds, 15.0)
        self.assertEqual(PenaltyType.DRIVE_THROUGH.time_seconds, 20.0)

    def test_penalty_default_points(self):
        """Test that penalty types have correct default points."""
        self.assertEqual(PenaltyType.TIME_5S.default_points, 1)
        self.assertEqual(PenaltyType.TIME_10S.default_points, 2)
        self.assertEqual(PenaltyType.DRIVE_THROUGH.default_points, 3)
        self.assertEqual(PenaltyType.GRID_DROP_5.default_points, 0)

    def test_is_served_at_pit(self):
        """Test which penalties are served at pit."""
        self.assertTrue(PenaltyType.TIME_5S.is_served_at_pit)
        self.assertTrue(PenaltyType.DRIVE_THROUGH.is_served_at_pit)
        self.assertFalse(PenaltyType.GRID_DROP_5.is_served_at_pit)


class TestPenaltyManager(unittest.TestCase):
    """Test penalty manager functionality."""

    def setUp(self):
        self.pm = PenaltyManager()

    def test_assess_penalty(self):
        """Test assessing a penalty."""
        penalty = self.pm.assess_penalty(
            driver="Hamilton",
            penalty_type=PenaltyType.TIME_5S,
            reason="Causing collision",
            time_assessed=100.0,
            lap_assessed=5,
            reason_enum=PenaltyReason.CAUSING_COLLISION,
        )

        self.assertEqual(penalty.driver, "Hamilton")
        self.assertEqual(penalty.penalty_type, PenaltyType.TIME_5S)
        self.assertEqual(penalty.points, 1)  # Default for TIME_5S
        self.assertFalse(penalty.is_served)

    def test_get_pending_penalties(self):
        """Test getting pending penalties."""
        # Add penalty
        self.pm.assess_penalty(
            driver="Verstappen",
            penalty_type=PenaltyType.TIME_10S,
            reason="Leaving track",
            time_assessed=200.0,
            lap_assessed=10,
        )

        # Check pending
        pending = self.pm.get_pending_penalties("Verstappen")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].penalty_type, PenaltyType.TIME_10S)

        # Check no penalties for other driver
        self.assertEqual(len(self.pm.get_pending_penalties("Hamilton")), 0)

    def test_serve_penalty(self):
        """Test serving a penalty."""
        penalty = self.pm.assess_penalty(
            driver="Leclerc",
            penalty_type=PenaltyType.TIME_5S,
            reason="Impeding",
            time_assessed=150.0,
            lap_assessed=8,
        )

        # Serve at pit
        result = self.pm.serve_penalty(
            driver="Leclerc",
            penalty_id=penalty.penalty_id,
            served_at="pit_stop",
            served_at_lap=15,
        )

        self.assertTrue(result)
        self.assertTrue(penalty.is_served)
        self.assertEqual(penalty.served_at, "pit_stop")
        self.assertEqual(len(self.pm.get_pending_penalties("Leclerc")), 0)

    def test_add_time_loss(self):
        """Test adding time loss for unsafe release."""
        tl = self.pm.add_time_loss(
            driver="Norris",
            seconds=3.5,
            reason="Unsafe release",
            time_assessed=50.0,
            lap_assessed=3,
        )

        self.assertEqual(tl.driver, "Norris")
        self.assertEqual(tl.seconds, 3.5)
        self.assertEqual(len(self.pm.time_losses), 1)

        # Should NOT be in pending penalties
        self.assertEqual(len(self.pm.get_pending_penalties("Norris")), 0)


class TestPenaltyPoints(unittest.TestCase):
    """Test penalty points (Super Licence) functionality."""

    def setUp(self):
        self.pp = PenaltyPoints()

    def test_add_and_get_points(self):
        """Test adding and retrieving penalty points."""
        self.pp.add_points("Hamilton", 3, "Causing collision")
        self.assertEqual(self.pp.get_points("Hamilton"), 3)

        self.pp.add_points("Hamilton", 2, "Unsafe release")
        self.assertEqual(self.pp.get_points("Hamilton"), 5)

    def test_check_race_ban(self):
        """Test race ban at 12 points."""
        # Add 11 points - no ban
        self.pp.add_points("Verstappen", 11, "Multiple incidents")
        self.assertFalse(self.pp.check_race_ban("Verstappen"))

        # Add 1 more point - triggers ban
        self.pp.add_points("Verstappen", 1, "Another incident")
        self.assertTrue(self.pp.check_race_ban("Verstappen"))

    def test_points_expiry(self):
        """Test that points expire after 12 months."""
        # Add points 13 months ago
        old_date = datetime.now() - timedelta(days=400)
        self.pp.add_points("Leclerc", 5, "Old incident", date_added=old_date)

        # Add recent points
        self.pp.add_points("Leclerc", 3, "Recent incident")

        # Only recent points should count
        self.assertEqual(self.pp.get_points("Leclerc"), 3)

        # Expire old points
        self.pp.expire_points()

        # After expiry, only 3 points remain
        self.assertEqual(self.pp.get_points("Leclerc"), 3)


class TestPenaltyService(unittest.TestCase):
    """Test penalty serving mechanics."""

    def setUp(self):
        self.ps = PenaltyService()

    def test_get_pit_stop_penalty_time(self):
        """Test calculating pit stop penalty time."""
        penalty = PenaltyManager().assess_penalty(
            driver="Test",
            penalty_type=PenaltyType.TIME_5S,
            reason="Test",
            time_assessed=0,
            lap_assessed=0,
        )

        # Pit stop time should be 5s + random(0-0.5)
        pit_time = self.ps.get_pit_stop_penalty_time(penalty)
        self.assertGreaterEqual(pit_time, 5.0)
        self.assertLessEqual(pit_time, 5.5)

    def test_get_post_race_penalty_time(self):
        """Test calculating post-race penalty time."""
        pm = PenaltyManager()
        penalty = pm.assess_penalty(
            driver="Test",
            penalty_type=PenaltyType.TIME_10S,
            reason="Test",
            time_assessed=0,
            lap_assessed=0,
        )

        # Post-race should be exactly 10s
        post_race_time = self.ps.get_post_race_penalty_time(penalty)
        self.assertEqual(post_race_time, 10.0)


class TestOvertakePenaltyHandler(unittest.TestCase):
    """Test overtake penalty handler."""

    def setUp(self):
        self.pm = PenaltyManager()
        self.handler = OvertakePenaltyHandler(self.pm)

    def test_overtake_collision_minor(self):
        """Test minor collision penalty."""
        result = self.handler.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MINOR,
            time=100.0,
            lap=5,
        )

        self.assertEqual(result["driver_penalized"], "Verstappen")
        self.assertEqual(result["penalty_type"], "5s_time_penalty")

        penalty = result["penalty"]
        self.assertEqual(penalty.points, 1)

    def test_overtake_collision_moderate(self):
        """Test moderate collision penalty."""
        result = self.handler.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MODERATE,
            time=100.0,
            lap=5,
        )

        self.assertEqual(result["penalty_type"], "10s_time_penalty")
        self.assertEqual(result["penalty"].points, 2)

    def test_overtake_collision_major(self):
        """Test major collision penalty."""
        result = self.handler.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MAJOR,
            time=100.0,
            lap=5,
        )

        self.assertEqual(result["penalty_type"], "drive_through")
        self.assertEqual(result["penalty"].points, 3)


class TestBlueFlagPenaltyHandler(unittest.TestCase):
    """Test blue flag penalty handler."""

    def setUp(self):
        self.pm = PenaltyManager()
        self.handler = BlueFlagPenaltyHandler(self.pm)

    def test_minor_resistance_warning(self):
        """Test minor resistance (no penalty on first offense)."""
        result = self.handler.handle_blue_flag_violation(
            driver="Russell",
            resistance_level=ResistanceLevel.MINOR,
            offense_count=1,
            time=50.0,
            lap=3,
        )

        # First minor offense = no penalty
        self.assertIsNone(result)

    def test_strong_resistance_penalty(self):
        """Test strong resistance (penalty on first offense)."""
        result = self.handler.handle_blue_flag_violation(
            driver="Russell",
            resistance_level=ResistanceLevel.STRONG,
            offense_count=1,
            time=50.0,
            lap=3,
        )

        # First strong resistance = 5s penalty
        self.assertEqual(result["penalty_type"], "5s_time_penalty")

    def test_violation_level_penalty(self):
        """Test violation level (drive-through)."""
        result = self.handler.handle_blue_flag_violation(
            driver="Russell",
            resistance_level=ResistanceLevel.VIOLATION,
            offense_count=1,
            time=50.0,
            lap=3,
        )

        self.assertEqual(result["penalty_type"], "drive_through")


class TestUnsafeRelease(unittest.TestCase):
    """Test unsafe release handling."""

    def setUp(self):
        self.pm = PenaltyManager()
        self.handler = IncidentPenaltyHandler(self.pm)

    def test_unsafe_release_time_loss(self):
        """Test that unsafe release gives time loss, not penalty."""
        result = self.handler.handle_unsafe_release(
            involved_drivers=["Norris", "Piastri", "Leclerc"],
            severity="minor",
            time=100.0,
            lap=5,
        )

        # Should affect all 3 drivers
        self.assertEqual(len(result["time_losses"]), 3)

        # Check no penalties were given
        for driver in ["Norris", "Piastri", "Leclerc"]:
            self.assertEqual(len(self.pm.get_pending_penalties(driver)), 0)

        # But time losses exist
        self.assertEqual(len(self.pm.time_losses), 3)

        # All time losses should be reasonable (1-2s for minor)
        for tl in result["time_losses"]:
            self.assertGreaterEqual(tl.seconds, 1.0)
            self.assertLessEqual(tl.seconds, 2.0)

    def test_unsafe_release_major(self):
        """Test major unsafe release (max 5s)."""
        result = self.handler.handle_unsafe_release(
            involved_drivers=["Hamilton"],
            severity="major",
            time=100.0,
            lap=5,
        )

        # Major = exactly 5 seconds
        self.assertEqual(result["time_losses"][0].seconds, 5.0)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components."""

    def test_full_race_penalty_flow(self):
        """Test a complete race scenario with multiple penalties."""
        # Setup
        pm = PenaltyManager()
        pp = PenaltyPoints()
        ps = PenaltyService()

        # Race scenario 1: Overtake collision
        overtake_handler = OvertakePenaltyHandler(pm)
        result = overtake_handler.handle_overtake_collision(
            attacker="Verstappen",
            defender="Hamilton",
            severity=IncidentSeverity.MODERATE,
            time=150.0,
            lap=10,
        )
        penalty = result["penalty"]
        pp.add_points(penalty.driver, penalty.points, "Overtake collision")

        # Race scenario 2: Unsafe release (time loss, no penalty)
        incident_handler = IncidentPenaltyHandler(pm)
        incident_handler.handle_unsafe_release(
            involved_drivers=["Norris", "Piastri"],
            severity="minor",
            time=300.0,
            lap=20,
        )

        # Race scenario 3: Blue flag violation
        blue_flag_handler = BlueFlagPenaltyHandler(pm)
        blue_flag_result = blue_flag_handler.handle_blue_flag_violation(
            driver="Russell",
            resistance_level=ResistanceLevel.STRONG,
            offense_count=1,
            time=500.0,
            lap=35,
        )
        # Add points from blue flag penalty
        if blue_flag_result:
            pp.add_points(
                "Russell", blue_flag_result["penalty"].points, "Blue flag violation"
            )

        # Check totals
        self.assertEqual(len(pm.penalties), 2)  # Overtake + Blue flag
        self.assertEqual(len(pm.time_losses), 2)  # Norris + Piastri
        self.assertEqual(pp.get_points("Verstappen"), 2)  # Moderate collision
        self.assertEqual(pp.get_points("Russell"), 1)  # Blue flag
        self.assertEqual(pp.get_points("Hamilton"), 0)  # No penalties

        # Serve penalty at pit stop
        pending = pm.get_pending_penalties("Verstappen")
        pit_time, served = ps.serve_penalties_at_pit(pending)
        
        # Mark them as served in the penalty manager
        for p in served:
            pm.serve_penalty(
                driver=p.driver,
                penalty_id=p.penalty_id,
                served_at="pit_stop",
            )
        
        # Verify penalties were served
        self.assertTrue(all(p.is_served for p in served))


def run_tests():
    """Run all penalty system tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestPenaltyTypes,
        TestPenaltyManager,
        TestPenaltyPoints,
        TestPenaltyService,
        TestOvertakePenaltyHandler,
        TestBlueFlagPenaltyHandler,
        TestUnsafeRelease,
        TestIntegration,
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
