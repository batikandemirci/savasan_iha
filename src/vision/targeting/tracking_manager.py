import numpy as np
import cv2
from typing import Dict, Tuple, Optional, List
import time

from .target_lock import TargetLockSystem
from .camera_controller import CameraController

class TrackingManager:
    """
    Hedef takip ve kamera kontrolü yöneticisi
    
    Bu sınıf, hedef kilitleme sistemi ile kamera kontrolörünü entegre eder.
    TEKNOFEST şartnamesine göre düşman İHA'yı tespit edip takip eder ve kilitlenir.
    """
    def __init__(self,
                 frame_width: int = 1280,
                 frame_height: int = 720,
                 required_lock_time: float = 5.0,
                 max_pan_rate: float = 30.0,
                 max_tilt_rate: float = 20.0,
                 debug_mode: bool = True):
        """
        Takip yöneticisini başlat
        
        Args:
            frame_width: Kare genişliği
            frame_height: Kare yüksekliği
            required_lock_time: Gerekli kilitlenme süresi (saniye)
            max_pan_rate: Maksimum pan hızı (derece/saniye)
            max_tilt_rate: Maksimum tilt hızı (derece/saniye)
            debug_mode: Hata ayıklama modu
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.debug_mode = debug_mode
        
        # Hedef kilitleme sistemi
        self.target_lock = TargetLockSystem(
            frame_width=frame_width,
            frame_height=frame_height,
            required_lock_time=required_lock_time
        )
        
        # Kamera kontrolörü
        self.camera_controller = CameraController(
            frame_width=frame_width,
            frame_height=frame_height,
            max_pan_rate=max_pan_rate,
            max_tilt_rate=max_tilt_rate,
            debug_mode=debug_mode
        )
        
        # Durum değişkenleri
        self.is_tracking = False
        self.is_locked = False
        self.current_target_id = None
        self.lock_start_time = None
        self.last_update_time = None
        self.tracking_history = []
        
        # Servo kontrol değişkenleri
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.target_pan = 0.0
        self.target_tilt = 0.0
        
    def update(self, tracked_objects: Dict, frame: np.ndarray) -> Tuple[Dict, np.ndarray]:
        """
        Takip yöneticisini güncelle
        
        Args:
            tracked_objects: Takip edilen nesneler sözlüğü
            frame: Görüntü karesi
            
        Returns:
            Komutlar ve işlenmiş kare
        """
        current_time = time.time()
        
        # İlk güncelleme için zamanı başlat
        if self.last_update_time is None:
            self.last_update_time = current_time
            
        # Zaman farkını hesapla
        dt = current_time - self.last_update_time
        
        # Hedef kilitleme sistemini güncelle
        lock_frame, lock_status = self.target_lock.update(tracked_objects, frame)
        
        # Kamera kontrolörünü güncelle (eğer takip edilen nesne varsa)
        camera_commands = {'pan': 0.0, 'tilt': 0.0, 'in_zone': False, 'tracking': False}
        
        if tracked_objects and len(tracked_objects) > 0:
            # İlk hedefi al (şu an için sadece bir hedef destekleniyor)
            target_id = list(tracked_objects.keys())[0]
            target_data = tracked_objects[target_id]
            
            # Kamera kontrolörünü güncelle
            camera_commands, _ = self.camera_controller.update(target_data)
            
            # Hedef takip durumunu güncelle
            self.is_tracking = camera_commands['tracking']
            self.current_target_id = target_id if self.is_tracking else None
            
            # Kilitlenme durumunu güncelle
            self.is_locked = lock_status['is_locked']
            
            # Takip geçmişine ekle
            self.tracking_history.append({
                'time': current_time,
                'target_id': target_id,
                'is_tracking': self.is_tracking,
                'is_locked': self.is_locked,
                'pan': camera_commands['pan'],
                'tilt': camera_commands['tilt'],
                'in_zone': camera_commands['in_zone']
            })
            
            # Geçmişi sınırla (son 100 kayıt)
            if len(self.tracking_history) > 100:
                self.tracking_history.pop(0)
        else:
            # Hedef yoksa, takibi sıfırla
            self.is_tracking = False
            self.current_target_id = None
            
        # Servo kontrol değerlerini güncelle
        self.target_pan += camera_commands['pan'] * dt
        self.target_tilt += camera_commands['tilt'] * dt
        
        # Servo pozisyonlarını sınırla (-90 ile 90 derece arası)
        self.target_pan = max(-90.0, min(90.0, self.target_pan))
        self.target_tilt = max(-90.0, min(90.0, self.target_tilt))
        
        # Yumuşak geçiş için mevcut değerleri hedefe doğru güncelle
        pan_diff = self.target_pan - self.current_pan
        tilt_diff = self.target_tilt - self.current_tilt
        
        # Yumuşatma faktörü (0.1 = yavaş, 0.5 = orta, 1.0 = anında)
        smoothing = 0.3
        
        self.current_pan += pan_diff * smoothing
        self.current_tilt += tilt_diff * smoothing
        
        # Komutları hazırla
        commands = {
            'is_tracking': self.is_tracking,
            'is_locked': self.is_locked,
            'target_id': self.current_target_id,
            'pan': self.current_pan,
            'tilt': self.current_tilt,
            'pan_rate': camera_commands['pan'],
            'tilt_rate': camera_commands['tilt'],
            'in_zone': camera_commands['in_zone'],
            'lock_status': lock_status
        }
        
        # Görselleştirme
        if self.debug_mode:
            frame = self.visualize(lock_frame, commands)
            
        # Zamanı güncelle
        self.last_update_time = current_time
            
        return commands, frame
        
    def visualize(self, frame: np.ndarray, commands: Dict) -> np.ndarray:
        """
        Takip yöneticisi durumunu görselleştir
        
        Args:
            frame: Görüntü karesi
            commands: Komutlar
            
        Returns:
            Görselleştirilmiş kare
        """
        # Servo pozisyonlarını göster
        cv2.putText(frame, f"Pan: {commands['pan']:.1f} deg", (10, 180),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Tilt: {commands['tilt']:.1f} deg", (10, 210),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Takip ve kilitlenme durumunu göster
        status_text = "LOCKED" if commands['is_locked'] else "TRACKING" if commands['is_tracking'] else "SEARCHING"
        status_color = (0, 255, 0) if commands['is_locked'] else (0, 255, 255) if commands['is_tracking'] else (0, 0, 255)
        
        cv2.putText(frame, f"Status: {status_text}", (10, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # Hedef ID'sini göster
        if commands['target_id'] is not None:
            cv2.putText(frame, f"Target ID: {commands['target_id']}", (10, 270),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
        
    def reset(self):
        """Takip yöneticisini sıfırla"""
        self.is_tracking = False
        self.is_locked = False
        self.current_target_id = None
        self.lock_start_time = None
        self.last_update_time = None
        self.tracking_history = []
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.target_pan = 0.0
        self.target_tilt = 0.0
        self.target_lock.reset_lock()
        self.camera_controller.reset()
        
    def get_status(self) -> Dict:
        """
        Takip yöneticisi durumunu al
        
        Returns:
            Durum sözlüğü
        """
        return {
            'is_tracking': self.is_tracking,
            'is_locked': self.is_locked,
            'current_target_id': self.current_target_id,
            'current_pan': self.current_pan,
            'current_tilt': self.current_tilt,
            'tracking_history': self.tracking_history
        } 