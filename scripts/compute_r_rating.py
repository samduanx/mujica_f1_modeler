import os, csv, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
report_dir = os.path.join(ROOT, "outputs", "reports", "current_pr_and_dr")
if not os.path.exists(report_dir):
    print("Run export_pr_dr.py first to generate inputs")
    raise SystemExit(1)

team_file = os.path.join(report_dir, "team_pr.csv")
driver_file = os.path.join(report_dir, "driver_dr.csv")
out_file = os.path.join(report_dir, "r_rating.csv")

teams = {}
with open(team_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        team = (r.get("Teams_en") or r.get("Teams_cn") or "").strip()
        pr = r.get("PR")
        try:
            prn = float(str(pr).strip())
        except Exception:
            # try to strip quotes/spaces
            try:
                prn = float(str(pr).replace('"', "").strip())
            except Exception:
                prn = None
        teams[team] = prn

missing_teams = set()
rows = []
with open(driver_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        driver_en = (r.get("driver_en") or "").strip()
        driver_cn = (r.get("driver_cn") or "").strip()
        team_en = (r.get("team_en") or "").strip()
        dr = r.get("DR")
        try:
            drn = float(str(dr).strip())
        except Exception:
            drn = None
        prn = teams.get(team_en)
        if prn is None:
            missing_teams.add(team_en)
        R = None
        if drn is not None and prn is not None:
            R = drn * prn / 100.0
        rows.append(
            {
                "driver_cn": driver_cn,
                "driver_en": driver_en,
                "team_en": team_en,
                "DR": drn,
                "PR": prn,
                "R": R,
            }
        )

with open(out_file, "w", encoding="utf-8", newline="") as f:
    fieldnames = ["driver_cn", "driver_en", "team_en", "DR", "PR", "R"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ("" if r[k] is None else r[k]) for k in fieldnames})

print("Wrote R ratings to", out_file)
if missing_teams:
    print("Warning: missing PR for teams:", ", ".join(sorted(missing_teams)))
