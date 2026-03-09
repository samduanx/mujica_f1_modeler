"""
Strategist System Module

This module provides the core functionality for F1 race strategy decisions,
including dice rolling mechanics, strategist profiles, and decision-making systems.
"""

from src.strategist.strategist_types import (
    StrategistProfile,
    StrategyDecision,
    RaceContext,
    DecisionType,
    DriverComplianceLevel,
    PaceMode,
    # Team Order Types
    TeamOrder,
    TeamOrderType,
    TeamOrderStatus,
    TeamOrderResult,
    TeamOrderCompliance,
    DriverTeamOrderTraits,
    TeamOrderContext,
)
from src.strategist.strategist_manager import (
    StrategistManager,
    get_manager,
)
from src.strategist.dice_mechanics import StrategistDiceRoller
from src.strategist.team_orders import (
    TeamOrderManager,
    get_driver_team_order_traits,
    execute_team_order,
    should_issue_team_order,
    DEFAULT_DRIVER_TEAM_ORDER_TRAITS,
)

__all__ = [
    "StrategistProfile",
    "StrategyDecision",
    "RaceContext",
    "DecisionType",
    "DriverComplianceLevel",
    "PaceMode",
    "StrategistManager",
    "get_manager",
    "StrategistDiceRoller",
    # Team Order exports
    "TeamOrder",
    "TeamOrderType",
    "TeamOrderStatus",
    "TeamOrderResult",
    "TeamOrderCompliance",
    "DriverTeamOrderTraits",
    "TeamOrderContext",
    "TeamOrderManager",
    "get_driver_team_order_traits",
    "execute_team_order",
    "should_issue_team_order",
    "DEFAULT_DRIVER_TEAM_ORDER_TRAITS",
]
