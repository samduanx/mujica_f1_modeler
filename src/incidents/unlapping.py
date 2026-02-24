"""
Unlapping System.

Manages the procedure for lapped cars to unlap themselves under Safety Car.
Based on F1 Sporting Regulations Article 55.14-55.15.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from incidents.vsc_sc import SafetyCarManager


class UnlappingState(Enum):
    """Unlapping procedure states"""

    NOT_ACTIVE = "not_active"
    AUTHORIZED = "authorized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RaceControlDecision:
    """
    Simulate Race Control decisions for unlapping.
    Based on F1 Sporting Regulations.
    """

    def __init__(self):
        self.decision_log: List[Dict] = []

    def should_authorize_unlapping(
        self,
        sc_duration_laps: int,
        lapped_cars_count: int,
        track_conditions: str = "dry",
        laps_remaining: int = 20,
        min_sc_laps: int = 3,
    ) -> Tuple[bool, str]:
        """
        Determine if Race Control should authorize unlapping.

        Factors based on F1 Sporting Regulations:
        - SC has been out for sufficient time (typically 3+ laps)
        - There are lapped cars to unlap
        - Track conditions permit safe unlapping
        - Sufficient laps remaining for procedure + restart

        Args:
            sc_duration_laps: Number of laps SC has been deployed
            lapped_cars_count: Number of cars 1+ laps down
            track_conditions: Current track conditions
            laps_remaining: Laps remaining in race
            min_sc_laps: Minimum SC laps before unlapping

        Returns:
            Tuple of (should_authorize, reason)
        """
        reason = ""

        # Minimum SC duration check
        if sc_duration_laps < min_sc_laps:
            reason = f"SC not out long enough ({sc_duration_laps}/{min_sc_laps} laps)"
            self._log_decision(False, reason)
            return False, reason

        # Check for lapped cars
        if lapped_cars_count == 0:
            reason = "No lapped cars to unlap"
            self._log_decision(False, reason)
            return False, reason

        # Track conditions check
        if track_conditions in ["wet", "heavy_rain", "storm"]:
            reason = f"Track conditions unsafe: {track_conditions}"
            self._log_decision(False, reason)
            return False, reason

        # Sufficient laps remaining
        # Need: current lap + procedure laps + restart laps
        min_laps_needed = sc_duration_laps + 3
        if laps_remaining < min_laps_needed:
            reason = (
                f"Insufficient laps remaining ({laps_remaining} < {min_laps_needed})"
            )
            self._log_decision(False, reason)
            return False, reason

        # All conditions met
        reason = f"Unlapping authorized - {lapped_cars_count} cars, {laps_remaining} laps remaining"
        self._log_decision(True, reason)
        return True, reason

    def _log_decision(self, authorized: bool, reason: str):
        """Log Race Control decision"""
        self.decision_log.append(
            {
                "authorized": authorized,
                "reason": reason,
            }
        )


@dataclass
class LappedCar:
    """Represents a lapped car"""

    name: str
    position: int
    laps_down: int
    can_unlap: bool = True
    has_unlapped: bool = False
    unlap_completion_lap: Optional[int] = None


class UnlappingManager:
    """
    Manage unlapping procedure under Safety Car.

    Based on F1 Sporting Regulations:
    - Article 55.14: Lapped cars must pass lead lap cars and SC
    - Article 55.15: SC returns to pits after last car passes
    """

    def __init__(self):
        # State
        self.state: UnlappingState = UnlappingState.NOT_ACTIVE
        self.lapped_cars: List[LappedCar] = []
        self.unlapped_count: int = 0
        self.total_to_unlap: int = 0

        # Timing
        self.authorization_lap: Optional[int] = None
        self.completion_lap: Optional[int] = None
        self.sc_in_lap: Optional[int] = None

        # History
        self.unlapping_history: List[Dict] = []

    @property
    def is_active(self) -> bool:
        """Check if unlapping procedure is active"""
        return self.state in [
            UnlappingState.AUTHORIZED,
            UnlappingState.IN_PROGRESS,
        ]

    @property
    def is_complete(self) -> bool:
        """Check if unlapping is complete"""
        return self.state == UnlappingState.COMPLETED

    def authorize_unlapping(
        self,
        lap: int,
        car_positions: Dict[str, int],
        car_laps: Dict[str, int],
        leader_laps: int,
    ) -> Tuple[bool, str]:
        """
        Authorize and initialize unlapping procedure.

        Args:
            lap: Current lap number
            car_positions: Dict of car name -> position
            car_laps: Dict of car name -> laps completed
            leader_laps: Laps completed by race leader

        Returns:
            Tuple of (success, message)
        """
        if self.state != UnlappingState.NOT_ACTIVE:
            return False, f"Unlapping already {self.state.value}"

        # Identify lapped cars
        self.lapped_cars = []
        for car_name, position in car_positions.items():
            car_lap = car_laps.get(car_name, leader_laps)
            laps_down = leader_laps - car_lap

            if laps_down > 0:
                self.lapped_cars.append(
                    LappedCar(
                        name=car_name,
                        position=position,
                        laps_down=laps_down,
                        can_unlap=True,
                    )
                )

        if not self.lapped_cars:
            return False, "No lapped cars to unlap"

        # Sort by position (closest to leader goes first)
        self.lapped_cars.sort(key=lambda x: x.position)

        self.total_to_unlap = len(self.lapped_cars)
        self.unlapped_count = 0
        self.state = UnlappingState.AUTHORIZED
        self.authorization_lap = lap

        self._log_event("authorized", f"Lapped cars authorized: {self.total_to_unlap}")

        return True, f"Unlapping authorized for {self.total_to_unlap} cars"

    def execute_unlap(self, car_name: str, lap: int) -> Tuple[bool, str]:
        """
        Execute unlapping for a single car.

        Args:
            car_name: Name of car completing unlapping
            lap: Current lap number

        Returns:
            Tuple of (success, message)
        """
        if self.state == UnlappingState.NOT_ACTIVE:
            return False, "Unlapping not authorized"

        if self.state == UnlappingState.COMPLETED:
            return False, "Unlapping already complete"

        # Find the car
        car = next((c for c in self.lapped_cars if c.name == car_name), None)

        if car is None:
            return False, f"Car {car_name} not in lapped list"

        if car.has_unlapped:
            return False, f"Car {car_name} already unlapped"

        # Complete unlapping for this car
        car.has_unlapped = True
        car.unlap_completion_lap = lap
        self.unlapped_count += 1

        self._log_event(
            "car_unlapped", f"{car_name} completed unlapping (P{car.position})"
        )

        # Check if all complete
        if self.unlapped_count >= self.total_to_unlap:
            self.state = UnlappingState.COMPLETED
            self.completion_lap = lap
            self._log_event("completed", f"All {self.total_to_unlap} cars unlapped")

        return True, f"{car_name} completed unlapping"

    def get_cars_to_unlap(self) -> List[str]:
        """Get list of cars that still need to unlap"""
        return [c.name for c in self.lapped_cars if not c.has_unlapped]

    def get_progress(self) -> Dict:
        """Get unlapping progress"""
        return {
            "state": self.state.value,
            "total_cars": self.total_to_unlap,
            "completed": self.unlapped_count,
            "remaining": self.total_to_unlap - self.unlapped_count,
            "progress_pct": (
                (self.unlapped_count / self.total_to_unlap * 100)
                if self.total_to_unlap > 0
                else 0
            ),
        }

    def can_sc_come_in(self) -> bool:
        """Check if SC can come in (all cars unlapped)"""
        return self.state == UnlappingState.COMPLETED

    def get_sc_in_lap(self) -> Optional[int]:
        """Get lap when SC should come in"""
        if not self.can_sc_come_in():
            return None
        # SC comes in the lap after completion
        return self.completion_lap + 1 if self.completion_lap else None

    def reset(self):
        """Reset unlapping state"""
        self.state = UnlappingState.NOT_ACTIVE
        self.lapped_cars = []
        self.unlapped_count = 0
        self.total_to_unlap = 0
        self.authorization_lap = None
        self.completion_lap = None
        self.sc_in_lap = None

    def _log_event(self, event_type: str, message: str):
        """Log an unlapping event"""
        self.unlapping_history.append(
            {
                "event": event_type,
                "message": message,
            }
        )

    def get_state(self) -> Dict:
        """Get full state"""
        return {
            "state": self.state.value,
            "cars": [
                {
                    "name": c.name,
                    "position": c.position,
                    "laps_down": c.laps_down,
                    "has_unlapped": c.has_unlapped,
                }
                for c in self.lapped_cars
            ],
            "progress": self.get_progress(),
            "can_sc_come_in": self.can_sc_come_in(),
            "sc_in_lap": self.get_sc_in_lap(),
            "history": self.unlapping_history,
        }


class SafetyCarManagerWithUnlapping(SafetyCarManager):
    """
    Extended Safety Car manager with unlapping support.
    """

    def __init__(self, base_lap_time: float):
        super().__init__(base_lap_time)
        self.unlapping = UnlappingManager()
        self.race_control = RaceControlDecision()

    def deploy(
        self,
        race_time: float,
        lap: int,
        reason: str,
        leader: str,
        car_order: List[str],
        gaps: Dict[str, float],
    ):
        """Deploy SC and reset unlapping"""
        super().deploy(race_time, lap, reason, leader, car_order, gaps)
        self.unlapping.reset()

    def authorize_unlapping(
        self,
        lap: int,
        car_positions: Dict[str, int],
        car_laps: Dict[str, int],
        leader_laps: int,
    ) -> Tuple[bool, str]:
        """Authorize and initialize unlapping"""
        if not self.is_deployed:
            return False, "Safety Car not deployed"

        return self.unlapping.authorize_unlapping(
            lap, car_positions, car_laps, leader_laps
        )

    def execute_unlap(self, car_name: str, lap: int) -> Tuple[bool, str]:
        """Execute unlapping for a car"""
        return self.unlapping.execute_unlap(car_name, lap)

    def can_come_in(self) -> Tuple[bool, str]:
        """
        Check if Safety Car can come in.

        Returns:
            Tuple of (can_come_in, reason)
        """
        if not self.is_deployed:
            return False, "SC not deployed"

        if self.unlapping.is_active:
            return False, "Unlapping in progress"

        if self.unlapping.can_sc_come_in():
            sc_in_lap = self.unlapping.get_sc_in_lap()
            return True, f"SC can come in lap {sc_in_lap}"

        return False, "Conditions not met"

    def recall(self, race_time: float, lap: int):
        """
        Signal SC to come in.

        If unlapping in progress but not complete, wait.
        """
        can_come_in, reason = self.can_come_in()

        if can_come_in:
            super().recall(race_time, lap)
        # If can't come in yet, just log the attempt
        # Actual recall will happen when conditions met

    def check_and_complete_unlapping(self, lap: int, cars_to_check: List[str]) -> Dict:
        """
        Check and complete unlapping for cars.

        Args:
            lap: Current lap number
            cars_to_check: List of car names to check for completion

        Returns:
            Dict with results
        """
        results = {
            "processed": [],
            "completed": [],
            "errors": [],
        }

        for car_name in cars_to_check:
            success, message = self.execute_unlap(car_name, lap)
            results["processed"].append(
                {
                    "car": car_name,
                    "success": success,
                    "message": message,
                }
            )

            if success:
                results["completed"].append(car_name)
            else:
                results["errors"].append(message)

        return results


class IncidentResponseUnlappingManager(UnlappingManager):
    """
    Extended unlapping manager with incident response integration.

    Connects to SafetyCarManager and provides enhanced unlapping
    procedure management during incident response periods.
    """

    def __init__(self, safety_car_manager=None):
        """
        Initialize the incident response unlapping manager.

        Args:
            safety_car_manager: Optional SafetyCarManager to connect to
        """
        super().__init__()
        self.sc_manager = safety_car_manager
        self.race_control = RaceControlDecision()

        # Track SC deployment state
        self.sc_deployment_lap: Optional[int] = None
        self.sc_laps_elapsed: int = 0
        self.unlapping_authorized: bool = False
        self.unlapping_completed: bool = False

        # Event tracking
        self.events: List[Dict] = []

    def on_sc_deployed(
        self,
        lap: int,
        car_positions: Dict[str, int],
        car_laps: Dict[str, int],
        leader_laps: int,
    ):
        """
        Called when Safety Car is deployed - prepares unlapping.

        This initializes tracking but does not immediately authorize unlapping.
        Race Control will decide when to authorize based on regulations.

        Args:
            lap: Current lap number
            car_positions: Dict of car name -> position
            car_laps: Dict of car name -> laps completed
            leader_laps: Laps completed by race leader
        """
        self.reset()
        self.sc_deployment_lap = lap
        self.sc_laps_elapsed = 0
        self.unlapping_authorized = False
        self.unlapping_completed = False

        # Identify lapped cars for tracking
        self._identify_lapped_cars(car_positions, car_laps, leader_laps)

        self._log_incident_event(
            "sc_deployed",
            {
                "lap": lap,
                "lapped_cars": len(self.lapped_cars),
                "total_cars": len(car_positions),
            },
        )

    def _identify_lapped_cars(
        self,
        car_positions: Dict[str, int],
        car_laps: Dict[str, int],
        leader_laps: int,
    ):
        """Identify lapped cars from race state"""
        self.lapped_cars = []
        for car_name, position in car_positions.items():
            car_lap = car_laps.get(car_name, leader_laps)
            laps_down = leader_laps - car_lap

            if laps_down > 0:
                self.lapped_cars.append(
                    LappedCar(
                        name=car_name,
                        position=position,
                        laps_down=laps_down,
                        can_unlap=True,
                    )
                )

        # Sort by position (closest to leader goes first)
        self.lapped_cars.sort(key=lambda x: x.position)
        self.total_to_unlap = len(self.lapped_cars)

    def update(
        self,
        lap: int,
        car_positions: Dict[str, int],
        car_laps: Dict[str, int],
        leader_laps: int,
        track_conditions: str = "dry",
        laps_remaining: int = 20,
    ) -> Optional[Dict]:
        """
        Update unlapping state each lap.

        Called once per lap during SC period. Evaluates whether to
        authorize unlapping and tracks progress.

        Args:
            lap: Current lap number
            car_positions: Dict of car name -> position
            car_laps: Dict of car name -> laps completed
            leader_laps: Laps completed by race leader
            track_conditions: Current track conditions
            laps_remaining: Laps remaining in race

        Returns:
            Event dict if state changed, None otherwise
        """
        if self.sc_deployment_lap is None:
            return None

        # Update SC duration
        self.sc_laps_elapsed = lap - self.sc_deployment_lap

        # Check if we should authorize unlapping (F1 Article 55.14-55.15)
        if not self.unlapping_authorized and not self.unlapping_completed:
            should_authorize, reason = self.race_control.should_authorize_unlapping(
                sc_duration_laps=self.sc_laps_elapsed,
                lapped_cars_count=len(self.lapped_cars),
                track_conditions=track_conditions,
                laps_remaining=laps_remaining,
                min_sc_laps=3,  # Minimum 3 SC laps before unlapping
            )

            if should_authorize:
                success, message = self.authorize_unlapping(
                    lap, car_positions, car_laps, leader_laps
                )
                if success:
                    self.unlapping_authorized = True
                    self._log_incident_event(
                        "unlapping_authorized",
                        {
                            "lap": lap,
                            "sc_laps": self.sc_laps_elapsed,
                            "cars": len(self.lapped_cars),
                            "reason": reason,
                        },
                    )
                    return {
                        "type": "unlapping_authorized",
                        "lap": lap,
                        "cars": len(self.lapped_cars),
                        "reason": reason,
                    }

        # Check if unlapping is complete
        if (
            self.unlapping_authorized
            and not self.unlapping_completed
            and self.state == UnlappingState.COMPLETED
        ):
            self.unlapping_completed = True
            self._log_incident_event(
                "unlapping_completed",
                {"lap": lap, "cars": self.unlapped_count},
            )
            return {
                "type": "unlapping_completed",
                "lap": lap,
                "cars": self.unlapped_count,
            }

        return None

    def process_car_unlap(self, car_name: str, lap: int) -> Tuple[bool, str]:
        """
        Process unlapping for a single car.

        Wrapper around execute_unlap with additional logging.

        Args:
            car_name: Name of car completing unlapping
            lap: Current lap number

        Returns:
            Tuple of (success, message)
        """
        success, message = self.execute_unlap(car_name, lap)

        if success:
            self._log_incident_event(
                "car_unlapped",
                {"car": car_name, "lap": lap, "progress": self.get_progress()},
            )
        else:
            self._log_incident_event(
                "unlap_error",
                {"car": car_name, "lap": lap, "error": message},
            )

        return success, message

    def should_sc_come_in(self) -> Tuple[bool, Optional[int], str]:
        """
        Determine if Safety Car should come in.

        Returns:
            Tuple of (should_come_in, lap_to_come_in, reason)
        """
        if not self.unlapping_authorized:
            return False, None, "Unlapping not yet authorized"

        if not self.can_sc_come_in():
            return False, None, "Unlapping in progress"

        sc_in_lap = self.get_sc_in_lap()
        if sc_in_lap:
            return True, sc_in_lap, f"SC can come in lap {sc_in_lap}"

        return False, None, "Conditions not met"

    def get_incident_response_state(self) -> Dict:
        """
        Get full incident response state.

        Returns comprehensive state for integration with incident system.
        """
        return {
            "sc_deployment_lap": self.sc_deployment_lap,
            "sc_laps_elapsed": self.sc_laps_elapsed,
            "unlapping_authorized": self.unlapping_authorized,
            "unlapping_completed": self.unlapping_completed,
            "unlapping_state": self.state.value,
            "lapped_cars_total": self.total_to_unlap,
            "lapped_cars_completed": self.unlapped_count,
            "lapped_cars_remaining": self.total_to_unlap - self.unlapped_count,
            "sc_can_come_in": self.can_sc_come_in(),
            "sc_in_lap": self.get_sc_in_lap(),
            "events": self.events,
        }

    def reset(self):
        """Reset all state"""
        super().reset()
        self.sc_deployment_lap = None
        self.sc_laps_elapsed = 0
        self.unlapping_authorized = False
        self.unlapping_completed = False
        self.events = []

    def _log_incident_event(self, event_type: str, data: Dict):
        """Log an incident response event"""
        self.events.append({"type": event_type, "data": data})


# F1 Article 55.14-55.15 compliance helper functions
def check_f1_article_55_compliance(
    sc_duration_laps: int,
    lapped_cars_count: int,
    track_conditions: str,
    laps_remaining: int,
) -> Tuple[bool, List[str]]:
    """
    Check compliance with F1 Sporting Regulations Article 55.14-55.15.

    Article 55.14: Lapped cars must pass the cars on the lead lap and the Safety Car
    Article 55.15: Once the last lapped car has passed the leader, the Safety Car
                   will return to the pits at the end of the following lap

    Args:
        sc_duration_laps: Number of laps SC has been deployed
        lapped_cars_count: Number of cars that are lapped
        track_conditions: Current track conditions
        laps_remaining: Laps remaining in race

    Returns:
        Tuple of (is_compliant, list_of_requirements_met)
    """
    requirements = []

    # Minimum SC duration (typically 3 laps for track cleanup)
    if sc_duration_laps >= 3:
        requirements.append("Minimum SC duration met")
    else:
        requirements.append(f"SC duration insufficient ({sc_duration_laps}/3 laps)")

    # Lapped cars exist
    if lapped_cars_count > 0:
        requirements.append("Lapped cars exist")
    else:
        requirements.append("No lapped cars")

    # Track conditions permit
    if track_conditions not in ["wet", "heavy_rain", "storm"]:
        requirements.append("Track conditions safe")
    else:
        requirements.append(f"Unsafe track conditions: {track_conditions}")

    # Sufficient laps remaining
    min_laps_needed = sc_duration_laps + 3
    if laps_remaining >= min_laps_needed:
        requirements.append("Sufficient laps remaining")
    else:
        requirements.append(f"Insufficient laps ({laps_remaining} < {min_laps_needed})")

    is_compliant = all(
        req.startswith(("Minimum", "Lapped", "Track", "Sufficient"))
        and "insufficient" not in req.lower()
        and "unsafe" not in req.lower()
        and "no " not in req.lower()
        for req in requirements
    )

    return is_compliant, requirements
