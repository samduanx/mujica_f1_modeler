"""
Driver table generator with Piastri/Ricciardo substitution logic.

Generates track-specific driver lineup CSV files from data/driver_ratings.csv.

Substitution Rule:
- Before/during Spain GP: Piastri in McLaren, Ricciardo not racing
- After Spain GP: Ricciardo in McLaren, Piastri not racing
"""

import pandas as pd
import os

# Chinese name to English name mapping (车手 -> Driver)
DRIVER_NAME_MAP = {
    "维斯塔潘": "Verstappen",
    "佩雷兹": "Perez",
    "勒克莱尔": "Leclerc",
    "塞恩斯": "Sainz",
    "汉密尔顿": "Hamilton",
    "拉塞尔": "Russell",
    "加斯利": "Gasly",
    "角田裕毅": "Tsunoda",
    "维特尔": "Vettel",
    "斯特罗尔": "Stroll",
    "阿隆索": "Alonso",
    "奥康": "Ocon",
    "博塔斯": "Bottas",
    "周冠宇": "Zhou",
    "诺里斯": "Norris",
    "里卡多": "Ricciardo",
    "马格努森": "Magnussen",
    "米克": "Schumacher",
    "阿尔本": "Albon",
    "拉提菲": "Latifi",
    "霍肯伯格": "Hulkenberg",
    "菲蒂帕尔迪": "Fittipaldi",
    "德弗里斯": "De Vries",
    "皮亚斯特里": "Piastri",
    "施瓦茨曼": "Schwartzman",
    "格罗斯让": "Grosjean",
}

# Reverse mapping (English -> Chinese) for Spain ratings lookup
DRIVER_NAME_MAP_REVERSE = {v: k for k, v in DRIVER_NAME_MAP.items()}

# Team name mappings
TEAM_NAME_MAP_CN_TO_EN = {
    "红牛": "Red Bull",
    "法拉利": "Ferrari",
    "奔驰": "Mercedes",
    "小红牛": "AlphaTauri",
    "马丁": "Aston Martin",
    "Alpine": "Alpine",
    "阿罗": "Alfa Romeo",
    "迈凯轮": "McLaren",
    "哈斯": "Haas",
    "威队": "Williams",
    "安德雷蒂": "Andretti",
    "迈/Alpine": "McLaren",
}

# Default track coefficients (C(M), C(A), C(P))
# These determine how much each car attribute contributes to PR for each track
DEFAULT_TRACK_COEFFS = {
    "C(M)": 1.0,
    "C(A)": 1.0,
    "C(P)": 1.0,
}


def load_track_coefficients(track_csv_path="data/track_characteristics.csv"):
    """
    Load track coefficients from CSV.

    Returns dict: {track_name: {'C(M)': x, 'C(A)': y, 'C(P)': z}}
    """
    track_coeffs = {}
    try:
        df = pd.read_csv(track_csv_path, encoding="utf-8-sig")

        # Find the track name column - it could be in the first column (Unnamed: 0) or first data column
        cols = df.columns.tolist()

        for _, row in df.iterrows():
            # Try to find track name - look for first non-C(M/A/P) column or Unnamed: 0
            track_name = None
            for col in cols:
                if col not in ["C(M)", "C(A)", "C(P)"]:
                    track_name = row[col]
                    break

            if pd.notna(track_name):
                track_coeffs[track_name] = {
                    "C(M)": float(row["C(M)"]) if pd.notna(row["C(M)"]) else 1.0,
                    "C(A)": float(row["C(A)"]) if pd.notna(row["C(A)"]) else 1.0,
                    "C(P)": float(row["C(P)"]) if pd.notna(row["C(P)"]) else 1.0,
                }
    except Exception as e:
        print(f"Warning: Could not load track coefficients: {e}")

    return track_coeffs


def load_team_parameters(team_csv_path="data/spain_team.csv"):
    """
    Load team parameters from CSV.

    Returns dict: {team_en: {'Mech': x, 'Aero': y, 'Power': z, 'Stability': s, 'PR': p}}
    """
    team_params = {}
    try:
        df = pd.read_csv(team_csv_path, encoding="utf-8-sig")
        for _, row in df.iterrows():
            team_en = row["Teams"]
            if pd.notna(team_en):
                team_params[team_en] = {
                    "Mech": float(row["Mech"]),
                    "Aero": float(row["Aero"]),
                    "Power": float(row["Power"]),
                    "Stability": float(row["Stability"]),
                    "PR": float(row["PR"]) if pd.notna(row.get("PR")) else None,
                }
    except Exception as e:
        print(f"Warning: Could not load team parameters: {e}")

    return team_params


def calculate_pr(cm, ca, cp, mechanical, aero, power):
    """
    Calculate PR (Performance Rating) using track coefficients and team parameters.

    PR = C(M) * 机械 + C(A) * 空动 + C(P) * 动力
    """
    return cm * mechanical + ca * aero + cp * power


def calculate_ro(dr, pr):
    """
    Calculate RO (Race Overall) from DR and PR.

    RO = DR * PR / 100
    """
    return dr * pr / 100


# Global caches for track coefficients and team parameters
_TRACK_COEFFS_CACHE = None
_TEAM_PARAMS_CACHE = None


def get_track_coefficients(track_name):
    """Get track coefficients, loading from file if needed."""
    global _TRACK_COEFFS_CACHE
    if _TRACK_COEFFS_CACHE is None:
        _TRACK_COEFFS_CACHE = load_track_coefficients()

    # Try direct lookup first
    if track_name in _TRACK_COEFFS_CACHE:
        return _TRACK_COEFFS_CACHE[track_name]

    # Try mapping from English to Chinese
    track_name_cn = TRACK_NAME_MAP_EN_TO_CN.get(track_name, track_name)
    if track_name_cn in _TRACK_COEFFS_CACHE:
        return _TRACK_COEFFS_CACHE[track_name_cn]

    return DEFAULT_TRACK_COEFFS


def get_team_parameters(team_name_cn):
    """Get team parameters, loading from file if needed."""
    global _TEAM_PARAMS_CACHE
    if _TEAM_PARAMS_CACHE is None:
        _TEAM_PARAMS_CACHE = load_team_parameters()
    return _TEAM_PARAMS_CACHE.get(team_name_cn)


# Chinese team name to English team name mapping (所属 -> Team)
# This is used in get_track_lineup to convert Chinese team names to English
TEAM_NAME_MAP = {
    "红牛": "Red Bull",
    "法拉利": "Ferrari",
    "奔驰": "Mercedes",
    "小红牛": "AlphaTauri",
    "马丁": "Aston Martin",
    "Alpine": "Alpine",
    "阿罗": "Alfa Romeo",
    "迈凯轮": "McLaren",
    "哈斯": "Haas",
    "威队": "Williams",
    "安德雷蒂": "Andretti",
    "迈/Alpine": "McLaren",  # Piastri's team notation
}

# Track name mapping (English -> Chinese for CSV lookup)
TRACK_NAME_MAP_EN_TO_CN = {
    "Spain": "西班牙",
    "Bahrain": "巴林",
    "Monaco": "摩纳哥",
    # Add more as needed
}

# 2022 F1 Calendar order for determining substitution
# Spain is round 6 in the 2022 calendar
F1_2022_CALENDAR = [
    "Bahrain",
    "Saudi Arabia",
    "Australia",
    "Italy",  # Imola
    "Miami",
    "Spain",  # Piastri substitutes until and including Spain
    "Monaco",
    "Azerbaijan",
    "Canada",
    "United Kingdom",
    "Austria",
    "France",
    "Hungary",
    "Belgium",
    "Netherlands",
    "Italy",  # Monza
    "Singapore",
    "Japan",
    "United States",
    "Mexico",
    "Brazil",
    "Abu Dhabi",
]

# Tracks where Piastri is substituted (Spain and before)
PIASTRI_TRACKS = set(F1_2022_CALENDAR[: F1_2022_CALENDAR.index("Spain") + 1])


def load_driver_ratings(csv_path="data/driver_ratings.csv"):
    """
    Load driver ratings from CSV file with Chinese headers.

    Returns dict with Chinese driver names as keys.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Driver ratings file not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    drivers = {}
    for _, row in df.iterrows():
        # Skip empty rows
        if pd.isna(row["车手"]):
            continue

        driver_cn = row["车手"].strip()
        team_cn = str(row["所属"]).strip() if pd.notna(row["所属"]) else ""
        dr_value = row["DR"]

        # Parse car number
        car_num = row["车号"]
        if pd.notna(car_num):
            try:
                car_num = int(float(car_num))
            except (ValueError, TypeError):
                car_num = None
        else:
            car_num = None

        # Get skills (技能1, 技能2)
        skills = []
        if "技能1" in df.columns and pd.notna(row["技能1"]):
            skills.append(row["技能1"])
        if "技能2" in df.columns and pd.notna(row["技能2"]):
            skills.append(row["技能2"])

        drivers[driver_cn] = {
            "car_number": car_num,
            "team_cn": team_cn,
            "dr": float(dr_value) if pd.notna(dr_value) else 99.0,
            "skills": skills,
        }

    return drivers


def get_track_lineup(track_name, driver_ratings):
    """
    Generate driver lineup for a specific track.

    Applies Piastri/Ricciardo substitution logic:
    - Before/during Spain: Piastri in McLaren, Ricciardo not racing
    - After Spain: Ricciardo in McLaren, Piastri not racing

    Limits each team to 2 drivers (main drivers only).
    """
    is_piastri_racing = track_name in PIASTRI_TRACKS

    # First pass: collect all drivers and group by team
    team_drivers = {}
    for driver_cn, data in driver_ratings.items():
        driver_en = DRIVER_NAME_MAP.get(driver_cn)
        if not driver_en:
            continue

        # Apply substitution logic
        if driver_en == "Ricciardo":
            # Ricciardo only races after Spain
            if is_piastri_racing:
                continue  # Skip Ricciardo during Piastri's substitution period

        if driver_en == "Piastri":
            # Piastri only races until and including Spain
            if not is_piastri_racing:
                continue  # Skip Piastri after Spain

        # Handle special case drivers without teams (Fittipaldi, De Vries are reserves)
        if driver_en in ("Fittipaldi", "De Vries"):
            continue  # These are reserve drivers, not in main lineup

        # Handle team mapping
        team_cn = data["team_cn"]

        # Fix Piastri's team to McLaren during substitution
        if driver_en == "Piastri" and "迈" in team_cn:
            team_en = "McLaren"
        else:
            team_en = TEAM_NAME_MAP.get(team_cn, team_cn)

        # Group drivers by team
        if team_en not in team_drivers:
            team_drivers[team_en] = []
        team_drivers[team_en].append(
            {
                "Driver": driver_en,
                "Team": team_en,
                "DR": data["dr"],
                "CarNumber": data["car_number"],
                "Skills": "|".join(data["skills"]) if data["skills"] else "",
            }
        )

    # Second pass: limit each team to 2 drivers (by car number, lower number = higher priority)
    lineup = []
    for team, drivers in team_drivers.items():
        # Sort by car number (None at end), take first 2
        drivers_sorted = sorted(
            drivers, key=lambda x: (x["CarNumber"] is None, x["CarNumber"] or 999)
        )
        lineup.extend(drivers_sorted[:2])

    return lineup


# Reverse mapping (English team name -> Chinese team name)
TEAM_NAME_EN_TO_CN = {v: k for k, v in TEAM_NAME_MAP_CN_TO_EN.items()}


def generate_track_csv(track_name, output_dir="outputs/tables", driver_ratings=None):
    """Generate driver lineup CSV for a specific track with PR/RO calculation."""
    if driver_ratings is None:
        driver_ratings = load_driver_ratings()

    # Get track coefficients (default if not found)
    track_coeffs = get_track_coefficients(track_name)
    cm = track_coeffs.get("C(M)", 1.0)
    ca = track_coeffs.get("C(A)", 1.0)
    cp = track_coeffs.get("C(P)", 1.0)

    lineup = get_track_lineup(track_name, driver_ratings)

    # Calculate PR and RO for each driver
    for entry in lineup:
        team_en = entry["Team"]

        # Get team parameters
        team_params = get_team_parameters(team_en)

        if team_params:
            # Use pre-calculated PR from spain_team.csv if available
            pr_value = team_params.get("PR")
            if pr_value is not None:
                pr = pr_value
            else:
                # Fallback: calculate from components
                mechanical = team_params.get("Mech", 95.0)
                aero = team_params.get("Aero", 95.0)
                power = team_params.get("Power", 100.0)
                pr = calculate_pr(cm, ca, cp, mechanical, aero, power)
            # Calculate RO = DR * PR / 100
            ro = calculate_ro(entry["DR"], pr)

            entry["PR"] = round(pr, 2)
            entry["RO"] = round(ro, 2)
        else:
            # Fallback if team params not found
            entry["PR"] = round(300 + (entry["DR"] - 99) * 2, 2)
            entry["RO"] = round(300 + (entry["DR"] - 99) * 2.5, 2)

    # Create DataFrame
    df = pd.DataFrame(lineup)

    # Sort by car number for consistent ordering
    df = df.sort_values("CarNumber").reset_index(drop=True)

    # Reorder columns to match expected format
    df = df[["Driver", "Team", "DR", "PR", "RO"]]

    # Save to CSV
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{track_name}.csv")
    df.to_csv(output_path, index=False)

    return output_path


def generate_all_track_csvs(driver_ratings=None, output_dir="outputs/tables"):
    """Generate driver lineup CSVs for all tracks in the calendar."""
    if driver_ratings is None:
        driver_ratings = load_driver_ratings()

    generated_files = []

    for track_name in F1_2022_CALENDAR:
        output_path = generate_track_csv(track_name, output_dir, driver_ratings)
        generated_files.append(output_path)
        print(f"Generated: {output_path}")

    return generated_files


def get_driver_dr_ratings(driver_ratings=None):
    """
    Get DR ratings dictionary for simulation use.

    Returns dict: {DriverName: DR_Value}
    """
    if driver_ratings is None:
        driver_ratings = load_driver_ratings()

    dr_dict = {}
    for driver_cn, data in driver_ratings.items():
        driver_en = DRIVER_NAME_MAP.get(driver_cn)
        if driver_en:
            dr_dict[driver_en] = data["dr"]

    return dr_dict


def get_active_drivers_for_track(track_name, driver_ratings=None):
    """
    Get list of active drivers for a specific track.

    Applies Piastri/Ricciardo substitution logic.
    """
    if driver_ratings is None:
        driver_ratings = load_driver_ratings()

    lineup = get_track_lineup(track_name, driver_ratings)
    return [d["Driver"] for d in lineup]


if __name__ == "__main__":
    # Generate all track CSVs
    print("Generating driver lineups for all tracks...")
    print(f"Piastri races in: {sorted(PIASTRI_TRACKS)}")
    print(f"Ricciardo races in: {sorted(set(F1_2022_CALENDAR) - PIASTRI_TRACKS)}")
    print()

    files = generate_all_track_csvs()
    print(f"\nGenerated {len(files)} track lineup files.")

    # Show substitution examples
    print("\n=== Substitution Examples ===")
    for track in ["Australia", "Spain", "Monaco", "Canada"]:
        active = get_active_drivers_for_track(track)
        mclaren_drivers = [d for d in active if d in ("Piastri", "Ricciardo")]
        print(
            f"{track}: {mclaren_drivers if mclaren_drivers else 'No McLaren sub driver'}"
        )
