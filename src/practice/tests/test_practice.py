"""
Practice System Unit Tests

Tests for the Free Practice system components.
"""

import unittest
from src.practice import (
    SetupDiceRoller,
    SetupEffectCalculator,
    SetupTuningManager,
    ParcFermeManager,
    ParcFermeCoordinator,
    PracticeLapSimulator,
    WeekendType,
    SetupCategory,
    PracticeSessionType,
)


class TestSetupDiceRoller(unittest.TestCase):
    """Tests for setup dice rolling."""

    def test_d6_range(self):
        """Test that d6 rolls are in range 1-6."""
        roller = SetupDiceRoller(seed=42)
        for _ in range(100):
            roll = roller.roll_d6()
            self.assertGreaterEqual(roll, 1)
            self.assertLessEqual(roll, 6)

    def test_reproducibility(self):
        """Test that same seed gives same results."""
        roller1 = SetupDiceRoller(seed=42)
        roller2 = SetupDiceRoller(seed=42)

        for _ in range(10):
            self.assertEqual(roller1.roll_d6(), roller2.roll_d6())

    def test_all_categories(self):
        """Test rolling for all categories."""
        roller = SetupDiceRoller(seed=42)
        rolls = roller.roll_all_categories()

        self.assertEqual(len(rolls), 5)
        for category in SetupCategory:
            self.assertIn(category, rolls)
            self.assertGreaterEqual(rolls[category], 1)
            self.assertLessEqual(rolls[category], 6)


class TestSetupEffectCalculator(unittest.TestCase):
    """Tests for setup effect calculation."""

    def test_modifier_mapping(self):
        """Test dice to modifier mapping."""
        calc = SetupEffectCalculator()

        self.assertEqual(calc.get_modifier_from_roll(1), -0.2)
        self.assertEqual(calc.get_modifier_from_roll(3), 0.0)
        self.assertEqual(calc.get_modifier_from_roll(6), 0.3)

    def test_total_effect(self):
        """Test total effect calculation."""
        calc = SetupEffectCalculator()

        rolls = {
            SetupCategory.AERODYNAMICS: 6,  # +0.3
            SetupCategory.SUSPENSION: 6,  # +0.3
            SetupCategory.DIFFERENTIAL: 6,  # +0.3
            SetupCategory.BRAKE_BALANCE: 6,  # +0.3
            SetupCategory.TYRE_PRESSURE: 6,  # +0.3
        }

        total = calc.calculate_total_effect(rolls)
        self.assertEqual(total, 1.5)  # 5 × 0.3

    def test_normalization(self):
        """Test R delta normalization."""
        calc = SetupEffectCalculator()

        # Should clamp to max 0.5
        self.assertEqual(calc.normalize_to_r_delta(1.0), 0.5)

        # Should clamp to min -0.5
        self.assertEqual(calc.normalize_to_r_delta(-1.0), -0.5)

        # Should pass through in range
        self.assertEqual(calc.normalize_to_r_delta(0.3), 0.3)

    def test_average_setups(self):
        """Test averaging multiple setups."""
        calc = SetupEffectCalculator()

        from src.practice import SetupTuningResult

        setup1 = SetupTuningResult(
            driver="Test",
            session="FP1",
            aerodynamics=6,
            suspension=6,
            differential=6,
            brake_balance=6,
            tyre_pressure=6,
        )

        setup2 = SetupTuningResult(
            driver="Test",
            session="FP2",
            aerodynamics=1,
            suspension=1,
            differential=1,
            brake_balance=1,
            tyre_pressure=1,
        )

        averaged = calc.average_setups([setup1, setup2])

        # Should average to 3-4 range
        self.assertEqual(averaged.aerodynamics, 4)  # (6+1)/2 rounded
        self.assertEqual(averaged.driver, "Test")


class TestParcFermeManager(unittest.TestCase):
    """Tests for parc fermé management."""

    def test_activation(self):
        """Test parc fermé activation."""
        manager = ParcFermeManager(weekend_type=WeekendType.NORMAL)

        self.assertFalse(manager.is_active())
        manager.activate(after_session="FP3")
        self.assertTrue(manager.is_active())
        self.assertEqual(manager.state.activated_after, "FP3")

    def test_lock_setup(self):
        """Test locking a driver setup."""
        manager = ParcFermeManager(weekend_type=WeekendType.NORMAL)

        from src.practice import SetupTuningResult

        setup = SetupTuningResult(
            driver="Verstappen",
            session="FP1",
            aerodynamics=6,
            suspension=5,
            differential=6,
            brake_balance=5,
            tyre_pressure=6,
            r_rating_delta=0.5,
        )

        manager.lock_driver_setup("Verstappen", setup)

        self.assertEqual(manager.get_r_delta("Verstappen"), 0.5)
        self.assertIn("Verstappen", manager.get_locked_setups())

    def test_apply_to_r_rating(self):
        """Test applying delta to R rating."""
        manager = ParcFermeManager(weekend_type=WeekendType.NORMAL)

        from src.practice import SetupTuningResult

        setup = SetupTuningResult(
            driver="Verstappen",
            session="FP1",
            r_rating_delta=0.3,
        )

        manager.lock_driver_setup("Verstappen", setup)

        final_r = manager.apply_to_r_rating("Verstappen", 100.0)
        self.assertEqual(final_r, 100.3)

    def test_normal_weekend_flow(self):
        """Test normal weekend parc fermé flow."""
        coordinator = ParcFermeCoordinator()

        from src.practice import SetupTuningResult

        # Create dummy setups
        fp1_setups = {
            "Driver1": SetupTuningResult("Driver1", "FP1", r_rating_delta=0.2),
            "Driver2": SetupTuningResult("Driver2", "FP1", r_rating_delta=-0.1),
        }
        fp2_setups = {
            "Driver1": SetupTuningResult("Driver1", "FP2", r_rating_delta=0.3),
            "Driver2": SetupTuningResult("Driver2", "FP2", r_rating_delta=0.1),
        }
        fp3_setups = {
            "Driver1": SetupTuningResult("Driver1", "FP3", r_rating_delta=0.1),
            "Driver2": SetupTuningResult("Driver2", "FP3", r_rating_delta=0.0),
        }

        manager = coordinator.setup_normal_weekend(fp1_setups, fp2_setups, fp3_setups)

        self.assertTrue(manager.is_active())
        # Should average the setups
        self.assertIn("Driver1", manager.get_locked_setups())

    def test_sprint_weekend_2022_flow(self):
        """Test 2022 sprint weekend parc fermé flow."""
        coordinator = ParcFermeCoordinator()

        from src.practice import SetupTuningResult

        # Only FP1 setups (2022 rules)
        fp1_setups = {
            "Driver1": SetupTuningResult("Driver1", "FP1", r_rating_delta=0.2),
        }

        manager = coordinator.setup_sprint_weekend_2022(fp1_setups)

        self.assertTrue(manager.is_active())
        self.assertEqual(manager.weekend_type, WeekendType.SPRINT)


class TestPracticeLapSimulator(unittest.TestCase):
    """Tests for lap simulation."""

    def test_r_factor_calculation(self):
        """Test R rating factor calculation."""
        sim = PracticeLapSimulator(seed=42)

        # Higher R = lower factor (faster)
        high_r_factor = sim.calculate_driver_r_factor(105.0)
        low_r_factor = sim.calculate_driver_r_factor(95.0)

        self.assertLess(high_r_factor, low_r_factor)

    def test_fuel_factor(self):
        """Test fuel load factor."""
        sim = PracticeLapSimulator(seed=42)

        light = sim.calculate_fuel_factor(10.0)
        heavy = sim.calculate_fuel_factor(100.0)

        self.assertLess(light, heavy)

    def test_tyre_degradation(self):
        """Test tyre degradation factor."""
        sim = PracticeLapSimulator(seed=42)

        fresh = sim.calculate_tyre_factor(0, "soft")
        worn = sim.calculate_tyre_factor(20, "soft")

        self.assertLess(fresh, worn)

    def test_track_evolution(self):
        """Test track evolution factor."""
        sim = PracticeLapSimulator(seed=42)

        early = sim.calculate_track_evolution(0.0)
        late = sim.calculate_track_evolution(1.0)

        self.assertGreater(early, late)  # Track gets faster

    def test_lap_time_range(self):
        """Test that simulated laps are in reasonable range."""
        sim = PracticeLapSimulator(seed=42)

        lap = sim.simulate_flying_lap(
            driver="Test",
            driver_r=100.0,
            track_base_time=90.0,
        )

        # Lap should be reasonable (within 10% of base)
        self.assertGreater(lap.lap_time, 80.0)
        self.assertLess(lap.lap_time, 100.0)


class TestSetupTuningManager(unittest.TestCase):
    """Tests for setup tuning manager."""

    def test_run_setup_session(self):
        """Test running setup session for multiple drivers."""
        manager = SetupTuningManager(seed=42)

        drivers = ["Driver1", "Driver2", "Driver3"]
        results = manager.run_setup_session(drivers, "FP1")

        self.assertEqual(len(results), 3)
        for driver in drivers:
            self.assertIn(driver, results)
            self.assertIsNotNone(results[driver].r_rating_delta)

    def test_calculate_final_setups_normal(self):
        """Test final setup calculation for normal weekend."""
        manager = SetupTuningManager(seed=42)

        drivers = ["Driver1"]

        # Create session results
        fp1 = manager.run_setup_session(drivers, "FP1")
        fp2 = manager.run_setup_session(drivers, "FP2")
        fp3 = manager.run_setup_session(drivers, "FP3")

        session_results = {
            "fp1": fp1,
            "fp2": fp2,
            "fp3": fp3,
        }

        final = manager.calculate_final_setups(session_results, "normal")

        self.assertIn("Driver1", final)

    def test_calculate_final_setups_sprint(self):
        """Test final setup calculation for sprint weekend."""
        manager = SetupTuningManager(seed=42)

        drivers = ["Driver1"]

        # Only FP1 for sprint
        fp1 = manager.run_setup_session(drivers, "FP1")

        session_results = {"fp1": fp1}

        final = manager.calculate_final_setups(session_results, "sprint")

        self.assertIn("Driver1", final)
        # Should use FP1 only
        self.assertEqual(final["Driver1"].session, "FP1")


if __name__ == "__main__":
    unittest.main()
