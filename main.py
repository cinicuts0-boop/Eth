import requests
import time
import yfinance as yf
import ta
import os

TOKEN = os.getenv("8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("8007854479")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_signal():
    df = yf.download("ETH-USD", period="1d", interval="5m")

    df['rsi'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])

    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    last = df.iloc[-1]

    signal = "NO SIGNAL"

    if last['rsi'] < 30 and last['macd'] > last['macd_signal']:
        signal = "🟢 BUY"

    elif last['rsi'] > 70 and last['macd'] < last['macd_signal']:
        signal = "🔴 SELL"

    msg = f"""
🚨 ETH SIGNAL

Price: {last['Close']:.2f}
RSI: {last['rsi']:.2f}

Signal: {signal}
"""
    return msg

while True:
    try:
        msg = get_signal()
        send_telegram(msg)
        print("Sent:", msg)
        time.sleep(300)
    except Exception as e:
        print("Error:", e)
        time.sleep(60)
