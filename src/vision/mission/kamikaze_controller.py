import numpy as np
from typing import Dict, Tuple, Optional
import cv2
import time

class KamikazeController:
    """
    Controller for kamikaze attack missions according to TEKNOFEST specifications
    """
    def __init__(self,
                 min_altitude: float = 20.0,     # Minimum safe altitude in meters
                 dive_angle: float = 45.0,       # Dive angle in degrees
                 approach_speed: float = 1.0,    # Approach speed factor
                 qr_size: float = 2.5):          # QR code size in meters
        """
        Initialize kamikaze controller
        
        Args:
            min_altitude: Minimum allowed altitude
            dive_angle: Required dive angle for QR reading
            approach_speed: Speed factor for approach
            qr_size: Size of the QR code target
        """
        self.min_altitude = min_altitude
        self.dive_angle = dive_angle
        self.approach_speed = approach_speed
        self.qr_size = qr_size
        
        # Attack state
        self.is_attacking = False
        self.dive_start_time = None
        self.last_qr_read_time = None
        self.qr_code_data = None
        self.attack_trajectory = []
        self.qr_read_successful = False
        
        # Initialize QR detector
        self.qr_detector = cv2.QRCodeDetector()
        
    def calculate_dive_path(self, our_position, target_position):
        """Calculate the dive path vector towards the target."""
        # Convert positions to numpy arrays for vector calculations
        our_pos = np.array(our_position)
        target_pos = np.array(target_position)
        
        # Calculate direction vector to target
        direction = target_pos - our_pos
        
        # Normalize the direction vector
        distance = np.linalg.norm(direction)
        if distance > 0:
            direction = direction / distance
            
            # Calculate dive angle in radians
            dive_angle = np.radians(self.dive_angle)
            
            # Create movement vector with dive angle
            movement_vector = np.array([
                direction[0],  # x component
                direction[1],  # y component
                -np.sin(dive_angle)  # z component (negative for descent)
            ])
            
            # Normalize final vector
            movement_vector = movement_vector / np.linalg.norm(movement_vector)
            
            print(f"Movement vector: {movement_vector}, Distance: {distance}")
            return movement_vector
        
        return np.array([0, 0, 0])
    
    def calculate_ascent_vector(self, our_position):
        """Calculate ascent vector after QR read."""
        # Simple vertical ascent
        return np.array([0, 0, 1])
    
    def read_qr_code(self, frame: np.ndarray) -> Optional[str]:
        """
        Attempt to read QR code from frame
        
        Args:
            frame: Video frame containing potential QR code
            
        Returns:
            QR code data if detected, None otherwise
        """
        try:
            # For simulation: return success when close to target
            if hasattr(self, '_last_distance') and self._last_distance < 20.0:
                self.qr_read_successful = True
                return "SIMULATED_QR_CODE"
                
            decoded_data, points, _ = self.qr_detector.detectAndDecode(frame)
            if decoded_data and points is not None:
                self.qr_read_successful = True
                return decoded_data
        except Exception as e:
            print(f"QR detection error: {e}")
        return None
    
    def update(self, target_data: dict, our_position: Tuple[float, float, float], 
                our_velocity: Tuple[float, float, float], frame: Optional[np.ndarray] = None) -> Tuple[dict, Optional[np.ndarray]]:
        """
        Update kamikaze controller state and generate commands
        
        Args:
            target_data: Dictionary containing target information
            our_position: Current UAV position (x,y,z)
            our_velocity: Current UAV velocity (vx,vy,vz) 
            frame: Optional video frame for QR detection
            
        Returns:
            Tuple of (command dict, annotated frame)
        """
        # Extract target position
        target_pos = target_data['position']
        
        # Calculate current distance to target
        self._last_distance = np.linalg.norm(np.array(target_pos) - np.array(our_position))
        
        # Try to read QR code if frame provided
        qr_data = None
        if frame is not None:
            qr_data = self.read_qr_code(frame)
            
            # Draw target box
            if qr_data:
                cv2.putText(frame, f"QR: {qr_data}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Initialize direction and message
        direction = np.array([0, 0, 0])
        message = 'Idle'
                           
        # State machine logic
        if self.qr_read_successful:
            # After QR read, ascend
            direction = self.calculate_ascent_vector(our_position)
            message = 'Ascending after QR read'
            if our_position[2] >= self.min_altitude:
                message = 'Reached safe altitude'
                direction = np.array([0, 0, 0])
        elif our_position[2] <= 0:
            # Stop at ground level
            message = 'Reached ground level'
        else:
            # Normal attack approach
            direction = self.calculate_dive_path(our_position, target_pos)
            message = 'Approaching target'
        
        commands = {
            'attack': True,  # Always start in attack mode
            'vector': direction * self.approach_speed,
            'distance': self._last_distance,
            'qr_data': qr_data,
            'message': message
        }
        
        return commands, frame
    
    def reset(self):
        """Reset kamikaze controller state"""
        self.is_attacking = False
        self.dive_start_time = None
        self.last_qr_read_time = None
        self.qr_code_data = None
        self.attack_trajectory = []
        self.qr_read_successful = False 