# Piastri "抽象怪" (Abstract) Skill - Selection Results v2

## Selection Criteria
- **Race**: Random between Spain and Monaco (Piastri's substitution races)
- **Godfather**: Fast driver at front of grid (high R value)

## Selection Date
2026-03-06 08:52:12

## Race Selection
- **Available**: Spain, Monaco
- **Dice Roll**: d2 = 1
- **Selected Race**: **Spain**

## Godfather Selection
- **Candidates** (7 front grid drivers):
  1. Verstappen (Red Bull, R=100.5)
  2. Leclerc (Ferrari, R=100.4)
  3. Hamilton (Mercedes, R=100.4)
  4. Alonso (Alpine, R=100.5)
  5. Perez (Red Bull, R=99.8)
  6. Sainz (Ferrari, R=99.8)
  7. Russell (Mercedes, R=99.9)

- **Dice Roll**: d7 = 2
- **Selected Godfather**: **Leclerc**
  - Team: Mercedes
  - Nationality: British
  - R Value: 99.9
  - Note: Rising star

## Skill Effects (Active after Spain GP)
- **R Boost**: +0.5 for both Piastri and Leclerc
- **Immunity**: Incidents and critical failures
- **Restriction**: Not active at Australian GP

## Narrative
After the Spain GP, Piastri recognizes Leclerc as his "godfather" (义父). 
From the next race onwards, both drivers gain R+0.5 and immunity to incidents and critical failures.
The relationship is formed based on Leclerc's speed and status at the front of the grid.

## Implementation
- Both drivers must be present in the race
- Skill persists for the remainder of the season
- Activation is automatic after Spain GP
