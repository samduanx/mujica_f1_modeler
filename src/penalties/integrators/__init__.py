"""
Penalty Integrators.

Connectors between existing incident systems and the penalty system.
"""

from src.penalties.integrators.overtake_penalties import OvertakePenaltyHandler
from src.penalties.integrators.blue_flag_penalties import BlueFlagPenaltyHandler
from src.penalties.integrators.vsc_penalties import VSCViolationHandler
from src.penalties.integrators.incident_penalties import IncidentPenaltyHandler

__all__ = [
    "OvertakePenaltyHandler",
    "BlueFlagPenaltyHandler",
    "VSCViolationHandler",
    "IncidentPenaltyHandler",
]
