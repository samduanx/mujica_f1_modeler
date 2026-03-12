"""
Dice Rolling Utilities for Incident System.

Provides random number generation for dice-based mechanics.
"""

import random
from typing import Dict, List, Optional, Tuple, Union


def roll_d6() -> int:
    """Roll a 6-sided die (1-6)"""
    return random.randint(1, 6)


def roll_d10() -> int:
    """Roll a 10-sided die (1-10)"""
    return random.randint(1, 10)


def roll_d20() -> int:
    """Roll a 20-sided die (1-20)"""
    return random.randint(1, 20)


def roll_d100() -> int:
    """Roll a 100-sided die (1-100)"""
    return random.randint(1, 100)


def roll_nd6(n: int) -> Tuple[int, List[int]]:
    """
    Roll n 6-sided dice.

    Args:
        n: Number of dice to roll

    Returns:
        Tuple of (total, list of individual rolls)
    """
    rolls = [random.randint(1, 6) for _ in range(n)]
    return sum(rolls), rolls


def roll_nd10(n: int) -> Tuple[int, List[int]]:
    """
    Roll n 10-sided dice.

    Args:
        n: Number of dice to roll

    Returns:
        Tuple of (total, list of individual rolls)
    """
    rolls = [random.randint(1, 10) for _ in range(n)]
    return sum(rolls), rolls


def roll_10d100() -> Tuple[int, List[int]]:
    """
    Roll 10 100-sided dice (for stability checks).

    Based on dice_rolling_rules.md:
    - 10d100 for stability check
    - Compare against stability threshold

    Returns:
        Tuple of (total, list of individual rolls)
    """
    rolls = [random.randint(1, 100) for _ in range(10)]
    return sum(rolls), rolls


def roll_with_modifier(
    dice_type: str = "d10", modifier: int = 0, bonus: int = 0, penalty: int = 0
) -> Dict:
    """
    Roll a die with modifiers applied.

    Args:
        dice_type: Type of die to roll (d6, d10, d20, d100)
        modifier: Base modifier to add
        bonus: Bonus to add
        penalty: Penalty to subtract

    Returns:
        Dictionary with roll details
    """
    # Roll the die
    dice_funcs = {
        "d6": roll_d6,
        "d10": roll_d10,
        "d20": roll_d20,
        "d100": roll_d100,
    }

    roll_func = dice_funcs.get(dice_type, roll_d10)
    base_roll = roll_func()

    # Calculate total
    total = base_roll + modifier + bonus - penalty

    return {
        "dice_type": dice_type,
        "base_roll": base_roll,
        "modifier": modifier,
        "bonus": bonus,
        "penalty": penalty,
        "total": total,
    }


class DiceRoller:
    """
    Dice rolling utility class for incident system.

    Provides consistent dice rolling with optional seeding
    for reproducible results.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize dice roller with optional seed.

        Args:
            seed: Random seed for reproducible results (None = random)
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def reset_seed(self, seed: Optional[int] = None):
        """
        Reset random seed.

        Args:
            seed: New seed (None = random)
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def roll_d6(self) -> int:
        """Roll a 6-sided die"""
        return random.randint(1, 6)

    def roll_d10(self) -> int:
        """Roll a 10-sided die"""
        return random.randint(1, 10)

    def roll_d20(self) -> int:
        """Roll a 20-sided die"""
        return random.randint(1, 20)

    def roll_d100(self) -> int:
        """Roll a 100-sided die"""
        return random.randint(1, 100)

    def roll_10d100(self) -> Tuple[int, List[int]]:
        """
        Roll 10 100-sided dice for stability check.

        Returns:
            Tuple of (total, individual rolls)
        """
        rolls = [random.randint(1, 100) for _ in range(10)]
        return sum(rolls), rolls

    def roll_for_stability(
        self, stability: float, check_type: str = "normal", team_name: str = None
    ) -> Dict:
        """
        Roll for stability check based on dice_rolling_rules.md.

        Args:
            stability: Team stability value (95-100)
            check_type: Type of check ("normal", "engine", "mechanical", "tyre")
            team_name: Team name for narrative assistance

        Returns:
            Dictionary with roll details and result
        """
        # Apply narrative assistance to stability if enabled
        if team_name:
            try:
                from src.core.narrative_assist import ProbabilityBalancer

                balancer = ProbabilityBalancer()
                stability = balancer.balance_stability(stability, team_name)
            except ImportError:
                pass
        total, rolls = self.roll_10d100()

        # Determine result based on stability
        if stability >= 96:
            # High stability thresholds
            if check_type == "normal":
                if total <= 800:  # 1-80 on each d100
                    result = "no_incident"
                elif total <= 900:  # 81-90
                    result = "driver_error"
                else:  # 91-100
                    result = "mechanical_fault"
            elif check_type == "engine":
                result = self._resolve_engine_fault(total)
            elif check_type == "mechanical":
                result = self._resolve_mechanical_fault(total)
            elif check_type == "tyre":
                result = self._resolve_tyre_fault(total)
            else:
                result = "no_incident"
        else:
            # Lower stability thresholds
            if check_type == "normal":
                if total <= 900:  # 1-90 on each d100
                    result = "no_incident"
                elif total <= 950:  # 91-95
                    result = "driver_error"
                else:  # 96-100
                    result = "mechanical_fault"
            elif check_type == "engine":
                result = self._resolve_engine_fault(total)
            elif check_type == "mechanical":
                result = self._resolve_mechanical_fault(total)
            elif check_type == "tyre":
                result = self._resolve_tyre_fault(total)
            else:
                result = "no_incident"

        return {
            "rolls": rolls,
            "total": total,
            "stability": stability,
            "result": result,
        }

    def _resolve_engine_fault(self, total: int) -> Dict:
        """Resolve engine fault type based on dice roll"""
        roll = random.randint(1, 10)

        fault_types = {
            (1, 3): {"type": "internal_combustion", "severity": "major"},
            (4, 6): {"type": "hybrid_system", "severity": "major"},
            (7, 9): {"type": "battery_or_oil", "severity": "moderate"},
            (10, 10): {"type": "catastrophic", "severity": "terminal"},
        }

        for range_roll, fault_info in fault_types.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return fault_info

        return {"type": "unknown", "severity": "minor"}

    def _resolve_mechanical_fault(self, total: int) -> Dict:
        """Resolve mechanical fault type based on dice roll"""
        roll = random.randint(1, 10)

        fault_types = {
            (1, 3): {"type": "chassis_suspension", "severity": "major"},
            (4, 6): {"type": "hydraulics", "severity": "major"},
            (7, 9): {"type": "electrical", "severity": "moderate"},
            (10, 10): {"type": "catastrophic", "severity": "terminal"},
        }

        for range_roll, fault_info in fault_types.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return fault_info

        return {"type": "unknown", "severity": "minor"}

    def _resolve_tyre_fault(self, total: int) -> Dict:
        """Resolve tyre fault type based on dice roll"""
        roll = random.randint(1, 10)

        fault_types = {
            (1, 3): {"type": "debris_damage", "severity": "moderate"},
            (4, 6): {"type": "overheating_burst", "severity": "major"},
            (7, 9): {"type": "manufacturing_defect", "severity": "moderate"},
            (10, 10): {"type": "structural_failure", "severity": "major"},
        }

        for range_roll, fault_info in fault_types.items():
            if range_roll[0] <= roll <= range_roll[1]:
                return fault_info

        return {"type": "unknown", "severity": "minor"}
