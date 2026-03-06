"""
DRS Simulation Engine.

Main simulation class for time-stepped DRS simulation.
Uses 0.2-second intervals to track position and DRS activation.
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from drs.base_config import (
    TrackDRSConfig,
    SectorConfig,
    DRSSettings,
    DRSZone,
    TrackDifficulty,
)
from drs.driver_state import (
    DriverRaceState,
    DriverTestData,
    create_test_driver_states,
)


@dataclass
class SimulationConfig:
    """Configuration for DRS simulation run"""

    time_resolution: float = 0.2  # 200ms intervals
    random_seed: Optional[int] = None
    enable_drs: bool = True
    enable_tyre_degradation: bool = True
    verbose: bool = True
    record_interval_data: bool = True

    def __post_init__(self):
        """Validate configuration"""
        if self.time_resolution <= 0:
            raise ValueError("time_resolution must be positive")


class TimeSteppedDRSSimulator:
    """
    Main DRS simulation engine using time-stepped intervals.

    This simulator divides each sector into small time intervals
    and tracks car positions to accurately model DRS effects.

    Attributes:
        config: Track DRS configuration
        drivers: Dictionary of driver states
        simulation_config: Simulation run configuration
    """

    TIME_RESOLUTION = 0.2  # 200ms intervals

    def __init__(
        self,
        config: TrackDRSConfig,
        drivers: Dict[str, DriverRaceState],
        simulation_config: Optional[SimulationConfig] = None,
    ):
        """
        Initialize the DRS simulator.

        Args:
            config: Track DRS configuration
            drivers: Dictionary of driver states keyed by name
            simulation_config: Optional simulation configuration
        """
        self.track_config = config
        self.drivers = drivers
        self.simulation_config = simulation_config or SimulationConfig()

        # Set random seed if specified
        if self.simulation_config.random_seed is not None:
            random.seed(self.simulation_config.random_seed)

        # Calculate intervals per sector
        self.intervals_per_sector = {}
        for sector_num, sector in config.sectors.items():
            intervals = int(sector.base_time / self.TIME_RESOLUTION)
            self.intervals_per_sector[sector_num] = max(1, intervals)

        # Calculate total intervals per lap
        self.total_intervals_per_lap = sum(self.intervals_per_sector.values())

    def can_activate_drs(
        self,
        driver: DriverRaceState,
        target: Optional[DriverRaceState],
        current_lap: int,
    ) -> Tuple[bool, str]:
        """
        Check if DRS can be activated for a driver.

        Rules:
        1. DRS must be enabled (not first lap(s))
        2. Must be within 1 second of car ahead at detection point

        Args:
            driver: Driver attempting to use DRS
            target: Car ahead (for gap calculation)
            current_lap: Current lap number

        Returns:
            Tuple of (can_activate, reason)
        """
        settings = self.track_config.drs_settings

        # Rule 1: Check if DRS is enabled
        if current_lap < settings.enabled_after_lap:
            return False, f"DRS disabled before lap {settings.enabled_after_lap}"

        # Rule 2: Check if first lap of race
        if settings.drs_disabled_first_lap and current_lap == 1:
            return False, "DRS disabled on first lap"

        # Rule 3: Check gap to car ahead
        if target is None:
            return False, "No car ahead"

        if driver.gap_to_ahead > settings.minimum_gap_for_drs:
            return (
                False,
                f"Gap too large ({driver.gap_to_ahead:.2f}s > {settings.minimum_gap_for_drs}s)",
            )

        return True, "Within 1 second at detection point"

    def calculate_drs_gain(self, driver: DriverRaceState, zone: DRSZone) -> float:
        """
        Calculate time gain from DRS activation.

        Args:
            driver: Driver activating DRS
            zone: DRS zone being used

        Returns:
            Time gain in seconds
        """
        settings = self.track_config.drs_settings

        # Base gain from zone configuration
        gain = zone.base_time_gain

        # Add random variation
        variation = random.uniform(-settings.gain_variation, settings.gain_variation)
        gain += variation

        # Apply activation probability
        if random.random() > zone.activation_probability:
            return 0.0  # DRS not activated

        return max(0.0, gain)

    def get_base_interval_time(
        self, driver: DriverRaceState, sector: SectorConfig
    ) -> float:
        """
        Calculate base interval time for a driver in a sector.

        Args:
            driver: Driver state
            sector: Sector configuration

        Returns:
            Base interval time in seconds
        """
        # Base time from sector configuration
        base_time = sector.base_time

        # Adjust for R-value (higher R = faster)
        # The adjustment should be proportional to sector time, not a fixed amount
        # Normalize: 302 (slowest) -> 0, 310 (fastest) -> 1
        r_min = 302.0
        r_max = 310.0
        r_factor = (driver.r_value - r_min) / (r_max - r_min)

        # Calculate total adjustment per lap (max 2.0s for fastest vs slowest)
        total_lap_adjustment = r_factor * 2.0

        # Distribute adjustment proportionally across sectors based on base time
        track_base_time = self.track_config.calculate_base_lap_time()
        sector_proportion = sector.base_time / track_base_time
        sector_adjustment = total_lap_adjustment * sector_proportion

        base_time -= sector_adjustment

        # Apply tyre degradation if enabled
        if self.simulation_config.enable_tyre_degradation:
            base_time *= driver.tyre_degradation

        # Calculate interval time
        intervals = self.intervals_per_sector.get(sector.sector_number, 1)
        interval_time = base_time / intervals

        return interval_time

    def simulate_interval(
        self,
        driver: DriverRaceState,
        target: Optional[DriverRaceState],
        sector: SectorConfig,
        sector_interval: int,
        current_lap: int,
    ) -> Tuple[float, Dict]:
        """
        Simulate one time interval with DRS effects.

        Args:
            driver: Driver being simulated
            target: Car ahead (for gap and DRS)
            sector: Current sector configuration
            sector_interval: Index of interval within sector
            current_lap: Current lap number

        Returns:
            Tuple of (interval_time, interval_data_dict)
        """
        # Get base interval time
        base_time = self.get_base_interval_time(driver, sector)

        # Calculate position within sector for DRS zone check
        sector_progress = sector_interval / max(
            1, self.intervals_per_sector[sector.sector_number]
        )
        distance_in_sector = sector.length * sector_progress
        total_distance = sector.start_distance + distance_in_sector

        # Check for DRS zone
        drs_gain = 0.0
        in_drs_zone = False
        drs_zone_info = None

        if self.simulation_config.enable_drs:
            zone = self.track_config.get_drs_zone_at_distance(total_distance)

            if zone:
                # Check if DRS can be activated
                can_activate, reason = self.can_activate_drs(
                    driver, target, current_lap
                )

                if can_activate:
                    gain = self.calculate_drs_gain(driver, zone)
                    if gain > 0:
                        drs_gain = gain
                        in_drs_zone = True
                        driver.activate_drs(gain)
                        drs_zone_info = {"zone_id": zone.zone_id, "gain": gain}
                else:
                    # Still in zone but can't activate
                    in_drs_zone = True

        # Calculate actual interval time
        actual_time = base_time - drs_gain

        # Create interval data
        interval_data = {
            "lap": current_lap,
            "sector": sector.sector_number,
            "interval": sector_interval,
            "distance": total_distance,
            "base_interval_time": base_time,
            "actual_interval_time": actual_time,
            "drs_gain": drs_gain,
            "in_drs_zone": in_drs_zone,
            "drs_zone_info": drs_zone_info,
            "cumulative_time": driver.cumulative_time + actual_time,
        }

        return actual_time, interval_data

    def simulate_lap(
        self,
        driver: DriverRaceState,
        ordered_drivers: List[DriverRaceState],
        lap_number: int,
    ) -> float:
        """
        Simulate one complete lap for a driver.

        Args:
            driver: Driver to simulate
            ordered_drivers: List of drivers in position order
            lap_number: Current lap number

        Returns:
            Lap time in seconds
        """
        # Find car ahead for gap calculations
        target = None
        for i, d in enumerate(ordered_drivers):
            if d.name == driver.name and i > 0:
                target = ordered_drivers[i - 1]
                break

        # Store lap start time
        lap_start_time = driver.cumulative_time

        # Simulate each sector
        for sector_num in [1, 2, 3]:
            sector = self.track_config.sectors[sector_num]
            num_intervals = self.intervals_per_sector[sector_num]

            for interval_idx in range(num_intervals):
                interval_time, interval_data = self.simulate_interval(
                    driver=driver,
                    target=target,
                    sector=sector,
                    sector_interval=interval_idx,
                    current_lap=lap_number,
                )

                # Update driver state
                driver.add_interval_time(interval_time, interval_data)

                # Advance tyre
                if interval_idx == num_intervals - 1:
                    driver.advance_tyre()

        # Calculate lap time
        lap_time = driver.cumulative_time - lap_start_time
        driver.lap_times.append(lap_time)

        return lap_time

    def simulate_race(self, num_laps: int, verbose: Optional[bool] = None) -> Dict:
        """
        Simulate a complete race.

        Args:
            num_laps: Number of laps to simulate
            verbose: Override for verbose output

        Returns:
            Dictionary with race results
        """
        if verbose is None:
            verbose = self.simulation_config.verbose

        if verbose:
            print(f"\n{'=' * 60}")
            print(
                f"Starting {self.track_config.track_name} {self.track_config.year} DRS Simulation"
            )
            print(f"Track: {self.track_config.total_distance}m | Laps: {num_laps}")
            print(f"Drivers: {len(self.drivers)} | Resolution: {self.TIME_RESOLUTION}s")
            print(f"{'=' * 60}\n")

        # Initialize positions
        for i, (name, driver) in enumerate(self.drivers.items()):
            driver.position = driver.grid_position
            driver.gap_to_ahead = float("inf")
            if verbose:
                print(f"{name}: Grid P{driver.grid_position}")

        # Calculate expected lap times for each driver (for position ordering)
        # Use R-value to determine base pace
        r_values = [d.r_value for d in self.drivers.values()]
        r_min, r_max = min(r_values), max(r_values)

        # Use the track's actual base lap time instead of hardcoded value
        track_base_time = self.track_config.calculate_base_lap_time()

        def get_expected_lap_time(driver: DriverRaceState) -> float:
            """Estimate lap time based on R-value"""
            r_factor = (driver.r_value - r_min) / (r_max - r_min)
            base_time = track_base_time  # Use actual track base time
            adjustment = r_factor * 0.5
            return base_time - adjustment

        # Track expected finishing times for position ordering
        expected_finish_times = {name: 0.0 for name in self.drivers.keys()}

        # Simulate each lap
        for lap in range(1, num_laps + 1):
            if verbose:
                print(f"\n--- Lap {lap}/{num_laps} ---")

            # Update expected positions based on pace
            # Sort by expected finish time (cumulative expected time)
            for name in expected_finish_times.keys():
                expected_finish_times[name] += get_expected_lap_time(self.drivers[name])

            # Order drivers by expected finishing time
            sorted_names = sorted(
                expected_finish_times.keys(), key=lambda n: expected_finish_times[n]
            )
            current_order = [self.drivers[n] for n in sorted_names]

            # Calculate gaps based on expected times
            for i, driver in enumerate(current_order):
                if i == 0:
                    driver.gap_to_ahead = float("inf")
                else:
                    driver.gap_to_ahead = (
                        expected_finish_times[driver.name]
                        - expected_finish_times[current_order[i - 1].name]
                    )

            # Simulate each driver in position order
            for driver in current_order:
                # Find car ahead for DRS
                target = None
                for i, d in enumerate(current_order):
                    if d.name == driver.name and i > 0:
                        target = current_order[i - 1]
                        break

                lap_time = self.simulate_lap(driver, current_order, lap)

                if verbose:
                    drs_status = "DRS" if driver.drs_available else ""
                    gap_display = (
                        f"{driver.gap_to_ahead:.3f}s"
                        if driver.gap_to_ahead != float("inf")
                        else "--"
                    )
                    print(
                        f"  {driver.name}: {lap_time:.3f}s "
                        f"(Gap: {gap_display}) {drs_status}"
                    )

        # Update final positions based on cumulative times
        sorted_drivers = sorted(self.drivers.values(), key=lambda d: d.cumulative_time)

        for i, driver in enumerate(sorted_drivers):
            driver.position = i + 1
            if i == 0:
                driver.gap_to_ahead = float("inf")
            else:
                driver.gap_to_ahead = (
                    driver.cumulative_time - sorted_drivers[i - 1].cumulative_time
                )

        # Final results
        results = self.get_results()

        if verbose:
            self.print_results(results)

        return results

    def get_results(self) -> Dict:
        """Compile race results"""
        # Sort by final position
        sorted_drivers = sorted(self.drivers.values(), key=lambda d: d.cumulative_time)

        results = {
            "track": self.track_config.track_name,
            "year": self.track_config.year,
            "total_laps": len(list(self.drivers.values())[0].lap_times)
            if self.drivers
            else 0,
            "positions": [],
            "drs_statistics": {},
            "lap_times": {},
            "average_lap_times": {},
        }

        for position, driver in enumerate(sorted_drivers, 1):
            driver.position = position

            results["positions"].append(
                {
                    "position": position,
                    "driver": driver.name,
                    "total_time": driver.cumulative_time,
                    "grid_position": driver.grid_position,
                    "gap_to_winner": driver.cumulative_time
                    - sorted_drivers[0].cumulative_time,
                }
            )

            results["lap_times"][driver.name] = driver.lap_times
            results["average_lap_times"][driver.name] = driver.get_average_lap_time()
            results["drs_statistics"][driver.name] = driver.get_drs_stats()

        return results

    def print_results(self, results: Dict):
        """Print race results"""
        print(f"\n{'=' * 60}")
        print(f"Final Results - {results['track']} {results['year']}")
        print(f"{'=' * 60}")

        for result in results["positions"]:
            driver = result["driver"]
            stats = results["drs_statistics"][driver]

            print(
                f"P{result['position']:2d}: {driver:<15} "
                f"{result['total_time'] / 60:.1f}min "
                f"(Gap: +{result['gap_to_winner']:.3f}s)"
            )
            print(
                f"      DRS: {stats['activations']} activations, "
                f"{stats['total_gain']:.3f}s total gain"
            )

        print(f"\n{'=' * 60}")


def run_drs_simulation(
    track_config: TrackDRSConfig,
    driver_data: List[DriverTestData],
    num_laps: int,
    random_seed: Optional[int] = None,
    verbose: bool = True,
) -> Dict:
    """
    Convenience function to run a DRS simulation.

    Args:
        track_config: Track DRS configuration
        driver_data: List of driver test data
        num_laps: Number of laps
        random_seed: Optional random seed for reproducibility
        verbose: Enable verbose output

    Returns:
        Race results dictionary
    """
    # Create driver states
    driver_states = create_test_driver_states(driver_data)

    # Create simulation configuration
    sim_config = SimulationConfig(random_seed=random_seed, verbose=verbose)

    # Create and run simulator
    simulator = TimeSteppedDRSSimulator(
        config=track_config, drivers=driver_states, simulation_config=sim_config
    )

    return simulator.simulate_race(num_laps)


# Example usage
if __name__ == "__main__":
    # Import configurations from new JSON-based zones module
    from drs.zones import get_monaco_config as get_config

    # Get Monaco configuration
    config = get_config()
    # Validation targets are now embedded in the JSON config
    targets = config.get("validation_targets", {})

    # Get test drivers
    from driver_state import TEST_DRIVERS

    # Run simulation
    results = run_drs_simulation(
        track_config=config,
        driver_data=TEST_DRIVERS,
        num_laps=5,  # Short test run
        random_seed=42,
        verbose=True,
    )

    print(f"\nValidation targets for Monaco:")
    print(
        f"  Avg lap time: {targets['avg_lap_time_target']}s ±{targets['lap_time_tolerance']}s"
    )
    print(f"  Expected DRS gain: {targets['drs_gain_target']}s")
    print(f"  Expected overtakes: {targets['expected_overtakes']}")
