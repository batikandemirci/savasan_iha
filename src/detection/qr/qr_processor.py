from typing import Dict, Optional
import json
import time
from enum import Enum

class QRCommand(Enum):
    """QR code command types"""
    KAMIKAZE = "KAMIKAZE"
    ESCAPE = "ESCAPE"
    LOCK = "LOCK"
    MISSION_UPDATE = "MISSION_UPDATE"
    STATUS_REQUEST = "STATUS_REQUEST"

class QRProcessor:
    """
    QR code data processing and command handling
    """
    def __init__(self):
        """Initialize QR processor"""
        self.last_command = None
        self.last_command_time = None
        self.command_history = []
        self.command_cooldown = 2.0  # Seconds between same commands
        
    def process_qr_data(self, qr_data: str) -> Optional[Dict]:
        """
        Process QR code data and extract commands
        
        Args:
            qr_data: Raw QR code data string
            
        Returns:
            Dictionary containing processed command info or None if invalid
        """
        try:
            # Try to parse as JSON
            data = json.loads(qr_data)
            
            # Validate required fields
            if 'command' not in data:
                return None
                
            # Convert command to enum
            try:
                command_type = QRCommand(data['command'])
            except ValueError:
                return None
                
            # Check command cooldown
            current_time = time.time()
            if (self.last_command == command_type and 
                self.last_command_time and 
                current_time - self.last_command_time < self.command_cooldown):
                return None
                
            # Create command info
            command_info = {
                'type': command_type,
                'timestamp': current_time,
                'raw_data': data,
                'parameters': data.get('parameters', {})
            }
            
            # Update state
            self.last_command = command_type
            self.last_command_time = current_time
            self.command_history.append(command_info)
            
            # Keep only last 50 commands
            if len(self.command_history) > 50:
                self.command_history.pop(0)
                
            return command_info
            
        except json.JSONDecodeError:
            return None
            
    def get_command_history(self) -> list:
        """Get command history"""
        return self.command_history
        
    def clear_history(self):
        """Clear command history"""
        self.command_history = []
        self.last_command = None
        self.last_command_time = None
        
    @staticmethod
    def create_qr_command(command_type: QRCommand, 
                         parameters: Dict = None) -> str:
        """
        Create a QR command string
        
        Args:
            command_type: Type of command
            parameters: Optional command parameters
            
        Returns:
            JSON string for QR code generation
        """
        command_data = {
            'command': command_type.value,
            'parameters': parameters or {}
        }
        return json.dumps(command_data) 