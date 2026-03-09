"""
Practice Weekend Simulator Module

Simulates complete practice weekends (normal or sprint) with setup tuning,
parc fermé management, and R rating export for qualifying/race integration.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from .types import (
    WeekendType,
    WeekendResults,
    PracticeSessionType,
    PracticeReport,
    RRatingExport,
    SetupTuningResult,
)
from .session import PracticeSessionManager
from .parc_ferme import ParcFermeManager, ParcFermeCoordinator
from .setup_tuning import SetupTuningManager


class PracticeWeekendSimulator:
    """
    Simulates a complete practice weekend.
    
    Handles both normal weekends (FP1, FP2, FP3) and sprint weekends (FP1 only).
    Manages parc fermé activation and R rating exports.
    """
    
    def __init__(
        self,
        track: str,
        track_base_time: float,
        weekend_type: WeekendType,
        drivers: List[str],
        driver_ratings: Dict[str, float],
        seed: Optional[int] = None,
    ):
        """
        Initialize weekend simulator.
        
        Args:
            track: Track name
            track_base_time: Base lap time for track
            weekend_type: NORMAL or SPRINT
            drivers: List of driver names
            driver_ratings: Dictionary of driver -> R rating
            seed: Optional random seed
        """
        self.track = track
        self.track_base_time = track_base_time
        self.weekend_type = weekend_type
        self.drivers = drivers
        self.driver_ratings = driver_ratings
        self.seed = seed
        
        # Results storage
        self.results = WeekendResults(
            weekend_type=weekend_type,
            track=track,
        )
        
        # Parc fermé
        self.parc_ferme_coordinator = ParcFermeCoordinator()
        
        # Setup tuning
        self.setup_manager = SetupTuningManager(seed=seed)
    
    def run_all_sessions(self) -> WeekendResults:
        """
        Run all practice sessions for the weekend.
        
        Returns:
            WeekendResults with all session data and parc fermé state
        """
        print(f"\n{'='*80}")
        print(f"PRACTICE WEEKEND SIMULATION")
        print(f"Track: {self.track}")
        print(f"Type: {self.weekend_type.value.upper()}")
        print(f"Drivers: {len(self.drivers)}")
        print(f"{'='*80}\n")
        
        if self.weekend_type == WeekendType.NORMAL:
            return self._run_normal_weekend()
        else:
            return self._run_sprint_weekend()
    
    def _run_normal_weekend(self) -> WeekendResults:
        """
        Run a normal race weekend (FP1, FP2, FP3).
        
        Normal weekend flow:
        FP1 → FP2 → FP3 → [PARC FERMÉ] → Qualifying → Race
        
        Setup effects are averaged across all three sessions.
        """
        print("Running NORMAL race weekend (FP1, FP2, FP3)\n")
        
        # FP1
        fp1_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP1,
            track=self.track,
            track_base_time=self.track_base_time,
            drivers=self.drivers,
            driver_ratings=self.driver_ratings,
            duration_minutes=60,
            seed=self.seed,
        )
        self.results.fp1 = fp1_manager.run_session()
        
        # FP2
        fp2_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP2,
            track=self.track,
            track_base_time=self.track_base_time,
            drivers=self.drivers,
            driver_ratings=self.driver_ratings,
            duration_minutes=60,
            seed=self.seed + 1 if self.seed else None,
        )
        self.results.fp2 = fp2_manager.run_session()
        
        # FP3
        fp3_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP3,
            track=self.track,
            track_base_time=self.track_base_time,
            drivers=self.drivers,
            driver_ratings=self.driver_ratings,
            duration_minutes=60,
            seed=self.seed + 2 if self.seed else None,
        )
        self.results.fp3 = fp3_manager.run_session()
        
        # Setup parc fermé after FP3
        parc_ferme = self.parc_ferme_coordinator.setup_normal_weekend(
            fp1_setups=self.results.fp1.setup_results,
            fp2_setups=self.results.fp2.setup_results,
            fp3_setups=self.results.fp3.setup_results,
        )
        self.results.parc_ferme_state = parc_ferme.state
        
        self._print_final_summary()
        
        return self.results
    
    def _run_sprint_weekend(self) -> WeekendResults:
        """
        Run a 2022 sprint race weekend.
        
        2022 Sprint weekend flow:
        FP1 → [PARC FERMÉ] → Qualifying → FP2 (under parc fermé) → Sprint → Race
        
        Setup effects are from FP1 ONLY (single chance for entire weekend).
        Parc fermé activates at Friday qualifying and stays active through Sunday.
        """
        print("Running 2022 SPRINT race weekend (FP1 only for setup)\n")
        print("⚠️  WARNING: 2022 Sprint weekends had RESTRICTIVE parc fermé rules!")
        print("   - Only FP1 allows setup changes")
        print("   - Parc fermé activates at Friday qualifying")
        print("   - Cars remain under parc fermé for FP2, Sprint, AND Race")
        print("   - Teams have ONE chance to get setup right!\n")
        
        # FP1 (ONLY setup session!)
        fp1_manager = PracticeSessionManager(
            session_type=PracticeSessionType.FP1,
            track=self.track,
            track_base_time=self.track_base_time,
            drivers=self.drivers,
            driver_ratings=self.driver_ratings,
            duration_minutes=60,
            seed=self.seed,
        )
        self.results.fp1 = fp1_manager.run_session()
        
        # Setup parc fermé after FP1 (before Friday qualifying)
        parc_ferme = self.parc_ferme_coordinator.setup_sprint_weekend_2022(
            fp1_setups=self.results.fp1.setup_results,
        )
        self.results.parc_ferme_state = parc_ferme.state
        
        self._print_final_summary()
        
        return self.results
    
    def _print_final_summary(self):
        """Print final weekend summary."""
        print(f"\n{'='*80}")
        print("WEEKEND PRACTICE SUMMARY")
        print(f"{'='*80}")
        
        # Print setup summary
        if self.results.parc_ferme_state:
            print("\nFinal Setup Effects (under Parc Fermé):")
            print("-" * 80)
            print(f"{'Driver':<20} {'R Delta':<10} {'Final R':<10}")
            print("-" * 80)
            
            # Sort by final R rating
            sorted_drivers = sorted(
                self.drivers,
                key=lambda d: self.driver_ratings[d] + self.results.parc_ferme_state.get_r_delta(d),
                reverse=True
            )
            
            for driver in sorted_drivers:
                base_r = self.driver_ratings[driver]
                delta = self.results.parc_ferme_state.get_r_delta(driver)
                final_r = base_r + delta
                print(f"{driver:<20} {delta:>+8.2f}  {final_r:>8.2f}")
        
        print(f"\n{'='*80}\n")
    
    def get_r_rating_deltas(self) -> Dict[str, float]:
        """
        Get R rating deltas for all drivers.
        
        Returns:
            Dictionary of driver -> delta
        """
        if self.results.parc_ferme_state:
            return self.results.parc_ferme_state.r_rating_deltas
        return {}
    
    def export_r_ratings(
        self,
        output_format: str = "dict",
    ) -> Any:
        """
        Export R rating deltas for integration with other systems.
        
        Args:
            output_format: "dict", "json", "list", or "csv"
            
        Returns:
            Exported data in requested format
        """
        if not self.results.parc_ferme_state:
            raise ValueError("No parc fermé state - run sessions first")
        
        exports = self.results.parc_ferme_state.export_r_ratings(self.driver_ratings)
        
        if output_format == "list":
            return exports
        
        elif output_format == "dict":
            return {
                exp.driver: {
                    "base_r": exp.base_r,
                    "delta": exp.delta,
                    "final_r": exp.final_r,
                    "setup_categories": exp.setup_categories,
                }
                for exp in exports
            }
        
        elif output_format == "json":
            data = {
                "weekend_type": self.weekend_type.value,
                "track": self.track,
                "timestamp": datetime.now().isoformat(),
                "driver_ratings": {
                    exp.driver: exp.to_dict()
                    for exp in exports
                },
            }
            return json.dumps(data, indent=2)
        
        elif output_format == "csv":
            lines = ["driver,base_r,delta,final_r,aero,susp,diff,brake,tyre"]
            for exp in exports:
                cats = exp.setup_categories
                line = (
                    f"{exp.driver},{exp.base_r:.2f},{exp.delta:.2f},{exp.final_r:.2f},"
                    f"{cats.get('aerodynamics', 3)},"
                    f"{cats.get('suspension', 3)},"
                    f"{cats.get('differential', 3)},"
                    f"{cats.get('brake_balance', 3)},"
                    f"{cats.get('tyre_pressure', 3)}"
                )
                lines.append(line)
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unknown output format: {output_format}")
    
    def save_r_ratings_to_file(self, filepath: str, format: str = "json"):
        """
        Save R ratings to a file.
        
        Args:
            filepath: Path to output file
            format: File format (json or csv)
        """
        data = self.export_r_ratings(output_format=format)
        
        with open(filepath, 'w') as f:
            f.write(data)
        
        print(f"R ratings exported to: {filepath}")
    
    def generate_report(self) -> PracticeReport:
        """
        Generate a comprehensive practice report.
        
        Returns:
            PracticeReport object
        """
        report = PracticeReport(
            weekend_type=self.weekend_type,
            track=self.track,
        )
        
        # Add session data
        if self.results.fp1:
            report.sessions["FP1"] = self.results.fp1
        if self.results.fp2:
            report.sessions["FP2"] = self.results.fp2
        if self.results.fp3:
            report.sessions["FP3"] = self.results.fp3
        
        # Add parc fermé info
        if self.results.parc_ferme_state:
            report.parc_ferme_active = self.results.parc_ferme_state.is_active
            report.parc_ferme_activated_after = self.results.parc_ferme_state.activated_after
            
            # Add setup summary
            for driver in self.drivers:
                setup = self.results.parc_ferme_state.locked_setups.get(driver)
                if setup:
                    report.setup_summary[driver] = {
                        "categories": {
                            "aerodynamics": setup.aerodynamics,
                            "suspension": setup.suspension,
                            "differential": setup.differential,
                            "brake_balance": setup.brake_balance,
                            "tyre_pressure": setup.tyre_pressure,
                        },
                        "total_effect": setup.total_effect,
                        "r_delta": setup.r_rating_delta,
                    }
                    report.final_r_ratings[driver] = (
                        self.driver_ratings[driver] + setup.r_rating_delta
                    )
            
            # Add R rating exports
            report.r_rating_exports = self.results.parc_ferme_state.export_r_ratings(
                self.driver_ratings
            )
        
        return report
    
    def print_full_report(self):
        """Print a comprehensive text report."""
        report = self.generate_report()
        
        print(f"\n{'='*80}")
        print("PRACTICE WEEKEND FULL REPORT")
        print(f"{'='*80}")
        print(f"Track: {self.track}")
        print(f"Weekend Type: {self.weekend_type.value.upper()}")
        print(f"Parc Fermé: {'ACTIVE' if report.parc_ferme_active else 'INACTIVE'}")
        print(f"Activated After: {report.parc_ferme_activated_after or 'N/A'}")
        
        # Setup table
        if report.setup_summary:
            print("\n" + report.generate_setup_table())
        
        # Lap times for each session
        for session_name in ["FP1", "FP2", "FP3"]:
            if session_name in report.sessions:
                print("\n" + report.generate_laptime_table(session_name))
        
        print(f"\n{'='*80}\n")
    
    def get_driver_final_r_rating(self, driver: str) -> float:
        """
        Get a driver's final R rating after setup effects.
        
        Args:
            driver: Driver name
            
        Returns:
            Final R rating
        """
        base_r = self.driver_ratings.get(driver, 100.0)
        
        if self.results.parc_ferme_state:
            delta = self.results.parc_ferme_state.get_r_delta(driver)
            return base_r + delta
        
        return base_r
    
    def get_all_final_r_ratings(self) -> Dict[str, float]:
        """
        Get all drivers' final R ratings.
        
        Returns:
            Dictionary of driver -> final R rating
        """
        return {
            driver: self.get_driver_final_r_rating(driver)
            for driver in self.drivers
        }


class RRatingConnector:
    """
    Connector for providing R ratings to other systems (qualifying, race).
    
    This class provides a clean interface for other modules to get
    driver R ratings that include practice setup effects.
    """
    
    def __init__(self, weekend_simulator: PracticeWeekendSimulator):
        """
        Initialize connector.
        
        Args:
            weekend_simulator: Completed weekend simulator
        """
        self.simulator = weekend_simulator
        self.parc_ferme = weekend_simulator.results.parc_ferme_state
    
    def get_r_for_qualifying(self) -> Dict[str, float]:
        """
        Get R ratings for qualifying session.
        
        Returns:
            Dictionary of driver -> R rating
        """
        return self.simulator.get_all_final_r_ratings()
    
    def get_r_for_race(self) -> Dict[str, float]:
        """
        Get R ratings for race session.
        
        Returns:
            Dictionary of driver -> R rating
        """
        return self.simulator.get_all_final_r_ratings()
    
    def get_r_for_sprint(self) -> Dict[str, float]:
        """
        Get R ratings for sprint race (2022 rules).
        
        For 2022, sprint uses same setup as main race (both under same parc fermé).
        
        Returns:
            Dictionary of driver -> R rating
        """
        return self.simulator.get_all_final_r_ratings()
    
    def get_driver_r(self, driver: str) -> float:
        """
        Get R rating for a specific driver.
        
        Args:
            driver: Driver name
            
        Returns:
            Driver's R rating with setup effects
        """
        return self.simulator.get_driver_final_r_rating(driver)
    
    def get_setup_delta(self, driver: str) -> float:
        """
        Get setup effect delta for a driver.
        
        Args:
            driver: Driver name
            
        Returns:
            Delta value
        """
        if self.parc_ferme:
            return self.parc_ferme.get_r_delta(driver)
        return 0.0
    
    def export_to_qualifying_system(self) -> Dict[str, Any]:
        """
        Export data in format suitable for qualifying system.
        
        Returns:
            Dictionary with R ratings and setup info
        """
        return {
            "driver_ratings": self.get_r_for_qualifying(),
            "setup_deltas": self.simulator.get_r_rating_deltas(),
            "parc_ferme_active": self.parc_ferme.is_active if self.parc_ferme else False,
            "weekend_type": self.simulator.weekend_type.value,
        }
    
    def export_to_race_system(self) -> Dict[str, Any]:
        """
        Export data in format suitable for race system.
        
        Returns:
            Dictionary with R ratings and setup info
        """
        return {
            "driver_ratings": self.get_r_for_race(),
            "setup_deltas": self.simulator.get_r_rating_deltas(),
            "parc_ferme_active": self.parc_ferme.is_active if self.parc_ferme else False,
            "weekend_type": self.simulator.weekend_type.value,
        }