"""
Team Order Strategy Decision Module

Handles team order decisions during a race:
- detect_team_order_opportunity(): Check if team order should be issued
- execute_team_order_decision(): Execute a team order with compliance check
- integrate with driver skills (团队精神, 狮子, 好大哥)

Based on driver ratings from data/driver_ratings.csv:
- 拉塞尔 (Russell): 团队精神 - 1d10=1或2以外的所有值时让车 (80% compliance)
- 奥康 (Ocon): 狮子 - 无视车队指令 (0% compliance)
- 博塔斯 (Bottas): 好大哥 - 在车队指令或overtake模式下帮助周冠宇
"""

from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass

from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    OutcomeLevel,
    TeamOrder,
    TeamOrderType,
    TeamOrderStatus,
    TeamOrderResult,
    TeamOrderCompliance,
    DriverTeamOrderTraits,
    TeamOrderContext,
)
from src.strategist.team_orders import (
    TeamOrderManager,
    get_driver_team_order_traits,
    should_issue_team_order,
    execute_team_order,
)
from src.strategist.dice_mechanics import StrategistDiceRoller


@dataclass
class TeamOrderDecisionResult:
    """Result of a team order strategy decision."""

    decision: StrategyDecision
    order: Optional[TeamOrder] = None
    execution_result: Optional[TeamOrderResult] = None
    positions_swapped: bool = False


class TeamOrderStrategy:
    """
    Strategy component for team order decisions.

    Integrates with the strategist system to issue and execute team orders.
    """

    def __init__(self, strategist: StrategistProfile):
        """
        Initialize with strategist.

        Args:
            strategist: The strategist making decisions
        """
        self.strategist = strategist
        self.order_manager = TeamOrderManager()
        self.roller = StrategistDiceRoller(strategist)

    def detect_opportunity(
        self,
        team: str,
        front_driver: str,
        rear_driver: str,
        front_position: int,
        rear_position: int,
        front_pace: float,
        rear_pace: float,
        gap: float,
        current_lap: int,
        is_drs_zone: bool = False,
        min_pace_delta: float = 0.3,
    ) -> Optional[TeamOrder]:
        """
        Detect if a team order opportunity exists and issue order.

        Args:
            team: Team name
            front_driver: Driver in front
            rear_driver: Driver behind
            front_position: Position of front driver
            rear_position: Position of rear driver
            front_pace: Pace of front driver (s/lap)
            rear_pace: Pace of rear driver (s/lap)
            gap: Gap between cars (seconds)
            current_lap: Current lap
            is_drs_zone: Whether in DRS zone
            min_pace_delta: Minimum pace advantage to trigger

        Returns:
            TeamOrder if issued, None otherwise
        """
        # Check if swap should be issued
        should_issue, reason = should_issue_team_order(
            front_driver=front_driver,
            rear_driver=rear_driver,
            front_pace=front_pace,
            rear_pace=rear_pace,
            gap=gap,
            is_same_team=True,
            is_drs_zone=is_drs_zone,
            min_pace_delta=min_pace_delta,
        )

        if not should_issue:
            return None

        # Calculate pace delta (rear - front, negative = rear faster)
        pace_delta = rear_pace - front_pace

        # Issue the order
        return self.order_manager.check_and_issue_swap_order(
            team=team,
            front_driver=front_driver,
            rear_driver=rear_driver,
            front_position=front_position,
            rear_position=rear_position,
            pace_delta=abs(pace_delta),
            gap=gap,
            current_lap=current_lap,
            is_drs_zone=is_drs_zone,
            min_pace_delta=min_pace_delta,
        )

    def execute_order(
        self,
        order: TeamOrder,
    ) -> TeamOrderResult:
        """
        Execute a team order with compliance check.

        Args:
            order: The team order to execute

        Returns:
            TeamOrderResult with execution outcome
        """
        return self.order_manager.execute_team_order_by_driver_name(order)

    def decide_team_order(
        self,
        race_context: RaceContext,
        team: str,
        front_driver: str,
        rear_driver: str,
        front_position: int,
        rear_position: int,
        pace_delta: float,
        gap: float,
        is_drs_zone: bool = False,
    ) -> TeamOrderDecisionResult:
        """
        Make a complete team order decision.

        This includes:
        1. Decision roll by strategist
        2. Detecting opportunity
        3. Issuing order
        4. Driver compliance check

        Args:
            race_context: Current race context
            team: Team name
            front_driver: Driver in front (target)
            rear_driver: Driver behind (beneficiary)
            front_position: Position of front driver
            rear_position: Position of rear driver
            pace_delta: Pace advantage of rear driver
            gap: Gap between cars
            is_drs_zone: Whether in DRS zone

        Returns:
            TeamOrderDecisionResult with full decision chain
        """
        # Strategist decision roll (whether to issue the order)
        base_tn = 10
        modifiers = self.roller.calculate_modifiers(
            DecisionType.TEAM_ORDER, race_context, base_tn
        )

        # Use the roll_decision method to get a StrategyDecision
        decision = self.roller.roll_decision(
            DecisionType.TEAM_ORDER, race_context, base_tn
        )

        # Update description
        decision.description = f"Team order: {front_driver} let {rear_driver} through"

        # If strategist decision failed, no order issued
        if decision.outcome in (
            OutcomeLevel.FAILURE,
            OutcomeLevel.CRITICAL_FAILURE,
        ):
            return TeamOrderDecisionResult(
                decision=decision,
                order=None,
                execution_result=None,
                positions_swapped=False,
            )

        # Detect and issue opportunity
        order = self.detect_opportunity(
            team=team,
            front_driver=front_driver,
            rear_driver=rear_driver,
            front_position=front_position,
            rear_position=rear_position,
            front_pace=race_context.tyre_life * 0.01,  # Placeholder
            rear_pace=race_context.tyre_life * 0.01 - pace_delta,
            gap=gap,
            current_lap=race_context.current_lap,
            is_drs_zone=is_drs_zone,
        )

        if order is None:
            decision.description += " - No opportunity detected"
            return TeamOrderDecisionResult(
                decision=decision,
                order=None,
                execution_result=None,
                positions_swapped=False,
            )

        # Execute order
        execution_result = self.execute_order(order)

        return TeamOrderDecisionResult(
            decision=decision,
            order=order,
            execution_result=execution_result,
            positions_swapped=execution_result.position_swap,
        )

    def periodic_check(
        self,
        race_positions: List[Dict[str, Any]],
        team_assignments: Dict[str, str],
        current_lap: int,
        check_interval: int = 5,
    ) -> List[TeamOrder]:
        """
        Periodic check for team order opportunities.

        Args:
            race_positions: List of position data
            team_assignments: Dict mapping driver -> team
            current_lap: Current lap
            check_interval: Check every N laps

        Returns:
            List of orders issued
        """
        # Only check every N laps
        if current_lap % check_interval != 0:
            return []

        issued_orders = []

        # Sort by position
        sorted_positions = sorted(race_positions, key=lambda x: x.get("position", 999))

        for i in range(len(sorted_positions) - 1):
            front = sorted_positions[i]
            rear = sorted_positions[i + 1]

            front_driver = front.get("driver", "")
            rear_driver = rear.get("driver", "")

            if not front_driver or not rear_driver:
                continue

            # Check same team
            if team_assignments.get(front_driver) != team_assignments.get(rear_driver):
                continue

            team = team_assignments.get(front_driver, "")

            # Get data
            gap = rear.get("gap_ahead", float("inf"))
            front_pace = front.get("pace", 0.0)
            rear_pace = rear.get("pace", 0.0)
            is_drs = rear.get("drs_enabled", False)

            # Detect opportunity
            order = self.detect_opportunity(
                team=team,
                front_driver=front_driver,
                rear_driver=rear_driver,
                front_position=front.get("position", 0),
                rear_position=rear.get("position", 0),
                front_pace=front_pace,
                rear_pace=rear_pace,
                gap=gap,
                current_lap=current_lap,
                is_drs_zone=is_drs,
            )

            if order:
                issued_orders.append(order)

        return issued_orders

    def get_order_history(self) -> List[TeamOrder]:
        """Get history of all orders."""
        return self.order_manager.order_history

    def get_driver_disobey_count(self, driver_name: str) -> int:
        """Get number of times driver disobeyed orders."""
        return self.order_manager.get_driver_disobey_count(driver_name)


def quick_team_order_check(
    target_driver: str,
    beneficiary_driver: str,
    team: str,
    pace_delta: float,
    gap: float,
) -> Tuple[bool, str]:
    """
    Quick check if team order should be issued and executed.

    This is a simplified entry point for simulations.

    Args:
        target_driver: Driver who should yield
        beneficiary_driver: Driver who benefits
        team: Team name
        pace_delta: Pace advantage of beneficiary (s/lap)
        gap: Gap between cars (seconds)

    Returns:
        Tuple of (positions_swapped, message)
    """
    # Check if should issue
    should_issue, reason = should_issue_team_order(
        front_driver=target_driver,
        rear_driver=beneficiary_driver,
        front_pace=0.0,
        rear_pace=-pace_delta,  # Negative = faster
        gap=gap,
        is_same_team=True,
    )

    if not should_issue:
        return False, f"No team order issued: {reason}"

    # Execute
    result = execute_team_order(
        target_driver=target_driver,
        beneficiary_driver=beneficiary_driver,
        team=team,
        order_type=TeamOrderType.SWAP_POSITIONS,
    )

    return result.position_swap, result.message
