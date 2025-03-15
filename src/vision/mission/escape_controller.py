import numpy as np
from typing import Dict, Tuple, Optional
import cv2
import time

class EscapeController:
    """
    Controller for escape maneuvers when enemy UAV lock is detected
    """
    def __init__(self,
                 min_altitude: float = 50.0,     # Minimum safe altitude in meters
                 max_altitude: float = 100.0,    # Maximum altitude for escape
                 escape_speed: float = 2.0,      # Escape speed multiplier
                 safe_distance: float = 30.0):   # Safe distance from enemy in meters
        """
        Initialize escape controller
        
        Args:
            min_altitude: Minimum allowed altitude
            max_altitude: Maximum allowed altitude
            escape_speed: Speed multiplier for escape maneuvers
            safe_distance: Minimum safe distance from enemy
        """
        self.min_altitude = min_altitude
        self.max_altitude = max_altitude
        self.escape_speed = escape_speed
        self.safe_distance = safe_distance
        
        # Escape state
        self.is_escaping = False
        self.escape_start_time = None
        self.last_enemy_position = None
        self.escape_trajectory = []
        self.current_maneuver = None
        
    def detect_enemy_lock(self, enemy_data: Dict) -> bool:
        """
        Detect if enemy UAV has locked onto us
        
        Args:
            enemy_data: Dictionary containing enemy UAV information
            
        Returns:
            True if enemy lock detected
        """
        if not enemy_data:
            return False
            
        # Check if enemy is in attack position
        enemy_pos = np.array(enemy_data.get('position', [0, 0, 0]))
        our_pos = np.array(enemy_data.get('our_position', [0, 0, 0]))
        
        # Calculate distance and angle
        distance = np.linalg.norm(enemy_pos - our_pos)
        
        # Get enemy's facing direction if available
        enemy_direction = enemy_data.get('direction')
        
        # Determine if we're being targeted based on:
        # 1. Distance is within attack range
        # 2. Enemy is facing us
        # 3. Enemy altitude is higher (advantage position)
        is_in_range = distance < self.safe_distance * 2.0  # Increased detection range
        is_above = enemy_pos[2] > our_pos[2]
        
        # If enemy direction is available, check if they're facing us
        if enemy_direction is not None:
            to_us = our_pos - enemy_pos
            angle = np.arccos(np.dot(enemy_direction, to_us) / 
                            (np.linalg.norm(enemy_direction) * np.linalg.norm(to_us)))
            is_facing_us = abs(angle) < np.pi/3  # Increased angle threshold to 60 degrees
        else:
            is_facing_us = True
            
        # Make detection more sensitive
        return (is_in_range and is_above) or (is_in_range and is_facing_us)
        
    def calculate_escape_vector(self, our_position: np.ndarray, 
                              enemy_position: np.ndarray) -> np.ndarray:
        """Calculate optimal escape vector"""
        # Get direction away from enemy
        direction = our_position - enemy_position
        distance = np.linalg.norm(direction)
        
        if distance > 0:
            # Normalize direction
            direction = direction / distance
            
            # Add stronger evasive maneuver
            perp = np.array([-direction[1], direction[0], 0])
            if not hasattr(self, 'last_perp') or np.random.random() < 0.1:
                self.last_perp = 1 if np.random.random() < 0.5 else -1
            
            # Add perpendicular component for more aggressive evasion
            direction = 0.6 * direction + 0.4 * (self.last_perp * perp)
            
            # Add vertical component based on current altitude
            if our_position[2] < self.min_altitude:
                direction[2] = 0.4  # Stronger upward movement
            elif our_position[2] > self.max_altitude:
                direction[2] = -0.4
            else:
                # Add oscillating vertical movement
                direction[2] = 0.2 * np.sin(time.time() * 2)
                
            # Normalize final vector
            direction = direction / np.linalg.norm(direction)
            
            # Apply higher escape speed
            return direction * (self.escape_speed * 1.5)
            
        return np.zeros(3)
        
    def update(self, enemy_data: Dict, our_position: Tuple[float, float, float],
               our_velocity: Tuple[float, float, float], 
               frame: Optional[np.ndarray] = None) -> Tuple[Dict, Optional[np.ndarray]]:
        """
        Update escape controller state and generate commands
        
        Args:
            enemy_data: Dictionary containing enemy UAV data
            our_position: Current UAV position (x,y,z)
            our_velocity: Current UAV velocity (vx,vy,vz)
            frame: Optional video frame for visualization
            
        Returns:
            Tuple of (command dict, annotated frame)
        """
        our_pos = np.array(our_position)
        enemy_pos = np.array(enemy_data.get('position', [0, 0, 0]))
        
        # Check for enemy lock
        enemy_lock = self.detect_enemy_lock(enemy_data)
        
        # Initialize commands
        commands = {
            'escape': False,
            'vector': np.zeros(3),
            'message': 'Monitoring'
        }
        
        if enemy_lock:
            if not self.is_escaping:
                self.is_escaping = True
                self.escape_start_time = time.time()
                self.escape_trajectory = []  # Reset trajectory on new escape
            
            # Calculate escape vector
            escape_vector = self.calculate_escape_vector(our_pos, enemy_pos)
            
            # Update commands
            commands.update({
                'escape': True,
                'vector': escape_vector,
                'message': 'Executing escape maneuver'
            })
            
            # Store trajectory point (only x,y coordinates)
            self.escape_trajectory.append([int(our_position[0]), int(our_position[1])])
            
            # Keep only last 50 points
            if len(self.escape_trajectory) > 50:
                self.escape_trajectory.pop(0)
            
        else:
            # Reset escape state if we're safe
            self.is_escaping = False
            self.escape_start_time = None
            self.escape_trajectory = []
            
        # Visualize if frame provided
        if frame is not None:
            # Draw enemy position
            cv2.circle(frame, (int(enemy_pos[0]), int(enemy_pos[1])), 
                      8, (0, 0, 255), -1)
            
            # Draw escape trajectory
            if len(self.escape_trajectory) > 1:
                points = np.array(self.escape_trajectory, dtype=np.int32)
                cv2.polylines(frame, [points], False, (255, 0, 0), 2)
            
            # Add status text
            cv2.putText(frame, f"Status: {commands['message']}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if enemy_lock:
                cv2.putText(frame, "WARNING: ENEMY LOCK DETECTED", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
        return commands, frame
        
    def reset(self):
        """Reset escape controller state"""
        self.is_escaping = False
        self.escape_start_time = None
        self.last_enemy_position = None
        self.escape_trajectory = []
        self.current_maneuver = None 