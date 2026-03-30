import os, csv, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from src.utils.generate_driver_tables import DRIVER_NAME_MAP, TEAM_NAME_MAP

report_dir = os.path.join(ROOT, 'outputs', 'reports', 'current_pr_and_dr')
os.makedirs(report_dir, exist_ok=True)

# export team PR
team_csv = os.path.join(ROOT, 'data', 'spain_team.csv')
team_out = os.path.join(report_dir, 'team_pr.csv')
with open(team_csv, 'r', encoding='utf-8') as f_in, open(team_out, 'w', encoding='utf-8', newline='') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = ['Teams_cn','Teams_en','Mech','Aero','Power','PR','Stability']
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    for r in reader:
        team_cn = r.get('Teams')
        mech = r.get('Mech')
        aero = r.get('Aero')
        power = r.get('Power')
        pr = r.get('PR')
        stability = r.get('Stability')
        team_en = TEAM_NAME_MAP.get(team_cn, team_cn)
        writer.writerow({'Teams_cn': team_cn, 'Teams_en': team_en, 'Mech': mech, 'Aero': aero, 'Power': power, 'PR': pr, 'Stability': stability})

# export drivers
drivers_csv = os.path.join(ROOT, 'data', 'driver_ratings.csv')
driver_out = os.path.join(report_dir, 'driver_dr.csv')
with open(drivers_csv, 'r', encoding='utf-8') as f_in, open(driver_out, 'w', encoding='utf-8', newline='') as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = ['car_number','driver_cn','driver_en','team_cn','team_en','DR']
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    for r in reader:
        if not r.get('车手'):
            continue
        car = r.get('车号')
        driver_cn = r.get('车手')
        team_cn = r.get('所属')
        dr = r.get('DR')
        driver_en = DRIVER_NAME_MAP.get(driver_cn.strip(), driver_cn.strip())
        team_en = TEAM_NAME_MAP.get(team_cn, team_cn)
        writer.writerow({'car_number': car, 'driver_cn': driver_cn, 'driver_en': driver_en, 'team_cn': team_cn, 'team_en': team_en, 'DR': dr})

print('Wrote:', team_out)
print('Wrote:', driver_out)
