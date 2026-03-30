import csv
import os
import sys
from collections import defaultdict, Counter
from statistics import mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, 'outputs', 'reports')
# find latest monte_carlo_weekend folder
folders = [d for d in os.listdir(REPORTS) if d.startswith('monte_carlo_weekend_')]
if not folders:
    print('No monte_carlo_weekend_* reports found')
    raise SystemExit(1)
folders.sort()
latest = folders[-1]
report_dir = os.path.join(REPORTS, latest)

detail_csv = os.path.join(report_dir, 'detailed_runs.csv')
if not os.path.exists(detail_csv):
    print('Detailed runs CSV not found:', detail_csv)
    raise SystemExit(1)

ratings_path = os.path.join(ROOT, 'data', 'driver_ratings.csv')
if not os.path.exists(ratings_path):
    print('Driver ratings not found:', ratings_path)
    raise SystemExit(1)

# load ratings and map Chinese names to English using project mapping
ratings = {}
try:
    # ensure project root is on sys.path for local imports
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from src.utils.generate_driver_tables import DRIVER_NAME_MAP
except Exception:
    DRIVER_NAME_MAP = {}

with open(ratings_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        driver_cn = (r.get('车手') or '').strip()
        dr = r.get('DR') or r.get('dr')
        if not driver_cn or not dr:
            continue
        try:
            dr_val = float(dr)
        except Exception:
            continue

        # map to English name if available
        driver_en = DRIVER_NAME_MAP.get(driver_cn, driver_cn)
        ratings[driver_en] = dr_val

# helper to parse race csv for positions

def parse_race_csv(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r.get('driver') or r.get('Driver') or r.get('车手')
            pos = r.get('position') or r.get('Position')
            try:
                pos = int(float(pos))
            except Exception:
                continue
            if name:
                rows.append((name.strip(), pos))
    return rows

# aggregate counts per driver
position_counts = defaultdict(Counter)  # driver -> Counter(position->count)
race_counts = Counter()  # driver -> number of races seen

with open(detail_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        race_csv = r.get('race_csv','').strip()
        if race_csv and os.path.exists(race_csv):
            parsed = parse_race_csv(race_csv)
            if parsed:
                for name,pos in parsed:
                    position_counts[name][pos] += 1
                    race_counts[name] += 1
                continue
        # fallback to winner/p2/p3
        for col,pos in [('winner',1),('p2',2),('p3',3)]:
            name = (r.get(col) or '').strip()
            if name:
                position_counts[name][pos] += 1
                race_counts[name] += 1

# create per-driver stats
drivers = sorted(position_counts.keys())
max_pos = 20
output_rows = []
for d in drivers:
    total = race_counts.get(d, 0)
    if total == 0:
        continue
    counts = position_counts[d]
    mean_pos = sum(p*cnt for p,cnt in counts.items() for _ in [0])
    # compute mean properly
    mean_pos = sum(p*cnt for p,cnt in counts.items()) / total
    top1 = counts.get(1,0)
    top3 = sum(counts.get(p,0) for p in range(1,4))
    output_rows.append({
        'driver': d,
        'rating': ratings.get(d,''),
        'races_observed': str(total),
        'mean_position': f"{mean_pos:.3f}",
        'top1_count': str(top1),
        'top1_pct': f"{top1/total:.3%}",
        'top3_count': str(top3),
        'top3_pct': f"{top3/total:.3%}",
    })

# write CSV
out_csv = os.path.join(report_dir, 'rating_position_distribution.csv')
with open(out_csv, 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['driver','rating','races_observed','mean_position','top1_count','top1_pct','top3_count','top3_pct']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in sorted(output_rows, key=lambda x: (-float(x['rating']) if x['rating']!='' else 0, x['driver'])):
        writer.writerow(row)

print('Wrote distribution to', out_csv)

# produce aggregated bucket stats by rating bins (quantiles or buckets)
# simple fixed buckets: [<99.6), [99.6-99.9), [99.9-100.2), [>100.2]
buckets = [(-1,99.6),(99.6,99.9),(99.9,100.2),(100.2,999)]
bucket_labels = ['<99.6','99.6-99.9','99.9-100.2','>100.2']
bucket_data = {lab: {'races':0,'top1':0,'top3':0,'drivers':set()} for lab in bucket_labels}

for row in output_rows:
    try:
        r = float(row['rating'])
    except Exception:
        continue
    for (low,high),lab in zip(buckets,bucket_labels):
        if low < r <= high:
            total = int(row['races_observed'])
            bucket_data[lab]['races'] += total
            bucket_data[lab]['top1'] += int(row['top1_count'])
            bucket_data[lab]['top3'] += int(row['top3_count'])
            bucket_data[lab]['drivers'].add(row['driver'])
            break

# write bucket summary
out_bucket = os.path.join(report_dir, 'rating_bucket_summary.csv')
with open(out_bucket, 'w', encoding='utf-8', newline='') as f:
    fieldnames = ['bucket','drivers_count','races','top1_pct','top3_pct']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for lab in bucket_labels:
        d = bucket_data[lab]
        races = d['races']
        top1pct = f"{d['top1']/races:.3%}" if races>0 else '0.000%'
        top3pct = f"{d['top3']/races:.3%}" if races>0 else '0.000%'
        writer.writerow({'bucket':lab,'drivers_count':str(len(d['drivers'])),'races':str(races),'top1_pct':top1pct,'top3_pct':top3pct})

print('Wrote bucket summary to', out_bucket)
