import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
import time
from dataclasses import dataclass
from enum import Enum

class ZoneType(Enum):
    """Types of no-fly zones"""
    AIR_DEFENSE = "AIR_DEFENSE"      # Hava savunma sistemi
    SIGNAL_JAMMING = "SIGNAL_JAMMING"  # Sinyal karıştırma bölgesi

@dataclass
class NoFlyZone:
    """No-fly zone data container"""
    zone_id: str
    zone_type: ZoneType
    center: Tuple[float, float, float]  # x, y, z coordinates
    radius: float
    activation_time: float
    is_active: bool = False
    total_violation_time: float = 0.0
    last_violation_check: Optional[float] = None

class NoFlyZoneController:
    """
    Controller for managing no-fly zones and calculating avoidance vectors
    according to TEKNOFEST specifications
    """
    def __init__(self,
                 penalty_points_per_second: float = 5.0,
                 max_violation_time: float = 30.0,
                 safety_margin: float = 3.0):  # Reduced from 5.0 to 3.0
        """
        Initialize no-fly zone controller
        
        Args:
            penalty_points_per_second: Penalty points per second in no-fly zone
            max_violation_time: Maximum allowed time in no-fly zones (seconds)
            safety_margin: Additional safety margin around zones (meters)
        """
        self.zones: Dict[str, NoFlyZone] = {}
        self.penalty_points_per_second = penalty_points_per_second
        self.max_violation_time = max_violation_time
        self.safety_margin = safety_margin
        
        # Statistics
        self.total_penalty_points = 0.0
        self.current_violations = set()  # Currently violated zones
        self.violation_history = []
        
    def add_zone(self, 
                 zone_id: str,
                 zone_type: ZoneType,
                 center: Tuple[float, float, float],
                 radius: float) -> NoFlyZone:
        """
        Add a new no-fly zone
        
        Args:
            zone_id: Unique zone identifier
            zone_type: Type of no-fly zone
            center: Zone center coordinates (x,y,z)
            radius: Zone radius in meters
            
        Returns:
            Created NoFlyZone object
        """
        zone = NoFlyZone(
            zone_id=zone_id,
            zone_type=zone_type,
            center=center,
            radius=radius,
            activation_time=time.time()
        )
        self.zones[zone_id] = zone
        return zone
    
    def activate_zone(self, zone_id: str):
        """Activate a no-fly zone"""
        if zone_id in self.zones:
            self.zones[zone_id].is_active = True
            self.zones[zone_id].activation_time = time.time()
    
    def deactivate_zone(self, zone_id: str):
        """Deactivate a no-fly zone"""
        if zone_id in self.zones:
            self.zones[zone_id].is_active = False
    
    def is_point_in_zone(self, point: np.ndarray, zone: NoFlyZone) -> bool:
        # Calculate 2D distance using only x,y coordinates
        distance = np.sqrt((point[0] - zone.center[0])**2 + (point[1] - zone.center[1])**2)
        
        # Check if point is within zone radius
        is_in_zone = distance <= zone.radius
        
        print(f"\nDetailed zone check for {zone.zone_id}:")
        print(f"Point coordinates: ({point[0]:.1f}, {point[1]:.1f})")
        print(f"Zone center: ({zone.center[0]:.1f}, {zone.center[1]:.1f})")
        print(f"Distance: {distance:.1f}")
        print(f"Zone radius: {zone.radius}")
        print(f"Is in zone: {is_in_zone}")
        
        return is_in_zone
    
    def calculate_avoidance_vector(self, 
                                 current_pos: Tuple[float, float, float],
                                 current_vel: Tuple[float, float, float],
                                 target_pos: Optional[Tuple[float, float, float]] = None
                                 ) -> Tuple[np.ndarray, List[str]]:
        """
        Calculate avoidance vector to stay clear of no-fly zones
        
        Args:
            current_pos: Current UAV position
            current_vel: Current UAV velocity
            target_pos: Optional target position to consider
            
        Returns:
            Tuple of (avoidance vector, list of violated zone IDs)
        """
        current_pos = np.array(current_pos)
        current_vel = np.array(current_vel)
        violated_zones = []
        
        # Initialize repulsive vector
        avoidance_vector = np.zeros(3)
        total_influence = 0.0
        
        for zone_id, zone in self.zones.items():
            if not zone.is_active:
                continue
                
            # Calculate distance and direction to zone center (2D only)
            to_center = np.array(zone.center) - current_pos
            to_center[2] = 0  # Ignore Z component for distance calculation
            distance = np.linalg.norm(to_center[:2])  # 2D distance
            
            # Extended safety range for early avoidance
            extended_range = zone.radius + self.safety_margin
            
            # Check if in potential violation range
            if distance <= extended_range:
                # Calculate repulsive force (stronger when closer)
                if distance > 0:
                    direction = -to_center / np.linalg.norm(to_center)  # Away from center
                    direction[2] = 0  # Keep movement in 2D plane
                    
                    # Linear repulsion force
                    strength = (1.0 - distance / extended_range)
                    
                    # No vertical boost - keep movement in 2D
                    avoidance_vector += direction * strength
                    total_influence += strength
                
                # Check for actual violation using 2D distance
                if distance <= zone.radius:
                    violated_zones.append(zone_id)
        
        # Normalize the avoidance vector if there were any influences
        if total_influence > 0:
            avoidance_vector = avoidance_vector / total_influence
            
        # If we have a target position and are in avoidance mode
        if target_pos is not None and np.any(avoidance_vector):
            target_pos = np.array(target_pos)
            to_target = target_pos - current_pos
            to_target[2] = 0  # Keep movement in 2D plane
            distance_to_target = np.linalg.norm(to_target[:2])
            
            if distance_to_target > 0:
                target_direction = to_target / np.linalg.norm(to_target)
                # Give even more weight to target direction
                avoidance_vector = 0.5 * avoidance_vector + 0.5 * target_direction  # Changed from 0.7/0.3 to 0.5/0.5
        
        # Normalize final vector
        magnitude = np.linalg.norm(avoidance_vector)
        if magnitude > 0:
            avoidance_vector = avoidance_vector / magnitude
        
        return avoidance_vector, violated_zones
    
    def update(self, current_pos: Tuple[float, float, float]) -> Dict:
        """
        Update zone violations and calculate penalties
        
        Args:
            current_pos: Current UAV position
            
        Returns:
            Dictionary with violation status and penalties
        """
        current_time = time.time()
        new_violations = set()
        
        # Check each active zone
        for zone_id, zone in self.zones.items():
            if not zone.is_active:
                continue
                
            if self.is_point_in_zone(current_pos, zone):
                new_violations.add(zone_id)
                
                # Initialize last_violation_check if this is a new violation
                if zone.last_violation_check is None:
                    zone.last_violation_check = current_time
                    print(f"New violation in zone {zone_id}")
                else:
                    # Calculate time since last check and update total violation time
                    time_delta = current_time - zone.last_violation_check
                    zone.total_violation_time += time_delta
                    self.total_penalty_points += time_delta * self.penalty_points_per_second
                    print(f"Zone {zone_id} violation continues - Total time: {zone.total_violation_time:.1f}s")
                
                # Update last violation check time
                zone.last_violation_check = current_time
            else:
                if zone.last_violation_check is not None:
                    print(f"Left zone {zone_id} - Total violation time: {zone.total_violation_time:.1f}s")
                # Reset last_violation_check when leaving the zone
                zone.last_violation_check = None
        
        # Update current violations
        self.current_violations = new_violations
        
        # Check for max violation time
        max_violation = max((zone.total_violation_time 
                           for zone in self.zones.values()), default=0.0)
        
        return {
            'in_violation': len(new_violations) > 0,
            'violated_zones': list(new_violations),
            'total_penalty_points': self.total_penalty_points,
            'max_violation_time': max_violation,
            'emergency_landing_required': max_violation >= self.max_violation_time
        }
    
    def visualize(self, frame: np.ndarray, 
                 camera_matrix: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Visualize no-fly zones on frame
        
        Args:
            frame: Video frame to draw on
            camera_matrix: Optional camera matrix for 3D->2D projection
            
        Returns:
            Annotated frame
        """
        for zone_id, zone in self.zones.items():
            if not zone.is_active:
                continue
                
            # If we have camera matrix, project 3D circle to 2D
            if camera_matrix is not None:
                # Project center point
                center_2d = camera_matrix @ np.array(zone.center)
                center_2d = center_2d[:2] / center_2d[2]
                center = tuple(map(int, center_2d))
                
                # Project radius (approximate)
                radius_px = int(zone.radius * camera_matrix[0,0] / zone.center[2])
            else:
                # Simple 2D visualization
                center = (int(zone.center[0]), int(zone.center[1]))
                radius_px = int(zone.radius)
            
            # Draw zone circle
            color = (0, 0, 255) if zone_id in self.current_violations else (0, 165, 255)
            cv2.circle(frame, center, radius_px, color, 2)
            
            # Add zone info
            cv2.putText(frame, f"{zone.zone_type.value}: {zone_id}",
                       (center[0] - 50, center[1] - radius_px - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Add violation time if applicable
            if zone.total_violation_time > 0:
                cv2.putText(frame,
                           f"Violation: {zone.total_violation_time:.1f}s",
                           (center[0] - 50, center[1] - radius_px - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def get_safe_corridors(self) -> List[Dict]:
        """
        Calculate safe corridors between no-fly zones
        
        Returns:
            List of corridor dictionaries with start/end points
        """
        # TODO: Implement path finding between zones
        # This will be used for finding optimal paths for target lock
        pass 