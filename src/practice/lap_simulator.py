"""
Practice Lap Simulator Module

Simulates lap times during practice sessions with various run types.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .types import PracticeLap, RunType


@dataclass
class LapTimeFactors:
    """Factors that affect lap time in practice."""

    base_time: float = 90.0
    fuel_load_factor: float = 1.0
    tyre_condition_factor: float = 1.0
    track_evolution_factor: float = 1.0
    traffic_factor: float = 1.0
    drs_factor: float = 1.0
    driver_r_factor: float = 1.0


class PracticeLapSimulator:
    """
    Simulates lap times for practice sessions.

    Factors considered:
    - Base lap time from track and driver rating
    - Fuel load (heavier in long runs)
    - Tyre condition (degrades over stint)
    - Track evolution (grip improves)
    - Traffic (yielding in practice)
    - DRS availability
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize lap simulator.

        Args:
            seed: Optional random seed
        """
        self.rng = random.Random(seed) if seed is not None else random

        # Constants
        self.FUEL_EFFECT_PER_KG = 0.03  # 0.03s per kg of fuel
        self.BASE_FUEL_KG = 100  # Base fuel load
        self.QUALI_FUEL_KG = 10  # Low fuel for quali sim
        self.DRS_GAIN = 0.3  # 0.3s gain from DRS
        self.TRAFFIC_LOSS_RANGE = (0.3, 2.0)  # 0.3-2.0s lost to traffic

    def calculate_driver_r_factor(
        self, driver_r: float, reference_r: float = 100.0
    ) -> float:
        """
        Calculate time factor from driver R rating.

        Args:
            driver_r: Driver's R rating
            reference_r: Reference R rating (default 100)

        Returns:
            Time multiplier (lower is faster)
        """
        # Each point of R is worth approximately 0.1% lap time
        r_diff = driver_r - reference_r
        return 1.0 - (r_diff * 0.001)

    def calculate_fuel_factor(self, fuel_kg: float) -> float:
        """
        Calculate time factor from fuel load.

        Args:
            fuel_kg: Fuel load in kg

        Returns:
            Time multiplier (higher with more fuel)
        """
        return 1.0 + (fuel_kg * self.FUEL_EFFECT_PER_KG / 100)

    def calculate_tyre_factor(self, tyre_age: int, compound: str) -> float:
        """
        Calculate time factor from tyre condition.

        Args:
            tyre_age: Number of laps on tyres
            compound: Tyre compound (soft, medium, hard)

        Returns:
            Time multiplier (higher as tyres degrade)
        """
        # Degradation rates per compound
        degradation_rates = {
            "soft": 0.08,
            "medium": 0.05,
            "hard": 0.03,
        }
        rate = degradation_rates.get(compound.lower(), 0.05)

        # Tyres get slower with age
        degradation = 1.0 + (tyre_age * rate / 100)
        return degradation

    def calculate_track_evolution(self, session_progress: float) -> float:
        """
        Calculate track evolution factor.

        Track grip improves as rubber is laid down.

        Args:
            session_progress: 0.0 to 1.0 (start to end of session)

        Returns:
            Time multiplier (lower as track improves)
        """
        # Track improves by up to 1.5% over session
        improvement = session_progress * 0.015
        return 1.0 - improvement

    def calculate_traffic_factor(self, traffic_density: float = 0.8) -> float:
        """
        Calculate traffic impact factor.

        In practice, drivers often encounter traffic and must yield.

        Args:
            traffic_density: How busy the track is (0-1)

        Returns:
            Time multiplier (higher with more traffic)
        """
        # Chance of encountering traffic
        if self.rng.random() < traffic_density * 0.3:
            # Lose time yielding or being impeded
            loss = self.rng.uniform(*self.TRAFFIC_LOSS_RANGE)
            return 1.0 + (loss / 100)
        return 1.0

    def simulate_lap(
        self,
        driver: str,
        driver_r: float,
        track_base_time: float,
        run_type: RunType,
        session_progress: float = 0.5,
        tyre_compound: str = "medium",
        tyre_age: int = 5,
        fuel_kg: Optional[float] = None,
        drs_available: bool = True,
        track_temp: float = 35.0,
        air_temp: float = 25.0,
    ) -> PracticeLap:
        """
        Simulate a single practice lap.

        Args:
            driver: Driver name
            driver_r: Driver R rating
            track_base_time: Base lap time for track
            run_type: Type of run
            session_progress: Progress through session (0-1)
            tyre_compound: Tyre compound
            tyre_age: Laps on tyres
            fuel_kg: Fuel load (None for auto based on run type)
            drs_available: Whether DRS is available
            track_temp: Track temperature
            air_temp: Air temperature

        Returns:
            PracticeLap with simulated data
        """
        # Determine fuel load based on run type
        if fuel_kg is None:
            fuel_kg = self._get_fuel_for_run_type(run_type)

        # Calculate factors
        r_factor = self.calculate_driver_r_factor(driver_r)
        fuel_factor = self.calculate_fuel_factor(fuel_kg)
        tyre_factor = self.calculate_tyre_factor(tyre_age, tyre_compound)
        evolution_factor = self.calculate_track_evolution(session_progress)
        traffic_factor = self.calculate_traffic_factor()

        # DRS factor
        drs_used = False
        drs_factor = 1.0
        if drs_available and run_type in [RunType.FLYING_LAP, RunType.QUALI_SIM]:
            drs_used = True
            drs_factor = 1.0 - self.DRS_GAIN / 100

        # Base lap time adjusted by driver skill
        adjusted_base = track_base_time * r_factor

        # Apply all factors
        lap_time = (
            adjusted_base
            * fuel_factor
            * tyre_factor
            * evolution_factor
            * traffic_factor
            * drs_factor
        )

        # Add small random variation (driver inconsistency)
        variation = self.rng.gauss(0, 0.1)  # 0.1s standard deviation
        lap_time += variation

        # Calculate sector times (approximate split)
        sector_times = self._split_into_sectors(lap_time)

        # Determine if traffic was encountered
        traffic_encountered = traffic_factor > 1.0
        traffic_impact = (traffic_factor - 1.0) * 100 if traffic_encountered else 0.0

        # Create lap object
        lap = PracticeLap(
            driver=driver,
            session="",  # To be filled by session manager
            lap_time=lap_time,
            sector_times=sector_times,
            tyre_compound=tyre_compound,
            tyre_age=tyre_age,
            run_type=run_type,
            track_temperature=track_temp,
            air_temperature=air_temp,
            track_condition="dry",  # TODO: Weather integration
            drs_available=drs_available,
            drs_used=drs_used,
            traffic_encountered=traffic_encountered,
            traffic_impact=traffic_impact,
        )

        return lap

    def simulate_flying_lap(
        self, driver: str, driver_r: float, track_base_time: float, **kwargs
    ) -> PracticeLap:
        """Simulate a flying lap (push lap)."""
        # Use provided values or defaults
        tyre_compound = kwargs.pop("tyre_compound", "soft")
        tyre_age = kwargs.pop("tyre_age", 1)
        return self.simulate_lap(
            driver=driver,
            driver_r=driver_r,
            track_base_time=track_base_time,
            run_type=RunType.FLYING_LAP,
            tyre_compound=tyre_compound,
            tyre_age=tyre_age,
            **kwargs,
        )

    def simulate_quali_sim(
        self, driver: str, driver_r: float, track_base_time: float, **kwargs
    ) -> PracticeLap:
        """Simulate a qualifying simulation lap."""
        # Use provided tyre_compound or default to "soft"
        tyre_compound = kwargs.pop("tyre_compound", "soft")
        return self.simulate_lap(
            driver=driver,
            driver_r=driver_r,
            track_base_time=track_base_time,
            run_type=RunType.QUALI_SIM,
            tyre_compound=tyre_compound,
            tyre_age=kwargs.pop("tyre_age", 0),
            fuel_kg=self.QUALI_FUEL_KG,
            **kwargs,
        )

    def simulate_long_run_lap(
        self,
        driver: str,
        driver_r: float,
        track_base_time: float,
        stint_lap: int,
        **kwargs,
    ) -> PracticeLap:
        """
        Simulate a lap during a long run.

        Args:
            stint_lap: Which lap of the stint (0-indexed)
        """
        # Use provided values or calculate defaults
        tyre_compound = kwargs.pop("tyre_compound", "medium")
        tyre_age = kwargs.pop("tyre_age", stint_lap)
        fuel_kg = kwargs.pop("fuel_kg", self.BASE_FUEL_KG - (stint_lap * 2.5))
        return self.simulate_lap(
            driver=driver,
            driver_r=driver_r,
            track_base_time=track_base_time,
            run_type=RunType.LONG_RUN,
            tyre_compound=tyre_compound,
            tyre_age=tyre_age,
            fuel_kg=fuel_kg,
            **kwargs,
        )

    def simulate_out_lap(
        self, driver: str, driver_r: float, track_base_time: float, **kwargs
    ) -> PracticeLap:
        """Simulate an out lap (leaving pits, warming tyres)."""
        # Out laps are slower - cold tyres, careful driving
        # Use provided values or defaults
        tyre_compound = kwargs.pop("tyre_compound", "soft")
        tyre_age = kwargs.pop("tyre_age", 0)
        # Filter out track_condition from kwargs (not used by simulate_lap)
        kwargs.pop("track_condition", None)
        lap = self.simulate_lap(
            driver=driver,
            driver_r=driver_r,
            track_base_time=track_base_time * 1.15,  # 15% slower
            run_type=RunType.OUT_LAP,
            tyre_compound=tyre_compound,
            tyre_age=tyre_age,
            drs_available=False,  # No DRS on out lap
            **kwargs,
        )
        return lap

    def simulate_in_lap(
        self, driver: str, driver_r: float, track_base_time: float, **kwargs
    ) -> PracticeLap:
        """Simulate an in lap (returning to pits)."""
        # In laps are slower - cooling down
        lap = self.simulate_lap(
            driver=driver,
            driver_r=driver_r,
            track_base_time=track_base_time * 1.10,  # 10% slower
            run_type=RunType.IN_LAP,
            drs_available=False,  # No DRS on in lap
            **kwargs,
        )
        return lap

    def simulate_stint(
        self,
        driver: str,
        driver_r: float,
        track_base_time: float,
        num_laps: int,
        session_progress: float = 0.5,
    ) -> List[PracticeLap]:
        """
        Simulate a full stint of consecutive laps.

        Args:
            driver: Driver name
            driver_r: Driver R rating
            track_base_time: Base lap time
            num_laps: Number of laps in stint
            session_progress: Session progress

        Returns:
            List of PracticeLap objects
        """
        laps = []

        # Out lap
        out_lap = self.simulate_out_lap(
            driver, driver_r, track_base_time, session_progress=session_progress
        )
        laps.append(out_lap)

        # Flying laps
        for i in range(num_laps):
            lap = self.simulate_long_run_lap(
                driver, driver_r, track_base_time, i, session_progress=session_progress
            )
            laps.append(lap)

        # In lap
        in_lap = self.simulate_in_lap(
            driver, driver_r, track_base_time, session_progress=session_progress
        )
        laps.append(in_lap)

        return laps

    def _get_fuel_for_run_type(self, run_type: RunType) -> float:
        """Get typical fuel load for run type."""
        fuel_loads = {
            RunType.INSTALLATION: 100.0,
            RunType.OUT_LAP: 80.0,
            RunType.FLYING_LAP: 50.0,
            RunType.IN_LAP: 50.0,
            RunType.LONG_RUN: 100.0,
            RunType.QUALI_SIM: 10.0,
        }
        return fuel_loads.get(run_type, 50.0)

    def _split_into_sectors(self, lap_time: float) -> List[float]:
        """
        Split lap time into three sectors.

        Args:
            lap_time: Total lap time

        Returns:
            List of three sector times
        """
        # Approximate sector splits (can vary by track)
        # Sector 1: ~30%, Sector 2: ~35%, Sector 3: ~35%
        s1 = lap_time * 0.30
        s2 = lap_time * 0.35
        s3 = lap_time * 0.35

        # Add small variations
        s1 *= self.rng.gauss(1.0, 0.02)
        s2 *= self.rng.gauss(1.0, 0.02)
        s3 *= self.rng.gauss(1.0, 0.02)

        return [s1, s2, s3]
