"""
Lapping Overtake System.

Extends the base OvertakeConfrontation with blue flag compliance mechanics
for lapping situations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from drs.overtake import OvertakeConfrontation, OvertakeSituation, ConfrontationResult


# Section suitability for lapping overtakes (how easy it is for lapped car to give way)
SECTION_SUITABILITY = {
    "straight": 1.0,  # Ideal - easy to move aside
    "drs_zone": 1.0,  # Ideal - easy to move aside
    "corner_exit": 0.7,  # OK if careful
    "corner_entry": 0.3,  # Risky, drivers avoid
    "corner_apex": 0.0,  # Unsafe, won't give way
    "braking_zone": 0.1,  # Very unsafe
    "s_curve": 0.5,  # Moderate
    "hairpin": 0.2,  # Difficult
    "tech_section": 0.3,  # Difficult
}


@dataclass
class LappingResult:
    """
    Result of a lapping overtake attempt.

    This includes blue flag compliance, resistance factors, and any penalties.
    """

    success: bool  # Did the leader successfully lap the car?
    leader: str  # Name of the leading driver
    lapped_car: str  # Name of the lapped driver
    compliance_score: float  # How well the lapped car complied (0.0-1.0)
    resistance_score: float  # Resistance level (0.0-1.0)
    violation: bool  # Was there a blue flag violation?
    penalty: Optional[str]  # Penalty applied to lapped car (if any)
    narrative: str  # Narrative description of the event
    section_suitability: float  # Track section suitability (0.0-1.0)
    blue_flag_complied: bool  # Did the lapped car comply with blue flags?

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "leader": self.leader,
            "lapped_car": self.lapped_car,
            "compliance_score": self.compliance_score,
            "resistance_score": self.resistance_score,
            "violation": self.violation,
            "penalty": self.penalty,
            "narrative": self.narrative,
            "section_suitability": self.section_suitability,
            "blue_flag_complied": self.blue_flag_complied,
        }


class LappingOvertake(OvertakeConfrontation):
    """
    Overtake system for lapping situations.

    Extends OvertakeConfrontation with blue flag compliance mechanics.
    Lapped cars are expected to give way per blue flags.

    Key differences from normal overtake:
    1. Blue flag compliance gives leader significant advantage (+3 to +5)
    2. Lapped car can choose to resist (but risks penalty)
    3. Track section suitability matters more
    4. Less aggressive racing (safety consideration)
    """

    def __init__(self, track_config=None):
        """
        Initialize the lapping overtake system.

        Args:
            track_config: Optional track configuration for track-specific modifiers
        """
        super().__init__(track_config)

    def resolve_lapping(
        self,
        leader,
        lapped_car,
        blue_flag_state,
        track_section: str,
        blue_flag_complied: bool = True,
        resistance_level=None,
        lap: int = 1,
    ) -> LappingResult:
        """
        Resolve a lapping overtake.

        Key considerations:
        - Blue flag compliance modifier (leader gets +3 to +5 if complied)
        - Lapped car resistance roll (may refuse to give way)
        - Track section safety (won't move over in corners)
        - Penalty risk for lapped car

        Args:
            leader: The leading driver's state (DriverRaceState)
            lapped_car: The lapped driver's state (DriverRaceState)
            blue_flag_state: Current blue flag state
            track_section: Current track section type
            blue_flag_complied: Whether the lapped car complied with blue flags
            resistance_level: Level of resistance shown (if not complied)
            lap: Current lap number

        Returns:
            LappingResult with the outcome
        """
        leader_name = getattr(leader, "name", "Leader")
        lapped_name = getattr(lapped_car, "name", "Lapped")

        # Get section suitability
        section_suitability = SECTION_SUITABILITY.get(track_section, 0.5)

        # In unsafe sections, lapped cars are justified in not giving way
        if section_suitability < 0.3:
            # Lapped car cannot safely give way
            return self._create_unsafe_section_result(
                leader_name, lapped_name, track_section, section_suitability
            )

        # Calculate compliance score (0.0 to 1.0)
        compliance_score = self._calculate_compliance_score(
            blue_flag_complied, blue_flag_state, track_section
        )

        # Calculate resistance score (0.0 to 1.0)
        resistance_score = self._calculate_resistance_score(
            blue_flag_complied, resistance_level
        )

        # Check if leader successfully laps the car
        if blue_flag_complied:
            # Lapped car gives way - leader gets by with minimal issue
            success = True
            violation = False
            penalty = None
            narrative = self._create_compliance_narrative(
                leader_name, lapped_name, track_section, compliance_score
            )
        else:
            # Lapped car resists - may still let leader through or cause incident
            success, violation, penalty = self._resolve_resistance(
                leader,
                lapped_car,
                resistance_level,
                section_suitability,
                lap,
            )
            narrative = self._create_resistance_narrative(
                leader_name,
                lapped_name,
                track_section,
                resistance_level,
                success,
                violation,
            )

        return LappingResult(
            success=success,
            leader=leader_name,
            lapped_car=lapped_name,
            compliance_score=compliance_score,
            resistance_score=resistance_score,
            violation=violation,
            penalty=penalty,
            narrative=narrative,
            section_suitability=section_suitability,
            blue_flag_complied=blue_flag_complied,
        )

    def _create_unsafe_section_result(
        self, leader_name: str, lapped_name: str, track_section: str, suitability: float
    ) -> LappingResult:
        """Create a result for when section is too unsafe to give way"""
        return LappingResult(
            success=False,
            leader=leader_name,
            lapped_car=lapped_name,
            compliance_score=0.0,
            resistance_score=0.0,
            violation=False,  # Not a violation - section was unsafe
            penalty=None,
            narrative=f"{lapped_name} stays on racing line through {track_section} - too unsafe to give way",
            section_suitability=suitability,
            blue_flag_complied=False,
        )

    def _calculate_compliance_score(
        self, blue_flag_complied: bool, blue_flag_state, track_section: str
    ) -> float:
        """
        Calculate compliance score (0.0 to 1.0).

        Higher scores indicate better compliance with blue flags.
        """
        if not blue_flag_complied:
            return 0.0

        # Base compliance score
        score = 0.7

        # Bonus for immediate compliance (on WARNING vs FINAL)
        from incidents.blue_flag import BlueFlagState

        if blue_flag_state == BlueFlagState.WARNING:
            score += 0.2  # Complied early
        elif blue_flag_state == BlueFlagState.FINAL:
            score += 0.1  # Complied at final warning

        # Section modifier
        section_mod = SECTION_SUITABILITY.get(track_section, 0.5)
        score *= (0.7 + 0.3 * section_mod)  # Section affects how clean the compliance was

        return min(1.0, score)

    def _calculate_resistance_score(
        self, blue_flag_complied: bool, resistance_level
    ) -> float:
        """
        Calculate resistance score (0.0 to 1.0).

        Higher scores indicate more resistance to blue flags.
        """
        if blue_flag_complied:
            return 0.0

        from incidents.blue_flag import ResistanceLevel

        resistance_scores = {
            ResistanceLevel.NONE: 0.0,
            ResistanceLevel.MINOR: 0.2,
            ResistanceLevel.MODERATE: 0.5,
            ResistanceLevel.STRONG: 0.8,
            ResistanceLevel.VIOLATION: 1.0,
        }

        return resistance_scores.get(resistance_level, 0.5)

    def _resolve_resistance(
        self,
        leader,
        lapped_car,
        resistance_level,
        section_suitability: float,
        lap: int,
    ) -> Tuple[bool, bool, Optional[str]]:
        """
        Resolve what happens when lapped car resists.

        Returns:
            Tuple of (success, violation, penalty)
        """
        from incidents.blue_flag import ResistanceLevel

        # Leader may still get by depending on resistance level and DR values
        leader_dr = getattr(leader, "dr_value", 85)
        lapped_dr = getattr(lapped_car, "dr_value", 85)
        dr_advantage = leader_dr - lapped_dr

        # Base success chance for leader
        base_success = 0.6 + (dr_advantage / 50.0)  # DR advantage helps

        # Modify by resistance level
        resistance_modifiers = {
            ResistanceLevel.NONE: 1.0,
            ResistanceLevel.MINOR: 0.8,
            ResistanceLevel.MODERATE: 0.5,
            ResistanceLevel.STRONG: 0.2,
            ResistanceLevel.VIOLATION: 0.1,
        }

        success_chance = base_success * resistance_modifiers.get(resistance_level, 0.5)
        success_chance = max(0.1, min(0.9, success_chance))  # Clamp

        # Roll for success
        success = random.random() < success_chance

        # Determine violation and penalty
        violation = resistance_level in [
            ResistanceLevel.MODERATE,
            ResistanceLevel.STRONG,
            ResistanceLevel.VIOLATION,
        ]

        penalty = None
        if violation:
            penalty = self._determine_penalty(resistance_level)

        return success, violation, penalty

    def _determine_penalty(self, resistance_level) -> str:
        """Determine penalty based on resistance level"""
        from incidents.blue_flag import ResistanceLevel

        penalties = {
            ResistanceLevel.MINOR: "warning_logged",
            ResistanceLevel.MODERATE: "warning_announced",
            ResistanceLevel.STRONG: "5s_penalty",
            ResistanceLevel.VIOLATION: "drive_through",
        }

        return penalties.get(resistance_level, "warning_logged")

    def _create_compliance_narrative(
        self, leader_name: str, lapped_name: str, track_section: str, compliance_score: float
    ) -> str:
        """Create narrative for compliance scenario"""
        if compliance_score >= 0.9:
            return f"{lapped_name} moves aside immediately on the {track_section}, allowing {leader_name} through cleanly"
        elif compliance_score >= 0.7:
            return f"{lapped_name} gives way to {leader_name} on the {track_section}"
        else:
            return f"{lapped_name} eventually lets {leader_name} through after brief hesitation"

    def _create_resistance_narrative(
        self,
        leader_name: str,
        lapped_name: str,
        track_section: str,
        resistance_level,
        success: bool,
        violation: bool,
    ) -> str:
        """Create narrative for resistance scenario"""
        from incidents.blue_flag import ResistanceLevel

        narratives = {
            ResistanceLevel.MINOR: f"{lapped_name} hesitates briefly before letting {leader_name} through",
            ResistanceLevel.MODERATE: f"{lapped_name} holds up {leader_name} for a couple of corners before giving way",
            ResistanceLevel.STRONG: f"{lapped_name} defends strongly against {leader_name}, forcing the leader to work hard",
            ResistanceLevel.VIOLATION: f"{lapped_name} completely ignores blue flags, blocking {leader_name}",
        }

        base_narrative = narratives.get(
            resistance_level, f"{lapped_name} resists letting {leader_name} through"
        )

        if violation:
            base_narrative += " - blue flag violation noted by Race Control"

        if success and resistance_level in [ResistanceLevel.STRONG, ResistanceLevel.VIOLATION]:
            base_narrative += f", but {leader_name} eventually forces the pass"
        elif not success:
            base_narrative += f", {leader_name} unable to complete the lap immediately"

        return base_narrative

    def get_blue_flag_modifier(
        self, blue_flag_complied: bool, blue_flag_state
    ) -> float:
        """
        Get modifier for overtake confrontation based on blue flag status.

        This can be used by parent classes to adjust confrontation modifiers.

        Args:
            blue_flag_complied: Whether lapped car complied with blue flags
            blue_flag_state: Current blue flag state

        Returns:
            Modifier value (+3 to +5 for leader if complied, 0 otherwise)
        """
        from incidents.blue_flag import BlueFlagState

        if not blue_flag_complied:
            return 0.0

        # Leader gets bonus based on compliance timing
        if blue_flag_state == BlueFlagState.WARNING:
            return 5.0  # Maximum bonus for early compliance
        elif blue_flag_state == BlueFlagState.FINAL:
            return 4.0  # Good bonus for final warning compliance
        elif blue_flag_state == BlueFlagState.COMPLIED:
            return 3.0  # Standard bonus

        return 0.0
