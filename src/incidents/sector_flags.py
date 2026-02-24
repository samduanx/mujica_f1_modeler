"""
Sector Flag System.

Manages yellow flags for track sectors.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime


class SectorFlag(Enum):
    """Sector flag states"""
    GREEN = "green"
    YELLOW = "yellow"
    DOUBLE_YELLOW = "double_yellow"


@dataclass
class SectorFlagState:
    """State of a single sector's flags"""
    sector_number: int
    flag: SectorFlag = SectorFlag.GREEN
    active_incidents: List = field(default_factory=list)
    flag_time: float = 0.0  # Race time when flag was set
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "sector": self.sector_number,
            "flag": self.flag.value,
            "active_incidents": len(self.active_incidents),
            "flag_time": self.flag_time,
        }


class SectorFlagManager:
    """
    Manage sector flags during race.
    
    Tracks yellow/double yellow flags for each sector and
    determines when overtaking should be prohibited.
    """
    
    def __init__(self, num_sectors: int = 3):
        """
        Initialize sector flag manager.
        
        Args:
            num_sectors: Number of track sectors (typically 3)
        """
        self.num_sectors = num_sectors
        self.sectors: Dict[int, SectorFlagState] = {
            i: SectorFlagState(sector_number=i)
            for i in range(1, num_sectors + 1)
        }
        self.flag_history: List[Dict] = []
        
    def set_yellow_flag(
        self,
        sector: int,
        incident,
        race_time: float,
        double_yellow: bool = False
    ) -> SectorFlag:
        """
        Set yellow flag for a sector.
        
        Args:
            sector: Sector number (1-3)
            incident: The incident causing the flag
            race_time: Current race time
            double_yellow: Whether to set double yellow
            
        Returns:
            New flag state
        """
        if sector not in self.sectors:
            raise ValueError(f"Invalid sector: {sector}")
            
        flag = SectorFlag.DOUBLE_YELLOW if double_yellow else SectorFlag.YELLOW
        sector_state = self.sectors[sector]
        
        # Log the change
        if sector_state.flag != flag:
            self.flag_history.append({
                "time": race_time,
                "sector": sector,
                "old_flag": sector_state.flag.value,
                "new_flag": flag.value,
                "incident_type": incident.incident_type.value if hasattr(incident, 'incident_type') else "unknown",
            })
            
        sector_state.flag = flag
        sector_state.active_incidents.append(incident)
        sector_state.flag_time = race_time
        
        return flag
    
    def clear_yellow_flag(self, sector: int, race_time: float) -> SectorFlag:
        """
        Clear yellow flag when incident resolved.
        
        Args:
            sector: Sector number
            race_time: Current race time
            
        Returns:
            New flag state (always GREEN)
        """
        if sector not in self.sectors:
            raise ValueError(f"Invalid sector: {sector}")
            
        sector_state = self.sectors[sector]
        
        if sector_state.flag != SectorFlag.GREEN:
            self.flag_history.append({
                "time": race_time,
                "sector": sector,
                "old_flag": sector_state.flag.value,
                "new_flag": SectorFlag.GREEN.value,
                "incident_cleared": True,
            })
            
        sector_state.flag = SectorFlag.GREEN
        sector_state.active_incidents = []
        
        return SectorFlag.GREEN
    
    def get_flag_state(self, sector: int) -> SectorFlag:
        """Get current flag state for sector"""
        if sector not in self.sectors:
            return SectorFlag.GREEN
        return self.sectors[sector].flag
    
    def is_yellow_flag(self, sector: int) -> bool:
        """Check if sector has yellow flag"""
        return self.get_flag_state(sector) in [
            SectorFlag.YELLOW,
            SectorFlag.DOUBLE_YELLOW
        ]
    
    def is_double_yellow(self, sector: int) -> bool:
        """Check if sector has double yellow flag"""
        return self.get_flag_state(sector) == SectorFlag.DOUBLE_YELLOW
    
    def get_all_flagged_sectors(self) -> List[int]:
        """Get list of sectors with any yellow flag"""
        return [
            sector_num
            for sector_num, state in self.sectors.items()
            if state.flag != SectorFlag.GREEN
        ]
    
    def can_overtake(self, sector: int) -> bool:
        """
        Check if overtaking allowed in sector.
        
        Returns False if any yellow flag is active.
        """
        return self.get_flag_state(sector) == SectorFlag.GREEN
    
    def get_speed_limit_factor(self, sector: int) -> Optional[float]:
        """
        Get speed limit factor for sector.
        
        Returns:
            Factor to multiply lap time by, or None if no limit
        """
        flag = self.get_flag_state(sector)
        
        if flag == SectorFlag.YELLOW:
            # Single yellow - no speed limit, just no overtaking
            return None
        elif flag == SectorFlag.DOUBLE_YELLOW:
            # Double yellow - significantly reduced speed
            return 1.12  # 12% slower
            
        return None
    
    def get_full_state(self) -> Dict[int, Dict]:
        """Get full state of all sectors"""
        return {
            sector_num: state.to_dict()
            for sector_num, state in self.sectors.items()
        }
    
    def reset(self):
        """Reset all flags for new race"""
        for sector_state in self.sectors.values():
            sector_state.flag = SectorFlag.GREEN
            sector_state.active_incidents = []
            sector_state.flag_time = 0.0
        self.flag_history = []
    
    def get_active_flags_summary(self) -> Dict:
        """Get summary of currently active flags"""
        yellow_sectors = []
        double_yellow_sectors = []
        
        for sector_num, state in self.sectors.items():
            if state.flag == SectorFlag.YELLOW:
                yellow_sectors.append(sector_num)
            elif state.flag == SectorFlag.DOUBLE_YELLOW:
                double_yellow_sectors.append(sector_num)
                
        return {
            "yellow": yellow_sectors,
            "double_yellow": double_yellow_sectors,
            "total_flagged": len(yellow_sectors) + len(double_yellow_sectors),
        }


class YellowFlagImpact:
    """
    Calculate impact of yellow flags on driver behavior.
    """
    
    def __init__(self, flag_manager: SectorFlagManager):
        self.flag_manager = flag_manager
    
    def get_sector_impact(
        self,
        sector: int,
        base_lap_time: float
    ) -> Dict:
        """
        Get impact of yellow flags on a sector.
        
        Returns:
            Dict with can_overtake and speed_limit
        """
        flag = self.flag_manager.get_flag_state(sector)
        
        if flag == SectorFlag.GREEN:
            return {
                "can_overtake": True,
                "speed_limit": None,
                "flag": "green"
            }
        elif flag == SectorFlag.YELLOW:
            return {
                "can_overtake": False,
                "speed_limit": None,
                "flag": "yellow"
            }
        else:  # DOUBLE_YELLOW
            return {
                "can_overtake": False,
                "speed_limit": base_lap_time * 1.12,
                "flag": "double_yellow"
            }
