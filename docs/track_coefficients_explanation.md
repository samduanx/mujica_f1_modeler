# Track Coefficients Explanation

This document explains the methodology and reasoning behind the C(M), C(A), and C(P) coefficients in `track_characteristics.csv`.

## Coefficient Definitions

### C(M) - Mechanical Demand (Braking)
- **Formula**: Based on braking G-force from FastF1 telemetry
- **Calculation**: Ratio of corners with max brake G > 4G to corners with brake G > 2G
- **Scale**:
  - < 35%: C(M) = 1.0 (low braking demand)
  - 35% - 40%: C(M) = 1.05 (medium braking demand)
  - > 40%: C(M) = 1.1 (high braking demand)

### C(A) - Aerodynamic Demand
- **Source**: Pirelli Preview downforce ratings (1-5 scale)
- **Formula**: C(A) = 1.0 + (5 - rating) * 0.025
- **Scale**:
  - Rating 5 (high downforce): C(A) = 1.0
  - Rating 3 (medium): C(A) = 1.05
  - Rating 1 (low downforce): C(A) = 1.1

### C(P) - Power Demand
- **Formula**: Based on full throttle percentage from FastF1 telemetry
- **Calculation**: Percentage of lap at throttle ≥ 98%
- **Scale**:
  - ≤ 70%: C(P) = 1.0 (low power demand)
  - 70% - 80%: C(P) = 1.05 (medium power demand)
  - ≥ 80%: C(P) = 1.1 (high power demand)

---

## Data Sources

| Source | Description |
|--------|-------------|
| **fastf1** | Calculated from FastF1 telemetry data (2022-2025) |
| **reference** | Original values from spain_team.csv (manually calibrated) |
| **historical** | Estimated based on F1 track characteristics |

---

## Track-by-Track Explanation

### FastF1 Data (5 tracks)

| Track | C(M) | C(P) | Reasoning |
|-------|------|------|-----------|
| Bahrain | 1.0 | 1.05 | Medium-speed circuit, 73% full throttle |
| Saudi Arabia | 1.0 | 1.1 | Fast street circuit, 83.3% full throttle |
| Australia | 1.0 | 1.1 | Fast track with long straights, 83.9% full throttle |
| Italy (Imola) | 1.0 | 1.05 | Medium-speed, 79.7% full throttle |
| Monaco | 1.0 | 1.0 | Slow street circuit, only 62.9% full throttle |

### Reference Data (1 track)

| Track | C(M) | C(A) | C(P) | Reasoning |
|-------|------|------|------|-----------|
| Spain | 1.1 | 1.025 | 1.0 | Original calibrated values from spain_team.csv |

### Historical Data (18 tracks)

#### High-Speed / High Power Tracks

**Monza (Italy)**
- C(M) = 1.0, C(A) = 1.1, C(P) = 1.1
- Reasoning: Fastest circuit on calendar. Cars run minimum downforce (C(A)=1.1) and achieve highest full throttle percentage (~80%). Very low braking demand due to long straights.

**Belgium (Spa-Francorchamps)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.1
- Reasoning: Home to Eau Rouge (high-speed corner) and long straights. High full throttle percentage (~75-80%). Moderate braking only at certain corners.

**United Kingdom (Silverstone)**
- C(M) = 1.0, C(A) = 1.025, C(P) = 1.1
- Reasoning: High-speed circuit with Maggots/Becketts complex. Long full-throttle sections (Club Corner, Hangar Straight). High cornering speeds.

**Jeddah (Saudi Arabia)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.1
- Reasoning: One of the fastest street circuits. Very long full-throttle sections through turns 2-3. High speeds through the final sector.

**Austria (Red Bull Ring)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.05
- Reasoning: Medium-high speed circuit. Long full-throttle section from turns 3-4. Fewer braking zones than typical circuits.

**Azerbaijan (Baku)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.1
- Reasoning: Fast street circuit with longest full-throttle section in F1 (Turn 3 to finish). High top speeds on the main straight.

#### Technical / High Braking Tracks

**Singapore (Marina Bay)**
- C(M) = 1.15, C(A) = 1.0, C(P) = 1.0
- Reasoning: Street circuit with many slow-speed corners and heavy braking zones. Requires maximum downforce (C(A)=1.0). Low full throttle percentage (~55-60%).

**Hungary (Hungaroring)**
- C(M) = 1.15, C(A) = 1.075, C(P) = 1.0
- Reasoning: Most technical track on the calendar. Many slow corners requiring heavy braking. Low full throttle percentage (~55-60%).

**Mexico (Rodriguez Brothers)**
- C(M) = 1.15, C(A) = 1.075, C(P) = 1.0
- Reasoning: High altitude (2,200m) reduces engine power by ~15%. More emphasis on braking and mechanical grip. Lower full throttle due to altitude effects.

**Brazil (Interlagos)**
- C(M) = 1.1, C(A) = 1.075, C(P) = 1.0
- Reasoning: Several heavy braking zones (Turn 1, Turn 4). Mixed-speed circuit with some full-throttle sections (oval section).

**Canada (Gilles Villeneuve)**
- C(M) = 1.1, C(A) = 1.05, C(P) = 1.0
- Reasoning: Street circuit with many heavy braking zones. Technical final sector requires downforce. Lower full throttle due to many slow corners.

**Netherlands (Zandvoort)**
- C(M) = 1.1, C(A) = 1.05, C(P) = 1.0
- Reasoning: Banked corner (Arie Luyendijk) allows higher cornering speeds. Technical section in the middle requires downforce. Moderate braking demand.

#### Mixed Layout Tracks

**Japan (Suzuka)**
- C(M) = 1.05, C(A) = 1.025, C(P) = 1.0
- Reasoning: Mix of high-speed (130R, Degner) and slow corners (Hairpin). Medium braking demand. Good downforce needed for the technical sections.

**USA (Austin)**
- C(M) = 1.05, C(A) = 1.05, C(P) = 1.0
- Reasoning: Mixed layout with fast first sector, technical middle, and long back straight. Medium braking and downforce requirements.

**Qatar (Lusail)**
- C(M) = 1.05, C(A) = 1.05, C(P) = 1.0
- Reasoning: Medium-speed desert circuit. Long full-throttle sections but also technical corners. Medium all-round demands.

**China (Shanghai)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.05
- Reasoning: Long straights with heavy braking at the end. Medium-high full throttle percentage. Mix of slow and fast corners.

**France (Paul Ricard)**
- C(M) = 1.0, C(A) = 1.05, C(P) = 1.05
- Reasoning: Medium-high speed circuit with long straights. Moderate braking zones. Similar demands to Barcelona.

**Miami**
- C(M) = 1.1, C(A) = 1.075, C(P) = 1.0
- Reasoning: New street circuit with slow-speed technical sections. Heavy braking into the stadium section. Requires good downforce.

---

## Pirelli C(A) Values by Downforce Rating

| Rating | C(A) | Example Tracks |
|--------|------|----------------|
| 5 (Highest) | 1.0 | Monaco, Singapore |
| 4 | 1.025 | UK (Silverstone), Japan (Suzuka) |
| 3 | 1.05 | Bahrain, Australia, Austria, Belgium |
| 2 | 1.075 | Miami, Canada, Hungary, Mexico, Brazil |
| 1 (Lowest) | 1.1 | Italy (Monza) |

---

## Notes

1. **FastF1 data is limited** to years 2022-2025 and may have rate-limiting issues. More tracks can be calculated with improved data collection.

2. **Historical values are estimates** based on F1 broadcasting data, Pirelli previews, and track characteristics. They should be validated against real telemetry when possible.

3. **Spain reference values** are preserved for comparison with FastF1 calculations:
   - Reference: C(M)=1.1, C(A)=1.025, C(P)=1.0
   - FastF1: C(M)=1.0, C(A)=1.05, C(P)=1.05

4. **The C(A) scale is inverted** in the PR calculation: higher C(A) means the car needs to generate MORE downforce naturally (i.e., the track requires less dedicated downforce setup).

---

## FastF1 Data vs Historical Comparison

The following 18 tracks have actual FastF1 telemetry data for C(P):

| Track | C(P) from FastF1 | Full Throttle % | Years Analyzed |
|-------|-------------------|-----------------|----------------|
| Italy (Monza) | 1.1 | 86.2% | 2023 |
| Saudi Arabia | 1.1 | 83.3% | 2024, 2025 |
| Japan | 1.1 | 82.8% | 2023, 2025 |
| Qatar | 1.1 | 81.2% | 2023, 2024 |
| Belgium | 1.1 | 81.4% | 2023, 2025 |
| UK (Silverstone) | 1.1 | 82.7% | 2022 |
| Australia | 1.1 | 83.9% | 2023, 2024 |
| Italy (Imola) | 1.05 | 79.7% | 2024, 2025 |
| Abu Dhabi | 1.05 | 78.3% | 2022, 2023, 2024 |
| Austria | 1.05 | 78.6% | 2022, 2024 |
| Spain | 1.05 | 77.0% | 2022, 2024 |
| Canada | 1.05 | 75.6% | 2022, 2024 |
| USA | 1.05 | 74.8% | 2023, 2024 |
| Hungary | 1.05 | 73.6% | 2022, 2023, 2024 |
| France | 1.05 | 73.1% | 2022 |
| Bahrain | 1.05 | 73.0% | 2023, 2024, 2025 |
| China | 1.05 | 73.8% | 2024, 2025 |
| Monaco | 1.0 | 62.9% | 2022, 2025 |
| Singapore | 1.0 | 68.3% | 2022, 2025 |

### Tracks without FastF1 data (5 tracks - using historical):

| Track | C(P) | Reasoning |
|-------|------|-----------|
| Miami | 1.0 | New circuit, street characteristics |
| Azerbaijan | 1.0 | Fast street circuit |
| Netherlands | 1.0 | Banked corners, medium speed |
| Mexico | 1.0 | High altitude reduces power effect |
| Brazil | 1.0 | Mixed layout, heavy braking |

### Key Observations:

1. **C(P) accuracy**: FastF1-derived C(P) values match real F1 characteristics:
   - High-speed circuits (Belgium, Saudi Arabia, UK): C(P) = 1.1
   - Technical circuits (Monaco, Singapore): C(P) = 1.0
   - Medium circuits: C(P) = 1.05

2. **C(M) limitations**: FastF1 braking data showed all tracks with C(M) = 1.0, which doesn't match real F1 characteristics. This is due to limitations in the telemetry corner detection algorithm. Historical C(M) values are used instead.

3. **Spain comparison**:
   - Reference: C(M)=1.1, C(A)=1.025, C(P)=1.0
   - FastF1: C(M)=1.0, C(A)=1.05, C(P)=1.05
   - The reference values represent a "more aggressive" braking and aero setup
