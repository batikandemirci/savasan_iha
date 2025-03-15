import cv2
import numpy as np
import time
import os
from detection.models.yolo_detector import YOLODetector
from detection.tracking.kalman_tracker import KalmanTracker
from vision.targeting.target_lock import TargetLockSystem
from detection.qr.qr_detector import QRDetector
from detection.qr.qr_processor import QRProcessor
from vision.mission.mission_controller import MissionController, MissionState
import argparse

class UAVSystem:
    """
    Main UAV vision and targeting system
    """
    def __init__(self,
                 model_path: str = "yolo11x.pt",
                 video_source: str = "0",
                 frame_width: int = 1280,
                 frame_height: int = 720,
                 output_path: str = "output.mp4",
                 team_name: str = "Team_Name",
                 match_number: int = 1):
        """
        Initialize UAV system
        
        Args:
            model_path: Path to YOLO model weights
            video_source: Path to video file or camera index (as string)
            frame_width: Width of video frames
            frame_height: Height of video frames
            output_path: Path to save output video
            team_name: Team name for video filename
            match_number: Match number for video filename
        """
        self.team_name = team_name
        self.match_number = match_number
        
        # Ensure minimum resolution
        self.frame_width = max(frame_width, 640)
        self.frame_height = max(frame_height, 480)
        
        # Initialize video capture
        self.video_source = video_source
        try:
            if video_source.isdigit():
                self.cap = cv2.VideoCapture(int(video_source))
            else:
                self.cap = cv2.VideoCapture(video_source)
        except:
            raise ValueError(f"Could not open video source: {video_source}")
            
        # Set frame size
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        # Get actual frame size
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Check aspect ratio
        aspect_ratio = actual_width / actual_height
        valid_ratios = [4/3, 5/4, 16/9]  # Allowed aspect ratios
        if not any(abs(aspect_ratio - r) < 0.1 for r in valid_ratios):
            raise ValueError(f"Invalid aspect ratio: {aspect_ratio}. Must be one of: 4:3, 5:4, 16:9")
        
        # Set minimum FPS
        target_fps = max(15, self.cap.get(cv2.CAP_PROP_FPS))
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # Generate competition-compliant output filename
        date_str = time.strftime("%d_%m_%Y")
        self.output_path = f"{self.match_number}_{self.team_name}_{date_str}.mp4"
        
        # Initialize video writer with MP4V codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.output_path, fourcc, self.fps,
                                    (actual_width, actual_height))
        
        if not self.writer.isOpened():
            raise ValueError("Could not initialize video writer. Please check codec support.")
        
        # Initialize components
        self.detector = YOLODetector(model_path)
        self.tracker = KalmanTracker()
        self.target_lock = TargetLockSystem(
            frame_width=actual_width,
            frame_height=actual_height
        )
        
        # Initialize QR and mission components
        self.qr_detector = QRDetector(debug_mode=True)
        self.qr_processor = QRProcessor()
        self.mission_controller = MissionController()
        
        # Performance monitoring
        self.prev_time = 0
        self.fps = 0
        
        # Enhanced Statistics
        self.total_frames = 0
        self.lock_frames = 0
        self.successful_locks = 0
        self.lock_attempts = 0  # Total number of lock attempts
        self.server_time = 0.0
        self.lock_history = []  # List to store lock history
        self.uav_stats = {}  # Dictionary to store per-UAV statistics
        
    def set_server_time(self, server_time: float):
        """Update server time"""
        self.server_time = server_time
        self.target_lock.set_server_time(server_time)
        
    def _update_uav_stats(self, uav_id: str, lock_status: dict, position: tuple):
        """Update statistics for a specific UAV"""
        if uav_id not in self.uav_stats:
            self.uav_stats[uav_id] = {
                'total_frames_tracked': 0,
                'total_lock_attempts': 0,
                'successful_locks': 0,
                'total_lock_duration': 0.0,
                'lock_positions': [],  # List of positions where locks occurred
                'average_confidence': 0.0,
                'confidence_samples': 0
            }
        
        stats = self.uav_stats[uav_id]
        stats['total_frames_tracked'] += 1
        
        if lock_status['is_locked']:
            if position not in stats['lock_positions']:
                stats['lock_positions'].append(position)
            stats['total_lock_duration'] = lock_status['lock_duration']
        
    def run(self):
        """Main processing loop"""
        try:
            while True:
                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.total_frames += 1
                
                # Update server time (should be synced with competition server)
                self.server_time = time.time()
                self.target_lock.set_server_time(self.server_time)
                
                # Calculate FPS
                current_time = time.time()
                self.fps = 1 / (current_time - self.prev_time)
                self.prev_time = current_time
                
                # Detect QR codes first
                frame, qr_detections = self.qr_detector.detect(frame)
                
                # Process QR commands
                for qr_detection in qr_detections:
                    command_info = self.qr_processor.process_qr_data(qr_detection['data'])
                    if command_info:
                        self.mission_controller.process_command(command_info)
                
                # Detect objects
                frame, detections = self.detector.detect(frame)
                
                # Update tracker with detections
                tracked_objects = self.tracker.update(detections)
                
                # Update target lock status based on mission state
                mission_status = self.mission_controller.get_mission_status()
                if mission_status['current_state'] == MissionState.KAMIKAZE:
                    # Handle kamikaze mode
                    pass
                elif mission_status['current_state'] == MissionState.ESCAPING:
                    # Handle escape mode
                    pass
                else:
                    # Normal tracking and locking
                    frame, lock_status = self.target_lock.update(tracked_objects, frame)
                    
                    # Update statistics
                    if tracked_objects and lock_status['uav_id']:
                        # Get UAV position
                        obj = list(tracked_objects.values())[0]
                        position = obj['centroid']
                        
                        # Update UAV specific stats
                        self._update_uav_stats(lock_status['uav_id'], lock_status, position)
                        
                        # Update lock statistics
                        if lock_status['is_locked']:
                            self.lock_frames += 1
                            if self.lock_frames == 1:  # Just achieved lock
                                self.successful_locks += 1
                                # Record detailed lock information
                                lock_info = {
                                    'uav_id': lock_status['uav_id'],
                                    'time': time.strftime('%H:%M:%S') + f'.{int((time.time() % 1) * 1000):03d}',
                                    'duration': lock_status['lock_duration'],
                                    'position': position,
                                    'frame_number': self.total_frames
                                }
                                self.lock_history.append(lock_info)
                                self.uav_stats[lock_status['uav_id']]['successful_locks'] += 1
                                print(f"\nNew Lock Achieved!")
                                print(f"UAV: {lock_status['uav_id']}")
                                print(f"Time: {lock_info['time']}")
                                print(f"Frame: {self.total_frames}")
                        else:
                            if self.lock_frames > 0:  # Was trying to lock
                                self.lock_attempts += 1
                                self.uav_stats[lock_status['uav_id']]['total_lock_attempts'] += 1
                            self.lock_frames = 0
                
                # Draw enhanced statistics
                stats_text = [
                    f"FPS: {self.fps:.1f}",
                    f"Frames: {self.total_frames}",
                    f"Locks: {self.successful_locks}",
                    f"Success Rate: {(self.successful_locks/max(1, self.lock_attempts))*100:.1f}%",
                    f"Mission: {mission_status['current_state'].value}"
                ]
                
                for i, text in enumerate(stats_text):
                    cv2.putText(frame, text,
                               (frame.shape[1] - 250, 30 + (i * 25)),
                               cv2.FONT_HERSHEY_SIMPLEX,
                               0.7, (0, 255, 0), 2)
                
                # Write frame to output video
                self.writer.write(frame)
                
                # Display frame
                cv2.imshow('UAV Vision System', frame)
                
                # Check for exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            # Cleanup
            self.cleanup()
            
            # Print enhanced statistics
            print(f"\nProcessing Complete!")
            print(f"Total Frames: {self.total_frames}")
            print(f"Successful Locks: {self.successful_locks}")
            
            # Print QR statistics
            qr_stats = self.qr_detector.get_stats()
            print(f"\nQR Code Statistics:")
            print(f"Total Detections: {qr_stats['total_detections']}")
            print(f"Successful Decodes: {qr_stats['successful_decodes']}")
            
            # Print mission statistics
            mission_status = self.mission_controller.get_mission_status()
            print(f"\nMission Status:")
            print(f"Final State: {mission_status['current_state'].value}")
            print(f"State Duration: {mission_status['state_duration']:.1f}s")
            
            # Calculate and display success rate
            if self.lock_attempts > 0:
                success_rate = (self.successful_locks / self.lock_attempts) * 100
                print(f"Lock Success Rate: {success_rate:.1f}% ({self.successful_locks}/{self.lock_attempts} attempts)")
            
            # Display per-UAV statistics
            if self.uav_stats:
                print("\nPer-UAV Statistics:")
                for uav_id, stats in self.uav_stats.items():
                    print(f"\n{uav_id}:")
                    print(f"  Frames Tracked: {stats['total_frames_tracked']}")
                    print(f"  Successful Locks: {stats['successful_locks']}")
                    if stats['total_lock_attempts'] > 0:
                        uav_success_rate = (stats['successful_locks'] / stats['total_lock_attempts']) * 100
                        print(f"  Lock Success Rate: {uav_success_rate:.1f}%")
                    print(f"  Total Lock Duration: {stats['total_lock_duration']:.1f}s")
                    print(f"  Lock Positions: {len(stats['lock_positions'])} different positions")
            
            # Display detailed lock history
            if self.lock_history:
                print("\nDetailed Lock History:")
                for i, lock in enumerate(self.lock_history, 1):
                    print(f"{i}. {lock['uav_id']} locked at {lock['time']}")
                    print(f"   Duration: {lock['duration']:.1f}s")
                    print(f"   Position: ({lock['position'][0]:.1f}, {lock['position'][1]:.1f})")
                    print(f"   Frame: {lock['frame_number']}")
            
            print(f"\nOutput saved to: {self.output_path}")
            print(f"Video format: {self.frame_width}x{self.frame_height} @ {self.fps}fps")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'cap'):
            self.cap.release()
        if hasattr(self, 'writer'):
            self.writer.release()
        cv2.destroyAllWindows()
        
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

if __name__ == "__main__":
    # Command line arguments
    parser = argparse.ArgumentParser(description='UAV Vision System')
    parser.add_argument('--source', type=str, default='0',
                      help='Video source. Use 0 for webcam, or path to video file')
    parser.add_argument('--model', type=str, default='src/detection/models/yolo11_egitilmis.pt',
                      help='Path to YOLO model weights')
    parser.add_argument('--output', type=str, default='output_tracking.mp4',
                      help='Output video path')
    parser.add_argument('--width', type=int, default=1280,
                      help='Frame width')
    parser.add_argument('--height', type=int, default=720,
                      help='Frame height')
    parser.add_argument('--team_name', type=str, default='TEKNOFEST',
                      help='Team name for video filename')
    parser.add_argument('--match_number', type=int, default=1,
                      help='Match number for video filename')
    
    args = parser.parse_args()
    
    # Create and run UAV system
    uav_system = UAVSystem(
        model_path=args.model,
        video_source=args.source,
        frame_width=args.width,
        frame_height=args.height,
        team_name=args.team_name,
        match_number=args.match_number,
        output_path=args.output
    )
    
    print("\nUAV Vision System Starting...")
    print(f"Source: {'Webcam' if args.source == '0' else args.source}")
    print(f"Model: {args.model}")
    print(f"Output: {args.output}")
    print(f"Resolution: {args.width}x{args.height}")
    print("\nPress 'q' to quit\n")
    
    uav_system.run() 