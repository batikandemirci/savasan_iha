from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict

class YOLODetector:
    """
    YOLOv11 based object detector for UAV detection
    """
    def __init__(self, model_path: str = "yolo11_egitilmis.pt", conf_threshold: float = 0.15):
        """
        Initialize YOLO detector
        
        Args:
            model_path: Path to the YOLO model weights
            conf_threshold: Confidence threshold for detections (lowered to 0.15)
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, frame: np.ndarray, classes: List[int] = None) -> Tuple[np.ndarray, List[Dict]]:
        """Detect objects in frame"""
        # Create a clean copy of the frame for drawing
        draw_frame = frame.copy()
        
        # Ensure frame is in correct format
        if len(frame.shape) == 2:  # If grayscale
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            draw_frame = frame.copy()
            
        # Add NMS parameters for better detection
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            classes=classes,
            iou=0.3,  # Lower IOU threshold for NMS
            max_det=1,  # Only detect one object
            verbose=False
        )
        
        detections = []
        for result in results:
            boxes = result.boxes
            if len(boxes) > 0:
                # Get the highest confidence detection
                box = boxes[0]
                bbox = box.xyxy[0].cpu().numpy()
                detection = {
                    'bbox': bbox,
                    'confidence': float(box.conf),
                    'class_id': int(box.cls),
                    'class_name': result.names[int(box.cls)],
                    'centroid': self._get_bbox_centroid(bbox)
                }
                detections.append(detection)
                
                # Draw bounding box (3 pixel width as per rules)
                cv2.rectangle(draw_frame, 
                            (int(bbox[0]), int(bbox[1])),
                            (int(bbox[2]), int(bbox[3])), 
                            (0, 255, 0), 3)
                
                # Add label
                label = f"{detection['class_name']} {detection['confidence']:.2f}"
                cv2.putText(draw_frame, label,
                           (int(bbox[0]), int(bbox[1] - 10)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Draw centroid
                centroid = detection['centroid']
                cv2.circle(draw_frame, (int(centroid[0]), int(centroid[1])), 4, (0, 0, 255), -1)
        
        return draw_frame, detections
    
    def _get_bbox_centroid(self, bbox: np.ndarray) -> Tuple[float, float]:
        """Calculate centroid of bounding box"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2) 