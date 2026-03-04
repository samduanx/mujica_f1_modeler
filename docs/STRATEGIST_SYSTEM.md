# F1 Strategist System Documentation

## Overview

The Strategist System enables dice-based strategic decision-making during F1 race simulations. Each team has a strategist with unique attributes who makes critical race decisions including pit stop timing, tyre compound selection, racing pace, and weather responses. The system is designed for a doujin anchor novel series where the protagonist is a strategist.

---

## System Architecture

```
src/strategist/
├── __init__.py                         # Package exports
├── strategist_types.py                  # Core data types and enums
├── strategist_manager.py               # Strategist profile management
├── dice_mechanics.py                   # Dice rolling system
├── driver_interaction.py                # Driver-strategist interaction
├── decisions/
│   ├── __init__.py
│   ├── pit_strategy.py                  # Pit stop decisions
│   ├── pace_strategy.py                 # Racing pace decisions
│   ├── weather_strategy.py              # Weather response decisions
│   └── sc_strategy.py                   # Safety Car/VSC decisions
├── integrators/
│   ├── __init__.py
│   └── race_sim_integration.py          # Race simulation integration
└── tests/
    ├── __init__.py
    └── test_strategist_system.py         # Unit tests

data/strategists/
└── strategists.json                     # Strategist profile data
```

---

## Core Data Types

### 1. StrategistProfile ([`strategist_types.py`](src/strategist/strategist_types.py))

Represents a strategist's attributes and capabilities:

```python
@dataclass
class StrategistProfile:
    name: str                           # Strategist name
    team: str                           # Team name
    experience: int                     # Years of experience
    
    # Core Attributes (0.0-1.0 scale)
    aggression: float = 0.5           # Higher = more aggressive strategies
    conservatism: float = 0.5         # Higher = safer choices
    adaptability: float = 0.5        # Response to race developments
    intuition: float = 0.5            # "Gut feeling" dice bonuses
    analytical: float = 0.5           # Data-driven decision quality
    communication: float = 0.5        # Driver compliance impact
    
    # Specializations
    wet_weather_skill: float = 0.5    # Rain strategy expertise
    tire_management: float = 0.5      # Tyre compound decisions
    pit_timing: float = 0.5           # When to pit
    undercut_skill: float = 0.5       # Undercut timing
    
    # Track-specific knowledge
    track_familiarity: Dict[str, float] = field(default_factory=dict)
```

### 2. StrategyDecision ([`strategist_types.py`](src/strategist/strategist_types.py))

Records a strategic decision and its outcome:

```python
@dataclass
class StrategyDecision:
    decision_id: str                    # Unique identifier
    lap: int                           # Lap number
    decision_type: DecisionType        # Type of decision
    strategist: str                    # Who made the decision
    driver: str                        # Affected driver
    
    race_context: RaceContext          # Race situation
    decision: str                      # The decision made
    
    dice_rolls: List[DiceRoll]         # Dice roll results
    total_modifier: int                # Total modifier applied
    final_result: int                  # Final roll + modifier
    success: bool                      # Whether goal achieved
    
    driver_compliance: DriverComplianceLevel
    driver_override: Optional[str]     # If driver modified decision
    
    predicted_outcome: str             # Expected result
    actual_outcome: str                # Actual result
    time_impact: float                 # Seconds gained/lost
    position_impact: int               # Positions gained/lost
    narrative: str = ""                # Story text
```

### 3. RaceContext ([`strategist_types.py`](src/strategist/strategist_types.py))

Current race situation for decision-making:

```python
@dataclass
class RaceContext:
    lap: int                           # Current lap
    total_laps: int                    # Total race laps
    race_time: float                   # Seconds elapsed
    
    current_position: int             # Driver position
    positions_gained_lost: int         # Position change since start
    gap_to_leader: float               # Seconds behind leader
    gap_to_next: float                 # Gap to car ahead
    gap_to_behind: float               # Gap to car behind
    
    track_condition: TrackCondition   # Track state
    weather_state: WeatherState         # Current weather
    track_temperature: float           # Track temp
    
    current_tyre: str                  # Current tyre compound
    tyre_age: int                      # Laps on current tyre
    tyre_degradation: float            # 0.0-1.0 scale
    tyre_performance_remaining: float  # Estimated laps before cliff
    
    fuel_remaining: float              # Percentage
    fuel_save_needed: bool
    
    safety_car_deployed: bool          # SC status
    vsc_active: bool                   # VSC status
    drs_enabled: bool                  # DRS available
    
    rival_positions: Dict[str, int]   # Competitor positions
    teammate_position: Optional[int]   # Teammate position
    cars_pitted_last_3_laps: List[str] # Undercut detection
    
    pit_history: List[PitStopEvent]    # Past pit stops
    previous_decisions: List[StrategyDecision]  # Previous decisions
```

### 4. Decision Types ([`strategist_types.py`](src/strategist/strategist_types.py))

| Type | Description |
|------|-------------|
| `PIT_STOP_TIMING` | When to make pit stop |
| `TIRE_COMPOUND` | Which tyre to use |
| `RACING_PACE` | Push/manage speed |
| `WEATHER_TYRE_CHANGE` | Rain tyre decisions |
| `UNDERCUT_ATTEMPT` | Pit before rival to gain track position |
| `DEFEND_POSITION` | Defensive driving |
| `FUEL_MANAGEMENT` | Fuel conservation |
| `SAFETY_CAR_RESPONSE` | SC/VSC pit strategy |
| `VSC_RESPONSE` | Virtual Safety Car response |
| `DRS_TIMING` | DRS usage strategy |

### 5. Driver Compliance Levels ([`strategist_types.py`](src/strategist/strategist_types.py))

| Level | Description |
|-------|-------------|
| `FULL_COMPLIANCE` | Driver follows exactly |
| `PARTIAL_COMPLIANCE` | Modified execution |
| `SUGGESTION` | Driver adapts the suggestion |
| `REJECTION` | Driver ignores advice |
| `OVERRIDE` | Driver does opposite |

---

## Dice Rolling Mechanics

### Base System ([`dice_mechanics.py`](src/strategist/dice_mechanics.py))

All strategic decisions use **1d20 + modifiers** against a target number (TN):

| Roll | Outcome | Description |
|------|---------|-------------|
| Natural 1 | **Critical Failure** | Disastrous outcome |
| 2-5 | **Failure** | Decision backfires |
| 6-10 | **Partial Success** | Works with complications |
| 11-15 | **Success** | Works as intended |
| 16-19 | **Great Success** | Better than expected |
| Natural 20 | **Critical Success** | Exceptional result |

### Modifier Calculation

```
Total Modifier = Experience + Attribute + Track Bonus + Special - Difficulty
```

**Typical modifier range: -5 to +8**

#### Experience Modifier

| Years | Rank | Modifier |
|-------|------|----------|
| 0-2 | Rookie | +0 |
| 3-5 | Junior | +1 |
| 6-9 | Experienced | +2 |
| 10-14 | Senior | +3 |
| 15+ | Veteran | +4 |

#### Attribute Modifier (0.0-1.0 scale)

| Value | Modifier |
|-------|----------|
| 0.0-0.25 | -2 |
| 0.26-0.40 | -1 |
| 0.41-0.60 | 0 |
| 0.61-0.75 | +1 |
| 0.76-0.90 | +2 |
| 0.91-1.00 | +3 |

#### Track Familiarity Bonus

| Races at Track | Bonus |
|----------------|-------|
| Never raced | 0 |
| 1-2 races | +1 |
| 3-5 races | +2 |
| 6+ races | +3 |

### Decision Difficulty

| Situation | Base TN | Difficulty |
|-----------|---------|------------|
| Normal pit timing | 12 | 0 |
| Undercut attempt | 15 | -1 |
| Rain timing (first to switch) | 16 | -2 |
| Safety car gamble | 18 | -3 |
| Emergency response | 14 | -1 |
| Monaco overtaking | 17 | -2 |

---

## Decision Systems

### 1. Pit Stop Strategy ([`decisions/pit_strategy.py`](src/strategist/decisions/pit_strategy.py))

**Decisions:**
- Pre-race: Number of stops, initial tyre compound
- During race: Timing of each pit stop
- Adaptation: Strategy changes based on race development

**Key Attributes:** `pit_timing`, `tire_management`, `aggression`

**Outcomes:**

| Outcome | Timing Adjustment | Time Impact |
|---------|------------------|-------------|
| Critical Success | Perfect undercut/overcut | -3.0s |
| Great Success | Optimal window | -1.5s |
| Success | As planned | 0s |
| Partial Success | Slightly off | +1.0s |
| Failure | Poor timing | +3.0s or position loss |
| Critical Failure | Disastrous | +6.0s or major position loss |

### 2. Tyre Compound Selection ([`decisions/pit_strategy.py`](src/strategist/decisions/pit_strategy.py))

**Available Compounds:**
- Soft (Red): Fastest but least durable
- Medium (Yellow): Balanced performance
- Hard (White): Most durable, slower
- Intermediate (Green): Wet/damp conditions
- Wet (Blue): Heavy rain

**Selection Factors:**
- Track characteristics
- Race position
- Tyre degradation state
- Weather conditions
- Competitor strategy

### 3. Racing Pace Strategy ([`decisions/pace_strategy.py`](src/strategist/decisions/pace_strategy.py))

**Pace Modes:**

| Mode | Speed | Tyre Wear | Fuel Use | Use Case |
|------|-------|-----------|----------|----------|
| `PUSH` | 100% | High | High | Attack/overtake |
| `RACE` | 95% | Medium | Medium | Normal racing |
| `MANAGE` | 90% | Low | Low | Extend stint |
| `SAVE` | 85% | Very Low | Very Low | Conservation |
| `LIFT_AND_COAST` | 80% | Minimal | Minimal | Fuel critical |

**Key Attributes:** `aggression`, `analytical`, `tire_management`

### 4. Weather Response ([`decisions/weather_strategy.py`](src/strategist/decisions/weather_strategy.py))

**Decision Tree:**

```
Rain Incoming? (probability > 70%)
├── Yes
│   ├── Roll for timing
│   │   ├── Success → Early switch (gain positions)
│   │   ├── Partial → Correct timing
│   │   └── Failure → Late switch (lose positions)
│   └── Select tyre (INTER or WET)
├── Maybe (30-70%)
│   └── Risk assessment roll
│       ├── Aggressive → Gamble on early switch
│       └── Conservative → Wait for certainty
└── No → Stay on current tyres
```

**Key Attributes:** `wet_weather_skill`, `intuition`, `adaptability`

### 5. Safety Car/VSC Response ([`decisions/sc_strategy.py`](src/strategist/decisions/sc_strategy.py))

**Decisions:**
- Pit under SC/VSC (free pit stop opportunity)
- Stay out and track position
- Tyre change during stop
- Restart strategy

**Key Factors:**
- Gap to competitors
- Tyre age
- Fuel level
- Race position
- Time remaining

---

## Driver-Strategist Interaction

### Compliance System ([`driver_interaction.py`](src/strategist/driver_interaction.py))

Drivers don't always follow strategist advice. Compliance depends on:

```python
compliance_chance = (
    base_trust +              # Relationship trust level
    driver_personality +      # Driver's personality
    decision_importance +    # How critical the decision is
    recent_success_rate       # Recent outcomes
)
```

### Override Types

| Override | Description |
|----------|-------------|
| `DELAY_PIT` | Driver delays pit by 1 lap |
| `EARLY_PIT` | Driver demands immediate pit |
| `IGNORE_PACE` | Driver pushes harder than advised |
| `ALTERNATE_COMPOUND` | Driver chooses different tyre |
| `EXTEND_STINT` | Driver stays out despite call |
| `PUSH_HARDER` | Driver ignores conservation call |

### Relationship Management

```python
@dataclass
class DriverStrategistRelationship:
    trust: float                    # 0.0-1.0
    communication_quality: float    # Effectiveness of communication
    historical_success_rate: float  # Past decision success
    recent_decisions: List[bool]    # Last 10 decisions (True=success)
    personality_clash: bool         # Conflict potential
    past_conflicts: int             # Previous disagreements
```

---

## Strategist Profiles

### Sample Profiles (from [`data/strategists/strategists.json`](data/strategists/strategists.json))

| Team | Strategist | Key Traits |
|------|------------|------------|
| Red Bull Racing | Hannah Schmidt | Aggressive, wet weather expert |
| Mercedes | James Allison | Analytical, experienced |
| Ferrari | Ravin Jain | Balanced, intuitive |
| McLaren | William Joseph | Aggressive, risk-taker |
| Aston Martin | Bernie Collins | Conservative, methodical |
| Alpine | Ciaron Pilbeam | Balanced |
| Williams | Gaetan Jego | Developing |
| RB | Guillaume Rocquelin | Experienced |
| Sauber | Kyle Wilson-Clarke | Analytical |
| Haas | Mark Slade | Conservative |

---

## Integration

### Race Simulation Integration ([`integrators/race_sim_integration.py`](src/strategist/integrators/race_sim_integration.py))

The strategist system integrates with the race simulation:

```python
# Initialize
integration = StrategistIntegration(race_simulator)
integration.initialize_for_race(strategist_profiles)

# Per-lap decision checking
for lap in range(1, total_laps + 1):
    # Check for strategic decisions
    integration.on_lap_complete(lap, race_state)
    
    # Pre-pit decision
    decision = integration.check_pit_decision(driver, lap)
    if decision:
        compliance = integration.check_compliance(driver, decision)
        if compliance.level == DriverComplianceLevel.OVERRIDE:
            # Handle driver override
```

### With Weather System

```python
# Get weather context
weather_state = race_state.current_weather

# Make weather decision
decision = weather_strategy.decide_weather_response(
    strategist=profile,
    context=race_context,
    weather_forecast=forecast
)
```

### With Tyre System

```python
# Get tyre status
tyres = race_state.get_driver_tyres(driver)

# Make compound decision
decision = pit_strategy.select_tyre_compound(
    strategist=profile,
    context=race_context,
    available_compounds=tyres.available
)
```

---

## Usage Examples

### Loading a Strategist

```python
from src.strategist import StrategistManager

manager = StrategistManager()

# Load by name
schmidt = manager.load_strategist("Hannah Schmidt")

# Load team strategist
mercedes_strat = manager.get_team_strategist("Mercedes")

# Get attribute modifier
pit_timing_mod = schmidt.get_attribute_modifier("pit_timing")
```

### Making a Decision

```python
from src.strategist.decisions import PitStrategyDecision
from src.strategist.dice_mechanics import StrategistDiceRoller

# Create decision
decision_maker = PitStrategyDecision()
dice_roller = StrategistDiceRoller()

# Make pit timing decision
decision = decision_maker.decide_pit_timing(
    strategist=strategist_profile,
    context=race_context,
    planned_pit_lap=25
)

print(f"Decision: {decision.decision}")
print(f"Roll: {decision.dice_rolls[0].result}")
print(f"Success: {decision.success}")
print(f"Narrative: {decision.narrative}")
```

### Running Full Race with Strategists

```python
from src.strategist.integrators import StrategistIntegration
from src.simulation import EnhancedRaceSimulation

# Initialize simulation
sim = EnhancedRaceSimulation(track="Monaco", laps=78)

# Initialize strategist integration
integration = StrategistIntegration(sim)
integration.initialize_for_race(strategist_profiles)

# Run race
results = sim.run_simulation()
```

---

## Configuration

### Creating Custom Strategists

```python
from src.strategist.strategist_types import StrategistProfile

my_strategist = StrategistProfile(
    name="Protagonist",
    team="Ferrari",
    experience=5,
    
    # Core attributes
    aggression=0.75,
    conservatism=0.35,
    adaptability=0.80,
    intuition=0.90,
    analytical=0.70,
    communication=0.65,
    
    # Specializations
    wet_weather_skill=0.85,
    tire_management=0.75,
    pit_timing=0.70,
    undercut_skill=0.60,
    
    # Track familiarity
    track_familiarity={
        "Monaco": 0.8,
        "Silverstone": 0.5,
        "Spa": 0.3
    }
)

# Save to data file
manager.save_strategist(my_strategist)
```

---

## Testing

### Test Files

- [`strategist/tests/test_strategist_system.py`](src/strategist/tests/test_strategist_system.py) - Main test suite

### Test Coverage

- Strategist profile loading and attributes
- Dice rolling mechanics and outcomes
- Pit timing decisions
- Tyre compound selection
- Weather response decisions
- Driver compliance checking
- Full integration tests

---

## Related Documentation

- [STRATEGIST_DICE_RULES.md](docs/STRATEGIST_DICE_RULES.md) - Detailed dice mechanics
- [WEATHER_SYSTEM.md](docs/WEATHER_SYSTEM.md) - Weather system documentation
- [plans/STRATEGIST_SYSTEM_DESIGN.md](plans/STRATEGIST_SYSTEM_DESIGN.md) - Original design document
- [plans/STRATEGIST_SYSTEM_PLAN.md](plans/STRATEGIST_SYSTEM_PLAN.md) - Implementation plan
