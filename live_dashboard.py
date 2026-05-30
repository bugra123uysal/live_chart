
# py -m streamlit run C:\Users\batu\Desktop\kodlar\deneme.py 
import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
import websocket # type: ignore
import plotly.graph_objects as go  # type: ignore
import json
import threading
import time
import yfinance as yf # type: ignore
from google import genai 
from collections import deque
from  streamlit_autorefresh import st_autorefresh # type: ignore

api_key = "****************"
symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT "]

my_select=st.selectbox("kripto seçiniz",symbols)
clen_symbols =my_select.split(":")[1]
@st.cache_resource
def get_prices():
    return deque(maxlen=300)

prices=get_prices()


if "active_symbol" not in st.session_state:
    st.session_state.active_symbol = my_select
    
if st.session_state.active_symbol !=my_select:
    prices.clear()
    st.session_state.active_symbol = my_select
    st.session_state.started=False

def on_message(ws, message):
    
    data=json.loads(message)

    if data.get("type") == "trade":
        for trade in data["data"]:
            prices.append({
                "symbol": trade["s"],
                "price": trade["p"],
                "timestamp": pd.to_datetime(trade["t"], unit="ms"),
                "volume": trade["v"]
            })

def on_open(ws):
    print("WebSocket açıldı")
    
    ws.send(json.dumps({
        "type": "subscribe",
        "symbol": my_select
    }))

def start_websocket():
   
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={api_key}",
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

st.title("Canlı Kripto Fiyat Grafiği")


if "started" not in st.session_state or st.session_state.started ==False: 
    thread = threading.Thread(target=start_websocket, daemon=True)
    thread.daemon = True
    thread.start()
    st.session_state.started = True




if len(prices) > 0:
    df = pd.DataFrame(list(prices))
    
    df=df.set_index("timestamp")
    ahlc=df["price"].resample("1min").ohlc()

    fig = go.Figure(
        data=[
            go.Candlestick(
            x=ahlc.index,
            open=ahlc["open"],
            high=ahlc["high"],
            low=ahlc["low"],
            close=ahlc["close"],
            name="Fiyat"
            
           )
        ]
    )
    fig.update_layout(title=f"{clen_symbols} Canlı Fiyat Grafiği", xaxis_title="Zaman", yaxis_title="Fiyat (USD)", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig , use_container_width=True, key=f"candlestick_{len(prices)}")
    
else:
    st.info("bekleyiniz...") 
st_autorefresh(interval=1000, key="refresh")


""" yfinance ile geçmiş fiyat verisi çekme ve görselleştirme"""
y_map={
    "BINANCE:BTCUSDT": "BTC-USD",
    "BINANCE:ETHUSDT": "ETH-USD",
    "BINANCE:SOLUSDT": "SOL-USD "
    }
yıl=["1y","2y","5y","10y","max"]

zaman=st.selectbox("zaman aralığı seçiniz" , yıl)
sec=y_map[my_select]
cek=yf.download(sec , period=zaman)
st.line_chart(cek["Close"])

# portföy bölümü 
st.title("portföyüm")
portföy=[]
if "portföy" not in st.session_state:
    st.session_state.portföy=[]

h_seç=st.multiselect("hisse seçiniz",symbols)

for sec_coin in h_seç:

  adet=st.number_input(f"{sec_coin} için  adet giriniz", min_value=1 , step=1)
  


ekl_prfy=st.button("portföye ekle")

if ekl_prfy:
    for  sec_coin in h_seç:
     st.session_state.portföy.append({
        "hisse":sec_coin,
        "adet":adet
     })

    st.success(f"{sec_coin} kriptosu portföye eklendi")
if st.session_state.portföy:
   alt=pd.DataFrame(st.session_state.portföy)
   st.dataframe(alt)
