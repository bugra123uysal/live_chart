# py -m streamlit run borsa_takip_duzenlenmis.py
# Gerekli kütüphaneler:
# pip install streamlit pandas plotly websocket-client yfinance streamlit-autorefresh

import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
import websocket  # type: ignore
import json
import threading
import yfinance as yf  # type: ignore
from collections import deque
from streamlit_autorefresh import st_autorefresh  # type: ignore

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
FINNHUB_API_KEY = "********************"

# Finnhub'da ABD hisse sembolleri
SYMBOLS = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT", "NVDA", "META"]

st.set_page_config(page_title="ABD Borsası Takip", page_icon="📈", layout="wide")
st.title("📈 ABD Borsası Canlı Takip")

# ─────────────────────────────────────────────
# HIZ İÇİN CACHE FONKSİYONLARI
# ─────────────────────────────────────────────
@st.cache_resource
def get_prices():
    return {s: deque(maxlen=300) for s in SYMBOLS}

@st.cache_data(ttl=60, show_spinner=False)
def get_ticker_info(symbol: str) -> dict:
    """yfinance info yavaş olabilir. 60 saniye cache ile tekrar tekrar çekmiyoruz."""
    try:
        info = yf.Ticker(symbol).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}

@st.cache_data(ttl=120, show_spinner=False)
def get_history(symbol: str, period: str) -> pd.DataFrame:
    """Geçmiş veriyi 2 dakika cache'liyoruz."""
    return yf.download(symbol, period=period, auto_adjust=True, progress=False)

@st.cache_data(ttl=30, show_spinner=False)
def get_last_prices(symbols: tuple[str, ...]) -> dict:
    """Portföy için fiyatları tek tek değil, toplu çekiyoruz. Daha hızlıdır."""
    try:
        data = yf.download(list(symbols), period="1d", interval="1m", progress=False, auto_adjust=True)
        prices = {}

        if data.empty:
            return prices

        if len(symbols) == 1:
            close = data["Close"].dropna()
            if not close.empty:
                prices[symbols[0]] = float(close.iloc[-1])
            return prices

        close_df = data["Close"]
        for symbol in symbols:
            if symbol in close_df.columns:
                s = close_df[symbol].dropna()
                if not s.empty:
                    prices[symbol] = float(s.iloc[-1])
        return prices
    except Exception:
        return {}

all_prices = get_prices()

# ─────────────────────────────────────────────
# HİSSE SEÇİMİ
# ─────────────────────────────────────────────
col_sec, col_info = st.columns([2, 1])
with col_sec:
    my_select = st.selectbox("📊 Hisse Seçiniz", SYMBOLS)
with col_info:
    refresh_speed = st.selectbox("Yenileme Hızı", ["1 sn", "3 sn", "5 sn"], index=1)

prices = all_prices[my_select]

if "active_symbol" not in st.session_state:
    st.session_state.active_symbol = my_select

if st.session_state.active_symbol != my_select:
    st.session_state.active_symbol = my_select

# ─────────────────────────────────────────────
# WEBSOCKET FONKSİYONLARI
# ─────────────────────────────────────────────
def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "trade":
        for trade in data["data"]:
            symbol = trade["s"]
            if symbol in all_prices:
                all_prices[symbol].append({
                    "symbol": symbol,
                    "price": trade["p"],
                    "timestamp": pd.to_datetime(trade["t"], unit="ms"),
                    "volume": trade["v"]
                })

def on_open(ws):
    for symbol in SYMBOLS:
        ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))

def start_websocket():
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

if "started" not in st.session_state:
    thread = threading.Thread(target=start_websocket, daemon=True)
    thread.start()
    st.session_state.started = True

# ─────────────────────────────────────────────
# BÖLÜM 1: HİSSE DETAY KARTI
# ─────────────────────────────────────────────
st.subheader(f"🏢 {my_select} Hisse Bilgileri")

info = get_ticker_info(my_select)

try:
    d1, d2, d3, d4, d5 = st.columns(5)
    with d1:
        fiyat = info.get("currentPrice") or info.get("regularMarketPrice") or "—"
        st.metric("Anlık Fiyat", f"${fiyat}" if fiyat != "—" else "—")
    with d2:
        degisim = info.get("regularMarketChangePercent")
        if isinstance(degisim, (int, float)):
            st.metric("Günlük Değişim", f"%{degisim:.2f}", delta=f"{degisim:.2f}%")
        else:
            st.metric("Günlük Değişim", "—")
    with d3:
        pe = info.get("trailingPE", "—")
        pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else str(pe)
        st.metric("F/K Oranı", pe_str)
    with d4:
        yuksek = info.get("fiftyTwoWeekHigh", "—")
        st.metric("52 Hafta Yüksek", f"${yuksek}" if yuksek != "—" else "—")
    with d5:
        dusuk = info.get("fiftyTwoWeekLow", "—")
        st.metric("52 Hafta Düşük", f"${dusuk}" if dusuk != "—" else "—")

    aciklama = info.get("longBusinessSummary", "")
    if aciklama:
        with st.expander("📖 Şirket Hakkında"):
            st.write(aciklama[:500] + "...")
except Exception as e:
    st.warning(f"Hisse bilgisi gösterilemedi: {e}")

st.divider()

# ─────────────────────────────────────────────
# BÖLÜM 2: CANLI FİYAT GRAFİĞİ
# ─────────────────────────────────────────────
st.subheader("⚡ Canlı Fiyat Grafiği")

if len(prices) > 0:
    df = pd.DataFrame(list(prices))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["price"],
        mode="lines",
        name="Fiyat"
    ))
    fig.update_layout(
        title=f"{my_select} Canlı Fiyat",
        xaxis_title="Zaman",
        yaxis_title="Fiyat ($)",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_vol = px.bar(
        df,
        x="timestamp",
        y="volume",
        title=f"{my_select} İşlem Hacmi"
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    son = df.iloc[-1]
    st.info(f"Son fiyat: **${son['price']:.2f}** — {son['timestamp'].strftime('%H:%M:%S')}")
else:
    st.info("⏳ Lütfen bekleyiniz, canlı veriler yükleniyor...")

interval_map = {"1 sn": 1000, "3 sn": 3000, "5 sn": 5000}
st_autorefresh(interval=interval_map[refresh_speed], key="refresh")

st.divider()

# ─────────────────────────────────────────────
# BÖLÜM 3: GEÇMİŞ FİYAT + TEKNİK GÖSTERGELER
# ─────────────────────────────────────────────
st.subheader("📅 Geçmiş Fiyat Analizi")

col_zaman, col_ma = st.columns(2)
with col_zaman:
    donemler = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
    zaman = st.selectbox("Zaman Aralığı", donemler, index=3)
with col_ma:
    ma_gun = st.slider("Hareketli Ortalama (Gün)", min_value=5, max_value=100, value=20, step=5)

try:
    cek = get_history(my_select, zaman)

    if not cek.empty:
        cek["MA"] = cek["Close"].rolling(window=ma_gun).mean()

        fig_tarih = go.Figure()
        fig_tarih.add_trace(go.Scatter(
            x=cek.index,
            y=cek["Close"].squeeze(),
            name="Kapanış Fiyatı"
        ))
        fig_tarih.add_trace(go.Scatter(
            x=cek.index,
            y=cek["MA"].squeeze(),
            name=f"{ma_gun} Günlük Ortalama"
        ))
        fig_tarih.update_layout(
            title=f"{my_select} — {zaman} Geçmiş Fiyat",
            xaxis_title="Tarih",
            yaxis_title="Fiyat ($)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_tarih, use_container_width=True)

        s1, s2, s3, s4 = st.columns(4)
        close_series = cek["Close"].squeeze()
        with s1:
            st.metric("Dönem Başlangıcı", f"${float(close_series.iloc[0]):.2f}")
        with s2:
            st.metric("Dönem Sonu", f"${float(close_series.iloc[-1]):.2f}")
        with s3:
            yuzde = ((float(close_series.iloc[-1]) - float(close_series.iloc[0])) / float(close_series.iloc[0])) * 100
            st.metric("Toplam Değişim", f"%{yuzde:.1f}", delta=f"{yuzde:.1f}%")
        with s4:
            volatilite = float(close_series.pct_change().std() * 100)
            st.metric("Günlük Volatilite", f"%{volatilite:.2f}")
    else:
        st.warning("Geçmiş veri bulunamadı.")
except Exception as e:
    st.error(f"Geçmiş veri alınamadı: {e}")

st.divider()

# ─────────────────────────────────────────────
# GEMINI / AI BÖLÜMÜ KAPATILDI
# ─────────────────────────────────────────────
# Bu bölüm kapatıldı. Böylece google/genai paketi, Gemini API anahtarı ve API isteği gerekmez.

# ─────────────────────────────────────────────
# BÖLÜM 4: PORTFÖY YÖNETİMİ
# ─────────────────────────────────────────────
st.title("💼 Portföyüm")

if "portfoy" not in st.session_state:
    st.session_state.portfoy = []

left, right = st.columns([1, 2])

with left:
    st.subheader("➕ Hisse Ekle")
    h_sec = st.selectbox("Hisse Seçin", SYMBOLS, key="portfoy_sec")
    adet = st.number_input("Adet", min_value=1, step=1, key="portfoy_adet")
    alis_fiyati = st.number_input("Alış Fiyatı ($)", min_value=0.01, step=0.01, key="alis_fiyat")

    ekle = st.button("📥 Portföye Ekle", use_container_width=True)

    if ekle:
        st.session_state.portfoy.append({
            "Hisse": h_sec,
            "Adet": int(adet),
            "Alış ($)": float(alis_fiyati),
        })
        st.success(f"✅ {h_sec} portföye eklendi!")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Fiyatları Yenile", use_container_width=True):
            get_last_prices.clear()
            st.rerun()
    with c2:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.portfoy = []
            st.rerun()

with right:
    if st.session_state.portfoy:
        df_portfoy = pd.DataFrame(st.session_state.portfoy)

        # Aynı hisse birden fazla kez eklenirse tek satırda topluyoruz.
        df_portfoy = (
            df_portfoy
            .groupby("Hisse", as_index=False)
            .agg({"Adet": "sum", "Alış ($)": "mean"})
        )

        mevcut_hisseler = tuple(df_portfoy["Hisse"].unique())
        son_fiyatlar = get_last_prices(mevcut_hisseler)

        # Eğer websocket'ten daha güncel fiyat geldiyse onu kullan.
        for symbol in mevcut_hisseler:
            if len(all_prices[symbol]) > 0:
                son_fiyatlar[symbol] = float(all_prices[symbol][-1]["price"])

        df_portfoy["Güncel ($)"] = df_portfoy["Hisse"].map(son_fiyatlar).fillna(0)
        df_portfoy["Maliyet"] = df_portfoy["Adet"] * df_portfoy["Alış ($)"]
        df_portfoy["Toplam Değer"] = df_portfoy["Adet"] * df_portfoy["Güncel ($)"]
        df_portfoy["Kar/Zarar ($)"] = df_portfoy["Toplam Değer"] - df_portfoy["Maliyet"]
        df_portfoy["Kar/Zarar (%)"] = (df_portfoy["Kar/Zarar ($)"] / df_portfoy["Maliyet"]) * 100

        df_goster = df_portfoy.copy()
        sayisal_kolonlar = ["Alış ($)", "Güncel ($)", "Maliyet", "Toplam Değer", "Kar/Zarar ($)", "Kar/Zarar (%)"]
        df_goster[sayisal_kolonlar] = df_goster[sayisal_kolonlar].round(2)

        st.subheader("📊 Portföy Tablosu")

        def renk_ver(val):
            return "color: green" if val >= 0 else "color: red"

        styled = df_goster.style.map(
            renk_ver,
            subset=["Kar/Zarar ($)", "Kar/Zarar (%)"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        toplam_deger = df_portfoy["Toplam Değer"].sum()
        toplam_maliyet = df_portfoy["Maliyet"].sum()
        toplam_kar = toplam_deger - toplam_maliyet
        toplam_kar_yuzde = (toplam_kar / toplam_maliyet * 100) if toplam_maliyet > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Toplam Değer", f"${toplam_deger:,.2f}")
        with m2:
            st.metric("Toplam Maliyet", f"${toplam_maliyet:,.2f}")
        with m3:
            st.metric("Toplam Kar/Zarar", f"${toplam_kar:,.2f}", delta=f"{toplam_kar_yuzde:.2f}%")
        with m4:
            st.metric("Pozisyon Sayısı", len(df_portfoy))

        fig_pie = px.pie(
            df_portfoy,
            names="Hisse",
            values="Toplam Değer",
            title="Portföy Dağılımı"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        fig_kar = go.Figure(go.Bar(
            x=df_portfoy["Hisse"],
            y=df_portfoy["Kar/Zarar ($)"],
            text=[f"${k:+.2f}" for k in df_portfoy["Kar/Zarar ($)"]],
            textposition="auto"
        ))
        fig_kar.update_layout(
            title="Kar / Zarar Karşılaştırması",
            xaxis_title="Hisse",
            yaxis_title="Kar/Zarar ($)"
        )
        st.plotly_chart(fig_kar, use_container_width=True)
    else:
        st.info("Henüz portföy oluşturmadınız. Sol taraftan hisse ekleyin!")
