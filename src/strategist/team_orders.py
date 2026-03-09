"""
Team Order System Module

Implements the F1 team order mechanism including:
- Team order detection and issuance
- Driver compliance checks based on traits
- Position swap execution
- Integration with driver skills

Based on driver ratings from data/driver_ratings.csv:
- 拉塞尔 (Russell): 团队精神 - 1d10=1或2以外的所有值时让车 (80% compliance)
- 奥康 (Ocon): 狮子 - 无视车队指令 (0% compliance)
- 博塔斯 (Bottas): 好大哥 - 帮助周冠宇时自动触发
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from src.strategist.strategist_types import (
    TeamOrder,
    TeamOrderType,
    TeamOrderStatus,
    TeamOrderResult,
    TeamOrderCompliance,
    DriverTeamOrderTraits,
    TeamOrderContext,
)


# ============== Driver Trait Database ==============

# Driver traits based on data/driver_ratings.csv
DEFAULT_DRIVER_TEAM_ORDER_TRAITS: Dict[str, DriverTeamOrderTraits] = {
    # Russell - 团队精神: 1d10=1或2以外的所有值时让车 (80% compliance)
    "Russell": DriverTeamOrderTraits(
        driver_name="Russell",
        team_spirit=True,
        lion_trait=False,
        big_brother=False,
        base_compliance=0.8,
        stubbornness=0.2,
    ),
    # Ocon - 狮子: 无视车队指令
    "Ocon": DriverTeamOrderTraits(
        driver_name="Ocon",
        team_spirit=False,
        lion_trait=True,
        big_brother=False,
        base_compliance=0.0,
        stubbornness=0.9,
    ),
    # Bottas - 好大哥: 在车队指令或overtake模式下帮助周冠宇
    "Bottas": DriverTeamOrderTraits(
        driver_name="Bottas",
        team_spirit=False,
        lion_trait=False,
        big_brother=True,
        base_compliance=0.9,
        stubbornness=0.1,
    ),
    # Default traits for other drivers
    "Verstappen": DriverTeamOrderTraits(
        driver_name="Verstappen",
        base_compliance=0.7,
        stubbornness=0.6,
    ),
    "Hamilton": DriverTeamOrderTraits(
        driver_name="Hamilton",
        base_compliance=0.8,
        stubbornness=0.3,
    ),
    "Leclerc": DriverTeamOrderTraits(
        driver_name="Leclerc",
        base_compliance=0.75,
        stubbornness=0.4,
    ),
    "Sainz": DriverTeamOrderTraits(
        driver_name="Sainz",
        base_compliance=0.8,
        stubbornness=0.3,
    ),
    "Perez": DriverTeamOrderTraits(
        driver_name="Perez",
        base_compliance=0.85,
        stubbornness=0.2,
    ),
    "Norris": DriverTeamOrderTraits(
        driver_name="Norris",
        base_compliance=0.75,
        stubbornness=0.3,
    ),
    "Piastri": DriverTeamOrderTraits(
        driver_name="Piastri",
        base_compliance=0.8,
        stubbornness=0.2,
    ),
    "Alonso": DriverTeamOrderTraits(
        driver_name="Alonso",
        base_compliance=0.5,
        stubbornness=0.7,
    ),
    "Gasly": DriverTeamOrderTraits(
        driver_name="Gasly",
        base_compliance=0.75,
        stubbornness=0.3,
    ),
    "Stroll": DriverTeamOrderTraits(
        driver_name="Stroll",
        base_compliance=0.8,
        stubbornness=0.2,
    ),
    "Tsunoda": DriverTeamOrderTraits(
        driver_name="Tsunoda",
        base_compliance=0.6,
        stubbornness=0.5,
    ),
    "Zhou": DriverTeamOrderTraits(
        driver_name="Zhou",
        base_compliance=0.85,
        stubbornness=0.2,
    ),
    "Magnussen": DriverTeamOrderTraits(
        driver_name="Magnussen",
        base_compliance=0.5,
        stubbornness=0.7,
    ),
    "Hulkenberg": DriverTeamOrderTraits(
        driver_name="Hulkenberg",
        base_compliance=0.8,
        stubbornness=0.2,
    ),
    "Albon": DriverTeamOrderTraits(
        driver_name="Albon",
        base_compliance=0.85,
        stubbornness=0.15,
    ),
}


def get_driver_team_order_traits(driver_name: str) -> DriverTeamOrderTraits:
    """
    Get team order traits for a driver.

    Args:
        driver_name: Driver name

    Returns:
        DriverTeamOrderTraits for the driver
    """
    # Try exact match
    if driver_name in DEFAULT_DRIVER_TEAM_ORDER_TRAITS:
        return DEFAULT_DRIVER_TEAM_ORDER_TRAITS[driver_name]

    # Try case-insensitive match
    for name, traits in DEFAULT_DRIVER_TEAM_ORDER_TRAITS.items():
        if name.lower() == driver_name.lower():
            return traits

    # Return default traits
    return DriverTeamOrderTraits(
        driver_name=driver_name,
        base_compliance=0.7,
        stubbornness=0.3,
    )


# ============== Team Order Manager ==============


class TeamOrderManager:
    """
    Manages team orders during a race.

    Handles detection, issuance, and execution of team orders.
    """

    def __init__(self):
        self.active_orders: List[TeamOrder] = []
        self.order_history: List[TeamOrder] = []
        self.driver_disobey_count: Dict[str, int] = {}
        self.team_orders_issued: Dict[str, int] = {}  # team -> count

    def check_and_issue_swap_order(
        self,
        team: str,
        front_driver: str,
        rear_driver: str,
        front_position: int,
        rear_position: int,
        pace_delta: float,  # Positive = rear driver faster
        gap: float,
        current_lap: int,
        is_drs_zone: bool = False,
        min_pace_delta: float = 0.3,
    ) -> Optional[TeamOrder]:
        """
        Check if a swap order should be issued and create it.

        Args:
            team: Team name
            front_driver: Driver in front (needs to yield)
            rear_driver: Driver behind (beneficiary)
            front_position: Position of front driver
            rear_position: Position of rear driver
            pace_delta: Pace advantage of rear driver (seconds/lap)
            gap: Gap between cars (seconds)
            current_lap: Current lap number
            is_drs_zone: Whether in DRS zone
            min_pace_delta: Minimum pace delta to trigger

        Returns:
            TeamOrder if issued, None otherwise
        """
        # Validate positions
        if rear_position != front_position + 1:
            return None

        # Check pace delta
        if pace_delta < min_pace_delta:
            return None

        # Check gap (should be close but not too close)
        if gap > 2.0 or gap < 0.1:
            return None

        # Create order
        reason = f"{rear_driver} is {pace_delta:.2f}s/lap faster than {front_driver}"
        if is_drs_zone:
            reason += " (DRS zone active)"

        order = TeamOrder(
            order_type=TeamOrderType.SWAP_POSITIONS,
            target_driver=front_driver,
            beneficiary_driver=rear_driver,
            team=team,
            lap_issued=current_lap,
            reason=reason,
            gap_threshold=pace_delta,
            drs_zone=is_drs_zone,
        )

        self.active_orders.append(order)

        # Track orders issued by team
        self.team_orders_issued[team] = self.team_orders_issued.get(team, 0) + 1

        return order

    def execute_team_order(
        self,
        order: TeamOrder,
        driver_traits: Optional[DriverTeamOrderTraits] = None,
    ) -> TeamOrderResult:
        """
        Execute a team order and determine if driver complies.

        Args:
            order: The team order to execute
            driver_traits: Driver's team order traits (auto-loaded if None)

        Returns:
            TeamOrderResult with execution outcome
        """
        # Get driver traits
        if driver_traits is None:
            driver_traits = get_driver_team_order_traits(order.target_driver)

        # Get compliance threshold
        threshold, compliance_level = driver_traits.get_compliance_threshold()

        # Roll for compliance (1d10)
        roll = random.randint(1, 10)

        # Determine success
        success = roll >= threshold

        # Handle special cases
        if compliance_level == TeamOrderCompliance.NEVER:
            success = False
            message = f"{order.target_driver} (狮子) ignores team order completely!"
            disobey_penalty = False  # Expected behavior for lion trait
        elif compliance_level == TeamOrderCompliance.AUTO_COMPLY:
            success = True
            message = (
                f"{order.target_driver} (好大哥) automatically yields to help teammate"
            )
            disobey_penalty = False
        elif compliance_level == TeamOrderCompliance.HIGH:
            if success:
                message = f"{order.target_driver} (团队精神) complies with team order (rolled {roll})"
                disobey_penalty = False
            else:
                message = f"{order.target_driver} (团队精神) refuses team order! (rolled {roll}, needed 3+)"
                disobey_penalty = True
        else:
            if success:
                message = (
                    f"{order.target_driver} complies with team order (rolled {roll})"
                )
                disobey_penalty = False
            else:
                message = f"{order.target_driver} refuses team order! (rolled {roll}, needed {threshold}+)"
                disobey_penalty = True

        # Update order status
        if success:
            order.status = TeamOrderStatus.EXECUTED
        else:
            order.status = TeamOrderStatus.DISOBEYED
            # Track disobedience
            self.driver_disobey_count[order.target_driver] = (
                self.driver_disobey_count.get(order.target_driver, 0) + 1
            )

        # Move to history
        if order in self.active_orders:
            self.active_orders.remove(order)
        self.order_history.append(order)

        return TeamOrderResult(
            success=success,
            roll=roll,
            threshold=threshold,
            compliance_level=compliance_level,
            message=message,
            position_swap=success,
            disobey_penalty=disobey_penalty,
        )

    def execute_team_order_by_driver_name(
        self,
        order: TeamOrder,
    ) -> TeamOrderResult:
        """
        Convenience method to execute order using driver's name to lookup traits.

        Args:
            order: The team order to execute

        Returns:
            TeamOrderResult with execution outcome
        """
        traits = get_driver_team_order_traits(order.target_driver)
        return self.execute_team_order(order, traits)

    def get_active_orders_for_driver(self, driver_name: str) -> List[TeamOrder]:
        """Get all active orders targeting a specific driver."""
        return [
            o
            for o in self.active_orders
            if o.target_driver == driver_name and o.status == TeamOrderStatus.PENDING
        ]

    def get_orders_for_team(self, team: str) -> List[TeamOrder]:
        """Get all orders (active and history) for a team."""
        return [o for o in self.active_orders + self.order_history if o.team == team]

    def expire_old_orders(self, current_lap: int, max_age: int = 3) -> List[TeamOrder]:
        """
        Expire orders that are too old.

        Args:
            current_lap: Current lap number
            max_age: Maximum laps an order can be pending

        Returns:
            List of expired orders
        """
        expired = []
        for order in self.active_orders[:]:
            if current_lap - order.lap_issued > max_age:
                order.status = TeamOrderStatus.EXPIRED
                expired.append(order)
                self.active_orders.remove(order)
                self.order_history.append(order)
        return expired

    def get_driver_disobey_count(self, driver_name: str) -> int:
        """Get number of times a driver has disobeyed orders."""
        return self.driver_disobey_count.get(driver_name, 0)

    def reset(self):
        """Reset all state (for new race)."""
        self.active_orders.clear()
        self.order_history.clear()
        self.driver_disobey_count.clear()
        self.team_orders_issued.clear()


# ============== Utility Functions ==============


def should_issue_team_order(
    front_driver: str,
    rear_driver: str,
    front_pace: float,
    rear_pace: float,
    gap: float,
    is_same_team: bool,
    is_drs_zone: bool = False,
    min_pace_delta: float = 0.3,
) -> Tuple[bool, str]:
    """
    Determine if a team order should be issued.

    Args:
        front_driver: Driver in front
        rear_driver: Driver behind
        front_pace: Pace of front driver (s/lap)
        rear_pace: Pace of rear driver (s/lap)
        gap: Gap between cars (seconds)
        is_same_team: Whether drivers are teammates
        is_drs_zone: Whether in DRS zone
        min_pace_delta: Minimum pace advantage to trigger

    Returns:
        Tuple of (should_issue, reason)
    """
    if not is_same_team:
        return False, "Drivers are not teammates"

    pace_delta = rear_pace - front_pace  # Negative = rear faster

    if pace_delta >= 0:
        return False, "Rear driver is not faster"

    if abs(pace_delta) < min_pace_delta:
        return False, f"Pace delta ({abs(pace_delta):.2f}s) below threshold"

    if gap > 2.0:
        return False, "Gap too large"

    if gap < 0.1:
        return False, "Cars too close"

    reason = f"{rear_driver} is {abs(pace_delta):.2f}s/lap faster"
    if is_drs_zone:
        reason += " (DRS zone)"

    return True, reason


def execute_team_order(
    target_driver: str,
    beneficiary_driver: str,
    team: str,
    order_type: TeamOrderType = TeamOrderType.SWAP_POSITIONS,
) -> TeamOrderResult:
    """
    Execute a team order with compliance check.

    This is the main entry point for executing team orders.

    Args:
        target_driver: Driver who needs to yield
        beneficiary_driver: Driver who benefits
        team: Team name
        order_type: Type of team order

    Returns:
        TeamOrderResult with execution outcome
    """
    # Create temporary order
    order = TeamOrder(
        order_type=order_type,
        target_driver=target_driver,
        beneficiary_driver=beneficiary_driver,
        team=team,
        lap_issued=0,
        reason="Direct execution",
    )

    # Get driver traits
    traits = get_driver_team_order_traits(target_driver)

    # Execute
    manager = TeamOrderManager()
    return manager.execute_team_order(order, traits)


# ============== Periodic Detection ==============


def detect_team_order_opportunities(
    race_positions: List[Dict[str, Any]],
    team_assignments: Dict[str, str],
    current_lap: int,
    check_interval: int = 5,
) -> List[TeamOrderContext]:
    """
    Detect opportunities for team orders during race.

    Args:
        race_positions: List of position data [{driver, position, pace, gap_ahead}, ...]
        team_assignments: Dict mapping driver -> team
        current_lap: Current lap number
        check_interval: Only check every N laps

    Returns:
        List of TeamOrderContext for potential orders
    """
    # Only check every N laps
    if current_lap % check_interval != 0:
        return []

    opportunities = []

    # Sort by position
    sorted_positions = sorted(race_positions, key=lambda x: x.get("position", 999))

    for i in range(len(sorted_positions) - 1):
        front = sorted_positions[i]
        rear = sorted_positions[i + 1]

        front_driver = front.get("driver", "")
        rear_driver = rear.get("driver", "")

        if not front_driver or not rear_driver:
            continue

        # Check if same team
        if team_assignments.get(front_driver) != team_assignments.get(rear_driver):
            continue

        # Check gap
        gap = rear.get("gap_ahead", float("inf"))
        if gap > 2.0:
            continue

        # Calculate pace delta
        front_pace = front.get("pace", 0)
        rear_pace = rear.get("pace", 0)
        pace_delta = front_pace - rear_pace  # Positive = rear faster

        if pace_delta < 0.3:
            continue

        # Create context
        context = TeamOrderContext(
            current_lap=current_lap,
            total_laps=front.get("total_laps", 66),
            is_drs_active=rear.get("drs_enabled", False),
            target_position=front.get("position", 0),
            beneficiary_position=rear.get("position", 0),
            target_pace=front_pace,
            beneficiary_pace=rear_pace,
            pace_delta=pace_delta,
            gap_between=gap,
        )

        opportunities.append(context)

    return opportunities
