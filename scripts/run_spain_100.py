import os
import sys
import time
import csv
from datetime import datetime

# ensure project root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from main import run_race_weekend

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base_output_dir = os.path.join(
    "outputs", "reports", f"spain_monte_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
)
os.makedirs(base_output_dir, exist_ok=True)

seeds = list(range(2001, 2101))
rows = []
for i, seed in enumerate(seeds, start=1):
    start = time.time()
    print(f"Run {i}/{len(seeds)} seed={seed}")
    try:
        results = run_race_weekend(
            track_name="Spain",
            sessions=["fp1", "fp2", "fp3", "qualifying", "race"],
            seed=seed,
        )
        race_result = results.get("race", {}) if isinstance(results, dict) else {}
        status = race_result.get("status", "unknown")
        output_dir = results.get("_output_dir", "") if isinstance(results, dict) else ""
        winner = race_result.get("winner", "")
        p2 = race_result.get("p2", "")
        p3 = race_result.get("p3", "")
        rows.append(
            {
                "seed": seed,
                "status": status,
                "winner": winner,
                "p2": p2,
                "p3": p3,
                "output_dir": output_dir,
            }
        )
    except Exception as e:
        rows.append(
            {
                "seed": seed,
                "status": "error",
                "winner": "",
                "p2": "",
                "p3": "",
                "output_dir": "",
            }
        )
    elapsed = round(time.time() - start, 2)
    print(f"  done t={elapsed}s")

# write detailed csv
out_csv = os.path.join(base_output_dir, "detailed_runs_spain_100.csv")
with open(out_csv, "w", encoding="utf-8", newline="") as f:
    if rows:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

print("Wrote", out_csv)
