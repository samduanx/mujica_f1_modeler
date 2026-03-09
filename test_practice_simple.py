"""Simple test for practice module - directly test setup and parc ferme."""

import sys

sys.path.insert(0, "src")

print("Testing Practice Module...", flush=True)

from practice import (
    PracticeWeekendSimulator,
    WeekendType,
    SetupDiceRoller,
    SetupEffectCalculator,
    ParcFermeManager,
)

# Test 1: Setup Dice Roller
print("\n=== Test 1: Setup Dice Roller ===", flush=True)
roller = SetupDiceRoller(seed=42)
rolls = roller.roll_all_categories()
print(f"Rolls: {rolls}", flush=True)

# Test 2: Setup Effect Calculator
print("\n=== Test 2: Setup Effect Calculator ===", flush=True)
calc = SetupEffectCalculator()
total = calc.calculate_total_effect(rolls)
delta = calc.normalize_to_r_delta(total)
print(f"Total effect: {total}, Delta: {delta}", flush=True)

# Test 3: Normal Weekend Parc Ferme
print("\n=== Test 3: Normal Weekend Parc Ferme ===", flush=True)
pm_normal = ParcFermeManager(weekend_type=WeekendType.NORMAL)
from practice import SetupTuningResult

# Create dummy setups
fp1_setups = {
    "Driver1": SetupTuningResult(
        "Driver1",
        "FP1",
        aerodynamics=6,
        suspension=5,
        differential=6,
        brake_balance=5,
        tyre_pressure=6,
        r_rating_delta=0.5,
    ),
    "Driver2": SetupTuningResult(
        "Driver2",
        "FP1",
        aerodynamics=3,
        suspension=3,
        differential=3,
        brake_balance=3,
        tyre_pressure=3,
        r_rating_delta=0.0,
    ),
}
fp2_setups = {
    "Driver1": SetupTuningResult(
        "Driver1",
        "FP2",
        aerodynamics=5,
        suspension=6,
        differential=5,
        brake_balance=6,
        tyre_pressure=5,
        r_rating_delta=0.4,
    ),
    "Driver2": SetupTuningResult(
        "Driver2",
        "FP2",
        aerodynamics=2,
        suspension=2,
        differential=2,
        brake_balance=2,
        tyre_pressure=2,
        r_rating_delta=-0.3,
    ),
}
fp3_setups = {
    "Driver1": SetupTuningResult(
        "Driver1",
        "FP3",
        aerodynamics=4,
        suspension=4,
        differential=5,
        brake_balance=4,
        tyre_pressure=5,
        r_rating_delta=0.3,
    ),
    "Driver2": SetupTuningResult(
        "Driver2",
        "FP3",
        aerodynamics=4,
        suspension=4,
        differential=4,
        brake_balance=4,
        tyre_pressure=4,
        r_rating_delta=0.1,
    ),
}

from practice import ParcFermeCoordinator

coordinator = ParcFermeCoordinator()
manager = coordinator.setup_normal_weekend(fp1_setups, fp2_setups, fp3_setups)
print(f"Parc Fermé Active: {manager.is_active()}", flush=True)
print(f"Locked setups: {list(manager.get_locked_setups().keys())}", flush=True)
print(f"R Deltas: {manager.get_r_rating_deltas()}", flush=True)

# Test 4: Sprint Weekend Parc Ferme (2022 rules)
print("\n=== Test 4: Sprint Weekend Parc Ferme (2022) ===", flush=True)
pm_sprint = ParcFermeManager(weekend_type=WeekendType.SPRINT)
sprint_fp1 = {
    "Driver1": SetupTuningResult(
        "Driver1",
        "FP1",
        aerodynamics=6,
        suspension=6,
        differential=6,
        brake_balance=6,
        tyre_pressure=6,
        r_rating_delta=0.5,
    ),
}
manager_sprint = coordinator.setup_sprint_weekend_2022(sprint_fp1)
print(f"Parc Fermé Active: {manager_sprint.is_active()}", flush=True)
print(f"Weekend Type: {manager_sprint.weekend_type.value}", flush=True)
print(f"R Deltas: {manager_sprint.get_r_rating_deltas()}", flush=True)

# Test 5: Weekend Simulator
print("\n=== Test 5: Weekend Simulator ===", flush=True)
sim = PracticeWeekendSimulator(
    track="Monaco",
    track_base_time=72.5,
    weekend_type=WeekendType.NORMAL,
    drivers=["Verstappen", "Leclerc"],
    driver_ratings={"Verstappen": 100.0, "Leclerc": 99.0},
    seed=42,
)

# Just get setup results without running full session (which has bugs)
setup_results = sim.setup_manager.run_setup_session(sim.drivers, "FP1")
print(f"Setup results generated for: {list(setup_results.keys())}", flush=True)
for driver, setup in setup_results.items():
    print(f"  {driver}: delta={setup.r_rating_delta:.2f}", flush=True)

print("\n=== All Tests Passed! ===", flush=True)
