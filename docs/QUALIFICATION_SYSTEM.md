# F1 Qualification System Documentation

## Overview

The Qualification System simulates F1 qualifying sessions (Q1/Q2/Q3 for standard races, SQ1/SQ2/SQ3 for sprint races). It integrates with the existing Strategist, Weather, and Incident systems to provide realistic qualifying simulations.

## System Architecture

```
src/qualifying/
├── __init__.py                 # Package exports
├── types.py                    # Core data types
├── session.py                  # Session management (Q1/Q2/Q3)
├── tyre_allocation.py          # Tyre allocation manager
├── incident_handler.py         # Incidents and flags
├── weather_handler.py          # Weather integration
└── tests/
    └── test_qualifying.py     # Unit tests
```

## Session Types

### Standard Qualifying (Grand Prix)

| Session | Duration | Drivers | Eliminated | Grid Positions |
|---------|----------|---------|------------|----------------|
| Q1 | 18 min | All 20 | 5 slowest | 16-20 |
| Q2 | 15 min | 15 remaining | 5 slowest | 11-15 |
| Q3 | 12 min | 10 remaining | None | 1-10 (Pole) |

**Tyre Rules:**
- Free choice in Q1 and Q2
- Q3 participants must use soft tyres (new set)
- All drivers have FREE tyre choice for race start (2022+ rule)

### Sprint Qualifying (Sprint Race)

| Session | Duration | Drivers | Eliminated | Grid Positions |
|---------|----------|---------|------------|----------------|
| SQ1 | 12 min | All 20 | 5 slowest | 16-20 |
| SQ2 | 10 min | 15 remaining | 5 slowest | 11-15 |
| SQ3 | 8 min | 10 remaining | None | 1-10 (Pole) |

**Tyre Rules:**
- SQ1: Must use NEW medium tyres
- SQ2: Must use NEW medium tyres
- SQ3: Must use NEW soft tyres

### Alternative Tyre Allocation (ATA)

| Session | Required Tyre |
|---------|---------------|
| Q1 | Hard |
| Q2 | Medium |
| Q3 | Soft |

## Core Types

### QualifyingSessionType

```python
class QualifyingSessionType(Enum):
    STANDARD = "standard"  # Q1/Q2/Q3
    SPRINT = "sprint"     # SQ1/SQ2/SQ3
    ATA = "ata"           # Alternative Tyre Allocation
```

### QualifyingLap

Represents a complete qualifying lap:

```python
@dataclass
class QualifyingLap:
    driver: str
    session: str  # "Q1", "Q2", "Q3", etc.
    
    # Lap phases (seconds)
    out_lap_time: float
    flying_lap_time: float
    in_lap_time: float
    total_time: float
    
    # Timing
    release_time: float
    crossing_time: float
    
    # Tyre info
    tyre_compound: str
    tyre_condition: str  # new, scrubbed, used
    
    # Track conditions
    track_evolution: float  # Grip improvement
    
    # Result
    valid_lap: bool
    deleted_lap: bool  # Track limits
    best_lap: bool
```

### QualifyingResult

```python
@dataclass
class QualifyingResult:
    driver: str
    team: str
    q1_time: Optional[float]
    q2_time: Optional[float]
    q3_time: Optional[float]
    grid_position: int
    race_start_tyre: str  # Free choice in 2022+
    eliminated_in: Optional[str]  # "Q1", "Q2", or None
```

## Components

### TyreAllocationManager

Manages tyre sets per driver throughout qualifying:

```python
from src.qualifying import TyreAllocationManager

# Initialize
manager = TyreAllocationManager(
    session_type=QualifyingSessionType.STANDARD,
    total_sets=13  # 13 sets for standard, 12 for sprint
)

# Use a tyre set
success = manager.use_tyre_set(driver="Verstappen", compound="SOFT")

# Check remaining
remaining = manager.get_remaining_tyres(driver="Verstappen")
```

### QualifyingSessionManager

Manages Q1/Q2/Q3 elimination flow:

```python
from src.qualifying import QualifyingSessionManager

# Run Q1
q1 = QualifyingSessionManager(
    session_name="Q1",
    duration_minutes=18,
    drivers=all_drivers,
    elimination_count=5
)

q1.start_session()
# ... simulate laps ...
advancing, eliminated = q1.end_session()
```

### QualifyingIncidentHandler

Handles incidents during qualifying:

```python
from src.qualifying import QualifyingIncidentHandler

handler = QualifyingIncidentHandler()

# Check for incidents
incident = handler.check_incident(
    driver="Verstappen",
    driver_dr=92,
    pressure_level=0.8  # High pressure situation
)
```

### QualifyingWeatherHandler

Weather integration for qualifying:

```python
from src.qualifying import QualifyingWeatherHandler

weather = QualifyingWeatherHandler()

# Get tyre recommendation
recommended = weather.get_tyre_recommendation(
    track_condition=TrackCondition.DRY
)
```

## Tyre Distribution

### Standard Sessions

| Roll Result | Soft | Medium | Hard |
|-------------|------|--------|------|
| Critical Success (20) | 95% | 5% | 0% |
| Great Success (16-19) | 85% | 15% | 0% |
| Success (11-15) | 70% | 30% | 0% |
| Partial (6-10) | 50% | 45% | 5% |
| Failure (2-5) | 30% | 60% | 10% |
| Critical Fail (1) | 20% | 50% | 30% |

**Note:** Hard tyres suppressed in standard sessions.

### Sprint Sessions

Only medium and soft available:
- SQ1: Must use NEW medium
- SQ2: Must use NEW medium
- SQ3: Must use NEW soft

## Track Evolution

Track grip improves throughout the session:

```
Evolution = (session_time_elapsed / session_duration) * 0.5  # Up to 0.5s
          + cars_on_track * 0.01  # Rubbering in (up to 0.3s)
Total gain: 0.0 to 0.8 seconds
```

## Usage

### Run Full Qualifying

```python
from src.qualifying import (
    QualifyingSessionManager,
    QualifyingSessionType,
    TyreAllocationManager,
)

# Initialize
session_type = QualifyingSessionType.STANDARD
drivers = load_drivers()
tyres = TyreAllocationManager(session_type=session_type)

# Run Q1
q1 = QualifyingSessionManager("Q1", 18, drivers, 5)
q1.start_session()
# ... simulate laps ...
q1_results = q1.end_session()

# Run Q2 with advancing drivers
q2 = QualifyingSessionManager("Q15", 15, q1_results.advancing, 5)
# ... continue ...

# Run Q3 with top 10
q3 = QualifyingSessionManager("Q3", 12, q2_results.advancing, 0)

# Get final grid
final_grid = q3.get_final_results()
```

### Integration with main.py

```bash
# Run qualifying only
uv run python main.py --gp-name Monaco --sessions qualifying

# Run qualifying and race
uv run python main.py --gp-name Monaco --sessions qualifying,race
```

## Integration Points

### DRS Integration

Uses existing DRS zone configurations from `src/drs/zones/`:

```python
from drs.zones import TRACKS

# Get DRS benefit for qualifying
drs_config = TRACKS["Monza"]()
total_benefit = sum(zone.qualifying_benefit for zone in drs_config.zones)
```

### Weather Integration

Uses existing weather system:

```python
from src.weather import WeatherGenerator

weather = WeatherGenerator(seed=42)
initial = weather.generate_initial_weather(track_name)
```

### Strategist Integration

Decisions use dice-based mechanics:

```python
from src.strategist import StrategistDiceRoller

roller = StrategistDiceRoller(strategist_profile)
roll = roller.roll_d20()
# Apply modifiers and determine outcome
```

## Testing

Run qualification tests:

```bash
uv run python -m src.qualifying.tests.test_qualifying
```

## Related Documentation

- [STRATEGIST_SYSTEM.md](STRATEGIST_SYSTEM.md) - Strategist decisions
- [WEATHER_SYSTEM.md](WEATHER_SYSTEM.md) - Weather system
- [DRS_SYSTEM.md](DRS_SYSTEM.md) - DRS configuration
- [F1_SIMULATION_MODEL.md](F1_SIMULATION_MODEL.md) - Race simulation
