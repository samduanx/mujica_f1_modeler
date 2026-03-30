"""Copy of compare_metrics moved into scripts/ for repo cleanup."""
import csv
from pathlib import Path

ANALYSIS = Path("outputs") / "analysis"

def read_summary():
    p = ANALYSIS / "spain_montecarlo_summary.csv"
    if not p.exists():
        print("No summary found.")
        return
    with p.open() as fh:
        print(fh.read())

if __name__ == "__main__":
    read_summary()
import csv
import os

target_runs = {
    'subtle': r'outputs/race_weekend/Spain_2026-03-29_20-58-24/race/race_results_spain.csv',
    'moderate': r'outputs/race_weekend/Spain_2026-03-29_21-02-31/race/race_results_spain.csv',
    'strong': r'outputs/race_weekend/Spain_2026-03-29_21-03-22/race/race_results_spain.csv',
    'ultra': r'outputs/race_weekend/Spain_2026-03-29_21-04-07/race/race_results_spain.csv',
}

os.makedirs('outputs/analysis', exist_ok=True)
summary_rows = []

for intensity, path in target_runs.items():
    if not os.path.exists(path):
        summary_rows.append({
            'intensity': intensity,
            'error': f'missing {path}'
        })
        continue
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # helper
    def to_int(x):
        try:
            return int(x)
        except:
            return 0
    def to_float(x):
        try:
            return float(x)
        except:
            return None

    winner_row = next((r for r in rows if r.get('position') and r['position'].strip()!='' and int(r['position'])==1), None)
    winner_driver = winner_row['driver'] if winner_row else ''
    winner_team = winner_row['team'] if winner_row else ''
    winner_time = to_float(winner_row.get('total_time','')) if winner_row else None

    # Ferrari metrics
    ferrari_rows = [r for r in rows if r.get('team','').strip()=='Ferrari']
    ferrari_best = None
    ferrari_total_incidents = 0
    ferrari_total_pits = 0
    ferrari_laps_completed = 0
    for r in ferrari_rows:
        pos = to_int(r.get('position'))
        if ferrari_best is None or (pos!=0 and pos < to_int(ferrari_best.get('position',999))):
            ferrari_best = r
        ferrari_total_incidents += to_int(r.get('num_incidents',0))
        ferrari_total_pits += to_int(r.get('num_pits',0))
        ferrari_laps_completed += to_int(r.get('laps_completed',0))
    if ferrari_best:
        ferrari_best_pos = to_int(ferrari_best.get('position'))
        ferrari_best_driver = ferrari_best.get('driver')
        ferrari_best_time = to_float(ferrari_best.get('total_time',''))
        ferrari_gap_to_winner = None
        if winner_time is not None and ferrari_best_time is not None:
            ferrari_gap_to_winner = round(ferrari_best_time - winner_time, 6)
    else:
        ferrari_best_pos = None
        ferrari_best_driver = ''
        ferrari_best_time = None
        ferrari_gap_to_winner = None

    # podium
    podium = [r for r in rows if r.get('position') and r['position'].strip()!='' and int(r['position'])<=3]
    podium_list = [f"{to_int(r['position'])}: {r['driver']} ({r['team']})" for r in podium]
    ferrari_on_podium = any(r.get('team','').strip()=='Ferrari' for r in podium)

    # global incidents/pits
    total_incidents = sum(to_int(r.get('num_incidents',0)) for r in rows)
    total_pits = sum(to_int(r.get('num_pits',0)) for r in rows)

    summary_rows.append({
        'intensity': intensity,
        'winner_driver': winner_driver,
        'winner_team': winner_team,
        'winner_time': winner_time,
        'ferrari_best_pos': ferrari_best_pos,
        'ferrari_best_driver': ferrari_best_driver,
        'ferrari_best_time': ferrari_best_time,
        'ferrari_gap_to_winner': ferrari_gap_to_winner,
        'ferrari_total_incidents': ferrari_total_incidents,
        'ferrari_total_pits': ferrari_total_pits,
        'ferrari_laps_completed': ferrari_laps_completed,
        'ferrari_on_podium': ferrari_on_podium,
        'podium': ' | '.join(podium_list),
        'total_incidents': total_incidents,
        'total_pits': total_pits,
        'source_path': path
    })

# write CSV summary
out_csv = 'outputs/analysis/spain_crosssim_summary.csv'
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = [
        'intensity','winner_driver','winner_team','winner_time',
        'ferrari_best_pos','ferrari_best_driver','ferrari_best_time','ferrari_gap_to_winner',
        'ferrari_total_incidents','ferrari_total_pits','ferrari_laps_completed','ferrari_on_podium',
        'podium','total_incidents','total_pits','source_path'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in summary_rows:
        writer.writerow(r)

# print concise table
print('Intensity | Winner (team) | Ferrari best pos | Ferrari gap to winner | Ferrari incidents | Ferrari pits | Ferrari on podium')
for r in summary_rows:
    print(f"{r.get('intensity')} | {r.get('winner_driver')} ({r.get('winner_team')}) | {r.get('ferrari_best_pos')} | {r.get('ferrari_gap_to_winner')} | {r.get('ferrari_total_incidents')} | {r.get('ferrari_total_pits')} | {r.get('ferrari_on_podium')}")

print('\nCSV summary saved to:', out_csv)
