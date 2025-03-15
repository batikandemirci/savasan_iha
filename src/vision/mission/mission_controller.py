from enum import Enum
from typing import Dict, Optional
import time
from detection.qr.qr_processor import QRCommand

class MissionState(Enum):
    """Mission states"""
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    TRACKING = "TRACKING"
    LOCKING = "LOCKING"
    LOCKED = "LOCKED"
    KAMIKAZE = "KAMIKAZE"
    ESCAPING = "ESCAPING"
    EMERGENCY = "EMERGENCY"

class MissionController:
    """
    Mission state and command controller
    """
    def __init__(self):
        """Initialize mission controller"""
        self.current_state = MissionState.IDLE
        self.previous_state = None
        self.state_change_time = time.time()
        self.mission_data = {}
        self.state_history = []
        
    def update_state(self, new_state: MissionState):
        """
        Update mission state
        
        Args:
            new_state: New mission state
        """
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_change_time = time.time()
            
            # Record state change
            state_info = {
                'state': new_state,
                'timestamp': self.state_change_time,
                'previous_state': self.previous_state
            }
            self.state_history.append(state_info)
            
            # Keep only last 100 state changes
            if len(self.state_history) > 100:
                self.state_history.pop(0)
    
    def process_command(self, command_info: Dict) -> bool:
        """
        Process mission command
        
        Args:
            command_info: Command information from QR processor
            
        Returns:
            True if command was processed successfully
        """
        command_type = command_info['type']
        parameters = command_info['parameters']
        
        if command_type == QRCommand.KAMIKAZE:
            if self.current_state in [MissionState.LOCKED, MissionState.TRACKING]:
                self.update_state(MissionState.KAMIKAZE)
                self.mission_data['kamikaze_target'] = parameters.get('target_id')
                return True
                
        elif command_type == QRCommand.ESCAPE:
            if self.current_state != MissionState.EMERGENCY:
                self.update_state(MissionState.ESCAPING)
                self.mission_data['escape_direction'] = parameters.get('direction')
                return True
                
        elif command_type == QRCommand.LOCK:
            if self.current_state == MissionState.TRACKING:
                self.update_state(MissionState.LOCKING)
                self.mission_data['lock_target'] = parameters.get('target_id')
                return True
                
        elif command_type == QRCommand.MISSION_UPDATE:
            self.mission_data.update(parameters)
            return True
            
        elif command_type == QRCommand.STATUS_REQUEST:
            # Handle status request (could trigger telemetry)
            return True
            
        return False
    
    def get_mission_status(self) -> Dict:
        """Get current mission status"""
        return {
            'current_state': self.current_state,
            'previous_state': self.previous_state,
            'state_duration': time.time() - self.state_change_time,
            'mission_data': self.mission_data,
            'state_history': self.state_history
        }
    
    def reset(self):
        """Reset mission controller to initial state"""
        self.current_state = MissionState.IDLE
        self.previous_state = None
        self.state_change_time = time.time()
        self.mission_data = {}
        self.state_history = [] 