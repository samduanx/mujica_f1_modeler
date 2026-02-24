"""
Test script for incident system.
Run with: uv run python -m src.incidents.tests.test_incident_system
"""

import sys

sys.path.insert(0, "/home/samduan/Documents/Devs/Codes/mujica_f1_modeler")

from incidents import (
    IncidentManager,
    TeamStability,
    VehicleFaultResolver,
    DriverErrorProbability,
)
from incidents.overtake_incident import OvertakeIncidentProbability, OvertakeSituation
from incidents.incident_types import TrackDifficulty
from incidents.double_attack import DoubleAttackSystem


def test_vehicle_fault_system():
    """Test vehicle fault system with team stability values"""
    print("=" * 60)
    print("Testing Vehicle Fault System")
    print("=" * 60)

    # Test all teams
    teams = [
        ("Aston Martin", 98.5),
        ("Mercedes", 97.0),
        ("Haas", 97.5),
        ("Alpine", 97.75),
        ("Ferrari", 95.0),
        ("Red Bull", 96.0),
        ("McLaren", 96.5),
        ("Williams", 95.0),
    ]

    for team_name, stability in teams:
        stability_config = TeamStability(
            team_name=team_name,
            base_stability=stability,
        )
        resolver = VehicleFaultResolver(stability_config)

        fault_prob = stability_config.get_fault_probability(
            laps_on_pu=30,
            race_distance_km=150,
            has_incident_damage=False,
        )

        print(
            f"{team_name:20} (Stability: {stability:.1f}): Fault Prob = {fault_prob:.4f}"
        )

    print()


def test_driver_error_system():
    """Test driver error probability based on DR value"""
    print("=" * 60)
    print("Testing Driver Error System")
    print("=" * 60)

    dr_values = [78, 82, 86, 90, 92, 95]

    for dr in dr_values:
        prob = DriverErrorProbability().get_error_probability(
            dr_value=dr,
            lap_number=15,
            tyre_degradation=1.05,
            race_position=5,
            under_pressure=False,
            is_first_lap=False,
        )
        print(f"DR {dr:2d}: Error Prob = {prob:.4f}")

    print()


def test_overtake_incident_system():
    """Test overtake incident probability"""
    print("=" * 60)
    print("Testing Overtake Incident System")
    print("=" * 60)

    calc = OvertakeIncidentProbability(TrackDifficulty.MEDIUM)

    # Test different DR margins
    dr_margins = [-5, -2, 0, 2, 5]

    for dr_margin in dr_margins:
        prob = calc.get_collision_probability(
            situation=OvertakeSituation.IN_DRS_ZONE,
            dr_margin=dr_margin,
            speed_delta=15,
            attacker_dr_value=88,
            defender_dr_value=88,
        )
        print(f"DR Margin {dr_margin:+2d}: Collision Prob = {prob:.4f}")

    print()


def test_double_attack_system():
    """Test double attack system"""
    print("=" * 60)
    print("Testing Double Attack System")
    print("=" * 60)

    system = DoubleAttackSystem()

    # Test can_initiate_double_attack
    result, reason = system.can_initiate_double_attack(
        time_since_overtake=5.0,
        defender_tyre_degradation=1.05,
        attacker_has_drs=True,
        defender_has_drs=False,
        defender_dr=88,
        attacker_dr=90,
    )
    print(f"Can double attack (5s after, DR +2): {result} - {reason}")

    result, reason = system.can_initiate_double_attack(
        time_since_overtake=2.0,
        defender_tyre_degradation=1.05,
        attacker_has_drs=False,
        defender_has_drs=True,
        defender_dr=88,
        attacker_dr=90,
    )
    print(f"Can double attack (2s after, DR +2, DRS): {result} - {reason}")

    # Test probability
    prob = system.get_double_attack_probability(
        time_since_overtake=3.0,
        dr_diff=2,
        defender_has_drs=True,
    )
    print(f"Double attack probability: {prob:.4f}")

    print()


def test_incident_manager():
    """Test incident manager"""
    print("=" * 60)
    print("Testing Incident Manager")
    print("=" * 60)

    manager = IncidentManager(track_difficulty=TrackDifficulty.MEDIUM)

    # Simulate some drivers
    drivers = {
        "Verstappen": {
            "name": "Verstappen",
            "dr_value": 92,
            "position": 1,
            "team": "Red Bull",
            "tyre_degradation": 1.02,
            "under_pressure": False,
        },
        "Norris": {
            "name": "Norris",
            "dr_value": 88,
            "position": 2,
            "team": "McLaren",
            "tyre_degradation": 1.03,
            "under_pressure": True,
        },
        "Leclerc": {
            "name": "Leclerc",
            "dr_value": 85,
            "position": 3,
            "team": "Ferrari",
            "tyre_degradation": 1.05,
            "under_pressure": False,
        },
    }

    # Check for incidents over several "intervals"
    for lap in [1, 5, 15, 30, 50]:
        for i in range(10):  # Multiple checks per lap
            current_time = lap * 90 + i * 10
            incident = manager.check_incident(
                current_time=current_time,
                lap=lap,
                drivers=drivers,
                is_overtake_situation=(i % 3 == 0),
                situation=OvertakeSituation.IN_DRS_ZONE,
            )
            if incident:
                manager.add_incident(incident)
                print(
                    f"Lap {lap}: {incident.description} - {incident.narrative[:50]}..."
                )

    # Get statistics
    stats = manager.get_statistics()
    print(f"\nTotal incidents: {stats.total_incidents}")
    print(f"Incidents by type: {stats.incidents_by_type}")

    print()


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("INCIDENT SYSTEM TEST SUITE")
    print("=" * 60 + "\n")

    test_vehicle_fault_system()
    test_driver_error_system()
    test_overtake_incident_system()
    test_double_attack_system()
    test_incident_manager()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
