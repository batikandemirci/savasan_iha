import cv2
import numpy as np
import time
import argparse
import os
import sys

# Proje kök dizinini Python yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.tracking.kalman_tracker import KalmanTracker
from vision.targeting.tracking_manager import TrackingManager

def load_yolo_model(model_path):
    """YOLO modelini yükle"""
    try:
        # OpenCV DNN ile YOLO modelini yükle
        net = cv2.dnn.readNet(model_path)
        
        # CUDA kullanılabilirse GPU'yu kullan
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        print("CUDA backend kullanılıyor")
    except:
        # CUDA kullanılamıyorsa CPU kullan
        net = cv2.dnn.readNet(model_path)
        print("CPU backend kullanılıyor")
    
    # Sınıf isimlerini yükle (İHA tespiti için)
    classes = ["IHA"]
    
    # Çıkış katmanlarını al
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    
    return net, classes, output_layers

def detect_uavs(frame, net, output_layers, classes, conf_threshold=0.5):
    """YOLO ile İHA'ları tespit et"""
    height, width, _ = frame.shape
    
    # Görüntüyü YOLO için hazırla
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    
    # Çıktıları al
    outs = net.forward(output_layers)
    
    # Tespit edilen nesneleri işle
    class_ids = []
    confidences = []
    boxes = []
    
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > conf_threshold:
                # Nesne koordinatlarını hesapla
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # Dikdörtgen koordinatları
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Non-maximum suppression uygula
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, 0.4)
    
    detections = []
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = classes[class_ids[i]]
            confidence = confidences[i]
            
            # Tespit bilgilerini ekle
            detections.append({
                'bbox': [x, y, x+w, y+h],
                'confidence': confidence,
                'class': label
            })
    
    return detections

def main():
    # Komut satırı argümanlarını ayarla
    parser = argparse.ArgumentParser(description='İHA Takip Testi')
    parser.add_argument('--video', type=str, default='data/test_video.mp4', help='Test video dosyası')
    parser.add_argument('--model', type=str, default='models/yolov5s.pt', help='YOLO model dosyası')
    parser.add_argument('--conf', type=float, default=0.5, help='Tespit güven eşiği')
    parser.add_argument('--output', type=str, default='output/tracking_test.avi', help='Çıktı video dosyası')
    args = parser.parse_args()
    
    # Video dosyasını aç
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Hata: {args.video} açılamadı")
        return
    
    # Video özellikleri
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Çıktı video yazıcısını ayarla
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    out = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*'XVID'), fps, (frame_width, frame_height))
    
    # YOLO modelini yükle
    try:
        net, classes, output_layers = load_yolo_model(args.model)
    except Exception as e:
        print(f"Model yüklenirken hata oluştu: {e}")
        print("Varsayılan tespit kullanılacak")
        net, classes, output_layers = None, None, None
    
    # Kalman takipçisini oluştur
    tracker = KalmanTracker(max_disappeared=30, max_distance=150.0)
    
    # Takip yöneticisini oluştur
    tracking_manager = TrackingManager(
        frame_width=frame_width,
        frame_height=frame_height,
        required_lock_time=5.0,
        max_pan_rate=30.0,
        max_tilt_rate=20.0,
        debug_mode=True
    )
    
    # Simülasyon değişkenleri
    frame_count = 0
    start_time = time.time()
    
    # Simüle edilmiş kamera açıları
    pan_angle = 0.0
    tilt_angle = 0.0
    
    print("Test başlatılıyor...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Her 5 karede bir FPS hesapla
        if frame_count % 5 == 0:
            elapsed_time = time.time() - start_time
            fps_current = frame_count / elapsed_time
            print(f"İşlenen kare: {frame_count}, FPS: {fps_current:.2f}")
        
        # YOLO ile İHA'ları tespit et
        if net is not None:
            detections = detect_uavs(frame, net, output_layers, classes, args.conf)
        else:
            # Test için simüle edilmiş tespit
            # Ekranın ortasında hareket eden bir İHA simüle et
            center_x = int(frame_width/2 + 100 * np.sin(frame_count / 50.0))
            center_y = int(frame_height/2 + 80 * np.cos(frame_count / 30.0))
            w, h = 100, 60
            
            detections = [{
                'bbox': [center_x - w//2, center_y - h//2, center_x + w//2, center_y + h//2],
                'confidence': 0.9,
                'class': 'IHA'
            }]
        
        # Kalman takipçisini güncelle
        tracked_objects = tracker.update(detections)
        
        # Takip yöneticisini güncelle
        commands, processed_frame = tracking_manager.update(tracked_objects, frame)
        
        # Kamera açılarını güncelle
        pan_angle = commands['pan']
        tilt_angle = commands['tilt']
        
        # Durum bilgilerini ekle
        cv2.putText(processed_frame, f"Frame: {frame_count}", (10, 300),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(processed_frame, f"Tracking: {commands['is_tracking']}", (10, 330),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(processed_frame, f"Locked: {commands['is_locked']}", (10, 360),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Görüntüyü göster
        cv2.imshow('İHA Takip Testi', processed_frame)
        
        # Çıktı videosuna yaz
        out.write(processed_frame)
        
        # 'q' tuşuna basılırsa çık
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Kaynakları serbest bırak
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    print(f"Test tamamlandı. Çıktı: {args.output}")

if __name__ == "__main__":
    main() 