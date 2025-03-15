import cv2
import numpy as np
import qrcode
from detection.qr.qr_detector import QRDetector
from detection.qr.qr_processor import QRProcessor, QRCommand
import time

def create_test_qr_image(command_type: QRCommand, parameters: dict = None) -> np.ndarray:
    """Create a test QR code image"""
    # Create QR code data
    qr_data = QRProcessor.create_qr_command(command_type, parameters)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to numpy array
    qr_array = np.array(qr_image.convert('RGB'))
    return cv2.cvtColor(qr_array, cv2.COLOR_RGB2BGR)

def apply_perspective_transform(image: np.ndarray, tilt: float = 0, skew: float = 0) -> np.ndarray:
    """Apply perspective transform to simulate tilt and skew"""
    h, w = image.shape[:2]
    
    # Create source points
    src_points = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    
    # Calculate destination points with tilt and skew
    tilt_offset = int(h * np.sin(np.radians(tilt)))
    skew_offset = int(w * np.sin(np.radians(skew)))
    
    dst_points = np.float32([
        [skew_offset, tilt_offset],  # Top-left
        [w - skew_offset, tilt_offset],  # Top-right
        [w, h],  # Bottom-right
        [0, h]   # Bottom-left
    ])
    
    # Get perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    transformed = cv2.warpPerspective(image, M, (w, h))
    
    return transformed

def create_test_frame(qr_image: np.ndarray, angle: float = 0, tilt: float = 0, 
                     skew: float = 0, scale: float = 1.0) -> np.ndarray:
    """Create a test frame with rotated, tilted and skewed QR code"""
    # Create blank frame
    frame = np.ones((720, 1280, 3), dtype=np.uint8) * 255
    
    # Get QR code dimensions
    h, w = qr_image.shape[:2]
    
    # Apply rotation
    M_rot = cv2.getRotationMatrix2D((w/2, h/2), angle, scale)
    rotated_qr = cv2.warpAffine(qr_image, M_rot, (w, h))
    
    # Apply perspective transform for tilt and skew
    transformed_qr = apply_perspective_transform(rotated_qr, tilt, skew)
    
    # Calculate center for placement
    center_x = frame.shape[1] // 2
    center_y = frame.shape[0] // 2
    
    # Calculate placement coordinates
    x1 = center_x - w//2
    y1 = center_y - h//2
    x2 = x1 + w
    y2 = y1 + h
    
    # Ensure coordinates are within frame bounds
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(frame.shape[1], x2)
    y2 = min(frame.shape[0], y2)
    
    # Place QR code in frame
    try:
        frame[y1:y2, x1:x2] = transformed_qr[:y2-y1, :x2-x1]
    except ValueError:
        print("Warning: QR code placement failed due to size mismatch")
    
    return frame

def main():
    # Initialize QR detector
    detector = QRDetector(debug_mode=True)
    
    # Create test QR codes
    test_commands = [
        (QRCommand.KAMIKAZE, {'target_id': 'UAV_001'}),
        (QRCommand.LOCK, {'target_id': 'UAV_002'}),
        (QRCommand.ESCAPE, {'direction': 'NORTH'})
    ]
    
    # Test parameters
    angles = [0, 30, 45, 60, 90]  # Rotation angles
    tilts = [0, 15, 30, 45]      # Tilt angles
    skews = [0, 15, 30, 45]      # Skew angles
    
    print("QR Code Detection Test Starting...")
    print("Controls:")
    print("  'q' - Quit")
    print("  'n' - Next test")
    print("  'r' - Change rotation")
    print("  't' - Change tilt")
    print("  's' - Change skew")
    
    current_command = 0
    current_angle = 0
    current_tilt = 0
    current_skew = 0
    
    while True:
        # Get current test parameters
        command_type, parameters = test_commands[current_command]
        angle = angles[current_angle]
        tilt = tilts[current_tilt]
        skew = skews[current_skew]
        
        # Create test frame
        qr_image = create_test_qr_image(command_type, parameters)
        frame = create_test_frame(qr_image, angle=angle, tilt=tilt, skew=skew)
        
        # Detect QR codes
        processed_frame, detections = detector.detect(frame)
        
        # Add test information
        info_text = [
            f"Command: {command_type.value}",
            f"Rotation: {angle}°",
            f"Tilt: {tilt}°",
            f"Skew: {skew}°",
            f"Detections: {len(detections)}"
        ]
        
        for i, text in enumerate(info_text):
            cv2.putText(processed_frame, text,
                       (10, processed_frame.shape[0] - 150 + (i * 30)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Show frame
        cv2.imshow('QR Code Test', processed_frame)
        
        # Handle key events
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            # Next command
            current_command = (current_command + 1) % len(test_commands)
            print(f"\nTesting command: {test_commands[current_command][0].value}")
        elif key == ord('r'):
            # Change rotation
            current_angle = (current_angle + 1) % len(angles)
            print(f"Rotation: {angles[current_angle]}°")
        elif key == ord('t'):
            # Change tilt
            current_tilt = (current_tilt + 1) % len(tilts)
            print(f"Tilt: {tilts[current_tilt]}°")
        elif key == ord('s'):
            # Change skew
            current_skew = (current_skew + 1) % len(skews)
            print(f"Skew: {skews[current_skew]}°")
        
        time.sleep(0.1)  # Slow down the loop
    
    cv2.destroyAllWindows()
    print("\nTest completed!")

if __name__ == "__main__":
    main() 