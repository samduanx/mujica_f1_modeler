# F1 Simulation Model Documentation

## Overview

This F1 simulation system models Formula 1 race dynamics with realistic incident handling, strategy simulation, and performance modeling. The simulation uses a combination of deterministic calculations and stochastic (dice-based) elements to create varied and realistic race outcomes.

## System Architecture

### Core Modules

#### 1. Race Simulation Core (`src/simulation/enhanced_long_dist_sim.py`)

The main simulation engine that orchestrates the race. Key responsibilities:
- Initialize race state and driver data
- Run the main race loop (lap-by-lap simulation)
- Handle safety car and VSC deployments
- Calculate lap times and positions
- Manage pit stops and tyre changes

#### 2. Incident System (`src/incidents/`)

Comprehensive incident handling with multiple incident types:

| Module | Purpose |
|--------|---------|
| `incident_manager.py` | Central coordinator for all incidents |
| `vehicle_fault.py` | Mechanical failure simulation |
| `driver_error.py` | Driver mistake modeling |
| `overtake_incident.py` | Overtake attempt handling |
| `vsc_sc.py` | Virtual Safety Car and Safety Car |
| `red_flag.py` | Race stoppage handling |
| `blue_flag.py` | Blue flag (lapped car) handling |
| `rolling_start.py` | Race start simulation |
| `escalation_dice.py` | Incident escalation mechanics |

#### 3. DRS System (`src/drs/`)

Drag Reduction System modeling:
- `overtake.py` - Overtake attempt mechanics
- `driver_state.py` - Driver-specific DRS behavior
- `overtake_trigger.py` - DRS activation triggers

#### 4. Tyre Degradation (`src/ tyre/`)

Tyre wear modeling:
- `isolated_tyre_degradation.py` - Base degradation curves
- ` tyre_types.py` - Compound characteristics

## Key Simulation Components

### 1. Vehicle Fault System (Modern F1 Realism)

**Problem**: Real F1 cars rarely have mechanical failures (~0.1-0.5% per lap).

**Implementation**:
- Fault probability: 0.1% (top teams), 0.3% (mid-tier), 0.5% (backmarkers)
- Faults now cause **speed degradation** instead of DNF:
  - Minor: 0.1-0.5% speed reduction
  - Moderate: 0.5-1.5% speed reduction
  - Major: 1.5-3% speed reduction
  - Catastrophic: 3-5% speed reduction
- Faults accumulate over the race (compounding degradation)

### 2. Monaco-Specific Patches

Monaco is unique among F1 tracks:

**Overtake Resistance**:
- Position-based defense bonus applied
- Makes it harder to pass drivers ahead

**Pit Stop Strategy**:
- 85% probability of 1-stop strategy (realistic for Monaco)
- Extra stops receive +5 second penalty per additional stop

### 3. Driver Personality Model

Each driver has personality attributes:
- **Aggression** (1-10): Racing style
- **Consistency** (1-10): Performance stability
- **Battle Escalation** (1-10): Wheel-to-wheel behavior
- **Error in Clean Air** (1-10): Mistake frequency

### 4. Standing Start Mechanics

F1 standard for clear weather:
1. Formation lap completed before grid
2. Drivers in starting positions
3. 5-second countdown
4. All lights go out - reaction time roll
5. Position changes possible on run to Turn 1

**Reaction Time Outcomes**:
- 1: Extremely slow (0.4-0.6s)
- 2-3: Slow (0.3-0.5s)
- 4-7: Average (0.2-0.3s)
- 8-9: Good (0.15-0.2s)
- 10: Excellent (<0.15s)

### 5. Safety Car and VSC System

- **SC Probability**: ~2% per lap after lap 3
- **VSC Probability**: ~3% per lap after lap 3
- Duration: 1-6 laps (determined by dice roll)

## Key Parameters and Tuning

### Fault Probability

| Team Tier | Stability | Fault Probability |
|-----------|-----------|-------------------|
| Top (RBR, Ferrari, Mercedes) | ≥97.5 | 0.1% per lap |
| Mid (Aston Martin, Alpine) | 95-97.5 | 0.3% per lap |
| Backmarker (Alfa, Haas) | <95 | 0.5% per lap |

### Speed Degradation

| Severity | Degradation Range | Probability |
|----------|------------------|------------|
| Minor | 0.1-0.5% | 50% |
| Moderate | 0.5-1.5% | 30% |
| Major | 1.5-3% | 15% |
| Catastrophic | 3-5% | 5% |

### Overtake Probability

| Track Type | Base Probability |
|------------|-----------------|
| Normal | 100% |
| Monaco | 1% (with defense bonus) |

### Pit Stop Penalties (Monaco)

| Extra Stops | Time Penalty |
|-------------|--------------|
| 1 (2-stop total) | +5s |
| 2 (3-stop total) | +10s |
| 3+ | +15s per stop |

## How to Run Simulations

### Basic Usage

```bash
# Run simulation for Spain 2024
uv run python src/simulation/enhanced_long_dist_sim.py --gp-name Spain --year 2024

# Run with custom laps
uv run python src/simulation/enhanced_long_dist_sim.py --gp-name Monaco --year 2024 --num-laps 78

# Run with random seed for reproducibility
uv run python src/simulation/enhanced_long_dist_sim.py --gp-name Italy --year 2024 --seed 42
```

### Generate Report

```bash
# After simulation, generate report
uv run python -m simulation.report_generator \
    --track-name Monaco \
    --year 2024 \
    --output-dir outputs/enhanced_sim/Monaco_2024-02-23_19-53-14
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--gp-name` | Grand Prix name | Spain |
| `--year` | Season year | 2024 |
| `--num-laps` | Number of laps | Auto-detected |
| `--seed` | Random seed | None |
| `--no-drs` | Disable DRS | False |
| `--no-incidents` | Disable incidents | False |
| `--csv-file` | Custom driver CSV | Auto |

## Output File Formats

### Race Results CSV

```
position,driver,team,total_time,num_pits,pit_laps,num_incidents,incidents,fault_degradation
1,Max Verstappen,Red Bull Racing,5324.123,1,25,0,,0.0000
2,Lando Norris,McLaren,5341.456,1,26,1,driver_error,0.0034
```

### Dice Rolls CSV

```
timestamp,lap,driver,incident_type,dice_type,dice_result,outcome,details
2024-05-15T14:30:00,0,Max Verstappen,standing_start,d10,7,average,"{""grid_position"": 1}"
2024-05-15T14:35:00,5,Lewis Hamilton,vehicle_fault_check,probability,2,fault_occurred,"{""team"": Mercedes, ...}"
```

### Markdown Report

Comprehensive report including:
- Race summary (positions, times, pit stops)
- Dice rolling statistics
- Safety Car/VSC periods
- Standing start analysis
- Driver incident counts
- Fault degradation summary

## Track Configuration

### Supported Tracks

The system supports multiple tracks with individual characteristics:
- Base lap times
- DRS zones
- Pit stop times
- Strategy patterns

### Track Detection

Tracks are identified by name (case-insensitive):
- "Monaco" or "monaco"
- "Spain" or "spain"
- "Italy" or "italy" (Monza)

## Incident System Details

### Escalation Dice

Incidents can escalate based on dice rolls:
- Initial incident check
- Severity determination
- Time loss calculation
- Potential for multi-lap incidents

### Blue Flag Rules

Lapped cars must yield to leaders:
- Notification when lapped
- Time penalty for ignoring
- Position adjustment

## Tyre Degradation

### Compounds

- **Soft**: Fast but quick wear
- **Medium**: Balanced
- **Hard**: Slow but durable

### Degradation Factors

- Lap count on tyre
- Driver R-Value (skill)
- Track characteristics
- Number of pit stops

## Troubleshooting

### Common Issues

1. **No overtake simulation**: Position changes based on lap times only
2. **Too many faults**: Check fault probability settings
3. **Pit strategy unrealistic**: Verify pit_data CSV exists

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Planned improvements:
- Weather simulation (rain effects)
- Qualifying simulation
- Multi-race championship standings
- Advanced tire warm-up modeling
- Pit stop error modeling
- Team order / team strategy

## License

This simulation is for educational and research purposes.
