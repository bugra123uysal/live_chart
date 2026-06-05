# live_chart

# 📈 ABD Borsası Canlı Takip

Amerikan borsasındaki hisse senetlerini **gerçek zamanlı** olarak takip etmenizi, teknik analiz yapmanızı ve kendi portföyünüzü yönetmenizi sağlayan bir web uygulaması.

---

## 🚀 Özellikler

- ⚡ **Canlı Fiyat Takibi** — WebSocket bağlantısı ile anlık fiyat ve hacim verileri
- 📊 **RSI Göstergesi** — Aşırı alım/satım bölgelerini otomatik yorumlar
- 📅 **Geçmiş Fiyat Analizi** — 1 ay ile tüm geçmiş arasında seçilebilir zaman aralığı
- 📉 **Hareketli Ortalama** — Özelleştirilebilir MA göstergesi (5–100 gün)
- 💼 **Portföy Yönetimi** — Hisse ekle, kar/zarar takip et, pasta grafik ile dağılımı gör
- 🏢 **Şirket Bilgi Kartı** — Anlık fiyat, F/K oranı, 52 haftalık yüksek/düşük


---

## 🛠️ Kurulum

### 1. Repoyu klonla

```bash
git clone https://github.com/bugra123uysal/live_chart.git
cd live_chart
```

### 2. Gerekli kütüphaneleri yükle

```bash
pip install streamlit pandas plotly websocket-client yfinance streamlit-autorefresh python-dotenv
```

### 3. `.env` dosyası oluştur

Proje klasörüne `.env` adında bir dosya oluştur ve Finnhub API key'ini ekle:

```
FINNHUB_API_KEY=senin_api_keyin
```

> 🔑 Ücretsiz API key almak için: [finnhub.io](https://finnhub.io)

### 4. Uygulamayı çalıştır

```bash
py -m streamlit run borsa_takip_duzenlenmis.py
```

Tarayıcında otomatik olarak `http://localhost:8501` açılacaktır.

---

## 📦 Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|-----------|---------------|
| `Streamlit` | Web arayüzü |
| `yfinance` | Geçmiş fiyat verisi |
| `Finnhub WebSocket` | Canlı fiyat akışı |
| `Plotly` | İnteraktif grafikler |
| `Pandas` | Veri işleme |
| `python-dotenv` | API key güvenliği |

---

## 📌 Desteklenen Hisseler

`AAPL` `TSLA` `GOOGL` `AMZN` `MSFT` `NVDA` `META`

---

## 📁 Proje Yapısı

```
live_chart/
├── borsa_takip_duzenlenmis.py   # Ana uygulama
├── .env                          # API key (GitHub'a gitmez)
├── .gitignore
└── README.md
```



---

## 🖥️ Ekran Görüntüsü

<img width="1906" height="698" alt="Ekran görüntüsü 2026-06-03 213818" src="https://github.com/user-attachments/assets/b5167120-3087-4532-9099-3bdd44f88853" />

<img width="1891" height="683" alt="Ekran görüntüsü 2026-06-03 213846" src="https://github.com/user-attachments/assets/4ee915c9-7cd6-408e-9b58-fde9123f70d2" />

<img width="1874" height="730" alt="Ekran görüntüsü 2026-06-03 213924" src="https://github.com/user-attachments/assets/303f5dc7-e439-4df6-9f32-9aac179f8242" />

<img width="1860" height="716" alt="Ekran görüntüsü 2026-06-03 213957" src="https://github.com/user-attachments/assets/06289b3d-8c05-4d40-ad4f-7d54597916a4" />

<img width="1907" height="770" alt="Ekran görüntüsü 2026-06-03 214150" src="https://github.com/user-attachments/assets/17c29abc-ce4a-4ee8-be2d-6c0ff890b696" />

<img width="1871" height="538" alt="Ekran görüntüsü 2026-06-06 012031" src="https://github.com/user-attachments/assets/347526b2-0d0e-4c31-b833-345cee94f024" />


## 👤 Geliştirici

**Buğra Uysal**  
[GitHub](https://github.com/bugra123uysal)






