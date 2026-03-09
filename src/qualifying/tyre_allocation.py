"""
Tyre Allocation Manager for Qualifying

Manages tyre allocation throughout qualifying sessions with hard tyre suppression.
"""

from typing import Dict, Optional, List, Any
from src.qualifying.types import QualifyingSessionType, TyreAllocation


# Tyre distribution probabilities based on dice roll outcomes
# Hard tyres are suppressed to minimal probability in standard sessions
TYRE_DISTRIBUTION = {
    "CRITICAL_SUCCESS": {"SOFT": 0.95, "MEDIUM": 0.05, "HARD": 0.00},
    "GREAT_SUCCESS": {"SOFT": 0.85, "MEDIUM": 0.15, "HARD": 0.00},
    "SUCCESS": {"SOFT": 0.70, "MEDIUM": 0.30, "HARD": 0.00},
    "PARTIAL_SUCCESS": {"SOFT": 0.50, "MEDIUM": 0.45, "HARD": 0.05},
    "FAILURE": {"SOFT": 0.30, "MEDIUM": 0.60, "HARD": 0.10},
    "CRITICAL_FAILURE": {"SOFT": 0.20, "MEDIUM": 0.50, "HARD": 0.30},
}

# Required compounds per session type
REQUIRED_COMPOUNDS = {
    # Standard qualifying
    "Q1": None,  # Free choice
    "Q2": None,  # Free choice
    "Q3": "SOFT",  # Must use soft
    # Sprint qualifying
    "SQ1": "MEDIUM",  # Must use new medium
    "SQ2": "MEDIUM",  # Must use new medium
    "SQ3": "SOFT",    # Must use new soft
    # Alternative Tyre Allocation
    "ATA_Q1": "HARD",
    "ATA_Q2": "MEDIUM",
    "ATA_Q3": "SOFT",
}


class TyreAllocationManager:
    """Manages tyre allocation throughout qualifying."""
    
    def __init__(self, session_type: QualifyingSessionType, is_ata: bool = False):
        """
        Initialize tyre allocation manager.
        
        Args:
            session_type: Type of qualifying session
            is_ata: Whether this is an Alternative Tyre Allocation event
        """
        self.session_type = session_type
        self.is_ata = is_ata
        self.allocations: Dict[str, TyreAllocation] = {}
        
        # Set initial allocation based on session type
        self._set_initial_allocation()
    
    def _set_initial_allocation(self) -> None:
        """Set initial tyre allocation based on session type."""
        if self.session_type == QualifyingSessionType.SPRINT:
            # Sprint: 12 sets total (6 soft, 4 medium, 2 hard)
            self.default_soft = 6
            self.default_medium = 4
            self.default_hard = 2
        elif self.is_ata:
            # ATA: 11 sets total (2 hard, 4 medium, 5 soft)
            self.default_soft = 5
            self.default_medium = 4
            self.default_hard = 2
        else:
            # Standard: 13 sets total (8 soft, 3 medium, 2 hard)
            self.default_soft = 8
            self.default_medium = 3
            self.default_hard = 2
        
        self.default_inter = 4
        self.default_wet = 3
    
    def initialize_driver(self, driver: str) -> TyreAllocation:
        """Initialize tyre allocation for a driver."""
        allocation = TyreAllocation(
            driver=driver,
            soft=self.default_soft,
            medium=self.default_medium,
            hard=self.default_hard,
            inter=self.default_inter,
            wet=self.default_wet
        )
        self.allocations[driver] = allocation
        return allocation
    
    def get_required_compound(self, session: str) -> Optional[str]:
        """Get required compound for a session (if any)."""
        if self.is_ata:
            key = f"ATA_{session}"
        else:
            key = session
        return REQUIRED_COMPOUNDS.get(key)
    
    def use_tyre_set(
        self,
        driver: str,
        compound: str,
        session: str
    ) -> bool:
        """
        Record tyre usage.
        
        Args:
            driver: Driver name
            compound: Tyre compound used
            session: Session name
            
        Returns:
            True if tyre was available and used, False otherwise
        """
        if driver not in self.allocations:
            self.initialize_driver(driver)
        
        allocation = self.allocations[driver]
        
        # Check if required compound for this session
        required = self.get_required_compound(session)
        if required and compound != required:
            return False
        
        # Try to use the tyre
        return allocation.use_set(compound, session)
    
    def get_remaining_tyres(self, driver: str) -> Dict[str, int]:
        """Get remaining tyre sets for a driver."""
        if driver not in self.allocations:
            self.initialize_driver(driver)
        
        allocation = self.allocations[driver]
        return {
            "SOFT": allocation.soft,
            "MEDIUM": allocation.medium,
            "HARD": allocation.hard,
            "INTER": allocation.inter,
            "WET": allocation.wet,
        }
    
    def get_available_compounds(
        self,
        driver: str,
        session: str,
        track_wet: bool = False
    ) -> List[str]:
        """
        Get available compounds for a driver in a session.
        
        Args:
            driver: Driver name
            session: Session name
            track_wet: Whether track is wet
            
        Returns:
            List of available compounds
        """
        if track_wet:
            return ["INTER", "WET"]
        
        # Check if session requires specific compound
        required = self.get_required_compound(session)
        if required:
            return [required]
        
        # Return available compounds
        remaining = self.get_remaining_tyres(driver)
        available = []
        for compound, count in remaining.items():
            if count > 0 and compound in ["SOFT", "MEDIUM", "HARD"]:
                available.append(compound)
        
        return available if available else ["SOFT"]  # Fallback
    
    def get_tyre_distribution(self, outcome: str) -> Dict[str, float]:
        """
        Get tyre distribution probabilities based on outcome.
        
        Args:
            outcome: Outcome level (CRITICAL_SUCCESS, SUCCESS, etc.)
            
        Returns:
            Dictionary of compound -> probability
        """
        return TYRE_DISTRIBUTION.get(outcome, TYRE_DISTRIBUTION["SUCCESS"])
    
    def should_keep_soft_for_q3(self, driver: str) -> bool:
        """
        Check if driver should keep a soft set for potential Q3.
        
        Args:
            driver: Driver name
            
        Returns:
            True if driver has enough softs to save one for Q3
        """
        remaining = self.get_remaining_tyres(driver)
        # Keep at least one soft if possible
        return remaining.get("SOFT", 0) > 1
    
    def get_used_compounds_in_session(
        self,
        driver: str,
        session: str
    ) -> List[str]:
        """Get list of compounds used by driver in a session."""
        if driver not in self.allocations:
            return []
        
        allocation = self.allocations[driver]
        return [
            u["compound"] for u in allocation.used_sets
            if u["session"] == session
        ]
