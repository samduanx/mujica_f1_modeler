"""
Diagnose lapping issue (moved into scripts/)
"""

import pandas as pd
import numpy as np

lap_times = pd.read_csv(
    "outputs/enhanced_sim/Monaco_2026-03-27_16-25-40/lap_times_monaco.csv"
)
race_results = pd.read_csv(
    "outputs/enhanced_sim/Monaco_2026-03-27_16-25-40/race_results_monaco.csv"
)

print("=" * 80)
print("1. 比赛结果分析")
print("=" * 80)
print(
    race_results[
        [
            "position",
            "driver",
            "team",
            "total_time",
            "laps_down",
            "pit_laps",
            "num_pits",
        ]
    ].to_string()
)

print("\n" + "=" * 80)
print("2. 关键车手圈速对比")
print("=" * 80)


def calc_avg_race_pace(lap_times_row):
    laps = []
    for col in lap_times_row.index:
        if col.startswith("lap_"):
            val = lap_times_row[col]
            if pd.notna(val) and val < 110:
                laps.append(val)
    return np.mean(laps) if laps else 0


lap_times["avg_pace"] = lap_times.apply(calc_avg_race_pace, axis=1)
lap_times["fastest_lap"] = pd.to_numeric(lap_times["fastest_lap"], errors="coerce")

print("\n车手平均圈速（排除进站）:")
pace_df = lap_times[["driver", "fastest_lap", "avg_pace"]].sort_values("avg_pace")
print(pace_df.to_string(index=False))

print("\n" + "=" * 80)
print("3. 进站圈时间分析 (找出哪些圈是进站)")
print("=" * 80)

for driver in ["Verstappen", "Russell", "Hamilton", "Leclerc"]:
    row = lap_times[lap_times["driver"] == driver]
    if row.empty:
        continue
    row = row.iloc[0]
    print(f"\n{driver}:")
    pit_laps = []
    for col in row.index:
        if col.startswith("lap_"):
            lap_num = int(col.split("_")[1])
            val = row[col]
            if pd.notna(val) and val > 120:
                pit_laps.append((lap_num, val))
    if pit_laps:
        for lap_num, val in sorted(pit_laps):
            print(f"  Lap {lap_num}: {val:.3f}s (PIT STOP)")

print("\n" + "=" * 80)
print("4. 累计时间差异分析")
print("=" * 80)


def calc_cumulative_times(lap_times_row, max_lap=50):
    cum_times = []
    cum_time = 0
    for lap_num in range(1, max_lap + 1):
        col = f"lap_{lap_num}"
        if col in lap_times_row.index:
            val = lap_times_row[col]
            if pd.notna(val):
                cum_time += val
                cum_times.append((lap_num, cum_time))
    return cum_times


print("\n前50圈累计时间对比:")
ham_row = lap_times[lap_times["driver"] == "Hamilton"]
ver_row = lap_times[lap_times["driver"] == "Verstappen"]
rus_row = lap_times[lap_times["driver"] == "Russell"]

if not ham_row.empty and not ver_row.empty:
    ham_cum = calc_cumulative_times(ham_row.iloc[0], 50)
    ver_cum = calc_cumulative_times(ver_row.iloc[0], 50)
    rus_cum = calc_cumulative_times(rus_row.iloc[0], 50)

    print(
        f"{'Lap':>5} | {'Hamilton':>12} | {'Verstappen':>12} | {'Russell':>12} | {'Gap H-V':>10} | {'Gap H-R':>10}"
    )
    print("-" * 75)
    for i in range(min(len(ham_cum), len(ver_cum), len(rus_cum))):
        lap = ham_cum[i][0]
        h_time = ham_cum[i][1]
        v_time = ver_cum[i][1]
        r_time = rus_cum[i][1]
        gap_hv = v_time - h_time
        gap_hr = r_time - h_time
        marker = ""
        if gap_hv > 90:
            marker = " <<< LAPPED!"
        print(
            f"{lap:>5} | {h_time:>12.3f} | {v_time:>12.3f} | {r_time:>12.3f} | {gap_hv:>10.3f} | {gap_hr:>10.3f}{marker}"
        )

print("\n" + "=" * 80)
print("5. 问题诊断结论")
print("=" * 80)

ham_time = race_results[race_results["driver"] == "Hamilton"]["total_time"].values[0]
ver_time = race_results[race_results["driver"] == "Verstappen"]["total_time"].values[0]
rus_time = race_results[race_results["driver"] == "Russell"]["total_time"].values[0]

print(f"\nHamilton总时间: {ham_time:.3f}s")
print(f"Verstappen总时间: {ver_time:.3f}s (差距: {ver_time - ham_time:.3f}s)")
print(f"Russell总时间: {rus_time:.3f}s (差距: {rus_time - ham_time:.3f}s)")

avg_lap = 88
print(f"\n平均圈速约: {avg_lap}s")
print(f"Verstappen被套圈数: {(ver_time - ham_time) / avg_lap:.1f} laps")
print(f"Russell被套圈数: {(rus_time - ham_time) / avg_lap:.1f} laps")

print("\n" + "=" * 80)
