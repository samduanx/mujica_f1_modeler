# Mujica F1 Modeler - Architecture Documentation

## Overview

Mujica F1 Modeler is a **Formula 1 race simulation system** written in Python. It simulates complete Grand Prix races with realistic modeling of:
- Driver performance differentiation (R_Value, DR_Value)
- Tire degradation with cliff effects
- Pit stop strategies
- Start/launch simulations
- Track characteristics
- DRS (Drag Reduction System) simulation

The system is designed for "anke" (dice-rolling narrative) fan-fiction, creating realistic and dramatic race simulations.

## Project Structure

```
mujica_f1_modeler/
├── main.py                      # Entry point
├── README.md                    # Project documentation
├── pyproject.toml              # Python project configuration
├── .gitignore                  # Git ignore rules
├── uv.lock                     # UV lock file
├── .python-version             # Python version specification
├── .tool-versions              # Tool versions
├── src/                        # Source code directory
│   ├── drs/                   # DRS simulation module
│   │   ├── __init__.py
│   │   ├── simulator.py        # Main DRS simulation engine
│   │   ├── base_config.py      # Base configuration classes
│   │   ├── driver_state.py     # Driver state tracking
│   │   ├── run_prototype.py    # Prototype runner
│   │   └── zones/              # Track-specific configurations
│   │       ├── __init__.py
│   │       ├── monaco_2024.py
│   │       └── monza_2024.py
│   └── utils/                  # Utility scripts
│       ├── align_tracks.py
│       ├── cleanup_files.py
│       ├── fastest_lap_emu.py
│       ├── fix_table_paths.py
│       ├── get_box_window.py
│       ├── get_fastest_lap.py
│       ├── isolated_tyre_degradation.py
│       ├── long_dist_sim_with_box.py
│       ├── pirelli_data_downloader.py
│       ├── t_r_compare.py
│       ├── t_r_line.py
│       ├── t_r_nonlinear.py
│       ├── tyre_degrade_sim_compensated.py
│       └── tyre_types.py
├── docs/                       # Documentation
│   └── ARCHITECTURE.md         # This file
├── tables/                      # Data tables
├── outputs/                     # Output files and figures
│   └── figs/                    # Pirelli reference images
```

## DRS Simulation Module (src/drs/)

### Core Components

#### 1. Simulator (`simulator.py`)

The main DRS simulation engine using time-stepped intervals.

**Key Classes:**
- `SimulationConfig`: Configuration for DRS simulation runs
- `TimeSteppedDRSSimulator`: Main DRS simulation engine

**Key Features:**
- 0.2-second time resolution intervals
- DRS activation rules (within 1 second of car ahead, not first 2 laps)
- Time gain calculations per DRS zone
- Race position tracking

#### 2. Base Configuration (`base_config.py`)

Abstract base classes for track configurations.

**Key Classes:**
- `TrackDifficulty`: Track classification (LOW, MEDIUM, HIGH)
- `DRSZone`: Defines a DRS zone on the track
- `SectorConfig`: Configuration for one sector
- `DRSSettings`: Global DRS settings for the race
- `TrackDRSConfig`: Complete DRS configuration for a track

#### 3. Driver State (`driver_state.py`)

State tracking for drivers during simulation.

**Key Classes:**
- `DriverRaceState`: Complete driver state during race
- `DriverTestData`: Simplified driver data for testing

#### 4. Track Zones (`zones/`)

Track-specific DRS zone configurations.

**Files:**
- `monaco_2024.py`: Monaco Grand Prix configuration
- `monza_2024.py`: Monza Grand Prix configuration

### DRS Simulation Design

#### Resolution

- **Time Resolution**: 0.2 seconds (200ms intervals)
- **DRS Zones**: Distance-based (meters from start line)
- **Detection Point**: Located ~1 second before DRS zone

#### DRS Rules

1. DRS must be enabled (not first 2 laps)
2. Must be within 1 second of car ahead at detection point
3. DRS disabled on first lap of race

#### Track Characteristics

| Track Type | DRS Benefit | Example |
|------------|-------------|---------|
| **Power tracks** (Monza, Spa) | 0.4-0.6s | Long straights |
| **Balanced tracks** (Spain, Bahrain) | 0.25-0.4s | Medium straights |
| **Technical tracks** (Monaco, Hungary) | 0.1-0.15s | Tight corners |

### Usage Example

```python
from drs import TimeSteppedDRSSimulator
from drs.zones import monaco_2024
from drs.driver_state import create_test_driver_states

# Get Monaco configuration
config = monaco_2024.get_config()

# Create driver states
drivers = create_test_driver_states()

# Create simulator
simulator = TimeSteppedDRSSimulator(config, drivers)

# Run simulation
results = simulator.simulate_race(num_laps=78)
```

## Utility Scripts (src/utils/)

### Data Processing

| Script | Purpose |
|--------|---------|
| `align_tracks.py` | Align track names with FastF1 |
| `fastest_lap_emu.py` | R-value validation |
| `get_fastest_lap.py` | Extract fastest lap data |
| `pirelli_data_downloader.py` | Download Pirelli data |

### Simulation Scripts

| Script | Purpose |
|--------|---------|
| `long_dist_sim_with_box.py` | Long distance race simulation |
| `isolated_tyre_degradation.py` | Tire degradation analysis |
| `tyre_degrade_sim_compensated.py` | Compensated degradation |
| `tyre_types.py` | Tire type definitions |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `cleanup_files.py` | Clean and organize files |
| `fix_table_paths.py` | Fix table path references |
| `get_box_window.py` | Get pit box window |
| `t_r_compare.py` | Compare T-R relationships |
| `t_r_line.py` | Linear T-R model |
| `t_r_nonlinear.py` | Non-linear T-R model |

## Dependencies

```
bs4>=0.0.2
fastf1>=3.6.1
openpyxl>=3.1.5
pyqt6>=6.10.0
seaborn>=0.13.2
thefuzz>=0.22.1
tqdm>=4.67.1
```

## Usage

### Run Race Simulation

```bash
python main.py --gp-name Spain --year 2022
```

### Run DRS Prototype

```bash
python -m drs.run_prototype
```

### Development

```bash
uv pip install -e .
uv run python main.py --gp-name Monaco
```

## Output Files

```
outputs/
├── long_dist_sim/
│   ├── figs/
│   │   ├── spain_position_progression.png
│   │   └── spain_laptime_scatter.png
│   └── reports/
│       └── spain_race_report_YYYYMMDD_HHMMSS.md
└── figs/
    └── pirelli_2022_f1_images/
        ├── bahrain/
        ├── monaco/
        └── ...
```

## Mathematical Models

### Lap Time Calculation

```
Lap_Time = Base_Lap + Degradation×10 + Noise
```

Where:
- `Base_Lap = 95.0 - (R_Value - 288) × 0.05`
- `Degradation = f(laps_on_tire, compound, track)`
- `Noise ~ Normal(0, σ_DR)` where σ_DR depends on DR value

### Tire Degradation

```
M(laps) = 1 + a(1-e^(-k1×laps)) + b(1-e^(-k2×laps)) + cliff_magnitude × sigmoid(laps - cliff_lap)
```

### DRS Time Gain

DRS gain varies by track:
- **Monza**: 0.50-0.60s (maximum benefit)
- **Monaco**: 0.10-0.15s (limited benefit)

---

## Overtake System (Confronting Dice)

### Overview

The overtake system uses **Confronting Dice** mechanics where each driver rolls their own 1d10 for dramatic board-game-style tension.

**Key Features**:
- **Each driver rolls 1d10** (not a single roll with modifiers)
- **Higher total wins** (tie goes to defender)
- **R Rating**: Pace advantage from interval data
- **DR Value**: Racecraft modifier `(DR-80)/2`

### Three Overtake Situations

| Category | Location | Description |
|----------|----------|-------------|
| **A: DRS Zone** | Within active DRS zone | Equipment battle, DRS bonuses |
| **B: End of DRS** | 100m after DRS zone | Corner entry, technical battle |
| **C: Elsewhere** | Non-DRS areas | Pure racing/craft battle |

### Dice Formula

```
ATTACKER Total = 1d10 + DR_Attack + Situation_Mods
DEFENDER Total = 1d10 + DR_Defend + Situation_Mods

Winner = Higher Total (Tie = Defender)
```

### DR Modifier

```python
DR_Modifier = (DR_Value - 80) / 2  # Range: -5 to +6
```

### Push Mechanic

If defender wins by ≤3, attacker can "push":
- Roll 1d6, add to original total
- Must still beat defender
- Risk: +2 tyre degradation if push fails

### Documentation

See [`docs/OVERTAKE_SYSTEM_DESIGN.md`](docs/OVERTAKE_SYSTEM_DESIGN.md) for complete technical specification.

See [`docs/OVERTAKE_SYSTEM_DIAGRAM.md`](docs/OVERTAKE_SYSTEM_DIAGRAM.md) for visual flowcharts.

See [`docs/OVERTAKE_IMPLEMENTATION_PLAN.md`](docs/OVERTAKE_IMPLEMENTATION_PLAN.md) for Code mode plan.

---

## License

This project is open source for fan-fiction purposes. Data may have copyright.
