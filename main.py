import requests
import time
import yfinance as yf
import ta
import os

TOKEN = os.getenv("8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("8007854479")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def get_signal():
    try:
        df = yf.download("ETH-USD", period="1d", interval="5m")

        if df.empty:
            return "⚠️ No data"

        close = df['Close']

        # 🔥 Convert to 1D
        if len(close.shape) > 1:
            close = close.squeeze()

        # Indicators
        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()

        # 🔥 Get LAST VALUES (IMPORTANT FIX)
        last_price = float(close.iloc[-1])
        last_rsi = float(rsi.iloc[-1])
        last_macd = float(macd.iloc[-1])
        last_macd_signal = float(macd_signal.iloc[-1])

        signal = "⚪ NO SIGNAL"

        if last_rsi < 30 and last_macd > last_macd_signal:
            signal = "🟢 STRONG BUY"

        elif last_rsi > 70 and last_macd < last_macd_signal:
            signal = "🔴 STRONG SELL"

        msg = f"""
🚨 ETH SIGNAL

Price : {last_price:.2f}
RSI   : {last_rsi:.2f}

Signal: {signal}
"""

        return msg

    except Exception as e:
        return f"❌ Error in signal: {e}"


# 🔥 LOOP
while True:
    try:
        msg = get_signal()
        send_telegram(msg)
        print("Sent:", msg)

        time.sleep(300)

    except Exception as e:
        print("Loop Error:", e)
        time.sleep(60)
