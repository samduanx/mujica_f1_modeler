# F1 Driver Skills System Documentation

## Overview

The Driver Skills System adds character and strategic depth to F1 race simulations by giving each driver unique skills that modify their performance under specific conditions. Based on `data/driver_ratings.csv`, each driver has 1-2 unique skills that can activate during races, qualifying, or specific situations.

## System Architecture

```
src/skills/
├── __init__.py                 # Package exports
├── skill_types.py              # Core data types and enums
├── skill_parser.py             # Skill parsing from CSV
├── skill_context.py            # Context for skill activation
├── skill_effects.py            # Effect calculation
├── driver_skill_manager.py     # Central skill manager
└── tests/
    └── test_skills.py         # Unit tests
```

## Core Types

### SkillTrigger

Defines when a skill can activate:

| Trigger | Description |
|---------|-------------|
| `WEATHER_RAIN` | Rain conditions (any intensity) |
| `WEATHER_HEAVY_RAIN` | Heavy rain specifically |
| `QUALIFYING_Q1/Q2/Q3` | Specific qualifying sessions |
| `DEFENDING` | Defending position |
| `ATTACKING` | Attacking/overtaking |
| `IN_DRS_ZONE` | In DRS zone |
| `START` | Race start/launch |
| `TIRE_CLIFF` | After tire degradation cliff |
| `TEAM_ORDER` | Team order situation |
| `EVERY_RACE` | Always applied |

### SkillEffectType

| Effect | Description |
|--------|-------------|
| `RATING_BOOST` | Direct R value boost |
| `RATING_PENALTY` | R value penalty |
| `DICE_MODIFIER` | Modify dice roll |
| `DICE_CHANCE` | Chance-based activation |
| `EXTRA_DICE_CHECK` | Requires extra dice roll |
| `PREVENT_INCIDENT` | Prevent certain incidents |
| `TIRE_MODIFIER` | Modify tire degradation |

## Skill Categories

### Weather Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Verstappen | 老潘课堂 | +0.5 R in rain |
| Stroll | 直感A | +0.3 R when defending or in rain |

### Qualifying Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Leclerc | 勒一圈 | +0.5 R in qualifying |
| Hamilton | 刘一圈 | +0.5 R in qualifying |
| Magnussen | 排位神车 | +0.8 R in qualifying |

### Defense Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Sainz | Smooth Operator | +0.3 R when defending |
| Alonso | WIDELONSO | +0.8 R when defending |
| Ocon | 狮子 | +0.5 R when defending |
| Zhou | WIDEZHOU | +0.5 R when defending |

### Attack Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Hamilton | 振金超车 | Dice-based R boost when overtaking |
| Leclerc | 极限哥 | +0.5 R in DRS zone for 3+ laps |
| Gasly | 斗小牛士 | +0.5 R |

### Tire Management Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Perez | 保胎大师 | -0.3 R loss after tire cliff |
| Albon | 保胎大师 | -0.3 R loss after tire cliff |

### Start Skills

| Driver | Skill | Effect |
|--------|-------|--------|
| Bottas | 昏厥起步 | -0.5 R at start |
| Zhou | 昏厥起步 | -0.5 R at start |

## Usage

### Basic Usage

```python
from src.skills import get_skill_manager, SkillContext

# Get the skill manager
skill_mgr = get_skill_manager()

# Create context for skill check
context = SkillContext(
    session_type=SessionType.RACE,
    lap_number=10,
    is_defending=True,
    weather_condition=WeatherCondition.LIGHT_RAIN,
)

# Get adjusted R value
adjusted_r, modifier, activations = skill_mgr.get_adjusted_r_value(
    driver="Verstappen",
    base_r=100.5,
    context=context,
)
```

### Skill Context

The `SkillContext` class provides context for skill activation:

```python
@dataclass
class SkillContext:
    session_type: SessionType          # RACE, QUALIFYING, SPRINT
    lap_number: int
    weather_condition: WeatherCondition  # CLEAR, LIGHT_RAIN, etc.
    track_condition: TrackCondition    # DRY, WET, etc.
    is_defending: bool = False
    is_attacking: bool = False
    drs_zone_laps: int = 0
    tire_age: int = 0
    position: int = 1
    gap_to_ahead: float = 0.0
```

## Integration Points

### Lap Time Calculation

Skills modify the base R value before lap time calculation:

```python
def calculate_lap_time(driver, base_r, context, skill_mgr):
    # Get skill-modified R value
    adjusted_r, modifier, activations = skill_mgr.get_adjusted_r_value(
        driver=driver,
        base_r=base_r,
        context=context,
    )
    
    # Calculate lap time with adjusted R
    lap_time = calculate_lap_time_from_r(adjusted_r, track)
    return lap_time, modifier, activations
```

### Overtake System

Defense and attack skills modify confrontation dice:

```python
def resolve_overtake(attacker, defender, context, skill_mgr):
    # Get skill bonuses
    attacker_bonus = skill_mgr.get_overtake_bonus(attacker, context)
    defender_bonus = skill_mgr.get_defense_bonus(defender, context)
    
    # Apply to dice rolls
    attacker_total = attacker_roll + attacker_bonus
    defender_total = defender_roll + defender_bonus
```

### Race Start

Start skills modify launch performance:

```python
def simulate_start(grid_positions, drivers, skill_mgr):
    for driver, grid_pos in grid_positions.items():
        context = SkillContext(session_type=SessionType.RACE, lap_number=0)
        start_modifier = skill_mgr.get_start_modifier(driver, context)
        
        # Apply to reaction time
        reaction_time += start_modifier
```

## Data Source

Skills are loaded from `data/driver_ratings.csv`:

```csv
Driver,R_Value,DR_Value,Team,稳定性,技能1,技能2
Verstappen,100.5,92,Red Bull Racing,96.0,老潘课堂,
Perez,99.8,88,Red Bull Racing,96.0,,保胎大师
Leclerc,100.4,90,Ferrari,95.0,勒一圈,极限哥
```

## Testing

Run skill tests:

```bash
uv run python -m src.skills.tests.test_skills
```

## Configuration

Skill behavior can be configured in `src/skills/skill_effects.py`:

- `BASE_MODIFIER`: Base skill modifier
- `WEATHER_BOOST`: Rain skill multiplier
- `DEFENSE_BONUS`: Defense skill bonus
- `ATTACK_BONUS`: Attack skill bonus

## Related Documentation

- [STRATEGIST_DICE_RULES.md](STRATEGIST_DICE_RULES.md) - Dice mechanics
- [DRS_SYSTEM.md](DRS_SYSTEM.md) - DRS and overtake system
- [F1_SIMULATION_MODEL.md](F1_SIMULATION_MODEL.md) - Race simulation
