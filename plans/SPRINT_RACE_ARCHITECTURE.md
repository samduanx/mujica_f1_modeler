# Sprint Race System Architecture

## Overview

This document outlines the architecture for implementing F1 Sprint Race support in the Mujica F1 Modeler system. Sprint races are 100km short races that set the starting grid for the main Grand Prix.

## 2022 Sprint Race Tracks

Based on the 2022 F1 season, sprint races were held at:

1. **Imola (Italy)** - Autodromo Enzo e Dino Ferrari
   - Track length: 4.909 km
   - Sprint laps: ~21 laps (100km)
   - Characteristics: High downforce, technical, narrow

2. **Austria** - Red Bull Ring
   - Track length: 4.318 km
   - Sprint laps: ~24 laps (100km)
   - Characteristics: Short lap, high speed, multiple DRS zones

3. **Sao Paulo (Brazil)** - Autodromo Jose Carlos Pace (Interlagos)
   - Track length: 4.309 km
   - Sprint laps: ~24 laps (100km)
   - Characteristics: High altitude, anti-clockwise, good for overtaking

## Sprint Race Characteristics

- **Distance**: 100 km (approximately 1/3 of normal race distance)
- **Pit Stops**: None required (only for damage or weather)
- **Starting Grid**: Determined by qualifying (not yet implemented, use default/random)
- **Result Usage**: Sprint finishing positions become the main race starting grid
- **Points**: Top 8 finishers receive points (8-7-6-5-4-3-2-1)

## Architecture Components

### 1. Sprint Race Simulator (`src/sprint/`)

```
src/sprint/
├── __init__.py                    # Module exports
├── sprint_simulator.py            # Core sprint race simulation
├── starting_grid_connector.py     # Unified connector for grid positions
└── tracks/                        # Sprint-specific configurations
    ├── __init__.py
    ├── imola.py                   # Imola sprint config
    ├── austria.py                 # Austria sprint config
    └── sao_paulo.py               # Brazil sprint config
```

### 2. DRS Zone Configurations

Create DRS configurations for the three tracks in `src/drs/zones/`:

- `imola_2024.py` - Imola DRS zones (2 zones)
- `austria_2024.py` - Austria DRS zones (3 zones)
- `brazil_2024.py` - Brazil DRS zones (2 zones)

### 3. Unified StartingGridConnector

```python
class StartingGridConnector:
    """
    Unified connector for providing starting grid positions to races.
    Can accept results from sprint races, qualifying, or manual configuration.
    """

    def __init__(self, source_type: str, results_data: dict):
        """
        Args:
            source_type: "sprint", "qualifying", or "manual"
            results_data: Race results or qualifying times
        """

    def get_starting_grid(self) -> Dict[str, int]:
        """Returns driver_name -> grid_position mapping"""
```

### 4. Sprint Race Configuration

Track configurations for sprint races:

```python
SPRINT_TRACKS = {
    "Imola": {
        "gp_name": "Italy",           # For track characteristics lookup
        "sprint_laps": 21,
        "track_length_km": 4.909,
        "drs_zones": 2,
    },
    "Austria": {
        "gp_name": "Austria",
        "sprint_laps": 24,
        "track_length_km": 4.318,
        "drs_zones": 3,
    },
    "Sao_Paulo": {
        "gp_name": "Brazil",
        "sprint_laps": 24,
        "track_length_km": 4.309,
        "drs_zones": 2,
    },
}
```

## Data Flow

```mermaid
flowchart LR
    A[Driver Data<br/>Spain GP Ratings] --> B[Sprint Race Simulator]
    B --> C[Sprint Results<br/>Finishing Positions]
    C --> D[StartingGridConnector<br/>source_type="sprint"]
    D --> E[Main Race Simulator<br/>Grid positions set]
    F[Future Qualifying] --> D
    D --> E
```

## Integration with Existing System

### 1. Driver Data

Sprint races use the same driver ratings as Spain GP:
- Same `R_Value` and `DR_Value` calculations
- Same team performance characteristics
- Same driver skills system integration

### 2. Race Simulation Differences

| Feature | Normal Race | Sprint Race |
|---------|-------------|-------------|
| Distance | 300+ km | 100 km |
| Laps | 50-70 | 21-24 |
| Pit Stops | 1-3 required | None (usually) |
| Strategy | Complex | Minimal |
| Points | Full points | Top 8 only |

### 3. Output Format

Sprint races produce the same output format as normal races:
- `sprint_results_{track}.csv` - Race results
- `sprint_rolls_{track}.csv` - Dice rolls
- `sprint_report_{track}.md` - Human-readable report

## Implementation Plan

### Phase 1: Core Sprint Simulator
1. Create `src/sprint/sprint_simulator.py` - Adapted from `enhanced_long_dist_sim.py`
2. Simplify for no-pit-stop scenario
3. Configure sprint-specific lap counts

### Phase 2: DRS Configurations
1. Create DRS zone configs for Imola, Austria, Brazil
2. Register in `src/drs/zones/__init__.py`

### Phase 3: StartingGridConnector
1. Create unified connector class
2. Support sprint results and qualifying results
3. Interface with main race simulator

### Phase 4: Integration
1. Create sprint race entry point
2. Add sprint tracks to main.py
3. Test end-to-end flow

## Usage Example

```python
# Run sprint race
sprint_results = run_sprint_race("Imola", seed=42)

# Create connector from sprint results
connector = StartingGridConnector(
    source_type="sprint",
    results_data=sprint_results
)

# Run main race with sprint-determined grid
main_race_results = run_race(
    "Imola",
    grid_connector=connector,
    seed=42
)
```

## File Locations

- Sprint module: `src/sprint/`
- DRS configs: `src/drs/zones/imola_2024.py`, `austria_2024.py`, `brazil_2024.py`
- Driver data: `data/spain_team.csv` (reused)
- Track characteristics: `data/track_characteristics.csv` (existing)
- Output: `outputs/sprint_sim/`