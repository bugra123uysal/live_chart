
import streamlit as st
import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots 
import websocket 
import json
import threading
import yfinance as yf 
from collections import deque
from streamlit_autorefresh import st_autorefresh
import os
from dotenv import load_dotenv 
import numpy as np 
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# SAYFA YAPISI
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ABD Borsası Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# ÖZEL CSS — Profesyonel görünüm
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Genel */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    /* Metrik kartları */
    [data-testid="metric-container"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 18px;
    }
    [data-testid="metric-container"] label {
        font-size: 11px !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #64748b !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
    }
    [data-testid="stMetricDelta"] svg { display: none; }

    /* Başlık bantları */
    .section-header {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        border-left: 3px solid #3b82f6;
        padding: 8px 16px;
        border-radius: 0 6px 6px 0;
        margin: 10px 0 16px;
        color: #e2e8f0;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    /* Pozitif / Negatif renkler */
    .pos { color: #22c55e !important; }
    .neg { color: #ef4444 !important; }
    .neutral { color: #94a3b8 !important; }

    /* Sinyal kartı */
    .signal-card {
        border-radius: 10px;
        padding: 14px;
        margin: 6px 0;
        font-size: 13px;
        font-weight: 600;
    }
    .signal-buy { background: #052e16; border: 1px solid #166534; color: #86efac; }
    .signal-sell { background: #450a0a; border: 1px solid #991b1b; color: #fca5a5; }
    .signal-hold { background: #172554; border: 1px solid #1e40af; color: #93c5fd; }

    /* Değerleme tablosu */
    .val-table { width: 100%; font-size: 13px; border-collapse: collapse; }
    .val-table td { padding: 8px 12px; border-bottom: 1px solid #1e293b; }
    .val-table td:first-child { color: #64748b; width: 55%; }
    .val-table td:last-child { text-align: right; color: #e2e8f0; font-weight: 600; }
    .val-table tr:last-child td { border-bottom: none; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #080f1e;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p {
        font-size: 12px;
        color: #475569;
    }

    /* Dataframe */
    [data-testid="stDataFrameContainer"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# AYARLAR & SABITLER
# ─────────────────────────────────────────────
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

SYMBOLS = ["AAPL", "TSLA", "GOOGL", "AMZN", "MSFT", "NVDA", "META"]
BENCHMARK_SYMBOLS = {
    "S&P 500": "^GSPC",
    "NASDAQ 100 (QQQ)": "QQQ",
    "Dow Jones": "^DJI",
}

PLOTLY_TEMPLATE = "plotly_dark"

# ─────────────────────────────────────────────
# HESAPLAMA FONKSİYONLARI
# ─────────────────────────────────────────────
def hesapla_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def hesapla_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def hesapla_bollinger(close: pd.Series, period: int = 20, std_dev: float = 2):
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return ma + std_dev * std, ma, ma - std_dev * std

def hesapla_stokastik(high: pd.Series, low: pd.Series, close: pd.Series, k_period=14, d_period=3):
    low_min = low.rolling(k_period).min()
    high_max = high.rolling(k_period).max()
    k = 100 * (close - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def sinyal_uret(rsi_val, macd_line_val, macd_signal_val, close_val, bb_upper, bb_lower) -> tuple[str, list[str]]:
    """Basit teknik analiz sinyali üretir. Yatırım tavsiyesi değildir."""
    buy_signals, sell_signals = [], []
    if rsi_val < 30:
        buy_signals.append(f"RSI aşırı satım bölgesinde ({rsi_val:.1f})")
    if rsi_val > 70:
        sell_signals.append(f"RSI aşırı alım bölgesinde ({rsi_val:.1f})")
    if macd_line_val > macd_signal_val:
        buy_signals.append("MACD sinyal çizgisinin üzerinde")
    else:
        sell_signals.append("MACD sinyal çizgisinin altında")
    if close_val < bb_lower:
        buy_signals.append("Fiyat alt Bollinger bandının altında")
    if close_val > bb_upper:
        sell_signals.append("Fiyat üst Bollinger bandının üzerinde")

    if len(buy_signals) > len(sell_signals):
        return "AL", buy_signals
    elif len(sell_signals) > len(buy_signals):
        return "SAT", sell_signals
    return "BEKLE", buy_signals + sell_signals

# ─────────────────────────────────────────────
# CACHE FONKSİYONLARI
# ─────────────────────────────────────────────
@st.cache_resource
def get_prices():
    return {s: deque(maxlen=300) for s in SYMBOLS}

@st.cache_data(ttl=60, show_spinner=False)
def get_ticker_info(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}

@st.cache_data(ttl=120, show_spinner=False)
def get_history(symbol: str, period: str) -> pd.DataFrame:
    return yf.download(symbol, period=period, auto_adjust=True, progress=False)

@st.cache_data(ttl=120, show_spinner=False)
def get_benchmark_history(period: str) -> dict:
    """Benchmark endekslerini çeker."""
    result = {}
    for name, sym in BENCHMARK_SYMBOLS.items():
        try:
            df = yf.download(sym, period=period, auto_adjust=True, progress=False)
            if not df.empty:
                result[name] = df["Close"].squeeze()
        except Exception:
            pass
    return result

@st.cache_data(ttl=30, show_spinner=False)
def get_last_prices(symbols: tuple) -> dict:
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
# WEBSOCKET
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
    if not FINNHUB_API_KEY:
        return
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

if "ws_started" not in st.session_state and FINNHUB_API_KEY:
    thread = threading.Thread(target=start_websocket, daemon=True)
    thread.start()
    st.session_state.ws_started = True

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Kontrol Paneli")
    st.divider()

    my_select = st.selectbox("📊 Hisse Seçiniz", SYMBOLS)
    refresh_speed = st.selectbox("🔄 Yenileme Hızı", ["1 sn", "3 sn", "5 sn", "10 sn"], index=1)
    st.divider()

    st.markdown("### 📅 Dönem Seçimi")
    donemler = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
    zaman = st.selectbox("Zaman Aralığı", donemler, index=3)

    st.markdown("### 📐 İndikatör Ayarları")
    ma_gun = st.slider("Hareketli Ortalama (Gün)", min_value=5, max_value=200, value=20, step=5)
    bb_std = st.slider("Bollinger Bant Std. Sapma", min_value=1.0, max_value=3.0, value=2.0, step=0.5)
    rsi_period = st.slider("RSI Periyot", min_value=7, max_value=21, value=14)

    st.divider()

    # Sekme seçimi
    st.markdown("### 📑 Görünüm")
    aktif_sekme = st.radio("", ["Hisse Detayı", "Teknik Analiz", "Değerleme", "Portföy", "Benchmark", "🎯 Swing Trade"])

    st.divider()
    st.markdown("""
    <p>⚠️ Bu uygulama yalnızca eğitim amaçlıdır. Yatırım tavsiyesi değildir.</p>
    """, unsafe_allow_html=True)

interval_map = {"1 sn": 1000, "3 sn": 3000, "5 sn": 5000, "10 sn": 10000}
st_autorefresh(interval=interval_map[refresh_speed], key="refresh")

prices = all_prices[my_select]
info = get_ticker_info(my_select)

# ─────────────────────────────────────────────
# ANA BAŞLIK
# ─────────────────────────────────────────────
col_title, col_time = st.columns([4, 1])
with col_title:
    sektör = info.get("sector", "")
    sektör_str = f" · {sektör}" if sektör else ""
    st.markdown(f"# 📈 ABD Borsası Pro — {my_select}{sektör_str}")
with col_time:
    st.markdown(f"<p style='text-align:right; color:#475569; padding-top:14px; font-size:12px;'>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ÜST METRİKLER — Her sekmede görünür
# ─────────────────────────────────────────────
fiyat   = info.get("currentPrice") or info.get("regularMarketPrice") or 0
degisim = info.get("regularMarketChangePercent") or 0
yuksek  = info.get("fiftyTwoWeekHigh", "—")
dusuk   = info.get("fiftyTwoWeekLow", "—")
hacim   = info.get("volume") or info.get("regularMarketVolume") or 0
piyasa_deger = info.get("marketCap", 0)

# Canlı fiyat varsa onu kullan
if len(prices) > 0:
    fiyat = prices[-1]["price"]

m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    st.metric("Anlık Fiyat", f"${fiyat:.2f}" if fiyat else "—",
              delta=f"{degisim:+.2f}%" if degisim else None)
with m2:
    pe = info.get("trailingPE")
    st.metric("F/K (P/E)", f"{pe:.1f}x" if isinstance(pe, float) else "—")
with m3:
    ps = info.get("priceToSalesTrailing12Months")
    st.metric("F/S (P/S)", f"{ps:.2f}x" if isinstance(ps, float) else "—")
with m4:
    pb = info.get("priceToBook")
    st.metric("F/DD (P/B)", f"{pb:.2f}x" if isinstance(pb, float) else "—")
with m5:
    st.metric("52H Yüksek", f"${yuksek}" if isinstance(yuksek, (int, float)) else "—")
with m6:
    mc_str = f"${piyasa_deger/1e9:.1f}B" if piyasa_deger and piyasa_deger > 1e9 else (f"${piyasa_deger/1e6:.0f}M" if piyasa_deger else "—")
    st.metric("Piyasa Değeri", mc_str)

st.divider()

# ═══════════════════════════════════════════════════════
# SEKME: HİSSE DETAYI
# ═══════════════════════════════════════════════════════
if aktif_sekme == "Hisse Detayı":

    st.markdown('<div class="section-header">⚡ Canlı Fiyat Akışı</div>', unsafe_allow_html=True)

    if len(prices) > 1:
        df_live = pd.DataFrame(list(prices))
        fig_live = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 row_heights=[0.7, 0.3],
                                 vertical_spacing=0.04)
        # Fiyat çizgisi + gradient fill
        fig_live.add_trace(go.Scatter(
            x=df_live["timestamp"], y=df_live["price"],
            mode="lines", name="Fiyat",
            line=dict(color="#3b82f6", width=2),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.08)"
        ), row=1, col=1)

        # Son fiyat noktası
        fig_live.add_trace(go.Scatter(
            x=[df_live["timestamp"].iloc[-1]], y=[df_live["price"].iloc[-1]],
            mode="markers", showlegend=False,
            marker=dict(size=8, color="#60a5fa", line=dict(width=2, color="#1d4ed8"))
        ), row=1, col=1)

        # Hacim
        fig_live.add_trace(go.Bar(
            x=df_live["timestamp"], y=df_live["volume"],
            name="Hacim", marker_color="rgba(99,102,241,0.5)"
        ), row=2, col=1)

        fig_live.update_layout(
            template=PLOTLY_TEMPLATE, height=440,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis2_title="Zaman",
        )
        fig_live.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
        fig_live.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        st.plotly_chart(fig_live, use_container_width=True)
        son = df_live.iloc[-1]
        st.caption(f"Son güncelleme: ${son['price']:.2f} — {son['timestamp'].strftime('%H:%M:%S')} UTC")
    else:
        st.info("⏳ Canlı veriler yükleniyor... (Finnhub API anahtarını .env dosyasına ekleyin)")

    # Şirket bilgisi
    st.markdown('<div class="section-header">🏢 Şirket Bilgisi</div>', unsafe_allow_html=True)
    col_info1, col_info2 = st.columns([3, 2])
    with col_info1:
        aciklama = info.get("longBusinessSummary", "Bilgi bulunamadı.")
        st.markdown(f"<p style='color:#94a3b8; font-size:13px; line-height:1.7;'>{aciklama[:600]}{'...' if len(aciklama) > 600 else ''}</p>", unsafe_allow_html=True)
    with col_info2:
        fields = {
            "Sektör": info.get("sector", "—"),
            "Endüstri": info.get("industry", "—"),
            "Ülke": info.get("country", "—"),
            "Çalışan Sayısı": f"{info.get('fullTimeEmployees', 0):,}" if info.get("fullTimeEmployees") else "—",
            "Web Sitesi": info.get("website", "—"),
        }
        rows_html = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in fields.items()])
        st.markdown(f'<table class="val-table">{rows_html}</table>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# SEKME: TEKNİK ANALİZ
# ═══════════════════════════════════════════════════════
elif aktif_sekme == "Teknik Analiz":

    try:
        cek = get_history(my_select, zaman)
        if cek.empty:
            st.warning("Geçmiş veri bulunamadı.")
            st.stop()

        close_s = cek["Close"].squeeze()
        high_s  = cek["High"].squeeze()
        low_s   = cek["Low"].squeeze()
        volume_s = cek["Volume"].squeeze()

        # İndikatörler
        cek["MA"]          = close_s.rolling(window=ma_gun).mean()
        cek["EMA20"]       = close_s.ewm(span=20).mean()
        cek["RSI"]         = hesapla_rsi(close_s, rsi_period)
        macd_l, macd_sig, macd_hist = hesapla_macd(close_s)
        bb_up, bb_mid, bb_low = hesapla_bollinger(close_s, std_dev=bb_std)
        stoch_k, stoch_d  = hesapla_stokastik(high_s, low_s, close_s)

        # ── Sinyal üretimi
        last_rsi   = float(cek["RSI"].dropna().iloc[-1])
        last_macdl = float(macd_l.dropna().iloc[-1])
        last_macds = float(macd_sig.dropna().iloc[-1])
        last_close = float(close_s.iloc[-1])
        last_bbup  = float(bb_up.dropna().iloc[-1])
        last_bblow = float(bb_low.dropna().iloc[-1])

        sinyal, sinyal_aciklama = sinyal_uret(last_rsi, last_macdl, last_macds, last_close, last_bbup, last_bblow)

        col_sig, col_rsi_val, col_macd_val, col_stoch_val = st.columns(4)
        sinyal_css = {"AL": "signal-buy", "SAT": "signal-sell", "BEKLE": "signal-hold"}[sinyal]
        sinyal_emoji = {"AL": "🟢", "SAT": "🔴", "BEKLE": "🟡"}[sinyal]
        with col_sig:
            st.markdown(f'<div class="signal-card {sinyal_css}">{sinyal_emoji} Teknik Sinyal: {sinyal}<br><small style="font-weight:400">{" · ".join(sinyal_aciklama[:2])}</small></div>', unsafe_allow_html=True)
        with col_rsi_val:
            rsi_color = "#ef4444" if last_rsi > 70 else ("#22c55e" if last_rsi < 30 else "#94a3b8")
            st.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:14px"><span style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#64748b">RSI ({rsi_period})</span><br><span style="font-size:22px;font-weight:700;color:{rsi_color}">{last_rsi:.1f}</span></div>', unsafe_allow_html=True)
        with col_macd_val:
            macd_diff = last_macdl - last_macds
            macd_color = "#22c55e" if macd_diff > 0 else "#ef4444"
            st.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:14px"><span style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#64748b">MACD Farkı</span><br><span style="font-size:22px;font-weight:700;color:{macd_color}">{macd_diff:+.2f}</span></div>', unsafe_allow_html=True)
        with col_stoch_val:
            last_stk = float(stoch_k.dropna().iloc[-1])
            stoch_color = "#ef4444" if last_stk > 80 else ("#22c55e" if last_stk < 20 else "#94a3b8")
            st.markdown(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:14px"><span style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#64748b">Stokastik %K</span><br><span style="font-size:22px;font-weight:700;color:{stoch_color}">{last_stk:.1f}</span></div>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Fiyat + Bollinger + MA grafiği
        st.markdown('<div class="section-header">📊 Fiyat & Bollinger Bantları</div>', unsafe_allow_html=True)
        fig_main = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                 row_heights=[0.45, 0.2, 0.2, 0.15],
                                 vertical_spacing=0.03,
                                 subplot_titles=["Fiyat & Bantlar", "MACD", "RSI", "Hacim"])

        # Mum grafiği
        fig_main.add_trace(go.Candlestick(
            x=cek.index,
            open=cek["Open"].squeeze(), high=high_s,
            low=low_s, close=close_s,
            name="OHLC",
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
            increasing_fillcolor="#166534",
            decreasing_fillcolor="#7f1d1d",
        ), row=1, col=1)

        # Bollinger bantları
        fig_main.add_trace(go.Scatter(x=cek.index, y=bb_up, name="BB Üst",
            line=dict(color="#6366f1", width=1, dash="dot"), showlegend=True), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=cek.index, y=bb_mid, name="BB Orta",
            line=dict(color="#94a3b8", width=1), showlegend=True), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=cek.index, y=bb_low, name="BB Alt",
            line=dict(color="#6366f1", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(99,102,241,0.05)",
            showlegend=False), row=1, col=1)

        # MA & EMA
        fig_main.add_trace(go.Scatter(x=cek.index, y=cek["MA"].squeeze(),
            name=f"SMA {ma_gun}", line=dict(color="#f59e0b", width=1.5)), row=1, col=1)
        fig_main.add_trace(go.Scatter(x=cek.index, y=cek["EMA20"].squeeze(),
            name="EMA 20", line=dict(color="#ec4899", width=1.5, dash="dash")), row=1, col=1)

        # MACD
        colors_hist = ["#22c55e" if v >= 0 else "#ef4444" for v in macd_hist]
        fig_main.add_trace(go.Bar(x=cek.index, y=macd_hist, name="MACD Hist",
            marker_color=colors_hist, showlegend=False), row=2, col=1)
        fig_main.add_trace(go.Scatter(x=cek.index, y=macd_l, name="MACD",
            line=dict(color="#3b82f6", width=1.5), showlegend=False), row=2, col=1)
        fig_main.add_trace(go.Scatter(x=cek.index, y=macd_sig, name="Sinyal",
            line=dict(color="#f59e0b", width=1.5), showlegend=False), row=2, col=1)

        # RSI
        fig_main.add_trace(go.Scatter(x=cek.index, y=cek["RSI"].squeeze(), name="RSI",
            line=dict(color="#a78bfa", width=1.5), showlegend=False), row=3, col=1)
        fig_main.add_hline(y=70, line_dash="dash", line_color="#ef4444", line_width=1, row=3, col=1)
        fig_main.add_hline(y=30, line_dash="dash", line_color="#22c55e", line_width=1, row=3, col=1)
        fig_main.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.05)", line_width=0, row=3, col=1)
        fig_main.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.05)", line_width=0, row=3, col=1)

        # Hacim
        vol_colors = ["#22c55e" if close_s.iloc[i] >= close_s.iloc[i-1] else "#ef4444"
                      for i in range(1, len(close_s))]
        vol_colors.insert(0, "#94a3b8")
        fig_main.add_trace(go.Bar(x=cek.index, y=volume_s, name="Hacim",
            marker_color=vol_colors, showlegend=False), row=4, col=1)

        fig_main.update_layout(
            template=PLOTLY_TEMPLATE, height=900,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", y=1.01, x=0),
            xaxis_rangeslider_visible=False,
        )
        fig_main.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
        fig_main.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
        st.plotly_chart(fig_main, use_container_width=True)

        # ── Stokastik ayrı
        st.markdown('<div class="section-header">📊 Stokastik Osilatör</div>', unsafe_allow_html=True)
        fig_stoch = go.Figure()
        fig_stoch.add_trace(go.Scatter(x=cek.index, y=stoch_k, name="%K",
            line=dict(color="#60a5fa", width=1.5)))
        fig_stoch.add_trace(go.Scatter(x=cek.index, y=stoch_d, name="%D",
            line=dict(color="#f59e0b", width=1.5)))
        fig_stoch.add_hline(y=80, line_dash="dash", line_color="#ef4444", line_width=1)
        fig_stoch.add_hline(y=20, line_dash="dash", line_color="#22c55e", line_width=1)
        fig_stoch.add_hrect(y0=80, y1=100, fillcolor="rgba(239,68,68,0.05)", line_width=0)
        fig_stoch.add_hrect(y0=0, y1=20, fillcolor="rgba(34,197,94,0.05)", line_width=0)
        fig_stoch.update_layout(
            template=PLOTLY_TEMPLATE, height=250,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(range=[0, 100]),
        )
        st.plotly_chart(fig_stoch, use_container_width=True)

        # ── İstatistik özeti
        st.markdown('<div class="section-header">📋 Dönem İstatistikleri</div>', unsafe_allow_html=True)
        s1, s2, s3, s4, s5 = st.columns(5)
        with s1:
            st.metric("Dönem Başlangıcı", f"${float(close_s.iloc[0]):.2f}")
        with s2:
            st.metric("Dönem Sonu", f"${float(close_s.iloc[-1]):.2f}")
        with s3:
            yuzde = ((float(close_s.iloc[-1]) - float(close_s.iloc[0])) / float(close_s.iloc[0])) * 100
            st.metric("Toplam Değişim", f"%{yuzde:.1f}", delta=f"{yuzde:.1f}%")
        with s4:
            volatilite = float(close_s.pct_change().std() * 100 * np.sqrt(252))
            st.metric("Yıllık Volatilite", f"%{volatilite:.1f}")
        with s5:
            sharpe = (float(close_s.pct_change().mean()) * 252) / (float(close_s.pct_change().std()) * np.sqrt(252))
            st.metric("Sharpe Oranı*", f"{sharpe:.2f}", help="*Risk-free rate = 0 varsayımıyla")

    except Exception as e:
        st.error(f"Teknik analiz hesaplanamadı: {e}")

# ═══════════════════════════════════════════════════════
# SEKME: DEĞERLEME (F/K, F/S, F/DD vb.)
# ═══════════════════════════════════════════════════════
elif aktif_sekme == "Değerleme":

    st.markdown('<div class="section-header">💹 Temel Analiz & Değerleme Çarpanları</div>', unsafe_allow_html=True)

    col_val1, col_val2 = st.columns(2)

    with col_val1:
        st.markdown("#### 📐 Değerleme Çarpanları")
        metrics = {
            "F/K Oranı (Trailing P/E)":   ("trailingPE", "x"),
            "F/K Oranı (Forward P/E)":    ("forwardPE", "x"),
            "F/S Oranı (P/S)":            ("priceToSalesTrailing12Months", "x"),
            "F/DD Oranı (P/B)":           ("priceToBook", "x"),
            "EV/FAVÖK (EV/EBITDA)":       ("enterpriseToEbitda", "x"),
            "EV/Gelir":                   ("enterpriseToRevenue", "x"),
            "PEG Oranı":                  ("pegRatio", "x"),
        }
        rows_html = ""
        for label, (key, suffix) in metrics.items():
            val = info.get(key)
            val_str = f"{val:.2f}{suffix}" if isinstance(val, (int, float)) else "—"
            rows_html += f"<tr><td>{label}</td><td>{val_str}</td></tr>"
        st.markdown(f'<table class="val-table">{rows_html}</table>', unsafe_allow_html=True)

    with col_val2:
        st.markdown("#### 💰 Karlılık & Büyüme")
        fin_metrics = {
            "Brüt Kar Marjı":         ("grossMargins", "%"),
            "FAVÖK Marjı":            ("ebitdaMargins", "%"),
            "Net Kar Marjı":          ("profitMargins", "%"),
            "ROE (Öz Kaynak Karlılığı)": ("returnOnEquity", "%"),
            "ROA (Aktif Karlılığı)":  ("returnOnAssets", "%"),
            "Gelir Büyüme (YoY)":     ("revenueGrowth", "%"),
            "Kazanç Büyüme (YoY)":    ("earningsGrowth", "%"),
        }
        rows_html2 = ""
        for label, (key, suffix) in fin_metrics.items():
            val = info.get(key)
            if isinstance(val, (int, float)):
                val_pct = val * 100
                color_class = "pos" if val_pct > 0 else "neg"
                val_str = f'<span class="{color_class}">{val_pct:.1f}%</span>'
            else:
                val_str = "—"
            rows_html2 += f"<tr><td>{label}</td><td>{val_str}</td></tr>"
        st.markdown(f'<table class="val-table">{rows_html2}</table>', unsafe_allow_html=True)

    st.markdown("---")

    col_val3, col_val4 = st.columns(2)

    with col_val3:
        st.markdown("#### 📊 Bilanço Verileri")
        balance_metrics = {
            "Toplam Nakit":          ("totalCash", "$"),
            "Hisse Başı Nakit":      ("totalCashPerShare", "$"),
            "Toplam Borç":           ("totalDebt", "$"),
            "D/E Oranı":             ("debtToEquity", ""),
            "Cari Oran":             ("currentRatio", "x"),
            "Hızlı Oran":            ("quickRatio", "x"),
        }
        rows_html3 = ""
        for label, (key, suffix) in balance_metrics.items():
            val = info.get(key)
            if isinstance(val, (int, float)):
                if suffix == "$" and val > 1e9:
                    val_str = f"${val/1e9:.2f}B"
                elif suffix == "$" and val > 1e6:
                    val_str = f"${val/1e6:.1f}M"
                elif suffix == "$":
                    val_str = f"${val:.2f}"
                else:
                    val_str = f"{val:.2f}{suffix}"
            else:
                val_str = "—"
            rows_html3 += f"<tr><td>{label}</td><td>{val_str}</td></tr>"
        st.markdown(f'<table class="val-table">{rows_html3}</table>', unsafe_allow_html=True)

    with col_val4:
        st.markdown("#### 🎯 Analist & Temettü")
        analyst_metrics = {
            "Hedef Fiyat (Ortalama)": ("targetMeanPrice", "$"),
            "Hedef Fiyat (Yüksek)":  ("targetHighPrice", "$"),
            "Hedef Fiyat (Düşük)":   ("targetLowPrice", "$"),
            "Analist Tavsiyesi":      ("recommendationKey", ""),
            "Temettü Verimi":         ("dividendYield", "%"),
            "Ödeme Oranı":            ("payoutRatio", "%"),
            "Beta":                   ("beta", ""),
        }
        rows_html4 = ""
        for label, (key, suffix) in analyst_metrics.items():
            val = info.get(key)
            if val is None:
                val_str = "—"
            elif key == "recommendationKey":
                tavsiye_map = {"buy": "🟢 Al", "strong_buy": "🟢 Güçlü Al",
                               "hold": "🟡 Tut", "sell": "🔴 Sat",
                               "underperform": "🔴 Düşük Performans"}
                val_str = tavsiye_map.get(str(val).lower(), str(val).title())
            elif suffix == "%" and isinstance(val, float):
                val_str = f"{val*100:.2f}%"
            elif suffix == "$" and isinstance(val, (int, float)):
                val_str = f"${val:.2f}"
            else:
                val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            rows_html4 += f"<tr><td>{label}</td><td>{val_str}</td></tr>"
        st.markdown(f'<table class="val-table">{rows_html4}</table>', unsafe_allow_html=True)

    # Hedef fiyat görselleştirmesi
    tp_low  = info.get("targetLowPrice")
    tp_mean = info.get("targetMeanPrice")
    tp_high = info.get("targetHighPrice")
    if tp_low and tp_mean and tp_high and fiyat:
        st.markdown('<div class="section-header">🎯 Analist Hedef Fiyat Aralığı</div>', unsafe_allow_html=True)
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=fiyat,
            delta={"reference": tp_mean, "relative": False,
                   "valueformat": ".2f",
                   "increasing": {"color": "#22c55e"},
                   "decreasing": {"color": "#ef4444"}},
            number={"prefix": "$", "valueformat": ".2f"},
            gauge={
                "axis": {"range": [tp_low * 0.85, tp_high * 1.05],
                         "tickprefix": "$", "tickformat": ".0f"},
                "bar": {"color": "#3b82f6", "thickness": 0.3},
                "steps": [
                    {"range": [tp_low * 0.85, tp_low], "color": "rgba(239,68,68,0.3)"},
                    {"range": [tp_low, tp_mean], "color": "rgba(34,197,94,0.15)"},
                    {"range": [tp_mean, tp_high], "color": "rgba(34,197,94,0.3)"},
                    {"range": [tp_high, tp_high * 1.05], "color": "rgba(239,68,68,0.15)"},
                ],
                "threshold": {"line": {"color": "#f59e0b", "width": 3},
                              "thickness": 0.75, "value": tp_mean},
            },
            title={"text": f"Mevcut Fiyat vs Analist Hedefi (Ort: ${tp_mean:.2f})"},
        ))
        fig_tp.update_layout(
            template=PLOTLY_TEMPLATE, height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=40, b=20),
        )
        st.plotly_chart(fig_tp, use_container_width=True)

# ═══════════════════════════════════════════════════════
# SEKME: PORTFÖY
# ═══════════════════════════════════════════════════════
elif aktif_sekme == "Portföy":

    st.markdown('<div class="section-header">💼 Portföy Yönetimi</div>', unsafe_allow_html=True)

    if "portfoy" not in st.session_state:
        st.session_state.portfoy = []

    left, right = st.columns([1, 2])

    with left:
        st.markdown("#### ➕ Pozisyon Ekle")
        h_sec = st.selectbox("Hisse", SYMBOLS, key="portfoy_sec")
        adet  = st.number_input("Adet", min_value=1, step=1, key="portfoy_adet")
        alis  = st.number_input("Alış Fiyatı ($)", min_value=0.01, step=0.01, key="alis_fiyat")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 Ekle", use_container_width=True):
                st.session_state.portfoy.append({"Hisse": h_sec, "Adet": int(adet), "Alış ($)": float(alis)})
                st.success(f"✅ {h_sec} eklendi!")
        with c2:
            if st.button("🔄 Yenile", use_container_width=True):
                get_last_prices.clear()
                st.rerun()

        if st.button("🗑️ Portföyü Temizle", use_container_width=True):
            st.session_state.portfoy = []
            st.rerun()

    with right:
        if st.session_state.portfoy:
            df_p = pd.DataFrame(st.session_state.portfoy)
            df_p = df_p.groupby("Hisse", as_index=False).agg({"Adet": "sum", "Alış ($)": "mean"})

            mevcut = tuple(df_p["Hisse"].unique())
            son_fiyatlar = get_last_prices(mevcut)

            for sym in mevcut:
                if len(all_prices.get(sym, [])) > 0:
                    son_fiyatlar[sym] = float(all_prices[sym][-1]["price"])

            df_p["Güncel ($)"]   = df_p["Hisse"].map(son_fiyatlar).fillna(0)
            df_p["Maliyet"]      = df_p["Adet"] * df_p["Alış ($)"]
            df_p["Toplam Değer"] = df_p["Adet"] * df_p["Güncel ($)"]
            df_p["K/Z ($)"]      = df_p["Toplam Değer"] - df_p["Maliyet"]
            df_p["K/Z (%)"]      = (df_p["K/Z ($)"] / df_p["Maliyet"]) * 100
            df_p["Ağırlık (%)"]  = (df_p["Toplam Değer"] / df_p["Toplam Değer"].sum()) * 100

            # Özet metrikler
            t_deger  = df_p["Toplam Değer"].sum()
            t_maliyet = df_p["Maliyet"].sum()
            t_kar    = t_deger - t_maliyet
            t_kar_pct = (t_kar / t_maliyet * 100) if t_maliyet > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("Toplam Değer", f"${t_deger:,.2f}")
            with m2: st.metric("Toplam Maliyet", f"${t_maliyet:,.2f}")
            with m3: st.metric("Kar/Zarar", f"${t_kar:+,.2f}", delta=f"{t_kar_pct:.2f}%")
            with m4: st.metric("Pozisyon", len(df_p))

            # Tablo
            df_show = df_p.copy()
            num_cols = ["Alış ($)", "Güncel ($)", "Maliyet", "Toplam Değer", "K/Z ($)", "K/Z (%)", "Ağırlık (%)"]
            df_show[num_cols] = df_show[num_cols].round(2)

            def renk_kz(val):
                return "color: #22c55e" if val >= 0 else "color: #ef4444"

            styled = df_show.style.map(renk_kz, subset=["K/Z ($)", "K/Z (%)"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Grafikler
            gc1, gc2 = st.columns(2)
            with gc1:
                fig_pie = px.pie(df_p, names="Hisse", values="Toplam Değer",
                                 title="Portföy Dağılımı",
                                 color_discrete_sequence=px.colors.qualitative.Set2)
                fig_pie.update_layout(template=PLOTLY_TEMPLATE, height=320,
                                      paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

            with gc2:
                colors_bar = ["#22c55e" if k >= 0 else "#ef4444" for k in df_p["K/Z ($)"]]
                fig_kar = go.Figure(go.Bar(
                    x=df_p["Hisse"], y=df_p["K/Z ($)"],
                    marker_color=colors_bar,
                    text=[f"${k:+.2f}" for k in df_p["K/Z ($)"]],
                    textposition="auto"
                ))
                fig_kar.update_layout(
                    title="Kar / Zarar Karşılaştırması",
                    template=PLOTLY_TEMPLATE, height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=40, b=0, l=0, r=0)
                )
                st.plotly_chart(fig_kar, use_container_width=True)

            # Portföy performans zaman serisi
            st.markdown('<div class="section-header">📈 Portföy Değer Trendi (Geçmiş Veri)</div>', unsafe_allow_html=True)
            try:
                hisse_listesi = list(mevcut)
                tarihsel = yf.download(hisse_listesi, period=zaman, auto_adjust=True, progress=False)

                if not tarihsel.empty:
                    if len(hisse_listesi) == 1:
                        close_df = tarihsel["Close"].to_frame(hisse_listesi[0])
                    else:
                        close_df = tarihsel["Close"]

                    portfoy_deger = pd.Series(0.0, index=close_df.index)
                    for _, row in df_p.iterrows():
                        sym = row["Hisse"]
                        if sym in close_df.columns:
                            portfoy_deger += close_df[sym] * row["Adet"]

                    portfoy_pct = (portfoy_deger / portfoy_deger.iloc[0] - 1) * 100

                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=portfoy_deger.index, y=portfoy_deger,
                        name="Portföy Değeri ($)",
                        line=dict(color="#60a5fa", width=2),
                        fill="tozeroy", fillcolor="rgba(96,165,250,0.06)"
                    ))
                    fig_trend.update_layout(
                        template=PLOTLY_TEMPLATE, height=300,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=0, r=0, t=10, b=0),
                        yaxis_tickprefix="$"
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
            except Exception as e:
                st.caption(f"Portföy trendi hesaplanamadı: {e}")
        else:
            st.info("Sol panelden hisse ekleyerek portföy oluşturun.")

# ═══════════════════════════════════════════════════════
# SEKME: BENCHMARK KARŞILAŞTIRMASI
# ═══════════════════════════════════════════════════════
elif aktif_sekme == "Benchmark":

    st.markdown('<div class="section-header">📊 Benchmark Karşılaştırması — S&P 500, QQQ, Dow Jones</div>', unsafe_allow_html=True)

    try:
        # Seçilen hisse geçmiş verisi
        hisse_df = get_history(my_select, zaman)
        benchmark_data = get_benchmark_history(zaman)

        if hisse_df.empty:
            st.warning("Hisse verisi alınamadı.")
            st.stop()

        hisse_close = hisse_df["Close"].squeeze()

        # Normalize (başlangıç = 100)
        fig_bench = go.Figure()
        hisse_norm = (hisse_close / hisse_close.iloc[0]) * 100
        fig_bench.add_trace(go.Scatter(
            x=hisse_norm.index, y=hisse_norm,
            name=my_select,
            line=dict(color="#60a5fa", width=2.5)
        ))

        bench_colors = {"S&P 500": "#f59e0b", "NASDAQ 100 (QQQ)": "#a78bfa", "Dow Jones": "#34d399"}
        for name, series in benchmark_data.items():
            norm = (series / series.iloc[0]) * 100
            fig_bench.add_trace(go.Scatter(
                x=norm.index, y=norm,
                name=name,
                line=dict(color=bench_colors.get(name, "#94a3b8"), width=1.5, dash="dash")
            ))

        fig_bench.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.2)", line_width=1)
        fig_bench.update_layout(
            title=f"{my_select} vs Piyasa Endeksleri (Normalize: Başlangıç = 100)",
            template=PLOTLY_TEMPLATE, height=460,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(orientation="h", y=1.02),
            yaxis_title="Getiri (Başlangıç=100)",
            hovermode="x unified"
        )
        fig_bench.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
        fig_bench.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
        st.plotly_chart(fig_bench, use_container_width=True)

        # Karşılaştırma tablosu
        st.markdown('<div class="section-header">📋 Dönem Performans Karşılaştırması</div>', unsafe_allow_html=True)

        all_series = {my_select: hisse_close}
        all_series.update(benchmark_data)

        tablo_rows = []
        for name, series in all_series.items():
            if series is None or len(series) < 2:
                continue
            toplam_getiri = (float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100
            vol_yillik    = float(series.pct_change().std() * np.sqrt(252) * 100)
            max_deger     = float(series.max())
            min_deger     = float(series.min())
            gunluk_ort    = float(series.pct_change().mean() * 100)
            tablo_rows.append({
                "Enstrüman": name,
                "Toplam Getiri (%)": round(toplam_getiri, 2),
                "Yıllık Volatilite (%)": round(vol_yillik, 2),
                "Dönem Yüksek": round(max_deger, 2),
                "Dönem Düşük": round(min_deger, 2),
                "Ort. Günlük Getiri (%)": round(gunluk_ort, 4),
            })

        df_tablo = pd.DataFrame(tablo_rows)

        def renk_getiri(val):
            return "color: #22c55e" if val > 0 else "color: #ef4444"

        styled_bench = df_tablo.style.map(renk_getiri, subset=["Toplam Getiri (%)"])
        st.dataframe(styled_bench, use_container_width=True, hide_index=True)

        # Korelasyon grafiği
        st.markdown('<div class="section-header">🔗 Korelasyon Analizi</div>', unsafe_allow_html=True)
        corr_dict = {my_select: hisse_close.pct_change().dropna()}
        for name, series in benchmark_data.items():
            try:
                aligned = series.pct_change().dropna().reindex(corr_dict[my_select].index, method="nearest")
                corr_dict[name] = aligned
            except Exception:
                pass

        if len(corr_dict) > 1:
            corr_df = pd.DataFrame(corr_dict).dropna()
            corr_matrix = corr_df.corr()

            fig_corr = px.imshow(
                corr_matrix,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                title="Günlük Getiri Korelasyon Matrisi"
            )
            fig_corr.update_layout(
                template=PLOTLY_TEMPLATE, height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=50, b=0),
            )
            st.plotly_chart(fig_corr, use_container_width=True)

        # Rolling beta
        st.markdown('<div class="section-header">📐 Rolling Beta (S&P 500 Karşısı)</div>', unsafe_allow_html=True)
        if "S&P 500" in benchmark_data:
            hisse_ret = hisse_close.pct_change().dropna()
            sp_ret    = benchmark_data["S&P 500"].pct_change().dropna()

            combined = pd.DataFrame({"hisse": hisse_ret, "sp500": sp_ret}).dropna()
            window = min(60, len(combined) // 3)
            if window > 5:
                rolling_cov  = combined["hisse"].rolling(window).cov(combined["sp500"])
                rolling_var  = combined["sp500"].rolling(window).var()
                rolling_beta = rolling_cov / rolling_var

                fig_beta = go.Figure()
                fig_beta.add_trace(go.Scatter(
                    x=rolling_beta.index, y=rolling_beta,
                    name=f"Beta ({window}g Yuvarlanan)",
                    line=dict(color="#a78bfa", width=2),
                    fill="tozeroy", fillcolor="rgba(167,139,250,0.06)"
                ))
                fig_beta.add_hline(y=1, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
                fig_beta.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.1)", line_width=1)
                fig_beta.update_layout(
                    template=PLOTLY_TEMPLATE, height=280,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=10, b=0),
                    yaxis_title="Beta",
                    hovermode="x unified"
                )
                fig_beta.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
                fig_beta.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
                st.plotly_chart(fig_beta, use_container_width=True)
                son_beta = float(rolling_beta.dropna().iloc[-1])
                if son_beta > 1.2:
                    st.warning(f"Beta {son_beta:.2f} — Piyasadan daha oynak (Yüksek Risk)")
                elif son_beta < 0.8:
                    st.info(f"Beta {son_beta:.2f} — Piyasadan daha az oynak (Düşük Risk)")
                else:
                    st.info(f"Beta {son_beta:.2f} — Piyasaya yakın hareket")

    except Exception as e:
        st.error(f"Benchmark karşılaştırması yapılamadı: {e}")

# ═══════════════════════════════════════════════════════
# SEKME: SWING TRADE (Qullamaggie Stratejisi)
# ═══════════════════════════════════════════════════════
elif aktif_sekme == "🎯 Swing Trade":

    # ─── CSS eklentisi
    st.markdown("""
    <style>
    .qt-card {
        background:#0c1a2e; border:1px solid #1e3a5f;
        border-radius:12px; padding:16px 20px; margin:8px 0;
    }
    .qt-label { font-size:11px; color:#475569; text-transform:uppercase; letter-spacing:.08em; margin-bottom:4px; }
    .qt-val   { font-size:20px; font-weight:700; color:#f1f5f9; }
    .qt-sub   { font-size:12px; color:#64748b; margin-top:2px; }
    .qt-green { color:#22c55e !important; }
    .qt-red   { color:#ef4444 !important; }
    .qt-amber { color:#f59e0b !important; }
    .qt-badge {
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:11px; font-weight:700; letter-spacing:.05em;
    }
    .badge-buy  { background:#052e16; border:1px solid #166534; color:#86efac; }
    .badge-wait { background:#172554; border:1px solid #1e40af; color:#93c5fd; }
    .badge-skip { background:#450a0a; border:1px solid #991b1b; color:#fca5a5; }
    .rule-row { display:flex; gap:8px; align-items:flex-start; margin:6px 0; font-size:13px; color:#94a3b8; }
    .rule-icon { font-size:16px; flex-shrink:0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🎯 Qullamaggie Swing Trade Tarayıcısı")
    st.caption("Kristjan Kullamägi'nin momentum stratejisine göre otomatik hisse taraması. Yatırım tavsiyesi değildir.")

    # ─── Qullamaggie filtre parametreleri (sidebar'a bağlı)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🎯 Swing Trade Filtreler")
        min_adr   = st.slider("Min ADR% (Günlük Volatilite)", 1.0, 8.0, 2.0, 0.5,
                              help="Qullamaggie %2+ ADR ister — düşük ADR'li hisseler hareket etmez")
        min_hacim = st.slider("Min Hacim (M)", 0.5, 10.0, 1.0, 0.5,
                              help="Likidite filtresi: günlük ortalama hacim milyar cinsinden")
        tarama_evreni = st.multiselect(
            "Tarama Evreni",
            ["AAPL","MSFT","NVDA","META","AMZN","GOOGL","TSLA","AMD","NFLX",
             "CRM","SHOP","ADBE","NOW","SNOW","DDOG","CRWD","ZS","MDB",
             "COIN","MSTR","PLTR","SMCI","ARM","AVGO","ORCL","UBER","LYFT",
             "ABNB","DASH","RBLX","U","HOOD","SOFI","AFRM","UPST","PATH",
             "AI","GTLB","BILL","HUBS","TMDX","AXON","CELH","DUOL","TTD"],
            default=["AAPL","MSFT","NVDA","META","AMZN","GOOGL","TSLA",
                     "AMD","NFLX","CRM","SHOP","ADBE","NOW","SNOW","DDOG",
                     "CRWD","ZS","COIN","PLTR","SMCI","AVGO","UBER","AXON","CELH","TTD"]
        )
        detay_symbol = st.selectbox("📋 Detay Grafik İçin Hisse", tarama_evreni if tarama_evreni else SYMBOLS)

    # ─── Qullamaggie fonksiyonları
    @st.cache_data(ttl=300, show_spinner=False)
    def qqq_trend_kontrol() -> tuple[str, dict]:
        """QQQ üzerinde 8/21/50 EMA kontrolü — piyasa yönünü belirler."""
        try:
            df = yf.download("QQQ", period="3mo", auto_adjust=True, progress=False)
            c = df["Close"].squeeze()
            ema8  = float(c.ewm(span=8,  adjust=False).mean().iloc[-1])
            ema21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])
            ema50 = float(c.ewm(span=50, adjust=False).mean().iloc[-1])
            son   = float(c.iloc[-1])
            trend = "YUKARI" if son > ema8 > ema21 > ema50 else \
                    ("ZAYIF"  if son > ema50 else "ASAGI")
            return trend, {"ema8": ema8, "ema21": ema21, "ema50": ema50, "son": son,
                           "son_tarih": str(df.index[-1].date())}
        except Exception:
            return "BILINMIYOR", {}

    @st.cache_data(ttl=300, show_spinner=False)
    def hisse_tara(semboller: tuple, min_adr_pct: float, min_hacim_m: float) -> list[dict]:
        """
        Qullamaggie kriterleri:
        1. Fiyat EMA8, EMA21, EMA50 üzerinde (trend)
        2. ADR > min_adr_pct  (volatilite / hareket gücü)
        3. Hacim > min_hacim_m milyon (likidite)
        4. Son 3 günde düşen trend çizgisi var (konsolidasyon / bayrak)
        5. Hacim spike: son kapanış hacmi 20-gün ortalamasının üstünde
        6. RSI 50-80 arası (momentum bölgesi, aşırı alım değil)
        """
        sonuclar = []
        for sym in semboller:
            try:
                df = yf.download(sym, period="6mo", auto_adjust=True, progress=False)
                if df is None or df.empty or len(df) < 60:
                    continue

                c  = df["Close"].squeeze()
                h  = df["High"].squeeze()
                lo = df["Low"].squeeze()
                v  = df["Volume"].squeeze()

                son = float(c.iloc[-1])

                # EMA'lar
                ema8  = float(c.ewm(span=8,  adjust=False).mean().iloc[-1])
                ema21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])
                ema50 = float(c.ewm(span=50, adjust=False).mean().iloc[-1])
                ema_ok = son > ema8 and son > ema21 and son > ema50 and ema8 > ema21 > ema50

                # ADR hesapla (son 14 günlük ortalama günlük aralık / fiyat)
                adr_pct = float(((h - lo) / c).rolling(14).mean().iloc[-1] * 100)

                # Hacim (20g ortalama, milyon)
                avg_vol_m = float(v.rolling(20).mean().iloc[-1]) / 1e6
                son_vol   = float(v.iloc[-1]) / 1e6
                vol_spike = son_vol > float(v.rolling(20).mean().iloc[-1]) * 1.3

                # RSI
                delta = c.diff()
                gain  = delta.clip(lower=0).rolling(14).mean()
                loss  = -delta.clip(upper=0).rolling(14).mean()
                rs    = gain / loss
                rsi   = float((100 - 100 / (1 + rs)).iloc[-1])
                rsi_ok = 50 <= rsi <= 80

                # Düşen trend çizgisi tespiti (son 10 bar içinde yüksekler düşüyor mu?)
                son10_highs = h.iloc[-10:].values
                x = np.arange(len(son10_highs))
                egim = float(np.polyfit(x, son10_highs, 1)[0])
                dusus_var = egim < -0.05 * float(son10_highs.mean()) / 10

                # Son bar kırılım teyidi: son kapanış, son 10-bar highların trend çizgisini kırdı mı?
                trend_line_son = float(np.polyval(np.polyfit(x, son10_highs, 1), len(son10_highs) - 1))
                kirilim = son > trend_line_son and vol_spike

                # Skor hesapla (max 5)
                skor = sum([ema_ok, adr_pct >= min_adr_pct, avg_vol_m >= min_hacim_m,
                            rsi_ok, kirilim])

                if not (ema_ok and adr_pct >= min_adr_pct and avg_vol_m >= min_hacim_m):
                    continue  # Zorunlu filtreler geçilmeli

                # Giriş / Stop / Hedef seviyeleri
                # Qullamaggie: giriş = kırılım günü yüksek üstü
                gün_yüksek    = float(h.iloc[-1])
                gün_dusuk     = float(lo.iloc[-1])
                önceki_düşük  = float(lo.iloc[-3:-1].min())  # 1-2 önceki gün düşük (stop için)
                son5_yüksek   = float(h.iloc[-5:].max())     # 5-bar pivot yüksek (hedef 1)
                son20_yüksek  = float(h.iloc[-20:].max())    # Önceki zirve (hedef 2)

                giris          = round(gün_yüksek * 1.002, 2)   # Kırılım üstü %0.2 pip
                stop_loss      = round(min(gün_dusuk, önceki_düşük) * 0.995, 2)
                hedef1         = round(son5_yüksek  * 1.01, 2)
                hedef2         = round(son20_yüksek * 1.02, 2)
                risk_reward    = round((hedef1 - giris) / max(giris - stop_loss, 0.01), 2)
                risk_pct       = round((giris - stop_loss) / giris * 100, 2)

                # Formasyonu tespit et
                if dusus_var and kirilim:
                    formasyon = "🚩 Düşen Kanal Kırılımı"
                elif vol_spike and rsi_ok:
                    formasyon = "📊 Hacim Patlaması"
                elif ema_ok and rsi_ok:
                    formasyon = "📐 EMA Sıkışması"
                else:
                    formasyon = "🔍 Konsolidasyon"

                sonuclar.append({
                    "Sembol": sym,
                    "Fiyat ($)": round(son, 2),
                    "ADR (%)": round(adr_pct, 2),
                    "Ort.Hacim (M)": round(avg_vol_m, 1),
                    "RSI": round(rsi, 1),
                    "EMA Sırası ✓": ema_ok,
                    "Kırılım": kirilim,
                    "Formasyon": formasyon,
                    "Giriş ($)": giris,
                    "Stop ($)": stop_loss,
                    "Hedef 1 ($)": hedef1,
                    "Hedef 2 ($)": hedef2,
                    "Risk (%)": risk_pct,
                    "R/R Oranı": risk_reward,
                    "Skor": skor,
                    "EMA8": round(ema8,2), "EMA21": round(ema21,2), "EMA50": round(ema50,2),
                })
            except Exception:
                continue
        sonuclar.sort(key=lambda x: x["Skor"], reverse=True)
        return sonuclar

    @st.cache_data(ttl=300, show_spinner=False)
    def detay_grafik_verisi(symbol: str) -> pd.DataFrame:
        df = yf.download(symbol, period="6mo", auto_adjust=True, progress=False)
        return df

    # ─── ÇALIŞTIR
    st.markdown('<div class="section-header">📡 QQQ Piyasa Trendi (Qullamaggie Filtre #1)</div>', unsafe_allow_html=True)

    trend, qqq_vals = qqq_trend_kontrol()
    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    trend_badge = {
        "YUKARI":     '<span class="qt-badge badge-buy">⬆ YUKARI TREND — İşlem YAP</span>',
        "ZAYIF":      '<span class="qt-badge badge-wait">↔ ZAYIF TREND — Dikkatli Ol</span>',
        "ASAGI":      '<span class="qt-badge badge-skip">⬇ AŞAĞI TREND — İşlem YAPMA</span>',
        "BILINMIYOR": '<span class="qt-badge badge-wait">? Veri alınamadı</span>',
    }[trend]
    with tc1:
        st.markdown(f'<div class="qt-card"><div class="qt-label">QQQ Trend</div>{trend_badge}</div>', unsafe_allow_html=True)
    with tc2:
        st.markdown(f'<div class="qt-card"><div class="qt-label">QQQ Fiyat</div><div class="qt-val">${qqq_vals.get("son",0):.2f}</div><div class="qt-sub">{qqq_vals.get("son_tarih","")}</div></div>', unsafe_allow_html=True)
    with tc3:
        st.markdown(f'<div class="qt-card"><div class="qt-label">EMA 8</div><div class="qt-val qt-green">${qqq_vals.get("ema8",0):.2f}</div></div>', unsafe_allow_html=True)
    with tc4:
        st.markdown(f'<div class="qt-card"><div class="qt-label">EMA 21</div><div class="qt-val qt-amber">${qqq_vals.get("ema21",0):.2f}</div></div>', unsafe_allow_html=True)
    with tc5:
        st.markdown(f'<div class="qt-card"><div class="qt-label">EMA 50</div><div class="qt-val qt-red">${qqq_vals.get("ema50",0):.2f}</div></div>', unsafe_allow_html=True)

    if trend == "ASAGI":
        st.error("⛔ Piyasa düşüş trendinde. Qullamaggie: 'Piyasa karşında işlem açma, nakit tut.'")
    elif trend == "ZAYIF":
        st.warning("⚠️ Piyasa zayıf. Pozisyon boyutunu küçült, seçici ol.")
    else:
        st.success("✅ Piyasa yükseliş trendinde. Kırılım yapan hisseleri ara.")

    st.markdown("---")

    # ─── TARAMA
    st.markdown('<div class="section-header">🔍 Otomatik Hisse Taraması — Qullamaggie Kriterleri</div>', unsafe_allow_html=True)

    col_filtre, col_kural = st.columns([3, 2])
    with col_filtre:
        st.markdown(f"**Taranan:** {len(tarama_evreni)} hisse &nbsp;|&nbsp; **Min ADR:** %{min_adr} &nbsp;|&nbsp; **Min Hacim:** {min_hacim}M")
    with col_kural:
        st.markdown("""
        <div style="font-size:12px; color:#64748b; line-height:1.9;">
        ✅ EMA8 > EMA21 > EMA50 (Trend)&nbsp;&nbsp;
        ✅ ADR > %2 (Hareket Gücü)&nbsp;&nbsp;
        ✅ Hacim > 1M (Likidite)&nbsp;&nbsp;
        ✅ RSI 50–80 (Momentum)&nbsp;&nbsp;
        ✅ Düşen Kanal Kırılımı + Hacim Spike
        </div>
        """, unsafe_allow_html=True)

    with st.spinner("Hisseler taranıyor..."):
        tarama_sonuc = hisse_tara(tuple(tarama_evreni), min_adr, min_hacim)

    if not tarama_sonuc:
        st.info("Mevcut filtrelere uyan hisse bulunamadı. Min ADR veya Hacim eşiğini düşürmeyi deneyin.")
    else:
        st.success(f"✅ {len(tarama_sonuc)} hisse kriterleri karşıladı. Skor sırasına göre listelendi.")

        # Tablo gösterimi
        df_tarama = pd.DataFrame(tarama_sonuc)
        göster_kolonlar = ["Sembol","Fiyat ($)","ADR (%)","Ort.Hacim (M)","RSI",
                           "Formasyon","Giriş ($)","Stop ($)","Hedef 1 ($)","Hedef 2 ($)",
                           "Risk (%)","R/R Oranı","Skor"]
        df_göster = df_tarama[göster_kolonlar].copy()

        def rr_renk(val):
            if isinstance(val, float):
                return "color: #22c55e" if val >= 2 else ("color: #f59e0b" if val >= 1 else "color: #ef4444")
            return ""
        def risk_renk(val):
            if isinstance(val, float):
                return "color: #22c55e" if val <= 5 else ("color: #f59e0b" if val <= 8 else "color: #ef4444")
            return ""

        styled_tarama = df_göster.style \
            .map(rr_renk, subset=["R/R Oranı"]) \
            .map(risk_renk, subset=["Risk (%)"])
        st.dataframe(styled_tarama, use_container_width=True, hide_index=True)

        # ─── Özet bar chart: R/R oranı
        fig_rr = go.Figure(go.Bar(
            x=[r["Sembol"] for r in tarama_sonuc],
            y=[r["R/R Oranı"] for r in tarama_sonuc],
            marker_color=["#22c55e" if r["R/R Oranı"] >= 2 else "#f59e0b" for r in tarama_sonuc],
            text=[f"{r['R/R Oranı']:.1f}x" for r in tarama_sonuc],
            textposition="outside"
        ))
        fig_rr.add_hline(y=2, line_dash="dash", line_color="#94a3b8", line_width=1,
                         annotation_text="Min 2:1 R/R (Qullamaggie eşiği)")
        fig_rr.update_layout(
            title="Risk/Ödül Oranları",
            template=PLOTLY_TEMPLATE, height=260,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis_title="R/R Oranı"
        )
        st.plotly_chart(fig_rr, use_container_width=True)

    st.markdown("---")

    # ─── DETAY GRAFİĞİ
    st.markdown(f'<div class="section-header">📊 Detay Grafik: {detay_symbol} — Düşen Kanal + Seviyeler</div>', unsafe_allow_html=True)

    try:
        df_det = detay_grafik_verisi(detay_symbol)
        if df_det.empty:
            st.warning("Veri alınamadı.")
        else:
            c_det  = df_det["Close"].squeeze()
            h_det  = df_det["High"].squeeze()
            lo_det = df_det["Low"].squeeze()
            v_det  = df_det["Volume"].squeeze()

            # Son 60 bar üzerinden çalış
            son60 = df_det.iloc[-60:]
            c60   = son60["Close"].squeeze()
            h60   = son60["High"].squeeze()
            lo60  = son60["Low"].squeeze()
            v60   = son60["Volume"].squeeze()

            # EMA'lar (tüm seri üzerinden hesapla, son 60'ı al)
            ema8_s  = c_det.ewm(span=8,  adjust=False).mean().iloc[-60:]
            ema21_s = c_det.ewm(span=21, adjust=False).mean().iloc[-60:]
            ema50_s = c_det.ewm(span=50, adjust=False).mean().iloc[-60:]

            # Düşen trend çizgisi: son 10-15 bar highlarından regresyon
            pencere = 12
            son_pencere = h60.iloc[-pencere:]
            x_p = np.arange(pencere)
            pol = np.polyfit(x_p, son_pencere.values, 1)
            trend_y = np.polyval(pol, x_p)
            trend_x = son_pencere.index.tolist()

            # Seviyeler
            giris_fiyat = round(float(h60.iloc[-1]) * 1.002, 2)
            stop_fiyat  = round(min(float(lo60.iloc[-1]), float(lo60.iloc[-3:-1].min())) * 0.995, 2)
            hedef1_fiyat = round(float(h60.iloc[-5:].max()) * 1.01, 2)
            hedef2_fiyat = round(float(h60.max()) * 1.02, 2)

            # ─── Grafik
            fig_det = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    row_heights=[0.75, 0.25], vertical_spacing=0.04)

            # Mum grafiği
            fig_det.add_trace(go.Candlestick(
                x=son60.index,
                open=son60["Open"].squeeze(), high=h60,
                low=lo60, close=c60,
                name="OHLC",
                increasing_line_color="#22c55e", decreasing_line_color="#ef4444",
                increasing_fillcolor="#166534", decreasing_fillcolor="#7f1d1d",
            ), row=1, col=1)

            # EMA çizgileri
            fig_det.add_trace(go.Scatter(x=ema8_s.index,  y=ema8_s,
                name="EMA 8",  line=dict(color="#22c55e", width=1.5)), row=1, col=1)
            fig_det.add_trace(go.Scatter(x=ema21_s.index, y=ema21_s,
                name="EMA 21", line=dict(color="#f59e0b", width=1.5)), row=1, col=1)
            fig_det.add_trace(go.Scatter(x=ema50_s.index, y=ema50_s,
                name="EMA 50", line=dict(color="#ec4899", width=1.5, dash="dash")), row=1, col=1)

            # ── Düşen trend çizgisi (kırmızı kesikli)
            fig_det.add_trace(go.Scatter(
                x=trend_x, y=trend_y.tolist(),
                mode="lines", name="Düşen Trend Çizgisi",
                line=dict(color="#ef4444", width=2, dash="dash"),
            ), row=1, col=1)

            # Düşen kanal bölgesi — trend üstü gölge
            # Alt kanal = trend - (max high - trend ortası)
            aralik = float(np.max(trend_y) - np.min(trend_y)) * 0.5
            alt_kanal = trend_y - aralik
            fig_det.add_trace(go.Scatter(
                x=trend_x + trend_x[::-1],
                y=trend_y.tolist() + alt_kanal[::-1].tolist(),
                fill="toself", fillcolor="rgba(239,68,68,0.06)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Düşen Kanal", showlegend=True
            ), row=1, col=1)

            # ── Yatay seviye çizgileri
            y_range_pad = (giris_fiyat - stop_fiyat) * 0.3
            seviyeler = [
                (giris_fiyat,  "#60a5fa", "solid",  "🔵 Giriş", "right"),
                (stop_fiyat,   "#ef4444", "dot",    "🔴 Stop Loss", "right"),
                (hedef1_fiyat, "#22c55e", "dash",   "🟢 Hedef 1 (25% sat)", "right"),
                (hedef2_fiyat, "#a78bfa", "longdash","🟣 Hedef 2 (kalan %75)", "right"),
            ]
            for fiyat_s, renk, dash, etiket, pos in seviyeler:
                fig_det.add_hline(
                    y=fiyat_s, line_dash=dash, line_color=renk, line_width=1.5,
                    annotation_text=f"{etiket}: ${fiyat_s}",
                    annotation_position=f"top {pos}",
                    annotation_font_color=renk,
                    annotation_font_size=11,
                    row=1, col=1
                )

            # Risk bölgesi gölgesi (stop → giriş arası)
            fig_det.add_hrect(
                y0=stop_fiyat, y1=giris_fiyat,
                fillcolor="rgba(239,68,68,0.07)", line_width=0,
                annotation_text="⚠️ Risk Bölgesi", annotation_font_color="#ef4444",
                annotation_font_size=10, row=1, col=1
            )
            # Kar bölgesi gölgesi (giriş → hedef1 arası)
            fig_det.add_hrect(
                y0=giris_fiyat, y1=hedef1_fiyat,
                fillcolor="rgba(34,197,94,0.05)", line_width=0,
                row=1, col=1
            )

            # Hacim (renkli)
            vol_colors = ["#22c55e" if float(c60.iloc[i]) >= float(c60.iloc[i-1])
                          else "#ef4444" for i in range(1, len(c60))]
            vol_colors.insert(0, "#94a3b8")
            avg_vol = float(v60.rolling(20).mean().iloc[-1])
            fig_det.add_trace(go.Bar(x=son60.index, y=v60,
                marker_color=vol_colors, name="Hacim", showlegend=False), row=2, col=1)
            fig_det.add_hline(y=avg_vol, line_dash="dot", line_color="#94a3b8", line_width=1,
                               annotation_text="20g Ort.", annotation_font_size=10, row=2, col=1)

            fig_det.update_layout(
                title=f"{detay_symbol} — Son 60 Bar | Qullamaggie Swing Seviyeleri",
                template=PLOTLY_TEMPLATE, height=680,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=50, b=0),
                legend=dict(orientation="h", y=1.02),
                xaxis_rangeslider_visible=False,
                hovermode="x unified"
            )
            fig_det.update_yaxes(gridcolor="rgba(255,255,255,0.04)")
            fig_det.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
            st.plotly_chart(fig_det, use_container_width=True)

            # ─── Seviye özet kartları
            st.markdown('<div class="section-header">📐 İşlem Planı — Qullamaggie Kuralları</div>', unsafe_allow_html=True)

            risk_dolar  = round(giris_fiyat - stop_fiyat, 2)
            hedef1_kar  = round(hedef1_fiyat - giris_fiyat, 2)
            hedef2_kar  = round(hedef2_fiyat - giris_fiyat, 2)
            rr1 = round(hedef1_kar / max(risk_dolar, 0.01), 2)
            rr2 = round(hedef2_kar / max(risk_dolar, 0.01), 2)

            k1, k2, k3, k4, k5, k6 = st.columns(6)
            kart_data = [
                (k1, "🔵 Giriş Fiyatı",    f"${giris_fiyat}",    "Kırılım üstü %0.2 pip", "#3b82f6"),
                (k2, "🔴 Stop Loss",        f"${stop_fiyat}",     f"Risk: ${risk_dolar} / hisse", "#ef4444"),
                (k3, "🟢 Hedef 1",          f"${hedef1_fiyat}",   f"+${hedef1_kar} | R/R: {rr1}x", "#22c55e"),
                (k4, "🟣 Hedef 2",          f"${hedef2_fiyat}",   f"+${hedef2_kar} | R/R: {rr2}x", "#a78bfa"),
                (k5, "⚡ Risk (%)",         f"%{round((giris_fiyat-stop_fiyat)/giris_fiyat*100,2)}", "Girişten stop'a mesafe", "#f59e0b"),
                (k6, "📊 EMA Sırası",
                     "✅ Sıralı" if float(c_det.ewm(span=8,adjust=False).mean().iloc[-1]) >
                                    float(c_det.ewm(span=21,adjust=False).mean().iloc[-1]) >
                                    float(c_det.ewm(span=50,adjust=False).mean().iloc[-1]) else "❌ Bozuk",
                     "EMA8>EMA21>EMA50", "#64748b"),
            ]
            for kol, baslik, deger, alt, renk in kart_data:
                with kol:
                    st.markdown(f"""
                    <div class="qt-card" style="border-color:{renk}40">
                        <div class="qt-label">{baslik}</div>
                        <div class="qt-val" style="color:{renk}">{deger}</div>
                        <div class="qt-sub">{alt}</div>
                    </div>""", unsafe_allow_html=True)

            # ─── Qullamaggie kuralları özeti
            st.markdown("---")
            st.markdown("#### 📖 Qullamaggie Uygulama Kuralları")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown(f"""
                <div class="qt-card">
                <b style="color:#60a5fa">GİRİŞ KOŞULLARI</b><br><br>
                <div class="rule-row"><span class="rule-icon">1️⃣</span> QQQ fiyat EMA8 > EMA21 > EMA50 üzerinde olmalı</div>
                <div class="rule-row"><span class="rule-icon">2️⃣</span> Hisse EMA sırası korunuyor: EMA8 > EMA21 > EMA50</div>
                <div class="rule-row"><span class="rule-icon">3️⃣</span> Düşen trend çizgisi güçlü hacimle kırıldı</div>
                <div class="rule-row"><span class="rule-icon">4️⃣</span> RSI 50–80 arası (aşırı alım değil, momentum var)</div>
                <div class="rule-row"><span class="rule-icon">5️⃣</span> ADR ≥ %2 — hisse yeterli günlük hareket yapıyor</div>
                <div class="rule-row"><span class="rule-icon">6️⃣</span> 5 veya 15 dakikalık grafikte kırılım teyidi al</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r2:
                st.markdown(f"""
                <div class="qt-card">
                <b style="color:#22c55e">KAR ALMA & STOP YÖNETİMİ</b><br><br>
                <div class="rule-row"><span class="rule-icon">🟢</span> <b>Hedef 1 (${hedef1_fiyat}):</b> Pozisyonun %25'ini sat, stop'u maliyete çek → risk sıfır</div>
                <div class="rule-row"><span class="rule-icon">🟣</span> <b>Hedef 2 (${hedef2_fiyat}):</b> Kalan %75'i kademelı sat veya trailing stop ile tut</div>
                <div class="rule-row"><span class="rule-icon">🔴</span> <b>Stop Loss (${stop_fiyat}):</b> Giriş günü veya önceki günün düşüğü altı — kesinlikle uy!</div>
                <div class="rule-row"><span class="rule-icon">⚠️</span> QQQ yön değiştirirse pozisyonu küçült</div>
                <div class="rule-row"><span class="rule-icon">📏</span> Pozisyon boyutu: hesap riski max %1–2 (stop × lot = toplam risk)</div>
                <div class="rule-row"><span class="rule-icon">🧠</span> Duygularla değil, teknik sinyallerle hareket et</div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Detay grafik oluşturulamadı: {e}")

st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#334155; font-size:11px;'>"
    "Bu uygulama yalnızca eğitim amaçlıdır. Gerçek yatırım kararları için lütfen lisanslı bir finansal danışmana başvurun."
    "</p>",
    unsafe_allow_html=True
)
