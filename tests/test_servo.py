import time
import sys
import os
import argparse
import threading
import cv2
import numpy as np

# Proje kök dizinini Python yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.servo_controller import ServoController

def draw_servo_visualization(width=800, height=600, pan=0, tilt=0):
    """
    Servo pozisyonlarını görselleştir
    
    Args:
        width: Görüntü genişliği
        height: Görüntü yüksekliği
        pan: Pan açısı (derece)
        tilt: Tilt açısı (derece)
        
    Returns:
        Görselleştirilmiş görüntü
    """
    # Boş bir görüntü oluştur
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Merkez nokta
    center_x, center_y = width // 2, height // 2
    
    # Pan ve tilt çizgilerini çiz
    pan_rad = np.radians(pan)
    tilt_rad = np.radians(tilt)
    
    # Pan çizgisi (yatay düzlemde)
    pan_length = 200
    pan_end_x = int(center_x + pan_length * np.sin(pan_rad))
    pan_end_y = center_y
    
    # Tilt çizgisi (dikey düzlemde)
    tilt_length = 150
    tilt_end_x = pan_end_x
    tilt_end_y = int(pan_end_y - tilt_length * np.sin(tilt_rad))
    
    # Kamera gövdesi
    cv2.rectangle(img, (center_x-30, center_y-20), (center_x+30, center_y+20), (100, 100, 100), -1)
    
    # Pan ekseni
    cv2.line(img, (center_x, center_y), (pan_end_x, pan_end_y), (0, 0, 255), 3)
    
    # Tilt ekseni
    cv2.line(img, (pan_end_x, pan_end_y), (tilt_end_x, tilt_end_y), (255, 0, 0), 3)
    
    # Kamera lens
    cv2.circle(img, (tilt_end_x, tilt_end_y), 20, (0, 0, 0), -1)
    cv2.circle(img, (tilt_end_x, tilt_end_y), 15, (50, 50, 50), -1)
    cv2.circle(img, (tilt_end_x, tilt_end_y), 5, (200, 200, 200), -1)
    
    # Açı bilgilerini ekle
    cv2.putText(img, f"Pan: {pan:.1f} derece", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, f"Tilt: {tilt:.1f} derece", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Kontrol bilgilerini ekle
    cv2.putText(img, "Kontroller:", (50, height-120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "A/D: Pan Sol/Sağ", (50, height-90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "W/S: Tilt Yukarı/Aşağı", (50, height-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "R: Sıfırla, Q: Çıkış", (50, height-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    return img

def main():
    # Komut satırı argümanlarını ayarla
    parser = argparse.ArgumentParser(description='Servo Kontrolörü Testi')
    parser.add_argument('--simulation', action='store_true', help='Simülasyon modunu zorla')
    parser.add_argument('--pan_pin', type=int, default=12, help='Pan servo pin numarası')
    parser.add_argument('--tilt_pin', type=int, default=13, help='Tilt servo pin numarası')
    args = parser.parse_args()
    
    # Servo kontrolörünü oluştur
    servo_controller = ServoController(
        pan_pin=args.pan_pin,
        tilt_pin=args.tilt_pin,
        simulation_mode=args.simulation
    )
    
    # Servo kontrolörünü başlat
    servo_controller.start()
    
    # Başlangıç açıları
    pan = 0.0
    tilt = 0.0
    
    # Açı değişim miktarı
    pan_step = 5.0
    tilt_step = 5.0
    
    print("Servo Kontrolörü Testi")
    print("----------------------")
    print("Kontroller:")
    print("A/D: Pan Sol/Sağ")
    print("W/S: Tilt Yukarı/Aşağı")
    print("R: Sıfırla")
    print("Q: Çıkış")
    
    # Görselleştirme penceresini oluştur
    cv2.namedWindow('Servo Kontrolörü Testi', cv2.WINDOW_NORMAL)
    
    try:
        while True:
            # Servo pozisyonlarını görselleştir
            img = draw_servo_visualization(pan=pan, tilt=tilt)
            cv2.imshow('Servo Kontrolörü Testi', img)
            
            # Klavye girişini bekle
            key = cv2.waitKey(100) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('a'):
                pan -= pan_step
            elif key == ord('d'):
                pan += pan_step
            elif key == ord('w'):
                tilt += tilt_step
            elif key == ord('s'):
                tilt -= tilt_step
            elif key == ord('r'):
                pan = 0.0
                tilt = 0.0
            
            # Açıları sınırla
            pan = max(-90.0, min(90.0, pan))
            tilt = max(-45.0, min(45.0, tilt))
            
            # Servo motorları güncelle
            servo_controller.set_angles(pan, tilt)
            
            # Servo durumunu al
            status = servo_controller.get_status()
            
            # Durum bilgilerini yazdır
            if args.simulation:
                print(f"\rPan: {status['current_pan']:.1f}°, Tilt: {status['current_tilt']:.1f}°", end="")
    
    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu")
    
    finally:
        # Servo kontrolörünü durdur
        servo_controller.stop()
        
        # Pencereleri kapat
        cv2.destroyAllWindows()
        
        print("\nServo kontrolörü testi tamamlandı")

if __name__ == "__main__":
    main() 