#!/usr/bin/env python3
"""
Incident System Calibration Tool with FastF1 Data.

Fetches real race incidents (yellow/red flags, VSC, SC) from FastF1
and compares with our simulation to calibrate incident probabilities.
"""

import sys
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, "src")

try:
    import fastf1
    import fastf1.plotting
    import pandas as pd
    import numpy as np

    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False
    print("Warning: FastF1 not available. Install with: pip install fastf1")


@dataclass
class RealIncident:
    """Represents a real incident from FastF1 data"""
    lap: int
    time_seconds: float
    incident_type: str  # "yellow", "double_yellow", "vsc", "sc", "red_flag"
    sector: Optional[int] = None
    driver: Optional[str] = None
    description: str = ""
    duration_seconds: Optional[float] = None  # How long the flag was active


@dataclass
class CalibrationData:
    """Collected calibration data from real races"""
    # Incident counts
    total_incidents: int = 0
    yellow_flags: int = 0
    double_yellows: int = 0
    vsc_count: int = 0
    sc_count: int = 0
    red_flags: int = 0
    
    # Incident timing
    incidents_by_lap: Dict[int, int] = None
    incidents_by_sector: Dict[int, int] = None
    
    # Duration statistics
    yellow_durations: List[float] = None
    vsc_durations: List[float] = None
    sc_durations: List[float] = None
    
    # Lap analysis
    avg_incidents_per_lap: float = 0.0
    incident_lap_positions: List[float] = None  # Position in lap (0-100%)
    
    def __post_init__(self):
        if self.incidents_by_lap is None:
            self.incidents_by_lap = {}
        if self.incidents_by_sector is None:
            self.incidents_by_sector = {}
        if self.yellow_durations is None:
            self.yellow_durations = []
        if self.vsc_durations is None:
            self.vsc_durations = []
        if self.sc_durations is None:
            self.sc_durations = []
        if self.incident_lap_positions is None:
            self.incident_lap_positions = []


class FastF1IncidentExtractor:
    """Extract incidents from FastF1 session data"""
    
    def __init__(self):
        self.incidents: List[RealIncident] = []
        
    def load_session(self, year: int, gp: str, session_type: str = "R"):
        """Load a FastF1 session"""
        if not FASTF1_AVAILABLE:
            return None
            
        fastf1.Cache.enable_cache("f1_cache")
        fastf1.set_log_level("ERROR")
        
        try:
            session = fastf1.get_session(year, gp, session_type)
            session.load(laps=True, telemetry=True, weather=True)
            return session
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
    
    def extract_from_lap_data(self, session) -> List[RealIncident]:
        """Extract incidents from lap timing data"""
        if session is None:
            return []
            
        incidents = []
        
        try:
            # Get race control messages if available
            if hasattr(session, 'race_control_messages'):
                rc_msgs = session.race_control_messages
                if rc_msgs is not None and len(rc_msgs) > 0:
                    for _, msg in rc_msgs.iterrows():
                        incident = self._parse_race_control_message(msg)
                        if incident:
                            incidents.append(incident)
            
            # Analyze lap times for anomalies (safety car periods)
            if hasattr(session, 'laps'):
                incidents.extend(self._detect_sc_periods_from_laps(session.laps))
            
            # Check session status messages
            if hasattr(session, 'session_status'):
                status_data = session.session_status
                if status_data is not None:
                    incidents.extend(self._extract_from_session_status(status_data))
                    
        except Exception as e:
            print(f"Error extracting incidents: {e}")
            
        return incidents
    
    def _parse_race_control_message(self, msg: pd.Series) -> Optional[RealIncident]:
        """Parse a race control message for incidents"""
        try:
            message = str(msg.get('Message', '')).lower()
            
            # Skip non-incident messages
            if any(x in message for x in ['drs', 'drs enabled', 'drs disabled', 'track clear']):
                return None
            
            incident_type = None
            sector = None
            
            # Determine incident type
            if 'red flag' in message:
                incident_type = 'red_flag'
            elif 'safety car' in message or 'sc' in message:
                if 'virtual' in message or 'vsc' in message:
                    incident_type = 'vsc'
                else:
                    incident_type = 'sc'
            elif 'double yellow' in message or 'double waved yellow' in message:
                incident_type = 'double_yellow'
            elif 'yellow' in message:
                incident_type = 'yellow'
            
            if incident_type is None:
                return None
            
            # Extract sector info
            if 'sector 1' in message or 'sector1' in message:
                sector = 1
            elif 'sector 2' in message or 'sector2' in message:
                sector = 2
            elif 'sector 3' in message or 'sector3' in message:
                sector = 3
            
            # Get time
            time_seconds = 0
            if 'Time' in msg:
                t = msg['Time']
                if isinstance(t, timedelta):
                    time_seconds = t.total_seconds()
                elif isinstance(t, (int, float)):
                    time_seconds = float(t)
            
            return RealIncident(
                lap=0,  # Will be determined from session
                time_seconds=time_seconds,
                incident_type=incident_type,
                sector=sector,
                description=message,
            )
        except Exception as e:
            return None
    
    def _detect_sc_periods_from_laps(self, laps: pd.DataFrame) -> List[RealIncident]:
        """Detect safety car periods by analyzing lap times"""
        incidents = []
        
        try:
            # Group by lap number and calculate average lap time
            lap_times = laps.groupby('LapNumber')['LapTime'].apply(
                lambda x: x.dt.total_seconds().mean() if len(x) > 0 else None
            )
            
            # Detect abnormally slow laps (SC/VSC periods)
            # Normal lap time varies by track, but SC is typically ~140-150% slower
            if len(lap_times) > 0:
                median_lap = lap_times.median()
                threshold = median_lap * 1.3  # 30% slower suggests SC/VSC
                
                for lap_num, lap_time in lap_times.items():
                    if lap_time > threshold and not pd.isna(lap_time):
                        # Check if it's a consistent slow period
                        incidents.append(RealIncident(
                            lap=int(lap_num),
                            time_seconds=lap_time,
                            incident_type='sc_detected',
                            description=f"Detected SC/VSC - lap time {lap_time:.1f}s (threshold: {threshold:.1f}s)"
                        ))
                        
        except Exception as e:
            pass
            
        return incidents
    
    def _extract_from_session_status(self, status_data) -> List[RealIncident]:
        """Extract incidents from session status data"""
        incidents = []
        
        try:
            for _, status in status_data.iterrows():
                status_type = str(status.get('Status', '')).lower()
                
                if status_type in ['red', 'red flag', 'stopped']:
                    incidents.append(RealIncident(
                        lap=0,
                        time_seconds=0,
                        incident_type='red_flag',
                        description=f"Session status: {status_type}"
                    ))
                elif status_type in ['sc', 'safety car']:
                    incidents.append(RealIncident(
                        lap=0,
                        time_seconds=0,
                        incident_type='sc',
                        description=f"Session status: {status_type}"
                    ))
                    
        except Exception as e:
            pass
            
        return incidents


class IncidentCalibrator:
    """Calibrate incident system against real data"""
    
    def __init__(self):
        self.calibration_data: Dict[str, CalibrationData] = {}
        self.extractor = FastF1IncidentExtractor()
        
    def calibrate_race(self, year: int, gp: str, session_type: str = "R") -> CalibrationData:
        """Calibrate using a specific race"""
        print(f"\n{'=' * 60}")
        print(f"Calibrating {year} {gp} {session_type}")
        print(f"{'=' * 60}")
        
        # Load session
        session = self.extractor.load_session(year, gp, session_type)
        if session is None:
            print(f"Failed to load session")
            return CalibrationData()
        
        # Extract incidents
        incidents = self.extractor.extract_from_lap_data(session)
        print(f"Found {len(incidents)} incidents")
        
        # Build calibration data
        data = self._build_calibration_data(incidents, session)
        
        # Store and display
        key = f"{year}_{gp}_{session_type}"
        self.calibration_data[key] = data
        self._display_calibration(data)
        
        return data
    
    def _build_calibration_data(self, incidents: List[RealIncident], session) -> CalibrationData:
        """Build calibration data from extracted incidents"""
        data = CalibrationData()
        data.total_incidents = len(incidents)
        
        for inc in incidents:
            # Count by type
            if inc.incident_type == 'yellow':
                data.yellow_flags += 1
            elif inc.incident_type == 'double_yellow':
                data.double_yellows += 1
            elif inc.incident_type in ['vsc', 'vsc_detected']:
                data.vsc_count += 1
            elif inc.incident_type in ['sc', 'sc_detected']:
                data.sc_count += 1
            elif inc.incident_type == 'red_flag':
                data.red_flags += 1
            
            # Count by lap
            if inc.lap > 0:
                data.incidents_by_lap[inc.lap] = data.incidents_by_lap.get(inc.lap, 0) + 1
            
            # Count by sector
            if inc.sector:
                data.incidents_by_sector[inc.sector] = data.incidents_by_sector.get(inc.sector, 0) + 1
        
        # Calculate statistics
        if len(incidents) > 0:
            # Try to get total laps
            total_laps = 70  # Default
            if hasattr(session, 'laps'):
                total_laps = int(session.laps['LapNumber'].max())
            
            data.avg_incidents_per_lap = len(incidents) / total_laps
            
        return data
    
    def _display_calibration(self, data: CalibrationData):
        """Display calibration results"""
        print(f"\nIncident Summary:")
        print(f"  Total: {data.total_incidents}")
        print(f"  Yellow flags: {data.yellow_flags}")
        print(f"  Double yellows: {data.double_yellows}")
        print(f"  VSC periods: {data.vsc_count}")
        print(f"  SC periods: {data.sc_count}")
        print(f"  Red flags: {data.red_flags}")
        
        if data.incidents_by_sector:
            print(f"\nBy Sector:")
            for sector, count in sorted(data.incidents_by_sector.items()):
                print(f"  Sector {sector}: {count}")
        
        print(f"\nRecommendations for simulation:")
        self._generate_recommendations(data)
    
    def _generate_recommendations(self, data: CalibrationData):
        """Generate probability recommendations"""
        # Base probabilities based on real data
        if data.total_incidents == 0:
            print("  No incidents detected - use default probabilities")
            return
        
        # Calculate per-lap probabilities (assuming 70 lap race)
        laps = 70
        
        yellow_prob = data.yellow_flags / laps
        double_yellow_prob = data.double_yellows / laps
        vsc_prob = data.vsc_count / laps
        sc_prob = data.sc_count / laps
        red_flag_prob = data.red_flags / laps
        
        print(f"  Yellow flag probability per lap: ~{yellow_prob:.3f}")
        print(f"  Double yellow probability per lap: ~{double_yellow_prob:.3f}")
        print(f"  VSC probability per race: ~{vsc_prob:.2f} (expected {data.vsc_count})")
        print(f"  SC probability per race: ~{sc_prob:.2f} (expected {data.sc_count})")
        print(f"  Red flag probability per race: ~{red_flag_prob:.2f}")
        
        # Sector distribution
        if data.incidents_by_sector:
            total_with_sector = sum(data.incidents_by_sector.values())
            print(f"\n  Sector incident distribution:")
            for sector in [1, 2, 3]:
                count = data.incidents_by_sector.get(sector, 0)
                pct = (count / total_with_sector * 100) if total_with_sector > 0 else 0
                print(f"    Sector {sector}: {pct:.1f}%")


def analyze_historical_races():
    """Analyze multiple historical races for calibration"""
    calibrator = IncidentCalibrator()
    
    # Races known for incidents (for calibration)
    races_to_analyze = [
        (2023, "Baku", "R"),      # Multiple SC/VSC periods
        (2023, "Singapore", "R"), # Rain, multiple incidents
        (2023, "Qatar", "R"),     # Hot conditions, tire issues
        (2024, "Australia", "R"), # Multiple red flags
        (2024, "Imola", "R"),     # Changeable conditions
        (2022, "Japan", "R"),     # Rain, long red flag
        (2021, "Belgium", "R"),   # Rain, very short race
        (2021, "Baku", "R"),      # Multiple incidents
        (2020, "Italy", "R"),     # SC restart incidents
        (2019, "Germany", "R"),   # Rain chaos
    ]
    
    print("=" * 70)
    print("INCIDENT SYSTEM CALIBRATION WITH FASTF1")
    print("=" * 70)
    
    for year, gp, session_type in races_to_analyze:
        try:
            calibrator.calibrate_race(year, gp, session_type)
        except Exception as e:
            print(f"Error analyzing {year} {gp}: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("CALIBRATION SUMMARY")
    print("=" * 70)
    
    if not calibrator.calibration_data:
        print("No calibration data collected")
        return
    
    # Aggregate statistics
    total_yellow = sum(d.yellow_flags for d in calibrator.calibration_data.values())
    total_double = sum(d.double_yellows for d in calibrator.calibration_data.values())
    total_vsc = sum(d.vsc_count for d in calibrator.calibration_data.values())
    total_sc = sum(d.sc_count for d in calibrator.calibration_data.values())
    total_red = sum(d.red_flags for d in calibrator.calibration_data.values())
    num_races = len(calibrator.calibration_data)
    
    print(f"\nAnalyzed {num_races} races")
    print(f"\nAverage per race:")
    print(f"  Yellow flags: {total_yellow / num_races:.1f}")
    print(f"  Double yellows: {total_double / num_races:.1f}")
    print(f"  VSC periods: {total_vsc / num_races:.1f}")
    print(f"  SC periods: {total_sc / num_races:.1f}")
    print(f"  Red flags: {total_red / num_races:.1f}")
    
    print(f"\nRecommended simulation parameters:")
    print(f"  yellow_flag_prob_per_lap: {total_yellow / (num_races * 70):.4f}")
    print(f"  double_yellow_prob_per_lap: {total_double / (num_races * 70):.4f}")
    print(f"  vsc_prob_per_race: {total_vsc / num_races:.2f}")
    print(f"  sc_prob_per_race: {total_sc / num_races:.2f}")
    print(f"  red_flag_prob_per_race: {total_red / num_races:.2f}")


def main():
    """Main entry point"""
    if not FASTF1_AVAILABLE:
        print("ERROR: FastF1 is required for calibration")
        print("Install with: pip install fastf1")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Calibrate specific race
        year = int(sys.argv[1])
        gp = sys.argv[2]
        session_type = sys.argv[3] if len(sys.argv) > 3 else "R"
        
        calibrator = IncidentCalibrator()
        calibrator.calibrate_race(year, gp, session_type)
    else:
        # Analyze historical races
        analyze_historical_races()


if __name__ == "__main__":
    main()
