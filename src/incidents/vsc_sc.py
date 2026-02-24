"""
VSC (Virtual Safety Car) and Safety Car (SC) Systems.

Manages VSC and Safety Car periods during race.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class SafetyCarState(Enum):
    """Safety car states"""

    INACTIVE = "inactive"
    VSC = "vsc"  # Virtual Safety Car
    SC = "sc"  # Safety Car


@dataclass
class VSCConfig:
    """VSC (Virtual Safety Car) configuration"""

    # VSC target lap time is 70% of normal (F1 regulations)
    # This means cars go ~30% slower in speed terms
    vsc_time_factor: float = 0.70

    # Delta tolerance - drivers must stay within this of VSC delta
    delta_tolerance: float = 0.5  # seconds

    # Minimum/maximum VSC duration
    min_vsc_duration: float = 1.0  # laps
    max_vsc_duration: float = 5.0  # laps


@dataclass
class SafetyCarConfig:
    """Safety Car configuration"""

    # SC target lap time is 60% of normal (slower than VSC)
    sc_time_factor: float = 0.60

    # Gap maintenance
    pack_tightening_enabled: bool = True

    # Minimum/maximum SC duration
    min_sc_duration: float = 1.0  # laps
    max_sc_duration: float = 10.0  # laps


class VSCManager:
    """
    Manage Virtual Safety Car periods.

    Key characteristics:
    - Limits speed to ~70% of normal lap time
    - Does NOT require pack tightening (gaps maintained)
    - All drivers must maintain relative gaps
    """

    def __init__(self, base_lap_time: float, config: Optional[VSCConfig] = None):
        """
        Initialize VSC manager.

        Args:
            base_lap_time: Normal lap time in seconds
            config: VSC configuration
        """
        self.base_lap_time = base_lap_time
        self.config = config or VSCConfig()

        # VSC target lap time = 70% of normal
        self.vsc_target_lap_time = base_lap_time * self.config.vsc_time_factor

        # State
        self.is_active = False
        self.activation_time: Optional[float] = None
        self.activation_lap: Optional[int] = None
        self.vsc_periods: List[Dict] = []

    def activate(self, race_time: float, lap: int, reason: str):
        """Activate VSC"""
        if self.is_active:
            return  # Already active

        self.is_active = True
        self.activation_time = race_time
        self.activation_lap = lap

        self.vsc_periods.append(
            {
                "start_time": race_time,
                "start_lap": lap,
                "reason": reason,
                "end_time": None,
                "end_lap": None,
                "duration": None,
            }
        )

    def deactivate(self, race_time: float, lap: int):
        """Deactivate VSC"""
        if not self.is_active:
            return

        if self.vsc_periods:
            period = self.vsc_periods[-1]
            period["end_time"] = race_time
            period["end_lap"] = lap
            period["duration"] = race_time - period["start_time"]

        self.is_active = False
        self.activation_time = None
        self.activation_lap = None

    def get_target_lap_time(self) -> float:
        """Get target lap time under VSC"""
        return self.vsc_target_lap_time

    def get_speed_factor(self) -> float:
        """Get speed factor (relative to normal)"""
        return self.config.vsc_time_factor

    def check_delta_compliance(
        self, driver_lap_time: float, target_time: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Check if driver is maintaining VSC delta.

        Returns:
            Tuple of (is_compliant, deviation)
        """
        target = target_time or self.vsc_target_lap_time
        deviation = abs(driver_lap_time - target)
        is_compliant = deviation <= self.config.delta_tolerance
        return is_compliant, deviation

    def get_state(self) -> Dict:
        """Get current VSC state"""
        return {
            "active": self.is_active,
            "target_lap_time": self.vsc_target_lap_time,
            "activation_time": self.activation_time,
            "periods_count": len(self.vsc_periods),
        }


class SafetyCarManager:
    """
    Manage Safety Car periods.

    Key characteristics:
    - Limits speed more than VSC (~60% of normal)
    - Requires pack tightening (all cars bunch up)
    - SC leads the pack around track
    """

    def __init__(self, base_lap_time: float, config: Optional[SafetyCarConfig] = None):
        """
        Initialize Safety Car manager.

        Args:
            base_lap_time: Normal lap time in seconds
            config: Safety Car configuration
        """
        self.base_lap_time = base_lap_time
        self.config = config or SafetyCarConfig()

        # SC target lap time = 60% of normal
        self.sc_target_lap_time = base_lap_time * self.config.sc_time_factor

        # State
        self.is_deployed = False
        self.leader_behind_sc: Optional[str] = None
        self.activation_time: Optional[float] = None
        self.activation_lap: Optional[int] = None
        self.sc_periods: List[Dict] = []

        # Pack management
        self.car_order_before_sc: List[str] = []
        self.pack_gaps_before_sc: Dict[str, float] = {}

    def deploy(
        self,
        race_time: float,
        lap: int,
        reason: str,
        leader: str,
        car_order: List[str],
        gaps: Dict[str, float],
    ):
        """Deploy Safety Car"""
        if self.is_deployed:
            return  # Already deployed

        self.is_deployed = True
        self.leader_behind_sc = leader
        self.activation_time = race_time
        self.activation_lap = lap

        # Save pack state for later
        self.car_order_before_sc = car_order.copy()
        self.pack_gaps_before_sc = gaps.copy()

        self.sc_periods.append(
            {
                "start_time": race_time,
                "start_lap": lap,
                "reason": reason,
                "leader": leader,
                "end_time": None,
                "end_lap": None,
                "duration": None,
            }
        )

    def recall(self, race_time: float, lap: int):
        """
        Signal SC to come in at end of next lap.
        Called one lap before restart.
        """
        if self.is_deployed and self.sc_periods:
            period = self.sc_periods[-1]
            period["coming_in"] = True
            period["coming_in_lap"] = lap

    def deactivate(self, race_time: float, lap: int):
        """Deactivate Safety Car - racing resumes"""
        if not self.is_deployed:
            return

        if self.sc_periods:
            period = self.sc_periods[-1]
            period["end_time"] = race_time
            period["end_lap"] = lap
            period["duration"] = race_time - period["start_time"]

        self.is_deployed = False
        self.leader_behind_sc = None
        self.activation_time = None
        self.activation_lap = None

    def get_target_lap_time(self) -> float:
        """Get target lap time under Safety Car"""
        return self.sc_target_lap_time

    def get_speed_factor(self) -> float:
        """Get speed factor (relative to normal)"""
        return self.config.sc_time_factor

    def calculate_pack_gaps(
        self, leader_name: str, all_drivers: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate target gaps when pack is tightened.

        Under SC, all cars should be bunched together behind the SC.
        Returns target gap to car ahead for each driver.
        """
        if not self.is_deployed:
            return all_drivers.copy()

        # Sort drivers by their positions
        sorted_drivers = sorted(all_drivers.items(), key=lambda x: x[1])

        # Under SC, gaps are much smaller
        target_gaps = {}

        for i, (name, original_gap) in enumerate(sorted_drivers):
            if i == 0:
                # First car - gap to SC is minimal
                target_gaps[name] = 0.5  # 0.5s behind SC
            else:
                # Other cars - tight formation
                target_gaps[name] = 0.3  # 0.3s behind car ahead

        return target_gaps

    def get_state(self) -> Dict:
        """Get current SC state"""
        return {
            "deployed": self.is_deployed,
            "target_lap_time": self.sc_target_lap_time,
            "leader": self.leader_behind_sc,
            "activation_time": self.activation_time,
            "periods_count": len(self.sc_periods),
        }


class SafetyResponseManager:
    """
    Combined manager for VSC and Safety Car.

    Coordinates between the two systems and handles transitions.
    """

    def __init__(
        self,
        base_lap_time: float,
        vsc_config: Optional[VSCConfig] = None,
        sc_config: Optional[SafetyCarConfig] = None,
    ):
        self.base_lap_time = base_lap_time

        # Initialize managers
        self.vsc = VSCManager(base_lap_time, vsc_config)
        self.sc = SafetyCarManager(base_lap_time, sc_config)

        # Current state
        self.current_response: SafetyCarState = SafetyCarState.INACTIVE

        # Response history
        self.response_history: List[Dict] = []

    @property
    def is_active(self) -> bool:
        """Check if any safety response is active"""
        return self.vsc.is_active or self.sc.is_deployed

    @property
    def is_vsc(self) -> bool:
        """Check if VSC is active"""
        return self.vsc.is_active

    @property
    def is_sc(self) -> bool:
        """Check if Safety Car is deployed"""
        return self.sc.is_deployed

    def activate_vsc(self, race_time: float, lap: int, reason: str):
        """Activate VSC"""
        if self.current_response != SafetyCarState.INACTIVE:
            return  # Already in some response mode

        self.vsc.activate(race_time, lap, reason)
        self.current_response = SafetyCarState.VSC

        self.response_history.append(
            {
                "time": race_time,
                "lap": lap,
                "type": "vsc",
                "reason": reason,
            }
        )

    def activate_sc(
        self,
        race_time: float,
        lap: int,
        reason: str,
        leader: str,
        car_order: List[str],
        gaps: Dict[str, float],
    ):
        """Deploy Safety Car"""
        # First deactivate VSC if active
        if self.vsc.is_active:
            self.vsc.deactivate(race_time, lap)

        self.sc.deploy(race_time, lap, reason, leader, car_order, gaps)
        self.current_response = SafetyCarState.SC

        self.response_history.append(
            {
                "time": race_time,
                "lap": lap,
                "type": "sc",
                "reason": reason,
            }
        )

    def deactivate(self, race_time: float, lap: int):
        """Deactivate current response"""
        if self.vsc.is_active:
            self.vsc.deactivate(race_time, lap)
        elif self.sc.is_deployed:
            self.sc.deactivate(race_time, lap)

        if self.current_response != SafetyCarState.INACTIVE:
            self.response_history.append(
                {
                    "time": race_time,
                    "lap": lap,
                    "type": "resume",
                    "previous": self.current_response.value,
                }
            )

        self.current_response = SafetyCarState.INACTIVE

    def escalate_to_sc(
        self,
        race_time: float,
        lap: int,
        reason: str,
        leader: str,
        car_order: List[str],
        gaps: Dict[str, float],
    ):
        """Escalate from VSC to Safety Car"""
        self.vsc.deactivate(race_time, lap)
        self.sc.deploy(race_time, lap, reason, leader, car_order, gaps)
        self.current_response = SafetyCarState.SC

        self.response_history.append(
            {
                "time": race_time,
                "lap": lap,
                "type": "escalation",
                "from": "vsc",
                "to": "sc",
                "reason": reason,
            }
        )

    def get_target_lap_time(self) -> float:
        """Get target lap time based on current response"""
        if self.sc.is_deployed:
            return self.sc.get_target_lap_time()
        elif self.vsc.is_active:
            return self.vsc.get_target_lap_time()
        else:
            return self.base_lap_time

    def get_speed_factor(self) -> float:
        """Get speed factor based on current response"""
        if self.sc.is_deployed:
            return self.sc.get_speed_factor()
        elif self.vsc.is_active:
            return self.vsc.get_speed_factor()
        else:
            return 1.0

    def get_state(self) -> Dict:
        """Get full state"""
        return {
            "current_response": self.current_response.value,
            "is_active": self.is_active,
            "vsc_state": self.vsc.get_state(),
            "sc_state": self.sc.get_state(),
            "target_lap_time": self.get_target_lap_time(),
            "speed_factor": self.get_speed_factor(),
        }

    def can_overtake(self) -> bool:
        """Check if overtaking is allowed"""
        # No overtaking under VSC or SC
        return not self.is_active

    def get_delta_target(self, driver_position: int) -> float:
        """
        Get delta target for a driver.

        Under VSC: maintain relative gaps
        Under SC: tight pack formation
        """
        if self.sc.is_deployed:
            # Tight pack - small gaps
            return 0.3 * driver_position
        elif self.vsc.is_active:
            # Maintain gaps - use original gaps
            return 0.0  # Would need to track original gaps
        else:
            return 0.0
