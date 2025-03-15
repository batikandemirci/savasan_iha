import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
import time

class TargetLockSystem:
    """
    Target locking system implementing competition rules
    """
    def __init__(self, 
                 frame_width: int = 1280,
                 frame_height: int = 720,
                 required_lock_time: float = 5.0,  # Changed to 5 seconds as per competition rules
                 total_lock_window: float = 5.0,
                 lock_box_coverage: float = 0.70):  # Reduced coverage requirement to 70%
        """
        Initialize target locking system
        
        Args:
            frame_width: Width of input frames
            frame_height: Height of input frames
            required_lock_time: Required continuous lock duration (5 seconds)
            total_lock_window: Total time window for locking (5 seconds)
            lock_box_coverage: Required target coverage inside lock box (70%)
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.required_lock_time = required_lock_time
        self.total_lock_window = total_lock_window
        self.lock_box_coverage = lock_box_coverage
        self.lock_tolerance = 0.20  # Increased tolerance to 20%
        
        # Define competition zones
        self._setup_competition_zones()
        
        # Tracking state with hysteresis
        self.current_target_id = None
        self.lock_start_time = None
        self.window_start_time = None
        self.is_locked = False
        self.lock_duration = 0.0
        self.lock_duration_elapsed = 0.0
        self.last_locked_target = None
        self.server_time = 0
        self.lock_hysteresis = 0  # Counter for lock stability
        
        # UAV tracking
        self.uav_counter = 0  # Counter for generating unique IDs
        self.tracked_uavs = {}  # Dictionary to store UAV tracking history
        
    def _setup_competition_zones(self):
        """Setup competition-specific targeting zones"""
        # Camera view area (AK) is full frame
        self.camera_view = {
            'x1': 0,
            'y1': 0,
            'x2': self.frame_width,
            'y2': self.frame_height
        }
        
        # Target hit area (AV) - Yellow rectangle
        # 25% margin from left/right, 10% from top/bottom
        margin_x = int(0.25 * self.frame_width)
        margin_y = int(0.10 * self.frame_height)
        self.target_hit_area = {
            'x1': margin_x,
            'y1': margin_y,
            'x2': self.frame_width - margin_x,
            'y2': self.frame_height - margin_y
        }
        
        # Lock rectangle (AH) - Red rectangle
        # ≥5% margins within target hit area
        lock_margin_x = int(0.05 * self.frame_width)
        lock_margin_y = int(0.05 * self.frame_height)
        self.lock_zone = {
            'x1': self.target_hit_area['x1'] + lock_margin_x,
            'y1': self.target_hit_area['y1'] + lock_margin_y,
            'x2': self.target_hit_area['x2'] - lock_margin_x,
            'y2': self.target_hit_area['y2'] - lock_margin_y
        }
    
    def is_point_in_lock_zone(self, point: Tuple[float, float]) -> bool:
        """Check if point is within the lock zone"""
        x, y = point
        return (self.lock_zone['x1'] < x < self.lock_zone['x2'] and
                self.lock_zone['y1'] < y < self.lock_zone['y2'])
    
    def is_point_in_target_area(self, point: Tuple[float, float]) -> bool:
        """Check if point is within the target hit area"""
        x, y = point
        # Add small tolerance (1% of frame size)
        tolerance_x = self.frame_width * 0.01
        tolerance_y = self.frame_height * 0.01
        
        return (self.target_hit_area['x1'] - tolerance_x <= x <= self.target_hit_area['x2'] + tolerance_x and
                self.target_hit_area['y1'] - tolerance_y <= y <= self.target_hit_area['y2'] + tolerance_y)
    
    def is_bbox_in_target_area(self, bbox: np.ndarray) -> bool:
        """Check if bounding box overlaps significantly with target area"""
        # Calculate overlap area
        x1 = max(bbox[0], self.target_hit_area['x1'])
        y1 = max(bbox[1], self.target_hit_area['y1'])
        x2 = min(bbox[2], self.target_hit_area['x2'])
        y2 = min(bbox[3], self.target_hit_area['y2'])
        
        if x2 <= x1 or y2 <= y1:
            return False
            
        overlap_area = (x2 - x1) * (y2 - y1)
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        target_area = (self.target_hit_area['x2'] - self.target_hit_area['x1']) * (self.target_hit_area['y2'] - self.target_hit_area['y1'])
        
        # Calculate both relative to bbox and target area
        bbox_overlap_ratio = overlap_area / bbox_area
        target_overlap_ratio = overlap_area / target_area
        
        # Return true if either ratio is significant
        return bbox_overlap_ratio >= 0.3 or target_overlap_ratio >= 0.01
    
    def _calculate_coverage(self, target_bbox: np.ndarray, lock_box: dict) -> float:
        """Calculate what percentage of target is inside lock box"""
        # Calculate intersection
        x1 = max(target_bbox[0], lock_box['x1'])
        y1 = max(target_bbox[1], lock_box['y1'])
        x2 = min(target_bbox[2], lock_box['x2'])
        y2 = min(target_bbox[3], lock_box['y2'])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
            
        intersection_area = (x2 - x1) * (y2 - y1)
        target_area = (target_bbox[2] - target_bbox[0]) * (target_bbox[3] - target_bbox[1])
        
        return intersection_area / target_area if target_area > 0 else 0.0
        
    def is_target_in_area(self, bbox):
        """Check if target is in area with increased tolerance"""
        x1, y1, x2, y2 = bbox
        
        # Target area with 15% tolerance
        area_x1 = self.target_hit_area['x1'] - self.frame_width * self.lock_tolerance
        area_y1 = self.target_hit_area['y1'] - self.frame_height * self.lock_tolerance
        area_x2 = self.target_hit_area['x2'] + self.frame_width * self.lock_tolerance
        area_y2 = self.target_hit_area['y2'] + self.frame_height * self.lock_tolerance
        
        # Check if any part of the bbox overlaps with target area
        return not (x2 < area_x1 or x1 > area_x2 or y2 < area_y1 or y1 > area_y2)
    
    def update(self, tracked_objects, frame):
        """Update target lock status with hysteresis"""
        self.frame = frame.copy()
        
        # Draw target area first (yellow)
        cv2.rectangle(self.frame, 
                     (int(self.target_hit_area['x1']), int(self.target_hit_area['y1'])),
                     (int(self.target_hit_area['x2']), int(self.target_hit_area['y2'])), 
                     (0, 255, 255), 2)
        
        # Draw lock zone (red/green based on lock status)
        color = (0, 255, 0) if self.is_locked else (0, 0, 255)
        cv2.rectangle(self.frame, 
                     (int(self.lock_zone['x1']), int(self.lock_zone['y1'])),
                     (int(self.lock_zone['x2']), int(self.lock_zone['y2'])), 
                     color, 2)
        
        if not tracked_objects:
            self.lock_hysteresis = max(self.lock_hysteresis - 1, -3)
            if self.lock_hysteresis <= -3:
                self.reset_lock()
            return self.frame, self._get_lock_status()
        
        # Get the first (and only) tracked object
        obj_id = list(tracked_objects.keys())[0]
        obj = tracked_objects[obj_id]
        bbox = obj['bbox']
        conf = obj['confidence']
        centroid = obj['centroid']
        
        # Assign or get UAV ID
        if obj_id not in self.tracked_uavs:
            self.uav_counter += 1
            self.tracked_uavs[obj_id] = {
                'uav_id': f"UAV_{self.uav_counter:03d}",
                'first_seen': time.time(),
                'total_tracked_frames': 0,
                'total_lock_time': 0.0
            }
        
        uav_id = self.tracked_uavs[obj_id]['uav_id']
        self.tracked_uavs[obj_id]['total_tracked_frames'] += 1
        
        # Check target position
        in_lock_zone = self.is_point_in_lock_zone(centroid)
        in_target_area = self.is_target_in_area(bbox)
        
        # Draw bbox with color based on status
        if in_lock_zone:
            color = (0, 255, 0)  # Green for in lock zone
        elif in_target_area:
            color = (0, 255, 255)  # Yellow for in target area
        else:
            color = (0, 0, 255)  # Red for outside
        
        cv2.rectangle(self.frame, 
                     (int(bbox[0]), int(bbox[1])), 
                     (int(bbox[2]), int(bbox[3])), 
                     color, 2)
        
        # Update lock status
        if in_lock_zone:
            self.lock_hysteresis = min(self.lock_hysteresis + 1, 5)
            if self.lock_hysteresis >= 2:
                if not self.lock_start_time:
                    self.lock_start_time = time.time()
                    self.current_target_id = obj_id
                
                self.lock_duration = time.time() - self.lock_start_time
                self.is_locked = self.lock_duration >= self.required_lock_time
                self.lock_duration_elapsed = self.lock_duration
                
                if self.is_locked:
                    self.tracked_uavs[obj_id]['total_lock_time'] = self.lock_duration
        else:
            self.lock_hysteresis = max(self.lock_hysteresis - 1, -3)
            if self.lock_hysteresis <= -3:
                self.reset_lock()
        
        # Add status label with UAV ID
        status = "LOCKED" if self.is_locked else "TRACKING"
        label = f"{uav_id} | {status} {conf:.2f}"
        cv2.putText(self.frame, label,
                   (int(bbox[0]), int(bbox[1])-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Add debug info
        cv2.putText(self.frame, f"Objects: {len(tracked_objects)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(self.frame, f"Current UAV: {uav_id}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(self.frame, f"Lock time: {self.lock_duration:.1f}s", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(self.frame, f"Locked: {self.is_locked}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(self.frame, f"Total Tracked: {self.tracked_uavs[obj_id]['total_tracked_frames']}", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        if self.is_locked:
            lock_text = f"LOCKED ON {uav_id}"
            cv2.putText(self.frame, lock_text, 
                       (int(self.frame_width/2 - 200), int(self.frame_height - 50)),
                       cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 0), 3)
        
        return self.frame, self._get_lock_status()
    
    def reset_lock(self):
        """Reset all locking parameters"""
        self.current_target_id = None
        self.lock_start_time = None
        self.window_start_time = None
        self.is_locked = False
        self.lock_duration = 0.0
        self.lock_duration_elapsed = 0.0
    
    def _get_lock_status(self) -> Dict:
        """Get current lock status"""
        current_uav_id = None
        if self.current_target_id and self.current_target_id in self.tracked_uavs:
            current_uav_id = self.tracked_uavs[self.current_target_id]['uav_id']
            
        return {
            'is_locked': self.is_locked,
            'target_id': self.current_target_id,
            'uav_id': current_uav_id,
            'lock_duration': self.lock_duration_elapsed,
            'window_start_time': self.window_start_time,
            'server_time': self.server_time,
            'lock_zone': self.lock_zone,
            'target_hit_area': self.target_hit_area,
            'last_locked_target': self.last_locked_target,
            'total_tracked_uavs': len(self.tracked_uavs)
        }
    
    def _draw_status_box(self, frame: np.ndarray, text: str, color: Tuple[int, int, int]):
        """Draw a status box with text"""
        # Calculate text size and position
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        
        # Draw background box
        margin = 10
        box_x = 20
        box_y = 40
        box_width = text_size[0] + 2 * margin
        box_height = text_size[1] + 2 * margin
        
        cv2.rectangle(frame,
                     (box_x, box_y),
                     (box_x + box_width, box_y + box_height),
                     color, -1)  # Filled rectangle
        
        # Draw text
        text_x = box_x + margin
        text_y = box_y + text_size[1] + margin - 5
        cv2.putText(frame, text,
                   (text_x, text_y),
                   font, font_scale,
                   (255, 255, 255),  # White text
                   thickness)
    
    def set_server_time(self, server_time: float):
        """Update server time (to be synchronized with competition server)"""
        self.server_time = server_time 