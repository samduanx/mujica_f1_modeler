#!/usr/bin/env python3
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from statistics import mean

PARSER = argparse.ArgumentParser()
PARSER.add_argument('--n_seeds', type=int, default=1)
PARSER.add_argument('--start_seed', type=int, default=1000)
PARSER.add_argument('--intensities', type=str, default='subtle,moderate,strong,ultra,off')
PARSER.add_argument('--gp-name', type=str, default='Spain')
PARSER.add_argument('--out_dir', type=str, default='outputs/analysis')
PARSER.add_argument('--dry', action='store_true')
PARSER.add_argument('--timeout', type=int, default=900000)

args = PARSER.parse_args()
ints = args.intensities.split(',')

os.makedirs(args.out_dir, exist_ok=True)
rows = []

race_dir_re = re.compile(r'Race output directory: (.+)')

for i in range(args.n_seeds):
    seed = args.start_seed + i
    for intensity in ints:
        env = os.environ.copy()
        if intensity == 'off':
            env.pop('F1_NARRATIVE_ASSIST', None)
        else:
            env['F1_NARRATIVE_ASSIST'] = intensity
            env['F1_ASSIST_TARGET'] = 'Ferrari'

        cmd = ['uv', 'run', 'python', 'scripts/main.py', '--gp-name', args.gp_name, '--seed', str(seed)]
        print(f"Running seed={seed} intensity={intensity} -> cmd: {' '.join(cmd)}")
        if args.dry:
            # try to find existing outputs by seed in outputs/race_weekend
            rows.append({'seed': seed, 'intensity': intensity, 'note': 'dry-run'})
            continue

        try:
            p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            print(f"Timeout seed={seed} intensity={intensity}")
            rows.append({'seed': seed, 'intensity': intensity, 'error': 'timeout'})
            continue

        out = p.stdout + '\n' + p.stderr
        m = race_dir_re.search(out)
        out_dir = None
        if m:
            out_dir = m.group(1).strip()
            out_dir = out_dir.replace('\\','/')
        else:
            # try fallback: last created folder under outputs/race_weekend
            candidates = []
            base = os.path.join('outputs','race_weekend')
            if os.path.isdir(base):
                for name in os.listdir(base):
                    path = os.path.join(base, name)
                    if os.path.isdir(path):
                        candidates.append((os.path.getmtime(path), path))
                if candidates:
                    candidates.sort()
                    out_dir = candidates[-1][1]
        if not out_dir:
            rows.append({'seed': seed, 'intensity': intensity, 'error': 'no_output_dir'})
            continue

        race_csv = os.path.join(out_dir, 'race', 'race_results_spain.csv')
        if not os.path.exists(race_csv):
            rows.append({'seed': seed, 'intensity': intensity, 'error': f'missing {race_csv}', 'out_dir': out_dir})
            continue

        # parse race CSV
        with open(race_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)

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

        winner_row = next((r for r in all_rows if r.get('position') and r['position'].strip() and int(r['position'])==1), None)
        winner_driver = winner_row['driver'] if winner_row else ''
        winner_team = winner_row['team'] if winner_row else ''
        winner_time = to_float(winner_row.get('total_time','')) if winner_row else None

        ferrari_rows = [r for r in all_rows if r.get('team','').strip()=='Ferrari']
        ferrari_best = None
        ferrari_total_incidents = 0
        ferrari_total_pits = 0
        ferrari_laps_completed = 0
        for r in ferrari_rows:
            if ferrari_best is None or (r.get('position') and int(r['position']) < int(ferrari_best.get('position',999))):
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

        podium = [r for r in all_rows if r.get('position') and r['position'].strip() and int(r['position'])<=3]
        ferrari_on_podium = any(r.get('team','').strip()=='Ferrari' for r in podium)

        total_incidents = sum(to_int(r.get('num_incidents',0)) for r in all_rows)
        total_pits = sum(to_int(r.get('num_pits',0)) for r in all_rows)

        rows.append({
            'seed': seed,
            'intensity': intensity,
            'out_dir': out_dir,
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
            'total_incidents': total_incidents,
            'total_pits': total_pits,
        })

# write detailed CSV
fields = [
    'seed','intensity','out_dir','winner_driver','winner_team','winner_time',
    'ferrari_best_pos','ferrari_best_driver','ferrari_best_time','ferrari_gap_to_winner',
    'ferrari_total_incidents','ferrari_total_pits','ferrari_laps_completed','ferrari_on_podium',
    'total_incidents','total_pits'
]
with open(os.path.join(args.out_dir, 'spain_montecarlo_detailed.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        # filter to expected fields to avoid unexpected keys like 'error'
        rowf = {k: r.get(k, '') for k in fields}
        w.writerow(rowf)

# aggregate per intensity
ag = {}
for r in rows:
    if 'error' in r:
        continue
    k = r['intensity']
    ag.setdefault(k, []).append(r)

summary_rows = []
for k, items in ag.items():
    ferrari_wins = sum(1 for it in items if it.get('winner_team')=='Ferrari')
    ferrari_podiums = sum(1 for it in items if it.get('ferrari_on_podium'))
    ferrari_best_positions = [it['ferrari_best_pos'] for it in items if it.get('ferrari_best_pos')]
    gaps = [it['ferrari_gap_to_winner'] for it in items if it.get('ferrari_gap_to_winner') is not None]
    mean_pos = mean(ferrari_best_positions) if ferrari_best_positions else None
    mean_gap = mean(gaps) if gaps else None
    mean_incidents = mean([it['ferrari_total_incidents'] for it in items])
    mean_pits = mean([it['ferrari_total_pits'] for it in items])
    summary_rows.append({
        'intensity': k,
        'runs': len(items),
        'ferrari_wins': ferrari_wins,
        'ferrari_podiums': ferrari_podiums,
        'mean_ferrari_best_pos': mean_pos,
        'mean_gap_to_winner': mean_gap,
        'mean_ferrari_incidents': mean_incidents,
        'mean_ferrari_pits': mean_pits,
    })

with open(os.path.join(args.out_dir, 'spain_montecarlo_summary.csv'), 'w', newline='', encoding='utf-8') as f:
    fn = ['intensity','runs','ferrari_wins','ferrari_podiums','mean_ferrari_best_pos','mean_gap_to_winner','mean_ferrari_incidents','mean_ferrari_pits']
    w = csv.DictWriter(f, fieldnames=fn)
    w.writeheader()
    for r in summary_rows:
        w.writerow(r)

print('Done. Detailed and summary CSVs saved in', args.out_dir)
