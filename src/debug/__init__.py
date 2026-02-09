"""
Debug module for F1 Race Simulation.

This module provides debugging and testing tools for the F1 simulation system:
- Multi-run simulations with statistical analysis
- FastF1 data comparison
- Outlier detection and anomaly reporting
- Parameter sensitivity analysis
- Track-by-track calibration

Usage:
    from debug.multi_run_debug import run_multi_run_debug
    
    # Run debug simulations
    results = run_multi_run_debug(
        tracks=["Spain", "Bahrain", "Monaco"],
        num_runs=10,
        compare_fastf1=True
    )
"""

from .multi_run_debug import (
    run_multi_run_debug,
    MultiRunSimulator,
    SimulationComparator,
    DebugReportGenerator,
    DebugVisualizer,
    FastF1DataFetcher,
    TRACK_CONFIG,
    ALL_TRACKS,
)

__all__ = [
    "run_multi_run_debug",
    "MultiRunSimulator",
    "SimulationComparator",
    "DebugReportGenerator",
    "DebugVisualizer",
    "FastF1DataFetcher",
    "TRACK_CONFIG",
    "ALL_TRACKS",
]
