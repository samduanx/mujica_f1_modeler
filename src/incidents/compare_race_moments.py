#!/usr/bin/env python3
"""
Time-Point to Time-Point Race Comparison Tool.

Compares simulated incidents with real FastF1 data at specific time points
to debug and calibrate the incident system.
"""

import sys
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, "src")

try:
    import fastf1
    import fastf1.plotting
    import pandas as pd
    import numpy as np

    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False
    print("Warning: FastF1 not available")

from incidents.red_flag import RedFlagManager, RaceEndReason
from incidents.sector_flags import SectorFlagManager, SectorFlag
from incidents.vsc_sc import SafetyResponseManager


@dataclass
class RaceMoment:
    """Represents a specific moment in the race"""

    time_seconds: float
    lap: int
    lap_progress: float  # 0.0 to 1.0
    real_incidents: List[str] = field(default_factory=list)
    simulated_incidents: List[str] = field(default_factory=list)
    real_positions: Dict[str, int] = field(default_factory=dict)
    sim_positions: Dict[str, int] = field(default_factory=dict)


@dataclass
class MomentComparison:
    """Comparison between real and simulated at a moment"""

    time_seconds: float
    lap: int
    real_state: Dict
    simulated_state: Dict
    discrepancies: List[str] = field(default_factory=list)


class RaceMomentComparator:
    """Compare real race moments with simulation"""

    def __init__(self, year: int, gp: str, session_type: str = "R"):
        self.year = year
        self.gp = gp
        self.session_type = session_type
        self.session = None
        self.real_data = None

        if FASTF1_AVAILABLE:
            self._load_session()

    def _load_session(self):
        """Load FastF1 session"""
        fastf1.Cache.enable_cache("f1_cache")
        fastf1.set_log_level("ERROR")

        try:
            self.session = fastf1.get_session(self.year, self.gp, self.session_type)
            self.session.load(laps=True, telemetry=True, weather=True)
            print(f"Loaded {self.year} {self.gp} {self.session_type}")
        except Exception as e:
            print(f"Error loading session: {e}")
            self.session = None

    def extract_real_moments(self, interval_seconds: float = 60.0) -> List[RaceMoment]:
        """Extract real race moments at regular intervals"""
        if self.session is None:
            return []

        moments = []

        try:
            # Get race control messages with timestamps
            if hasattr(self.session, "race_control_messages"):
                rc_msgs = self.session.race_control_messages

                # Process messages to find incident moments
                for _, msg in rc_msgs.iterrows():
                    time_sec = self._get_time_seconds(msg.get("Time"))
                    if time_sec is None:
                        continue

                    message = str(msg.get("Message", "")).lower()

                    # Only process incident-related messages
                    if not any(
                        x in message
                        for x in ["yellow", "red", "safety car", "vsc", "clear"]
                    ):
                        continue

                    lap = self._time_to_lap(time_sec)
                    progress = self._time_to_lap_progress(time_sec)

                    moment = RaceMoment(
                        time_seconds=time_sec,
                        lap=lap,
                        lap_progress=progress,
                        real_incidents=[message],
                    )
                    moments.append(moment)

            # Sort by time
            moments.sort(key=lambda m: m.time_seconds)

        except Exception as e:
            print(f"Error extracting moments: {e}")

        return moments

    def _get_time_seconds(self, time_value) -> Optional[float]:
        """Convert time value to seconds"""
        if time_value is None:
            return None
        if isinstance(time_value, timedelta):
            return time_value.total_seconds()
        if isinstance(time_value, (int, float)):
            return float(time_value)
        return None

    def _time_to_lap(self, time_seconds: float) -> int:
        """Convert race time to lap number"""
        if self.session is None or not hasattr(self.session, "laps"):
            return 0

        try:
            # Find which lap this time falls into
            laps = self.session.laps
            # Use lap start times to determine current lap
            return 1  # Simplified - would need proper lap timing data
        except:
            return 0

    def _time_to_lap_progress(self, time_seconds: float) -> float:
        """Convert race time to lap progress (0-1)"""
        # This would need proper lap timing data
        return 0.0

    def get_real_flags_at_time(self, time_seconds: float) -> Dict[str, str]:
        """Get flag status at a specific time"""
        flags = {
            "sector_1": "green",
            "sector_2": "green",
            "sector_3": "green",
            "global": "green",
        }

        if self.session is None or not hasattr(self.session, "race_control_messages"):
            return flags

        try:
            rc_msgs = self.session.race_control_messages

            # Find the most recent message before this time
            for _, msg in rc_msgs.iterrows():
                msg_time = self._get_time_seconds(msg.get("Time"))
                if msg_time is None or msg_time > time_seconds:
                    continue

                message = str(msg.get("Message", "")).lower()

                # Update flags based on message
                if "double yellow" in message:
                    if "sector 1" in message:
                        flags["sector_1"] = "double_yellow"
                    elif "sector 2" in message:
                        flags["sector_2"] = "double_yellow"
                    elif "sector 3" in message:
                        flags["sector_3"] = "double_yellow"
                elif "yellow" in message:
                    if "sector 1" in message:
                        flags["sector_1"] = "yellow"
                    elif "sector 2" in message:
                        flags["sector_2"] = "yellow"
                    elif "sector 3" in message:
                        flags["sector_3"] = "yellow"
                elif "red flag" in message:
                    flags["global"] = "red"
                elif "safety car" in message:
                    flags["global"] = "sc"
                elif "virtual" in message:
                    flags["global"] = "vsc"
                elif "track clear" in message:
                    # Reset flags
                    if "sector 1" in message:
                        flags["sector_1"] = "green"
                    elif "sector 2" in message:
                        flags["sector_2"] = "green"
                    elif "sector 3" in message:
                        flags["sector_3"] = "green"

        except Exception as e:
            pass

        return flags

    def compare_moment(
        self,
        time_seconds: float,
        sim_sector_manager: SectorFlagManager,
        sim_safety_manager: SafetyResponseManager,
    ) -> MomentComparison:
        """Compare real and simulated state at a specific time"""

        # Get real state
        real_flags = self.get_real_flags_at_time(time_seconds)

        # Get simulated state
        sim_sector_state = (
            sim_sector_manager.get_summary() if sim_sector_manager else {}
        )
        sim_safety_state = {
            "vsc_active": sim_safety_manager.vsc.is_active
            if sim_safety_manager
            else False,
            "sc_active": sim_safety_manager.safety_car.is_active
            if sim_safety_manager
            else False,
        }

        # Build comparison
        comparison = MomentComparison(
            time_seconds=time_seconds,
            lap=self._time_to_lap(time_seconds),
            real_state={
                "flags": real_flags,
            },
            simulated_state={
                "sector_flags": sim_sector_state,
                "safety": sim_safety_state,
            },
            discrepancies=[],
        )

        # Find discrepancies
        for sector_num in [1, 2, 3]:
            real_flag = real_flags.get(f"sector_{sector_num}", "green")
            sim_flag = sim_sector_state.get(sector_num, {}).get("flag", "GREEN")

            if real_flag != sim_flag.lower().replace("_", ""):
                comparison.discrepancies.append(
                    f"Sector {sector_num}: Real={real_flag}, Sim={sim_flag}"
                )

        return comparison

    def generate_comparison_report(
        self,
        moments: List[RaceMoment],
        sim_sector_manager: SectorFlagManager,
        sim_safety_manager: SafetyResponseManager,
    ) -> str:
        """Generate a detailed comparison report"""

        report = []
        report.append("=" * 70)
        report.append(f"RACE MOMENT COMPARISON: {self.year} {self.gp}")
        report.append("=" * 70)

        discrepancies_found = 0

        for moment in moments[:20]:  # Limit to first 20 moments for readability
            comparison = self.compare_moment(
                moment.time_seconds, sim_sector_manager, sim_safety_manager
            )

            report.append(
                f"\nTime: {self._format_time(moment.time_seconds)} | Lap {moment.lap}"
            )
            report.append(f"Real incidents: {moment.real_incidents}")

            if comparison.discrepancies:
                report.append("DISCREPANCIES:")
                for disc in comparison.discrepancies:
                    report.append(f"  - {disc}")
                discrepancies_found += 1
            else:
                report.append("✓ Match")

        report.append(f"\n{'=' * 70}")
        report.append(f"Total discrepancies: {discrepancies_found}/{len(moments)}")

        return "\n".join(report)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS.ms"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{mins:02d}:{secs:02d}.{ms:03d}"


class CalibrationReport:
    """Generate calibration report from comparison data"""

    @staticmethod
    def generate(comparisons: List[MomentComparison]) -> str:
        """Generate calibration report"""
        report = []
        report.append("=" * 70)
        report.append("CALIBRATION REPORT")
        report.append("=" * 70)

        # Calculate metrics
        total = len(comparisons)
        matches = sum(1 for c in comparisons if not c.discrepancies)
        accuracy = (matches / total * 100) if total > 0 else 0

        report.append(f"\nTotal moments compared: {total}")
        report.append(f"Matches: {matches}")
        report.append(f"Accuracy: {accuracy:.1f}%")

        # Discrepancy analysis
        sector_discrepancies = [0, 0, 0]  # Per sector
        for comp in comparisons:
            for disc in comp.discrepancies:
                if "Sector 1" in disc:
                    sector_discrepancies[0] += 1
                elif "Sector 2" in disc:
                    sector_discrepancies[1] += 1
                elif "Sector 3" in disc:
                    sector_discrepancies[2] += 1

        report.append(f"\nDiscrepancies by sector:")
        for i, count in enumerate(sector_discrepancies, 1):
            report.append(f"  Sector {i}: {count}")

        # Recommendations
        report.append(f"\nRecommendations:")
        if accuracy < 50:
            report.append("  - Significant calibration needed")
            report.append("  - Consider adjusting incident trigger thresholds")
        elif accuracy < 80:
            report.append("  - Moderate calibration needed")
            report.append("  - Fine-tune sector flag durations")
        else:
            report.append("  - Good accuracy, minor fine-tuning may help")

        return "\n".join(report)


def example_comparison():
    """Example: Compare simulated race with real 2023 Baku"""
    print("=" * 70)
    print("EXAMPLE: Race Moment Comparison")
    print("=" * 70)

    # Create comparator
    comparator = RaceMomentComparator(2023, "Baku", "R")

    if comparator.session is None:
        print("Failed to load session")
        return

    # Extract real moments
    moments = comparator.extract_real_moments()
    print(f"\nExtracted {len(moments)} incident moments from real race")

    # Create simulated managers (empty for comparison)
    from incidents.sector_flags import SectorFlagManager
    from incidents.vsc_sc import SafetyResponseManager

    sector_manager = SectorFlagManager(num_sectors=3)
    safety_manager = SafetyResponseManager(base_lap_time=90.0)  # Baku lap time ~90s

    # Generate report
    report = comparator.generate_comparison_report(
        moments, sector_manager, safety_manager
    )
    print(report)

    # Calibration suggestions
    print("\n" + "=" * 70)
    print("CALIBRATION SUGGESTIONS")
    print("=" * 70)
    print("""
Based on real race data, adjust simulation parameters:

1. Yellow Flag Probability:
   - Current: Check your config
   - Target: ~0.08 per lap (from calibration data)

2. Safety Car Frequency:
   - Target: ~5.3 periods per incident-heavy race
   - For normal races: ~1-2 periods

3. Sector Incident Distribution:
   - Varies by track (check calibration output)
   - Adjust sector-specific probabilities

4. Red Flag Threshold:
   - Real data shows ~1.4 red flags per incident-heavy race
   - For normal races: ~0.1-0.2 per race
""")


def main():
    """Main entry point"""
    if not FASTF1_AVAILABLE:
        print("ERROR: FastF1 is required")
        sys.exit(1)

    if len(sys.argv) > 1:
        year = int(sys.argv[1])
        gp = sys.argv[2]
        comparator = RaceMomentComparator(year, gp)
        moments = comparator.extract_real_moments()
        print(f"Found {len(moments)} incident moments")

        for moment in moments[:10]:
            print(
                f"Time: {moment.time_seconds:.0f}s | Lap {moment.lap}: {moment.real_incidents}"
            )
    else:
        example_comparison()


if __name__ == "__main__":
    main()
