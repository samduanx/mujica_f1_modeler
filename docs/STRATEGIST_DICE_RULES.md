# Strategist System Dice Rolling Rules

## Overview

This document defines all dice rolling mechanics for the Strategist System. The system uses primarily **1d20 + modifiers** against target numbers, with additional dice types for specific situations.

## Base Dice Mechanics

### The d20 System

All strategic decisions use a 1d20 roll with the following outcome chart:

| Roll | Outcome | Description |
|------|---------|-------------|
| Natural 1 | **Critical Failure** | Disastrous outcome, worst possible result |
| 2-5 | **Failure** | Decision backfires, negative consequences |
| 6-10 | **Partial Success** | Works but with complications or reduced effectiveness |
| 11-15 | **Success** | Decision works as intended |
| 16-19 | **Great Success** | Better than expected outcome |
| Natural 20 | **Critical Success** | Exceptional result, maximum benefit |

### Modifier Calculation

```
Total Modifier = Experience + Attribute + Track Bonus + Special - Difficulty

Maximum typical modifier range: -5 to +8
```

#### Experience Modifier

| Years Experience | Modifier |
|------------------|----------|
| 0-2 (Rookie) | +0 |
| 3-5 (Junior) | +1 |
| 6-9 (Experienced) | +2 |
| 10-14 (Senior) | +3 |
| 15+ (Veteran) | +4 |

#### Attribute Modifier

Attributes are rated 0.0-1.0 and convert to modifiers:

| Attribute Value | Modifier |
|-----------------|----------|
| 0.0-0.25 | -2 |
| 0.26-0.40 | -1 |
| 0.41-0.60 | 0 |
| 0.61-0.75 | +1 |
| 0.76-0.90 | +2 |
| 0.91-1.00 | +3 |

#### Track Familiarity Bonus

| Familiarity | Bonus |
|-------------|-------|
| Never raced | 0 |
| 1-2 races | +1 |
| 3-5 races | +2 |
| 6+ races | +3 |

#### Special Modifiers

| Condition | Modifier |
|-----------|----------|
| Previous success this race | +1 (cumulative to +3) |
| Previous failure this race | -1 (cumulative to -3) |
| Driver highly trusts strategist | +1 |
| Driver distrusts strategist | -1 |
| Home race (strategist nationality) | +1 |
| Pressure situation (championship deciding) | -1 or -2 |

#### Difficulty Penalties

| Situation | Penalty |
|-----------|---------|
| Standard decision | 0 |
| Complex situation | -1 |
| High pressure | -2 |
| Extreme circumstances | -3 |
| Monaco-style tight racing | -2 |
| Wet weather uncertainty | -2 |
| Unknown tire behavior | -1 |

## Decision Type Specifics

### 1. Pit Stop Timing Decision

**Base Target Number:** 12

**Key Attributes:** pit_timing, tire_management, aggression

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier
3. Add pit_timing attribute modifier
4. Add tire_management attribute modifier (if considering tire life)
5. Add track familiarity bonus
6. Subtract situation difficulty

**Outcome Table:**

| Final Result | Timing Quality | Time Impact vs Optimal |
|--------------|----------------|----------------------|
| 20+ (Crit) | Perfect undercut/overcut | -3.0s |
| 16-19 | Optimal window | -1.5s |
| 11-15 | Good timing | 0s |
| 6-10 | Slightly off | +1.0s |
| 2-5 | Poor timing | +3.0s |
| 1 (Crit Fail) | Disastrous timing | +6.0s or position lost |

**Special Rules:**
- **Undercut attempt:** Base TN increases to 15
- **Stacked pit stops (Monaco):** Additional -2 penalty
- **Weather uncertainty:** Additional -1 to -3 penalty

### 2. Tyre Compound Selection

**Base Target Number:** 12

**Key Attributes:** tire_management, analytical, intuition

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier (capped at +2 for this decision)
3. Add tire_management attribute modifier
4. Add analytical attribute modifier
5. Add intuition modifier (for "gut feeling" calls)
6. Subtract difficulty based on weather certainty

**Weather Uncertainty Penalty:**

| Rain Probability | Penalty |
|------------------|---------|
| 0-20% | 0 |
| 21-40% | -1 |
| 41-60% | -2 |
| 61-80% | -3 |
| 81-100% | -1 (certainty returns) |

**Compound Selection Results:**

| Final Result | Selection Quality | Effect |
|--------------|-------------------|--------|
| 20+ (Crit) | Perfect choice | Optimal compound + extra life |
| 16-19 | Excellent | Optimal compound |
| 11-15 | Good | Very good compound |
| 6-10 | Acceptable | Suboptimal but workable |
| 2-5 | Poor | Wrong compound type |
| 1 (Crit Fail) | Disastrous | Completely wrong compound |

**Tire Performance Modifiers:**

| Quality | Speed Modifier | Degradation Modifier |
|---------|---------------|---------------------|
| Perfect | +0.5% | -10% |
| Excellent | 0% | 0% |
| Good | -0.3% | +5% |
| Acceptable | -0.8% | +15% |
| Poor | -2.0% | +30% |
| Disastrous | -4.0% | +50% |

### 3. Racing Pace Decision

**Base Target Number:** 10

**Key Attributes:** aggression, conservatism, analytical

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier
3. Add relevant attribute based on mode:
   - Push mode: aggression modifier
   - Manage/Save mode: conservatism modifier
   - Analyze: analytical modifier

**Pace Mode Effectiveness:**

| Final Result | Effectiveness | Lap Time Impact |
|--------------|---------------|-----------------|
| 20+ (Crit) | 130% | Mode benefits amplified |
| 16-19 | 115% | Better than expected |
| 11-15 | 100% | As designed |
| 6-10 | 85% | Reduced effectiveness |
| 2-5 | 65% | Poor execution |
| 1 (Crit Fail) | 40% | Backfires completely |

**Pace Modes Reference:**

| Mode | Speed | Tire Wear | Fuel Use | Risk |
|------|-------|-----------|----------|------|
| Push | 100% | 150% | 120% | High |
| Race | 95% | 100% | 100% | Normal |
| Manage | 90% | 70% | 85% | Low |
| Save | 85% | 50% | 70% | Very Low |
| Lift & Coast | 80% | 40% | 50% | Minimal |

### 4. Weather Response Decision

**Base Target Number:** 14 (higher due to uncertainty)

**Key Attributes:** wet_weather_skill, intuition, adaptability

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier
3. Add wet_weather_skill modifier (x1.5, rounded)
4. Add intuition modifier
5. Add adaptability modifier
6. Subtract forecast uncertainty penalty

**Forecast Uncertainty:**

| Rain ETA Certainty | Penalty |
|-------------------|---------|
| Certain (< 10% variance) | 0 |
| Likely (10-25% variance) | -1 |
| Uncertain (25-50% variance) | -2 |
| Very Uncertain (> 50% variance) | -3 |

**Timing Quality Results:**

| Final Result | Timing | Laps vs Optimal | Positions Impact |
|--------------|--------|-----------------|------------------|
| 20+ (Crit) | Anticipatory | -2 laps | +2 to +4 positions |
| 16-19 | Early | -1 lap | +1 to +2 positions |
| 11-15 | Optimal | 0 | Maintain position |
| 6-10 | Reactive | +1 lap | -1 position |
| 2-5 | Late | +3 laps | -2 to -3 positions |
| 1 (Crit Fail) | Disastrous | +5 laps | -4+ positions |

**Special - Rain Intensity Roll:**

When switching to wet tyres, roll 1d10 for rain intensity prediction accuracy:

| d10 | Prediction Accuracy |
|-----|---------------------|
| 1-2 | Underestimated (need full wets, got inters) |
| 3-4 | Slightly underestimated |
| 5-6 | Accurate |
| 7-8 | Slightly overestimated |
| 9-10 | Overestimated (got wets, only needed inters) |

### 5. Safety Car / VSC Response

**Base Target Number:** 13

**Key Attributes:** analytical, adaptability, aggression

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier
3. Add analytical modifier
4. Add adaptability modifier (for quick decisions)
5. Aggression modifier (affects preference):
   - Aggressive (> 0.6): -1 (prefer stay out)
   - Conservative (> 0.6): +1 (prefer pit)
6. Subtract decision complexity

**Decision Complexity Penalty:**

| Situation | Penalty |
|-----------|---------|
| Clear SC, obvious pit window | 0 |
| VSC (shorter window) | -1 |
| End of race (unknown duration) | -2 |
| Multiple cars pitting | -1 |
| Championship implications | -1 |

**SC/VSC Decision Results:**

| Final Result | Decision Quality | Outcome |
|--------------|------------------|---------|
| 20+ (Crit) | Perfect | Optimal call with bonus track position |
| 16-19 | Excellent | Correct decision executed perfectly |
| 11-15 | Good | Correct decision |
| 6-10 | Questionable | 50% chance of wrong call |
| 2-5 | Poor | Wrong decision |
| 1 (Crit Fail) | Disastrous | Completely wrong call, major loss |

**Time Lost Under Caution:**

| Caution Type | Normal Pit Loss | SC Pit Loss | VSC Pit Loss |
|--------------|-----------------|-------------|--------------|
| Full SC | 22s | 12s | - |
| VSC | 22s | - | 8s |
| Double Yellow | 22s | 15s | - |

### 6. Driver Compliance Check

**Base Target Number:** 12

**Roll:** 1d20

**Modifiers:**
- Relationship trust: -2 to +2
- Driver professionalism: -2 to +1
- Driver aggression: -2 to 0 (higher aggression = less compliant)
- Driver stubbornness: -3 to 0
- Decision importance: +0 to +4
- Recent strategist success: -1 to +2

**Compliance Levels:**

| Final Result | Compliance Level | Driver Action |
|--------------|------------------|---------------|
| 20+ (Crit) | Perfect | Executes flawlessly with enthusiasm |
| 16-19 | Full | Follows instructions exactly |
| 11-15 | Partial | Follows with minor adaptation |
| 6-10 | Suggestion | Takes as advice, may modify |
| 2-5 | Resistance | Reluctant compliance |
| 1 (Crit Fail) | Override | Completely disregards advice |

**Compliance Effectiveness:**

| Level | Strategy Effectiveness |
|-------|----------------------|
| Perfect | 120% |
| Full | 100% |
| Partial | 85% |
| Suggestion | 70% |
| Resistance | 50% |
| Override | 0% (may be negative) |

### 7. Undercut/Overcut Timing

**Base Target Number:** 15 (difficult decision)

**Key Attributes:** undercut_skill, pit_timing, aggression

**Roll Procedure:**
1. Roll 1d20
2. Add experience modifier (capped at +2)
3. Add undercut_skill modifier (x1.5)
4. Add pit_timing modifier
5. Add aggression modifier (for attempt willingness)
6. Subtract track-specific difficulty

**Track Difficulty for Undercuts:**

| Track Type | Penalty |
|------------|---------|
| High overtaking (Monza, Spa) | 0 |
| Medium overtaking | -1 |
| Low overtaking (Monaco, Hungary) | -2 |
| Very difficult (Singapore street) | -3 |

**Undercut Results:**

| Final Result | Outcome | Position Change |
|--------------|---------|-----------------|
| 20+ (Crit) | Perfect undercut | +2 positions |
| 16-19 | Successful undercut | +1 position |
| 11-15 | Net neutral | 0 positions |
| 6-10 | Failed undercut | -1 position |
| 2-5 | Backfires | -2 positions |
| 1 (Crit Fail) | Disaster | -3+ positions |

## Special Dice Rolls

### Pressure Check (High Stakes Decisions)

When championship or race win is on the line:

1. Roll 2d10 instead of 1d20
2. Take the lower result (representing pressure affecting performance)
3. Apply normal modifiers

### Momentum Check (Consecutive Decisions)

If strategist has made 3+ successful decisions:

- Roll 1d20 with advantage (roll twice, take higher)

If strategist has made 3+ failed decisions:

- Roll 1d20 with disadvantage (roll twice, take lower)

### Team Order Check

When deciding whether to issue team orders:

1. Roll 1d20 + communication modifier
2. TN 15 to convince team principal
3. TN 12 to convince driver

### Gamble Check

For high-risk strategic gambles:

1. Roll 1d100 for outcome probability
2. Roll 1d20 for execution quality
3. Combined result determines success

| d100 | Gamble Risk Level |
|------|-------------------|
| 1-20 | Very High (25% base success) |
| 21-40 | High (40% base success) |
| 41-60 | Moderate (55% base success) |
| 61-80 | Low (70% base success) |
| 81-100 | Very Low (85% base success) |

## Critical Success/Failure Tables

### Critical Success (Natural 20) Bonuses

Roll 1d6 for additional benefit:

| d6 | Bonus Effect |
|----|--------------|
| 1 | Driver gains +5% pace for next 5 laps |
| 2 | Tire life extended by 20% |
| 3 | Perfect pit stop execution (-1.0s) |
| 4 | Rival makes mistake due to pressure |
| 5 | Weather prediction perfect |
| 6 | Double benefit (roll twice, take both) |

### Critical Failure (Natural 1) Penalties

Roll 1d6 for additional penalty:

| d6 | Penalty Effect |
|----|----------------|
| 1 | Driver loses confidence (-5% pace for 5 laps) |
| 2 | Tire degradation accelerated (+30%) |
| 3 | Slow pit stop (+3.0s) |
| 4 | Driver makes error due to confusion |
| 5 | Misread weather completely |
| 6 | Double penalty (roll twice, take both) |

## Example Dice Roll Scenarios

### Scenario 1: Monaco Pit Stop Timing

**Situation:** Lap 28 of 78, strategist planning pit stop

**Strategist:**
- Experience: 8 years (+2)
- Pit Timing: 0.75 (+1)
- Track Familiarity: Monaco 0.8 (+2)

**Modifiers:**
- Experience: +2
- Pit Timing: +1
- Track: +2
- Monaco Difficulty: -2
- **Total: +3**

**Roll:** 1d20 = 14
**Final:** 14 + 3 = 17 (Great Success!)

**Outcome:** Optimal pit timing, driver exits in clean air.

### Scenario 2: Wet Weather Gamble

**Situation:** 60% rain predicted in 3 laps, considering early switch

**Strategist:**
- Experience: 5 years (+1)
- Wet Weather: 0.8 (+2)
- Intuition: 0.7 (+1)

**Modifiers:**
- Experience: +1
- Wet Weather: +2
- Intuition: +1
- Forecast Uncertainty: -2
- **Total: +2**

**Roll:** 1d20 = 16
**Final:** 16 + 2 = 18 (Great Success!)

**Outcome:** Early switch pays off perfectly. Rain arrives 2 laps early, others scramble to pit while protagonist gains positions.

### Scenario 3: Driver Compliance Check

**Situation:** Aggressive driver asked to manage tires

**Relationship:**
- Trust: 0.4 (-1)
- Recent failures: 2 (-2)

**Driver:**
- Aggression: 0.9 (-2)
- Stubbornness: 0.7 (-1)
- Professionalism: 0.6 (+0)

**Modifiers:**
- Trust: -1
- Recent failures: -2
- Aggression: -2
- Stubbornness: -1
- Importance: +2
- **Total: -4**

**Roll:** 1d20 = 11
**Final:** 11 - 4 = 7 (Resistance)

**Outcome:** Driver acknowledges the call but continues pushing. Tires degrade faster than planned.

## Quick Reference Card

| Decision Type | Base TN | Key Dice | Critical Modifiers |
|--------------|---------|----------|-------------------|
| Pit Timing | 12 | 1d20 | pit_timing, experience |
| Tyre Compound | 12 | 1d20 | tire_management, weather |
| Racing Pace | 10 | 1d20 | aggression/conservatism |
| Weather Response | 14 | 1d20 | wet_weather_skill |
| SC/VSC Response | 13 | 1d20 | analytical, adaptability |
| Driver Compliance | 12 | 1d20 | trust, personality |
| Undercut | 15 | 1d20 | undercut_skill |
| Pressure Check | 15 | 2d10 (low) | experience, composure |

## Narrative Dice Integration

For storytelling purposes, dice rolls can be described narratively:

- **1-5:** "The call seemed right, but circumstances conspired against it..."
- **6-10:** "It was a marginal call, and it showed in the execution..."
- **11-15:** "The decision played out exactly as planned."
- **16-19:** "An inspired call! Everything fell into place perfectly."
- **20:** "A stroke of genius! This is the kind of call that wins championships!"
- **1 (Critical):** "A catastrophic miscalculation..."

## Balance Notes

- Typical success rate should be 55-60% for experienced strategists
- Critical successes/failures should be rare (5% each)
- Driver compliance should vary by relationship (40-70% typical)
- Weather decisions should be high variance due to uncertainty
- Pit timing should be most controllable (experience matters most)
