"""
Parc Fermé Management Module

Manages parc fermé state and setup locking according to F1 2022 regulations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .types import ParcFermeState, SetupTuningResult, WeekendType, RRatingExport


class ParcFermeManager:
    """
    Manages parc fermé conditions for race weekends.

    2022 F1 Regulations:
    - Normal weekends: Parc fermé activates after FP3
    - Sprint weekends: Parc fermé activates when car first leaves pit lane in Friday qualifying
      and remains active through FP2, Sprint, AND Sunday's race (continuous)
    """

    def __init__(self, weekend_type: WeekendType = WeekendType.NORMAL):
        """
        Initialize parc fermé manager.

        Args:
            weekend_type: Type of weekend (normal or sprint)
        """
        self.state = ParcFermeState(weekend_type=weekend_type)
        self.weekend_type = weekend_type

    def activate(self, after_session: str, timestamp: Optional[datetime] = None):
        """
        Activate parc fermé.

        Args:
            after_session: Session after which parc fermé activates
            timestamp: Optional activation timestamp
        """
        self.state.activate(after_session, timestamp)

        # Log activation
        print(f"\n{'=' * 60}")
        print(f"PARC FERME ACTIVATED")
        print(f"Weekend Type: {self.weekend_type.value.upper()}")
        print(f"Activated After: {after_session}")
        print(f"Setup changes are now PROHIBITED")
        print(f"{'=' * 60}\n")

    def deactivate(self):
        """
        Deactivate parc fermé.

        Note: This is rarely used in F1. Only applicable for specific
        regulatory periods (not used in 2022 sprint weekends).
        """
        self.state.deactivate()
        print(f"\n*** PARC FERME DEACTIVATED ***\n")

    def is_active(self) -> bool:
        """Check if parc fermé is currently active."""
        return self.state.is_active

    def lock_driver_setup(self, driver: str, setup: SetupTuningResult):
        """
        Lock a driver's setup into parc fermé.

        Args:
            driver: Driver name
            setup: Setup tuning result to lock
        """
        self.state.lock_driver_setup(driver, setup)

    def lock_all_setups(self, setups: Dict[str, SetupTuningResult]):
        """
        Lock all driver setups.

        Args:
            setups: Dictionary of driver name -> setup result
        """
        for driver, setup in setups.items():
            self.lock_driver_setup(driver, setup)

        print(f"Locked setups for {len(setups)} drivers under parc fermé")

    def get_locked_setups(self) -> Dict[str, SetupTuningResult]:
        """Get all locked setups."""
        return self.state.locked_setups

    def get_r_rating_deltas(self) -> Dict[str, float]:
        """Get R rating deltas for all locked drivers."""
        return self.state.r_rating_deltas

    def get_r_delta(self, driver: str) -> float:
        """Get R rating delta for a specific driver."""
        return self.state.get_r_delta(driver)

    def apply_to_r_rating(self, driver: str, base_r: float) -> float:
        """
        Apply parc fermé delta to a driver's base R rating.

        Args:
            driver: Driver name
            base_r: Base R rating

        Returns:
            Adjusted R rating with setup effect applied
        """
        return self.state.apply_to_r_rating(driver, base_r)

    def export_r_ratings(
        self,
        base_ratings: Dict[str, float],
    ) -> List[RRatingExport]:
        """
        Export R rating deltas for integration with other systems.

        Args:
            base_ratings: Dictionary of driver -> base R rating

        Returns:
            List of RRatingExport objects
        """
        exports = []

        source = self._get_source_description()

        for driver, base_r in base_ratings.items():
            delta = self.get_r_delta(driver)
            final_r = base_r + delta

            # Get setup categories if available
            setup = self.state.locked_setups.get(driver)
            categories = {}
            if setup:
                categories = {
                    "aerodynamics": setup.aerodynamics,
                    "suspension": setup.suspension,
                    "differential": setup.differential,
                    "brake_balance": setup.brake_balance,
                    "tyre_pressure": setup.tyre_pressure,
                }

            export = RRatingExport(
                driver=driver,
                base_r=base_r,
                delta=delta,
                final_r=final_r,
                source=source,
                setup_categories=categories,
            )
            exports.append(export)

        return exports

    def export_to_dict(self, base_ratings: Dict[str, float]) -> Dict[str, Any]:
        """
        Export all data as a dictionary for JSON serialization.

        Args:
            base_ratings: Base R ratings

        Returns:
            Dictionary with all parc fermé data
        """
        exports = self.export_r_ratings(base_ratings)

        return {
            "weekend_type": self.weekend_type.value,
            "is_active": self.state.is_active,
            "activated_after": self.state.activated_after,
            "activation_time": self.state.activation_time.isoformat()
            if self.state.activation_time
            else None,
            "driver_ratings": {
                exp.driver: {
                    "base_r": exp.base_r,
                    "delta": exp.delta,
                    "final_r": exp.final_r,
                    "setup_categories": exp.setup_categories,
                }
                for exp in exports
            },
        }

    def _get_source_description(self) -> str:
        """Get description of setup source based on weekend type."""
        if self.weekend_type == WeekendType.SPRINT:
            return "FP1 (Sprint Weekend - Single Session)"
        else:
            return "FP1+FP2+FP3 (Normal Weekend - Averaged)"

    def generate_report(self) -> str:
        """Generate a text report of parc fermé status."""
        lines = []
        lines.append("=" * 70)
        lines.append("PARC FERMÉ STATUS REPORT")
        lines.append("=" * 70)
        lines.append(f"Weekend Type: {self.weekend_type.value.upper()}")
        lines.append(f"Status: {'ACTIVE' if self.state.is_active else 'INACTIVE'}")

        if self.state.activated_after:
            lines.append(f"Activated After: {self.state.activated_after}")

        if self.state.activation_time:
            lines.append(
                f"Activation Time: {self.state.activation_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        lines.append("-" * 70)
        lines.append(f"{'Driver':<20} {'R Delta':<10} {'Status':<20}")
        lines.append("-" * 70)

        for driver, delta in sorted(self.state.r_rating_deltas.items()):
            status = "LOCKED" if driver in self.state.locked_setups else "UNLOCKED"
            lines.append(f"{driver:<20} {delta:>+8.2f}  {status:<20}")

        lines.append("=" * 70)
        return "\n".join(lines)


class ParcFermeCoordinator:
    """
    Coordinates parc fermé across a complete race weekend.

    Handles the complex logic of different weekend types.
    """

    def __init__(self):
        self.managers: Dict[str, ParcFermeManager] = {}

    def create_for_weekend(
        self,
        weekend_type: WeekendType,
    ) -> ParcFermeManager:
        """
        Create parc fermé manager for a weekend.

        Args:
            weekend_type: Type of weekend

        Returns:
            Configured ParcFermeManager
        """
        return ParcFermeManager(weekend_type=weekend_type)

    def setup_normal_weekend(
        self,
        fp1_setups: Dict[str, SetupTuningResult],
        fp2_setups: Dict[str, SetupTuningResult],
        fp3_setups: Dict[str, SetupTuningResult],
    ) -> ParcFermeManager:
        """
        Set up parc fermé for a normal weekend.

        Normal weekend flow:
        FP1 → FP2 → FP3 → [PARC FERMÉ] → Qualifying → Race

        Setup effects are averaged across all three sessions.

        Args:
            fp1_setups: FP1 setup results
            fp2_setups: FP2 setup results
            fp3_setups: FP3 setup results

        Returns:
            ParcFermeManager with activated parc fermé
        """
        from .setup_tuning import SetupEffectCalculator

        manager = ParcFermeManager(weekend_type=WeekendType.NORMAL)

        # Average setups across all sessions
        calculator = SetupEffectCalculator()

        # Get all drivers
        all_drivers = (
            set(fp1_setups.keys()) | set(fp2_setups.keys()) | set(fp3_setups.keys())
        )

        for driver in all_drivers:
            setups = []
            if driver in fp1_setups:
                setups.append(fp1_setups[driver])
            if driver in fp2_setups:
                setups.append(fp2_setups[driver])
            if driver in fp3_setups:
                setups.append(fp3_setups[driver])

            if setups:
                final_setup = calculator.average_setups(setups)
                manager.lock_driver_setup(driver, final_setup)

        # Activate parc fermé after FP3
        manager.activate(after_session="FP3")

        return manager

    def setup_sprint_weekend_2022(
        self,
        fp1_setups: Dict[str, SetupTuningResult],
    ) -> ParcFermeManager:
        """
        Set up parc fermé for a 2022 sprint weekend.

        2022 Sprint weekend flow:
        FP1 → [PARC FERMÉ at Qualifying] → Qualifying → FP2 (under parc fermé)
        → Sprint → Race

        Setup effects are from FP1 ONLY (single chance).
        Parc fermé is continuous from Friday qualifying through Sunday race.

        Args:
            fp1_setups: FP1 setup results (ONLY setup session!)

        Returns:
            ParcFermeManager with activated parc fermé
        """
        manager = ParcFermeManager(weekend_type=WeekendType.SPRINT)

        # Lock FP1 setups (only chance!)
        for driver, setup in fp1_setups.items():
            manager.lock_driver_setup(driver, setup)

        # Activate parc fermé at qualifying start
        manager.activate(after_session="FP1 (before Qualifying)")

        print("\n[WARNING] 2022 SPRINT WEEKEND - RESTRICTIVE PARC FERME RULES")
        print("=" * 60)
        print("Parc ferme will remain active through:")
        print("  - Friday Qualifying")
        print("  - Saturday FP2 (under parc ferme)")
        print("  - Saturday Sprint Race")
        print("  - Sunday Grand Prix")
        print("=" * 60)
        print("Teams had ONE chance (FP1) to find a setup for both races!\n")

        return manager

    def check_setup_change_allowed(
        self,
        session: str,
        weekend_type: WeekendType,
        parc_ferme_active: bool,
    ) -> bool:
        """
        Check if setup changes are allowed in a given session.

        Args:
            session: Current session name
            weekend_type: Type of weekend
            parc_ferme_active: Whether parc fermé is currently active

        Returns:
            True if setup changes are allowed
        """
        if not parc_ferme_active:
            return True

        # Parc fermé is active - check if any exceptions apply
        if weekend_type == WeekendType.SPRINT:
            # 2022 Sprint: No setup changes allowed once parc fermé is active
            # This includes FP2 which runs under parc fermé
            return False
        else:
            # Normal weekend: No setup changes after parc fermé activates
            return False
