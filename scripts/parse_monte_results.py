import csv
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(ROOT, "outputs", "reports")
# find latest monte_carlo_weekend folder
folders = [d for d in os.listdir(csv_path) if d.startswith("monte_carlo_weekend_")]
folders.sort()
if not folders:
    print("No monte_carlo_weekend_* reports found")
    raise SystemExit(1)
latest = folders[-1]
detail = os.path.join(csv_path, latest, "detailed_runs.csv")
if not os.path.exists(detail):
    print("Detailed CSV not found:", detail)
    raise SystemExit(1)

experiments = defaultdict(
    lambda: {"winner": Counter(), "p2": Counter(), "p3": Counter(), "rows": 0}
)
all_top3 = Counter()
subjects = ["Tsunoda", "Stroll", "Albon", "Zhou"]
subject_counts = Counter()

with open(detail, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        exp = r.get("experiment", "")
        experiments[exp]["rows"] += 1
        for col in ("winner", "p2", "p3"):
            name = (r.get(col) or "").strip()
            if name:
                experiments[exp][col][name] += 1
                all_top3[name] += 1
                if name in subjects:
                    subject_counts[name] += 1

print("Report from:", latest)
print()
for exp, data in experiments.items():
    print(f"Experiment: {exp} (runs={data['rows']})")
    print("  Top winners:")
    for name, c in data["winner"].most_common(5):
        print(f"    {name}: {c}")
    print("  Top p2:")
    for name, c in data["p2"].most_common(5):
        print(f"    {name}: {c}")
    print("  Top p3:")
    for name, c in data["p3"].most_common(5):
        print(f"    {name}: {c}")
    print()

print("Aggregate top-3 counts (all experiments):")
for name, c in all_top3.most_common(10):
    print(f"  {name}: {c}")

print(
    "\nCounts for subjects (Tsunoda/Stroll/Albon/Zhou) in top-3 across all experiments:"
)
for s in subjects:
    print(f"  {s}: {subject_counts.get(s, 0)}")
