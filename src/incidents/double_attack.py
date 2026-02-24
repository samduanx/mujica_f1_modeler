"""
Double Attack System.

Handles counter-attack scenarios where defender immediately attacks after being overtaken.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

from incidents.incident_types import IncidentSeverity


@dataclass
class DoubleAttackResult:
    """Result of a double attack confrontation"""
    attacker: str  # Original attacker who was counter-attacked
    defender: str  # Original defender who initiated counter-attack
    attacker_roll: int
    defender_roll: int
    attacker_total: float
    defender_total: float
    winner: str  # "attacker", "defender", or "tie"
    margin: float
    position_changed: bool = False
    narrative: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "attacker": self.attacker,
            "defender": self.defender,
            "attacker_roll": self.attacker_roll,
            "defender_roll": self.defender_roll,
            "attacker_total": self.attacker_total,
            "defender_total": self.defender_total,
            "winner": self.winner,
            "margin": self.margin,
            "position_changed": self.position_changed,
            "narrative": self.narrative,
        }


class DoubleAttackSystem:
    """
    Handle double-attack scenarios where defender immediately counters.
    """
    
    def __init__(self):
        self.double_attack_enabled = True
        self.cooldown_seconds = 3.0  # Minimum time before counter
        self.min_speed_delta = 0.5  # Speed delta threshold for trigger
        
    def can_initiate_double_attack(
        self,
        time_since_overtake: float,
        defender_tyre_degradation: float,
        attacker_has_drs: bool,
        defender_has_drs: bool,
        defender_dr: float,
        attacker_dr: float,
    ) -> Tuple[bool, str]:
        """
        Determine if defender can initiate double attack.
        
        Args:
            time_since_overtake: Seconds since original overtake
            defender_tyre_degradation: Defender's tyre degradation
            attacker_has_drs: Whether attacker has DRS
            defender_has_drs: Whether defender has DRS
            defender_dr: Defender's DR value
            attacker_dr: Attacker's DR value
            
        Returns:
            Tuple of (can_attack, reason)
        """
        # Check cooldown
        if time_since_overtake < self.cooldown_seconds:
            return False, f"Cooldown active ({time_since_overtake:.1f}s)"
            
        # Check if defender has fresh tyres
        if defender_tyre_degradation > 1.15:
            return False, "Tyres too degraded"
            
        # Check DRS balance
        if attacker_has_drs and not defender_has_drs:
            return False, "Attacker has DRS advantage"
            
        # Check DR - defender must be competitive
        dr_diff = defender_dr - attacker_dr
        if dr_diff < -5:
            return False, f"DR too low for counter-attack ({defender_dr:.0f} vs {attacker_dr:.0f})"
            
        return True, "Double attack available"
    
    def get_double_attack_probability(
        self,
        time_since_overtake: float,
        dr_diff: float,
        defender_has_drs: bool,
    ) -> float:
        """
        Calculate probability of double attack occurring.
        
        Args:
            time_since_overtake: Seconds since overtake
            dr_diff: DR difference (defender - attacker)
            defender_has_drs: Whether defender has DRS
            
        Returns:
            Probability of double attack (0.0 to 1.0)
        """
        # Base probability
        prob = 0.3  # 30% base chance
        
        # Time since overtake factor (more likely soon after)
        if time_since_overtake < 2.0:
            prob *= 1.5
        elif time_since_overtake < 5.0:
            prob *= 1.2
        elif time_since_overtake > 10.0:
            prob *= 0.5
            
        # DR factor
        if dr_diff > 3:
            prob *= 1.3
        elif dr_diff > 0:
            prob *= 1.1
        elif dr_diff < -2:
            prob *= 0.7
            
        # DRS factor
        if defender_has_drs:
            prob *= 1.2
            
        return min(0.6, max(0.1, prob))


class DoubleAttackConfrontation:
    """
    Resolve double-attack scenarios using confronting dice.
    """
    
    # Double attack modifiers
    ATTACKER_PENALTY = -2.0  # Defending is harder
    DEFENDER_BONUS = 2.0  # Fresh attack
    
    def resolve(
        self,
        attacker_name: str,
        attacker_dr: float,
        defender_name: str,
        defender_dr: float,
        defender_has_drs: bool = False,
        attacker_has_drs: bool = False,
        situation: str = "in_drs_zone",
    ) -> DoubleAttackResult:
        """
        Resolve double-attack confrontation.
        
        Special rules for double attacks:
        - Attacker gets -2 penalty (defending position is harder)
        - Defender gets +2 bonus (fresh attack)
        - Same dice formula as normal overtake
        
        Args:
            attacker_name: Original attacker's name
            attacker_dr: Original attacker's DR value
            defender_name: Original defender's name (now attacker)
            defender_dr: Original defender's DR value
            defender_has_drs: Whether defender has DRS
            attacker_has_drs: Whether attacker has DRS
            situation: Overtake situation type
            
        Returns:
            DoubleAttackResult with outcome
        """
        # Roll dice for both drivers
        attacker_roll = random.randint(1, 10)
        defender_roll = random.randint(1, 10)
        
        # Calculate DR modifiers
        attacker_dr_mod = (attacker_dr - 80) / 2  # -5 to +6
        defender_dr_mod = (defender_dr - 80) / 2  # -5 to +6
        
        # Calculate situation modifiers
        attacker_sit_mod = self._get_situation_modifier(situation, attacker_has_drs, True)
        defender_sit_mod = self._get_situation_modifier(situation, defender_has_drs, False)
        
        # Apply double attack specific modifiers
        attacker_total = attacker_roll + attacker_dr_mod + attacker_sit_mod + self.ATTACKER_PENALTY
        defender_total = defender_roll + defender_dr_mod + defender_sit_mod + self.DEFENDER_BONUS
        
        # Determine winner (tie goes to defender)
        if attacker_total > defender_total:
            winner = "attacker"
        elif defender_total > attacker_total:
            winner = "defender"
        else:
            winner = "tie"
            
        margin = abs(attacker_total - defender_total)
        position_changed = winner != "attacker"
        
        # Generate narrative
        narrative = self._generate_narrative(
            attacker_name, defender_name, winner, margin, situation
        )
        
        return DoubleAttackResult(
            attacker=attacker_name,
            defender=defender_name,
            attacker_roll=attacker_roll,
            defender_roll=defender_roll,
            attacker_total=attacker_total,
            defender_total=defender_total,
            winner=winner,
            margin=margin,
            position_changed=position_changed,
            narrative=narrative,
        )
    
    def _get_situation_modifier(
        self,
        situation: str,
        has_drs: bool,
        is_attacker: bool,
    ) -> float:
        """Get situation modifier for double attack"""
        mods = {}
        
        if situation == "in_drs_zone":
            if is_attacker and has_drs:
                mods["DRS_Bonus"] = 3.0
            elif not is_attacker and has_drs:
                mods["DRS_Penalty"] = -3.0
        elif situation == "end_of_drs_zone":
            if not is_attacker and has_drs:
                mods["Defensive"] = 2.0
                
        return sum(mods.values()) if mods else 0.0
    
    def _generate_narrative(
        self,
        attacker: str,
        defender: str,
        winner: str,
        margin: float,
        situation: str,
    ) -> str:
        """Generate narrative for double attack result"""
        if winner == "attacker":
            narratives = [
                f"{defender} attempts an immediate counter-attack at {situation}, "
                f"but {attacker} defends successfully!",
                f"{attacker} holds off {defender}'s fierce counter-attack "
                f"in the {situation} battle.",
            ]
        elif winner == "defender":
            narratives = [
                f"DOUBLE ATTACK! {defender} immediately counters "
                f"{attacker} at {situation} and retakes the position!",
                f"What a response! {defender} immediately strikes back "
                f"against {attacker} in the {situation}!",
            ]
        else:
            narratives = [
                f"Epic battle! {attacker} and {defender} fight wheel-to-wheel "
                f"in {situation}, but neither can gain the advantage.",
                f"Incredible defending by {attacker} keeps {defender} at bay "
                f"in the {situation} scrap.",
            ]
            
        return random.choice(narratives)


class DoubleAttackSimulator:
    """
    Simulate double attack scenarios throughout a race.
    """
    
    def __init__(self):
        """Initialize simulator"""
        self.double_attack_system = DoubleAttackSystem()
        self.confrontation = DoubleAttackConfrontation()
        self.results: List[DoubleAttackResult] = []
        self.double_attack_count = 0
        
    def check_double_attack(
        self,
        attacker_name: str,
        attacker_dr: float,
        attacker_tyre_deg: float,
        attacker_has_drs: bool,
        defender_name: str,
        defender_dr: float,
        defender_tyre_deg: float,
        defender_has_drs: bool,
        time_since_overtake: float,
    ) -> Optional[DoubleAttackResult]:
        """
        Check for and resolve double attack.
        
        Returns:
            DoubleAttackResult if double attack occurs, None otherwise
        """
        if not self.double_attack_system.double_attack_enabled:
            return None
            
        # Check if double attack is possible
        can_attack, reason = self.double_attack_system.can_initiate_double_attack(
            time_since_overtake=time_since_overtake,
            defender_tyre_degradation=defender_tyre_deg,
            attacker_has_drs=attacker_has_drs,
            defender_has_drs=defender_has_drs,
            defender_dr=defender_dr,
            attacker_dr=attacker_dr,
        )
        
        if not can_attack:
            return None
            
        # Check probability
        dr_diff = defender_dr - attacker_dr
        prob = self.double_attack_system.get_double_attack_probability(
            time_since_overtake=time_since_overtake,
            dr_diff=dr_diff,
            defender_has_drs=defender_has_drs,
        )
        
        if random.random() > prob:
            return None
            
        # Resolve double attack
        result = self.confrontation.resolve(
            attacker_name=attacker_name,
            attacker_dr=attacker_dr,
            defender_name=defender_name,
            defender_dr=defender_dr,
            defender_has_drs=defender_has_drs,
            attacker_has_drs=attacker_has_drs,
        )
        
        self.results.append(result)
        self.double_attack_count += 1
        
        return result
    
    def get_statistics(self) -> Dict:
        """Get double attack statistics"""
        if not self.results:
            return {"total_double_attacks": 0}
            
        attacker_wins = sum(1 for r in self.results if r.winner == "attacker")
        defender_wins = sum(1 for r in self.results if r.winner == "defender")
        ties = sum(1 for r in self.results if r.winner == "tie")
        
        return {
            "total_double_attacks": self.double_attack_count,
            "attacker_defense_success_rate": attacker_wins / len(self.results),
            "defender_counter_success_rate": defender_wins / len(self.results),
            "ties": ties,
            "position_changes": sum(1 for r in self.results if r.position_changed),
        }
