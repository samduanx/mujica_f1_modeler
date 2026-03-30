import csv
from src.utils.generate_driver_tables import DRIVER_NAME_MAP

p = "data/driver_ratings.csv"
with open(p, "r", encoding="utf-8") as f:
    r = csv.DictReader(f)
    count = 0
    for row in r:
        name = row.get("车手")
        dr = row.get("DR")
        if name and dr:
            en = DRIVER_NAME_MAP.get(name.strip(), name.strip())
            print(f"{name.strip()} -> {en} : {dr}")
            count += 1
            if count > 30:
                break
print("done", count)
