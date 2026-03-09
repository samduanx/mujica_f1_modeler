"""Test script for practice module."""

import sys
import os

sys.path.insert(0, "src")

print("Starting test...", flush=True)

try:
    from practice import PracticeWeekendSimulator, WeekendType

    print("Import successful!", flush=True)

    drivers = ["Verstappen", "Leclerc", "Hamilton"]
    ratings = {d: 100.0 for d in drivers}

    # Test normal weekend
    print("Testing normal weekend...", flush=True)
    sim = PracticeWeekendSimulator(
        track="Spain",
        track_base_time=78.5,
        weekend_type=WeekendType.NORMAL,
        drivers=drivers,
        driver_ratings=ratings,
        seed=42,
    )
    results = sim.run_all_sessions()
    print(
        f"Normal weekend: Parc Fermé Active = {results.parc_ferme_state.is_active}",
        flush=True,
    )

    # Test sprint weekend
    print("Testing sprint weekend...", flush=True)
    sim2 = PracticeWeekendSimulator(
        track="Imola",
        track_base_time=82.0,
        weekend_type=WeekendType.SPRINT,
        drivers=drivers,
        driver_ratings=ratings,
        seed=42,
    )
    results2 = sim2.run_all_sessions()
    print(
        f"Sprint weekend: Parc Fermé Active = {results2.parc_ferme_state.is_active}",
        flush=True,
    )

    # Get R deltas
    print("Getting R rating deltas...", flush=True)
    deltas = sim.get_r_rating_deltas()
    print(f"R deltas: {deltas}", flush=True)

    print("All tests passed!", flush=True)

except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback

    traceback.print_exc()
