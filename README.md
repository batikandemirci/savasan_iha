# 🚁 TEKNOFEST İHA Yarışması - İHA Takip ve Kilitlenme Sistemi

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.7%2B-blue" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/OpenCV-4.5%2B-green" alt="OpenCV 4.5+">
  <img src="https://img.shields.io/badge/YOLO-11-orange" alt="YOLO 11">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License: MIT">
</div>

## 📋 Proje Hakkında

Merhaba! Bu projemde TEKNOFEST SİHA yarışması için geliştirdiğim bir İHA takip ve kilitlenme sistemini sizlerle paylaşıyorum. Neden böyle bir şey yapıyorum çünkü iyilik kadar elde edilmesi kolay bir şey yok. Sistemimiz, düşman İHA'ları tespit edip takip ediyor ve yarışma şartnamesine uygun olarak kilitlenme gerçekleştiriyor. Görüntü işleme, nesne takibi ve servo motor kontrolü teknolojilerini bir araya getirerek, düşman İHA'ların tespiti, takibi ve gerektiğinde kilitlenme işlemlerini otomatik olarak yapabiliyoruz.

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/Tespit_ve_kilitlenme.gif" alt="Tespit ve Kilitlenme" width="600">
</p>

### 🎯 Neler Yapabiliyoruz?

- **Düşman İHA Tespiti**: Kamera görüntüsünden düşman İHA'ları gerçek zamanlı olarak tespit ediyoruz
- **Sürekli Takip**: Tespit ettiğimiz İHA'ları sürekli olarak takip edip kamera görüş alanında tutuyoruz
- **Hedef Kilitleme**: Şartname gereksinimlerine uygun olarak hedef kilitleme yapıyoruz
- **Yasak Bölge Kontrolü**: Önceden tanımlanmış yasak bölgeleri tanıyıp bu bölgelerden kaçınıyoruz
- **QR Kod Tanımlama**: Hedef İHA'ların üzerindeki QR kodları okuyup tanımlıyoruz
- **Kamikaze Modu**: Gerektiğinde kamikaze saldırı moduna geçip hedef İHA'ya yaklaşıyoruz

## 🛠️ Sistemimizin Özellikleri

### 1. Görüntü İşleme ve Nesne Tespiti

YOLO11 derin öğrenme algoritmasını kullanarak İHA tespiti yapıyoruz. Özellikle İHA yarışması için kendimiz eğittiğimiz özel "yolo11_batikan.pt" modelimiz sayesinde, tek bir işlemde hem nesne konumunu hem de sınıfını yüksek doğrulukla tahmin edebiliyoruz. Böylece gerçek zamanlı görüntü işleme için gereken hızı ve doğruluğu sağlıyoruz.

YOLO11 modelimiz ile:
- İHA'ların konumunu yüksek doğrulukla belirleyebiliyoruz
- Her tespit için güven skorunu hesaplayabiliyoruz
- Birden fazla İHA'yı aynı anda tespit edebiliyoruz
- Zorlu ışık koşullarında bile başarılı tespitler yapabiliyoruz

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/Tespit_ve_kilitlenme.png" alt="Tespit ve Kilitlenme Çıktısı" width="600">
</p>

### 2. Nesne Takibi Algoritması

Tespit ettiğimiz İHA'ların takibi için Kalman filtresi kullanıyoruz. Bu filtre sayesinde:

- İHA'nın hareketini tahmin edebiliyoruz
- Kamera görüş alanından kısa süreli çıksa bile takibi sürdürebiliyoruz
- Hareket yönü ve hızını hesaplayabiliyoruz
- Tespit gürültüsünü filtreleyebiliyoruz

### 3. PID Tabanlı Kamera Kontrolü

Kamera hareketlerini, PID (Proportional-Integral-Derivative) kontrolörü kullanarak hassas bir şekilde kontrol ediyoruz. PID kontrolörü, hedef ile kamera merkezi arasındaki hatayı en aza indirmeye çalışıyor.

PID kontrolörü ile:
- Hedefi kamera merkezinde tutabiliyoruz
- Ani hareketlerde bile kararlı takip yapabiliyoruz
- Aşırı düzeltme olmadan yumuşak kamera hareketi sağlayabiliyoruz
- Farklı hız ve mesafelerde çalışabiliyoruz

### 4. Servo Motor Kontrolü

Pan/tilt mekanizması için iki servo motor kullanıyoruz. Bu motorlar, PID kontrolörünün çıktısına göre hareket ederek kameranın hedefi takip etmesini sağlıyor.

Servo kontrol sistemimiz:
- Yatay (pan) ve dikey (tilt) eksenlerde hareket sağlıyor
- 0-180 derece arasında hassas açı kontrolü yapıyor
- Yumuşak geçişler için hareket interpolasyonu uyguluyor
- Hem gerçek donanım hem de simülasyon modunda çalışabiliyor

### 5. No-fly Zone Kontrolü

Önceden tanımlanmış yasak bölgeleri (no-fly zone) tanıyıp bu bölgelerden kaçınıyoruz. Her yasak bölge, merkez koordinatları ve yarıçapı ile tanımlanıyor. İHA'nın konumunu sürekli olarak kontrol edip yasak bölgeye yaklaşması durumunda kaçınma vektörü hesaplıyoruz.

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/no-fly-zone.gif" alt="No-fly Zone Kontrolü" width="600">
</p>

No-fly zone kontrolü ile:
- Yasak bölgeleri gerçek zamanlı tespit ediyoruz
- Yasak bölgelere yaklaşıldığında otomatik kaçınma yapıyoruz
- Yasak bölge ihlallerini kaydedip raporluyoruz
- Güvenli geçiş rotaları hesaplıyoruz

### 6. QR Kod Okuma

PyZBar kütüphanesi kullanarak QR kodları okuyup işliyoruz. Bu özellik, hedef İHA'ların tanımlanması için kullanılıyor.

QR kod okuma sistemimiz:
- Kamera görüntüsündeki QR kodları tespit ediyor
- Kodları gerçek zamanlı olarak çözümlüyor
- İHA kimlik bilgilerini çıkarıyor
- Hedef önceliklendirme için bilgi sağlıyor

### 7. Kamikaze Modu

Hedef İHA'ya yaklaşıp QR kodunu okumak için kamikaze modunu kullanıyoruz. Bu mod, düşman İHA'ya kontrollü bir şekilde yaklaşmamızı sağlıyor.

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/Kamikaze.gif" alt="Kamikaze Modu" width="600">
</p>

Kamikaze modu ile:
- Hedef İHA'ya güvenli bir şekilde yaklaşabiliyoruz
- QR kodunu yakından okuyabiliyoruz
- Çarpışma riskini minimize ediyoruz
- Görev tamamlandığında güvenli bir şekilde uzaklaşabiliyoruz

## 🏗️ Sistemimizin Mimarisi

Sistemimiz, aşağıdaki ana bileşenlerden oluşuyor:

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/system_architecture.png" alt="Sistem Mimarisi" width="800">
</p>

1. **Tespit Modülü**: Özel eğitilmiş YOLO11 modeli kullanarak İHA'ları tespit ediyoruz
2. **Takip Modülü**: Kalman filtresi kullanarak İHA'ları takip ediyoruz
3. **Kamera Kontrolörü**: PID kontrolörü kullanarak kamerayı yönlendiriyoruz
4. **Servo Kontrolörü**: Fiziksel servo motorları kontrol ediyoruz
5. **Takip Yöneticisi**: Tespit, takip ve kamera kontrolünü entegre ediyoruz
6. **Görev Modülleri**: Kamikaze, kaçış ve diğer görevleri yönetiyoruz
7. **Güvenlik Modülü**: No-fly zone kontrolü yapıyoruz

## 📦 Modüllerimiz ve İşlevleri

### 1. Tespit Modülü
- İHA'ları gerçek zamanlı olarak tespit ediyoruz
- Her tespit için sınırlayıcı kutu (bounding box) ve güven skoru üretiyoruz
- Farklı ışık koşullarında ve mesafelerde çalışabiliyoruz
- Kısmi görünürlük durumlarında bile tespit yapabiliyoruz

### 2. Takip Modülü
- Tespit ettiğimiz İHA'ları sürekli olarak takip ediyoruz
- Geçici tespit kayıplarında bile takibi sürdürüyoruz
- Birden fazla hedefi aynı anda takip edebiliyoruz
- Hedef kimliklerini koruyor ve karışmalarını önlüyoruz

### 3. Kamera Kontrolü
- Hedefi kamera merkezinde tutmak için pan/tilt hareketlerini hesaplıyoruz
- PID algoritması ile yumuşak ve kararlı kamera hareketi sağlıyoruz
- Farklı hareket hızlarına uyum sağlıyoruz
- Hedef kilitleme durumunu yönetiyoruz

### 4. Servo Kontrolü
- Pan ve tilt servo motorlarını hassas bir şekilde kontrol ediyoruz
- PWM sinyalleri ile motor açılarını ayarlıyoruz
- Hareket sınırlarını kontrol ediyoruz
- Simülasyon modunda görsel geri bildirim sağlıyoruz

### 5. Görev Modülleri
- Kamikaze modu: Hedef İHA'ya yaklaşma ve QR kodu okuma
- Görev durumuna göre sistem davranışını değiştiriyoruz
- Görev önceliklerini yönetiyoruz

### 6. Güvenlik Modülü
- Yasak bölgeleri tanıyor ve kaçınma vektörleri hesaplıyoruz
- İhlal durumlarını kaydediyor ve raporluyoruz
- Güvenli geçiş rotaları öneriyoruz
- Çarpışma önleme algoritmaları uyguluyoruz

## 🔧 Kurulum ve Kullanım

### Gereksinimler

- Python 3.7+
- OpenCV 4.5+
- NumPy
- PyZBar (QR kod okuma için)
- PiGPIO (Raspberry Pi üzerinde servo kontrolü için)
- YOLO11 (Projede özel eğitilmiş model kullanıyoruz)

### Kurulum Adımları

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/batikandemirci/savasan_iha.git
   cd savasan_iha
   ```

2. Gerekli paketleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

3. Model dosyası zaten proje içerisinde bulunuyor:
   ```
   savasan_iha\src\detection\models\yolo11_batikan.pt
   ```
   Bu model, İHA yarışması için özel olarak eğitilmiş ve optimize edilmiştir.

4. Servo motorları bağlayın (Raspberry Pi kullanıyorsanız):
   - Pan servo: GPIO 12
   - Tilt servo: GPIO 13

### Kullanım Senaryoları

#### 1. Takip ve Kilitlenme Sistemini Çalıştırma

```bash
python src/run_tracking.py --video 0 --model src/detection/models/yolo11_batikan.pt
```

Bu komutla:
- Webcam'i açıyoruz (--video 0)
- Özel eğitilmiş YOLO11 modelimizi yüklüyoruz
- İHA tespiti ve takibini başlatıyoruz
- Servo kontrolünü etkinleştiriyoruz
- Gerçek zamanlı görüntü gösteriyoruz

Parametreler:
- `--video`: Video kaynağı (0=webcam, dosya yolu=video dosyası)
- `--model`: YOLO model dosyası (varsayılan: src/detection/models/yolo11_batikan.pt)
- `--conf`: Tespit güven eşiği (varsayılan: 0.5)
- `--output`: Çıktı video dosyası (varsayılan: output/tracking_output.avi)
- `--simulation`: Servo simülasyon modunu zorla
- `--pan_pin`: Pan servo pin numarası (varsayılan: 12)
- `--tilt_pin`: Tilt servo pin numarası (varsayılan: 13)
- `--no_display`: Görüntü gösterme

#### 2. Servo Kontrolörü Testi

```bash
python src/test_servo.py --simulation
```

Bu testle:
- Servo kontrolörünü simülasyon modunda başlatıyoruz
- Klavye kontrolleri ile servo hareketlerini test edebiliyoruz
- Servo açılarını ve hareketlerini görsel olarak görebiliyoruz

Parametreler:
- `--simulation`: Simülasyon modunu zorla
- `--pan_pin`: Pan servo pin numarası (varsayılan: 12)
- `--tilt_pin`: Tilt servo pin numarası (varsayılan: 13)

#### 3. Takip Testi

```bash
python src/test_tracking.py --video data/test_video.mp4 --model src/detection/models/yolo11_batikan.pt
```

Bu testle:
- Belirtilen video dosyasını açıyoruz
- İHA tespiti ve takibini gerçekleştiriyoruz
- Takip performansını değerlendiriyoruz
- Sonuçları görsel olarak gösterip kaydediyoruz

Parametreler:
- `--video`: Test video dosyası
- `--model`: YOLO model dosyası (varsayılan: src/detection/models/yolo11_batikan.pt)
- `--conf`: Tespit güven eşiği (varsayılan: 0.5)
- `--output`: Çıktı video dosyası (varsayılan: output/tracking_test.avi)

## 🎮 Simülasyon Modu

Sistemimizi, gerçek donanım olmadan da test edebiliyoruz. Simülasyon modu, servo motorları ve kamera hareketlerini görsel olarak simüle ediyor.

<p align="center">
  <img src="https://github.com/batikandemirci/savasan_iha/raw/main/docs/images/servo_simulation.png" alt="Servo Simülasyonu" width="400">
</p>

Simülasyon modunun avantajları:
- Gerçek donanım olmadan sistem geliştirme ve test yapabiliyoruz
- Servo hareketlerini görsel olarak izleyebiliyoruz
- Farklı senaryoları hızlı bir şekilde test edebiliyoruz
- Algoritma iyileştirmeleri için geri bildirim alabiliyoruz

### Simülasyon Modunu Çalıştırma

```bash
python src/test_servo.py --simulation
```

## ⚡ Performans ve Optimizasyon

Sistemimizi gerçek zamanlı çalışma için optimize ettik:

- **Özel Eğitilmiş Model**: YOLO11 tabanlı özel eğitilmiş "yolo11_batikan.pt" modelimiz ile İHA'ları yüksek doğrulukla tespit ediyoruz
- **Verimli Takip**: Kalman filtresi ile takip performansını artırırken hesaplama yükünü azaltıyoruz
- **Hassas Kontrol**: PID parametrelerini (Kp, Ki, Kd) sistem yanıtını optimize etmek için ayarlıyoruz
- **Adaptif İşleme**: Sistem yükü ve performans arasında denge sağlamak için adaptif işleme teknikleri kullanıyoruz

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 📞 İletişim

Proje Sahibi - [@github_batikandemirci](https://github.com/batikandemirci)

Proje Linki: [https://github.com/batikandemirci/savasan_iha](https://github.com/batikandemirci/savasan_iha)

---


<p align="center">
  TEKNOFEST SİHA Yarışması için geliştirilmiştir, umarım yararlı olur. Herhangi bir anomali durum olursa veya geliştirilmesi&düzeltilmesi gereken bir yer görürseniz, LinkedIn:@batikandemirci
</p>
