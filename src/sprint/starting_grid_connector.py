"""
Starting Grid Connector - Unified interface for providing starting grid positions.

This module provides a unified connector that can accept starting grid positions
from various sources:
- Sprint race results
- Qualifying session results
- Manual configuration

Usage:
    # From sprint race results
    connector = StartingGridConnector.from_sprint_results(sprint_results)

    # From qualifying results (for future implementation)
    connector = StartingGridConnector.from_qualifying_results(qualifying_results)

    # Manual configuration
    connector = StartingGridConnector.manual(grid_positions)

    # Get grid positions for main race
    grid_positions = connector.get_starting_grid()
"""

from enum import Enum
from typing import Dict, List, Optional, Any
import pandas as pd


class GridSourceType(Enum):
    """Source type for starting grid positions."""

    SPRINT = "sprint"
    QUALIFYING = "qualifying"
    MANUAL = "manual"


class StartingGridConnector:
    """
    Unified connector for providing starting grid positions to races.

    Can accept results from sprint races, qualifying sessions, or manual configuration.
    Provides a consistent interface for the main race simulator to get grid positions.
    """

    def __init__(
        self,
        source_type: GridSourceType,
        grid_positions: Dict[str, int],
        source_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the StartingGridConnector.

        Args:
            source_type: Type of source (sprint, qualifying, or manual)
            grid_positions: Dictionary mapping driver_name -> grid_position
            source_data: Optional additional data from the source (results, times, etc.)
        """
        self.source_type = source_type
        self.grid_positions = grid_positions
        self.source_data = source_data or {}

        # Validate grid positions
        self._validate_grid_positions()

    def _validate_grid_positions(self) -> None:
        """Validate that grid positions are valid."""
        if not self.grid_positions:
            raise ValueError("Grid positions cannot be empty")

        # Check for duplicate positions
        positions = list(self.grid_positions.values())
        if len(positions) != len(set(positions)):
            raise ValueError("Duplicate grid positions detected")

        # Check that positions start from 1
        if min(positions) < 1:
            raise ValueError("Grid positions must start from 1")

    @classmethod
    def from_sprint_results(
        cls,
        sprint_results: Dict[str, Any],
        results_csv_path: Optional[str] = None,
    ) -> "StartingGridConnector":
        """
        Create a StartingGridConnector from sprint race results.

        Args:
            sprint_results: Dictionary containing sprint race results
            results_csv_path: Optional path to sprint results CSV file

        Returns:
            StartingGridConnector configured with sprint race finishing positions
        """
        grid_positions = {}

        # Try to get results from the dictionary
        if "final_positions" in sprint_results and sprint_results["final_positions"]:
            # Results already processed
            for position, driver in sprint_results["final_positions"].items():
                grid_positions[driver] = int(position)
        elif "results" in sprint_results and sprint_results["results"]:
            # Extract from results dictionary
            for driver, data in sprint_results["results"].items():
                if isinstance(data, dict) and "Position" in data:
                    grid_positions[driver] = int(data["Position"])
        elif "results_df" in sprint_results:
            # Results as DataFrame
            df = sprint_results["results_df"]
            for _, row in df.iterrows():
                driver = row.get("Driver", row.get("driver", ""))
                position = row.get("Position", row.get("position", 0))
                if driver and position:
                    grid_positions[driver] = int(position)
        elif results_csv_path:
            # Load from CSV file
            df = pd.read_csv(results_csv_path)
            for _, row in df.iterrows():
                driver = row.get("Driver", row.get("driver", ""))
                position = row.get("Position", row.get("position", 0))
                if driver and position:
                    grid_positions[driver] = int(position)
        else:
            raise ValueError("No valid sprint results found")

        return cls(
            source_type=GridSourceType.SPRINT,
            grid_positions=grid_positions,
            source_data={
                "sprint_results": sprint_results,
                "results_csv_path": results_csv_path,
            },
        )

    @classmethod
    def from_qualifying_results(
        cls,
        qualifying_results: Dict[str, Any],
        results_csv_path: Optional[str] = None,
    ) -> "StartingGridConnector":
        """
        Create a StartingGridConnector from qualifying session results.

        Args:
            qualifying_results: Dictionary containing qualifying results
            results_csv_path: Optional path to qualifying results CSV file

        Returns:
            StartingGridConnector configured with qualifying positions
        """
        grid_positions = {}

        # Try to get results from the dictionary
        if "grid_positions" in qualifying_results:
            # Results already processed
            grid_positions = qualifying_results["grid_positions"]
        elif "results_df" in qualifying_results:
            # Results as DataFrame
            df = qualifying_results["results_df"]
            for _, row in df.iterrows():
                driver = row.get("Driver", row.get("driver", ""))
                position = row.get("GridPosition", row.get("grid_position", 0))
                if driver and position:
                    grid_positions[driver] = int(position)
        elif results_csv_path:
            # Load from CSV file
            df = pd.read_csv(results_csv_path)
            for _, row in df.iterrows():
                driver = row.get("Driver", row.get("driver", ""))
                position = row.get("GridPosition", row.get("grid_position", 0))
                if driver and position:
                    grid_positions[driver] = int(position)
        else:
            raise ValueError("No valid qualifying results found")

        return cls(
            source_type=GridSourceType.QUALIFYING,
            grid_positions=grid_positions,
            source_data={
                "qualifying_results": qualifying_results,
                "results_csv_path": results_csv_path,
            },
        )

    @classmethod
    def manual(
        cls,
        grid_positions: Dict[str, int],
        description: Optional[str] = None,
    ) -> "StartingGridConnector":
        """
        Create a StartingGridConnector with manually specified grid positions.

        Args:
            grid_positions: Dictionary mapping driver_name -> grid_position
            description: Optional description of the manual configuration

        Returns:
            StartingGridConnector with manual grid positions
        """
        return cls(
            source_type=GridSourceType.MANUAL,
            grid_positions=grid_positions,
            source_data={
                "description": description or "Manual grid configuration",
            },
        )

    def get_starting_grid(self) -> Dict[str, int]:
        """
        Get the starting grid positions.

        Returns:
            Dictionary mapping driver_name -> grid_position
        """
        return self.grid_positions.copy()

    def get_driver_position(self, driver_name: str) -> Optional[int]:
        """
        Get the grid position for a specific driver.

        Args:
            driver_name: Name of the driver

        Returns:
            Grid position or None if driver not found
        """
        return self.grid_positions.get(driver_name)

    def get_sorted_grid(self) -> List[tuple]:
        """
        Get the grid sorted by position.

        Returns:
            List of (position, driver_name) tuples sorted by position
        """
        return sorted(
            [(pos, driver) for driver, pos in self.grid_positions.items()],
            key=lambda x: x[0],
        )

    def apply_to_driver_data(self, driver_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Apply grid positions to driver data dictionary.

        Args:
            driver_data: Dictionary of driver data (driver_name -> driver_info)

        Returns:
            Updated driver data with grid_position field added
        """
        updated_data = {}
        for driver_name, driver_info in driver_data.items():
            updated_info = driver_info.copy()
            if driver_name in self.grid_positions:
                updated_info["grid_position"] = self.grid_positions[driver_name]
            updated_data[driver_name] = updated_info
        return updated_data

    def get_source_info(self) -> Dict[str, Any]:
        """
        Get information about the source of the grid positions.

        Returns:
            Dictionary with source type and metadata
        """
        return {
            "source_type": self.source_type.value,
            "num_drivers": len(self.grid_positions),
            "source_data": self.source_data,
        }

    def __repr__(self) -> str:
        """String representation of the connector."""
        return f"StartingGridConnector(source_type={self.source_type.value}, drivers={len(self.grid_positions)})"
