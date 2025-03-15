import cv2
import numpy as np
import time
from vision.safety.no_fly_zone_controller import NoFlyZoneController, ZoneType

def create_visualization_frame(width: int = 800, height: int = 800):
    """Create visualization frame with grid"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame.fill(255)
    
    # Draw grid lines
    for i in range(0, width, 50):
        cv2.line(frame, (i, 0), (i, height), (200, 200, 200), 1)
        cv2.line(frame, (0, i), (800, i), (200, 200, 200), 1)
    
    return frame

def simulate_uav_movement(current_pos: np.ndarray, 
                        target_pos: np.ndarray,
                        avoidance_vector: np.ndarray,
                        speed: float = 3.0) -> np.ndarray:
    """Simulate UAV movement with avoidance"""
    if avoidance_vector is not None and np.any(avoidance_vector):
        # Blend target direction with avoidance
        to_target = target_pos - current_pos
        distance = np.linalg.norm(to_target)
        
        if distance > 0:
            target_dir = to_target / distance
            movement = 0.1 * target_dir + 0.9 * avoidance_vector
            movement = movement / np.linalg.norm(movement)
        else:
            movement = avoidance_vector
    else:
        # Move directly to target
        to_target = target_pos - current_pos
        distance = np.linalg.norm(to_target)
        
        if distance > 0:
            movement = to_target / distance
        else:
            movement = np.zeros(3)
    
    return current_pos + movement * speed

def main():
    # Initialize no-fly zone controller
    controller = NoFlyZoneController(
        penalty_points_per_second=5.0,
        max_violation_time=30.0,
        safety_margin=50.0
    )
    
    # Add test zones
    zones = [
        # Air defense zones
        ("AD1", ZoneType.AIR_DEFENSE, (300, 400, 0), 80),
        ("AD2", ZoneType.AIR_DEFENSE, (500, 300, 0), 100),
        # Signal jamming zones
        ("SJ1", ZoneType.SIGNAL_JAMMING, (400, 600, 0), 70),
        ("SJ2", ZoneType.SIGNAL_JAMMING, (600, 500, 0), 90),
    ]
    
    for zone_id, zone_type, center, radius in zones:
        controller.add_zone(zone_id, zone_type, center, radius)
        controller.activate_zone(zone_id)
    
    # Initial positions
    uav_pos = np.array([100.0, 100.0, 50.0])  # Starting position
    uav_vel = np.zeros(3)
    target_pos = np.array([700.0, 700.0, 50.0])  # Target position
    
    print("No-Fly Zone Test Starting...")
    print("Controls:")
    print("  'q' - Quit")
    print("  'r' - Reset UAV position")
    print("  't' - New random target")
    print("  'z' - Toggle zones")
    
    while True:
        # Create visualization frame
        frame = create_visualization_frame()
        
        # Update zone violations
        status = controller.update(tuple(uav_pos))
        
        # Calculate avoidance vector
        avoidance_vector, violated_zones = controller.calculate_avoidance_vector(
            tuple(uav_pos),
            tuple(uav_vel),
            tuple(target_pos)
        )
        
        # Update UAV position
        uav_pos = simulate_uav_movement(uav_pos, target_pos, avoidance_vector)
        
        # Visualize zones
        frame = controller.visualize(frame)
        
        # Draw UAV and target
        cv2.circle(frame, (int(uav_pos[0]), int(uav_pos[1])), 8, (0, 255, 0), -1)
        cv2.circle(frame, (int(target_pos[0]), int(target_pos[1])), 8, (255, 0, 0), -1)
        
        # Draw movement vector
        if np.any(avoidance_vector):
            end_point = (
                int(uav_pos[0] + avoidance_vector[0] * 50),
                int(uav_pos[1] + avoidance_vector[1] * 50)
            )
            cv2.arrowedLine(frame, 
                          (int(uav_pos[0]), int(uav_pos[1])),
                          end_point,
                          (255, 255, 0), 2)
        
        # Add status info
        status_text = [
            f"Violations: {len(status['violated_zones'])}",
            f"Penalty Points: {status['total_penalty_points']:.1f}",
            f"Max Violation Time: {status['max_violation_time']:.1f}s",
            f"Emergency Landing: {'YES' if status['emergency_landing_required'] else 'NO'}"
        ]
        
        for i, text in enumerate(status_text):
            cv2.putText(frame, text,
                       (10, 30 + (i * 30)),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.7, (0, 0, 0), 2)
        
        # Show frame
        cv2.imshow('No-Fly Zone Test', frame)
        
        # Handle key events
        key = cv2.waitKey(50) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Reset UAV position
            uav_pos = np.array([100.0, 100.0, 50.0])
            uav_vel = np.zeros(3)
        elif key == ord('t'):
            # New random target
            target_pos = np.array([
                np.random.uniform(100, 700),
                np.random.uniform(100, 700),
                50.0
            ])
        elif key == ord('z'):
            # Toggle random zone
            zone_id = np.random.choice(list(controller.zones.keys()))
            zone = controller.zones[zone_id]
            if zone.is_active:
                controller.deactivate_zone(zone_id)
                print(f"Deactivated zone: {zone_id}")
            else:
                controller.activate_zone(zone_id)
                print(f"Activated zone: {zone_id}")
    
    cv2.destroyAllWindows()
    print("\nTest completed!")

if __name__ == "__main__":
    main() 