# DRS Simulator Package

"""
DRS (Drag Reduction System) Simulator

This package provides a sector-based race simulation with DRS support.

Modules:
- base_config: Abstract base classes for track configurations
- driver_state: Driver state tracking during simulation
- simulator: Main DRS simulation engine
- zones: Track-specific DRS zone configurations

Usage:
    from drs import TimeSteppedDRSSimulator
    from drs.zones import get_monaco_config, get_monza_config

    config = get_monaco_config()
    simulator = TimeSteppedDRSSimulator(config, driver_data)
    results = simulator.simulate_race(num_laps=78)

    # Or use the generic get_track_config for any track:
    from drs.zones import get_track_config
    config = get_track_config("Monaco")
"""

__version__ = "1.0.0"
__author__ = "Mujica F1 Modeler"
