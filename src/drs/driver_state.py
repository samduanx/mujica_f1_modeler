"""
Driver state tracking for DRS simulation.

Tracks cumulative time, lap times, and DRS-related state for each driver.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random


@dataclass
class DriverRaceState:
    """
    State tracking for one driver during DRS simulation.

    Attributes:
        name: Driver name
        r_value: Raw pace value (determines base speed)
        dr_value: Racecraft/consistency value
        grid_position: Starting grid position
        cumulative_time: Total race time in seconds
        lap_times: List of lap times
        interval_times: List of all interval times
        interval_data: Detailed interval data for analysis
        current_sector: Current sector (1, 2, or 3)
        current_distance: Current distance within the track (meters)
        current_interval: Current interval index within the lap
        gap_to_ahead: Time gap to the car ahead (seconds)
        position: Current race position
        tyre_compound: Current tyre compound
        laps_on_tyre: Laps completed on current tyre
        pit_stops: Number of pit stops completed
        pit_laps: List of lap numbers where pit stops occurred
        drs_available: Whether DRS is currently available to this driver
        drs_activations: Count of DRS activations
        drs_gains: Total time gained from DRS
        tyre_degradation: Current tyre degradation factor
    """

    name: str
    r_value: float
    dr_value: float
    grid_position: int

    # Timing data
    cumulative_time: float = 0.0
    lap_times: List[float] = field(default_factory=list)
    interval_times: List[float] = field(default_factory=list)
    interval_data: List[Dict] = field(default_factory=list)

    # Position tracking
    current_sector: int = 1
    current_distance: float = 0.0
    current_interval: int = 0
    gap_to_ahead: float = float("inf")
    position: int = 0

    # Tyre state
    tyre_compound: str = "C3"
    laps_on_tyre: int = 0
    pit_stops: int = 0
    pit_laps: List[int] = field(default_factory=list)
    tyre_degradation: float = 1.0

    # DRS state
    drs_available: bool = False
    drs_activations: int = 0
    drs_gains: float = 0.0

    def get_current_lap(self) -> int:
        """Get current lap number (1-indexed)"""
        return len(self.lap_times) + 1

    def get_lap_elapsed_time(self) -> float:
        """Get time elapsed in current lap"""
        if not self.lap_times:
            return self.cumulative_time
        return self.cumulative_time - sum(self.lap_times[:-1])

    def update_position(self, new_position: int):
        """Update race position"""
        self.position = new_position

    def update_gap(self, target_state: "DriverRaceState"):
        """Update gap to car ahead"""
        if target_state:
            self.gap_to_ahead = self.cumulative_time - target_state.cumulative_time

    def add_lap_time(self, lap_time: float):
        """Record a completed lap time"""
        self.lap_times.append(lap_time)
        self.current_sector = 1
        self.current_interval = 0

    def add_interval_time(self, interval_time: float, interval_data: Dict):
        """Record an interval time with data"""
        self.interval_times.append(interval_time)
        self.cumulative_time += interval_time
        self.interval_data.append(interval_data)
        self.current_interval += 1

    def pit_stop(self, new_compound: str):
        """Record a pit stop"""
        self.pit_stops += 1
        self.pit_laps.append(self.get_current_lap())
        self.tyre_compound = new_compound
        self.laps_on_tyre = 0
        self.tyre_degradation = 1.0

    def advance_tyre(self):
        """Advance tyre state by one lap"""
        self.laps_on_tyre += 1
        # Simple degradation model
        self.tyre_degradation = 1.0 + (self.laps_on_tyre * 0.01)

    def activate_drs(self, time_gain: float):
        """Record DRS activation with time gain"""
        self.drs_available = True
        self.drs_activations += 1
        self.drs_gains += time_gain

    def deactivate_drs(self):
        """Deactivate DRS when exiting zone"""
        self.drs_available = False

    def get_drs_stats(self) -> Dict:
        """Get DRS statistics for this driver"""
        return {
            "activations": self.drs_activations,
            "total_gain": self.drs_gains,
            "avg_gain": self.drs_gains / self.drs_activations
            if self.drs_activations > 0
            else 0.0,
        }

    def get_average_lap_time(self) -> float:
        """Calculate average lap time"""
        if not self.lap_times:
            return 0.0
        return sum(self.lap_times) / len(self.lap_times)

    def get_total_drs_time(self) -> float:
        """Get total time spent in DRS zones"""
        # Estimate based on interval data
        drs_intervals = [d for d in self.interval_data if d.get("in_drs_zone", False)]
        if not drs_intervals:
            return 0.0
        return sum(
            d["base_interval_time"] - d["actual_interval_time"] for d in drs_intervals
        )


@dataclass
class DriverTestData:
    """
    Simplified driver data for testing DRS simulation.

    Attributes:
        name: Driver name
        r_value: Raw pace value (determines base speed)
        dr_value: Racecraft/consistency value
        grid_position: Starting grid position
        team: Team name
    """

    name: str
    r_value: float
    dr_value: float
    grid_position: int
    team: str = "Unknown"

    def to_state(self) -> DriverRaceState:
        """Convert to race state"""
        return DriverRaceState(
            name=self.name,
            r_value=self.r_value,
            dr_value=self.dr_value,
            grid_position=self.grid_position,
            position=self.grid_position,
        )


# Test data for prototype
TEST_DRIVERS = [
    DriverTestData("Verstappen", 310.0, 92, 1, "Red Bull"),
    DriverTestData("Norris", 308.0, 88, 2, "McLaren"),
    DriverTestData("Leclerc", 305.2, 85, 3, "Ferrari"),
    DriverTestData("Hamilton", 307.5, 88, 4, "Mercedes"),
    DriverTestData("Sainz", 304.5, 82, 5, "Ferrari"),
    DriverTestData("Russell", 305.8, 84, 6, "Mercedes"),
    DriverTestData("Piastri", 303.5, 80, 7, "McLaren"),
    DriverTestData("Alonso", 302.0, 90, 8, "Aston Martin"),
]


def create_test_driver_states(
    drivers: List[DriverTestData] = None,
) -> Dict[str, DriverRaceState]:
    """Create driver states from test data"""
    if drivers is None:
        drivers = TEST_DRIVERS

    states = {}
    for driver in drivers:
        state = driver.to_state()
        states[driver.name] = state

    return states


def create_driver_states_from_csv(csv_file: str) -> Dict[str, DriverRaceState]:
    """
    Create driver states from CSV file.

    Expected CSV format:
    Driver,R_Value,DR_Value,Team
    Verstappen,310.0,92,Red Bull
    ...
    """
    import pandas as pd

    df = pd.read_csv(csv_file)
    states = {}

    for idx, row in df.iterrows():
        driver = DriverTestData(
            name=row["Driver"],
            r_value=row["R_Value"],
            dr_value=row.get("DR_Value", 80),
            grid_position=idx + 1,
            team=row.get("Team", "Unknown"),
        )
        states[driver.name] = driver.to_state()

    return states


# ============================================================================
# Overtake System Helper Functions
# ============================================================================

def get_dr_modifier(dr_value: float) -> float:
    """
    Calculate DR modifier for overtake dice.
    
    Formula: (DR_Value - 80) / 2
    
    Examples:
        DR 80 -> -5.0 (Novice)
        DR 86 ->  0.0 (Average)
        DR 92 -> +6.0 (Elite)
    
    Args:
        dr_value: Driver's DR value (typically 80-92)
        
    Returns:
        DR modifier (-5 to +6)
    """
    return (dr_value - 80) / 2.0


def get_dr_penalty(dr_value: float) -> float:
    """
    Calculate DR penalty for comparisons (half of modifier).
    
    Formula: (DR_Value - 80) / 4
    
    Used when comparing two drivers' DR values.
    
    Args:
        dr_value: Driver's DR value
        
    Returns:
        DR penalty (-2.5 to +3)
    """
    return (dr_value - 80) / 4.0


def get_r_pace_modifier(r_value: float, base_r: float = 302.0) -> float:
    """
    Calculate R pace modifier for overtake calculations.
    
    Formula: (R_Value - Base_R) / 10
    
    Examples:
        R 310 vs 302 -> +0.8 pace advantage
        R 305 vs 302 -> +0.3 pace advantage
    
    Args:
        r_value: Driver's R value
        base_r: Base R value for comparison (default 302)
        
    Returns:
        Pace modifier
    """
    return (r_value - base_r) / 10.0


def get_dr_description(dr_value: float) -> str:
    """
    Get a text description of DR value level.
    
    Args:
        dr_value: Driver's DR value
        
    Returns:
        Description string
    """
    if dr_value >= 91:
        return "Elite"
    elif dr_value >= 87:
        return "Excellent"
    elif dr_value >= 84:
        return "Good"
    elif dr_value >= 81:
        return "Average"
    else:
        return "Below Average"
