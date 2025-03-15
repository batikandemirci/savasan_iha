import numpy as np
import time
from typing import Dict, Tuple, Optional, List

class PIDController:
    """
    PID kontrolörü sınıfı
    """
    def __init__(self, kp: float, ki: float, kd: float, min_output: float, max_output: float):
        """
        PID kontrolörünü başlat
        
        Args:
            kp: Oransal kazanç
            ki: İntegral kazanç
            kd: Türev kazanç
            min_output: Minimum çıkış değeri
            max_output: Maximum çıkış değeri
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_output = min_output
        self.max_output = max_output
        
        # PID durumu
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = None
        
    def compute(self, setpoint: float, process_variable: float, current_time: float = None) -> float:
        """
        PID çıkışını hesapla
        
        Args:
            setpoint: Hedef değer
            process_variable: Mevcut değer
            current_time: Mevcut zaman (None ise otomatik alınır)
            
        Returns:
            PID çıkış değeri
        """
        if current_time is None:
            current_time = time.time()
            
        # İlk çağrı için zaman başlat
        if self.last_time is None:
            self.last_time = current_time
            self.previous_error = setpoint - process_variable
            return 0.0
            
        # Zaman farkını hesapla
        dt = current_time - self.last_time
        if dt <= 0:
            return 0.0  # Zaman farkı yoksa hesaplama yapma
            
        # Hata hesapla
        error = setpoint - process_variable
        
        # İntegral hesapla (anti-windup ile)
        self.integral += error * dt
        
        # Türev hesapla
        derivative = (error - self.previous_error) / dt if dt > 0 else 0
        
        # PID çıkışını hesapla
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        # Çıkışı sınırla
        output = max(self.min_output, min(self.max_output, output))
        
        # Durumu güncelle
        self.previous_error = error
        self.last_time = current_time
        
        return output
        
    def reset(self):
        """PID durumunu sıfırla"""
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = None


class CameraController:
    """
    PID tabanlı kamera yönelim kontrolörü
    """
    def __init__(self, 
                 frame_width: int = 1280,
                 frame_height: int = 720,
                 target_zone_margin: float = 0.1,  # Hedef bölge marjı (merkeze göre)
                 max_pan_rate: float = 30.0,       # Saniyede maksimum pan açısı (derece)
                 max_tilt_rate: float = 20.0,      # Saniyede maksimum tilt açısı (derece)
                 debug_mode: bool = True):
        """
        Kamera kontrolörünü başlat
        
        Args:
            frame_width: Kare genişliği
            frame_height: Kare yüksekliği
            target_zone_margin: Hedef bölge marjı (merkeze göre)
            max_pan_rate: Maksimum pan hızı (derece/saniye)
            max_tilt_rate: Maksimum tilt hızı (derece/saniye)
            debug_mode: Hata ayıklama modu
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_zone_margin = target_zone_margin
        self.max_pan_rate = max_pan_rate
        self.max_tilt_rate = max_tilt_rate
        self.debug_mode = debug_mode
        
        # Kamera merkezi
        self.center_x = frame_width / 2
        self.center_y = frame_height / 2
        
        # Hedef bölge (merkez etrafında)
        margin_x = frame_width * target_zone_margin
        margin_y = frame_height * target_zone_margin
        self.target_zone = {
            'x1': self.center_x - margin_x,
            'y1': self.center_y - margin_y,
            'x2': self.center_x + margin_x,
            'y2': self.center_y + margin_y
        }
        
        # PID kontrolörleri oluştur
        # Pan (yatay hareket) için PID
        self.pan_pid = PIDController(
            kp=0.05,  # Oransal kazanç
            ki=0.01,  # İntegral kazanç
            kd=0.02,  # Türev kazanç
            min_output=-max_pan_rate,
            max_output=max_pan_rate
        )
        
        # Tilt (dikey hareket) için PID
        self.tilt_pid = PIDController(
            kp=0.04,  # Oransal kazanç
            ki=0.008, # İntegral kazanç
            kd=0.015, # Türev kazanç
            min_output=-max_tilt_rate,
            max_output=max_tilt_rate
        )
        
        # Durum değişkenleri
        self.is_tracking = False
        self.last_target_position = None
        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0
        self.tracking_history = []
        self.last_update_time = None
        
    def is_target_in_zone(self, target_position: Tuple[float, float]) -> bool:
        """
        Hedefin merkez bölgede olup olmadığını kontrol et
        
        Args:
            target_position: Hedef pozisyonu (x, y)
            
        Returns:
            Hedef merkez bölgede ise True
        """
        x, y = target_position
        return (self.target_zone['x1'] <= x <= self.target_zone['x2'] and
                self.target_zone['y1'] <= y <= self.target_zone['y2'])
                
    def calculate_camera_movement(self, target_position: Tuple[float, float], 
                                current_time: float = None) -> Dict:
        """
        Hedefi takip etmek için kamera hareketini hesapla
        
        Args:
            target_position: Hedef pozisyonu (x, y)
            current_time: Mevcut zaman (None ise otomatik alınır)
            
        Returns:
            Kamera hareket komutları içeren sözlük
        """
        if current_time is None:
            current_time = time.time()
            
        # İlk güncelleme için zamanı başlat
        if self.last_update_time is None:
            self.last_update_time = current_time
            self.last_target_position = target_position
            return {'pan': 0.0, 'tilt': 0.0, 'in_zone': False}
            
        # Hedefin merkez bölgede olup olmadığını kontrol et
        in_zone = self.is_target_in_zone(target_position)
        
        # Hedef merkez bölgede ise, kamera hareketi gerekmez
        if in_zone and self.is_tracking:
            return {'pan': 0.0, 'tilt': 0.0, 'in_zone': True}
            
        # PID kontrolörleri ile pan ve tilt hızlarını hesapla
        pan_rate = self.pan_pid.compute(self.center_x, target_position[0], current_time)
        tilt_rate = self.tilt_pid.compute(self.center_y, target_position[1], current_time)
        
        # Zaman farkını hesapla
        dt = current_time - self.last_update_time
        
        # Açı değişimlerini hesapla
        pan_change = pan_rate * dt
        tilt_change = tilt_rate * dt
        
        # Mevcut açıları güncelle
        self.current_pan_angle += pan_change
        self.current_tilt_angle += tilt_change
        
        # Durumu güncelle
        self.is_tracking = True
        self.last_target_position = target_position
        self.last_update_time = current_time
        
        # Takip geçmişine ekle
        self.tracking_history.append({
            'time': current_time,
            'position': target_position,
            'pan': self.current_pan_angle,
            'tilt': self.current_tilt_angle,
            'in_zone': in_zone
        })
        
        # Geçmişi sınırla (son 100 kayıt)
        if len(self.tracking_history) > 100:
            self.tracking_history.pop(0)
            
        return {
            'pan': pan_rate,
            'tilt': tilt_rate,
            'pan_angle': self.current_pan_angle,
            'tilt_angle': self.current_tilt_angle,
            'in_zone': in_zone
        }
        
    def update(self, target_data: Dict, frame=None) -> Tuple[Dict, Optional[np.ndarray]]:
        """
        Kamera kontrolörünü güncelle
        
        Args:
            target_data: Hedef verisi (centroid, bbox, vb.)
            frame: İsteğe bağlı görüntü karesi
            
        Returns:
            Kamera komutları ve işlenmiş kare
        """
        # Hedef pozisyonunu al
        if 'centroid' in target_data:
            target_position = target_data['centroid']
        elif 'bbox' in target_data:
            # Bounding box'ın merkezini hesapla
            bbox = target_data['bbox']
            target_position = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        else:
            # Hedef pozisyonu yoksa, takibi durdur
            self.is_tracking = False
            return {'pan': 0.0, 'tilt': 0.0, 'in_zone': False, 'tracking': False}, frame
            
        # Kamera hareketini hesapla
        camera_commands = self.calculate_camera_movement(target_position)
        camera_commands['tracking'] = self.is_tracking
        
        # Görüntü karesi varsa, görselleştir
        if frame is not None and self.debug_mode:
            frame = self.visualize(frame, target_position, camera_commands)
            
        return camera_commands, frame
        
    def visualize(self, frame: np.ndarray, target_position: Tuple[float, float], 
                 commands: Dict) -> np.ndarray:
        """
        Kamera kontrolörü durumunu görselleştir
        
        Args:
            frame: Görüntü karesi
            target_position: Hedef pozisyonu
            commands: Kamera komutları
            
        Returns:
            Görselleştirilmiş kare
        """
        import cv2
        
        # Hedef bölgeyi çiz (yeşil/kırmızı)
        color = (0, 255, 0) if commands['in_zone'] else (0, 0, 255)
        cv2.rectangle(frame, 
                     (int(self.target_zone['x1']), int(self.target_zone['y1'])),
                     (int(self.target_zone['x2']), int(self.target_zone['y2'])),
                     color, 2)
        
        # Merkezi çiz
        cv2.circle(frame, (int(self.center_x), int(self.center_y)), 5, (255, 255, 255), -1)
        
        # Hedef pozisyonunu çiz
        cv2.circle(frame, (int(target_position[0]), int(target_position[1])), 8, color, -1)
        
        # Hareket vektörünü çiz
        if self.is_tracking:
            # Pan ve tilt vektörlerini çiz
            pan_length = commands['pan'] * 5  # Görselleştirme için ölçekle
            tilt_length = commands['tilt'] * 5
            
            cv2.arrowedLine(frame, 
                          (int(self.center_x), int(self.center_y)),
                          (int(self.center_x + pan_length), int(self.center_y)),
                          (255, 0, 0), 2)
            
            cv2.arrowedLine(frame, 
                          (int(self.center_x), int(self.center_y)),
                          (int(self.center_x), int(self.center_y + tilt_length)),
                          (0, 255, 0), 2)
        
        # Durum bilgilerini ekle
        cv2.putText(frame, f"Tracking: {self.is_tracking}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Pan: {commands['pan']:.2f} deg/s", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Tilt: {commands['tilt']:.2f} deg/s", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(frame, f"In Zone: {commands['in_zone']}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
        
    def reset(self):
        """Kamera kontrolörünü sıfırla"""
        self.is_tracking = False
        self.last_target_position = None
        self.current_pan_angle = 0.0
        self.current_tilt_angle = 0.0
        self.tracking_history = []
        self.last_update_time = None
        self.pan_pid.reset()
        self.tilt_pid.reset() 