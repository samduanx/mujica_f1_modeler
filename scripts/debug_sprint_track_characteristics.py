"""
Debug script to investigate track_characteristics issues in sprint race simulation.

Moved into scripts/ for repo cleanup.
"""

import sys
import os

# Add project root to path
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd


def get_track_characteristics():
    try:
        df = pd.read_csv("data/track_characteristics.csv")
        track_chars = {}
        for _, row in df.iterrows():
            track_name = row["Track"].lower()
            cm = row.get("C(M)", 1.0)
            ca = row.get("C(A)", 1.0)
            cp = row.get("C(P)", 1.0)

            abrasion = min(1.0, (cm - 0.9) * 10 + 0.3) if cm else 0.5
            grip = max(0.3, 1.0 - (ca - 1.0) * 5) if ca else 0.7

            track_chars[track_name] = {
                "abrasion": round(abrasion, 2),
                "grip": round(grip, 2),
                "C(M)": cm,
                "C(A)": ca,
                "C(P)": cp,
            }
        return track_chars
    except Exception as e:
        print(f"Error loading track characteristics: {e}")
        return {}


def calculate_wear_compensation(abrasion_level: float) -> float:
    normalized_abrasion = (abrasion_level - 3) / 2.0
    wear_factor = 1 + 0.2 * normalized_abrasion
    return wear_factor


def main():
    print("=" * 70)
    print("TRACK CHARACTERISTICS DEBUG FOR SPRINT RACES")
    print("=" * 70)

    sprint_tracks = {
        "Imola": "imola",
        "Austria": "austria",
        "Sao_Paulo": "brazil",
    }

    all_track_chars = get_track_characteristics()

    print("\n1. TRACK CHARACTERISTICS FROM CSV:")
    print("-" * 70)
    print(
        f"{'Track':<15} {'CSV Name':<20} {'C(M)':<8} {'C(A)':<8} {'C(P)':<8} {'Abrasion':<10} {'Grip':<8}"
    )
    print("-" * 70)

    for track, gp_name in sprint_tracks.items():
        if gp_name in all_track_chars:
            chars = all_track_chars[gp_name]
            print(
                f"{track:<15} {gp_name:<20} {chars['C(M)']:<8.2f} {chars['C(A)']:<8.2f} {chars['C(P)']:<8.2f} {chars['abrasion']:<10.2f} {chars['grip']:<8.2f}"
            )
        else:
            print(f"{track:<15} {gp_name:<20} NOT FOUND")

    print("\n2. ABRASION VALUE RANGE ANALYSIS:")
    print("-" * 70)
    all_abrasions = [v["abrasion"] for v in all_track_chars.values()]
    all_grips = [v["grip"] for v in all_track_chars.values()]
    print(
        f"All tracks - Abrasion range: {min(all_abrasions):.2f} to {max(all_abrasions):.2f}"
    )
    print(f"All tracks - Grip range: {min(all_grips):.2f} to {max(all_grips):.2f}")

    print("\n3. DEFAULT VALUES USED IN CODE:")
    print("-" * 70)
    print(f"In calculate_degradation_with_cliff() - default abrasion: 5")
    print(
        f"In SprintRaceSimulator.__init__() - default track_chars: {{'abrasion': 0.5, 'grip': 0.7}}"
    )

    print("\n4. WEAR COMPENSATION CALCULATION:")
    print("-" * 70)
    print(f"{'Abrasion':<12} {'Normalized':<15} {'Wear Factor':<15} {'Notes'}")
    print("-" * 70)

    test_values = [0.3, 0.5, 0.7, 1.0, 5]
    for abrasion in test_values:
        normalized = (abrasion - 3) / 2.0
        wear_factor = 1 + 0.2 * normalized
        notes = ""
        if abrasion == 0.5:
            notes = "<- SprintRaceSimulator default"
        elif abrasion == 5:
            notes = "<- calculate_degradation_with_cliff default"
        elif abrasion == 1.0:
            notes = "<- Max from track_characteristics"
        print(f"{abrasion:<12.1f} {normalized:<15.2f} {wear_factor:<15.2f} {notes}")

    print("\n5. POTENTIAL ISSUES IDENTIFIED:")
    print("-" * 70)
    print("ISSUE 1: Numerical Range Mismatch")
    print("  - get_track_characteristics() returns abrasion in range [0.3, 1.0]")
    print("  - calculate_wear_compensation() expects abrasion around 3-5 range")
    print("  - calculate_degradation_with_cliff() uses default abrasion = 5")
    print()
    print("  Impact: With abrasion=0.5 (typical track):")
    print(f"    - normalized = (0.5 - 3) / 2.0 = -1.25")
    print(f"    - wear_factor = 1 + 0.2 * (-1.25) = 0.75 (25% LESS degradation)")
    print()
    print("  With abrasion=5 (default in degradation function):")
    print(f"    - normalized = (5 - 3) / 2.0 = 1.0")
    print(f"    - wear_factor = 1 + 0.2 * 1.0 = 1.2 (20% MORE degradation)")
    print()
    print("  This means tracks with missing characteristics get 60% more degradation!")
    print(f"    - 1.2 / 0.75 = 1.6 (60% difference)")

    print("\n6. SPRINT TRACK SPECIFIC CHECK:")
    print("-" * 70)
    for track, gp_name in sprint_tracks.items():
        chars = all_track_chars.get(gp_name, {"abrasion": 0.5, "grip": 0.7})
        abrasion = chars["abrasion"]
        wear_factor = calculate_wear_compensation(abrasion)
        print(f"{track}: abrasion={abrasion:.2f} -> wear_factor={wear_factor:.2f}")

    print("\n" + "=" * 70)
    print("CONCLUSION: Numerical range mismatch confirmed!")
    print("=" * 70)

    print("""
The track_characteristics.csv provides values that get converted to 0.3-1.0 range,
but calculate_wear_compensation() expects values in 3-5 range.

Additionally, there's a bug in sprint_simulator.py line 269:
  calculate_base_lap_time(r_value, self.track_name.lower())

This is missing the required 'team_pr' argument.
""")


if __name__ == "__main__":
    main()
