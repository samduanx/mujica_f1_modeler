# F1 Sprint Race System Documentation

## Overview

The Sprint Race System simulates F1 sprint races - 100km short races that determine the starting grid for the main Grand Prix. Based on the 2022 format, sprint races are held at specific circuits with shorter distances and different rules than regular races.

## System Architecture

```
src/sprint/
├── __init__.py                 # Package exports
├── sprint_simulator.py         # Core sprint race simulation
├── starting_grid_connector.py  # Grid position connector
└── drs_config_reader.py       # DRS configuration reader
```

## Sprint Race Tracks (2022 Format)

| Track | GP Name | Distance | Laps | Characteristics |
|-------|---------|----------|------|----------------|
| Imola | Emilia Romagna | 4.909 km | 21 | High downforce, technical, narrow |
| Austria | Red Bull Ring | 4.318 km | 24 | High speed, short lap, 3 DRS zones |
| Sao Paulo | Brazil | 4.309 km | 24 | Anti-clockwise, high altitude |

## Sprint Race Characteristics

- **Distance**: 100 km (approximately 1/3 of normal race)
- **Laps**: 21-24 laps depending on track
- **Pit Stops**: None required (usually)
- **Starting Grid**: Determined by qualifying
- **Result Usage**: Sprint finishing positions become main race grid
- **Points**: Top 8 finishers (8-7-6-5-4-3-2-1)

## Core Components

### SprintRaceSimulator

Main simulator for sprint races:

```python
from src.sprint import SprintRaceSimulator, run_sprint_race

# Run sprint race
results = run_sprint_race("Imola", seed=42)

# Or use the class directly
simulator = SprintRaceSimulator(
    track_name="Austria",
    num_laps=24,
    seed=42,
)

results = simulator.simulate()
```

### StartingGridConnector

Unified connector for providing starting grid positions to races:

```python
from src.sprint import StartingGridConnector, GridSourceType

# From sprint results
connector = StartingGridConnector.from_sprint_results(sprint_results)

# From qualifying results (future)
connector = StartingGridConnector.from_qualifying_results(qualifying_results)

# Manual configuration
connector = StartingGridConnector.manual({
    "Verstappen": 1,
    "Leclerc": 2,
    # ...
})

# Get grid positions for main race
grid_positions = connector.get_starting_grid()
```

### GridSourceType

```python
class GridSourceType(Enum):
    SPRINT = "sprint"       # From sprint race
    QUALIFYING = "qualifying"  # From qualifying (future)
    MANUAL = "manual"       # Manual configuration
```

## Sprint Race Configuration

```python
SPRINT_TRACKS = {
    "Imola": {
        "gp_name": "Imola",
        "track_length_km": 4.909,
        "sprint_laps": 21,
        "base_lap_time": 82.0,
        "drs_zones": 2,
        "characteristics": "high_downforce, technical, narrow",
    },
    "Austria": {
        "gp_name": "Austria",
        "track_length_km": 4.318,
        "sprint_laps": 24,
        "base_lap_time": 68.0,
        "drs_zones": 3,
        "characteristics": "high_speed, short_lap, overtaking",
    },
    "Sao_Paulo": {
        "gp_name": "Brazil",
        "track_length_km": 4.309,
        "sprint_laps": 24,
        "base_lap_time": 71.0,
        "drs_zones": 2,
        "characteristics": "anti_clockwise, high_altitude",
    },
}
```

## Differences from Normal Race

| Feature | Normal Race | Sprint Race |
|---------|-------------|-------------|
| Distance | 300+ km | 100 km |
| Laps | 50-70 | 21-24 |
| Pit Stops | 1-3 required | None (usually) |
| Strategy | Complex | Minimal |
| Points | Full (25-18-15-...) | Top 8 only (8-7-6-5-4-3-2-1) |

## Data Flow

```
Driver Data (Spain GP Ratings)
        ↓
Sprint Race Simulator
        ↓
Sprint Results (Finishing Positions)
        ↓
StartingGridConnector (source_type="sprint")
        ↓
Main Race Simulator (Grid positions set)
```

## Integration with Main System

### Reuses Existing Modules

The sprint system reuses several existing modules:

1. **Driver Data**: Same as Spain GP (`data/spain_team.csv`)
2. **Race Simulation**: Adapted from `enhanced_long_dist_sim.py`
3. **DRS Zones**: Uses track-specific configurations
4. **Tyre System**: Simplified (no mandatory stops)
5. **Incidents**: Same as normal race

### Output Format

Sprint races produce similar outputs to normal races:

```
outputs/sprint_sim/
├── sprint_results_{track}.csv     # Race results
├── sprint_dice_rolls_{track}.csv # Dice rolls
└── sprint_report_{track}.md       # Human-readable report
```

## Usage

### Run Sprint Race

```python
from src.sprint import run_sprint_race

# Run sprint race at Imola
results = run_sprint_race("Imola", seed=42)

print(f"Winner: {results['winner']}")
print(f"Grid positions for main race:")
for pos, driver in results['grid_positions'].items():
    print(f"  {pos}: {driver}")
```

### Run Sprint Weekend

```python
from src.sprint import run_sprint_race, StartingGridConnector
from src.simulation import run_race

# Step 1: Run sprint race
sprint_results = run_sprint_race("Imola", seed=42)

# Step 2: Create connector
connector = StartingGridConnector.from_sprint_results(sprint_results)

# Step 3: Run main race with sprint-determined grid
main_race_results = run_race(
    "Imola",
    grid_connector=connector,
    seed=42
)
```

### Command Line

```bash
# Run sprint race only
uv run python main.py --gp-name Imola --sessions sprint

# Run sprint and main race
uv run python main.py --gp-name Imola --sessions sprint,race
```

## DRS Configuration

The system uses DRS configurations from `src/drs/zones/`:

```python
from src.sprint.drs_config_reader import load_drs_config, get_track_drs_summary

# Load DRS config for sprint track
config = load_drs_config("Austria")

# Get summary
summary = get_track_drs_summary("Austria")
print(f"DRS Zones: {summary['num_zones']}")
print(f"Total Benefit: {summary['total_benefit']}s")
```

## Tyre Strategy

Sprint races typically use minimal tyre strategy:

- **No mandatory pit stops**: 100km is short enough to complete on one set
- **Soft tyre preferred**: Teams typically qualify on softs and start on them
- **One-stop alternative**: If safety car or damage, may need to pit

## Testing

Run sprint system tests:

```bash
# Run sprint demo
uv run python -m src.sprint.sprint_simulator --track Imola

# Or import and run
python -c "from src.sprint import run_sprint_race; print(run_sprint_race('Austria', seed=42))"
```

## Related Documentation

- [F1_SIMULATION_MODEL.md](F1_SIMULATION_MODEL.md) - Base race simulation
- [DRS_SYSTEM.md](DRS_SYSTEM.md) - DRS system
- [QUALIFICATION_SYSTEM.md](QUALIFICATION_SYSTEM.md) - Qualifying system
- [main.py](main.py) - Main entry point for running races
