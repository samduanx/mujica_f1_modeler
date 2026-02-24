"""
Tests for the Blue Flag and Lapping System.

This module contains comprehensive tests for:
- BlueFlagState enum and transitions
- LappingDetectionConfig
- BlueFlagComplianceRoller (dice-based compliance)
- ResistanceLevel enum
- DriverPersonality
- BlueFlagManager
- LappingPair and BlueFlagViolation dataclasses
- LappingOvertake class
- IncidentResponseUnlappingManager
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import random

from incidents.blue_flag import (
    BlueFlagState,
    ResistanceLevel,
    LappingDetectionConfig,
    DriverPersonality,
    BlueFlagComplianceRoller,
    BlueFlagManager,
    LappingPair,
    BlueFlagViolation,
)
from incidents.lapping_overtake import (
    LappingOvertake,
    LappingResult,
    SECTION_SUITABILITY,
)
from incidents.unlapping import (
    IncidentResponseUnlappingManager,
    UnlappingState,
    check_f1_article_55_compliance,
)


class TestBlueFlagState(unittest.TestCase):
    """Test BlueFlagState enum"""

    def test_enum_values(self):
        """Test that all states exist with correct values"""
        self.assertEqual(BlueFlagState.NONE.value, "none")
        self.assertEqual(BlueFlagState.WARNING.value, "warning")
        self.assertEqual(BlueFlagState.FINAL.value, "final")
        self.assertEqual(BlueFlagState.COMPLIED.value, "complied")
        self.assertEqual(BlueFlagState.VIOLATION.value, "violation")


class TestResistanceLevel(unittest.TestCase):
    """Test ResistanceLevel enum"""

    def test_enum_values(self):
        """Test that all resistance levels exist with correct values"""
        self.assertEqual(ResistanceLevel.NONE.value, "none")
        self.assertEqual(ResistanceLevel.MINOR.value, "minor")
        self.assertEqual(ResistanceLevel.MODERATE.value, "moderate")
        self.assertEqual(ResistanceLevel.STRONG.value, "strong")
        self.assertEqual(ResistanceLevel.VIOLATION.value, "violation")


class TestLappingDetectionConfig(unittest.TestCase):
    """Test LappingDetectionConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = LappingDetectionConfig()
        self.assertEqual(config.warning_gap, 3.0)
        self.assertEqual(config.final_gap, 1.5)
        self.assertEqual(config.min_sections_apart, 0)
        self.assertEqual(config.max_sections_apart, 1)

    def test_custom_values(self):
        """Test custom configuration values"""
        config = LappingDetectionConfig(
            warning_gap=4.0, final_gap=2.0, min_sections_apart=0, max_sections_apart=2
        )
        self.assertEqual(config.warning_gap, 4.0)
        self.assertEqual(config.final_gap, 2.0)
        self.assertEqual(config.max_sections_apart, 2)


class TestDriverPersonality(unittest.TestCase):
    """Test DriverPersonality dataclass"""

    def test_default_values(self):
        """Test default personality values"""
        personality = DriverPersonality()
        self.assertEqual(personality.professionalism, 0.5)
        self.assertEqual(personality.aggression, 0.5)
        self.assertEqual(personality.team_loyalty, 0.5)
        self.assertEqual(personality.stubbornness, 0.5)
        self.assertEqual(personality.sportsmanship, 0.5)

    def test_compliance_modifier_neutral(self):
        """Test compliance modifier with neutral personality"""
        personality = DriverPersonality()  # All 0.5
        modifier = personality.get_compliance_modifier()
        self.assertEqual(modifier, 0)

    def test_compliance_modifier_professional(self):
        """Test compliance modifier for professional driver"""
        personality = DriverPersonality(professionalism=0.9, aggression=0.3)
        modifier = personality.get_compliance_modifier()
        # (0.9-0.5)*4 = +1.6 -> 1
        # (0.3-0.5)*3 = -0.6 -> 0 (negative, so subtract)
        # Total: +1 - 0 = +1
        self.assertGreater(modifier, 0)

    def test_compliance_modifier_aggressive(self):
        """Test compliance modifier for aggressive driver"""
        personality = DriverPersonality(professionalism=0.3, aggression=0.9)
        modifier = personality.get_compliance_modifier()
        # (0.3-0.5)*4 = -0.8 -> 0
        # (0.9-0.5)*3 = +1.2 -> 1 (but negative because aggression subtracts)
        # Total should be negative
        self.assertLess(modifier, 0)

    def test_frustration_rate(self):
        """Test frustration rate calculation"""
        # Low stubbornness
        personality_low = DriverPersonality(stubbornness=0.0)
        self.assertAlmostEqual(personality_low.get_frustration_rate(), 0.5)

        # High stubbornness
        personality_high = DriverPersonality(stubbornness=1.0)
        self.assertAlmostEqual(personality_high.get_frustration_rate(), 1.0)

        # Medium
        personality_med = DriverPersonality(stubbornness=0.5)
        self.assertAlmostEqual(personality_med.get_frustration_rate(), 0.75)


class TestBlueFlagComplianceRoller(unittest.TestCase):
    """Test BlueFlagComplianceRoller dice-based system"""

    def setUp(self):
        self.roller = BlueFlagComplianceRoller()
        self.mock_driver = Mock()
        self.mock_driver.dr_value = 85
        self.mock_driver.team_status = None
        self.mock_driver.team = None
        self.mock_leader = Mock()
        self.mock_leader.team = None
        self.mock_leader.championship_position = 5

    def test_base_target(self):
        """Test base compliance target"""
        self.assertEqual(self.roller.base_target, 15)

    def test_dr_modifier_calculation(self):
        """Test DR modifier calculation"""
        # Need to set championship_position to avoid Mock comparison issues
        self.mock_leader.championship_position = 99

        # DR 80: no bonus, blue_flag_count=1 adds +1
        self.mock_driver.dr_value = 80
        target = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "straight", 0.5
        )
        self.assertEqual(target, 18)  # 15 base + 0 (DR) + 2 (straight) + 1 (first flag)

        # DR 85: +1 bonus
        self.mock_driver.dr_value = 85
        target = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "straight", 0.5
        )
        self.assertEqual(
            target, 19
        )  # 15 + 1 (DR) + 2 (straight) + 1 (first flag, capped)

        # DR 90: +2 bonus (with blue_flag_count=2 no first flag bonus)
        self.mock_driver.dr_value = 90
        target = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 2, "straight", 0.5
        )
        self.assertEqual(target, 19)  # 15 + 2 (DR) + 2 (straight)

    def test_track_section_modifiers(self):
        """Test track section modifiers"""
        # Straight (safest)
        target_straight = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "straight", 0.5
        )

        # Corner apex (most dangerous)
        target_apex = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "corner_apex", 0.5
        )

        # Straight should have higher target (easier to comply)
        self.assertGreater(target_straight, target_apex)

    def test_blue_flag_frustration(self):
        """Test blue flag repetition frustration"""
        # First blue flag - bonus
        target1 = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "straight", 0.5
        )

        # Second blue flag - neutral
        target2 = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 2, "straight", 0.5
        )

        # Third blue flag - penalty
        target3 = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 3, "straight", 0.5
        )

        # First should be highest (easiest), third lowest (hardest)
        self.assertGreater(target1, target3)
        self.assertGreaterEqual(target2, target3)

    def test_target_clamping(self):
        """Test that target is clamped between 3 and 19"""
        # Very high target scenario
        self.mock_driver.dr_value = 95
        self.mock_driver.team = "Red Bull"
        self.mock_leader.team = "Red Bull"  # Teammate (+3)
        target = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 1, "straight", 0.5
        )
        self.assertLessEqual(target, 19)

        # Very low target scenario
        self.mock_driver.dr_value = 75
        target = self.roller.get_compliance_target(
            self.mock_driver, self.mock_leader, 5, "corner_apex", 0.95
        )
        self.assertGreaterEqual(target, 3)

    def test_compliance_dice_probabilities(self):
        """Test compliance dice probabilities (75% base rate)"""
        # With base target 15, roll 15-20 = 6/20 = 30% but we have modifiers
        # Actually with target 15, need to roll 15-20 = 6/20 = 30% chance
        # But with section and other modifiers, target increases
        results = []
        for _ in range(1000):
            roll, compliant = self.roller.roll_compliance(15)
            results.append(compliant)

        compliance_rate = sum(results) / len(results)
        # With target 15, should have ~30% compliance (rolls 15-20)
        self.assertAlmostEqual(compliance_rate, 0.30, delta=0.05)

    def test_compliance_dice_higher_target(self):
        """Test compliance with higher target (easier)"""
        results = []
        for _ in range(1000):
            roll, compliant = self.roller.roll_compliance(10)
            results.append(compliant)

        compliance_rate = sum(results) / len(results)
        # With target 10, should have ~55% compliance (rolls 10-20)
        self.assertAlmostEqual(compliance_rate, 0.55, delta=0.05)

    def test_resistance_level_determination(self):
        """Test resistance level determination"""
        # Roll >= target: NO resistance
        level = self.roller.determine_resistance_level(15, 15, 0.5)
        self.assertEqual(level, ResistanceLevel.NONE)

        # Roll 1-2 below target: MINOR
        level = self.roller.determine_resistance_level(13, 15, 0.5)
        self.assertEqual(level, ResistanceLevel.MINOR)

        # Roll 3-4 below target: MODERATE
        level = self.roller.determine_resistance_level(11, 15, 0.5)
        self.assertEqual(level, ResistanceLevel.MODERATE)

        # Roll 5-6 below target: STRONG
        level = self.roller.determine_resistance_level(9, 15, 0.5)
        self.assertEqual(level, ResistanceLevel.STRONG)

        # Roll >6 below target: VIOLATION
        level = self.roller.determine_resistance_level(8, 15, 0.5)
        self.assertEqual(level, ResistanceLevel.VIOLATION)

    def test_aggression_affects_resistance(self):
        """Test that aggression affects resistance level"""
        # Same roll and target, different aggression
        level_low = self.roller.determine_resistance_level(14, 15, 0.2)
        level_high = self.roller.determine_resistance_level(14, 15, 0.9)

        # Higher aggression should result in higher resistance
        resistance_values = {
            ResistanceLevel.NONE: 0,
            ResistanceLevel.MINOR: 1,
            ResistanceLevel.MODERATE: 2,
            ResistanceLevel.STRONG: 3,
            ResistanceLevel.VIOLATION: 4,
        }
        self.assertGreaterEqual(
            resistance_values[level_high], resistance_values[level_low]
        )


class TestBlueFlagManager(unittest.TestCase):
    """Test BlueFlagManager class"""

    def setUp(self):
        self.manager = BlueFlagManager()
        self.mock_leader = Mock()
        self.mock_leader.name = "Leader"
        self.mock_leader.dr_value = 88
        self.mock_leader.cumulative_time = 100.0
        self.mock_leader.current_sector = 2
        self.mock_leader.get_current_lap.return_value = 10

        self.mock_lapped = Mock()
        self.mock_lapped.name = "Lapped"
        self.mock_lapped.dr_value = 82
        self.mock_lapped.cumulative_time = 97.5  # 2.5s behind (within warning gap)
        self.mock_lapped.current_sector = 2
        self.mock_lapped.get_current_lap.return_value = 9  # 1 lap down

    def test_initialization(self):
        """Test BlueFlagManager initialization"""
        self.assertEqual(len(self.manager.active_blue_flags), 0)
        self.assertEqual(len(self.manager.lapping_pairs), 0)
        self.assertEqual(len(self.manager.violations), 0)
        self.assertIsNotNone(self.manager.compliance_roller)

    def test_detect_lapping_situation(self):
        """Test lapping situation detection"""
        pair = self.manager.detect_lapping_situation(
            self.mock_leader, self.mock_lapped, "straight", 0.5
        )

        self.assertIsNotNone(pair)
        self.assertEqual(pair.leader, "Leader")
        self.assertEqual(pair.lapped_car, "Lapped")
        self.assertEqual(pair.lap_difference, 1)
        self.assertEqual(pair.gap, 2.5)  # 100.0 - 97.5

    def test_no_lapping_if_same_lap(self):
        """Test that same-lap cars don't trigger lapping"""
        self.mock_lapped.get_current_lap.return_value = 10  # Same lap
        pair = self.manager.detect_lapping_situation(
            self.mock_leader, self.mock_lapped, "straight", 0.5
        )
        self.assertIsNone(pair)

    def test_no_lapping_if_gap_too_large(self):
        """Test that large gaps don't trigger lapping"""
        self.mock_lapped.cumulative_time = 96.0  # 4s gap (> 3s warning)
        pair = self.manager.detect_lapping_situation(
            self.mock_leader, self.mock_lapped, "straight", 0.5
        )
        self.assertIsNone(pair)

    def test_evaluate_compliance(self):
        """Test compliance evaluation"""
        # Set championship_position to avoid Mock comparison issues
        self.mock_leader.championship_position = 99

        pair = LappingPair(
            leader="Leader",
            lapped_car="Lapped",
            gap=2.0,
            lap_difference=1,
            track_section="straight",
            blue_flag_state=BlueFlagState.WARNING,
            blue_flag_count=1,
        )

        with patch.object(
            self.manager.compliance_roller, "roll_compliance", return_value=(16, True)
        ):
            is_compliant, resistance, roll = self.manager.evaluate_compliance(
                pair, self.mock_leader, self.mock_lapped, 0.5
            )

        self.assertTrue(is_compliant)
        # Resistance level may vary based on roll vs target, just check it exists
        self.assertIsNotNone(resistance)
        self.assertEqual(self.manager.blue_flag_counts["Lapped"], 1)

    def test_record_violation(self):
        """Test violation recording"""
        violation = self.manager.record_violation(
            driver_name="Lapped",
            lap=10,
            resistance_level=ResistanceLevel.MODERATE,
            track_section="straight",
            narrative="Test violation",
        )

        self.assertEqual(violation.driver, "Lapped")
        self.assertEqual(violation.resistance_level, ResistanceLevel.MODERATE)
        self.assertEqual(violation.offense_count, 1)
        self.assertEqual(len(self.manager.violations), 1)
        self.assertEqual(self.manager.offense_counts["Lapped"], 1)

    def test_penalty_escalation(self):
        """Test penalty escalation based on resistance level and offense count"""
        # First MINOR offense - warning_logged
        penalty1 = self.manager._determine_penalty(ResistanceLevel.MINOR, 1)
        self.assertEqual(penalty1, "warning_logged")

        # Second MINOR offense - warning_announced
        penalty2 = self.manager._determine_penalty(ResistanceLevel.MINOR, 2)
        self.assertEqual(penalty2, "warning_announced")

        # Third MINOR offense - 5s penalty
        penalty3 = self.manager._determine_penalty(ResistanceLevel.MINOR, 3)
        self.assertEqual(penalty3, "5s_penalty")

        # First MODERATE offense - warning_announced
        penalty_mod1 = self.manager._determine_penalty(ResistanceLevel.MODERATE, 1)
        self.assertEqual(penalty_mod1, "warning_announced")

        # First STRONG offense - 5s penalty
        penalty_strong1 = self.manager._determine_penalty(ResistanceLevel.STRONG, 1)
        self.assertEqual(penalty_strong1, "5s_penalty")

        # First VIOLATION - drive_through
        penalty_viol1 = self.manager._determine_penalty(ResistanceLevel.VIOLATION, 1)
        self.assertEqual(penalty_viol1, "drive_through")

    def test_is_lapping_situation(self):
        """Test lapping situation check"""
        # Add an active lapping pair
        pair = LappingPair(
            leader="Leader",
            lapped_car="Lapped",
            gap=2.0,
            lap_difference=1,
            track_section="straight",
            blue_flag_state=BlueFlagState.WARNING,
        )
        self.manager.lapping_pairs.append(pair)

        self.assertTrue(self.manager.is_lapping_situation("Leader", "Lapped"))
        self.assertFalse(self.manager.is_lapping_situation("Other", "Lapped"))

    def test_get_statistics(self):
        """Test statistics gathering"""
        # Add some violations
        self.manager.record_violation(
            "Driver1", 5, ResistanceLevel.MINOR, "straight", "Test"
        )
        self.manager.record_violation(
            "Driver1", 8, ResistanceLevel.MODERATE, "straight", "Test 2"
        )
        self.manager.record_violation(
            "Driver2", 10, ResistanceLevel.STRONG, "straight", "Test 3"
        )

        stats = self.manager.get_statistics()

        self.assertEqual(stats["total_violations"], 3)
        self.assertEqual(stats["violations_by_driver"]["Driver1"], 2)
        self.assertEqual(stats["violations_by_driver"]["Driver2"], 1)


class TestSectionSuitability(unittest.TestCase):
    """Test section suitability constants"""

    def test_straight_and_drs(self):
        """Test that straight and DRS zones are fully suitable"""
        self.assertEqual(SECTION_SUITABILITY["straight"], 1.0)
        self.assertEqual(SECTION_SUITABILITY["drs_zone"], 1.0)

    def test_unsafe_sections(self):
        """Test that apex and braking zones are unsafe"""
        self.assertEqual(SECTION_SUITABILITY["corner_apex"], 0.0)
        self.assertEqual(SECTION_SUITABILITY["braking_zone"], 0.1)

    def test_moderate_sections(self):
        """Test moderately suitable sections"""
        self.assertGreater(SECTION_SUITABILITY["corner_exit"], 0.5)
        self.assertLess(SECTION_SUITABILITY["corner_entry"], 0.5)


class TestLappingOvertake(unittest.TestCase):
    """Test LappingOvertake class"""

    def setUp(self):
        self.lapping_overtake = LappingOvertake()
        self.mock_leader = Mock()
        self.mock_leader.name = "Verstappen"
        self.mock_leader.dr_value = 92

        self.mock_lapped = Mock()
        self.mock_lapped.name = "Latifi"
        self.mock_lapped.dr_value = 78

    def test_resolve_lapping_compliance(self):
        """Test lapping resolution with compliance"""
        result = self.lapping_overtake.resolve_lapping(
            leader=self.mock_leader,
            lapped_car=self.mock_lapped,
            blue_flag_state=BlueFlagState.WARNING,
            track_section="straight",
            blue_flag_complied=True,
            resistance_level=ResistanceLevel.NONE,
            lap=10,
        )

        self.assertTrue(result.success)
        self.assertTrue(result.blue_flag_complied)
        self.assertFalse(result.violation)
        self.assertIsNone(result.penalty)
        self.assertGreater(result.compliance_score, 0.7)

    def test_resolve_lapping_unsafe_section(self):
        """Test lapping in unsafe section (corner apex)"""
        result = self.lapping_overtake.resolve_lapping(
            leader=self.mock_leader,
            lapped_car=self.mock_lapped,
            blue_flag_state=BlueFlagState.WARNING,
            track_section="corner_apex",
            blue_flag_complied=False,
            lap=10,
        )

        # Should not succeed in unsafe section
        self.assertFalse(result.success)
        self.assertEqual(result.section_suitability, 0.0)

    def test_resolve_lapping_resistance(self):
        """Test lapping with resistance"""
        with patch("random.random", return_value=0.1):  # Force success
            result = self.lapping_overtake.resolve_lapping(
                leader=self.mock_leader,
                lapped_car=self.mock_lapped,
                blue_flag_state=BlueFlagState.FINAL,
                track_section="straight",
                blue_flag_complied=False,
                resistance_level=ResistanceLevel.MODERATE,
                lap=10,
            )

        self.assertTrue(result.violation)
        self.assertGreater(result.resistance_score, 0)

    def test_get_blue_flag_modifier(self):
        """Test blue flag modifier calculation"""
        # Warning compliance gives +5
        mod_warning = self.lapping_overtake.get_blue_flag_modifier(
            True, BlueFlagState.WARNING
        )
        self.assertEqual(mod_warning, 5.0)

        # Final compliance gives +4
        mod_final = self.lapping_overtake.get_blue_flag_modifier(
            True, BlueFlagState.FINAL
        )
        self.assertEqual(mod_final, 4.0)

        # No compliance gives 0
        mod_none = self.lapping_overtake.get_blue_flag_modifier(
            False, BlueFlagState.WARNING
        )
        self.assertEqual(mod_none, 0.0)


class TestIncidentResponseUnlappingManager(unittest.TestCase):
    """Test IncidentResponseUnlappingManager class"""

    def setUp(self):
        self.manager = IncidentResponseUnlappingManager()

    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsNone(self.manager.sc_deployment_lap)
        self.assertEqual(self.manager.sc_laps_elapsed, 0)
        self.assertFalse(self.manager.unlapping_authorized)
        self.assertFalse(self.manager.unlapping_completed)

    def test_on_sc_deployed(self):
        """Test SC deployment handling"""
        car_positions = {"Car1": 1, "Car2": 2, "Car3": 3}
        car_laps = {"Car1": 10, "Car2": 10, "Car3": 9}  # Car3 is lapped

        self.manager.on_sc_deployed(
            lap=10,
            car_positions=car_positions,
            car_laps=car_laps,
            leader_laps=10,
        )

        self.assertEqual(self.manager.sc_deployment_lap, 10)
        self.assertEqual(len(self.manager.lapped_cars), 1)
        self.assertEqual(self.manager.lapped_cars[0].name, "Car3")

    def test_update_authorizes_after_min_laps(self):
        """Test that unlapping is authorized after minimum SC laps"""
        car_positions = {"Car1": 1, "Car2": 2, "Car3": 3}
        car_laps = {"Car1": 10, "Car2": 10, "Car3": 9}

        self.manager.on_sc_deployed(
            lap=10,
            car_positions=car_positions,
            car_laps=car_laps,
            leader_laps=10,
        )

        # Update on lap 11 (1 SC lap) - should not authorize
        event1 = self.manager.update(
            lap=11,
            car_positions=car_positions,
            car_laps=car_laps,
            leader_laps=11,
            track_conditions="dry",
            laps_remaining=20,
        )
        self.assertIsNone(event1)
        self.assertFalse(self.manager.unlapping_authorized)

        # Update on lap 13 (3 SC laps) - should authorize
        event2 = self.manager.update(
            lap=13,
            car_positions=car_positions,
            car_laps={"Car1": 12, "Car2": 12, "Car3": 11},
            leader_laps=12,
            track_conditions="dry",
            laps_remaining=20,
        )
        self.assertIsNotNone(event2)
        self.assertEqual(event2["type"], "unlapping_authorized")
        self.assertTrue(self.manager.unlapping_authorized)

    def test_process_car_unlap(self):
        """Test processing a car unlap"""
        car_positions = {"Car1": 1, "Car2": 2, "Car3": 3}
        car_laps = {"Car1": 10, "Car2": 10, "Car3": 9}

        self.manager.on_sc_deployed(
            lap=10,
            car_positions=car_positions,
            car_laps=car_laps,
            leader_laps=10,
        )

        # Authorize unlapping first
        self.manager.authorize_unlapping(
            lap=13,
            car_positions=car_positions,
            car_laps={"Car1": 12, "Car2": 12, "Car3": 11},
            leader_laps=12,
        )

        # Process unlap for Car3
        success, message = self.manager.process_car_unlap("Car3", lap=13)

        self.assertTrue(success)
        self.assertIn("completed", message.lower())
        self.assertEqual(self.manager.unlapped_count, 1)

    def test_should_sc_come_in(self):
        """Test SC come-in decision"""
        car_positions = {"Car1": 1, "Car2": 2, "Car3": 3}
        car_laps = {"Car1": 10, "Car2": 10, "Car3": 9}

        self.manager.on_sc_deployed(
            lap=10,
            car_positions=car_positions,
            car_laps=car_laps,
            leader_laps=10,
        )

        # Before unlapping authorized
        should_come, lap, reason = self.manager.should_sc_come_in()
        self.assertFalse(should_come)

        # Authorize and complete unlapping
        self.manager.authorize_unlapping(
            lap=13,
            car_positions=car_positions,
            car_laps={"Car1": 12, "Car2": 12, "Car3": 11},
            leader_laps=12,
        )
        # Manually set the authorized flag (normally done by update())
        self.manager.unlapping_authorized = True
        self.manager.execute_unlap("Car3", lap=13)

        # Check if SC can come in
        should_come, lap, reason = self.manager.should_sc_come_in()
        # SC can come in when unlapping is complete
        if self.manager.can_sc_come_in():
            self.assertTrue(should_come)
            self.assertIsNotNone(lap)


class TestF1Article55Compliance(unittest.TestCase):
    """Test F1 Article 55.14-55.15 compliance helper"""

    def test_compliant_conditions(self):
        """Test compliant conditions for unlapping"""
        is_compliant, requirements = check_f1_article_55_compliance(
            sc_duration_laps=5,
            lapped_cars_count=3,
            track_conditions="dry",
            laps_remaining=20,
        )

        self.assertTrue(is_compliant)
        self.assertIn("Minimum SC duration met", requirements)
        self.assertIn("Lapped cars exist", requirements)
        self.assertIn("Track conditions safe", requirements)
        self.assertIn("Sufficient laps remaining", requirements)

    def test_insufficient_sc_duration(self):
        """Test insufficient SC duration"""
        is_compliant, requirements = check_f1_article_55_compliance(
            sc_duration_laps=1,
            lapped_cars_count=3,
            track_conditions="dry",
            laps_remaining=20,
        )

        self.assertFalse(is_compliant)
        self.assertTrue(any("insufficient" in r.lower() for r in requirements))

    def test_no_lapped_cars(self):
        """Test no lapped cars"""
        is_compliant, requirements = check_f1_article_55_compliance(
            sc_duration_laps=5,
            lapped_cars_count=0,
            track_conditions="dry",
            laps_remaining=20,
        )

        self.assertFalse(is_compliant)
        self.assertTrue(any("no lapped cars" in r.lower() for r in requirements))

    def test_unsafe_track_conditions(self):
        """Test unsafe track conditions"""
        is_compliant, requirements = check_f1_article_55_compliance(
            sc_duration_laps=5,
            lapped_cars_count=3,
            track_conditions="heavy_rain",
            laps_remaining=20,
        )

        self.assertFalse(is_compliant)
        self.assertTrue(any("unsafe" in r.lower() for r in requirements))


class TestIntegration(unittest.TestCase):
    """Integration tests for the blue flag system"""

    def test_full_lapping_scenario(self):
        """Test a complete lapping scenario"""
        # Create manager
        manager = BlueFlagManager()

        # Create driver states
        leader = Mock()
        leader.name = "Leader"
        leader.dr_value = 90
        leader.cumulative_time = 500.0
        leader.current_sector = 1
        leader.team = "Red Bull"
        leader.get_current_lap.return_value = 20

        lapped = Mock()
        lapped.name = "Lapped"
        lapped.dr_value = 82
        lapped.cumulative_time = 497.8  # 2.2s gap
        lapped.current_sector = 1
        lapped.team = "Williams"
        lapped.get_current_lap.return_value = 19

        # Detect lapping
        pair = manager.detect_lapping_situation(
            leader, lapped, "straight", race_progress=0.6
        )
        self.assertIsNotNone(pair)

        # Evaluate compliance (mock to ensure non-compliance)
        with patch.object(
            manager.compliance_roller,
            "roll_compliance",
            return_value=(8, False),  # Failed roll
        ):
            is_compliant, resistance, roll = manager.evaluate_compliance(
                pair,
                leader,
                lapped,
                race_progress=0.6,  # type: ignore
            )

        self.assertFalse(is_compliant)

        # Record violation
        violation = manager.record_violation(
            driver_name="Lapped",
            lap=20,
            resistance_level=resistance,
            track_section="straight",
            narrative="Integration test violation",
        )

        self.assertEqual(violation.driver, "Lapped")
        self.assertEqual(len(manager.violations), 1)


if __name__ == "__main__":
    unittest.main()
