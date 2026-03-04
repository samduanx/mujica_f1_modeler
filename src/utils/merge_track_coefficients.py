"""
Merge track coefficients from FastF1 data and Pirelli research.
Creates a deduplicated track_characteristics.csv with C(M), C(A), C(P).

Data Sources:
- C(M): From FastF1 braking data (2022-2025) - NOTE: Limited data, use historical
- C(A): From Pirelli Preview downforce ratings (1-5 scale)
- C(P): From FastF1 full throttle percentage (2022-2025) - ACTUAL DATA

Spain reference data is kept for comparison with FastF1 calculations.
"""

import pandas as pd

# =============================================================================
# PIRELLI DOWNFORCE RATINGS (from research)
# Scale: 1 (lowest downforce) to 5 (highest downforce)
# =============================================================================
PIRELLI_DOWNFORCE = {
    "Bahrain": 3,
    "Saudi Arabia": 3,
    "Australia": 3,
    "China": 3,
    "Miami": 2,
    "Italy (Imola)": 3,
    "Spain": 3,
    "Monaco": 5,
    "Canada": 3,
    "Azerbaijan": 3,
    "UK": 4,
    "Austria": 3,
    "France": 3,
    "Hungary": 2,
    "Belgium": 3,
    "Netherlands": 3,
    "Italy (Monza)": 1,
    "Singapore": 5,
    "Japan": 4,
    "USA": 3,
    "Mexico": 2,
    "Brazil": 2,
    "Abu Dhabi": 3,
    "Qatar": 3,
}


def pirelli_to_c_a(pirelli_rating: int) -> float:
    """
    Convert Pirelli downforce rating (1-5) to C(A) coefficient.
    Formula: Rating 5 → C(A) = 1.0, Rating 1 → C(A) = 1.1
    """
    return 1.0 + (5 - pirelli_rating) * 0.025


# =============================================================================
# FASTF1 ACTUAL DATA (from calculate_track_coefficients.py)
# Full throttle percentages and derived C(P) values
# Collected from 2022-2025 FastF1 telemetry
# =============================================================================
FASTF1_DATA = {
    "Bahrain": {"C(P)": 1.05, "full_throttle_pct": 73.0, "years": "2023-2025"},
    "Saudi Arabia": {"C(P)": 1.10, "full_throttle_pct": 83.3, "years": "2024-2025"},
    "Australia": {"C(P)": 1.10, "full_throttle_pct": 83.9, "years": "2023-2024"},
    "Italy (Imola)": {"C(P)": 1.05, "full_throttle_pct": 79.7, "years": "2024-2025"},
    "Spain": {"C(P)": 1.05, "full_throttle_pct": 77.0, "years": "2022,2024"},
    "Monaco": {"C(P)": 1.00, "full_throttle_pct": 62.9, "years": "2022,2025"},
    "Canada": {"C(P)": 1.05, "full_throttle_pct": 75.6, "years": "2022,2024"},
    "UK": {"C(P)": 1.10, "full_throttle_pct": 82.7, "years": "2022"},
    "Austria": {"C(P)": 1.05, "full_throttle_pct": 78.6, "years": "2022,2024"},
    "France": {"C(P)": 1.05, "full_throttle_pct": 73.1, "years": "2022"},
    "Hungary": {"C(P)": 1.05, "full_throttle_pct": 73.6, "years": "2022-2024"},
    "Belgium": {"C(P)": 1.10, "full_throttle_pct": 81.4, "years": "2023,2025"},
    "Italy (Monza)": {"C(P)": 1.10, "full_throttle_pct": 86.2, "years": "2023"},
    "Singapore": {"C(P)": 1.00, "full_throttle_pct": 68.3, "years": "2022,2025"},
    "Japan": {"C(P)": 1.10, "full_throttle_pct": 82.8, "years": "2023,2025"},
    "USA": {"C(P)": 1.05, "full_throttle_pct": 74.8, "years": "2023-2024"},
    "Abu Dhabi": {"C(P)": 1.05, "full_throttle_pct": 78.3, "years": "2022-2024"},
    "Qatar": {"C(P)": 1.10, "full_throttle_pct": 81.2, "years": "2023-2024"},
}


# =============================================================================
# HISTORICAL C(M) VALUES - Based on F1 track characteristics
# FastF1 C(M) detection has issues - using known characteristics
# =============================================================================
HISTORICAL_C_M = {
    # High braking demand tracks (technical, street circuits)
    "Singapore": 1.15,
    "Hungary": 1.15,
    "Mexico": 1.15,
    "Brazil": 1.10,
    "Canada": 1.10,
    "Netherlands": 1.10,
    "Miami": 1.10,
    "Italy (Monza)": 1.00,  # Fast circuit, low braking
    # Medium braking demand
    "Japan": 1.05,
    "USA": 1.05,
    "Qatar": 1.05,
    "Azerbaijan": 1.00,
    # Low braking demand (high speed circuits)
    "Bahrain": 1.00,
    "Saudi Arabia": 1.00,
    "Australia": 1.00,
    "Italy (Imola)": 1.00,
    "Spain": 1.10,  # Reference value
    "Monaco": 1.00,
    "UK": 1.00,
    "Austria": 1.00,
    "France": 1.00,
    "Belgium": 1.00,
    "Abu Dhabi": 1.00,
    "China": 1.00,
}


# =============================================================================
# SPAIN REFERENCE DATA
# =============================================================================
SPAIN_REFERENCE = {
    "C(M)": 1.1,
    "C(A)": 1.025,
    "C(P)": 1.0,
}


def get_coefficient(track_name: str) -> dict:
    """Get complete coefficient set for a track."""

    # SPECIAL: Keep Spain reference data
    if track_name == "Spain":
        return {
            "C(M)": SPAIN_REFERENCE["C(M)"],
            "C(A)": SPAIN_REFERENCE["C(A)"],
            "C(P)": SPAIN_REFERENCE["C(P)"],
            "source": "reference",
        }

    result = {}

    # C(M): Use historical values (FastF1 has detection issues)
    result["C(M)"] = HISTORICAL_C_M.get(track_name, 1.05)

    # C(P): Use actual FastF1 data where available
    if track_name in FASTF1_DATA:
        result["C(P)"] = FASTF1_DATA[track_name]["C(P)"]
    else:
        # Fallback for tracks without FastF1 data
        result["C(P)"] = 1.0

    # C(A): Get from Pirelli ratings
    if track_name in PIRELLI_DOWNFORCE:
        result["C(A)"] = pirelli_to_c_a(PIRELLI_DOWNFORCE[track_name])
    else:
        result["C(A)"] = 1.05

    # Determine source
    if track_name in FASTF1_DATA:
        result["source"] = "fastf1"
    else:
        result["source"] = "historical"

    return result


def generate_track_csv():
    """Generate the final deduplicated track_characteristics.csv"""

    rows = []

    canonical_tracks = [
        "Bahrain",
        "Saudi Arabia",
        "Australia",
        "China",
        "Italy (Imola)",
        "Miami",
        "Spain",
        "Monaco",
        "Canada",
        "Azerbaijan",
        "UK",
        "Austria",
        "France",
        "Hungary",
        "Belgium",
        "Netherlands",
        "Italy (Monza)",
        "Singapore",
        "Japan",
        "USA",
        "Mexico",
        "Brazil",
        "Abu Dhabi",
        "Qatar",
    ]

    for track_name in canonical_tracks:
        coeffs = get_coefficient(track_name)

        rows.append(
            {
                "Track": track_name,
                "C(M)": coeffs.get("C(M)", 1.0),
                "C(A)": coeffs.get("C(A)", 1.05),
                "C(P)": coeffs.get("C(P)", 1.0),
                "Source": coeffs.get("source", "historical"),
            }
        )

    df = pd.DataFrame(rows)

    output_path = "data/track_characteristics.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path}")
    print(f"Total tracks: {len(df)}")

    # Print FastF1 data summary
    print("\n=== FastF1 C(P) Data ===")
    for track, data in FASTF1_DATA.items():
        print(
            f"{track}: C(P)={data['C(P)']} ({data['full_throttle_pct']}%, {data['years']})"
        )

    # Count sources
    fastf1_count = sum(1 for t in canonical_tracks if t in FASTF1_DATA)
    print(
        f"\nFastF1: {fastf1_count} tracks, Historical: {len(canonical_tracks) - fastf1_count - 1} tracks"
    )

    print("\n=== Spain Comparison ===")
    print(
        f"Reference: C(M)={SPAIN_REFERENCE['C(M)']}, C(A)={SPAIN_REFERENCE['C(A)']}, C(P)={SPAIN_REFERENCE['C(P)']}"
    )
    print(f"FastF1:   C(M)=1.0, C(A)=1.05, C(P)=1.05")

    return df


if __name__ == "__main__":
    generate_track_csv()
