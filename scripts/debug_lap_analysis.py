#!/usr/bin/env python
"""
Lap Count Analysis Script (moved to scripts/)
"""

import csv
import os

# Race results from Austria 2026
RACE_RESULTS_PATH = (
    "outputs/race_weekend/Austria_2026-03-26_23-59-17/race/race_results_austria.csv"
)
LAP_TIMES_PATH = (
    "outputs/race_weekend/Austria_2026-03-26_23-59-17/race/lap_times_austria.csv"
)

# Driver ratings from CSV
DRIVER_RATINGS = {
    "Leclerc": 100.4,
    "Vettel": 100.3,
    "Albon": 100.1,
    "Perez": 99.8,
    "Hamilton": 100.4,
    "Gasly": 100.1,
    "Ocon": 99.7,
    "Stroll": 99.6,
    "Russell": 99.9,
    "Verstappen": 100.5,
    "Schumacher": 99.5,
    "Bottas": 100.2,
    "Tsunoda": 99.75,
    "Sainz": 99.8,
    "Alonso": 100.5,
    "Ricciardo": 99.6,
    "Zhou": 99.5,
    "Norris": 100.1,
    "Magnussen": 100.1,
    "Latifi": 99.5,
}

# Race configuration
NUM_LAPS = 71  # Total race laps
AUSTRIA_BASE_LAP_TIME = 68.0  # seconds


def read_csv(filepath):
    """Read CSV file and return rows."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def calculate_theoretical_lap_time(dr_value, base_lap_time=68.0):
    r_value = dr_value * 3.0
    adjustment = (r_value - 300.0) * 0.01
    lap_time = base_lap_time - adjustment
    return lap_time


def analyze_race():
    print("=" * 70)
    print("LAP COUNT ANALYSIS - Austria 2026")
    print("=" * 70)

    race_results = read_csv(RACE_RESULTS_PATH)
    lap_times = read_csv(LAP_TIMES_PATH)

    driver_lap_times = {}
    for row in lap_times:
        driver = row["driver"]
        times = []
        for lap in range(1, NUM_LAPS + 1):
            lap_key = f"lap_{lap}"
            if lap_key in row and row[lap_key]:
                try:
                    times.append(float(row[lap_key]))
                except (ValueError, KeyError):
                    pass
        driver_lap_times[driver] = times

    print("\n--- Driver Performance Analysis ---")
    print(
        f"{'Driver':<15} {'Rating':<8} {'Fastest':<8} {'Avg':<8} {'Slowest':<8} {'Total Time':<12} {'Laps':<6}"
    )
    print("-" * 70)

    driver_stats = []

    for result in race_results:
        driver = result["driver"]
        position = result["position"]
        total_time = float(result["total_time"])
        laps_completed = int(result["laps_completed"])

        dr_value = DRIVER_RATINGS.get(driver, 100.0)

        times = driver_lap_times.get(driver, [])

        if times:
            fastest = min(times)
            avg = sum(times) / len(times)
            slowest = max(times)
        else:
            fastest = avg = slowest = 0.0

        driver_stats.append(
            {
                "driver": driver,
                "position": position,
                "dr_value": dr_value,
                "fastest_lap": fastest,
                "avg_lap": avg,
                "slowest_lap": slowest,
                "total_time": total_time,
                "laps_completed": laps_completed,
            }
        )

        print(
            f"{driver:<15} {dr_value:<8.2f} {fastest:<8.2f} {avg:<8.2f} {slowest:<8.2f} {total_time:<12.2f} {laps_completed:<6}"
        )

    print("\n--- Theoretical Lap Count Analysis ---")

    fastest_avg = min(driver_stats, key=lambda x: x["avg_lap"])
    slowest_avg = max(driver_stats, key=lambda x: x["avg_lap"])

    print(
        f"\nFastest driver: {fastest_avg['driver']} (avg: {fastest_avg['avg_lap']:.2f}s)"
    )
    print(
        f"Slowest driver: {slowest_avg['driver']} (avg: {slowest_avg['avg_lap']:.2f}s)"
    )

    lap_time_diff_per_lap = slowest_avg["avg_lap"] - fastest_avg["avg_lap"]
    print(f"\nLap time difference per lap: {lap_time_diff_per_lap:.2f}s")

    leader_time = fastest_avg["total_time"]
    slow_time = slowest_avg["total_time"]
    time_gap = slow_time - leader_time

    if lap_time_diff_per_lap > 0:
        theoretical_laps_behind = time_gap / fastest_avg["avg_lap"]
    else:
        theoretical_laps_behind = 0

    print(f"Total time gap: {time_gap:.2f}s")
    print(
        f"Theoretical laps behind (based on avg lap time): {theoretical_laps_behind:.2f}"
    )

    print("\n--- Actual Lap Count Check ---")

    laps_completed_set = set(int(r["laps_completed"]) for r in race_results)

    if len(laps_completed_set) == 1:
        print(
            "WARNING: All drivers completed {} laps!".format(
                list(laps_completed_set)[0]
            )
        )
        print("    This indicates no lap deficits were calculated.")
    else:
        print("OK: Lap counts vary: {}".format(laps_completed_set))

    print("\n--- Lap Deficit Calculation Analysis ---")
    print(
        f"Formula: laps_down = int(time_gap / avg_lap_time) if time_gap > avg_lap_time * 0.5 else 0"
    )
    print(f"Using leader's average lap time: {leader_time / NUM_LAPS:.2f}s")

    leader = driver_stats[0]

    for stat in driver_stats:
        driver = stat["driver"]
        position = stat["position"]
        dr_value = stat["dr_value"]
        total_time = stat["total_time"]

        time_gap = total_time - leader["total_time"]
        avg_lap_time = total_time / NUM_LAPS

        threshold = avg_lap_time * 0.5
        if time_gap > threshold:
            theoretical_deficit = int(time_gap / avg_lap_time)
        else:
            theoretical_deficit = 0

        theoretical_deficit = min(theoretical_deficit, NUM_LAPS - 1)

        actual_deficit = NUM_LAPS - stat["laps_completed"]

        if actual_deficit > 0:
            status = f"BEHIND {actual_deficit} lap(s)"
        else:
            status = "ON LEAD LAP"

        print(
            f"  P{position}: {driver:<15} DR={dr_value:.2f} time_gap={time_gap:>8.2f}s theoretical_deficit={theoretical_deficit:>2} actual={actual_deficit:>2} -> {status}"
        )

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)

    all_same_laps = all(int(r["laps_completed"]) == NUM_LAPS for r in race_results)

    if all_same_laps:
        print("BUG CONFIRMED: All drivers completed the same number of laps (71)")
        print("   Despite significant rating differences, no lap deficits are present.")
        print(
            "   Expected behavior: Slower drivers should be lapped by faster drivers."
        )
        print("   Actual behavior: Everyone completes same laps, only time gap varies.")
    else:
        print("OK: Lap deficits are being calculated correctly.")
        laps_variation = sorted(set(int(r["laps_completed"]) for r in race_results))
        print("   Lap variation: {}".format(laps_variation))


if __name__ == "__main__":
    analyze_race()
#!/usr/bin/env python
"""
Lap Count Analysis Script
Moved into scripts/ for project cleanliness.
"""

import csv
import os

# Race results from Austria 2026
RACE_RESULTS_PATH = (
    "outputs/race_weekend/Austria_2026-03-26_23-59-17/race/race_results_austria.csv"
)
LAP_TIMES_PATH = (
    "outputs/race_weekend/Austria_2026-03-26_23-59-17/race/lap_times_austria.csv"
)

DRIVER_RATINGS = {
    "Leclerc": 100.4,
    "Vettel": 100.3,
    "Albon": 100.1,
    "Perez": 99.8,
    "Hamilton": 100.4,
    "Gasly": 100.1,
    "Ocon": 99.7,
    "Stroll": 99.6,
    "Russell": 99.9,
    "Verstappen": 100.5,
    "Schumacher": 99.5,
    "Bottas": 100.2,
    "Tsunoda": 99.75,
    "Sainz": 99.8,
    "Alonso": 100.5,
    "Ricciardo": 99.6,
    "Zhou": 99.5,
    "Norris": 100.1,
    "Magnussen": 100.1,
    "Latifi": 99.5,
}

NUM_LAPS = 71
AUSTRIA_BASE_LAP_TIME = 68.0


def read_csv(filepath):
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def calculate_theoretical_lap_time(dr_value, base_lap_time=68.0):
    r_value = dr_value * 3.0
    adjustment = (r_value - 300.0) * 0.01
    lap_time = base_lap_time - adjustment
    return lap_time


def analyze_race():
    print("=" * 70)
    print("LAP COUNT ANALYSIS - Austria 2026")
    print("=" * 70)

    race_results = read_csv(RACE_RESULTS_PATH)
    lap_times = read_csv(LAP_TIMES_PATH)

    driver_lap_times = {}
    for row in lap_times:
        driver = row["driver"]
        times = []
        for lap in range(1, NUM_LAPS + 1):
            lap_key = f"lap_{lap}"
            if lap_key in row and row[lap_key]:
                try:
                    times.append(float(row[lap_key]))
                except (ValueError, KeyError):
                    pass
        driver_lap_times[driver] = times

    print("\n--- Driver Performance Analysis ---")
    print(
        f"{'Driver':<15} {'Rating':<8} {'Fastest':<8} {'Avg':<8} {'Slowest':<8} {'Total Time':<12} {'Laps':<6}"
    )
    print("-" * 70)

    driver_stats = []

    for result in race_results:
        driver = result["driver"]
        position = result["position"]
        total_time = float(result["total_time"])
        laps_completed = int(result["laps_completed"])

        dr_value = DRIVER_RATINGS.get(driver, 100.0)
        times = driver_lap_times.get(driver, [])

        if times:
            fastest = min(times)
            avg = sum(times) / len(times)
            slowest = max(times)
        else:
            fastest = avg = slowest = 0.0

        driver_stats.append(
            {
                "driver": driver,
                "position": position,
                "dr_value": dr_value,
                "fastest_lap": fastest,
                "avg_lap": avg,
                "slowest_lap": slowest,
                "total_time": total_time,
                "laps_completed": laps_completed,
            }
        )

        print(
            f"{driver:<15} {dr_value:<8.2f} {fastest:<8.2f} {avg:<8.2f} {slowest:<8.2f} {total_time:<12.2f} {laps_completed:<6}"
        )

    print("\n--- Theoretical Lap Count Analysis ---")

    fastest_avg = min(driver_stats, key=lambda x: x["avg_lap"])
    slowest_avg = max(driver_stats, key=lambda x: x["avg_lap"])

    print(
        f"\nFastest driver: {fastest_avg['driver']} (avg: {fastest_avg['avg_lap']:.2f}s)"
    )
    print(
        f"Slowest driver: {slowest_avg['driver']} (avg: {slowest_avg['avg_lap']:.2f}s)"
    )

    lap_time_diff_per_lap = slowest_avg["avg_lap"] - fastest_avg["avg_lap"]
    print(f"\nLap time difference per lap: {lap_time_diff_per_lap:.2f}s")

    leader_time = fastest_avg["total_time"]
    slow_time = slowest_avg["total_time"]
    time_gap = slow_time - leader_time

    if lap_time_diff_per_lap > 0:
        theoretical_laps_behind = time_gap / fastest_avg["avg_lap"]
    else:
        theoretical_laps_behind = 0

    print(f"Total time gap: {time_gap:.2f}s")
    print(
        f"Theoretical laps behind (based on avg lap time): {theoretical_laps_behind:.2f}"
    )

    print("\n--- Actual Lap Count Check ---")
    laps_completed_set = set(int(r["laps_completed"]) for r in race_results)
    if len(laps_completed_set) == 1:
        print(
            "WARNING: All drivers completed {} laps!".format(
                list(laps_completed_set)[0]
            )
        )
        print("    This indicates no lap deficits were calculated.")
    else:
        print("OK: Lap counts vary: {}".format(laps_completed_set))

    print("\n--- Lap Deficit Calculation Analysis ---")
    print(
        f"Formula: laps_down = int(time_gap / avg_lap_time) if time_gap > avg_lap_time * 0.5 else 0"
    )
    print(f"Using leader's average lap time: {leader_time / NUM_LAPS:.2f}s")

    leader = driver_stats[0]

    for stat in driver_stats:
        driver = stat["driver"]
        position = stat["position"]
        dr_value = stat["dr_value"]
        total_time = stat["total_time"]

        time_gap = total_time - leader["total_time"]
        avg_lap_time = total_time / NUM_LAPS

        threshold = avg_lap_time * 0.5
        if time_gap > threshold:
            theoretical_deficit = int(time_gap / avg_lap_time)
        else:
            theoretical_deficit = 0

        theoretical_deficit = min(theoretical_deficit, NUM_LAPS - 1)

        actual_deficit = NUM_LAPS - stat["laps_completed"]

        if actual_deficit > 0:
            status = f"BEHIND {actual_deficit} lap(s)"
        else:
            status = "ON LEAD LAP"

        print(
            f"  P{position}: {driver:<15} DR={dr_value:.2f} time_gap={time_gap:>8.2f}s theoretical_deficit={theoretical_deficit:>2} actual={actual_deficit:>2} -> {status}"
        )

    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)

    all_same_laps = all(int(r["laps_completed"]) == NUM_LAPS for r in race_results)

    if all_same_laps:
        print("BUG CONFIRMED: All drivers completed the same number of laps (71)")
    else:
        print("OK: Lap deficits are being calculated correctly.")


if __name__ == "__main__":
    analyze_race()
