import cv2
import numpy as np
import time
from typing import Tuple
from vision.mission.kamikaze_controller import KamikazeController

def create_visualization_frame():
    # Create a larger frame with white background
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    frame.fill(255)
    
    # Draw grid lines
    for i in range(0, 800, 50):
        cv2.line(frame, (i, 0), (i, 800), (200, 200, 200), 1)
        cv2.line(frame, (0, i), (800, i), (200, 200, 200), 1)
    
    return frame

def create_qr_frame(frame, target_pos):
    # Draw QR code area
    qr_size = 30
    x, y = int(target_pos[0]), int(target_pos[1])
    cv2.rectangle(frame, 
                 (x - qr_size, y - qr_size),
                 (x + qr_size, y + qr_size),
                 (0, 0, 255), 2)
    
    # Draw QR code pattern
    inner_size = 20
    cv2.rectangle(frame,
                 (x - inner_size, y - inner_size),
                 (x + inner_size, y + inner_size),
                 (0, 0, 255), -1)
    
    # Add simulated QR code text
    cv2.putText(frame, "QR", (x - 15, y + 7),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return frame

def main():
    # Initialize kamikaze controller
    controller = KamikazeController(
        min_altitude=50.0,      # Minimum safe altitude
        dive_angle=30.0,        # Dive angle
        approach_speed=2.0,     # Base approach speed
        qr_size=2.5
    )
    
    # Initial positions
    our_position = [400.0, 500.0, 100.0]  # Starting position
    our_velocity = [0.0, 0.0, 0.0]
    target_position = [400.0, 300.0, 0.0]  # QR code on ground
    
    # Store trajectory points
    trajectory = []
    
    print("Kamikaze Attack Test Starting...")
    print("Press 'q' to quit, 'r' to reset")
    
    t = 0
    while True:
        # Create visualization frame
        frame = create_visualization_frame()
        
        # Add QR code to frame
        frame = create_qr_frame(frame, (target_position[0], target_position[1]))
        
        # Update target data
        target_data = {
            'position': target_position
        }
        
        # Update kamikaze controller
        commands, frame = controller.update(
            target_data, 
            tuple(our_position),
            tuple(our_velocity),
            frame
        )
        
        # Update our position based on attack vector
        if commands['attack'] and commands['vector'] is not None:
            vector = commands['vector']
            movement_scale = 5.0  # Movement speed
            
            # Print debug info
            print(f"Vector: {vector}, Position: {our_position}, Status: {commands['message']}")
            
            # Store current position for trajectory
            trajectory.append((int(our_position[0]), int(our_position[1])))
            
            # Apply movement vector directly
            new_position = [
                our_position[0] + vector[0] * movement_scale,
                our_position[1] + vector[1] * movement_scale,
                max(0, our_position[2] + vector[2] * movement_scale)  # Prevent negative altitude
            ]
            our_position = new_position
            
            # Update velocity
            our_velocity = [
                vector[0] * movement_scale,
                vector[1] * movement_scale,
                vector[2] * movement_scale
            ]
            
            # Draw trajectory
            if len(trajectory) > 1:
                for i in range(1, len(trajectory)):
                    cv2.line(frame, trajectory[i-1], trajectory[i], (255, 0, 0), 2)
            
            # Draw current position
            cv2.circle(frame, (int(our_position[0]), int(our_position[1])), 8, (0, 255, 0), -1)
            
            # Draw target
            cv2.circle(frame, (int(target_position[0]), int(target_position[1])), 8, (0, 0, 255), -1)
            
            # Draw movement vector
            cv2.line(frame, 
                    (int(our_position[0]), int(our_position[1])),
                    (int(our_position[0] + vector[0]*50), int(our_position[1] + vector[1]*50)),
                    (0, 255, 255), 2)
            
            # Add text info
            cv2.putText(frame, f"Alt: {our_position[2]:.1f}m", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(frame, f"Dist: {commands['distance']:.1f}m", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(frame, f"Status: {commands['message']}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            if commands['qr_data']:
                cv2.putText(frame, f"QR Read: {commands['qr_data']}", (10, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Show frame
            cv2.imshow('Kamikaze Test', frame)
            
            # Check for quit
            key = cv2.waitKey(50) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                our_position = [400.0, 500.0, 100.0]
                our_velocity = [0.0, 0.0, 0.0]
                trajectory = []
                controller.reset()
                
    cv2.destroyAllWindows()
    print("\nTest completed!")

if __name__ == "__main__":
    main() 