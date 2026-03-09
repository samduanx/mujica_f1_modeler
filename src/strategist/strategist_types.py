"""
Strategist Types Module

Defines all core data structures for the Strategist System including:
- StrategistProfile: Stats and attributes for a race strategist
- StrategyDecision: Container for strategy decision outcomes
- RaceContext: Current race state for decision-making
- DecisionType: Enum for different strategy decision types
- DriverComplianceLevel: Enum for driver compliance levels
- PaceMode: Enum for racing pace modes
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict


class DecisionType(Enum):
    """Types of strategy decisions a strategist can make."""

    PIT_TIMING = "pit_timing"
    TYRE_COMPOUND = "tyre_compound"
    RACING_PACE = "racing_pace"
    WEATHER_RESPONSE = "weather_response"
    SAFETY_CAR_RESPONSE = "safety_car_response"
    UNDERCUT_ATTEMPT = "undercut_attempt"
    TEAM_ORDER = "team_order"


class DriverComplianceLevel(Enum):
    """Levels of driver compliance with strategist instructions."""

    PERFECT = "perfect"  # Executes flawlessly with enthusiasm
    FULL = "full"  # Follows instructions exactly
    PARTIAL = "partial"  # Follows with minor adaptation
    SUGGESTION = "suggestion"  # Takes as advice, may modify
    RESISTANCE = "resistance"  # Reluctant compliance
    OVERRIDE = "override"  # Completely disregards advice


class PaceMode(Enum):
    """Racing pace modes available to strategists."""

    PUSH = "push"  # 100% speed, 150% tire wear, 120% fuel
    RACE = "race"  # 95% speed, 100% tire wear, 100% fuel
    MANAGE = "manage"  # 90% speed, 70% tire wear, 85% fuel
    SAVE = "save"  # 85% speed, 50% tire wear, 70% fuel
    LIFT_AND_COAST = "lift_and_coast"  # 80% speed, 40% tire wear, 50% fuel


class OutcomeLevel(Enum):
    """Outcome levels for dice roll results."""

    CRITICAL_FAILURE = "critical_failure"  # Natural 1
    FAILURE = "failure"  # 2-5
    PARTIAL_SUCCESS = "partial_success"  # 6-10
    SUCCESS = "success"  # 11-15
    GREAT_SUCCESS = "great_success"  # 16-19
    CRITICAL_SUCCESS = "critical_success"  # Natural 20


@dataclass
class StrategistProfile:
    """
    Profile for a race strategist with all their attributes and stats.

    Attributes:
        name: Strategist's name
        team: F1 team the strategist works for
        experience: Years of experience (affects modifier)
        aggression: 0.0-1.0, affects risk-taking decisions
        conservatism: 0.0-1.0, affects defensive strategy
        intuition: 0.0-1.0, affects gut-feeling calls
        adaptability: 0.0-1.0, affects response to changing conditions
        analytical: 0.0-1.0, affects data-driven decisions
        communication: 0.0-1.0, affects driver/team relations
        wet_weather_skill: 0.0-1.0, affects wet weather decisions
        tire_management: 0.0-1.0, affects tyre strategy
        undercut_skill: 0.0-1.0, affects undercut attempts
        pit_timing: 0.0-1.0, affects pit stop timing
        track_familiarity: Dict mapping track names to familiarity level (races)
    """

    name: str
    team: str
    experience: int = 0  # Years of experience

    # Core attributes (0.0-1.0)
    aggression: float = 0.5
    conservatism: float = 0.5
    intuition: float = 0.5
    adaptability: float = 0.5
    analytical: float = 0.5
    communication: float = 0.5

    # Specialized skills (0.0-1.0)
    wet_weather_skill: float = 0.5
    tire_management: float = 0.5
    undercut_skill: float = 0.5
    pit_timing: float = 0.5

    # Track familiarity: track_name -> number of races
    track_familiarity: Dict[str, int] = field(default_factory=dict)

    # Runtime state
    successful_decisions: int = 0
    failed_decisions: int = 0

    def get_experience_modifier(self) -> int:
        """Calculate experience modifier based on years of experience."""
        if self.experience <= 2:
            return 0  # Rookie
        elif self.experience <= 5:
            return 1  # Junior
        elif self.experience <= 9:
            return 2  # Experienced
        elif self.experience <= 14:
            return 3  # Senior
        else:
            return 4  # Veteran

    def get_attribute_modifier(self, attribute_value: float) -> int:
        """
        Convert attribute value (0.0-1.0) to modifier.

        | Attribute Value | Modifier |
        | 0.0-0.25       | -2       |
        | 0.26-0.40      | -1       |
        | 0.41-0.60      | 0        |
        | 0.61-0.75      | +1       |
        | 0.76-0.90      | +2       |
        | 0.91-1.00      | +3       |
        """
        if attribute_value <= 0.25:
            return -2
        elif attribute_value <= 0.40:
            return -1
        elif attribute_value <= 0.60:
            return 0
        elif attribute_value <= 0.75:
            return 1
        elif attribute_value <= 0.90:
            return 2
        else:
            return 3

    def get_track_familiarity_bonus(self, track_name: str) -> int:
        """Calculate track familiarity bonus."""
        races = self.track_familiarity.get(track_name, 0)
        if races == 0:
            return 0
        elif races <= 2:
            return 1
        elif races <= 5:
            return 2
        else:
            return 3

    def get_aggression_modifier(self) -> int:
        """Get modifier from aggression attribute."""
        return self.get_attribute_modifier(self.aggression)

    def get_conservatism_modifier(self) -> int:
        """Get modifier from conservatism attribute."""
        return self.get_attribute_modifier(self.conservatism)

    def get_intuition_modifier(self) -> int:
        """Get modifier from intuition attribute."""
        return self.get_attribute_modifier(self.intuition)

    def get_adaptability_modifier(self) -> int:
        """Get modifier from adaptability attribute."""
        return self.get_attribute_modifier(self.adaptability)

    def get_analytical_modifier(self) -> int:
        """Get modifier from analytical attribute."""
        return self.get_attribute_modifier(self.analytical)

    def get_communication_modifier(self) -> int:
        """Get modifier from communication attribute."""
        return self.get_attribute_modifier(self.communication)

    def get_wet_weather_modifier(self) -> int:
        """Get modifier from wet weather skill (x1.5 multiplier for decisions)."""
        base_mod = self.get_attribute_modifier(self.wet_weather_skill)
        return int(base_mod * 1.5)

    def get_tire_management_modifier(self) -> int:
        """Get modifier from tire management skill."""
        return self.get_attribute_modifier(self.tire_management)

    def get_undercut_modifier(self) -> int:
        """Get modifier from undercut skill (x1.5 multiplier for decisions)."""
        base_mod = self.get_attribute_modifier(self.undercut_skill)
        return int(base_mod * 1.5)

    def get_pit_timing_modifier(self) -> int:
        """Get modifier from pit timing skill."""
        return self.get_attribute_modifier(self.pit_timing)


@dataclass
class StrategyDecision:
    """
    Container for a strategy decision made by a strategist.

    Attributes:
        decision_type: Type of decision made
        roll: The raw dice roll (1d20)
        modifier: Total modifier applied
        final_value: roll + modifier
        outcome: Outcome level (critical failure to critical success)
        description: Human-readable description of the decision
        time_impact: Time impact in seconds (positive = slower)
        position_impact: Position impact (positive = gained positions)
        special_effects: Any special effects from the decision
    """

    decision_type: DecisionType
    roll: int
    modifier: int
    final_value: int
    outcome: OutcomeLevel
    description: str
    time_impact: float = 0.0  # seconds
    position_impact: int = 0  # positions
    special_effects: Dict[str, any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """Check if the decision was successful (partial success or better)."""
        return self.outcome in (
            OutcomeLevel.PARTIAL_SUCCESS,
            OutcomeLevel.SUCCESS,
            OutcomeLevel.GREAT_SUCCESS,
            OutcomeLevel.CRITICAL_SUCCESS,
        )

    def is_failure(self) -> bool:
        """Check if the decision was a failure."""
        return self.outcome in (OutcomeLevel.FAILURE, OutcomeLevel.CRITICAL_FAILURE)


@dataclass
class RaceContext:
    """
    Current race state for making strategy decisions.

    Attributes:
        track_name: Current track
        current_lap: Current race lap
        total_laps: Total race laps
        is_wet: Whether track is wet
        rain_intensity: Rain intensity (0-100)
        rain_eta: Estimated laps until rain (None if no rain expected)
        is_sc_active: Whether Safety Car is active
        is_vsc_active: Whether Virtual Safety Car is active
        race_position: Current race position
        pit_stops_completed: Number of pit stops completed
        current_tyre: Current tyre compound
        tyre_life: Laps remaining on current tyre
        fuel_level: Fuel remaining (percentage)
        driver_trust: Driver's trust level (0.0-1.0)
        championship_leading: Whether in championship contention
        pressure_level: Current pressure level (0=none, 3=extreme)
    """

    track_name: str = "Unknown"
    current_lap: int = 1
    total_laps: int = 78

    # Weather conditions
    is_wet: bool = False
    rain_intensity: int = 0
    rain_eta: Optional[int] = None  # Laps until rain

    # Race control
    is_sc_active: bool = False
    is_vsc_active: bool = False

    # Car state
    race_position: int = 20
    pit_stops_completed: int = 0
    current_tyre: str = "SOFT"
    tyre_life: int = 20  # Laps remaining
    fuel_level: float = 100.0  # Percentage

    # Driver relationship
    driver_trust: float = 0.5  # 0.0-1.0

    # Championship context
    championship_leading: bool = False
    pressure_level: int = 0  # 0=none, 1=normal, 2=high, 3=extreme


@dataclass
class ComplianceCheck:
    """
    Result of a driver compliance check.

    Attributes:
        roll: The raw dice roll (1d20)
        modifier: Total modifier applied
        final_value: roll + modifier
        outcome: Compliance level achieved
        effectiveness: Strategy effectiveness multiplier
    """

    roll: int
    modifier: int
    final_value: int
    outcome: DriverComplianceLevel
    effectiveness: float = 1.0

    @staticmethod
    def get_effectiveness(level: DriverComplianceLevel) -> float:
        """Get effectiveness multiplier for compliance level."""
        effectiveness_map = {
            DriverComplianceLevel.PERFECT: 1.20,
            DriverComplianceLevel.FULL: 1.00,
            DriverComplianceLevel.PARTIAL: 0.85,
            DriverComplianceLevel.SUGGESTION: 0.70,
            DriverComplianceLevel.RESISTANCE: 0.50,
            DriverComplianceLevel.OVERRIDE: 0.00,
        }
        return effectiveness_map.get(level, 1.0)


# Helper functions for outcome determination


def determine_outcome(roll: int, final_value: int) -> OutcomeLevel:
    """
    Determine outcome level from roll and final value.

    Criticals are determined by raw roll (1 or 20),
    other outcomes by final value.
    """
    if roll == 1:
        return OutcomeLevel.CRITICAL_FAILURE
    elif roll == 20:
        return OutcomeLevel.CRITICAL_SUCCESS
    elif final_value <= 5:
        return OutcomeLevel.FAILURE
    elif final_value <= 10:
        return OutcomeLevel.PARTIAL_SUCCESS
    elif final_value <= 15:
        return OutcomeLevel.SUCCESS
    elif final_value <= 19:
        return OutcomeLevel.GREAT_SUCCESS
    else:
        return OutcomeLevel.CRITICAL_SUCCESS


def determine_compliance_outcome(roll: int, final_value: int) -> DriverComplianceLevel:
    """
    Determine compliance level from roll and final value.
    """
    if roll == 1:
        return DriverComplianceLevel.OVERRIDE
    elif roll == 20:
        return DriverComplianceLevel.PERFECT
    elif final_value <= 5:
        return DriverComplianceLevel.RESISTANCE
    elif final_value <= 10:
        return DriverComplianceLevel.SUGGESTION
    elif final_value <= 15:
        return DriverComplianceLevel.PARTIAL
    elif final_value <= 19:
        return DriverComplianceLevel.FULL
    else:
        return DriverComplianceLevel.PERFECT


# F1 Track data for realistic strategy decisions

TRACK_PIT_LOSS = {
    "Bahrain": 22.5,
    "Jeddah": 23.0,
    "Australia": 21.5,
    "China": 21.0,
    "Miami": 22.0,
    "Monaco": 25.0,  # Very slow pit lane
    "Canada": 20.5,
    "Spain": 21.0,
    "Austria": 21.0,
    "Great Britain": 21.5,
    "Hungary": 22.0,
    "Belgium": 21.0,
    "Netherlands": 21.5,
    "Italy": 22.5,  # Very fast pit lane at Monza
    "Singapore": 25.0,  # Slow pit lane
    "Japan": 21.0,
    "Qatar": 22.0,
    "United States": 22.0,
    "Mexico": 22.5,
    "Brazil": 22.0,
    "Las Vegas": 23.0,
    "Abu Dhabi": 22.0,
}

TRACK_OVERTAKING_DIFFICULTY = {
    "Bahrain": "medium",
    "Jeddah": "high",
    "Australia": "medium",
    "China": "high",
    "Miami": "high",
    "Monaco": "very_low",  # Almost impossible to overtake
    "Canada": "high",
    "Spain": "medium",
    "Austria": "high",
    "Great Britain": "high",
    "Hungary": "low",
    "Belgium": "high",  # Eau Rouge
    "Netherlands": "medium",
    "Italy": "very_high",  # Monza - easiest to overtake
    "Singapore": "very_low",  # Street circuit
    "Japan": "medium",
    "Qatar": "high",
    "United States": "high",
    "Mexico": "high",
    "Brazil": "high",
    "Las Vegas": "high",
    "Abu Dhabi": "medium",
}

TRACK_UNDERCUT_DIFFICULTY = {
    "Bahrain": 0,
    "Jeddah": 0,
    "Australia": -1,
    "China": 0,
    "Miami": 0,
    "Monaco": -2,  # Very hard to undercut
    "Canada": 0,
    "Spain": -1,
    "Austria": 0,
    "Great Britain": 0,
    "Hungary": -1,
    "Belgium": 0,
    "Netherlands": -1,
    "Italy": 0,  # Easy to undercut at Monza
    "Singapore": -3,  # Very hard to undercut
    "Japan": -1,
    "Qatar": 0,
    "United States": 0,
    "Mexico": 0,
    "Brazil": 0,
    "Las Vegas": 0,
    "Abu Dhabi": -1,
}


# ============== Team Order System Types ==============


class TeamOrderType(Enum):
    """Types of team orders that can be issued."""

    SWAP_POSITIONS = "swap_positions"  # 交换位置 - 让快车通过
    HOLD_POSITION = "hold_position"  # 保持位置 - 防守指令
    YIELD_TO_TEAMMATE = "yield_to_teammate"  # 让车给队友 - 拉塞尔的技能相关
    LET_FASTER_CAR_THROUGH = "let_faster_car_through"  # 让更快的车通过


class TeamOrderStatus(Enum):
    """Status of a team order."""

    PENDING = "pending"  # 等待执行
    EXECUTED = "executed"  # 已成功执行
    DISOBEYED = "disobeyed"  # 车手拒绝执行
    EXPIRED = "expired"  # 指令过期
    CANCELLED = "cancelled"  # 被取消


class TeamOrderCompliance(Enum):
    """Compliance levels for team orders based on driver traits."""

    AUTO_COMPLY = "auto_comply"  # 自动执行（如博塔斯帮助周冠宇）
    HIGH = "high"  # 高概率执行（如拉塞尔的团队精神：1-2拒绝）
    NORMAL = "normal"  # 正常概率（3-10执行，1-2拒绝）
    LOW = "low"  # 低概率（顽固车手）
    NEVER = "never"  # 从不执行（如奥康的狮子）


@dataclass
class TeamOrder:
    """
    Represents a team order issued during a race.

    Attributes:
        order_type: Type of team order
        target_driver: Driver who needs to comply (让车的车手)
        beneficiary_driver: Driver who benefits (获得位置的车手)
        team: Team name
        lap_issued: Lap when order was issued
        reason: Reason for issuing the order
        gap_threshold: Gap threshold that triggered the order (seconds)
        status: Current status of the order
        drs_zone: Whether issued in DRS zone (more effective)
    """

    order_type: TeamOrderType
    target_driver: str
    beneficiary_driver: str
    team: str
    lap_issued: int
    reason: str
    gap_threshold: float = 0.0
    status: TeamOrderStatus = TeamOrderStatus.PENDING
    drs_zone: bool = False

    def is_active(self) -> bool:
        """Check if the order is still active (pending)."""
        return self.status == TeamOrderStatus.PENDING


@dataclass
class TeamOrderResult:
    """
    Result of a team order execution attempt.

    Attributes:
        success: Whether the order was successfully executed
        roll: The dice roll (1d10)
        threshold: Threshold for compliance
        compliance_level: Driver's compliance level
        message: Human-readable description of the result
        position_swap: Whether positions were actually swapped
        disobey_penalty: Whether there should be a penalty for disobeying
    """

    success: bool
    roll: int
    threshold: int
    compliance_level: TeamOrderCompliance
    message: str
    position_swap: bool = False
    disobey_penalty: bool = False


@dataclass
class DriverTeamOrderTraits:
    """
    Driver characteristics related to team order compliance.

    These traits affect how likely a driver is to follow team orders.

    Attributes:
        driver_name: Driver name
        team_spirit: 团队精神 (like Russell - high compliance)
        lion_trait: 狮子 (like Ocon - ignores team orders)
        big_brother: 好大哥 (like Bottas - helps teammate)
        base_compliance: Base compliance level (0.0-1.0)
        stubbornness: How stubborn the driver is (0.0-1.0)
    """

    driver_name: str
    team_spirit: bool = False  # 拉塞尔的团队精神
    lion_trait: bool = False  # 奥康的狮子
    big_brother: bool = False  # 博塔斯的好大哥
    base_compliance: float = 0.5
    stubbornness: float = 0.5

    def get_compliance_threshold(self) -> tuple[int, TeamOrderCompliance]:
        """
        Get the compliance threshold and level for this driver.

        Returns:
            Tuple of (threshold, compliance_level)
            threshold: Roll >= this value to comply (1d10)
        """
        if self.lion_trait:
            return 11, TeamOrderCompliance.NEVER  # Never complies
        elif self.team_spirit:
            return 3, TeamOrderCompliance.HIGH  # Only 1-2 fails (80% success)
        elif self.big_brother:
            return 1, TeamOrderCompliance.AUTO_COMPLY  # Always helps teammate
        elif self.stubbornness >= 0.8:
            return 8, TeamOrderCompliance.LOW  # 80% success rate
        elif self.base_compliance >= 0.7:
            return 3, TeamOrderCompliance.HIGH  # 80% success
        else:
            return 3, TeamOrderCompliance.NORMAL  # Standard 80% success


@dataclass
class TeamOrderContext:
    """
    Context for team order decisions.

    Contains all relevant race state for determining if/when to issue
    team orders and whether they will be followed.
    """

    # Race state
    current_lap: int
    total_laps: int
    is_drs_active: bool = False

    # Car positions (relative)
    target_position: int = 0
    beneficiary_position: int = 0

    # Performance data
    target_pace: float = 0.0  # Seconds per lap
    beneficiary_pace: float = 0.0
    pace_delta: float = 0.0  # Positive = beneficiary faster

    # Gap data
    gap_between: float = 0.0  # Seconds between cars
    gap_to_leader: float = 0.0

    # Championship context
    beneficiary_in_championship_fight: bool = False
    target_in_championship_fight: bool = False

    # Previous orders history
    recent_disobey_count: int = 0
    total_orders_issued: int = 0

    def should_issue_swap_order(self, min_pace_delta: float = 0.3) -> bool:
        """
        Determine if a swap order should be issued.

        Args:
            min_pace_delta: Minimum pace advantage to trigger (seconds/lap)

        Returns:
            True if swap order should be issued
        """
        # Check if cars are adjacent
        if abs(self.target_position - self.beneficiary_position) != 1:
            return False

        # Check if beneficiary is behind
        if self.beneficiary_position >= self.target_position:
            return False

        # Check pace delta
        if self.pace_delta < min_pace_delta:
            return False

        # Check if gap is reasonable (not too far)
        if self.gap_between > 2.0:
            return False

        return True

    def get_pace_delta(self) -> float:
        """Calculate pace delta (beneficiary - target, negative = faster)."""
        return self.beneficiary_pace - self.target_pace
