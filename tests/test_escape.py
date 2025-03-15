import cv2
import numpy as np
import time
from vision.mission.escape_controller import EscapeController

def create_visualization_frame():
    """Create visualization frame with grid"""
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    frame.fill(255)
    
    # Draw grid lines
    for i in range(0, 800, 50):
        cv2.line(frame, (i, 0), (i, 800), (200, 200, 200), 1)
        cv2.line(frame, (0, i), (800, i), (200, 200, 200), 1)
    
    return frame

def simulate_enemy_movement(t: float, center_pos: tuple, our_position: tuple,
                          radius: float = 100.0, speed: float = 1.0) -> tuple:
    """Simulate aggressive enemy movement that pursues our UAV"""
    our_pos = np.array(our_position)
    center = np.array(center_pos)
    
    # Calculate base circular movement
    circular_x = center[0] + radius * np.cos(speed * t)
    circular_y = center[1] + radius * np.sin(speed * t)
    circular_z = center[2] + 10 * np.sin(speed * t / 2)
    circular_pos = np.array([circular_x, circular_y, circular_z])
    
    # Calculate direction to our UAV
    to_target = our_pos - circular_pos
    distance = np.linalg.norm(to_target)
    
    if distance > 0:
        # Combine circular movement with pursuit
        pursuit_weight = 0.7  # 70% pursuit, 30% circular
        final_pos = (1 - pursuit_weight) * circular_pos + pursuit_weight * (
            circular_pos + to_target / distance * min(distance, 50)
        )
        
        # Calculate movement direction
        direction = to_target / distance
        
        # Add some vertical oscillation
        final_pos[2] = center[2] + 20 * np.sin(speed * t / 2)
        
        return tuple(final_pos), direction
    
    return tuple(circular_pos), np.array([0, 0, 1])

def main():
    # Initialize escape controller with more aggressive settings
    controller = EscapeController(
        min_altitude=50.0,
        max_altitude=100.0,
        escape_speed=3.0,  # Increased escape speed
        safe_distance=40.0  # Increased safe distance
    )
    
    # Initial positions
    our_position = [400.0, 400.0, 70.0]  # Starting position
    our_velocity = [0.0, 0.0, 0.0]
    enemy_center = (400.0, 400.0, 90.0)  # Enemy movement center
    
    print("Escape Maneuver Test Starting...")
    print("Press 'q' to quit, 'r' to reset")
    
    t = 0
    while True:
        # Create visualization frame
        frame = create_visualization_frame()
        
        # Simulate enemy movement that pursues our UAV
        enemy_pos, enemy_dir = simulate_enemy_movement(t, enemy_center, our_position, 
                                                     speed=1.5)  # Increased speed
        
        # Update enemy data
        enemy_data = {
            'position': enemy_pos,
            'direction': enemy_dir,
            'our_position': our_position
        }
        
        # Update escape controller
        commands, frame = controller.update(
            enemy_data,
            tuple(our_position),
            tuple(our_velocity),
            frame
        )
        
        # Update our position based on escape vector
        if commands['escape']:
            vector = commands['vector']
            movement_scale = 5.0  # Movement speed
            
            # Print debug info
            print(f"Vector: {vector}, Position: {our_position}, Status: {commands['message']}")
            
            # Apply movement vector
            our_position = [
                our_position[0] + vector[0] * movement_scale,
                our_position[1] + vector[1] * movement_scale,
                max(0, our_position[2] + vector[2] * movement_scale)  # Prevent negative altitude
            ]
            
            # Update velocity
            our_velocity = [
                vector[0] * movement_scale,
                vector[1] * movement_scale,
                vector[2] * movement_scale
            ]
            
            # Draw escape vector
            start_point = (int(our_position[0]), int(our_position[1]))
            end_point = (int(our_position[0] + vector[0] * 50),
                        int(our_position[1] + vector[1] * 50))
            cv2.arrowedLine(frame, start_point, end_point, (255, 0, 0), 2)
        
        # Draw current positions
        cv2.circle(frame, (int(our_position[0]), int(our_position[1])), 
                  8, (0, 255, 0), -1)
        cv2.circle(frame, (int(enemy_pos[0]), int(enemy_pos[1])), 
                  8, (0, 0, 255), -1)
        
        # Draw enemy direction
        enemy_dir_point = (int(enemy_pos[0] + enemy_dir[0] * 30),
                          int(enemy_pos[1] + enemy_dir[1] * 30))
        cv2.arrowedLine(frame, 
                       (int(enemy_pos[0]), int(enemy_pos[1])),
                       enemy_dir_point,
                       (0, 0, 255), 2)
        
        # Add altitude and status info
        cv2.putText(frame, f"Our Alt: {our_position[2]:.1f}m", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(frame, f"Enemy Alt: {enemy_pos[2]:.1f}m", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(frame, f"Distance: {np.linalg.norm(np.array(enemy_pos) - np.array(our_position)):.1f}m",
                   (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # Show frame
        cv2.imshow('Escape Test', frame)
        
        # Handle key events
        key = cv2.waitKey(50) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            our_position = [400.0, 400.0, 70.0]
            our_velocity = [0.0, 0.0, 0.0]
            controller.reset()
        
        t += 0.05  # Time increment
        
    cv2.destroyAllWindows()
    print("\nTest completed!")

if __name__ == "__main__":
    main() 