from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Optional
import time

class MissionPriority(Enum):
    """Mission priority levels"""
    CRITICAL = auto()    # Immediate action required (e.g., being locked on)
    HIGH = auto()        # Important but not critical (e.g., kamikaze opportunity)
    MEDIUM = auto()      # Standard operations (e.g., tracking target)
    LOW = auto()         # Background tasks (e.g., area scanning)

class MissionType(Enum):
    """Available mission types"""
    SCAN = auto()          # Scan area for targets
    TRACK = auto()         # Track specific target
    LOCK = auto()          # Lock onto target
    KAMIKAZE = auto()      # Execute kamikaze attack
    ESCAPE = auto()        # Escape from threat
    RETURN_HOME = auto()   # Return to home position
    
    def get_default_priority(self) -> 'MissionPriority':
        """Get default priority for mission type"""
        priority_map = {
            MissionType.SCAN: MissionPriority.LOW,
            MissionType.TRACK: MissionPriority.MEDIUM,
            MissionType.LOCK: MissionPriority.HIGH,
            MissionType.KAMIKAZE: MissionPriority.HIGH,
            MissionType.ESCAPE: MissionPriority.CRITICAL,
            MissionType.RETURN_HOME: MissionPriority.MEDIUM
        }
        return priority_map[self]

class MissionStatus(Enum):
    """Mission execution status"""
    PENDING = auto()     # Not yet started
    ACTIVE = auto()      # Currently executing
    COMPLETED = auto()   # Successfully completed
    FAILED = auto()      # Failed to complete
    INTERRUPTED = auto() # Interrupted by higher priority mission

@dataclass
class MissionData:
    """Mission data container"""
    mission_id: str
    mission_type: MissionType
    priority: MissionPriority
    status: MissionStatus
    start_time: float
    completion_time: Optional[float] = None
    target_id: Optional[str] = None
    parameters: Dict = None
    
    def duration(self) -> float:
        """Calculate mission duration"""
        end_time = self.completion_time or time.time()
        return end_time - self.start_time
    
    def update_status(self, new_status: MissionStatus):
        """Update mission status"""
        self.status = new_status
        if new_status in [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.INTERRUPTED]:
            self.completion_time = time.time()

class MissionResult:
    """Mission execution result"""
    def __init__(self, 
                 success: bool,
                 message: str = "",
                 data: Dict = None):
        self.success = success
        self.message = message
        self.data = data or {} 