"""
Analyze podium anomalies from detailed_runs.csv: flag runs where any podium driver
is not from Mercedes, Ferrari, or Red Bull, and attempt an automated cause analysis.
"""

import csv
import json
import os
import sys
from collections import Counter
from typing import List, Dict

DETAILED_CSV = (
    "outputs/reports/monte_carlo_weekend_2026-03-27_21-25-57/detailed_runs.csv"
)
TOP_TEAMS = {"Mercedes", "Ferrari", "Red Bull"}
DRIVERS_JSON = "data/drivers.json"


def load_driver_teams(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("teams", {})


def parse_detailed(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def analyze_race_csv(race_csv: str) -> Dict[str, str]:
    # Basic extraction: top3 drivers and teams, DNFs, pit counts, grid positions
    if not os.path.exists(race_csv):
        return {"error": "race csv not found"}

    rows = []
    with open(race_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        return {"error": "empty race csv"}

    # Map by position
    pos_map = {int(r.get("position", 9999)): r for r in rows if r.get("position")}
    top3 = [pos_map.get(1), pos_map.get(2), pos_map.get(3)]

    dnf_count = sum(
        1 for r in rows if r.get("status", "").lower() not in ("finished", "")
    )
    incidents = sum(
        int(r.get("num_incidents", "0") or 0)
        for r in rows
        if r.get("num_incidents") is not None
    )
    avg_pits = sum(int(r.get("num_pits", "0") or 0) for r in rows) / len(rows)

    # grid anomalies: count of top teams starting off inside top5
    grid_top5 = [
        r for r in rows if r.get("grid_position") and int(r.get("grid_position")) <= 5
    ]

    return {
        "top3_rows": top3,
        "dnf_count": str(dnf_count),
        "incidents_total": str(incidents),
        "avg_pits_per_driver": f"{avg_pits:.2f}",
        "grid_top5_count": str(len(grid_top5)),
    }


def main():
    detailed_csv = sys.argv[1] if len(sys.argv) > 1 else DETAILED_CSV
    driver_teams = load_driver_teams(DRIVERS_JSON)
    runs = parse_detailed(detailed_csv)

    flagged = []
    for r in runs:
        p1 = r.get("winner", "")
        p2 = r.get("p2", "")
        p3 = r.get("p3", "")
        podium = [p1, p2, p3]
        teams = [driver_teams.get(d, "Unknown") for d in podium]
        # If any of the podium teams is not in TOP_TEAMS, flag
        abnormal = any(t not in TOP_TEAMS for t in teams)
        if abnormal:
            entry = dict(r)
            entry["podium_teams"] = ",".join(teams)
            entry["podium_drivers"] = ",".join(podium)
            flagged.append(entry)

    print(f"Total runs: {len(runs)}; Flagged abnormal podium runs: {len(flagged)}")

    # For each flagged run, analyze the race CSV
    analyses = []
    for f in flagged:
        race_csv = f.get("race_csv")
        analysis = analyze_race_csv(race_csv) if race_csv else {"error": "no race_csv"}
        analyses.append((f, analysis))

    # Summarize reasons heuristically
    reasons_counter = Counter()
    detailed_reports = []
    for f, a in analyses:
        reason_notes = []
        if a.get("error"):
            reason_notes.append(a.get("error"))
        else:
            # Heuristics: many DNFs among top teams -> reliability/incident cascade
            dnf = int(a.get("dnf_count", "0"))
            incidents = int(a.get("incidents_total", "0"))
            avg_pits = float(a.get("avg_pits_per_driver", "0"))
            grid_top5 = int(a.get("grid_top5_count", "0"))

            if dnf >= 2:
                reason_notes.append("Multiple DNFs")
            if incidents >= 3:
                reason_notes.append("High incident count")
            if avg_pits > 1.5:
                reason_notes.append("High pit activity / strategy variance")
            # grid_top5 low indicates starting order shuffled
            if grid_top5 < 2:
                reason_notes.append("Top teams started poorly")

        if not reason_notes:
            reason_notes.append("No clear numeric anomaly - investigate logs")

        reasons_counter.update(reason_notes)
        detailed_reports.append(
            {
                "experiment": f.get("experiment"),
                "track": f.get("track"),
                "seed": f.get("seed"),
                "podium_drivers": f.get("podium_drivers"),
                "podium_teams": f.get("podium_teams"),
                "reasons": "; ".join(reason_notes),
                "race_csv": f.get("race_csv"),
                "log_path": f.get("log_path"),
            }
        )

    # Output summary
    out_dir = os.path.dirname(detailed_csv)
    summary_path = os.path.join(out_dir, "podium_anomalies_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        headers = [
            "experiment",
            "track",
            "seed",
            "podium_drivers",
            "podium_teams",
            "reasons",
            "race_csv",
            "log_path",
        ]
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(detailed_reports)

    print("Reason counts:")
    for k, v in reasons_counter.most_common():
        print(f"  {k}: {v}")

    print(f"Detailed anomaly report saved to: {summary_path}")


if __name__ == "__main__":
    main()
