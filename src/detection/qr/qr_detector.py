import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import time
from pyzbar.pyzbar import decode
from pyzbar import pyzbar

class QRDetector:
    """
    Enhanced QR code detection and decoding system with support for angled/skewed codes
    """
    def __init__(self, 
                 min_confidence: float = 0.7,
                 debug_mode: bool = False):
        """
        Initialize QR detector
        
        Args:
            min_confidence: Minimum confidence for QR detection
            debug_mode: Enable debug visualization
        """
        self.min_confidence = min_confidence
        self.debug_mode = debug_mode
        
        # Statistics
        self.total_detections = 0
        self.successful_decodes = 0
        self.last_detection_time = None
        self.detection_history = []
        
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for better QR detection
        
        Args:
            frame: Input frame
            
        Returns:
            Preprocessed frame
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # Apply morphological operations to reduce noise
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return thresh
        
    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """
        Detect and decode QR codes in frame with enhanced angle support
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (processed frame, list of QR detections)
        """
        # Create a copy for drawing
        draw_frame = frame.copy()
        
        # Preprocess frame
        processed = self.preprocess_frame(frame)
        
        # Detect QR codes using pyzbar
        qr_codes = decode(processed)
        
        detections = []
        for qr in qr_codes:
            self.total_detections += 1
            self.last_detection_time = time.time()
            
            if qr.data:  # If successfully decoded
                self.successful_decodes += 1
                
                # Get QR code points
                points = np.array(qr.polygon, np.int32)
                points = points.reshape((-1, 1, 2))
                
                # Calculate center point
                center = np.mean(points, axis=0).astype(int)[0]
                
                # Get rotation angle
                rect = cv2.minAreaRect(points)
                angle = rect[-1]
                
                # Create detection info
                detection = {
                    'data': qr.data.decode('utf-8'),
                    'points': points,
                    'center': center,
                    'angle': angle,
                    'timestamp': self.last_detection_time,
                    'quality': qr.quality
                }
                detections.append(detection)
                
                # Draw QR code boundary and data
                cv2.polylines(draw_frame, [points], True, (0, 255, 0), 2)
                
                # Draw orientation indicator
                cv2.line(draw_frame, 
                        tuple(points[0][0]),
                        tuple(points[1][0]),
                        (0, 0, 255), 3)
                
                # Draw data with background for better visibility
                text = detection['data']
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                
                # Get text size
                (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                
                # Draw background rectangle
                text_x = center[0] - text_width // 2
                text_y = center[1] - text_height // 2
                cv2.rectangle(draw_frame,
                            (text_x - 5, text_y - text_height - 5),
                            (text_x + text_width + 5, text_y + 5),
                            (0, 0, 0), -1)
                
                # Draw text
                cv2.putText(draw_frame, text,
                          (text_x, text_y),
                          font, font_scale, (0, 255, 0), thickness)
                
                # Add angle information
                angle_text = f"Angle: {angle:.1f}°"
                cv2.putText(draw_frame, angle_text,
                          (text_x, text_y + 25),
                          font, 0.5, (0, 255, 0), 1)
                
                # Add to history
                self.detection_history.append(detection)
                
                # Keep only last 100 detections
                if len(self.detection_history) > 100:
                    self.detection_history.pop(0)
        
        # Add debug info if enabled
        if self.debug_mode:
            debug_info = [
                f"QR Detections: {self.total_detections}",
                f"Successful Decodes: {self.successful_decodes}",
                f"Active QRs: {len(detections)}"
            ]
            
            for i, text in enumerate(debug_info):
                cv2.putText(draw_frame, text,
                           (10, 30 + (i * 30)),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.7, (0, 255, 0), 2)
        
        return draw_frame, detections
    
    def get_stats(self) -> Dict:
        """Get detection statistics"""
        return {
            'total_detections': self.total_detections,
            'successful_decodes': self.successful_decodes,
            'last_detection_time': self.last_detection_time,
            'detection_history': self.detection_history
        } 