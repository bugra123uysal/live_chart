import streamlit as st 
import pandas as pd 
import plotly.express as px 
import websocket 
import plotly.graph_objects as go 
import json
import threading
import time
import yfinance as yf 
from google import genai 
from collections import deque
from  streamlit_autorefresh import st_autorefresh 
import matplotlib.pyplot as plt 

api_key = "*****"
symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT"]

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
    for symbol in symbols:
        
       ws.send(json.dumps({
           "type": "subscribe",
           "symbol": symbol,
           
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
    df_grafik=df[df["symbol"]==my_select]
    
    
    fig = px.line(
        df_grafik,
        x="timestamp",
        y="price",
        color="symbol",
        title=f"{clen_symbols} canlı fiyat grafiği"
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{len(prices)}")

else:
    st.info("lütfen bekleiniz ...")
st_autorefresh(interval=1000 , key="refresh")

    


""" yfinance ile geçmiş fiyat verisi çekme ve görselleştirme"""
y_map={
    "BINANCE:BTCUSDT": "BTC-USD",
    "BINANCE:ETHUSDT": "ETH-USD",
    "BINANCE:SOLUSDT": "SOL-USD",
    }
yıl=["1y","2y","5y","10y","max"]

zaman=st.selectbox("zaman aralığı seçiniz" , yıl)
sec=y_map[my_select]
cek=yf.download(sec , period=zaman)
st.line_chart(cek["Close"])

# portföy bölümü 
st.title("portföyüm")
left , right =st.columns([1,2])
portföy=[]
adetler={}
if "portföy" not in st.session_state:
    st.session_state.portföy=[]
with left:
  h_seç=st.multiselect("hisse seçiniz",symbols)
  
  for sec_coin in h_seç:
  
     adetler[sec_coin]=st.number_input(f"{sec_coin} için  adet giriniz", min_value=1 , step=1,key=f"adet_{sec_coin}")
    
  
  
  ekl_prfy=st.button("portföye ekle")
with right:
  if ekl_prfy:
      for  sec_coin in h_seç:
        coinn=sec_coin.split(":")[1]
        co=df[df["symbol"]==sec_coin]
        if not co.empty:
            son_coin=co["price"].iloc[-1]
            st.session_state.portföy.append({
              "hisse":coinn,
              "adet":adetler[sec_coin],
              "fiyat":son_coin,
              "değer": adetler[sec_coin] * son_coin
              
          })
            
      st.success(f"{sec_coin} kriptosu portföye eklendi")
  if st.session_state.portföy:
     alt=pd.DataFrame(st.session_state.portföy)
     st.dataframe(alt, use_container_width=True)
     
     fig_pie=px.pie(
         alt,
         names="hisse",
         values="değer",
         title="portföydeki hisse dağılımı"
         
                    )
     st.plotly_chart(fig_pie, use_container_width=True)
