# live_chart


# 📈 Gerçek Zamanlı Hisse Senedi ve Portföy Takip Uygulaması

Streamlit, Finnhub WebSocket, Plotly ve Yahoo Finance kullanılarak geliştirilmiş gerçek zamanlı hisse senedi takip ve portföy yönetim uygulaması.

Bu uygulama kullanıcıların canlı hisse fiyatlarını takip etmesini, geçmiş performans analizleri yapmasını ve kendi yatırım portföylerini yönetmesini sağlar.

---

# 🚀 Özellikler

## 📊 Canlı Piyasa Takibi

* Finnhub WebSocket ile gerçek zamanlı fiyat verileri
* Otomatik güncellenen fiyat grafikleri
* Birden fazla hisse senedini takip edebilme
* Anlık işlem hacmi görüntüleme
* Hızlı ve akıcı veri akışı

---

## 📈 Grafik ve Teknik Analiz

* Canlı fiyat grafikleri

* Geçmiş fiyat analizleri

* Farklı zaman aralıkları:

  * 1 Ay
  * 3 Ay
  * 6 Ay
  * 1 Yıl
  * 2 Yıl
  * 5 Yıl

* Hareketli Ortalama (Moving Average) göstergesi

* Volatilite hesaplamaları

* Fiyat değişim yüzdeleri

---

## 🏢 Şirket Bilgileri

Seçilen hisse senedi için:

* Güncel fiyat
* Günlük değişim oranı
* F/K (P/E) Oranı
* 52 haftalık en yüksek fiyat
* 52 haftalık en düşük fiyat
* Şirket açıklaması

görüntülenebilir.

---

## 💼 Portföy Yönetimi

Kullanıcılar kendi yatırım portföylerini oluşturabilir.

### Portföy Özellikleri

* Hisse ekleme
* Alış fiyatı girme
* Lot/adet girme
* Portföy değerini hesaplama
* Güncel fiyatları takip etme
* Kar/Zarar hesaplama
* Yüzdesel getiri hesaplama

---

## 📉 Portföy Analitiği

Portföy oluşturulduktan sonra:

* Toplam portföy değeri
* Toplam yatırım maliyeti
* Toplam kar/zarar
* Kar/zarar yüzdesi
* Pozisyon sayısı

hesaplanır.

Ayrıca:

* Portföy dağılımı pasta grafiği
* Kar/Zarar karşılaştırma grafiği

otomatik olarak oluşturulur.

---

# ⚡ Performans Optimizasyonları

Uygulama daha hızlı çalışması için çeşitli optimizasyonlar içermektedir.

## Cache Kullanımı

Yahoo Finance üzerinden çekilen:

* Şirket bilgileri
* Geçmiş fiyat verileri
* Portföy fiyatları

belirli sürelerle önbelleğe alınır.

Bu sayede gereksiz API çağrıları azaltılır.

---

## Bellek Yönetimi

Canlı fiyat verileri Python'un `deque` veri yapısı ile saklanır.

Bu yöntem:

* Daha az RAM kullanır
* Eski verileri otomatik temizler
* Daha hızlı çalışır

---

## Arka Plan Veri İşleme

WebSocket bağlantısı ayrı bir thread üzerinde çalışır.

Böylece:

* Arayüz donmaz
* Kullanıcı deneyimi iyileşir
* Canlı veri akışı kesintisiz devam eder

---

## Ayarlanabilir Yenileme Süresi

Kullanıcı:

* 1 saniye
* 3 saniye
* 5 saniye

yenileme seçeneklerinden birini seçebilir.

Bu sayede performans ve güncellik dengesi kurulabilir.

---

# 🛠 Kullanılan Teknolojiler

## Programlama Dili

* Python

## Arayüz

* Streamlit

## Veri İşleme

* Pandas

## Grafikler

* Plotly
* Plotly Express

## Veri Kaynakları

* Finnhub API
* Yahoo Finance (yfinance)

## Gerçek Zamanlı Veri

* WebSocket

---

# 📦 Kurulum

Projeyi klonlayın:

```bash
git clone https://github.com/kullaniciadi/proje-adi.git
cd proje-adi
```

Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

Uygulamayı çalıştırın:

```bash
streamlit run borsa_takip_duzenlenmis.py
```

---

# 🔑 API Anahtarı

Finnhub üzerinden ücretsiz API anahtarı oluşturabilirsiniz:

https://finnhub.io

Daha sonra aşağıdaki değişkene kendi anahtarınızı girmeniz yeterlidir:

```python
FINNHUB_API_KEY = "API_ANAHTARINIZ"
```

---

# 🎯 Gelecek Güncellemeler

Projeye eklenmesi planlanan özellikler:

* RSI göstergesi
* MACD göstergesi
* Bollinger Bands
* Hisse haberleri
* İzleme listesi (Watchlist)
* Excel'e aktarma
* Alım/Satım sinyalleri
* Risk analizi
* Temettü takibi
* Formasyon tespiti
* Yapay zeka destekli analizler

---

# 👨‍💻 Geliştirici

**Buğra Uysal**

Ekonomi ve Finans Öğrencisi

İlgi Alanları:

* Veri Bilimi (Data Science)
* Finansal Analiz
* Makine Öğrenmesi (Machine Learning)
* Yazılım Geliştirme
* Yapay Zeka Destekli Uygulamalar
* Finansal Teknolojiler (FinTech)

## 🌐 Bağlantılar

**GitHub**

[bugra123uysal GitHub Profili](https://github.com/bugra123uysal?utm_source=chatgpt.com)

**LinkedIn**

[Mesut Buğra Uysal LinkedIn Profili](https://www.linkedin.com/in/mesut-bu%C4%9Fra-uysal-16a1bb288/?utm_source=chatgpt.com)

## 📫 İletişim

GitHub ve LinkedIn üzerinden benimle iletişime geçebilir, projelerimi inceleyebilir veya geri bildirimde bulunabilirsiniz.

---

# 🤝 Teşekkürler

Bu proje geliştirilirken modern yapay zeka araçlarından destek alınmıştır:

* ChatGPT
* Claude

Bu araçlar;

* Kod inceleme
* Hata ayıklama
* Performans optimizasyonu
* Mimari planlama
* Özellik geliştirme

süreçlerinde yardımcı olarak kullanılmıştır.

<img width="1906" height="698" alt="Ekran görüntüsü 2026-06-03 213818" src="https://github.com/user-attachments/assets/b5167120-3087-4532-9099-3bdd44f88853" />

<img width="1891" height="683" alt="Ekran görüntüsü 2026-06-03 213846" src="https://github.com/user-attachments/assets/4ee915c9-7cd6-408e-9b58-fde9123f70d2" />

<img width="1874" height="730" alt="Ekran görüntüsü 2026-06-03 213924" src="https://github.com/user-attachments/assets/303f5dc7-e439-4df6-9f32-9aac179f8242" />

<img width="1860" height="716" alt="Ekran görüntüsü 2026-06-03 213957" src="https://github.com/user-attachments/assets/06289b3d-8c05-4d40-ad4f-7d54597916a4" />

<img width="1907" height="770" alt="Ekran görüntüsü 2026-06-03 214150" src="https://github.com/user-attachments/assets/17c29abc-ce4a-4ee8-be2d-6c0ff890b696" />





