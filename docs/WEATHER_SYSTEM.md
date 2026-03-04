# F1 Weather System Documentation

## Overview

The Weather System provides realistic weather simulation for F1 races, including dynamic weather changes, track conditions, tyre selection impacts, and race control responses. The system is designed to create dramatic and unpredictable race scenarios based on real-world F1 weather patterns.

---

## System Architecture

```
src/weather/
├── __init__.py                      # Package exports
├── weather_generator.py             # WeatherGenerator class - main weather generation logic
├── weather_types.py                 # Weather enums and data classes
└── integrators/
    ├── __init__.py
    └── enhanced_sim_weather.py      # Integration with simulation
```

---

## Core Components

### 1. Weather Types ([`weather_types.py:14-25`](src/weather/weather_types.py:14))

The `WeatherType` enum defines all possible weather conditions:

| Type | Description |
|------|-------------|
| `CLEAR` | No precipitation, optimal racing conditions |
| `PARTLY_CLOUDY` | Partial cloud cover |
| `CLOUDY` | Overcast without precipitation |
| `OVERCAST` | Complete cloud cover |
| `LIGHT_RAIN` | Light drizzle |
| `MODERATE_RAIN` | Steady moderate rainfall |
| `HEAVY_RAIN` | Heavy continuous rain |
| `TORRENTIAL_RAIN` | Extreme rainfall, dangerous conditions |
| `THUNDERSTORM` | Lightning risk, extreme danger |

### 2. Rain Intensity ([`weather_types.py:49-56`](src/weather/weather_types.py:49))

| Level | Value | Impact |
|-------|-------|--------|
| `NONE` | 0 | No rain |
| `LIGHT` | 1 | Light drizzle, minimal track impact |
| `MODERATE` | 2 | Steady rain, noticeable grip reduction |
| `HEAVY` | 3 | Heavy rain, significant grip loss |
| `TORRENTIAL` | 4 | Extreme rain, standing water, potential red flag |

### 3. Track Conditions ([`weather_types.py:28-34`](src/weather/weather_types.py:28))

| Condition | Description | Tyre Requirement |
|-----------|-------------|------------------|
| `DRY` | Full dry line, no standing water | Slick tyres (Soft/Medium/Hard) |
| `DAMP` | Damp/misty, no standing water | Intermediate recommended |
| `WET` | Wet but draining, light patches | Intermediate or Wet |
| `FLOODED` | Standing water significant | Wet tyres mandatory |

### 4. Race Control States ([`weather_types.py:37-46`](src/weather/weather_types.py:37))

| State | Description | Speed |
|-------|-------------|-------|
| `GREEN` | All clear, normal racing | 100% |
| `YELLOW` | Caution in affected sector | 80% |
| `DOUBLE_YELLOW` | Caution in multiple sectors | 60% |
| `SAFETY_CAR` | Safety car deployed | ~80% (following pace car) |
| `VSC` | Virtual Safety Car | 60-80% delta |
| `RED_FLAG` | Race suspended | 0% |
| `WET_START` | 2026 wet start regulations | Controlled start |

---

## Weather State Data Class ([`weather_types.py:59-121`](src/weather/weather_types.py:59))

The `WeatherState` dataclass contains all current weather information:

```python
@dataclass
class WeatherState:
    weather_type: WeatherType           # Current weather condition
    track_condition: TrackCondition     # Track surface state
    race_control: RaceControlState      # Race control flags
    temperature: float                 # Air temperature (°C)
    track_temperature: float           # Track surface temperature (°C)
    humidity: float                    # Humidity percentage (0-100)
    wind_speed: float                  # Wind speed (km/h)
    precipitation_probability: float    # Chance of rain (0-100)
    rain_intensity: RainIntensity      # Current rain intensity
    visibility: float                  # Visibility (meters)
    rainfall_accumulation: float       # mm of rain accumulated
    weather_change_probability: float   # Likelihood of change (0-1)
    last_weather_change_time: float    # Minutes since last change
    weather_history: list              # Record of all changes
```

---

## Weather Generator ([`weather_generator.py:221-725`](src/weather/weather_generator.py:221))

The `WeatherGenerator` class is the main component for generating weather patterns.

### Initialization

```python
generator = WeatherGenerator(seed: Optional[int] = None)
```

### Key Methods

#### generate_initial_weather(gp_name: str) -> WeatherState

Generates starting weather conditions for a race:

```python
initial_weather = generator.generate_initial_weather("Monaco")
```

**Factors considered:**
- Track location and climate type
- Race month/season
- Historical weather patterns
- Geographic location (tropical, desert, temperate, etc.)

#### generate_race_weather_events(gp_name: str, race_duration: float = 120.0) -> List[WeatherEvent]

Generates weather events during the race:

```python
events = generator.generate_race_weather_events("Britain", race_duration=120.0)
```

**Event types:**
- `rain_start`: Rain begins
- `rain_intensify`: Rain gets heavier
- `rain_weaken`: Rain decreases
- `rain_stop`: Rain ends
- `dry_line`: Track begins drying

---

## Climate-Based Weather System

### Track Climate Profiles ([`weather_types.py:147-405`](src/weather/weather_types.py:147))

The system includes climate data for all 2022 F1 circuits:

| Climate Type | Examples | Rain Chance Modifier |
|--------------|----------|---------------------|
| `desert` | Bahrain, Saudi Arabia, Abu Dhabi | 0.2x (very low) |
| `tropical` | Singapore, Miami, Brazil | 1.5x (high) |
| `temperate` | Britain, Belgium, Netherlands | 1.3x (moderate-high) |
| `continental` | Hungary, Austria, Canada | 1.0x (baseline) |
| `mediterranean` | Spain, Monaco, Italy | 0.7x (low) |

### Track Rain Probabilities

Selected circuits and their baseline rain probabilities:

| Circuit | Climate | Rain Chance | Weather Change Prob |
|---------|---------|-------------|---------------------|
| Bahrain | desert | 5% | 5% |
| Monaco | mediterranean | 20% | 15% |
| Singapore | tropical | 50% | 20% |
| Britain | temperate | 18% | 45% |
| Belgium | temperate | 45% | 40% |
| Spa-Francorchamps | temperate | 45% | 40% |
| Suzuka | temperate | 35% | 20% |
| Interlagos | tropical | 45% | 25% |

---

## Dynamic Weather Patterns

### DynamicWeatherPattern Class ([`weather_generator.py:105-218`](src/weather/weather_generator.py:105))

Models the "British summer" effect where weather can change multiple times during a race:

```python
pattern = DynamicWeatherPattern(
    track_name="Britain",
    weather_change_probability=0.45,
    current_weather_state="CLEAR",
    min_time_between_changes=10.0,
    max_time_between_changes=45.0
)
```

**Key behaviors:**

- **Minimum time between changes**: Prevents unrealistic rapid switching (default 10-45 minutes)
- **Time-based probability**: Rain becomes more likely as race progresses (afternoon showers)
- **Toggle mechanism**: CLEAR ↔ RAIN state changes

### Weather Change Triggers

```python
if pattern.should_change_weather(race_time_minutes):
    new_weather, description = pattern.trigger_weather_change(
        race_time_minutes, current_weather
    )
```

---

## Tyre Selection Impact

### Crossover Points

| Transition | Trigger Point |
|------------|----------------|
| Slick → Intermediate | 110-112% of dry lap time |
| Intermediate → Wet | 115-120% of dry lap time |
| Wet → Intermediate | 105-108% of dry lap time |
| Intermediate → Slick | 102-105% of dry lap time (drying) |

### Speed Penalties by Condition

| Condition | Speed Multiplier | Additional Penalty |
|-----------|------------------|-------------------|
| Light rain on slicks | 1.08-1.12 | +0-5s per lap |
| Moderate rain on slicks | 1.12-1.18 | +10-20s per lap |
| Heavy rain on slicks | 1.18-1.25 | +20-30s per lap |
| Wrong tyre (wet on dry) | - | +15-25s per lap |
| Correct Intermediate | 1.00 | Baseline |
| Correct Wet | 1.00 | Baseline |

---

## Integration

### With Race Simulation

The weather system integrates with the race simulation through [`weather/integrators/enhanced_sim_weather.py`](src/weather/integrators/enhanced_sim_weather.py):

```python
# Initialize weather for race
weather_gen = WeatherGenerator(seed=42)
initial_weather = weather_gen.generate_initial_weather(track_name)

# During race
for lap in range(1, total_laps + 1):
    # Check for weather changes
    if weather_pattern.should_change_weather(race_time):
        new_weather, desc = weather_pattern.trigger_weather_change(
            race_time, current_weather
        )
        # Apply to race state
```

### With Strategist System

The weather system provides critical information for strategic decisions:

```python
# In strategist decisions
if weather_state.track_condition == TrackCondition.WET:
    # Consider pit for wet tyres
    decision = strategist.decide_weather_response(
        weather_forecast=weather_forecast
    )
```

---

## Usage Examples

### Basic Weather Generation

```python
from weather import WeatherGenerator
from weather.weather_types import WeatherType, TrackCondition

# Create generator with seed for reproducibility
gen = WeatherGenerator(seed=2024)

# Generate initial weather for Monaco
initial = gen.generate_initial_weather("Monaco")
print(f"Weather: {initial.weather_type}")
print(f"Track: {initial.track_condition}")
print(f"Temperature: {initial.temperature}°C")
print(f"Rain probability: {initial.precipitation_probability}%")

# Generate weather events during race
events = gen.generate_race_weather_events("Monaco", race_duration=120)
for event in events:
    print(f"Lap {event.timestamp}: {event.description}")
```

### Monte Carlo Weather Simulation

```python
# Run multiple simulations to understand weather probability distribution
from weather.tests.test_monte_carlo import run_weather_monte_carlo

results = run_weather_monte_carlo(
    track="Britain",
    num_simulations=1000,
    race_duration=120
)

# Analyze results
print(f"Rain occurred: {results['rain_frequency']}%")
print(f"Average rain start: {results['avg_rain_start']} minutes")
print(f"Rain intensity distribution: {results['intensity_distribution']}")
```

---

## Configuration

### Climate Modifiers ([`weather_generator.py:30-62`](src/weather/weather_generator.py:30))

Customize weather behavior per climate type:

```python
CLIMATE_RAIN_MODIFIERS = {
    "desert": {
        "rain_chance_multiplier": 0.2,
        "rain_intensity_bias": 0.1,      # Light rain more likely
        "thunderstorm_chance": 0.01,
        "typical_rain_duration": (10, 20),
    },
    "tropical": {
        "rain_chance_multiplier": 1.5,
        "rain_intensity_bias": 0.6,      # Heavy rain more likely
        "thunderstorm_chance": 0.15,
        "typical_rain_duration": (20, 45),
    },
    # ... etc
}
```

### Seasonal Modifiers ([`weather_generator.py:64-78`](src/weather/weather_generator.py:64))

Monthly rain probability adjustments:

```python
SEASONAL_RAIN_MODIFIERS = {
    1: {"modifier": 1.2, "description": "Winter - higher rain in temperate"},
    6: {"modifier": 0.9, "description": "Early summer"},
    7: {"modifier": 0.8, "description": "Summer - lowest rain chance"},
    # ... etc
}
```

---

## Testing

### Test Files

- [`weather/tests/test_monte_carlo.py`](src/weather/tests/test_monte_carlo.py) - Monte Carlo weather simulation tests
- [`weather/tests/test_weather_integration.py`](src/weather/tests/test_weather_integration.py) - Integration tests

### Key Test Scenarios

1. **Rain probability calibration**: Verify tracks match historical data
2. **Dynamic weather timing**: Test minimum/maximum time between changes
3. **Intensity distribution**: Ensure climate bias is reflected
4. **Race control triggers**: Safety car/red flag activation
5. **Tyre crossover detection**: Correct tyre selection timing

---

## Related Documentation

- [STRATEGIST_DICE_RULES.md](docs/STRATEGIST_DICE_RULES.md) - Strategist decision dice mechanics
- [WEATHER_SYSTEM_PLAN.md](docs/WEATHER_SYSTEM_PLAN.md) - Original implementation plan
- [MONTE_CARLO_WEATHER_RESULTS.md](docs/MONTE_CARLO_WEATHER_RESULTS.md) - Weather probability analysis
