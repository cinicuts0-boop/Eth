
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

        # 🔥 EMPTY DATA CHECK
        if df.empty:
            return "⚠️ No data received"

        close = df['Close']

        # 🔥 FIX: Convert to 1D
        if len(close.shape) > 1:
            close = close.squeeze()

        # 🔥 Remove NaN values
        df = df.dropna()

        # Indicators
        df['rsi'] = ta.momentum.RSIIndicator(close).rsi()

        macd = ta.trend.MACD(close)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        last = df.iloc[-1]

        signal = "⚪ NO SIGNAL"

        # 🔥 STRONG LOGIC
        if last['rsi'] < 30 and last['macd'] > last['macd_signal']:
            signal = "🟢 STRONG BUY"

        elif last['rsi'] > 70 and last['macd'] < last['macd_signal']:
            signal = "🔴 STRONG SELL"

        msg = f"""
🚨 ETH SIGNAL

Price : {last['Close']:.2f}
RSI   : {last['rsi']:.2f}

Signal: {signal}
"""

        return msg

    except Exception as e:
        return f"❌ Error in signal: {e}"


# 🔥 MAIN LOOP
while True:
    try:
        msg = get_signal()
        send_telegram(msg)
        print("Sent:", msg)

        time.sleep(300)  # 5 minutes

    except Exception as e:
        print("Loop Error:", e)
        time.sleep(60)
