"""
Incident Manager.

Central manager for all race incidents.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random
import time

from incidents.incident_types import (
    IncidentType,
    Incident,
    IncidentSeverity,
    IncidentConfig,
    IncidentStatistics,
    TrackDifficulty,
)
from incidents.vehicle_fault import (
    TeamStability,
    VehicleFaultResolver,
    get_team_stability,
)
from incidents.driver_error import (
    DriverErrorType,
    DriverError,
    DriverErrorResolver,
    DriverErrorProbability,
)
from incidents.overtake_incident import (
    OvertakeCollision,
    OvertakeIncidentProbability,
    OvertakeSituation,
)
from incidents.double_attack import (
    DoubleAttackSystem,
    DoubleAttackResult,
    DoubleAttackSimulator,
)


class IncidentManager:
    """
    Central manager for all race incidents.

    Responsibilities:
    - Track incident probability per simulation interval
    - Roll for incidents at appropriate times
    - Apply incident effects to drivers
    - Generate narrative descriptions
    """

    def __init__(
        self,
        team_stabilities: Optional[Dict[str, TeamStability]] = None,
        incident_config: Optional[IncidentConfig] = None,
        track_difficulty: TrackDifficulty = TrackDifficulty.MEDIUM,
    ):
        """
        Initialize incident manager.

        Args:
            team_stabilities: Dictionary of team name to stability
            incident_config: Configuration for incident behavior
            track_difficulty: Track difficulty for collision calculations
        """
        self.config = incident_config or IncidentConfig()
        self.track_difficulty = track_difficulty

        # Initialize team stabilities
        self.team_stabilities = team_stabilities or {}

        # Initialize sub-systems
        self.vehicle_fault_resolvers: Dict[str, VehicleFaultResolver] = {}
        self.driver_error_resolver = DriverErrorResolver()
        self.overtake_incident_prob = OvertakeIncidentProbability(track_difficulty)
        self.double_attack_simulator = DoubleAttackSimulator()

        # Incident tracking
        self.incidents: List[Incident] = []
        self.incident_count = 0

        # Timing
        self.last_incident_time = 0.0
        self._incident_id_counter = 0

    def check_incident(
        self,
        current_time: float,
        lap: int,
        drivers: Dict[str, Dict],
        is_overtake_situation: bool = False,
        situation: Optional[OvertakeSituation] = None,
        recent_speed_delta: Optional[float] = None,
    ) -> Optional[Incident]:
        """
        Check if an incident occurs at current time.

        Args:
            current_time: Current race time
            lap: Current lap number
            drivers: Dictionary of driver info (name -> info dict)
            is_overtake_situation: Whether an overtake is in progress
            situation: Overtake situation type
            recent_speed_delta: Recent speed delta for double attack

        Returns:
            Incident if one occurs, None otherwise
        """
        # Check minimum interval
        if (
            current_time - self.last_incident_time
            < self.config.min_interval_for_incident
        ):
            return None

        # Check max incidents
        if len(self.incidents) >= self.config.max_incidents_per_race:
            return None

        # Roll for incident type
        incident_roll = random.randint(1, 100)

        if is_overtake_situation and incident_roll <= 40:
            return self._check_overtake_incident(drivers, situation, current_time, lap)
        elif incident_roll <= 60:
            return self._check_driver_error(drivers, current_time, lap)
        else:
            return self._check_vehicle_fault(drivers, current_time, lap)

    def _check_overtake_incident(
        self,
        drivers: Dict[str, Dict],
        situation: Optional[OvertakeSituation],
        current_time: float,
        lap: int,
    ) -> Optional[Incident]:
        """Check for overtake-related incident"""
        # Get attacker and defender
        driver_names = list(drivers.keys())
        if len(driver_names) < 2:
            return None

        attacker_name, defender_name = random.sample(driver_names, 2)
        attacker = drivers[attacker_name]
        defender = drivers[defender_name]

        # Calculate DR margin and speed delta
        dr_margin = attacker.get("dr_value", 85) - defender.get("dr_value", 85)
        speed_delta = 15.0  # Default speed delta

        # Check collision probability
        collision_prob = self.overtake_incident_prob.get_collision_probability(
            situation=situation or OvertakeSituation.ELSEWHERE,
            dr_margin=dr_margin,
            speed_delta=speed_delta,
            attacker_dr_value=attacker.get("dr_value", 85),
            defender_dr_value=defender.get("dr_value", 85),
        )

        if random.random() < collision_prob:
            return self._create_overtake_collision(
                attacker_name,
                defender_name,
                situation or OvertakeSituation.ELSEWHERE,
                current_time,
                lap,
            )

        return None

    def _check_driver_error(
        self,
        drivers: Dict[str, Dict],
        current_time: float,
        lap: int,
    ) -> Optional[Incident]:
        """Check for driver error incident"""
        if not self.config.enable_driver_errors:
            return None

        # Select random driver
        driver_name = random.choice(list(drivers.keys()))
        driver = drivers[driver_name]

        # Check error probability - R value controls error rate for top drivers
        error_prob = DriverErrorProbability().get_error_probability(
            dr_value=driver.get("dr_value", 85),
            lap_number=lap,
            tyre_degradation=driver.get("tyre_degradation", 1.0),
            race_position=driver.get("position", 10),
            under_pressure=driver.get("under_pressure", False),
            is_first_lap=(lap == 1),
            r_value=driver.get("R_Value", driver.get("r_value", None)),
        )

        if random.random() < error_prob:
            return self._create_driver_error(driver_name, current_time, lap)

        return None

    def _check_vehicle_fault(
        self,
        drivers: Dict[str, Dict],
        current_time: float,
        lap: int,
    ) -> Optional[Incident]:
        """Check for vehicle fault incident"""
        if not self.config.enable_vehicle_faults:
            return None

        # Select random driver
        driver_name = random.choice(list(drivers.keys()))
        driver = drivers[driver_name]

        # Get team stability
        team_name = driver.get("team", "Unknown")
        if team_name not in self.vehicle_fault_resolvers:
            stability = self.team_stabilities.get(
                team_name, get_team_stability(team_name)
            )
            self.vehicle_fault_resolvers[team_name] = VehicleFaultResolver(stability)

        resolver = self.vehicle_fault_resolvers[team_name]

        # Check fault probability
        fault_prob = resolver.stability.get_fault_probability(
            laps_on_pu=lap,
            race_distance_km=lap * 5.0,
            has_incident_damage=driver.get("has_incident_damage", False),
        )

        if random.random() < fault_prob:
            return self._create_vehicle_fault(
                driver_name, team_name, resolver, current_time, lap
            )

        return None

    def _create_overtake_collision(
        self,
        attacker: str,
        defender: str,
        situation: OvertakeSituation,
        current_time: float,
        lap: int,
    ) -> Incident:
        """Create overtake collision incident"""
        self._incident_id_counter += 1

        # Determine severity
        severity = IncidentSeverity.MODERATE
        time_penalty = 5.0

        # Generate narrative
        narrative = (
            f"{attacker} attempts to overtake {defender} "
            f"in {situation.value}, but they collide! "
            f"Both drivers continue but lose time."
        )

        return Incident(
            incident_id=f"INC_{self._incident_id_counter:03d}",
            incident_type=IncidentType.OVERTAKE_COLLISION,
            time=current_time,
            lap=lap,
            driver=attacker,
            severity=severity,
            description=f"Collision during overtake attempt",
            position_impact=0,
            time_penalty=time_penalty,
            affected_drivers=[attacker, defender],
            narrative=narrative,
        )

    def _create_driver_error(
        self,
        driver_name: str,
        current_time: float,
        lap: int,
    ) -> Incident:
        """Create driver error incident"""
        self._incident_id_counter += 1

        # Select error type
        error_type = random.choice(list(DriverErrorType))

        # Create error
        error = self.driver_error_resolver.resolve_error(
            driver_name=driver_name,
            dr_value=85,  # Will be overridden by caller
            error_type=error_type,
        )

        # Generate narrative
        narratives = {
            DriverErrorType.LOCKED_BRAKES: f"{driver_name} locks up at the braking zone",
            DriverErrorType.OFF_TRACK: f"{driver_name} runs wide and goes off track",
            DriverErrorType.SPIN: f"{driver_name} spins out of control",
            DriverErrorType.CORNER_MISTAKE: f"{driver_name} makes a mistake at the corner",
            DriverErrorType.POLE_POSITION_ERROR: f"{driver_name} loses control at the apex",
            DriverErrorType.UNDERSHOOT_CORNER: f"{driver_name} undershoots the corner",
            DriverErrorType.OVERSHOT_CORNER: f"{driver_name} overshoots the corner",
            DriverErrorType.BRAKING_POINT_ERROR: f"{driver_name} gets the braking point wrong",
        }

        return Incident(
            incident_id=f"INC_{self._incident_id_counter:03d}",
            incident_type=IncidentType.DRIVER_ERROR,
            time=current_time,
            lap=lap,
            driver=driver_name,
            severity=IncidentSeverity.MODERATE,
            description=error_type.value,
            position_impact=-1,
            time_penalty=3.0,
            narrative=narratives.get(error_type, f"{driver_name} makes an error"),
        )

    def _create_vehicle_fault(
        self,
        driver_name: str,
        team_name: str,
        resolver: VehicleFaultResolver,
        current_time: float,
        lap: int,
    ) -> Optional[Incident]:
        """Create vehicle fault incident"""
        self._incident_id_counter += 1

        # Resolve component fault
        fault = resolver.check_for_fault(
            laps_on_pu=lap,
            race_distance_km=lap * 5.0,
        )

        if fault:
            severity_map = {
                "minor": IncidentSeverity.MINOR,
                "moderate": IncidentSeverity.MODERATE,
                "major": IncidentSeverity.MAJOR,
                "terminal": IncidentSeverity.SEVERE,
            }

            return Incident(
                incident_id=f"INC_{self._incident_id_counter:03d}",
                incident_type=IncidentType.VEHICLE_FAULT,
                time=current_time,
                lap=lap,
                driver=driver_name,
                severity=severity_map.get(
                    fault.severity.value, IncidentSeverity.MODERATE
                ),
                description=f"{fault.component}: {fault.fault_type}",
                position_impact=0,
                time_penalty=fault.time_loss,
                is_retirement=not fault.repairable,
                narrative=f"{driver_name}'s car suffers a {fault.fault_type}",
            )

        return None

    def check_double_attack(
        self,
        attacker_name: str,
        attacker_dr: float,
        attacker_tyre_deg: float,
        attacker_has_drs: bool,
        defender_name: str,
        defender_dr: float,
        defender_tyre_deg: float,
        defender_has_drs: bool,
        time_since_overtake: float,
    ) -> Optional[DoubleAttackResult]:
        """Check for and resolve double attack scenario"""
        if not self.config.enable_double_attack:
            return None

        return self.double_attack_simulator.check_double_attack(
            attacker_name=attacker_name,
            attacker_dr=attacker_dr,
            attacker_tyre_deg=attacker_tyre_deg,
            attacker_has_drs=attacker_has_drs,
            defender_name=defender_name,
            defender_dr=defender_dr,
            defender_tyre_deg=defender_tyre_deg,
            defender_has_drs=defender_has_drs,
            time_since_overtake=time_since_overtake,
        )

    def _check_blue_flag_violation(
        self,
        driver_name: str,
        resistance_level,
        offense_count: int,
        current_time: float,
        lap: int,
        track_section: str = "unknown",
    ) -> Optional[Incident]:
        """
        Check for and create blue flag violation incident.

        Blue flag violations occur when lapped cars fail to give way
        to leaders in a timely manner. Penalties escalate based on
        resistance level and offense count.

        Args:
            driver_name: Name of the violating driver
            resistance_level: Level of resistance shown
            offense_count: Number of previous offenses
            current_time: Current race time
            lap: Current lap number
            track_section: Where the violation occurred

        Returns:
            Incident if violation warrants report, None otherwise
        """
        from incidents.blue_flag import ResistanceLevel

        # MINOR resistance on first offense may not warrant incident report
        if resistance_level == ResistanceLevel.NONE:
            return None

        if resistance_level == ResistanceLevel.MINOR and offense_count <= 1:
            # First minor offense - just logged, no incident
            return None

        self._incident_id_counter += 1

        # Determine severity and penalty based on resistance level
        severity_map = {
            ResistanceLevel.MINOR: IncidentSeverity.MINOR,
            ResistanceLevel.MODERATE: IncidentSeverity.MODERATE,
            ResistanceLevel.STRONG: IncidentSeverity.MAJOR,
            ResistanceLevel.VIOLATION: IncidentSeverity.SEVERE,
        }

        severity = severity_map.get(resistance_level, IncidentSeverity.MODERATE)

        # Determine penalty
        penalty_map = {
            (ResistanceLevel.MINOR, 2): "warning_announced",
            (ResistanceLevel.MINOR, 3): "5s_penalty",
            (ResistanceLevel.MODERATE, 1): "warning_announced",
            (ResistanceLevel.MODERATE, 2): "5s_penalty",
            (ResistanceLevel.MODERATE, 3): "drive_through",
            (ResistanceLevel.STRONG, 1): "5s_penalty",
            (ResistanceLevel.STRONG, 2): "drive_through",
            (ResistanceLevel.STRONG, 3): "stop_go",
            (ResistanceLevel.VIOLATION, 1): "drive_through",
            (ResistanceLevel.VIOLATION, 2): "stop_go",
            (ResistanceLevel.VIOLATION, 3): "black_flag",
        }

        penalty = penalty_map.get(
            (resistance_level, min(offense_count, 3)),
            "warning_announced",  # Default
        )

        # Time penalty in seconds
        time_penalty_map = {
            "warning_announced": 0.0,
            "5s_penalty": 5.0,
            "drive_through": 20.0,  # Approximate time loss
            "stop_go": 30.0,  # Approximate time loss
            "black_flag": 0.0,  # Disqualification
        }
        time_penalty = time_penalty_map.get(penalty, 0.0)

        # Generate narrative
        narratives = {
            ResistanceLevel.MINOR: (
                f"{driver_name} shows minor resistance to blue flags "
                f"at {track_section} - warned by Race Control"
            ),
            ResistanceLevel.MODERATE: (
                f"{driver_name} holds up the leader for several corners "
                f"at {track_section} - blue flag violation"
            ),
            ResistanceLevel.STRONG: (
                f"{driver_name} defends aggressively against blue flags "
                f"at {track_section} - significant time lost"
            ),
            ResistanceLevel.VIOLATION: (
                f"{driver_name} completely ignores blue flags "
                f"at {track_section} - major infringement"
            ),
        }

        narrative = narratives.get(
            resistance_level, f"{driver_name} blue flag violation at {track_section}"
        )

        return Incident(
            incident_id=f"INC_{self._incident_id_counter:03d}",
            incident_type=IncidentType.BLUE_FLAG_VIOLATION,
            time=current_time,
            lap=lap,
            driver=driver_name,
            severity=severity,
            description=f"Blue flag violation: {resistance_level.value}",
            position_impact=0,
            time_penalty=time_penalty,
            narrative=narrative,
        )

    def report_blue_flag_violation(
        self,
        driver_name: str,
        resistance_level,
        offense_count: int,
        current_time: float,
        lap: int,
        track_section: str = "unknown",
    ) -> Optional[Incident]:
        """
        Report a blue flag violation from external system.

        This is the public interface for reporting blue flag violations
        from the BlueFlagManager or LappingOvertake systems.

        Args:
            driver_name: Name of the violating driver
            resistance_level: Level of resistance shown
            offense_count: Number of previous offenses
            current_time: Current race time
            lap: Current lap number
            track_section: Where the violation occurred

        Returns:
            Incident if created, None otherwise
        """
        incident = self._check_blue_flag_violation(
            driver_name=driver_name,
            resistance_level=resistance_level,
            offense_count=offense_count,
            current_time=current_time,
            lap=lap,
            track_section=track_section,
        )

        if incident:
            self.add_incident(incident)

        return incident

    def add_incident(self, incident: Incident):
        """Add an incident to the manager"""
        self.incidents.append(incident)
        self.last_incident_time = incident.time

    def get_statistics(self) -> IncidentStatistics:
        """Get incident statistics"""
        stats = IncidentStatistics()
        for incident in self.incidents:
            stats.add_incident(incident)
        return stats

    def get_narrative_summary(self) -> str:
        """Get narrative summary of all incidents"""
        if not self.incidents:
            return "No incidents occurred during the race."

        summary = "Race Incidents Summary:\n"
        for incident in self.incidents:
            summary += f"- Lap {incident.lap}: {incident.narrative}\n"

        return summary

    def reset(self):
        """Reset incident manager for new race"""
        self.incidents = []
        self.incident_count = 0
        self.last_incident_time = 0.0
        self._incident_id_counter = 0
        self.vehicle_fault_resolvers = {}
