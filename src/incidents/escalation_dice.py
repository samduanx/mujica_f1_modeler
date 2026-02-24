"""
Dice-Controlled Incident Escalation and Duration System.

Implements:
- Severity-based escalation from incidents to safety responses (yellow → VSC → SC → Red Flag)
- Gaussian distribution for VSC/SC durations based on real-world data
- Dice-controlled red flag timing (without weather system)

Based on FastF1 calibration data and F1 sporting regulations.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from incidents.incident_types import IncidentSeverity, Incident
from incidents.dice_roller import roll_d100, roll_d10, roll_d6


class SafetyResponseType(Enum):
    """Types of safety responses"""

    SECTOR_YELLOW = "sector_yellow"
    SECTOR_DOUBLE_YELLOW = "sector_double_yellow"
    VSC = "vsc"
    SC = "sc"
    RED_FLAG = "red_flag"
    NONE = "none"


@dataclass
class SafetyResponse:
    """Represents a safety response decision"""

    response_type: SafetyResponseType
    duration_laps: Optional[int] = None
    duration_seconds: Optional[float] = None
    sector: Optional[int] = None
    reason: str = ""
    escalation_roll: int = 0


@dataclass
class EscalationThresholds:
    """Dice thresholds for escalation decisions"""

    # Base response thresholds (1d100 roll <= threshold)
    sector_yellow_max: int = 40
    double_yellow_max: int = 65
    vsc_max: int = 85
    sc_max: int = 95
    # 96-100 = red flag

    # Escalation thresholds (probability of escalating)
    yellow_to_double_threshold: int = 30  # 30%
    double_to_vsc_threshold: int = 25  # 25%
    vsc_to_sc_threshold: int = 20  # 20%
    sc_to_red_threshold: int = 15  # 15%


@dataclass
class SeverityModifiers:
    """Dice roll modifiers based on incident severity"""

    minor: int = -20  # Less likely for major responses
    moderate: int = 0  # No modifier
    major: int = 15  # More likely for SC/VSC
    severe: int = 30  # Very likely for SC/red flag

    def get_modifier(self, severity: IncidentSeverity) -> int:
        mapping = {
            IncidentSeverity.MINOR: self.minor,
            IncidentSeverity.MODERATE: self.moderate,
            IncidentSeverity.MAJOR: self.major,
            IncidentSeverity.SEVERE: self.severe,
        }
        return mapping.get(severity, 0)


class IncidentEscalationDice:
    """
    Dice-controlled escalation from incident to safety response.

    Flow:
    1. Roll 1d100 + severity modifier
    2. Determine base response type
    3. For VSC/SC, roll additional dice to confirm eligibility
    4. Return SafetyResponse with appropriate parameters
    """

    def __init__(
        self,
        thresholds: Optional[EscalationThresholds] = None,
        severity_mods: Optional[SeverityModifiers] = None,
    ):
        self.thresholds = thresholds or EscalationThresholds()
        self.severity_mods = severity_mods or SeverityModifiers()

    def determine_response(
        self,
        incident: Incident,
        current_response: SafetyResponseType = SafetyResponseType.NONE,
    ) -> SafetyResponse:
        """
        Roll dice to determine safety response based on incident.

        Args:
            incident: The incident that triggered this response check
            current_response: Current active safety response (for escalation)

        Returns:
            SafetyResponse with type, duration, and reason
        """
        # Roll base response
        base_roll = roll_d100()
        severity_mod = self.severity_mods.get_modifier(incident.severity)
        modified_roll = base_roll + severity_mod

        # Check for escalation from current response
        if current_response != SafetyResponseType.NONE:
            escalate, escalate_reason = self._check_escalation(current_response)
            if escalate:
                return self._handle_escalation(current_response, escalate_reason)

        # Determine base response type
        return self._determine_base_response(modified_roll, base_roll, incident)

    def _check_escalation(
        self,
        current: SafetyResponseType,
    ) -> Tuple[bool, str]:
        """Check if current response should escalate"""
        roll = roll_d100()

        if current == SafetyResponseType.SECTOR_YELLOW:
            threshold = self.thresholds.yellow_to_double_threshold
            if roll <= threshold:
                return True, "Yellow flag escalated to double yellow"
        elif current == SafetyResponseType.SECTOR_DOUBLE_YELLOW:
            threshold = self.thresholds.double_to_vsc_threshold
            if roll <= threshold:
                return True, "Double yellow escalated to VSC"
        elif current == SafetyResponseType.VSC:
            threshold = self.thresholds.vsc_to_sc_threshold
            if roll <= threshold:
                return True, "VSC escalated to SC"
        elif current == SafetyResponseType.SC:
            threshold = self.thresholds.sc_to_red_threshold
            if roll <= threshold:
                return True, "SC escalated to Red Flag"

        return False, ""

    def _handle_escalation(
        self,
        from_response: SafetyResponseType,
        reason: str,
    ) -> SafetyResponse:
        """Handle escalation to next response level"""

        if from_response == SafetyResponseType.SECTOR_YELLOW:
            return SafetyResponse(
                response_type=SafetyResponseType.SECTOR_DOUBLE_YELLOW,
                reason=reason,
                escalation_roll=roll_d100(),
            )
        elif from_response == SafetyResponseType.SECTOR_DOUBLE_YELLOW:
            return SafetyResponse(
                response_type=SafetyResponseType.VSC,
                duration_laps=DurationDiceRoller().roll_vsc_duration(),
                reason=reason,
                escalation_roll=roll_d100(),
            )
        elif from_response == SafetyResponseType.VSC:
            return SafetyResponse(
                response_type=SafetyResponseType.SC,
                duration_laps=DurationDiceRoller().roll_sc_duration(),
                reason=reason,
                escalation_roll=roll_d100(),
            )
        elif from_response == SafetyResponseType.SC:
            return SafetyResponse(
                response_type=SafetyResponseType.RED_FLAG,
                reason=reason,
                escalation_roll=roll_d100(),
            )

        return SafetyResponse(response_type=SafetyResponseType.NONE)

    def _determine_base_response(
        self,
        modified_roll: int,
        base_roll: int,
        incident: Incident,
    ) -> SafetyResponse:
        """Determine base response type from dice roll"""

        # Check each threshold in order
        if modified_roll <= self.thresholds.sector_yellow_max:
            return SafetyResponse(
                response_type=SafetyResponseType.SECTOR_YELLOW,
                sector=incident.sector if hasattr(incident, "sector") else 1,
                reason=f"Sector yellow - roll {base_roll}+{self.severity_mods.get_modifier(incident.severity)}={modified_roll}",
                escalation_roll=base_roll,
            )

        elif modified_roll <= self.thresholds.double_yellow_max:
            return SafetyResponse(
                response_type=SafetyResponseType.SECTOR_DOUBLE_YELLOW,
                sector=incident.sector if hasattr(incident, "sector") else 1,
                reason=f"Double yellow - roll {base_roll}+{self.severity_mods.get_modifier(incident.severity)}={modified_roll}",
                escalation_roll=base_roll,
            )

        elif modified_roll <= self.thresholds.vsc_max:
            # Additional roll for VSC eligibility
            vsc_roll = roll_d100()
            if vsc_roll <= 70:  # 70% chance to confirm VSC
                return SafetyResponse(
                    response_type=SafetyResponseType.VSC,
                    duration_laps=DurationDiceRoller().roll_vsc_duration(),
                    reason=f"VSC confirmed - eligibility roll {vsc_roll}/70",
                    escalation_roll=base_roll,
                )
            else:
                # Downgrade to double yellow
                return SafetyResponse(
                    response_type=SafetyResponseType.SECTOR_DOUBLE_YELLOW,
                    sector=incident.sector if hasattr(incident, "sector") else 1,
                    reason=f"VSC rejected (roll {vsc_roll}/70), downgraded to double yellow",
                    escalation_roll=base_roll,
                )

        elif modified_roll <= self.thresholds.sc_max:
            # Additional roll for SC eligibility
            sc_roll = roll_d100()
            if sc_roll <= 60:  # 60% chance to confirm SC
                return SafetyResponse(
                    response_type=SafetyResponseType.SC,
                    duration_laps=DurationDiceRoller().roll_sc_duration(),
                    reason=f"SC confirmed - eligibility roll {sc_roll}/60",
                    escalation_roll=base_roll,
                )
            else:
                # Downgrade to VSC
                return SafetyResponse(
                    response_type=SafetyResponseType.VSC,
                    duration_laps=DurationDiceRoller().roll_vsc_duration(),
                    reason=f"SC rejected (roll {sc_roll}/60), downgraded to VSC",
                    escalation_roll=base_roll,
                )

        else:
            # Red flag
            rf_roll = roll_d100()
            if rf_roll <= 50:  # 50% chance to confirm red flag
                return SafetyResponse(
                    response_type=SafetyResponseType.RED_FLAG,
                    reason=f"Red flag confirmed - eligibility roll {rf_roll}/50",
                    escalation_roll=base_roll,
                )
            else:
                # Downgrade to SC
                return SafetyResponse(
                    response_type=SafetyResponseType.SC,
                    duration_laps=DurationDiceRoller().roll_sc_duration(),
                    reason=f"Red flag rejected (roll {rf_roll}/50), downgraded to SC",
                    escalation_roll=base_roll,
                )


class DurationDiceRoller:
    """
    Gaussian distribution-based duration rolling.

    Uses Box-Muller transform for normal distribution sampling.
    Based on FastF1 calibration data from real F1 races.
    """

    # Real-world statistics (from FastF1 calibration)
    VSC_MEAN_LAPS = 2.8
    VSC_STD_DEV = 0.8

    SC_MEAN_LAPS = 4.2
    SC_STD_DEV = 1.5

    def __init__(self):
        self._vsc_samples: List[float] = []
        self._sc_samples: List[float] = []

    def roll_vsc_duration(self) -> int:
        """
        Roll VSC duration using Gaussian distribution.

        Returns:
            Duration in laps, clamped to valid range (1-5 laps)
        """
        # Box-Muller transform
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)

        # Scale to our distribution
        duration = self.VSC_MEAN_LAPS + (z * self.VSC_STD_DEV)

        # Clamp to valid range (within 3-sigma and practical limits)
        duration = max(1.0, min(5.0, duration))

        result = int(round(duration))
        self._vsc_samples.append(result)
        return result

    def roll_sc_duration(self) -> int:
        """
        Roll SC duration using Gaussian distribution.

        Returns:
            Duration in laps, clamped to valid range (1-10 laps)
        """
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)

        duration = self.SC_MEAN_LAPS + (z * self.SC_STD_DEV)
        duration = max(1.0, min(10.0, duration))

        result = int(round(duration))
        self._sc_samples.append(result)
        return result

    def apply_duration_modifiers(
        self,
        base_duration: int,
        track_conditions: str = "dry",
        incident_count: int = 1,
    ) -> int:
        """
        Apply modifiers to base duration (dry conditions).

        Args:
            base_duration: Base duration in laps
            track_conditions: Track condition (only "dry" for now)
            incident_count: Number of cascading incidents

        Returns:
            Modified duration in laps
        """
        modified = base_duration

        # No weather modifier for dry conditions
        # (kept for future weather system integration)

        # Incident cascade modifier
        if incident_count > 1:
            modified += incident_count - 1

        # Recovery difficulty roll
        recovery_roll = roll_d100()
        if recovery_roll > 70:
            modified += 1  # Complex recovery
        if recovery_roll > 90:
            modified += 1  # Very complex recovery

        return min(modified, 10)  # Cap at 10 laps

    def get_statistics(self) -> Dict:
        """Get statistics on rolled durations"""
        return {
            "vsc": {
                "samples": len(self._vsc_samples),
                "mean": sum(self._vsc_samples) / len(self._vsc_samples)
                if self._vsc_samples
                else 0,
                "min": min(self._vsc_samples) if self._vsc_samples else 0,
                "max": max(self._vsc_samples) if self._vsc_samples else 0,
            },
            "sc": {
                "samples": len(self._sc_samples),
                "mean": sum(self._sc_samples) / len(self._sc_samples)
                if self._sc_samples
                else 0,
                "min": min(self._sc_samples) if self._sc_samples else 0,
                "max": max(self._sc_samples) if self._sc_samples else 0,
            },
        }


class RedFlagTimingDice:
    """
    Dice-controlled red flag timing (dry conditions only).

    For future weather system integration, see plan Section 14.
    Currently assumes dry track conditions.
    """

    def __init__(self):
        self._stoppage_times: List[float] = []

    def determine_stoppage_duration(
        self,
        track_damage: int = 50,  # 0-100 scale
    ) -> Dict:
        """
        Roll dice to determine red flag stoppage timing (dry conditions).

        Args:
            track_damage: Amount of track damage (0-100)

        Returns:
            Dict with min/max resume times in seconds
        """
        # Base stoppage time roll (1d100)
        base_time_roll = roll_d100()

        # Base duration table (minutes)
        if base_time_roll <= 30:
            base_minutes = 10  # Quick clear
        elif base_time_roll <= 60:
            base_minutes = 20  # Standard
        elif base_time_roll <= 85:
            base_minutes = 35  # Extended
        else:
            base_minutes = 50  # Major delay

        # Track damage modifier
        damage_mod = track_damage / 50  # 0-2 additional minutes per 50 damage

        total_minutes = base_minutes + damage_mod

        self._stoppage_times.append(total_minutes * 60)

        return {
            "min_resume_time": total_minutes * 60,
            "max_resume_time": (total_minutes + 15) * 60,
            "base_roll": base_time_roll,
            "base_minutes": base_minutes,
            "damage_modifier": damage_mod,
        }

    def get_statistics(self) -> Dict:
        """Get statistics on stoppage times"""
        if not self._stoppage_times:
            return {}

        return {
            "samples": len(self._stoppage_times),
            "mean_seconds": sum(self._stoppage_times) / len(self._stoppage_times),
            "min_seconds": min(self._stoppage_times),
            "max_seconds": max(self._stoppage_times),
        }


# Default instances for easy import
default_escalation_dice = IncidentEscalationDice()
default_duration_roller = DurationDiceRoller()
default_red_flag_timing = RedFlagTimingDice()
