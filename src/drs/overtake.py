"""
Overtake System - Confronting Dice Mechanics.

This module implements the Confronting Dice overtake system where each driver
rolls their own 1d10 for dramatic board-game-style tension.

Each driver rolls 1d10 and adds their own modifiers based on:
- DR Value (racecraft)
- R Rating (pace from interval data)
- Situation modifiers (DRS, corner, etc.)

Higher total wins. Tie goes to defender.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


class OvertakeSituation(Enum):
    """Classification of overtake situations"""

    IN_DRS_ZONE = "in_drs_zone"
    END_OF_DRS_ZONE = "end_of_drs_zone"
    ELSEWHERE = "elsewhere"


@dataclass
class ConfrontationResult:
    """
    Result of a dice confrontation between two drivers.

    Each driver rolls 1d10 and adds their modifiers.
    Higher total wins. Tie goes to defender.
    """

    # Attacker info
    attacker_roll: int
    attacker_modifiers: Dict[str, float]
    attacker_total: float

    # Defender info
    defender_roll: int
    defender_modifiers: Dict[str, float]
    defender_total: float

    # Outcome
    winner: str  # "attacker", "defender", "tie"
    margin: float
    situation: OvertakeSituation

    # Push mechanics
    push_available: bool = False
    push_roll: Optional[int] = None
    push_result: Optional[str] = None
    tyre_penalty_applied: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "attacker": {
                "roll": self.attacker_roll,
                "modifiers": self.attacker_modifiers,
                "total": self.attacker_total,
            },
            "defender": {
                "roll": self.defender_roll,
                "modifiers": self.defender_modifiers,
                "total": self.defender_total,
            },
            "winner": self.winner,
            "margin": self.margin,
            "situation": self.situation.value,
            "push_available": self.push_available,
            "push_roll": self.push_roll,
            "push_result": self.push_result,
        }


class OvertakeConfrontation:
    """
    Manages confronting dice for overtakes.

    Each driver rolls 1d10 and adds their own modifiers.
    Higher total wins (tie = defender).
    """

    def __init__(self, track_config=None):
        """
        Initialize the overtake confrontation manager.

        Args:
            track_config: Optional track configuration for track-specific modifiers
        """
        self.track_config = track_config

    def resolve(
        self,
        attacker,
        defender,
        situation: OvertakeSituation,
        interval_history: Optional[List[Dict]] = None,
    ) -> ConfrontationResult:
        """
        Resolve an overtake confrontation.

        Each driver rolls 1d10 and adds their modifiers.
        Higher total wins. Tie goes to defender.

        Args:
            attacker: Driver attempting the overtake
            defender: Driver defending the position
            situation: The overtake situation category
            interval_history: Recent interval data for speed calculations

        Returns:
            ConfrontationResult with the outcome
        """
        # Roll dice for both drivers
        attacker_roll = random.randint(1, 10)
        defender_roll = random.randint(1, 10)

        # Calculate modifiers for each driver
        attacker_mods = self._calc_attacker_mods(
            attacker, defender, situation, interval_history
        )
        defender_mods = self._calc_defender_mods(
            attacker, defender, situation, interval_history
        )

        # Calculate totals
        attacker_total = attacker_roll + sum(attacker_mods.values())
        defender_total = defender_roll + sum(defender_mods.values())

        # Determine winner (tie goes to defender)
        if attacker_total > defender_total:
            winner = "attacker"
        elif defender_total > attacker_total:
            winner = "defender"
        else:
            winner = "tie"

        margin = abs(attacker_total - defender_total)

        # Check push availability (defender wins by <= 3, attacker has fresh tires)
        push_available = (
            winner in ["defender", "tie"]
            and margin <= 3
            and attacker.tyre_degradation < 1.15
        )

        return ConfrontationResult(
            attacker_roll=attacker_roll,
            attacker_modifiers=attacker_mods,
            attacker_total=attacker_total,
            defender_roll=defender_roll,
            defender_modifiers=defender_mods,
            defender_total=defender_total,
            winner=winner,
            margin=margin,
            situation=situation,
            push_available=push_available,
        )

    def _calc_attacker_mods(
        self, attacker, defender, situation, history
    ) -> Dict[str, float]:
        """Calculate attacker's modifiers based on situation"""
        mods = {"DR": self._get_dr_modifier(attacker.dr_value)}

        if situation == OvertakeSituation.IN_DRS_ZONE:
            if attacker.drs_available:
                mods["DRS_Bonus"] = 3.0
            mods["Speed_Delta"] = self._get_speed_delta_mod(attacker, defender, history)

        elif situation == OvertakeSituation.END_OF_DRS_ZONE:
            mods["Corner_Exit"] = self._get_corner_exit_mod(attacker, defender)
            mods["Brake"] = self._get_brake_mod(attacker)

        else:  # ELSEWHERE
            mods.update(self._get_elsewhere_mods(attacker, situation, history))

        return mods

    def _calc_defender_mods(
        self, attacker, defender, situation, history
    ) -> Dict[str, float]:
        """Calculate defender's modifiers based on situation"""
        mods = {"DR": self._get_dr_modifier(defender.dr_value)}

        if situation == OvertakeSituation.IN_DRS_ZONE:
            if attacker.drs_available:
                mods["DRS_Penalty"] = -3.0
            mods["Grip"] = self._get_grip_mod(defender)

        elif situation == OvertakeSituation.END_OF_DRS_ZONE:
            mods["Line"] = self._get_line_mod(defender)
            if defender.drs_available:
                mods["Defensive"] = 2.0

        else:  # ELSEWHERE
            mods.update(self._get_elsewhere_mods(defender, situation, history))

        return mods

    def _get_dr_modifier(self, dr_value: float) -> float:
        """
        Calculate DR modifier: (DR-80)/2, range -5 to +6

        Examples:
            DR 80 -> -5
            DR 86 ->  0
            DR 92 -> +6
        """
        return (dr_value - 80) / 2.0

    def _get_speed_delta_mod(self, attacker, defender, history) -> float:
        """
        Get speed delta modifier from interval history.

        Returns a modifier based on recent speed comparison.
        """
        if not history or attacker.r_value == defender.r_value:
            return 0.0

        # Base speed delta on R value difference
        r_diff = attacker.r_value - defender.r_value
        # Each 5 R points = +1 modifier
        mod = r_diff / 5.0
        return float(max(-3.0, min(3.0, mod)))

    def _get_corner_exit_mod(self, attacker, defender) -> float:
        """Get corner exit modifier based on track characteristics"""
        if not self.track_config:
            return 1.0  # Default moderate bonus

        track_name = self.track_config.track_name.lower()

        corner_mods = {
            "monza": 3.0,  # Long run, good exit
            "monaco": -2.0,  # Tight hairpin, hard to pass
            "spa": 2.0,  # Fast entry, good opportunities
            "silverstone": 2.0,
            "barcelona": 1.0,
            "bahrain": 1.0,
            "jeddah": 1.0,
            "las_vegas": 1.0,
        }

        return corner_mods.get(track_name, 1.0)

    def _get_brake_mod(self, driver) -> float:
        """
        Get brake control modifier based on DR value.

        Higher DR = better brake control.
        """
        dr_mod = (driver.dr_value - 80) / 12.0  # DR 92 = +1
        return float(max(0.0, min(3.0, dr_mod)))

    def _get_grip_mod(self, driver) -> float:
        """
        Get grip modifier based on DR value.

        Higher DR = better traction.
        """
        dr_mod = (driver.dr_value - 82) / 10.0
        return float(max(0.0, min(2.0, dr_mod)))

    def _get_line_mod(self, driver) -> float:
        """
        Get defensive line modifier based on DR value.

        Higher DR = better defensive positioning.
        """
        dr_mod = (driver.dr_value - 80) / 12.0
        return float(max(0.0, min(3.0, dr_mod)))

    def _get_elsewhere_mods(self, driver, situation, history) -> Dict[str, float]:
        """Get modifiers for non-DRS situations"""
        mods = {}

        if situation == OvertakeSituation.ELSEWHERE:
            # Generic situation - use DR-based modifiers
            dr_based = (driver.dr_value - 80) / 8.0  # DR 92 = +1.5
            mods["Precision"] = float(max(0.0, min(4.0, dr_based + 1.0)))
            mods["Experience"] = float(max(0.0, min(4.0, dr_based + 1.0)))

        return mods

    def execute_push(self, result: ConfrontationResult) -> ConfrontationResult:
        """
        Execute a push after near-miss.

        Args:
            result: The original confrontation result with push available

        Returns:
            Updated result with push outcome
        """
        if not result.push_available:
            return result

        push_roll = random.randint(1, 6)
        new_total = result.attacker_total + push_roll

        if new_total > result.defender_total:
            push_result = "success"
            result.tyre_penalty_applied = True  # Push uses extra energy
        else:
            push_result = "failed"
            result.tyre_penalty_applied = True  # Failed push also uses energy

        return ConfrontationResult(
            attacker_roll=result.attacker_roll,
            attacker_modifiers=result.attacker_modifiers,
            attacker_total=new_total,
            defender_roll=result.defender_roll,
            defender_modifiers=result.defender_modifiers,
            defender_total=result.defender_total,
            winner="attacker" if new_total > result.defender_total else "defender",
            margin=abs(new_total - result.defender_total),
            situation=result.situation,
            push_available=False,
            push_roll=push_roll,
            push_result=push_result,
            tyre_penalty_applied=True,
        )
