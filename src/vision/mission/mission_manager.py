from typing import Dict, List, Optional
import time
import uuid
from .mission_types import (
    MissionType, MissionPriority, MissionStatus,
    MissionData, MissionResult
)

class MissionManager:
    """
    Mission management system for UAV autonomous operations
    """
    def __init__(self):
        """Initialize mission manager"""
        self.active_missions: Dict[str, MissionData] = {}
        self.mission_history: List[MissionData] = []
        self.current_mission: Optional[MissionData] = None
        
    def create_mission(self, 
                      mission_type: MissionType,
                      target_id: str = None,
                      priority: MissionPriority = None,
                      parameters: Dict = None) -> MissionData:
        """
        Create a new mission
        
        Args:
            mission_type: Type of mission to create
            target_id: Optional target ID
            priority: Optional priority override
            parameters: Optional mission parameters
            
        Returns:
            Created mission data
        """
        # Generate unique mission ID
        mission_id = str(uuid.uuid4())
        
        # Use default priority if not specified
        if priority is None:
            priority = mission_type.get_default_priority()
            
        # Create mission data
        mission = MissionData(
            mission_id=mission_id,
            mission_type=mission_type,
            priority=priority,
            status=MissionStatus.PENDING,
            start_time=time.time(),
            target_id=target_id,
            parameters=parameters or {}
        )
        
        # Add to active missions
        self.active_missions[mission_id] = mission
        return mission
    
    def update_mission_status(self, 
                            mission_id: str,
                            new_status: MissionStatus,
                            result: MissionResult = None):
        """Update mission status and handle completion"""
        if mission_id not in self.active_missions:
            return
            
        mission = self.active_missions[mission_id]
        mission.update_status(new_status)
        
        # Handle completed missions
        if new_status in [MissionStatus.COMPLETED, MissionStatus.FAILED]:
            # Move to history
            self.mission_history.append(mission)
            del self.active_missions[mission_id]
            
            # Clear current mission if this was it
            if self.current_mission and self.current_mission.mission_id == mission_id:
                self.current_mission = None
    
    def get_highest_priority_mission(self) -> Optional[MissionData]:
        """Get the highest priority pending mission"""
        if not self.active_missions:
            return None
            
        # Sort by priority (CRITICAL = highest)
        pending_missions = [
            m for m in self.active_missions.values()
            if m.status == MissionStatus.PENDING
        ]
        
        if not pending_missions:
            return None
            
        return max(pending_missions, key=lambda m: m.priority.value)
    
    def interrupt_current_mission(self, reason: str = "Interrupted by higher priority mission"):
        """Interrupt current mission if any"""
        if self.current_mission:
            self.update_mission_status(
                self.current_mission.mission_id,
                MissionStatus.INTERRUPTED,
                MissionResult(False, reason)
            )
            self.current_mission = None
    
    def update(self) -> Optional[MissionData]:
        """
        Update mission manager state
        
        Returns:
            Current active mission or None
        """
        # Check for higher priority mission
        highest_priority = self.get_highest_priority_mission()
        
        if highest_priority:
            if not self.current_mission:
                # No current mission, start the highest priority one
                highest_priority.update_status(MissionStatus.ACTIVE)
                self.current_mission = highest_priority
            elif (highest_priority.priority.value > 
                  self.current_mission.priority.value):
                # Interrupt current mission for higher priority
                self.interrupt_current_mission()
                highest_priority.update_status(MissionStatus.ACTIVE)
                self.current_mission = highest_priority
                
        return self.current_mission
    
    def get_mission_stats(self) -> Dict:
        """Get mission statistics"""
        total_missions = len(self.mission_history) + len(self.active_missions)
        completed_missions = len([
            m for m in self.mission_history
            if m.status == MissionStatus.COMPLETED
        ])
        failed_missions = len([
            m for m in self.mission_history
            if m.status == MissionStatus.FAILED
        ])
        interrupted_missions = len([
            m for m in self.mission_history
            if m.status == MissionStatus.INTERRUPTED
        ])
        
        return {
            'total_missions': total_missions,
            'active_missions': len(self.active_missions),
            'completed_missions': completed_missions,
            'failed_missions': failed_missions,
            'interrupted_missions': interrupted_missions,
            'success_rate': (completed_missions / max(1, total_missions)) * 100
        }
    
    def get_mission_history(self, 
                          mission_type: MissionType = None,
                          status: MissionStatus = None) -> List[MissionData]:
        """Get filtered mission history"""
        history = self.mission_history.copy()
        
        if mission_type:
            history = [m for m in history if m.mission_type == mission_type]
        if status:
            history = [m for m in history if m.status == status]
            
        return history 