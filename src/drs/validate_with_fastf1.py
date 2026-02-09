#!/usr/bin/env python3
"""
DRS Zone Validation Tool

Fetches real DRS zone and sector data from FastF1 to validate
and calibrate the simulation configurations.
"""

import sys

sys.path.insert(0, "src")

try:
    import fastf1
    import fastf1.plotting
    import pandas as pd

    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False
    print("Warning: FastF1 not available. Install with: pip install fastf1")

from drs.zones.monaco_2024 import get_config as get_monaco_config
from drs.zones.monza_2024 import get_config as get_monza_config
from drs.zones.spain_2024 import get_config as get_spain_config
from drs.zones.bahrain_2024 import get_config as get_bahrain_config


def get_fastf1_session(year: int, grand_prix: str, session_type: str = "Q"):
    """Fetch a FastF1 session for analysis"""
    if not FASTF1_AVAILABLE:
        return None

    fastf1.Cache.enable_cache("f1_cache")
    fastf1.set_log_level("ERROR")

    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load()
        return session
    except Exception as e:
        print(f"Error loading session: {e}")
        return None


def get_sector_times(session):
    """Extract sector times from session data"""
    if session is None:
        return None

    try:
        laps = session.laps
        if laps is None or len(laps) == 0:
            return None

        # Get fastest lap for each driver
        fastest_laps = laps.groupby("Driver")["LapTime"].min()

        # Get sector times
        sector_times = laps.groupby("Driver").agg(
            {
                "Sector1Time": "min",
                "Sector2Time": "min",
                "Sector3Time": "min",
                "LapTime": "min",
            }
        )

        return {"fastest_laps": fastest_laps, "sector_times": sector_times}
    except Exception as e:
        print(f"Error extracting sector times: {e}")
        return None


def analyze_drs_zones(session):
    """Analyze DRS zone data from FastF1"""
    if session is None:
        return None

    try:
        # Get car data for telemetry
        laps = session.laps
        if laps is None:
            return None

        # Try to get telemetry data with DRS info
        sample_lap = laps[laps["Driver"] == laps["Driver"].iloc[0]].iloc[0]

        # Get telemetry for fastest lap
        fastest_driver = laps.loc[laps["LapTime"].idxmin(), "Driver"]
        tel = laps[laps["Driver"] == fastest_driver].iloc[0].get_telemetry()

        if tel is None:
            return None

        # Check for DRS data
        has_drs = "DRS" in tel.columns

        return {
            "has_drs_data": has_drs,
            "telemetry_columns": list(tel.columns) if tel is not None else [],
            "fastest_driver": fastest_driver,
        }
    except Exception as e:
        print(f"Error analyzing DRS zones: {e}")
        return None


def compare_config_with_fastf1(
    config_name: str, config_getter, year: int = 2024, gp: str = None
):
    """Compare our config with FastF1 data"""
    if gp is None:
        gp = config_name

    print(f"\n{'=' * 60}")
    print(f"Comparing {config_name} with FastF1 {year} data")
    print(f"{'=' * 60}")

    # Get our configuration
    config = config_getter()

    print(f"\nOur Configuration:")
    print(f"  Track: {config.track_name}")
    print(f"  Distance: {config.total_distance}m")
    print(f"  Base lap time: {config.calculate_base_lap_time():.1f}s")
    print(f"  Sectors:")
    for i, sector in config.sectors.items():
        print(f"    Sector {i}: {sector.base_time}s")

    # Get FastF1 data
    if not FASTF1_AVAILABLE:
        print(f"\n[INFO] FastF1 not available. Install to get real data.")
        print(f"[INFO] Expected lap time: ~{config.calculate_base_lap_time()}s")
        return

    session = get_fastf1_session(year, gp)
    if session is None:
        print(f"\n[INFO] Could not load FastF1 session for {gp}")
        return

    sector_data = get_sector_times(session)
    if sector_data:
        print(f"\nFastF1 Sector Times (2024):")
        avg_sector1 = sector_data["sector_times"]["Sector1Time"].mean().total_seconds()
        avg_sector2 = sector_data["sector_times"]["Sector2Time"].mean().total_seconds()
        avg_sector3 = sector_data["sector_times"]["Sector3Time"].mean().total_seconds()
        avg_lap = sector_data["fastest_laps"].mean().total_seconds()

        print(f"  Sector 1: {avg_sector1:.1f}s")
        print(f"  Sector 2: {avg_sector2:.1f}s")
        print(f"  Sector 3: {avg_sector3:.1f}s")
        print(f"  Average lap: {avg_lap:.1f}s")

        print(f"\nComparison:")
        our_s1 = config.sectors[1].base_time
        our_s2 = config.sectors[2].base_time
        our_s3 = config.sectors[3].base_time
        our_total = config.calculate_base_lap_time()

        print(
            f"  Sector 1: Ours={our_s1:.1f}s vs FastF1={avg_sector1:.1f}s (diff={our_s1 - avg_sector1:+.1f}s)"
        )
        print(
            f"  Sector 2: Ours={our_s2:.1f}s vs FastF1={avg_sector2:.1f}s (diff={our_s2 - avg_sector2:+.1f}s)"
        )
        print(
            f"  Sector 3: Ours={our_s3:.1f}s vs FastF1={avg_sector3:.1f}s (diff={our_s3 - avg_sector3:+.1f}s)"
        )
        print(
            f"  Total: Ours={our_total:.1f}s vs FastF1={avg_lap:.1f}s (diff={our_total - avg_lap:+.1f}s)"
        )

    # DRS zone analysis
    drs_analysis = analyze_drs_zones(session)
    if drs_analysis:
        print(f"\nDRS Analysis:")
        print(f"  Has DRS telemetry: {drs_analysis['has_drs_data']}")
        print(f"  Fastest driver: {drs_analysis['fastest_driver']}")


def run_all_validations():
    """Run validations for all configured tracks"""
    print("=" * 70)
    print("DRS SYSTEM VALIDATION WITH FASTF1 DATA")
    print("=" * 70)

    tracks = [
        ("Monaco", get_monaco_config),
        ("Monza", get_monza_config),
        ("Spain", get_spain_config),
        ("Bahrain", get_bahrain_config),
    ]

    for name, config_getter in tracks:
        try:
            compare_config_with_fastf1(name, config_getter)
        except Exception as e:
            print(f"Error validating {name}: {e}")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        track_name = sys.argv[1].title()
        tracks = {
            "Monaco": get_monaco_config,
            "Monza": get_monza_config,
            "Spain": get_spain_config,
            "Bahrain": get_bahrain_config,
        }
        if track_name in tracks:
            compare_config_with_fastf1(track_name, tracks[track_name])
        else:
            print(f"Unknown track: {track_name}")
            print(f"Available: {', '.join(tracks.keys())}")
    else:
        run_all_validations()


if __name__ == "__main__":
    main()
