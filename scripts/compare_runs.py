"""Compare runs helper (moved to scripts/)."""

import csv
from pathlib import Path

ANALYSIS = Path("outputs") / "analysis"


def summarize_crosssim(csv_path):
    winners = {}
    with open(csv_path, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            winners[row["intensity"]] = row.get("winner", "")
    return winners


if __name__ == "__main__":
    path = ANALYSIS / "spain_crosssim_summary.csv"
    if not path.exists():
        print("No cross-sim summary found at", path)
    else:
        w = summarize_crosssim(path)
        for k in sorted(w.keys()):
            print(f"{k}: {w[k]}")
import csv
import os

runs = {
    "subtle": r"outputs/race_weekend/Spain_2026-03-29_20-58-24/race/race_results_spain.csv",
    "moderate": r"outputs/race_weekend/Spain_2026-03-29_21-02-31/race/race_results_spain.csv",
    "strong": r"outputs/race_weekend/Spain_2026-03-29_21-03-22/race/race_results_spain.csv",
    "ultra": r"outputs/race_weekend/Spain_2026-03-29_21-04-07/race/race_results_spain.csv",
}

results = {}
for intensity, path in runs.items():
    if not os.path.exists(path):
        results[intensity] = {"error": f"missing {path}"}
        continue
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        winner = None
        ferrari = []
        for row in reader:
            pos = int(row["position"])
            if pos == 1:
                winner = (row["driver"], row["team"], row["total_time"])
            if row.get("team", "").strip() == "Ferrari":
                ferrari.append(
                    (
                        int(row["position"]),
                        row["driver"],
                        row["total_time"],
                        row["interval"],
                    )
                )
        results[intensity] = {"winner": winner, "ferrari": ferrari}

print(
    "Intensity,Winner (driver - team - total_time),Ferrari results (pos: driver - total_time - interval)"
)
for k in ["subtle", "moderate", "strong", "ultra"]:
    r = results.get(k)
    if "error" in r:
        print(f"{k},ERROR,{r['error']}")
        continue
    w = r["winner"]
    wstr = f"{w[0]} - {w[1]} - {w[2]}"
    ferr = " | ".join(
        [f"{p}: {d} - {t} - interval {iv}" for (p, d, t, iv) in r["ferrari"]]
    )
    if not ferr:
        ferr = "none"
    print(f"{k},{wstr},{ferr}")
