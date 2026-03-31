# 📍 Kentsel Haber İzleme ve Harita Üzerinde Görselleştirme Sistemi

![Proje Arayüzü](BURAYA_ISSUE_ÜZERİNDEN_ALDIĞIN_GÖRSEL_LİNKİNİ_YAPIŞTIR)

![Kocaeli University](https://img.shields.io/badge/Kocaeli_University-Computer_Engineering-blue) ![Project Status](https://img.shields.io/badge/Status-Completed-success) ![Python](https://img.shields.io/badge/Python-3.12+-yellow) ![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688) ![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248)

## 📖 Proje Hakkında
Bu sistem, Kocaeli yerel haber kaynaklarından son 3 güne ait verileri otomatik olarak toplayan, **Doğal Dil İşleme (NLP)** ile kategorize eden ve olayları **Google Maps API** üzerinden interaktif bir haritada görselleştiren uçtan uca bir platformdur. Proje, Kocaeli Üniversitesi Yazılım Laboratuvarı-II dersi kapsamında geliştirilmiştir.

## 🚀 Öne Çıkan Özellikler

* **Otomatik Veri Toplama (Web Scraping):** Çağdaş Kocaeli, Özgür Kocaeli, Ses Kocaeli, Yeni Kocaeli ve Bizim Yaka sitelerinden asenkron olarak veri çeker.
* **NLP ile Akıllı Sınıflandırma:** `intfloat/multilingual-e5-base` modeli kullanılarak haberler; *Trafik Kazası, Yangın, Hırsızlık, Elektrik Kesintisi ve Kültürel Etkinlikler* kategorilerine %74+ doğruluk eşiğiyle atanır.
* **Semantik Benzerlik Denetimi:** İçerik olarak %90 ve üzeri benzerlik gösteren haberler tespit edilir ve harita üzerinde tek bir noktada tüm kaynaklarıyla listelenir.
* **Konum ve Geocoding:** Haber metninden mahalle/sokak bilgileri Regex ile ayıklanır ve Google Geocoding API ile koordinata dönüştürülür.
* **Maliyet Tasarrufu (Caching):** Aynı konum için tekrar API çağrısı yapmamak adına MongoDB tabanlı bir koordinat önbellekleme sistemi kullanılır.

## 🛠 Teknik Mimari

### Backend (Python)
* **Framework:** FastAPI (Asenkron API yapısı).
* **Veritabanı:** MongoDB (Schema Validation ile zorunlu veri yapısı korunur).
* **AI & NLP:** `Sentence-Transformers` (E5 Embedding modeli).
* **Kütüphaneler:** `Motor` (Async MongoDB), `httpx` (Async Request), `BeautifulSoup4` (HTML Parsing).

### Frontend (Modern Dashboard)
* **Google Maps JS API:** Advanced Markers ve özel Gece Modu harita tasarımı.
* **Tasarım:** Glassmorphism efekti, CSS değişkenleri ile dinamik tema ve duyarlı (responsive) yapı.

## 📂 Proje Yapısı
```bash
.
├── backend/
│   ├── main.py            # API uç noktaları ve startup konfigürasyonu
│   ├── scraper.py         # Haber siteleri için özel geliştirilmiş tarayıcı
│   ├── nlp_processor.py   # AI Sınıflandırma ve semantik analiz
│   ├── geocoder.py        # Konum-Koordinat dönüşüm mantığı
│   ├── database.py        # MongoDB Schema ve Index tanımları
│   └── requirements.txt   # Gerekli bağımlılıklar listesi
├── frontend/
│   ├── index.html         # Uygulama ana arayüzü
│   ├── style.css          # Modern görsel tasarım dosyası
│   ├── app.js             # Harita ve filtreleme mantığı
│   └── config.js          # API Anahtarları (Google Maps & Backend URL)
└── README.md


🔧 Kurulum ve Çalıştırma
1. Gereksinimler
Python 3.12+

MongoDB (Local veya Atlas)

Google Maps API Key

2. Backend Kurulumu
Bash
cd backend
pip install -r requirements.txt
.env dosyasını oluşturun ve bilgilerinizi girin:

Kod snippet'i
MONGO_URI=mongodb://localhost:27017
GOOGLE_MAPS_API_KEY=KENDI_ANAHTARINIZ
3. Sistemi Başlatma
Backend'i çalıştırın:

Bash
uvicorn main:app --reload
Ardından frontend/index.html dosyasını tarayıcınızda açın.

👨‍💻 Hazırlayan
Ömercan - [Kocaeli Üniversitesi Bilgisayar Mühendisliği]
