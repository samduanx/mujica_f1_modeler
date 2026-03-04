"""
Tests for the Strategist System

Basic unit tests to verify the core functionality of the Strategist System.
"""

import unittest
import random


class TestStrategistProfile(unittest.TestCase):
    """Tests for StrategistProfile class."""

    def test_create_protagonist(self):
        """Test creating the protagonist profile from JSON."""
        from src.strategist.strategist_manager import get_manager, reset_manager

        # Reset manager to ensure clean state
        reset_manager()
        manager = get_manager()

        protagonist = manager.get_strategist("Sakiko Togawa")

        self.assertIsNotNone(protagonist)
        self.assertEqual(protagonist.name, "Sakiko Togawa")
        self.assertEqual(protagonist.team, "Ferrari")
        self.assertEqual(protagonist.experience, 3)

    def test_experience_modifier(self):
        """Test experience modifier calculation."""
        from src.strategist.strategist_types import StrategistProfile

        # Rookie (0-2 years)
        rookie = StrategistProfile(name="Test", team="Test", experience=1)
        self.assertEqual(rookie.get_experience_modifier(), 0)

        # Junior (3-5 years)
        junior = StrategistProfile(name="Test", team="Test", experience=4)
        self.assertEqual(junior.get_experience_modifier(), 1)

        # Experienced (6-9 years)
        experienced = StrategistProfile(name="Test", team="Test", experience=7)
        self.assertEqual(experienced.get_experience_modifier(), 2)

        # Senior (10-14 years)
        senior = StrategistProfile(name="Test", team="Test", experience=12)
        self.assertEqual(senior.get_experience_modifier(), 3)

        # Veteran (15+ years)
        veteran = StrategistProfile(name="Test", team="Test", experience=18)
        self.assertEqual(veteran.get_experience_modifier(), 4)

    def test_attribute_modifier(self):
        """Test attribute modifier calculation."""
        from src.strategist.strategist_types import StrategistProfile

        strategist = StrategistProfile(name="Test", team="Test")

        # Test different attribute ranges
        self.assertEqual(strategist.get_attribute_modifier(0.1), -2)  # 0.0-0.25
        self.assertEqual(strategist.get_attribute_modifier(0.3), -1)  # 0.26-0.40
        self.assertEqual(strategist.get_attribute_modifier(0.5), 0)  # 0.41-0.60
        self.assertEqual(strategist.get_attribute_modifier(0.7), 1)  # 0.61-0.75
        self.assertEqual(strategist.get_attribute_modifier(0.85), 2)  # 0.76-0.90
        self.assertEqual(strategist.get_attribute_modifier(0.95), 3)  # 0.91-1.00

    def test_track_familiarity(self):
        """Test track familiarity bonus calculation."""
        from src.strategist.strategist_types import StrategistProfile

        strategist = StrategistProfile(name="Test", team="Test")

        # No races
        self.assertEqual(strategist.get_track_familiarity_bonus("Monaco"), 0)

        # Add some races
        strategist.track_familiarity["Monaco"] = 2
        self.assertEqual(strategist.get_track_familiarity_bonus("Monaco"), 1)

        strategist.track_familiarity["Monaco"] = 4
        self.assertEqual(strategist.get_track_familiarity_bonus("Monaco"), 2)

        strategist.track_familiarity["Monaco"] = 8
        self.assertEqual(strategist.get_track_familiarity_bonus("Monaco"), 3)


class TestStrategistManager(unittest.TestCase):
    """Tests for StrategistManager class."""

    def test_create_and_get_strategist(self):
        """Test creating and retrieving strategists."""
        from src.strategist.strategist_manager import get_manager

        # Use the global manager (loads from JSON)
        manager = get_manager()

        retrieved = manager.get_strategist("Sakiko Togawa")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.team, "Ferrari")

    def test_get_strategist_by_team(self):
        """Test getting strategist by team name."""
        from src.strategist.strategist_manager import get_manager

        # Use the global manager (loads from JSON)
        manager = get_manager()

        ferrari_strategist = manager.get_strategist_by_team("Ferrari")
        self.assertIsNotNone(ferrari_strategist)
        self.assertEqual(ferrari_strategist.name, "Sakiko Togawa")

    def test_default_team_strategists(self):
        """Test that all default team strategists are loaded from JSON."""
        from src.strategist.strategist_manager import get_manager

        # Use the global manager (loads from JSON)
        manager = get_manager()

        # Get all teams
        teams = manager.list_teams()

        # Should have all teams
        self.assertIn("Ferrari", teams)
        self.assertIn("Red Bull Racing", teams)
        self.assertIn("Mercedes", teams)

        # Ferrari should be protagonist with Sakiko Togawa
        ferrari = manager.get_strategist_by_team("Ferrari")
        self.assertEqual(ferrari.name, "Sakiko Togawa")


class TestDiceMechanics(unittest.TestCase):
    """Tests for dice rolling mechanics."""

    def test_d20_roll(self):
        """Test d20 roll returns valid values."""
        from src.strategist.dice_mechanics import StrategistDiceRoller
        from src.strategist.strategist_types import StrategistProfile

        # Set seed for reproducibility
        random.seed(42)

        strategist = StrategistProfile(name="Test", team="Test")
        roller = StrategistDiceRoller(strategist)

        roll = roller.roll_d20()
        self.assertGreaterEqual(roll, 1)
        self.assertLessEqual(roll, 20)

    def test_outcome_determination(self):
        """Test outcome determination from rolls."""
        from src.strategist.strategist_types import determine_outcome, OutcomeLevel

        # Critical failure (natural 1)
        outcome = determine_outcome(1, 5)
        self.assertEqual(outcome, OutcomeLevel.CRITICAL_FAILURE)

        # Critical success (natural 20)
        outcome = determine_outcome(20, 25)
        self.assertEqual(outcome, OutcomeLevel.CRITICAL_SUCCESS)

        # Regular outcomes based on final value
        outcome = determine_outcome(10, 12)
        self.assertEqual(outcome, OutcomeLevel.SUCCESS)

        outcome = determine_outcome(8, 8)
        self.assertEqual(outcome, OutcomeLevel.PARTIAL_SUCCESS)

        outcome = determine_outcome(3, 4)
        self.assertEqual(outcome, OutcomeLevel.FAILURE)

    def test_modifier_calculation(self):
        """Test modifier calculation for decisions."""
        from src.strategist.dice_mechanics import StrategistDiceRoller
        from src.strategist.strategist_types import (
            StrategistProfile,
            RaceContext,
            DecisionType,
        )

        strategist = StrategistProfile(
            name="Test",
            team="Test",
            experience=5,
            pit_timing=0.7,
            aggression=0.6,
        )
        roller = StrategistDiceRoller(strategist)

        context = RaceContext(
            track_name="Monaco",
            current_lap=20,
            total_laps=78,
        )

        modifiers = roller.calculate_modifiers(DecisionType.PIT_TIMING, context, 12)

        # Should have experience modifier
        self.assertIn("experience", modifiers)
        self.assertEqual(modifiers["experience"], 1)  # Junior = +1


class TestDriverCompliance(unittest.TestCase):
    """Tests for driver compliance checking."""

    def test_compliance_outcome_determination(self):
        """Test compliance outcome determination."""
        from src.strategist.strategist_types import (
            determine_compliance_outcome,
            DriverComplianceLevel,
        )

        # Critical override (natural 1)
        outcome = determine_compliance_outcome(1, 5)
        self.assertEqual(outcome, DriverComplianceLevel.OVERRIDE)

        # Critical perfect (natural 20)
        outcome = determine_compliance_outcome(20, 25)
        self.assertEqual(outcome, DriverComplianceLevel.PERFECT)

        # Regular outcomes
        outcome = determine_compliance_outcome(10, 14)
        self.assertEqual(outcome, DriverComplianceLevel.PARTIAL)

    def test_compliance_effectiveness(self):
        """Test compliance effectiveness multipliers."""
        from src.strategist.strategist_types import (
            ComplianceCheck,
            DriverComplianceLevel,
        )

        self.assertEqual(
            ComplianceCheck.get_effectiveness(DriverComplianceLevel.PERFECT), 1.20
        )
        self.assertEqual(
            ComplianceCheck.get_effectiveness(DriverComplianceLevel.FULL), 1.00
        )
        self.assertEqual(
            ComplianceCheck.get_effectiveness(DriverComplianceLevel.OVERRIDE), 0.00
        )


class TestPaceMode(unittest.TestCase):
    """Tests for pace mode functionality."""

    def test_pace_mode_values(self):
        """Test that all pace modes are defined."""
        from src.strategist.strategist_types import PaceMode

        modes = list(PaceMode)
        self.assertGreaterEqual(len(modes), 5)

        # Check specific modes
        self.assertIn(PaceMode.PUSH, modes)
        self.assertIn(PaceMode.RACE, modes)
        self.assertIn(PaceMode.MANAGE, modes)
        self.assertIn(PaceMode.SAVE, modes)
        self.assertIn(PaceMode.LIFT_AND_COAST, modes)


class TestDecisionTypes(unittest.TestCase):
    """Tests for decision type enums."""

    def test_decision_types(self):
        """Test all decision types are defined."""
        from src.strategist.strategist_types import DecisionType

        types = list(DecisionType)

        self.assertIn(DecisionType.PIT_TIMING, types)
        self.assertIn(DecisionType.TYRE_COMPOUND, types)
        self.assertIn(DecisionType.RACING_PACE, types)
        self.assertIn(DecisionType.WEATHER_RESPONSE, types)
        self.assertIn(DecisionType.SAFETY_CAR_RESPONSE, types)
        self.assertIn(DecisionType.UNDERCUT_ATTEMPT, types)


class TestTrackData(unittest.TestCase):
    """Tests for track data."""

    def test_pit_loss_times(self):
        """Test pit loss times for tracks."""
        from src.strategist.strategist_types import TRACK_PIT_LOSS

        # Monaco should have higher pit loss (slower pit lane)
        self.assertGreater(TRACK_PIT_LOSS["Monaco"], TRACK_PIT_LOSS["Italy"])

        # All major tracks should be present
        expected_tracks = [
            "Bahrain",
            "Monaco",
            "Great Britain",
            "Italy",
            "Belgium",
            "Japan",
            "Singapore",
            "United States",
            "Abu Dhabi",
        ]

        for track in expected_tracks:
            self.assertIn(track, TRACK_PIT_LOSS)

    def test_undercut_difficulty(self):
        """Test undercut difficulty modifiers."""
        from src.strategist.strategist_types import TRACK_UNDERCUT_DIFFICULTY

        # Monaco and Singapore should be hardest for undercuts
        self.assertEqual(TRACK_UNDERCUT_DIFFICULTY["Monaco"], -2)
        self.assertEqual(TRACK_UNDERCUT_DIFFICULTY["Singapore"], -3)

        # Monza should be easiest
        self.assertEqual(TRACK_UNDERCUT_DIFFICULTY["Italy"], 0)


if __name__ == "__main__":
    unittest.main()
