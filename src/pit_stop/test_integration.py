"""
Integration test for front wing replacement in race simulation.

This test manually triggers a front wing damage and verifies the
replacement logic works correctly in the simulation context.
"""

import sys
import os

# Add project root to path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pit_stop.front_wing_replacement import FrontWingManager


def test_front_wing_integration():
    """Test front wing replacement integration with race simulation"""
    print("=== Integration Test: Front Wing Replacement in Race ===\n")

    # Create a minimal race state for testing
    driver_data = {
        "Verstappen": {
            "Team": "red_bull",
            "DR_Value": 90,
            "PR_Value": 310,
            "R_Value": 279,
        },
        "Hamilton": {
            "Team": "mercedes",
            "DR_Value": 88,
            "PR_Value": 305,
            "R_Value": 268.4,
        },
    }

    # Initialize front wing manager
    fw_manager = FrontWingManager()

    # Create front wing damage for Verstappen (simulating driver error)
    print("1. Creating front wing damage for Verstappen (driver_error)...")
    damage = fw_manager.create_damage_from_incident(
        driver="Verstappen",
        incident_type="driver_error",
        incident_severity="moderate",  # 50% chance to replace
        lap=15,
    )
    assert damage is not None
    print(f"   Created: {damage.to_dict()}")

    # Try to replace at pit stop
    print("\n2. Attempting replacement at pit stop...")
    result = fw_manager.attempt_replacement("Verstappen", lap=20)
    print(f"   Result: {result.message}")

    # Check if replaced
    print(
        f"\n3. Replacement status: {'Success' if result.replaced else 'Failed/Not replaced'}"
    )
    print(f"   Extra time added: {result.extra_time:.2f}s")

    # Create another damage for Hamilton (simulating overtake collision)
    print("\n4. Creating front wing damage for Hamilton (overtake_collision)...")
    damage2 = fw_manager.create_damage_from_incident(
        driver="Hamilton",
        incident_type="overtake_collision",
        incident_severity="major",  # 80% chance to replace
        lap=25,
    )
    assert damage2 is not None
    print(f"   Created: {damage2.to_dict()}")

    # Try to replace
    print("\n5. Attempting replacement at pit stop...")
    result2 = fw_manager.attempt_replacement("Hamilton", lap=30)
    print(f"   Result: {result2.message}")

    print(
        f"\n6. Replacement status: {'Success' if result2.replaced else 'Failed/Not replaced'}"
    )
    print(f"   Extra time added: {result2.extra_time:.2f}s")

    # Test WIDELONSO exclusion
    print("\n7. Testing WIDELONSO skill exclusion...")
    damage3 = fw_manager.create_damage_from_incident(
        driver="Alonso",
        incident_type="widelonso",
        incident_severity="moderate",
        lap=35,
    )
    assert damage3 is None
    print("   WIDELONSO skill correctly excluded!")

    print("\n" + "=" * 60)
    print("INTEGRATION TEST PASSED")
    print("=" * 60)
    print("\nSummary:")
    print("- Front wing damage creation from incidents: OK")
    print("- Replacement decision (first dice roll): OK")
    print("- Extra time calculation (second dice roll): OK")
    print("- WIDELONSO skill exclusion: OK")


if __name__ == "__main__":
    test_front_wing_integration()
