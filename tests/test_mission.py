import time
from vision.mission.mission_types import (
    MissionType, MissionPriority, MissionStatus, MissionResult
)
from vision.mission.mission_manager import MissionManager

def print_mission_status(mission_manager: MissionManager):
    """Print current mission status"""
    current = mission_manager.current_mission
    stats = mission_manager.get_mission_stats()
    
    print("\nCurrent Mission:", 
          current.mission_id if current else "None")
    if current:
        print(f"Type: {current.mission_type}")
        print(f"Priority: {current.priority}")
        print(f"Status: {current.status}")
        print(f"Duration: {current.duration():.1f}s")
    
    print("\nMission Stats:")
    print(f"Total Missions: {stats['total_missions']}")
    print(f"Active: {stats['active_missions']}")
    print(f"Completed: {stats['completed_missions']}")
    print(f"Failed: {stats['failed_missions']}")
    print(f"Interrupted: {stats['interrupted_missions']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")

def main():
    # Create mission manager
    manager = MissionManager()
    
    print("Mission Priority Test Starting...")
    print("Simulating different mission scenarios...")
    
    # Scenario 1: Basic scanning and tracking
    print("\nScenario 1: Basic scanning and tracking")
    scan_mission = manager.create_mission(
        MissionType.SCAN,
        parameters={'area': 'NORTH'}
    )
    manager.update()
    print_mission_status(manager)
    
    time.sleep(2)  # Simulate some time passing
    
    # Add tracking mission (higher priority)
    print("\nAdding tracking mission...")
    track_mission = manager.create_mission(
        MissionType.TRACK,
        target_id='UAV_001'
    )
    manager.update()
    print_mission_status(manager)
    
    time.sleep(2)
    
    # Scenario 2: Emergency escape
    print("\nScenario 2: Emergency escape")
    escape_mission = manager.create_mission(
        MissionType.ESCAPE,
        parameters={'direction': 'WEST'}
    )
    manager.update()
    print_mission_status(manager)
    
    time.sleep(2)
    
    # Complete escape mission
    print("\nCompleting escape mission...")
    manager.update_mission_status(
        escape_mission.mission_id,
        MissionStatus.COMPLETED,
        MissionResult(True, "Successfully escaped")
    )
    manager.update()
    print_mission_status(manager)
    
    # Scenario 3: Multiple concurrent missions
    print("\nScenario 3: Multiple concurrent missions")
    missions = [
        (MissionType.SCAN, None, MissionPriority.LOW),
        (MissionType.TRACK, 'UAV_002', MissionPriority.MEDIUM),
        (MissionType.LOCK, 'UAV_002', MissionPriority.HIGH),
        (MissionType.KAMIKAZE, 'UAV_002', MissionPriority.HIGH)
    ]
    
    for mission_type, target_id, priority in missions:
        manager.create_mission(
            mission_type,
            target_id=target_id,
            priority=priority
        )
        manager.update()
        print(f"\nAdded {mission_type.name} mission")
        print_mission_status(manager)
        time.sleep(1)
    
    # Scenario 4: Mission completion and transitions
    print("\nScenario 4: Mission completion and transitions")
    current = manager.current_mission
    if current:
        print(f"\nCompleting current {current.mission_type.name} mission...")
        manager.update_mission_status(
            current.mission_id,
            MissionStatus.COMPLETED,
            MissionResult(True, "Mission completed successfully")
        )
        manager.update()
        print_mission_status(manager)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main() 