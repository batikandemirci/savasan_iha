import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from scipy.spatial import distance

class KalmanTracker:
    """
    Kalman Filter based multi-object tracker optimized for UAV tracking
    """
    def __init__(self, max_disappeared: int = 60, max_distance: float = 100.0):
        """
        Initialize tracker
        
        Args:
            max_disappeared: Maximum number of frames to keep track of disappeared object
            max_distance: Maximum distance between detections to consider it the same object
        """
        self.next_object_id = 0
        self.objects = {}  # Dictionary to store tracked objects {id: (centroid, kalman_filter)}
        self.disappeared = {}  # Dictionary to count frames since last detection
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.min_confidence = 0.1  # Lower confidence threshold
        
    def _create_kalman_filter(self) -> cv2.KalmanFilter:
        """Create and initialize Kalman Filter for new object"""
        kf = cv2.KalmanFilter(6, 2)  # 6 state variables (x,y,z,dx,dy,dz), 2 measurement variables (x,y)
        
        # Measurement matrix (converts state vector into measurement vector)
        kf.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0]], np.float32)
        
        # State transition matrix
        dt = 1/30.0  # Assuming 30 FPS
        kf.transitionMatrix = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]], np.float32)
        
        # Increased process noise for more dynamic tracking
        kf.processNoiseCov = 1e-3 * np.eye(6, dtype=np.float32)
        
        # Reduced measurement noise for more trust in measurements
        kf.measurementNoiseCov = 1e-4 * np.eye(2, dtype=np.float32)
        
        return kf
        
    def register(self, centroid: Tuple[float, float]):
        """Register new object with Kalman Filter"""
        kf = self._create_kalman_filter()
        self.objects[self.next_object_id] = (centroid, kf)
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
        
    def deregister(self, object_id: int):
        """Deregister disappeared object"""
        del self.objects[object_id]
        del self.disappeared[object_id]
        
    def update(self, detections: List[Dict]) -> Dict:
        """
        Update tracker with new detections
        
        Args:
            detections: List of detection dictionaries with bbox, confidence, etc.
            
        Returns:
            Dictionary of tracked objects with IDs as keys
        """
        tracked_objects = {}
        
        # Extract centroids from detections
        detection_list = []
        detection_centroids = []
        for det in detections:
            bbox = det['bbox']
            centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            detection_list.append({
                'centroid': centroid,
                'bbox': bbox,
                'confidence': det['confidence']
            })
            detection_centroids.append(centroid)
            
        # If no detections, mark all objects as disappeared
        if len(detection_list) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            # Return remaining objects with their predicted positions
            for obj_id, (centroid, kf) in self.objects.items():
                prediction = kf.predict()
                predicted_centroid = (prediction[0][0], prediction[1][0])
                tracked_objects[obj_id] = {
                    'centroid': predicted_centroid,
                    'bbox': [predicted_centroid[0]-50, predicted_centroid[1]-50,  # Estimated bbox
                            predicted_centroid[0]+50, predicted_centroid[1]+50],
                    'confidence': 0.5  # Lower confidence for predictions
                }
            return tracked_objects
            
        # If no existing objects, register all detections as new
        if len(self.objects) == 0:
            for i, det in enumerate(detection_list):
                self.register(det['centroid'])
                tracked_objects[i] = {
                    'centroid': det['centroid'],
                    'bbox': det['bbox'],
                    'confidence': det['confidence']
                }
        else:
            # Calculate distances between existing objects and new detections
            object_ids = list(self.objects.keys())
            object_centroids = [obj[0] for obj in self.objects.values()]
            
            # Convert lists to numpy arrays for distance calculation
            object_centroids = np.array(object_centroids)
            detection_centroids = np.array(detection_centroids)
            
            # Ensure 2D arrays
            if len(object_centroids.shape) == 1:
                object_centroids = object_centroids.reshape(1, -1)
            if len(detection_centroids.shape) == 1:
                detection_centroids = detection_centroids.reshape(1, -1)
            
            D = distance.cdist(object_centroids, detection_centroids)
            
            # Find best matches using Hungarian algorithm
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                    
                if D[row, col] > self.max_distance:
                    continue
                    
                object_id = object_ids[row]
                det = detection_list[col]
                centroid = det['centroid']
                kf = self.objects[object_id][1]
                
                # Update Kalman Filter
                prediction = kf.predict()
                measurement = np.array([[centroid[0]], [centroid[1]]], dtype=np.float32)
                kf.correct(measurement)
                
                # Update object position with Kalman Filter prediction
                predicted_centroid = (prediction[0][0], prediction[1][0])
                self.objects[object_id] = (predicted_centroid, kf)
                self.disappeared[object_id] = 0
                
                # Add to tracked objects
                tracked_objects[object_id] = {
                    'centroid': predicted_centroid,
                    'bbox': det['bbox'],
                    'confidence': det['confidence']
                }
                
                used_rows.add(row)
                used_cols.add(col)
            
            # Handle unmatched existing objects
            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
                else:
                    # Predict new position using Kalman Filter
                    kf = self.objects[object_id][1]
                    prediction = kf.predict()
                    predicted_centroid = (prediction[0][0], prediction[1][0])
                    self.objects[object_id] = (predicted_centroid, kf)
                    
                    # Add prediction to tracked objects
                    tracked_objects[object_id] = {
                        'centroid': predicted_centroid,
                        'bbox': [predicted_centroid[0]-50, predicted_centroid[1]-50,  # Estimated bbox
                                predicted_centroid[0]+50, predicted_centroid[1]+50],
                        'confidence': 0.5  # Lower confidence for predictions
                    }
            
            # Register unmatched detections as new objects
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)
            for col in unused_cols:
                det = detection_list[col]
                self.register(det['centroid'])
                new_id = self.next_object_id - 1  # ID of just registered object
                tracked_objects[new_id] = {
                    'centroid': det['centroid'],
                    'bbox': det['bbox'],
                    'confidence': det['confidence']
                }
        
        return tracked_objects 