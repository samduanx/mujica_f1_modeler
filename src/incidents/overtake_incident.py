"""
Overtake Incident System.

Handles collision probability during overtake attempts.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

from incidents.incident_types import TrackDifficulty, IncidentSeverity
from incidents.driver_error import DriverErrorType


class OvertakeSituation(Enum):
    """Classification of overtake situations"""

    IN_DRS_ZONE = "in_drs_zone"
    END_OF_DRS_ZONE = "end_of_drs_zone"
    ELSEWHERE = "elsewhere"


@dataclass
class OvertakeCollision:
    """Represents a collision during overtake"""

    attacker: str
    defender: str
    situation: OvertakeSituation
    severity: IncidentSeverity
    time_penalty: float
    narrative: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "attacker": self.attacker,
            "defender": self.defender,
            "situation": self.situation.value,
            "severity": self.severity.value,
            "time_penalty": self.time_penalty,
            "narrative": self.narrative,
        }


class OvertakeIncidentProbability:
    """
    Calculate collision probability during overtake attempts.

    Based on factors including:
    - DR margin between drivers
    - Speed delta
    - Track difficulty
    - Overtake situation type
    """

    # Base collision probability per overtake attempt
    BASE_COLLISION_PROB = 0.05  # 5% base chance

    def __init__(self, track_difficulty: TrackDifficulty = TrackDifficulty.MEDIUM):
        """Initialize with track difficulty"""
        self.track_difficulty = track_difficulty

    def get_collision_probability(
        self,
        situation: OvertakeSituation,
        dr_margin: float,
        speed_delta: float,
        attacker_dr_value: float,
        defender_dr_value: float,
    ) -> float:
        """
        Calculate collision probability for current overtake attempt.

        Args:
            situation: DRS zone, end of DRS, or elsewhere
            dr_margin: DR difference (attacker - defender)
            speed_delta: Speed difference in km/h
            attacker_dr_value: Attacker's DR value
            defender_dr_value: Defender's DR value

        Returns:
            Probability of collision (0.0 to 1.0)
        """
        prob = self.BASE_COLLISION_PROB

        # DR margin impact
        # Positive = attacker better than defender (lower risk)
        # Negative = attacker worse than defender (higher risk)
        if dr_margin < -3:  # Attacker much worse than defender
            prob *= 1.5  # Increased risk
        elif dr_margin < -1:
            prob *= 1.2
        elif dr_margin > 3:  # Attacker much better than defender
            prob *= 0.7  # Reduced risk
        elif dr_margin > 1:
            prob *= 0.85

        # Speed delta impact
        if speed_delta > 30:
            prob *= 1.3
        elif speed_delta > 20:
            prob *= 1.15
        elif speed_delta < 10:
            prob *= 0.8
        elif speed_delta < 5:
            prob *= 0.6

        # Track difficulty modifier
        prob *= self.track_difficulty.collision_risk_factor

        # Situation modifier
        if situation == OvertakeSituation.ELSEWHERE:
            prob *= 1.2  # Higher risk outside DRS zones
        elif situation == OvertakeSituation.END_OF_DRS_ZONE:
            prob *= 1.1  # Slightly higher risk at DRS exit

        return min(1.0, max(0.0, prob))

    def check_collision(
        self,
        situation: OvertakeSituation,
        dr_margin: float,
        speed_delta: float,
        attacker_name: str,
        attacker_dr: float,
        defender_name: str,
        defender_dr: float,
    ) -> Optional[OvertakeCollision]:
        """
        Check if collision occurs during overtake.

        Args:
            situation: Overtake situation type
            dr_margin: DR difference
            speed_delta: Speed difference
            attacker_name: Name of attacking driver
            attacker_dr: Attacker's DR value
            defender_name: Name of defending driver
            defender_dr: Defender's DR value

        Returns:
            OvertakeCollision if collision occurs, None otherwise
        """
        prob = self.get_collision_probability(
            situation=situation,
            dr_margin=dr_margin,
            speed_delta=speed_delta,
            attacker_dr_value=attacker_dr,
            defender_dr_value=defender_dr,
        )

        if random.random() < prob:
            return self._create_collision(
                attacker=attacker_name,
                defender=defender_name,
                situation=situation,
                dr_margin=dr_margin,
                speed_delta=speed_delta,
            )

        return None

    def _create_collision(
        self,
        attacker: str,
        defender: str,
        situation: OvertakeSituation,
        dr_margin: float,
        speed_delta: float,
    ) -> OvertakeCollision:
        """Create a collision incident"""
        # Determine severity based on DR margin
        if abs(dr_margin) > 5:
            severity = IncidentSeverity.MINOR
            time_penalty = 2.0
        elif abs(dr_margin) > 2:
            severity = IncidentSeverity.MODERATE
            time_penalty = 5.0
        else:
            severity = IncidentSeverity.MAJOR
            time_penalty = 10.0

        # Adjust for situation
        if situation == OvertakeSituation.END_OF_DRS_ZONE:
            time_penalty *= 1.2

        # Generate narrative
        narratives = [
            f"{attacker} attempts to overtake {defender} in {situation.value}, "
            f"but they collide! Both drivers continue but lose time.",
            f"Racing incident between {attacker} and {defender} - "
            f"contact made during the overtake battle.",
            f"{defender} defends aggressively against {attacker}, "
            f"resulting in a collision. Both cars damaged.",
        ]

        narrative = random.choice(narratives)

        return OvertakeCollision(
            attacker=attacker,
            defender=defender,
            situation=situation,
            severity=severity,
            time_penalty=time_penalty,
            narrative=narrative,
        )


class OvertakeIncidentSimulator:
    """
    Simulate overtake incidents throughout a race.
    """

    def __init__(self, track_difficulty: TrackDifficulty = TrackDifficulty.MEDIUM):
        """Initialize simulator"""
        self.collision_calculator = OvertakeIncidentProbability(track_difficulty)
        self.collisions: List[OvertakeCollision] = []

    def check_overtake_incident(
        self,
        attacker_name: str,
        attacker_dr: float,
        defender_name: str,
        defender_dr: float,
        situation: OvertakeSituation,
        speed_delta: float,
        is_overtake_attempt: bool = True,
    ) -> Optional[OvertakeCollision]:
        """
        Check for incident during overtake attempt.

        Args:
            attacker_name: Name of attacking driver
            attacker_dr: Attacker's DR value
            defender_name: Name of defending driver
            defender_dr: Defender's DR value
            situation: Overtake situation type
            speed_delta: Speed difference
            is_overtake_attempt: Whether this is an active attempt

        Returns:
            OvertakeCollision if collision occurs, None otherwise
        """
        if not is_overtake_attempt:
            return None

        dr_margin = attacker_dr - defender_dr

        collision = self.collision_calculator.check_collision(
            situation=situation,
            dr_margin=dr_margin,
            speed_delta=speed_delta,
            attacker_name=attacker_name,
            attacker_dr=attacker_dr,
            defender_name=defender_name,
            defender_dr=defender_dr,
        )

        if collision:
            self.collisions.append(collision)

        return collision

    def get_statistics(self) -> Dict:
        """Get collision statistics"""
        return {
            "total_collisions": len(self.collisions),
            "by_severity": self._count_by_severity(),
        }

    def _count_by_severity(self) -> Dict[str, int]:
        """Count collisions by severity"""
        counts = {}
        for collision in self.collisions:
            counts[collision.severity.value] = (
                counts.get(collision.severity.value, 0) + 1
            )
        return counts
