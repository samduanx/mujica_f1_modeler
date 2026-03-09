"""
Qualifying System Tests

Basic tests for the qualification system components.
"""

import unittest
from src.qualifying.types import (
    QualifyingSessionType,
    QualifyingResult,
    QualifyingSessionState,
    QualifyingIncident,
    TyreAllocation,
    FlagState,
)
from src.qualifying.tyre_allocation import TyreAllocationManager
from src.qualifying.session import QualifyingSessionManager
from src.qualifying.incident_handler import QualifyingIncidentHandler, roll_d100
from src.qualifying.weather_handler import QualifyingWeatherHandler


class TestTyreAllocationManager(unittest.TestCase):
    """Test tyre allocation manager."""

    def test_standard_allocation(self):
        """Test standard qualifying tyre allocation."""
        manager = TyreAllocationManager(QualifyingSessionType.STANDARD)
        manager.initialize_driver("Verstappen")

        remaining = manager.get_remaining_tyres("Verstappen")
        self.assertEqual(remaining["SOFT"], 8)
        self.assertEqual(remaining["MEDIUM"], 3)
        self.assertEqual(remaining["HARD"], 2)

    def test_sprint_allocation(self):
        """Test sprint qualifying tyre allocation."""
        manager = TyreAllocationManager(QualifyingSessionType.SPRINT)
        manager.initialize_driver("Hamilton")

        remaining = manager.get_remaining_tyres("Hamilton")
        self.assertEqual(remaining["SOFT"], 6)
        self.assertEqual(remaining["MEDIUM"], 4)
        self.assertEqual(remaining["HARD"], 2)

    def test_tyre_usage(self):
        """Test using tyre sets."""
        manager = TyreAllocationManager(QualifyingSessionType.STANDARD)
        manager.initialize_driver("Leclerc")

        # Use a soft tyre
        result = manager.use_tyre_set("Leclerc", "SOFT", "Q1")
        self.assertTrue(result)

        remaining = manager.get_remaining_tyres("Leclerc")
        self.assertEqual(remaining["SOFT"], 7)

    def test_q3_requires_soft(self):
        """Test that Q3 requires soft tyres."""
        manager = TyreAllocationManager(QualifyingSessionType.STANDARD)

        required = manager.get_required_compound("Q3")
        self.assertEqual(required, "SOFT")

    def test_sprint_requires_mediums(self):
        """Test that sprint SQ1/SQ2 require mediums."""
        manager = TyreAllocationManager(QualifyingSessionType.SPRINT)

        self.assertEqual(manager.get_required_compound("SQ1"), "MEDIUM")
        self.assertEqual(manager.get_required_compound("SQ2"), "MEDIUM")
        self.assertEqual(manager.get_required_compound("SQ3"), "SOFT")


class TestQualifyingSessionManager(unittest.TestCase):
    """Test qualifying session manager."""

    def test_session_initialization(self):
        """Test session initialization."""
        drivers = [f"Driver{i}" for i in range(1, 21)]
        session = QualifyingSessionManager("Q1", 18, drivers, elimination_count=5)

        self.assertEqual(session.session_name, "Q1")
        self.assertEqual(session.duration, 18 * 60)
        self.assertEqual(len(session.state.drivers_active), 20)

    def test_lap_time_recording(self):
        """Test recording lap times."""
        drivers = ["Verstappen", "Hamilton", "Leclerc"]
        session = QualifyingSessionManager("Q1", 18, drivers)

        session.record_lap_time("Verstappen", 75.234)
        session.record_lap_time("Hamilton", 75.567)
        session.record_lap_time("Leclerc", 75.123)

        standings = session.get_current_standings()
        self.assertEqual(standings[0][0], "Leclerc")  # Fastest
        self.assertEqual(standings[0][1], 75.123)

    def test_session_end_elimination(self):
        """Test session end with elimination."""
        drivers = [f"Driver{i}" for i in range(1, 21)]
        session = QualifyingSessionManager("Q1", 18, drivers, elimination_count=5)

        # Record times (lower is faster)
        for i, driver in enumerate(drivers):
            session.record_lap_time(driver, 80.0 + i * 0.1)

        advancing, eliminated = session.end_session()

        self.assertEqual(len(advancing), 15)
        self.assertEqual(len(eliminated), 5)
        # Slowest 5 should be eliminated (Driver16-20)
        self.assertIn("Driver20", eliminated)
        self.assertIn("Driver16", eliminated)
        # Fastest should be advancing (Driver1-15)
        self.assertIn("Driver1", advancing)
        self.assertIn("Driver15", advancing)


class TestIncidentHandler(unittest.TestCase):
    """Test incident handler."""

    def test_roll_d100(self):
        """Test dice rolling function."""
        for _ in range(100):
            roll = roll_d100()
            self.assertGreaterEqual(roll, 1)
            self.assertLessEqual(roll, 100)

    def test_crash_incident_creation(self):
        """Test crash incident creation."""
        handler = QualifyingIncidentHandler()
        incident = handler._create_crash_incident("Verstappen")

        self.assertEqual(incident.driver, "Verstappen")
        self.assertEqual(incident.incident_type, "crash")
        self.assertEqual(incident.flag_triggered, "red")
        self.assertTrue(incident.lap_deleted)

    def test_track_limits_incident(self):
        """Test track limits incident creation."""
        handler = QualifyingIncidentHandler()
        incident = handler._create_track_limits_incident("Hamilton")

        self.assertEqual(incident.incident_type, "track_limits")
        self.assertIsNone(incident.flag_triggered)
        self.assertTrue(incident.lap_deleted)


class TestWeatherHandler(unittest.TestCase):
    """Test weather handler."""

    def test_dry_conditions(self):
        """Test dry weather conditions."""
        handler = QualifyingWeatherHandler("Spain")
        state = handler.update_conditions("dry", 0.0, 30.0, 25.0)

        self.assertTrue(state.drs_enabled)
        self.assertEqual(handler.get_recommended_tyres(), "DRY")

    def test_wet_conditions(self):
        """Test wet weather conditions."""
        handler = QualifyingWeatherHandler("Monaco")
        # Very heavy rain (> 0.8) should trigger red flag
        state = handler.update_conditions("wet", 0.9, 20.0, 18.0)

        self.assertFalse(state.drs_enabled)
        self.assertEqual(handler.get_recommended_tyres(), "WET")
        self.assertTrue(handler.should_red_flag())

    def test_damp_conditions(self):
        """Test damp weather conditions."""
        handler = QualifyingWeatherHandler("Silverstone")
        state = handler.update_conditions("damp", 0.3, 22.0, 20.0)

        self.assertFalse(state.drs_enabled)
        self.assertEqual(handler.get_recommended_tyres(), "INTER")


class TestQualifyingResult(unittest.TestCase):
    """Test qualifying result data structures."""

    def test_result_creation(self):
        """Test creating a qualifying result."""
        result = QualifyingResult(
            driver="Verstappen",
            team="Red Bull",
            q1_time=76.234,
            q2_time=75.890,
            q3_time=75.456,
            grid_position=1,
            race_start_tyre="SOFT",
        )

        self.assertEqual(result.get_best_time(), 75.456)
        self.assertIsNone(result.eliminated_in)

    def test_eliminated_driver(self):
        """Test result for eliminated driver."""
        result = QualifyingResult(
            driver="Latifi",
            team="Williams",
            q1_time=79.456,
            grid_position=20,
            eliminated_in="Q1",
        )

        self.assertEqual(result.eliminated_in, "Q1")
        self.assertEqual(result.get_best_time(), 79.456)


if __name__ == "__main__":
    unittest.main()
