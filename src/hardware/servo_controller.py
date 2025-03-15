import time
import threading
import numpy as np
from typing import Dict, Tuple, Optional, List

# Raspberry Pi üzerinde çalışıyorsa GPIO kütüphanesini içe aktar
try:
    import RPi.GPIO as GPIO
    import pigpio
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    print("Uyarı: RPi.GPIO veya pigpio kütüphanesi bulunamadı. Simülasyon modu kullanılacak.")

class ServoController:
    """
    Pan/Tilt servo motorlarını kontrol eden sınıf
    
    Bu sınıf, kamera kontrolörünün çıktılarını fiziksel servo motorlara iletir.
    Raspberry Pi üzerinde çalışıyorsa gerçek servo motorları kontrol eder,
    aksi takdirde simülasyon modunda çalışır.
    """
    def __init__(self,
                 pan_pin: int = 12,       # Pan servo pin numarası
                 tilt_pin: int = 13,      # Tilt servo pin numarası
                 pan_min: int = 500,      # Pan servo minimum PWM değeri (μs)
                 pan_max: int = 2500,     # Pan servo maximum PWM değeri (μs)
                 tilt_min: int = 500,     # Tilt servo minimum PWM değeri (μs)
                 tilt_max: int = 2500,    # Tilt servo maximum PWM değeri (μs)
                 pan_angle_min: float = -90.0,  # Pan minimum açı (derece)
                 pan_angle_max: float = 90.0,   # Pan maximum açı (derece)
                 tilt_angle_min: float = -45.0, # Tilt minimum açı (derece)
                 tilt_angle_max: float = 45.0,  # Tilt maximum açı (derece)
                 update_rate: float = 50.0,     # Güncelleme hızı (Hz)
                 simulation_mode: bool = not RPI_AVAILABLE):  # Simülasyon modu
        """
        Servo kontrolörünü başlat
        
        Args:
            pan_pin: Pan servo pin numarası
            tilt_pin: Tilt servo pin numarası
            pan_min: Pan servo minimum PWM değeri (μs)
            pan_max: Pan servo maximum PWM değeri (μs)
            tilt_min: Tilt servo minimum PWM değeri (μs)
            tilt_max: Tilt servo maximum PWM değeri (μs)
            pan_angle_min: Pan minimum açı (derece)
            pan_angle_max: Pan maximum açı (derece)
            tilt_angle_min: Tilt minimum açı (derece)
            tilt_angle_max: Tilt maximum açı (derece)
            update_rate: Güncelleme hızı (Hz)
            simulation_mode: Simülasyon modu
        """
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self.pan_min = pan_min
        self.pan_max = pan_max
        self.tilt_min = tilt_min
        self.tilt_max = tilt_max
        self.pan_angle_min = pan_angle_min
        self.pan_angle_max = pan_angle_max
        self.tilt_angle_min = tilt_angle_min
        self.tilt_angle_max = tilt_angle_max
        self.update_rate = update_rate
        self.simulation_mode = simulation_mode
        
        # Mevcut açılar
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.target_pan = 0.0
        self.target_tilt = 0.0
        
        # Durum değişkenleri
        self.is_running = False
        self.update_thread = None
        
        # Raspberry Pi üzerinde çalışıyorsa GPIO'yu ayarla
        if not self.simulation_mode and RPI_AVAILABLE:
            try:
                # pigpio kullan (daha hassas PWM kontrolü için)
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    print("Uyarı: pigpio daemon'a bağlanılamadı. Simülasyon modu kullanılacak.")
                    self.simulation_mode = True
                else:
                    # Servo pinlerini ayarla
                    self.pi.set_mode(self.pan_pin, pigpio.OUTPUT)
                    self.pi.set_mode(self.tilt_pin, pigpio.OUTPUT)
                    
                    # Başlangıç pozisyonuna getir
                    self._set_servo_pulse(self.pan_pin, self._angle_to_pulse(0, self.pan_min, self.pan_max, self.pan_angle_min, self.pan_angle_max))
                    self._set_servo_pulse(self.tilt_pin, self._angle_to_pulse(0, self.tilt_min, self.tilt_max, self.tilt_angle_min, self.tilt_angle_max))
                    print("Servo kontrolörü başlatıldı")
            except Exception as e:
                print(f"GPIO başlatılırken hata oluştu: {e}")
                self.simulation_mode = True
        
        if self.simulation_mode:
            print("Servo kontrolörü simülasyon modunda başlatıldı")
    
    def _angle_to_pulse(self, angle: float, pulse_min: int, pulse_max: int, angle_min: float, angle_max: float) -> int:
        """
        Açıyı PWM darbe genişliğine dönüştür
        
        Args:
            angle: Açı (derece)
            pulse_min: Minimum darbe genişliği (μs)
            pulse_max: Maximum darbe genişliği (μs)
            angle_min: Minimum açı (derece)
            angle_max: Maximum açı (derece)
            
        Returns:
            PWM darbe genişliği (μs)
        """
        # Açıyı sınırla
        angle = max(angle_min, min(angle_max, angle))
        
        # Açıyı 0-1 aralığına normalize et
        normalized = (angle - angle_min) / (angle_max - angle_min)
        
        # Darbe genişliğini hesapla
        pulse = int(pulse_min + normalized * (pulse_max - pulse_min))
        
        return pulse
    
    def _set_servo_pulse(self, pin: int, pulse: int):
        """
        Servo motorun darbe genişliğini ayarla
        
        Args:
            pin: Servo pin numarası
            pulse: Darbe genişliği (μs)
        """
        if not self.simulation_mode and RPI_AVAILABLE:
            try:
                self.pi.set_servo_pulsewidth(pin, pulse)
            except Exception as e:
                print(f"Servo kontrolünde hata: {e}")
        else:
            # Simülasyon modunda sadece değeri yazdır
            pass
    
    def _update_servos(self):
        """Servo motorları güncelle (ayrı bir iş parçacığında çalışır)"""
        last_update = time.time()
        
        while self.is_running:
            current_time = time.time()
            dt = current_time - last_update
            
            # Hedef açılara doğru yumuşak geçiş
            pan_diff = self.target_pan - self.current_pan
            tilt_diff = self.target_tilt - self.current_tilt
            
            # Yumuşatma faktörü (0.1 = yavaş, 0.5 = orta, 1.0 = anında)
            smoothing = 0.3
            
            self.current_pan += pan_diff * smoothing
            self.current_tilt += tilt_diff * smoothing
            
            # Açıları sınırla
            self.current_pan = max(self.pan_angle_min, min(self.pan_angle_max, self.current_pan))
            self.current_tilt = max(self.tilt_angle_min, min(self.tilt_angle_max, self.current_tilt))
            
            # Servo motorları güncelle
            pan_pulse = self._angle_to_pulse(self.current_pan, self.pan_min, self.pan_max, self.pan_angle_min, self.pan_angle_max)
            tilt_pulse = self._angle_to_pulse(self.current_tilt, self.tilt_min, self.tilt_max, self.tilt_angle_min, self.tilt_angle_max)
            
            self._set_servo_pulse(self.pan_pin, pan_pulse)
            self._set_servo_pulse(self.tilt_pin, tilt_pulse)
            
            if self.simulation_mode and (abs(pan_diff) > 0.1 or abs(tilt_diff) > 0.1):
                print(f"Servo pozisyonları - Pan: {self.current_pan:.1f}°, Tilt: {self.current_tilt:.1f}°")
            
            # Güncelleme hızına göre bekle
            last_update = current_time
            time.sleep(1.0 / self.update_rate)
    
    def start(self):
        """Servo kontrolörünü başlat"""
        if not self.is_running:
            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_servos)
            self.update_thread.daemon = True
            self.update_thread.start()
            print("Servo kontrolörü başlatıldı")
    
    def stop(self):
        """Servo kontrolörünü durdur"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
            self.update_thread = None
        
        # Servo motorları merkez pozisyona getir
        if not self.simulation_mode and RPI_AVAILABLE:
            try:
                self._set_servo_pulse(self.pan_pin, self._angle_to_pulse(0, self.pan_min, self.pan_max, self.pan_angle_min, self.pan_angle_max))
                self._set_servo_pulse(self.tilt_pin, self._angle_to_pulse(0, self.tilt_min, self.tilt_max, self.tilt_angle_min, self.tilt_angle_max))
                time.sleep(0.5)  # Servo motorların hareket etmesi için bekle
                
                # Servo motorları kapat
                self.pi.set_servo_pulsewidth(self.pan_pin, 0)
                self.pi.set_servo_pulsewidth(self.tilt_pin, 0)
                self.pi.stop()
            except Exception as e:
                print(f"Servo kapatılırken hata oluştu: {e}")
        
        print("Servo kontrolörü durduruldu")
    
    def set_angles(self, pan: float, tilt: float):
        """
        Servo motorların hedef açılarını ayarla
        
        Args:
            pan: Pan açısı (derece)
            tilt: Tilt açısı (derece)
        """
        # Açıları sınırla
        self.target_pan = max(self.pan_angle_min, min(self.pan_angle_max, pan))
        self.target_tilt = max(self.tilt_angle_min, min(self.tilt_angle_max, tilt))
    
    def update_from_tracking(self, tracking_commands: Dict):
        """
        Takip komutlarına göre servo motorları güncelle
        
        Args:
            tracking_commands: Takip komutları
        """
        if 'pan' in tracking_commands and 'tilt' in tracking_commands:
            self.set_angles(tracking_commands['pan'], tracking_commands['tilt'])
    
    def get_status(self) -> Dict:
        """
        Servo kontrolörü durumunu al
        
        Returns:
            Durum sözlüğü
        """
        return {
            'current_pan': self.current_pan,
            'current_tilt': self.current_tilt,
            'target_pan': self.target_pan,
            'target_tilt': self.target_tilt,
            'is_running': self.is_running,
            'simulation_mode': self.simulation_mode
        } 