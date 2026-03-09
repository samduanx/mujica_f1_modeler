"""
Practice Types Module

Core data structures for the F1 Free Practice System.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime


class PracticeSessionType(Enum):
    """Type of practice session."""

    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"


class WeekendType(Enum):
    """Type of race weekend."""

    NORMAL = "normal"
    SPRINT = "sprint"


class RunType(Enum):
    """Type of practice run/lap."""

    OUT_LAP = "out_lap"
    FLYING_LAP = "flying_lap"
    IN_LAP = "in_lap"
    LONG_RUN = "long_run"
    QUALI_SIM = "quali_sim"
    INSTALLATION = "installation"


class SetupCategory(Enum):
    """Setup tuning categories for dice rolling."""

    AERODYNAMICS = "aerodynamics"
    SUSPENSION = "suspension"
    DIFFERENTIAL = "differential"
    BRAKE_BALANCE = "brake_balance"
    TYRE_PRESSURE = "tyre_pressure"


@dataclass
class PracticeLap:
    """A complete practice lap."""

    driver: str
    session: str  # "FP1", "FP2", "FP3"

    # Lap timing (seconds)
    lap_time: float = 0.0
    sector_times: List[float] = field(default_factory=list)  # [s1, s2, s3]

    # Tyre info
    tyre_compound: str = ""
    tyre_age: int = 0  # Laps on this tyre set

    # Run type
    run_type: RunType = RunType.FLYING_LAP

    # Track conditions
    track_temperature: float = 0.0
    air_temperature: float = 0.0
    track_condition: str = "dry"  # "dry", "damp", "wet"

    # DRS
    drs_available: bool = True
    drs_used: bool = False

    # Incidents
    traffic_encountered: bool = False
    traffic_impact: float = 0.0  # Time lost to traffic
    yellow_flag_lost: float = 0.0  # Time lost to yellow flags

    # Validity
    valid_lap: bool = True
    deleted_lap: bool = False  # Track limits violation

    # Timing
    lap_number: int = 0
    session_time: float = 0.0  # Time in session when lap completed


@dataclass
class SetupTuningResult:
    """Result of setup tuning dice rolls for a driver."""

    driver: str
    session: str  # Which FP session this was from

    # Tuning categories (dice roll results 1-6)
    aerodynamics: int = 3  # Effect on downforce/drag balance
    suspension: int = 3  # Effect on mechanical grip
    differential: int = 3  # Effect on traction/power delivery
    brake_balance: int = 3  # Effect on braking stability
    tyre_pressure: int = 3  # Effect on tyre wear and grip

    # Calculated effects
    total_effect: float = 0.0  # Sum of all effects
    r_rating_delta: float = 0.0  # Final R rating modifier

    # Description
    effect_summary: str = ""

    def get_category_value(self, category: SetupCategory) -> int:
        """Get dice value for a specific category."""
        mapping = {
            SetupCategory.AERODYNAMICS: self.aerodynamics,
            SetupCategory.SUSPENSION: self.suspension,
            SetupCategory.DIFFERENTIAL: self.differential,
            SetupCategory.BRAKE_BALANCE: self.brake_balance,
            SetupCategory.TYRE_PRESSURE: self.tyre_pressure,
        }
        return mapping.get(category, 3)


@dataclass
class PracticeIncident:
    """An incident during practice."""

    driver: str
    incident_type: str  # "off_track", "spin", "track_limits", "contact"
    severity: str  # "minor", "major", "critical"
    sector: int = 0
    time_lost: float = 0.0
    lap_deleted: bool = False
    session_time: float = 0.0
    description: str = ""


@dataclass
class PracticeSessionResult:
    """Complete result of a practice session."""

    session_type: PracticeSessionType
    track: str = ""

    # Lap times results
    lap_times: Dict[str, List[PracticeLap]] = field(
        default_factory=dict
    )  # Driver -> laps
    best_times: Dict[str, float] = field(
        default_factory=dict
    )  # Driver -> best lap time

    # Setup tuning results
    setup_results: Dict[str, SetupTuningResult] = field(default_factory=dict)

    # Session statistics
    total_laps: int = 0
    incidents: List[PracticeIncident] = field(default_factory=list)
    weather_conditions: List[str] = field(default_factory=list)

    def get_standings(self) -> List[Tuple[str, float]]:
        """Get current standings sorted by lap time."""
        sorted_drivers = sorted(
            self.best_times.items(),
            key=lambda x: x[1] if x[1] is not None and x[1] > 0 else float("inf"),
        )
        return sorted_drivers

    def get_driver_best_lap(self, driver: str) -> Optional[float]:
        """Get best lap time for a driver."""
        return self.best_times.get(driver)

    def get_driver_laps(self, driver: str) -> List[PracticeLap]:
        """Get all laps for a driver."""
        return self.lap_times.get(driver, [])


@dataclass
class ParcFermeState:
    """Tracks whether parc fermé is active and what setup effects are locked."""

    is_active: bool = False
    activated_after: Optional[str] = None  # Which session activated it
    activation_time: Optional[datetime] = None
    weekend_type: WeekendType = WeekendType.NORMAL

    # Locked setup effects (cannot be changed after parc fermé)
    locked_setups: Dict[str, SetupTuningResult] = field(default_factory=dict)

    # R rating deltas to apply
    r_rating_deltas: Dict[str, float] = field(default_factory=dict)

    def activate(self, after_session: str, timestamp: Optional[datetime] = None):
        """Activate parc fermé."""
        self.is_active = True
        self.activated_after = after_session
        self.activation_time = timestamp or datetime.now()

    def deactivate(self):
        """Deactivate parc fermé (rare, only for specific regulations)."""
        self.is_active = False

    def lock_driver_setup(self, driver: str, setup: SetupTuningResult):
        """Lock a driver's setup."""
        self.locked_setups[driver] = setup
        self.r_rating_deltas[driver] = setup.r_rating_delta

    def get_r_delta(self, driver: str) -> float:
        """Get R rating delta for a driver."""
        return self.r_rating_deltas.get(driver, 0.0)

    def apply_to_r_rating(self, driver: str, base_r: float) -> float:
        """Apply parc fermé delta to base R rating."""
        delta = self.get_r_delta(driver)
        return base_r + delta


@dataclass
class WeekendResults:
    """Results for a complete race weekend practice sessions."""

    weekend_type: WeekendType
    track: str = ""

    # Session results
    fp1: Optional[PracticeSessionResult] = None
    fp2: Optional[PracticeSessionResult] = None
    fp3: Optional[PracticeSessionResult] = None

    # Final parc fermé state
    parc_ferme_state: Optional[ParcFermeState] = None

    def get_r_rating_deltas(self) -> Dict[str, float]:
        """Get final R rating deltas for all drivers."""
        if self.parc_ferme_state:
            return self.parc_ferme_state.r_rating_deltas
        return {}

    def get_final_standings(self) -> List[Tuple[str, float]]:
        """Get final practice standings (from last session)."""
        last_session = None
        if self.fp3:
            last_session = self.fp3
        elif self.fp2:
            last_session = self.fp2
        elif self.fp1:
            last_session = self.fp1

        if last_session:
            return last_session.get_standings()
        return []

    def get_driver_setup_result(self, driver: str) -> Optional[SetupTuningResult]:
        """Get final setup result for a driver."""
        if self.parc_ferme_state and driver in self.parc_ferme_state.locked_setups:
            return self.parc_ferme_state.locked_setups[driver]
        return None


@dataclass
class RRatingExport:
    """Export format for R rating deltas to other systems."""

    driver: str
    base_r: float
    delta: float
    final_r: float
    source: str  # "FP1", "FP1+FP2+FP3", etc.
    setup_categories: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "driver": self.driver,
            "base_r": self.base_r,
            "delta": self.delta,
            "final_r": self.final_r,
            "source": self.source,
            "setup_categories": self.setup_categories,
        }


@dataclass
class PracticeReport:
    """Full practice session report for export/display."""

    weekend_type: WeekendType
    track: str

    # Session data
    sessions: Dict[str, PracticeSessionResult] = field(default_factory=dict)

    # Setup dice results
    setup_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Parc fermé
    parc_ferme_active: bool = False
    parc_ferme_activated_after: Optional[str] = None

    # Final R ratings
    final_r_ratings: Dict[str, float] = field(default_factory=dict)

    # Export data
    r_rating_exports: List[RRatingExport] = field(default_factory=list)

    def generate_setup_table(self) -> str:
        """Generate ASCII table of setup dice results."""
        lines = []
        lines.append("=" * 80)
        lines.append("SETUP TUNING DICE RESULTS")
        lines.append("=" * 80)
        lines.append(
            f"{'Driver':<20} {'Aero':<6} {'Susp':<6} {'Diff':<6} {'Brake':<6} {'Tyre':<6} | {'Total':<8} {'R Delta':<8}"
        )
        lines.append("-" * 80)

        for driver, data in self.setup_summary.items():
            cats = data.get("categories", {})
            lines.append(
                f"{driver:<20} "
                f"{cats.get('aerodynamics', 3):<6} "
                f"{cats.get('suspension', 3):<6} "
                f"{cats.get('differential', 3):<6} "
                f"{cats.get('brake_balance', 3):<6} "
                f"{cats.get('tyre_pressure', 3):<6} | "
                f"{data.get('total_effect', 0):>+6.1f}   "
                f"{data.get('r_delta', 0):>+6.2f}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)

    def generate_laptime_table(self, session: str = "FP3") -> str:
        """Generate ASCII table of lap times for a session."""
        session_result = self.sessions.get(session)
        if not session_result:
            return f"No data for {session}"

        lines = []
        lines.append("=" * 80)
        lines.append(f"LAP TIMES - {session}")
        lines.append("=" * 80)
        lines.append(
            f"{'Pos':<4} {'Driver':<20} {'Best Lap':<12} {'Gap':<10} {'Laps':<6}"
        )
        lines.append("-" * 80)

        best_time = None
        for pos, (driver, time) in enumerate(session_result.get_standings(), 1):
            if time is None or time <= 0:
                continue

            if best_time is None:
                best_time = time

            gap = time - best_time if best_time else 0
            gap_str = f"+{gap:.3f}" if gap > 0 else "---"

            driver_laps = len(session_result.get_driver_laps(driver))

            lines.append(
                f"{pos:<4} {driver:<20} {time:<12.3f} {gap_str:<10} {driver_laps:<6}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)


@dataclass
class PracticeSessionConfig:
    """Configuration for a practice session."""

    session_type: PracticeSessionType = PracticeSessionType.FP1
    duration_minutes: int = 60
    track: str = ""
    base_lap_time: float = 90.0

    # Dice configuration
    dice_categories: List[SetupCategory] = field(
        default_factory=lambda: list(SetupCategory)
    )
    dice_sides: int = 6

    # Simulation parameters
    traffic_density: float = 0.8  # Higher in practice than qualifying
    pit_stop_probability: float = 0.3
    extended_stop_probability: float = 0.1
