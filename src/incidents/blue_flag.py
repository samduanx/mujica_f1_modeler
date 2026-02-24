"""
Blue Flag System.

Manages blue flag situations during races, including:
- Lapping detection
- Driver compliance with dice-based mechanics
- Violation tracking and penalty escalation

Based on F1 Sporting Regulations Article 55.14-55.15.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
import random


class BlueFlagState(Enum):
    """Blue flag states for lapped cars"""

    NONE = "none"  # No blue flag
    WARNING = "warning"  # First warning (shown 2-3 corners before)
    FINAL = "final"  # Final warning (last chance to give way)
    COMPLIED = "complied"  # Driver complied
    VIOLATION = "violation"  # Driver ignored blue flags


class ResistanceLevel(Enum):
    """Levels of resistance to blue flags"""

    NONE = "none"  # No resistance, immediate compliance
    MINOR = "minor"  # Brief hesitation, then complies
    MODERATE = "moderate"  # Defends for 2-3 corners
    STRONG = "strong"  # Extended defense, likely penalty
    VIOLATION = "violation"  # Complete refusal, certain penalty


@dataclass
class LappingDetectionConfig:
    """Configuration for lapping detection"""

    warning_gap: float = 3.0  # Show warning when gap < 3s
    final_gap: float = 1.5  # Final warning at 1.5s
    min_sections_apart: int = 0  # Min sectors apart to trigger
    max_sections_apart: int = 1  # Max sectors apart to trigger


@dataclass
class DriverPersonality:
    """
    Personality traits affecting blue flag compliance.
    These would be defined per driver in configuration.
    """

    professionalism: float = 0.5  # 0.0-1.0, affects base compliance
    aggression: float = 0.5  # 0.0-1.0, higher = more resistance
    team_loyalty: float = 0.5  # 0.0-1.0, affects teammate cooperation
    stubbornness: float = 0.5  # 0.0-1.0, affects frustration buildup
    sportsmanship: float = 0.5  # 0.0-1.0, affects willingness to help rivals

    def get_compliance_modifier(self) -> int:
        """Convert personality to compliance modifier"""
        modifier = 0

        # Professional drivers comply more readily
        modifier += int((self.professionalism - 0.5) * 4)

        # Aggressive drivers resist more
        modifier -= int((self.aggression - 0.5) * 3)

        # Sportsmanlike drivers help rivals too
        modifier += int((self.sportsmanship - 0.5) * 2)

        return modifier

    def get_frustration_rate(self) -> float:
        """How quickly frustration builds with repeated blue flags"""
        # Stubborn drivers get frustrated faster
        return 0.5 + (self.stubbornness * 0.5)


@dataclass
class LappingPair:
    """Represents a leader-lapped car pair in a blue flag situation"""

    leader: str  # Name of the leading driver
    lapped_car: str  # Name of the lapped driver
    gap: float  # Time gap between them (seconds)
    lap_difference: int  # How many laps the leader is ahead
    track_section: str  # Current track section
    blue_flag_state: BlueFlagState = BlueFlagState.NONE
    blue_flag_count: int = 0  # Number of times blue flag shown
    resistance_level: ResistanceLevel = ResistanceLevel.NONE


@dataclass
class BlueFlagViolation:
    """Record of a blue flag violation"""

    driver: str
    lap: int
    resistance_level: ResistanceLevel
    offense_count: int
    penalty: str
    track_section: str
    narrative: str = ""


class BlueFlagComplianceRoller:
    """
    Dice-based compliance system for blue flags.
    Roll 1d20 against a target number to determine compliance.
    """

    def __init__(self):
        self.base_target = 15  # Roll 15+ to comply (75% base compliance)

    def get_compliance_target(
        self,
        driver,
        leader,
        blue_flag_count: int,
        track_section: str,
        race_progress: float,
        personality: Optional[DriverPersonality] = None,
    ) -> int:
        """
        Calculate target number for compliance roll (1d20).
        Higher target = easier to comply.

        Returns: Target number (roll >= this to comply)
        """
        target = self.base_target  # Start at 15

        # DR Modifier: Professional drivers comply more readily
        # DR 85: +1, DR 90: +2, DR 95: +3
        dr_bonus = max(0, (driver.dr_value - 80) // 5)
        target += dr_bonus

        # Team Status Modifier (use driver attributes if available)
        team_status = getattr(driver, "team_status", None)
        if team_status == "backmarker":
            target += 2  # Backmarkers used to giving way
        elif team_status == "championship_contender":
            target -= 1  # Less willing to yield

        # Blue Flag Repetition Modifier (frustration)
        # Each additional blue flag shown reduces willingness
        if blue_flag_count == 1:
            target += 1  # First time - very willing
        elif blue_flag_count == 2:
            target += 0  # Second time - neutral
        elif blue_flag_count >= 3:
            target -= blue_flag_count - 2  # Increasing frustration

        # Track Section Safety Modifier
        # Drivers won't risk moving over in unsafe sections
        section_modifiers = {
            "straight": 2,  # Easy to give way
            "drs_zone": 2,  # Easy to give way
            "corner_exit": 1,  # Generally safe
            "corner_entry": -2,  # Unsafe - justified hold-up
            "corner_apex": -5,  # Never move over at apex
            "braking_zone": -3,  # Never move over under braking
            "narrow_section": -2,  # Tight sections are risky
        }
        target += section_modifiers.get(track_section, 0)

        # Race Progress Modifier
        if race_progress >= 0.9:  # Final 10% of race
            target -= 2  # More desperate
        elif race_progress >= 0.75:
            target -= 1

        # Personality Modifier
        if personality:
            target += personality.get_compliance_modifier()

        # Leader Identity Modifier (relationship/history)
        target += self._get_driver_relationship_modifier(driver, leader)

        # Clamp between 3-19 (allows both auto-fail and auto-success edge cases)
        return max(3, min(19, target))

    def _get_driver_relationship_modifier(self, lapped_driver, leader) -> int:
        """
        Modifiers based on driver relationships.
        Can be positive (willing to help) or negative (rivalry).
        """
        modifier = 0

        # Team relationship
        lapped_team = getattr(lapped_driver, "team", None)
        leader_team = getattr(leader, "team", None)
        if lapped_team and leader_team:
            if lapped_team == leader_team:
                modifier += 3  # Teammates always give way quickly
            else:
                # Check for team alliances
                lapped_alliance = getattr(lapped_driver, "team_alliance", None)
                leader_alliance = getattr(leader, "team_alliance", None)
                if lapped_alliance and lapped_alliance == leader_alliance:
                    modifier += 1  # Allied teams more cooperative

        # Championship consideration
        leader_champ_pos = getattr(leader, "championship_position", 99)
        try:
            if leader_champ_pos <= 3:
                modifier += 1  # More willing to let championship contender through
        except TypeError:
            # Handle case where championship_position is not comparable
            pass

        return modifier

    def determine_resistance_level(
        self, roll: int, target: int, driver_aggression: float = 0.5
    ) -> ResistanceLevel:
        """
        Determine resistance level based on roll result.

        Args:
            roll: The dice roll (1-20)
            target: The compliance target number
            driver_aggression: Driver's aggression level (0.0-1.0)

        Returns:
            ResistanceLevel indicating how much the driver resisted
        """
        difference = roll - target

        # Aggressive drivers may escalate resistance
        try:
            aggression_mod = int((driver_aggression - 0.5) * 2)
        except TypeError:
            aggression_mod = 0
        adjusted_diff = difference - aggression_mod

        if adjusted_diff >= 0:
            return ResistanceLevel.NONE
        elif adjusted_diff >= -2:
            return ResistanceLevel.MINOR
        elif adjusted_diff >= -4:
            return ResistanceLevel.MODERATE
        elif adjusted_diff >= -6:
            return ResistanceLevel.STRONG
        else:
            return ResistanceLevel.VIOLATION

    def roll_compliance(self, target: int) -> Tuple[int, bool]:
        """
        Roll for compliance.

        Args:
            target: The target number to meet or exceed

        Returns:
            Tuple of (roll_result, is_compliant)
        """
        roll = random.randint(1, 20)
        return roll, roll >= target


class BlueFlagManager:
    """Manages blue flag situations during race"""

    def __init__(self, config: Optional[LappingDetectionConfig] = None):
        self.config = config or LappingDetectionConfig()
        self.compliance_roller = BlueFlagComplianceRoller()

        # State tracking
        self.active_blue_flags: Dict[str, BlueFlagState] = {}
        self.lapping_pairs: List[LappingPair] = []
        self.violations: List[BlueFlagViolation] = []

        # Per-driver tracking
        self.blue_flag_counts: Dict[
            str, int
        ] = {}  # How many times shown to each driver
        self.offense_counts: Dict[str, int] = {}  # Violation count per driver
        self.driver_personalities: Dict[str, DriverPersonality] = {}

        # History
        self.event_history: List[Dict] = []

    def register_driver_personality(
        self, driver_name: str, personality: DriverPersonality
    ):
        """Register a driver's personality for compliance calculations"""
        self.driver_personalities[driver_name] = personality

    def detect_lapping_situation(
        self,
        leader,
        lapped_car,
        track_section: str,
        race_progress: float,
    ) -> Optional[LappingPair]:
        """
        Detect if a blue flag situation exists between leader and lapped car.

        Uses cross-lap gap calculation based on DriverRaceState data:
        - current_sector
        - current_distance
        - get_current_lap()

        Args:
            leader: The leading driver's state (DriverRaceState)
            lapped_car: The potentially lapped driver's state (DriverRaceState)
            track_section: Current track section type
            race_progress: Race progress as fraction (0.0-1.0)

        Returns:
            LappingPair if a lapping situation exists, None otherwise
        """
        leader_name = getattr(leader, "name", "Unknown")
        lapped_name = getattr(lapped_car, "name", "Unknown")

        # Get lap numbers
        leader_lap = (
            leader.get_current_lap() if hasattr(leader, "get_current_lap") else 1
        )
        lapped_lap = (
            lapped_car.get_current_lap()
            if hasattr(lapped_car, "get_current_lap")
            else 1
        )

        # Calculate lap difference
        lap_difference = leader_lap - lapped_lap

        # Must be at least 1 lap ahead
        if lap_difference < 1:
            return None

        # Calculate cross-lap gap using cumulative time
        leader_time = getattr(leader, "cumulative_time", 0.0)
        lapped_time = getattr(lapped_car, "cumulative_time", 0.0)

        # Gap is leader_time - lapped_time (leader is ahead in time)
        gap = leader_time - lapped_time

        # Check sector proximity (must be in same or adjacent sectors)
        leader_sector = getattr(leader, "current_sector", 1)
        lapped_sector = getattr(lapped_car, "current_sector", 1)
        sector_diff = abs(leader_sector - lapped_sector)

        # Wrap around for sectors 1 and 3 being adjacent
        if sector_diff == 2:
            sector_diff = 1  # Sector 1 and 3 are considered adjacent

        if sector_diff > self.config.max_sections_apart:
            return None

        # Determine blue flag state based on gap
        if gap < self.config.final_gap:
            blue_state = BlueFlagState.FINAL
        elif gap < self.config.warning_gap:
            blue_state = BlueFlagState.WARNING
        else:
            blue_state = BlueFlagState.NONE

        if blue_state == BlueFlagState.NONE:
            return None

        # Get or initialize blue flag count for this driver
        blue_count = self.blue_flag_counts.get(lapped_name, 0)

        return LappingPair(
            leader=leader_name,
            lapped_car=lapped_name,
            gap=gap,
            lap_difference=lap_difference,
            track_section=track_section,
            blue_flag_state=blue_state,
            blue_flag_count=blue_count,
        )

    def evaluate_compliance(
        self,
        lapping_pair: LappingPair,
        leader,
        lapped_car,
        race_progress: float,
    ) -> Tuple[bool, ResistanceLevel, int]:
        """
        Evaluate if the lapped driver will comply with blue flags.

        Args:
            lapping_pair: The lapping pair situation
            leader: The leading driver's state
            lapped_car: The lapped driver's state
            race_progress: Race progress (0.0-1.0)

        Returns:
            Tuple of (will_comply, resistance_level, roll_result)
        """
        lapped_name = lapping_pair.lapped_car

        # Get driver personality
        personality = self.driver_personalities.get(lapped_name)

        # Get driver aggression for resistance calculation
        aggression = 0.5
        if personality:
            aggression = personality.aggression
        else:
            aggression = getattr(lapped_car, "aggression", 0.5)

        # Calculate compliance target
        target = self.compliance_roller.get_compliance_target(
            driver=lapped_car,
            leader=leader,
            blue_flag_count=lapping_pair.blue_flag_count,
            track_section=lapping_pair.track_section,
            race_progress=race_progress,
            personality=personality,
        )

        # Roll for compliance
        roll, is_compliant = self.compliance_roller.roll_compliance(target)

        # Determine resistance level
        resistance = self.compliance_roller.determine_resistance_level(
            roll, target, aggression
        )

        # Update blue flag count for this driver
        if lapped_name not in self.blue_flag_counts:
            self.blue_flag_counts[lapped_name] = 0
        self.blue_flag_counts[lapped_name] += 1
        lapping_pair.blue_flag_count = self.blue_flag_counts[lapped_name]

        # Update active blue flags
        if is_compliant:
            self.active_blue_flags[lapped_name] = BlueFlagState.COMPLIED
            lapping_pair.blue_flag_state = BlueFlagState.COMPLIED
            lapping_pair.resistance_level = ResistanceLevel.NONE
        else:
            self.active_blue_flags[lapped_name] = BlueFlagState.WARNING
            lapping_pair.resistance_level = resistance

        # Log the event
        self._log_event(
            "compliance_check",
            {
                "driver": lapped_name,
                "roll": roll,
                "target": target,
                "compliant": is_compliant,
                "resistance": resistance.value,
            },
        )

        return is_compliant, resistance, roll

    def record_violation(
        self,
        driver_name: str,
        lap: int,
        resistance_level: ResistanceLevel,
        track_section: str,
        narrative: str = "",
    ) -> BlueFlagViolation:
        """
        Record a blue flag violation and determine penalty.

        Args:
            driver_name: Name of the violating driver
            lap: Current lap number
            resistance_level: Level of resistance shown
            track_section: Where the violation occurred
            narrative: Narrative description

        Returns:
            BlueFlagViolation record
        """
        # Get offense count for this driver
        if driver_name not in self.offense_counts:
            self.offense_counts[driver_name] = 0
        self.offense_counts[driver_name] += 1
        offense_count = self.offense_counts[driver_name]

        # Determine penalty based on resistance level and offense count
        penalty = self._determine_penalty(resistance_level, offense_count)

        violation = BlueFlagViolation(
            driver=driver_name,
            lap=lap,
            resistance_level=resistance_level,
            offense_count=offense_count,
            penalty=penalty,
            track_section=track_section,
            narrative=narrative,
        )

        self.violations.append(violation)

        # Update active blue flags
        self.active_blue_flags[driver_name] = BlueFlagState.VIOLATION

        self._log_event(
            "violation",
            {
                "driver": driver_name,
                "resistance": resistance_level.value,
                "offense": offense_count,
                "penalty": penalty,
            },
        )

        return violation

    def _determine_penalty(
        self, resistance_level: ResistanceLevel, offense_count: int
    ) -> str:
        """
        Determine penalty based on resistance level and offense count.

        Penalty escalation:
        - First MINOR resistance: Warning (logged)
        - Second MINOR: Warning (announced)
        - MODERATE: Warning announced → 5s → Drive-through
        - STRONG: 5s → Drive-through → Stop-go
        - VIOLATION: Drive-through minimum
        """
        if resistance_level == ResistanceLevel.NONE:
            return "none"

        if resistance_level == ResistanceLevel.MINOR:
            if offense_count == 1:
                return "warning_logged"
            elif offense_count == 2:
                return "warning_announced"
            else:
                return "5s_penalty"

        if resistance_level == ResistanceLevel.MODERATE:
            if offense_count == 1:
                return "warning_announced"
            elif offense_count == 2:
                return "5s_penalty"
            else:
                return "drive_through"

        if resistance_level == ResistanceLevel.STRONG:
            if offense_count == 1:
                return "5s_penalty"
            elif offense_count == 2:
                return "drive_through"
            else:
                return "stop_go"

        if resistance_level == ResistanceLevel.VIOLATION:
            if offense_count == 1:
                return "drive_through"
            elif offense_count == 2:
                return "stop_go"
            else:
                return "black_flag"

        return "warning_logged"

    def is_lapping_situation(self, leader_name: str, lapped_name: str) -> bool:
        """Check if there's an active lapping situation between two drivers"""
        for pair in self.lapping_pairs:
            if pair.leader == leader_name and pair.lapped_car == lapped_name:
                return pair.blue_flag_state in [
                    BlueFlagState.WARNING,
                    BlueFlagState.FINAL,
                ]
        return False

    def get_active_lapping_pairs(self) -> List[LappingPair]:
        """Get all currently active lapping pairs"""
        return [
            pair
            for pair in self.lapping_pairs
            if pair.blue_flag_state in [BlueFlagState.WARNING, BlueFlagState.FINAL]
        ]

    def reset_driver_state(self, driver_name: str):
        """Reset blue flag state for a driver (e.g., after compliance or penalty)"""
        if driver_name in self.active_blue_flags:
            del self.active_blue_flags[driver_name]

        # Remove from lapping pairs
        self.lapping_pairs = [
            pair for pair in self.lapping_pairs if pair.lapped_car != driver_name
        ]

    def get_driver_violations(self, driver_name: str) -> List[BlueFlagViolation]:
        """Get all violations for a specific driver"""
        return [v for v in self.violations if v.driver == driver_name]

    def get_statistics(self) -> Dict:
        """Get blue flag statistics"""
        return {
            "total_violations": len(self.violations),
            "violations_by_driver": {
                driver: len(self.get_driver_violations(driver))
                for driver in set(v.driver for v in self.violations)
            },
            "violations_by_resistance": {
                level.value: len(
                    [v for v in self.violations if v.resistance_level == level]
                )
                for level in ResistanceLevel
            },
            "total_blue_flags_shown": sum(self.blue_flag_counts.values()),
            "drivers_with_violations": list(self.offense_counts.keys()),
        }

    def _log_event(self, event_type: str, data: Dict):
        """Log a blue flag event"""
        self.event_history.append({"type": event_type, "data": data})

    def clear_completed_situations(self):
        """Remove completed or violated situations from active list"""
        self.lapping_pairs = [
            pair
            for pair in self.lapping_pairs
            if pair.blue_flag_state
            not in [BlueFlagState.COMPLIED, BlueFlagState.VIOLATION]
        ]
