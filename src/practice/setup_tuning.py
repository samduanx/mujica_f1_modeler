"""
Setup Tuning Dice Mechanics Module

Implements the dice rolling system for car setup tuning in practice sessions.
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .types import SetupTuningResult, SetupCategory


# Dice roll to R modifier mapping
DICE_MODIFIER_MAP = {
    1: -0.2,  # Poor setup
    2: -0.1,  # Suboptimal
    3: 0.0,  # Neutral
    4: 0.1,  # Good
    5: 0.2,  # Very good
    6: 0.3,  # Optimal
}

# Category descriptions for reporting
CATEGORY_DESCRIPTIONS = {
    SetupCategory.AERODYNAMICS: {
        "name": "Aerodynamics",
        "description": "Downforce/drag balance",
        1: "Unstable aero platform",
        2: "Suboptimal downforce",
        3: "Balanced aero",
        4: "Good downforce balance",
        5: "Excellent aero efficiency",
        6: "Perfect aero setup",
    },
    SetupCategory.SUSPENSION: {
        "name": "Suspension",
        "description": "Mechanical grip",
        1: "Poor mechanical grip",
        2: "Harsh over kerbs",
        3: "Acceptable balance",
        4: "Good kerb handling",
        5: "Excellent compliance",
        6: "Optimal mechanical grip",
    },
    SetupCategory.DIFFERENTIAL: {
        "name": "Differential",
        "description": "Traction/power delivery",
        1: "Poor traction out of corners",
        2: "Some wheelspin issues",
        3: "Standard diff settings",
        4: "Good traction",
        5: "Strong corner exit",
        6: "Perfect power delivery",
    },
    SetupCategory.BRAKE_BALANCE: {
        "name": "Brake Balance",
        "description": "Braking stability",
        1: "Unstable under braking",
        2: "Minor lock-up issues",
        3: "Balanced braking",
        4: "Good brake feel",
        5: "Excellent stability",
        6: "Optimal brake balance",
    },
    SetupCategory.TYRE_PRESSURE: {
        "name": "Tyre Pressure",
        "description": "Tyre wear and grip",
        1: "Poor tyre window",
        2: "Some graining",
        3: "In the window",
        4: "Good tyre management",
        5: "Excellent tyre life",
        6: "Perfect tyre window",
    },
}


class SetupDiceRoller:
    """
    Handles dice rolling for setup tuning.

    Uses 1d6 per category with the following mapping:
    - 1: -0.2 (Poor)
    - 2: -0.1 (Suboptimal)
    - 3: 0.0 (Neutral)
    - 4: +0.1 (Good)
    - 5: +0.2 (Very good)
    - 6: +0.3 (Optimal)

    Best Setup Locking Mechanism:
    - Tracks best setup results for each driver across sessions
    - If a category already has the maximum roll (6), it's locked and won't change
    - Significantly reduced probability for roll 6 (from 16.7% to ~5%)
    """

    # Best roll value (6 = +0.3 modifier)
    BEST_ROLL = 6

    # Reduced probability weights for rolling - heavily weighted towards middle values
    # Original: equal 1/6 chance for each value
    # New: reduced chance for extreme values (1 and 6), higher chance for middle values
    WEIGHTED_ROLL_CHOICES = [1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 6]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the dice roller.

        Args:
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random

        # Track best setup results per driver across sessions
        # Format: {driver_name: {SetupCategory: best_roll_value}}
        self.best_results: Dict[str, Dict[SetupCategory, int]] = {}

    def roll_d6(self) -> int:
        """Roll a 6-sided die with weighted probability (reduced chance for best/worst)."""
        return self.rng.choice(self.WEIGHTED_ROLL_CHOICES)

    def roll_setup_category(self, category: SetupCategory, driver: str) -> int:
        """
        Roll for a specific setup category.

        If the driver already has the best result (6) for this category,
        the category is locked and won't change.

        Args:
            category: The setup category to roll for
            driver: Driver name for tracking best results

        Returns:
            Dice roll result (1-6)
        """
        # Check if driver has a best result recorded
        if driver in self.best_results:
            driver_best = self.best_results[driver]
            # If this category already has the best roll, keep it locked
            if category in driver_best and driver_best[category] == self.BEST_ROLL:
                return self.BEST_ROLL  # Locked at best value

        return self.roll_d6()

    def roll_all_categories(self, driver: str) -> Dict[SetupCategory, int]:
        """
        Roll dice for all setup categories.

        Args:
            driver: Driver name for tracking best results

        Returns:
            Dictionary mapping categories to roll results
        """
        results = {}
        for category in SetupCategory:
            results[category] = self.roll_setup_category(category, driver)
        return results

    def roll_for_driver(self, driver: str) -> Dict[SetupCategory, int]:
        """
        Roll setup dice for a driver.

        Args:
            driver: Driver name

        Returns:
            Dictionary of category rolls
        """
        return self.roll_all_categories(driver)

    def update_best_results(self, driver: str, rolls: Dict[SetupCategory, int]):
        """
        Update the best results tracking for a driver.

        This should be called after each session to lock in best results.

        Args:
            driver: Driver name
            rolls: Dictionary of category to roll value
        """
        if driver not in self.best_results:
            self.best_results[driver] = {}

        for category, roll in rolls.items():
            current_best = self.best_results[driver].get(category, 0)
            # Only update if this roll is better (higher = better)
            if roll > current_best:
                self.best_results[driver][category] = roll

    def is_category_locked(self, driver: str, category: SetupCategory) -> bool:
        """
        Check if a category is locked (has best result) for a driver.

        Args:
            driver: Driver name
            category: Setup category

        Returns:
            True if category is locked at best value
        """
        if driver not in self.best_results:
            return False
        return self.best_results[driver].get(category) == self.BEST_ROLL

    def get_locked_categories(self, driver: str) -> List[SetupCategory]:
        """
        Get list of locked categories for a driver.

        Args:
            driver: Driver name

        Returns:
            List of categories that are locked at best value
        """
        if driver not in self.best_results:
            return []
        return [
            cat
            for cat, roll in self.best_results[driver].items()
            if roll == self.BEST_ROLL
        ]


class SetupEffectCalculator:
    """
    Calculates setup effects from dice rolls.
    """

    @staticmethod
    def get_modifier_from_roll(roll: int) -> float:
        """
        Get R modifier from a dice roll.

        Args:
            roll: Dice roll (1-6)

        Returns:
            R rating modifier
        """
        return DICE_MODIFIER_MAP.get(roll, 0.0)

    @classmethod
    def calculate_total_effect(cls, rolls: Dict[SetupCategory, int]) -> float:
        """
        Calculate total effect from all category rolls.

        Args:
            rolls: Dictionary of category to roll value

        Returns:
            Sum of all modifiers
        """
        return sum(cls.get_modifier_from_roll(roll) for roll in rolls.values())

    @staticmethod
    def normalize_to_r_delta(
        total_effect: float, min_delta: float = -0.5, max_delta: float = 0.5
    ) -> float:
        """
        Normalize total effect to R rating delta range.

        Args:
            total_effect: Sum of all modifiers
            min_delta: Minimum allowed delta
            max_delta: Maximum allowed delta

        Returns:
            Clamped R rating delta
        """
        return max(min_delta, min(max_delta, total_effect))

    @classmethod
    def create_setup_result(
        cls,
        driver: str,
        session: str,
        rolls: Dict[SetupCategory, int],
    ) -> SetupTuningResult:
        """
        Create a complete setup result from dice rolls.

        Args:
            driver: Driver name
            session: Session name
            rolls: Dictionary of category rolls

        Returns:
            SetupTuningResult with calculated effects
        """
        total_effect = cls.calculate_total_effect(rolls)
        r_delta = cls.normalize_to_r_delta(total_effect)

        # Generate summary
        summary_parts = []
        for category, roll in rolls.items():
            desc = CATEGORY_DESCRIPTIONS[category][roll]
            modifier = cls.get_modifier_from_roll(roll)
            summary_parts.append(f"{category.value}: {roll} ({modifier:+.1f}) - {desc}")

        return SetupTuningResult(
            driver=driver,
            session=session,
            aerodynamics=rolls.get(SetupCategory.AERODYNAMICS, 3),
            suspension=rolls.get(SetupCategory.SUSPENSION, 3),
            differential=rolls.get(SetupCategory.DIFFERENTIAL, 3),
            brake_balance=rolls.get(SetupCategory.BRAKE_BALANCE, 3),
            tyre_pressure=rolls.get(SetupCategory.TYRE_PRESSURE, 3),
            total_effect=total_effect,
            r_rating_delta=r_delta,
            effect_summary="; ".join(summary_parts),
        )

    @classmethod
    def average_setups(cls, setups: List[SetupTuningResult]) -> SetupTuningResult:
        """
        Average multiple setup results (for normal weekends with multiple FP sessions).

        Args:
            setups: List of setup results to average

        Returns:
            Averaged setup result
        """
        if not setups:
            return SetupTuningResult(driver="", session="")

        if len(setups) == 1:
            return setups[0]

        driver = setups[0].driver
        sessions = "+".join(s.session for s in setups)

        # Average each category
        avg_aero = round(sum(s.aerodynamics for s in setups) / len(setups))
        avg_susp = round(sum(s.suspension for s in setups) / len(setups))
        avg_diff = round(sum(s.differential for s in setups) / len(setups))
        avg_brake = round(sum(s.brake_balance for s in setups) / len(setups))
        avg_tyre = round(sum(s.tyre_pressure for s in setups) / len(setups))

        # Calculate new total effect
        rolls = {
            SetupCategory.AERODYNAMICS: avg_aero,
            SetupCategory.SUSPENSION: avg_susp,
            SetupCategory.DIFFERENTIAL: avg_diff,
            SetupCategory.BRAKE_BALANCE: avg_brake,
            SetupCategory.TYRE_PRESSURE: avg_tyre,
        }

        total_effect = cls.calculate_total_effect(rolls)
        r_delta = cls.normalize_to_r_delta(total_effect)

        return SetupTuningResult(
            driver=driver,
            session=sessions,
            aerodynamics=avg_aero,
            suspension=avg_susp,
            differential=avg_diff,
            brake_balance=avg_brake,
            tyre_pressure=avg_tyre,
            total_effect=total_effect,
            r_rating_delta=r_delta,
            effect_summary=f"Averaged from {len(setups)} sessions",
        )


class SetupTuningManager:
    """
    Manages setup tuning for all drivers in a session.
    
    Implements best setup locking mechanism:
    - Tracks best setup results for each driver across multiple sessions
    - If a category achieves the maximum roll (6 = +0.3), it becomes locked
    - Locked categories won't be re-rolled in subsequent sessions
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the setup tuning manager.
        
        Args:
            seed: Optional random seed
        """
        self.roller = SetupDiceRoller(seed)
        self.calculator = SetupEffectCalculator()
    
    def run_setup_session(
        self,
        drivers: List[str],
        session: str,
    ) -> Dict[str, SetupTuningResult]:
        """
        Run setup tuning for all drivers in a session.
        
        If a driver has locked categories (best roll achieved in previous sessions),
        those categories will not be re-rolled.
        
        Args:
            drivers: List of driver names
            session: Session name (FP1, FP2, FP3)
            
        Returns:
            Dictionary mapping drivers to their setup results
        """
        results = {}
        
        for driver in drivers:
            # Check for locked categories before rolling
            locked_cats = self.roller.get_locked_categories(driver)
            if locked_cats:
                locked_str = ", ".join([c.value for c in locked_cats])
                print(f"    {driver}: Locked categories ({locked_str}) - keeping best results")
            
            rolls = self.roller.roll_for_driver(driver)
            result = self.calculator.create_setup_result(driver, session, rolls)
            results[driver] = result
            
            # Update best results tracking after each session
            self.roller.update_best_results(driver, rolls)
            
            # Report any newly locked categories
            new_locked = self.roller.get_locked_categories(driver)
            newly_locked = [c for c in new_locked if c not in locked_cats]
            if newly_locked:
                for cat in newly_locked:
                    print(f"    {driver}: {cat.value} locked at best result (+0.3)")
        
        return results

    def calculate_final_setups(
        self,
        session_results: Dict[str, Dict[str, SetupTuningResult]],
        weekend_type: str,
    ) -> Dict[str, SetupTuningResult]:
        """
        Calculate final setups after all practice sessions.

        For normal weekends: Average FP1, FP2, FP3
        For sprint weekends: Use only FP1

        Args:
            session_results: Dictionary of session name -> driver setups
            weekend_type: "normal" or "sprint"

        Returns:
            Dictionary of final driver setups
        """
        if not session_results:
            return {}

        # Get all drivers from first session
        first_session = list(session_results.values())[0]
        drivers = list(first_session.keys())

        final_setups = {}

        for driver in drivers:
            if weekend_type == "sprint":
                # Sprint weekends: Only FP1 matters
                if "fp1" in session_results and driver in session_results["fp1"]:
                    final_setups[driver] = session_results["fp1"][driver]
            else:
                # Normal weekends: Average all sessions
                setups = []
                for session_data in session_results.values():
                    if driver in session_data:
                        setups.append(session_data[driver])

                if setups:
                    final_setups[driver] = self.calculator.average_setups(setups)

        return final_setups

    def get_category_description(self, category: SetupCategory, roll: int) -> str:
        """
        Get description for a category roll.

        Args:
            category: Setup category
            roll: Dice roll (1-6)

        Returns:
            Description string
        """
        return CATEGORY_DESCRIPTIONS[category].get(roll, "Unknown")

    def generate_setup_report(
        self,
        setups: Dict[str, SetupTuningResult],
    ) -> str:
        """
        Generate a text report of setup results.

        Args:
            setups: Dictionary of driver setups

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 90)
        lines.append("SETUP TUNING DICE RESULTS")
        lines.append("=" * 90)
        lines.append(
            f"{'Driver':<20} {'Aero':<6} {'Susp':<6} {'Diff':<6} "
            f"{'Brake':<6} {'Tyre':<6} | {'Total':<8} {'R Delta':<8}"
        )
        lines.append("-" * 90)

        # Sort by R delta (best to worst)
        sorted_setups = sorted(
            setups.items(), key=lambda x: x[1].r_rating_delta, reverse=True
        )

        for driver, setup in sorted_setups:
            lines.append(
                f"{driver:<20} "
                f"{setup.aerodynamics:<6} "
                f"{setup.suspension:<6} "
                f"{setup.differential:<6} "
                f"{setup.brake_balance:<6} "
                f"{setup.tyre_pressure:<6} | "
                f"{setup.total_effect:>+6.1f}   "
                f"{setup.r_rating_delta:>+6.2f}"
            )

        lines.append("=" * 90)
        return "\n".join(lines)
