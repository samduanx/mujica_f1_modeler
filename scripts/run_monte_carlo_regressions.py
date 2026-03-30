"""
Batch Monte Carlo-style weekend regression runner.

Runs multiple seeded full-weekend simulations across sprint and non-sprint formats,
then writes detailed and summary reports.

Usage:
    uv run python scripts/run_monte_carlo_regressions.py
"""

from __future__ import annotations

import csv
import os
import glob
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from contextlib import redirect_stdout, redirect_stderr

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import run_race_weekend


@dataclass
class Experiment:
    name: str
    track: str
    weekend_type: str
    sessions: List[str]
    seeds: List[int]


def _safe_int(value: str, default: int = 9999) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _find_race_csv(output_dir: str, gp_name: Optional[str]) -> Optional[str]:
    race_dir = os.path.join(output_dir, "race")
    if not os.path.isdir(race_dir):
        return None

    if gp_name:
        expected = os.path.join(race_dir, f"race_results_{gp_name.lower()}.csv")
        if os.path.exists(expected):
            return expected

    candidates = sorted(glob.glob(os.path.join(race_dir, "race_results_*.csv")))
    return candidates[0] if candidates else None


def _parse_podium_and_lapping(csv_path: str) -> Tuple[Optional[str], Optional[str], Optional[str], int, int]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return None, None, None, 0, 0

    ordered = sorted(rows, key=lambda r: _safe_int(r.get("position", "9999")))

    p1 = ordered[0].get("driver") if len(ordered) >= 1 else None
    p2 = ordered[1].get("driver") if len(ordered) >= 2 else None
    p3 = ordered[2].get("driver") if len(ordered) >= 3 else None

    lapped_count = 0
    max_laps_down = 0
    for row in ordered:
        laps_down = _safe_int(row.get("laps_down", "0"), default=0)
        if laps_down > 0:
            lapped_count += 1
            max_laps_down = max(max_laps_down, laps_down)

    return p1, p2, p3, lapped_count, max_laps_down


def run_experiment(exp: Experiment, base_output_dir: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    logs_dir = os.path.join(base_output_dir, "logs", exp.name)
    os.makedirs(logs_dir, exist_ok=True)

    total = len(exp.seeds)
    print(f"\n=== [{exp.name}] {exp.track} | {exp.weekend_type} | runs={total} ===")

    for index, seed in enumerate(exp.seeds, start=1):
        run_start = time.time()
        log_path = os.path.join(logs_dir, f"seed_{seed}.log")

        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                with redirect_stdout(log_file), redirect_stderr(log_file):
                    results = run_race_weekend(
                        track_name=exp.track,
                        sessions=exp.sessions,
                        seed=seed,
                    )

            race_result = results.get("race", {}) if isinstance(results, dict) else {}
            status = race_result.get("status", "unknown")
            output_dir = results.get("_output_dir", "") if isinstance(results, dict) else ""
            gp_name = race_result.get("gp_name", exp.track)

            winner = None
            p2 = None
            p3 = None
            lapped_count = 0
            max_laps_down = 0
            race_csv = None

            if status == "completed" and output_dir:
                race_csv = _find_race_csv(output_dir, gp_name)
                if race_csv and os.path.exists(race_csv):
                    winner, p2, p3, lapped_count, max_laps_down = _parse_podium_and_lapping(race_csv)

            elapsed = round(time.time() - run_start, 2)
            print(
                f"[{exp.name}] {index}/{total} seed={seed} status={status} winner={winner or '-'} lapped={lapped_count} t={elapsed}s"
            )

            rows.append(
                {
                    "experiment": exp.name,
                    "track": exp.track,
                    "weekend_type": exp.weekend_type,
                    "sessions": ",".join(exp.sessions),
                    "seed": str(seed),
                    "status": status,
                    "winner": winner or "",
                    "p2": p2 or "",
                    "p3": p3 or "",
                    "lapped_count": str(lapped_count),
                    "max_laps_down": str(max_laps_down),
                    "output_dir": output_dir,
                    "race_csv": race_csv or "",
                    "log_path": log_path,
                    "elapsed_seconds": str(elapsed),
                }
            )

        except Exception as exc:
            elapsed = round(time.time() - run_start, 2)
            print(f"[{exp.name}] {index}/{total} seed={seed} status=error err={exc} t={elapsed}s")
            rows.append(
                {
                    "experiment": exp.name,
                    "track": exp.track,
                    "weekend_type": exp.weekend_type,
                    "sessions": ",".join(exp.sessions),
                    "seed": str(seed),
                    "status": "error",
                    "winner": "",
                    "p2": "",
                    "p3": "",
                    "lapped_count": "0",
                    "max_laps_down": "0",
                    "output_dir": "",
                    "race_csv": "",
                    "log_path": log_path,
                    "elapsed_seconds": str(elapsed),
                }
            )

    return rows


def _write_detailed_csv(rows: List[Dict[str, str]], file_path: str) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    headers = list(rows[0].keys())
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    summary: Dict[str, Dict[str, str]] = {}

    for row in rows:
        exp = row["experiment"]
        item = summary.setdefault(
            exp,
            {
                "track": row["track"],
                "weekend_type": row["weekend_type"],
                "runs": "0",
                "completed": "0",
                "errors": "0",
                "avg_lapped": "0.00",
                "max_laps_down": "0",
                "top_winner": "",
                "top_winner_count": "0",
            },
        )

        runs = int(item["runs"]) + 1
        item["runs"] = str(runs)

        if row["status"] == "completed":
            item["completed"] = str(int(item["completed"]) + 1)
        else:
            item["errors"] = str(int(item["errors"]) + 1)

    for exp, item in summary.items():
        exp_rows = [r for r in rows if r["experiment"] == exp and r["status"] == "completed"]
        if not exp_rows:
            continue

        lapped_values = [int(r.get("lapped_count", "0")) for r in exp_rows]
        item["avg_lapped"] = f"{sum(lapped_values) / len(lapped_values):.2f}"
        item["max_laps_down"] = str(max(int(r.get("max_laps_down", "0")) for r in exp_rows))

        winner_counts: Dict[str, int] = {}
        for r in exp_rows:
            w = r.get("winner", "")
            if w:
                winner_counts[w] = winner_counts.get(w, 0) + 1

        if winner_counts:
            top_winner = max(winner_counts.items(), key=lambda kv: kv[1])
            item["top_winner"] = top_winner[0]
            item["top_winner_count"] = str(top_winner[1])

    return summary


def _write_summary_md(summary: Dict[str, Dict[str, str]], rows: List[Dict[str, str]], file_path: str) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    lines: List[str] = []
    lines.append("# Monte Carlo Weekend Regression Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Experiment Overview")
    lines.append("")
    lines.append("| Experiment | Track | Weekend Type | Runs | Completed | Errors | Avg Lapped Cars | Max Laps Down | Most Frequent Winner | Count |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|")

    for exp, item in summary.items():
        lines.append(
            "| {exp} | {track} | {weekend_type} | {runs} | {completed} | {errors} | {avg_lapped} | {max_laps_down} | {top_winner} | {top_winner_count} |".format(
                exp=exp,
                track=item["track"],
                weekend_type=item["weekend_type"],
                runs=item["runs"],
                completed=item["completed"],
                errors=item["errors"],
                avg_lapped=item["avg_lapped"],
                max_laps_down=item["max_laps_down"],
                top_winner=item["top_winner"] or "-",
                top_winner_count=item["top_winner_count"],
            )
        )

    lines.append("")
    lines.append("## Winner Distribution")
    lines.append("")

    experiments = sorted(set(r["experiment"] for r in rows))
    for exp in experiments:
        lines.append(f"### {exp}")
        exp_rows = [r for r in rows if r["experiment"] == exp and r["status"] == "completed"]
        winner_counts: Dict[str, int] = {}
        for r in exp_rows:
            winner = r.get("winner", "")
            if winner:
                winner_counts[winner] = winner_counts.get(winner, 0) + 1

        if not winner_counts:
            lines.append("- No completed runs.")
            lines.append("")
            continue

        sorted_counts = sorted(winner_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        for winner, count in sorted_counts:
            lines.append(f"- {winner}: {count}")
        lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_output_dir = os.path.join("outputs", "reports", f"monte_carlo_weekend_{timestamp}")
    os.makedirs(base_output_dir, exist_ok=True)

    experiments = [
        Experiment(
            name="austria_sprint_main",
            track="Austria",
            weekend_type="sprint",
            sessions=["fp1", "qualifying", "fp2", "sprint", "race"],
            seeds=list(range(1001, 1101)),
        ),
        Experiment(
            name="spain_full_weekend",
            track="Spain",
            weekend_type="normal",
            sessions=["fp1", "fp2", "fp3", "qualifying", "race"],
            seeds=list(range(1101, 1201)),
        ),
        Experiment(
            name="imola_sprint_extra",
            track="Imola",
            weekend_type="sprint",
            sessions=["fp1", "qualifying", "fp2", "sprint", "race"],
            seeds=list(range(1201, 1301)),
        ),
        Experiment(
            name="bahrain_full_extra",
            track="Bahrain",
            weekend_type="normal",
            sessions=["fp1", "fp2", "fp3", "qualifying", "race"],
            seeds=list(range(1301, 1401)),
        ),
    ]

    all_rows: List[Dict[str, str]] = []

    print("Starting multi-track Monte Carlo-style weekend regressions...")
    print(f"Output root: {base_output_dir}")

    for exp in experiments:
        all_rows.extend(run_experiment(exp, base_output_dir))

    detailed_csv_path = os.path.join(base_output_dir, "detailed_runs.csv")
    summary_md_path = os.path.join(base_output_dir, "summary.md")

    _write_detailed_csv(all_rows, detailed_csv_path)
    summary = _summarize(all_rows)
    _write_summary_md(summary, all_rows, summary_md_path)

    total_runs = len(all_rows)
    completed_runs = sum(1 for r in all_rows if r["status"] == "completed")
    error_runs = total_runs - completed_runs

    print("\n=== Regression Batch Completed ===")
    print(f"Total runs: {total_runs}")
    print(f"Completed: {completed_runs}")
    print(f"Errors: {error_runs}")
    print(f"Detailed CSV: {detailed_csv_path}")
    print(f"Summary MD: {summary_md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
