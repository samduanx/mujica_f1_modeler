"""
Test script for sector flag system.
Run with: uv run python -c "import sys; sys.path.insert(0, 'src'); exec(open('src/incidents/tests/test_sector_flags.py').read())"
"""

from incidents.sector_flags import SectorFlag, SectorFlagManager, YellowFlagImpact
from drs.overtake_trigger import TimeIntervalOvertakeSystem

print("=" * 60)
print("SECTOR FLAG SYSTEM TEST")
print("=" * 60)

# Test 1: Basic sector flag operations
print("\n1. Basic Sector Flag Operations")
flag_manager = SectorFlagManager(num_sectors=3)

print(f"   Initial state: {flag_manager.get_full_state()}")

# Set yellow flag in sector 2
class MockIncident:
    def __init__(self):
        self.incident_type = type('obj', (object,), {'value': 'test'})()

mock_incident = MockIncident()
flag_manager.set_yellow_flag(
    sector=2,
    incident=mock_incident,
    race_time=120.5,
    double_yellow=False
)

print(f"   After yellow in sector 2: {flag_manager.get_active_flags_summary()}")
print(f"   Can overtake sector 1: {flag_manager.can_overtake(1)}")
print(f"   Can overtake sector 2: {flag_manager.can_overtake(2)}")
print(f"   Can overtake sector 3: {flag_manager.can_overtake(3)}")

# Set double yellow in sector 1
flag_manager.set_yellow_flag(
    sector=1,
    incident=mock_incident,
    race_time=125.0,
    double_yellow=True
)

print(f"   After double yellow in sector 1: {flag_manager.get_active_flags_summary()}")
print(f"   Flagged sectors: {flag_manager.get_all_flagged_sectors()}")

# Clear flags
flag_manager.clear_yellow_flag(sector=2, race_time=180.0)
print(f"   After clearing sector 2: {flag_manager.get_active_flags_summary()}")

# Test 2: Yellow Flag Impact on Lap Times
print("\n2. Yellow Flag Impact on Lap Times")
yellow_impact = YellowFlagImpact(flag_manager)
base_lap_time = 90.0  # seconds

for sector in [1, 2, 3]:
    impact = yellow_impact.get_sector_impact(sector, base_lap_time)
    print(f"   Sector {sector}: {impact}")

# Test 3: Overtake System Integration
print("\n3. Overtake System Integration")
ot_system = TimeIntervalOvertakeSystem(track_name="default")

# Test overtake with green flag
result, reason, debug = ot_system.should_overtake(
    current_time=100.0,
    lap=5,
    total_laps=50,
    in_drs_zone=True,
    gap_ahead=0.8,
    section_type="straight",
    drivers_in_range=2,
    attacker_name="Verstappen",
    defender_name="Norris",
    sector_flag_manager=flag_manager,
    current_sector=3,  # Sector 3 is green
)
print(f"   Sector 3 (green): Overtake allowed = {result}, reason = {reason[:50]}...")

# Test overtake with yellow flag
result, reason, debug = ot_system.should_overtake(
    current_time=100.0,
    lap=5,
    total_laps=50,
    in_drs_zone=True,
    gap_ahead=0.8,
    section_type="straight",
    drivers_in_range=2,
    attacker_name="Verstappen",
    defender_name="Norris",
    sector_flag_manager=flag_manager,
    current_sector=1,  # Sector 1 has double yellow
)
print(f"   Sector 1 (double yellow): Overtake allowed = {result}")
print(f"   Reason: {reason}")
print(f"   Debug info: {debug}")

# Test 4: Check sector flag helper method
print("\n4. Check Sector Flag Helper")
can_overtake, flag_reason = ot_system.check_sector_flag(flag_manager, current_sector=1)
print(f"   Can overtake sector 1: {can_overtake}, reason: {flag_reason}")

can_overtake, flag_reason = ot_system.check_sector_flag(flag_manager, current_sector=3)
print(f"   Can overtake sector 3: {can_overtake}, reason: {flag_reason}")

# Test 5: Flag History
print("\n5. Flag History")
print(f"   Number of flag changes: {len(flag_manager.flag_history)}")
for entry in flag_manager.flag_history:
    print(f"   Time {entry['time']:.1f}s: Sector {entry['sector']} - {entry['old_flag']} -> {entry['new_flag']}")

# Test 6: Reset
print("\n6. Reset")
flag_manager.reset()
print(f"   After reset: {flag_manager.get_active_flags_summary()}")

print("\n" + "=" * 60)
print("All sector flag tests completed successfully!")
print("=" * 60)
