"""
Practice Session Manager Module

Manages individual practice sessions (FP1, FP2, FP3).
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .types import (
    PracticeSessionType,
    PracticeLap,
    PracticeSessionResult,
    PracticeIncident,
    RunType,
    SetupTuningResult,
)
from .lap_simulator import PracticeLapSimulator
from .setup_tuning import SetupTuningManager


@dataclass
class DriverSessionState:
    """Tracks a driver's state during a practice session."""

    driver: str
    driver_r: float = 100.0

    # Session state
    in_garage: bool = True
    current_lap: int = 0
    total_laps: int = 0
    best_lap_time: float = float("inf")

    # Current run
    current_run_type: Optional[RunType] = None
    current_stint_laps: int = 0
    target_stint_length: int = 0

    # Tyre state
    current_compound: str = ""
    tyre_age: int = 0

    # Fuel state
    fuel_kg: float = 100.0

    # Timing
    last_lap_end_time: float = 0.0
    next_available_time: float = 0.0


class PracticeSessionManager:
    """
    Manages a single practice session (FP1, FP2, or FP3).

    Simulates:
    - Driver run plans (installation, long runs, quali sims)
    - Pit stops and extended garage time
    - Traffic and yielding
    - Setup tuning dice rolls
    """

    def __init__(
        self,
        session_type: PracticeSessionType,
        track: str,
        track_base_time: float,
        drivers: List[str],
        driver_ratings: Dict[str, float],
        duration_minutes: int = 60,
        seed: Optional[int] = None,
    ):
        """
        Initialize practice session manager.

        Args:
            session_type: FP1, FP2, or FP3
            track: Track name
            track_base_time: Base lap time for track
            drivers: List of driver names
            driver_ratings: Dictionary of driver -> R rating
            duration_minutes: Session duration
            seed: Optional random seed
        """
        self.session_type = session_type
        self.track = track
        self.track_base_time = track_base_time
        self.drivers = drivers
        self.driver_ratings = driver_ratings
        self.duration_seconds = duration_minutes * 60
        self.seed = seed

        # Random number generator
        self.rng = random.Random(seed)

        # Simulators
        self.lap_simulator = PracticeLapSimulator(seed=self.rng.randint(0, 10000))
        self.setup_manager = SetupTuningManager(seed=self.rng.randint(0, 10000))

        # Session state
        self.elapsed_time = 0.0
        self.incidents: List[PracticeIncident] = []

        # Initialize driver states
        self.driver_states: Dict[str, DriverSessionState] = {}
        for driver in drivers:
            self.driver_states[driver] = DriverSessionState(
                driver=driver,
                driver_r=driver_ratings.get(driver, 100.0),
                next_available_time=self._get_random_start_time(),
            )

        # Results
        self.result = PracticeSessionResult(
            session_type=session_type,
            track=track,
            lap_times={driver: [] for driver in drivers},
            best_times={driver: float("inf") for driver in drivers},
        )

    def run_session(self) -> PracticeSessionResult:
        """
        Run the complete practice session.

        Returns:
            PracticeSessionResult with all data
        """
        print(f"\n{'=' * 70}")
        print(f"{self.session_type.value.upper()} - {self.track}")
        print(f"Duration: {self.duration_seconds // 60} minutes")
        print(f"Drivers: {len(self.drivers)}")
        print(f"{'=' * 70}\n")

        # Run setup tuning dice rolls
        self._run_setup_tuning()

        # Simulate session time
        while self.elapsed_time < self.duration_seconds:
            # Process each driver
            for driver in self.drivers:
                self._process_driver(driver)

            # Advance time (1 second increments)
            self.elapsed_time += 1.0

        # Compile final results
        self._compile_results()

        return self.result

    def _run_setup_tuning(self):
        """Run setup tuning dice rolls for all drivers."""
        setup_results = self.setup_manager.run_setup_session(
            self.drivers,
            self.session_type.value.upper(),
        )
        self.result.setup_results = setup_results

        # Print setup results
        report = self.setup_manager.generate_setup_report(setup_results)
        print(report)

    def _process_driver(self, driver: str):
        """
        Process a driver's actions at current time.

        Args:
            driver: Driver name
        """
        state = self.driver_states[driver]

        # Check if driver is available to run
        if self.elapsed_time < state.next_available_time:
            return

        # Driver is in garage - decide what to do
        if state.in_garage:
            self._decide_run_plan(driver)
        else:
            # Driver is on track - complete current lap
            self._complete_lap(driver)

    def _decide_run_plan(self, driver: str):
        """
        Decide what type of run to do next.

        Args:
            driver: Driver name
        """
        state = self.driver_states[driver]
        session_progress = self.elapsed_time / self.duration_seconds

        # Decide run type based on session phase
        if session_progress < 0.15:
            # Early session - installation/out laps
            run_type = RunType.INSTALLATION
            target_laps = self.rng.randint(3, 5)
        elif session_progress < 0.70:
            # Middle session - long runs
            if self.rng.random() < 0.7:
                run_type = RunType.LONG_RUN
                target_laps = self.rng.randint(8, 15)
            else:
                run_type = RunType.FLYING_LAP
                target_laps = self.rng.randint(2, 4)
        else:
            # Late session - quali sims
            if self.rng.random() < 0.6:
                run_type = RunType.QUALI_SIM
                target_laps = self.rng.randint(3, 5)
            else:
                run_type = RunType.FLYING_LAP
                target_laps = self.rng.randint(2, 3)

        # Set up the run
        state.in_garage = False
        state.current_run_type = run_type
        state.current_stint_laps = 0
        state.target_stint_length = target_laps
        state.tyre_age = 0

        # Choose compound
        if run_type == RunType.QUALI_SIM:
            state.current_compound = "soft"
        elif run_type == RunType.LONG_RUN:
            state.current_compound = self.rng.choice(["medium", "hard"])
        else:
            state.current_compound = self.rng.choice(["soft", "medium"])

        # First lap is out lap
        self._run_out_lap(driver)

    def _run_out_lap(self, driver: str):
        """Simulate out lap leaving pits."""
        state = self.driver_states[driver]

        lap = self.lap_simulator.simulate_out_lap(
            driver=driver,
            driver_r=state.driver_r,
            track_base_time=self.track_base_time,
            session_progress=self.elapsed_time / self.duration_seconds,
        )

        lap.session = self.session_type.value.upper()
        lap.lap_number = state.current_lap
        lap.session_time = self.elapsed_time

        self._record_lap(driver, lap)

        # Update state
        state.current_lap += 1
        state.next_available_time = self.elapsed_time + lap.lap_time

    def _complete_lap(self, driver: str):
        """Complete a lap on track."""
        state = self.driver_states[driver]

        # Check if stint is complete
        if state.current_stint_laps >= state.target_stint_length:
            # Return to pits
            self._run_in_lap(driver)
            return

        # Decide lap type
        if state.current_run_type == RunType.QUALI_SIM:
            lap = self.lap_simulator.simulate_quali_sim(
                driver=driver,
                driver_r=state.driver_r,
                track_base_time=self.track_base_time,
                session_progress=self.elapsed_time / self.duration_seconds,
                tyre_compound=state.current_compound,
                tyre_age=state.tyre_age,
            )
        elif state.current_run_type == RunType.LONG_RUN:
            lap = self.lap_simulator.simulate_long_run_lap(
                driver=driver,
                driver_r=state.driver_r,
                track_base_time=self.track_base_time,
                stint_lap=state.current_stint_laps,
                session_progress=self.elapsed_time / self.duration_seconds,
                tyre_compound=state.current_compound,
                tyre_age=state.tyre_age,
            )
        else:
            lap = self.lap_simulator.simulate_flying_lap(
                driver=driver,
                driver_r=state.driver_r,
                track_base_time=self.track_base_time,
                session_progress=self.elapsed_time / self.duration_seconds,
                tyre_compound=state.current_compound,
                tyre_age=state.tyre_age,
            )

        lap.session = self.session_type.value.upper()
        lap.lap_number = state.current_lap
        lap.session_time = self.elapsed_time

        self._record_lap(driver, lap)

        # Update state
        state.current_lap += 1
        state.current_stint_laps += 1
        state.tyre_age += 1
        state.total_laps += 1
        state.next_available_time = self.elapsed_time + lap.lap_time

    def _run_in_lap(self, driver: str):
        """Simulate in lap returning to pits."""
        state = self.driver_states[driver]

        lap = self.lap_simulator.simulate_in_lap(
            driver=driver,
            driver_r=state.driver_r,
            track_base_time=self.track_base_time,
            session_progress=self.elapsed_time / self.duration_seconds,
            tyre_compound=state.current_compound,
            tyre_age=state.tyre_age,
        )

        lap.session = self.session_type.value.upper()
        lap.lap_number = state.current_lap
        lap.session_time = self.elapsed_time

        self._record_lap(driver, lap)

        # Back to garage
        state.in_garage = True
        state.current_run_type = None
        state.current_stint_laps = 0
        state.current_lap += 1

        # Decide if extended stop (setup work)
        stop_time = self._calculate_garage_time()
        state.next_available_time = self.elapsed_time + lap.lap_time + stop_time

    def _record_lap(self, driver: str, lap: PracticeLap):
        """
        Record a completed lap.

        Args:
            driver: Driver name
            lap: PracticeLap object
        """
        self.result.lap_times[driver].append(lap)

        # Update best time if valid flying lap
        if lap.valid_lap and not lap.deleted_lap:
            if lap.run_type in [RunType.FLYING_LAP, RunType.QUALI_SIM]:
                if lap.lap_time < self.result.best_times[driver]:
                    self.result.best_times[driver] = lap.lap_time

    def _calculate_garage_time(self) -> float:
        """
        Calculate time spent in garage between runs.

        Returns:
            Time in seconds
        """
        # Normal turnaround: 60-120 seconds
        # Extended stop (setup work): 300-900 seconds (5-15 minutes)

        if self.rng.random() < 0.1:  # 10% chance of extended stop
            return self.rng.uniform(300, 900)
        else:
            return self.rng.uniform(60, 120)

    def _get_random_start_time(self) -> float:
        """Get random start time for driver (staggered starts)."""
        # Drivers leave pits at different times (0-5 minutes)
        return self.rng.uniform(0, 300)

    def _compile_results(self):
        """Compile final session results."""
        # Calculate total laps
        self.result.total_laps = sum(
            len(laps) for laps in self.result.lap_times.values()
        )

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print session summary."""
        print(f"\n{'=' * 70}")
        print(f"{self.session_type.value.upper()} RESULTS")
        print(f"{'=' * 70}")

        # Sort by best time
        standings = self.result.get_standings()

        print(f"{'Pos':<4} {'Driver':<20} {'Best Lap':<12} {'Gap':<10} {'Laps':<6}")
        print("-" * 70)

        best_time = None
        for pos, (driver, time) in enumerate(standings, 1):
            if time is None or time == float("inf"):
                continue

            if best_time is None:
                best_time = time

            gap = time - best_time if best_time else 0
            gap_str = f"+{gap:.3f}" if gap > 0 else "---"

            driver_laps = len(self.result.get_driver_laps(driver))

            print(f"{pos:<4} {driver:<20} {time:<12.3f} {gap_str:<10} {driver_laps:<6}")

        print(f"{'=' * 70}")
        print(f"Total Laps: {self.result.total_laps}")
        print(f"Incidents: {len(self.result.incidents)}")
        print(f"{'=' * 70}\n")

    def get_driver_laps(self, driver: str) -> List[PracticeLap]:
        """Get all laps for a driver."""
        return self.result.get_driver_laps(driver)

    def get_standings(self) -> List[Tuple[str, float]]:
        """Get current standings."""
        return self.result.get_standings()
