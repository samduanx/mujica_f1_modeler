# F1 Penalty System

## Overview

The F1 Penalty System provides comprehensive penalty management for the race simulation, including time penalties, drive-through penalties, grid penalties, and penalty points tracking. The system is based on FIA Formula 1 Sporting Regulations.

## 1. Penalty Types

| Penalty Type | Description | Time Impact | Points |
|-------------|-------------|-------------|--------|
| **5-second time penalty** | Added to race time | +5s | 1 |
| **10-second time penalty** | Added to race time | +10s | 2 |
| **15-second time penalty** | Added to race time | +15s | 3 |
| **Drive-through** | Must drive through pit lane | ~20s | 3 |
| **Stop-and-go (5s/10s/15s)** | Must stop in pit box | +5s/10s/15s + stop | 3 |
| **Grid penalty** | Drop positions for next race | Variable | 0 |
| **Back of grid** | Start from last position | Position loss | 0 |
| **Reprimand** | Verbal/written warning | None | 0 |
| **Race ban** | Suspended for races | N/A | 0 |

## 2. System Architecture

### File Structure

```
src/penalties/
├── __init__.py                      # Package exports
├── penalty_types.py                 # PenaltyType enum, Penalty dataclass
├── penalty_manager.py               # Central PenaltyManager class
├── penalty_points.py                # Super Licence points tracking
├── penalty_service.py               # Serving mechanics
├── grid_penalty.py                  # Grid penalties for future races
├── reprimand.py                     # Reprimand tracking
├── integrators/
│   ├── __init__.py
│   ├── overtake_penalties.py       # Overtake collision penalties
│   ├── blue_flag_penalties.py      # Blue flag violations
│   ├── vsc_penalties.py            # VSC/SC violations
│   ├── incident_penalties.py       # General incidents (unsafe release)
│   └── race_simulation_integration.py
└── tests/
    ├── __init__.py
    ├── test_penalty_system.py       # 21 unit tests
    └── test_race_integration.py    # 8 integration tests
```

### Core Components

**PenaltyManager** (`penalty_manager.py`)
- Central coordinator for all penalties
- Methods: `assess_penalty()`, `get_pending_penalties()`, `serve_penalty()`

**PenaltyPoints** (`penalty_points.py`)
- Super Licence points tracking
- 12 points = automatic race ban
- Points expire after 12 months

**PenaltyService** (`penalty_service.py`)
- Penalty serving mechanics
- Pit stop serving with overhead: penalty_time + normal_pit_time + random(0-0.5s)

## 3. Actions That Trigger Penalties

| Action | Typical Penalty | Points |
|--------|-----------------|--------|
| Causing a collision | 5-15s time penalty | 2-3 |
| Leaving track + gaining advantage | 5s time penalty | 1 |
| Blue flag violation | 5s → Drive-through | 1-2 |
| Yellow/VSC flag violation | 5-10s time penalty | 2 |
| Unsafe release | Time loss (no points) | 0 |
| Impeding another driver | 5s time penalty | 2 |
| Pit lane speeding | 5s time penalty | 1 |
| Weaving | 5s time penalty | 1 |

## 4. Key Design Decisions

### 4.1 Time Penalty Serving

- **At Pit Stop**: penalty_time + normal_pit_time + random(0.0-0.5s)
- **After Race**: Added directly to final race time

### 4.2 Unsafe Release

- **No driver penalties** (only team fine in real F1)
- **Time loss to ALL drivers involved** (1-5 seconds based on severity)
- **Max 5 seconds** time loss

### 4.3 Penalty Points

- 12 points = race ban
- Points expire after 12 months (rolling)
- 3 reprimands (2+ driving offenses) = 10-place grid penalty

## 5. Usage Examples

### Basic Usage

```python
from src.penalties import PenaltyManager, PenaltyType, PenaltyPoints

# Initialize
pm = PenaltyManager()
pp = PenaltyPoints()

# Assess penalty
penalty = pm.assess_penalty(
    driver="Verstappen",
    penalty_type=PenaltyType.TIME_5S,
    reason="Causing collision",
    time_assessed=100.0,
    lap_assessed=5,
)

# Add penalty points
pp.add_points("Verstappen", penalty.points, "Collision")

# Check for race ban
if pp.check_race_ban("Verstappen"):
    print("Driver banned!")
```

### Race Integration

```python
from src.penalties.integrators.race_simulation_integration import RacePenaltyIntegration

# Initialize
integration = RacePenaltyIntegration("Spain", 2024)

# Handle overtake collision
result = integration.handle_overtake_collision(
    attacker="Verstappen",
    defender="Hamilton",
    severity=IncidentSeverity.MODERATE,
    race_time=600.0,
    lap=10,
)

# Serve penalty at pit stop
pit_time, served = integration.handle_pit_stop_with_penalties(
    driver="Verstappen",
    lap=15,
    base_pit_time=22.0,
    has_more_pit_stops=True,
)

# Apply post-race penalties
post_race_time = integration.get_post_race_penalty_time("Russell")
```

### Unsafe Release

```python
# Unsafe release gives time loss to ALL drivers involved
result = integration.handle_unsafe_release(
    involved_drivers=["Norris", "Piastri", "Leclerc"],
    severity="minor",  # 1-2 seconds each
    race_time=500.0,
    lap=25,
)

# No penalty points, just time loss
print(f"Time loss: {result['time_losses']}")
```

## 6. Penalty Handlers

### OvertakePenaltyHandler
- MINOR → 5s time penalty (1 point)
- MODERATE → 10s time penalty (2 points)
- MAJOR → Drive-through (3 points)

### BlueFlagPenaltyHandler
- Escalation: warning → warning → 5s → drive-through
- Based on resistance level and offense count

### VSCViolationHandler
- Speed over VSC delta: 5-10s time penalty
- Speed over SC limit: 10s time penalty or Stop-and-go

### IncidentPenaltyHandler
- Unsafe release: Time loss to all drivers (max 5s)
- Impeding: 5s time penalty (2 points)
- Pit lane speeding: 5s time penalty (1 point)
- Weaving: 5s time penalty (1 point)

## 7. Tests

Run all tests:
```bash
uv run python -m src.penalties.tests.test_penalty_system
uv run python -m src.penalties.tests.test_race_integration
```

**Test Results**: 29 tests passing (21 unit + 8 integration)

## 8. Integration with Race Simulation

To integrate with the race simulation:

1. Import the integration module:
```python
from src.penalties.integrators.race_simulation_integration import RacePenaltyIntegration
```

2. Initialize in the simulator:
```python
self.penalty_integration = RacePenaltyIntegration(track_name, year)
```

3. Hook into incidents:
```python
# On overtake collision
self.penalty_integration.handle_overtake_collision(att severity, time, lap)

# On blue flag violation
self.penalty_inacker, defender,tegration.handle_blue_flag_violation(driver, resistance, count, time, lap)
```

4. Handle pit stops:
```python
# When driver pits
pit_time, served = self.penalty_integration.handle_pit_stop_with_penalties(
    driver=driver,
    lap=current_lap,
    base_pit_time=normal_pit_time,
    has_more_pit_stops=will_pit_again,
)
```

5. Apply post-race:
```python
# After race ends
for driver in drivers:
    race_time += self.penalty_integration.get_post_race_penalty_time(driver)
    race_time += self.penalty_integration.get_total_time_loss(driver)
```

## 9. Summary

The F1 Penalty System provides:

- ✅ Comprehensive penalty types (time, drive-through, stop-go, grid, reprimand)
- ✅ Penalty points with 12-month expiry and race ban at 12 points
- ✅ Proper penalty serving mechanics (pit stop vs post-race)
- ✅ Special handling for unsafe release (time loss, no points)
- ✅ Integration with race simulation via `RacePenaltyIntegration`
- ✅ 29 passing tests

All code is in [`src/penalties/`](src/penalties/).
