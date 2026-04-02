
import requests
import time
import yfinance as yf
import ta
import os

TOKEN = os.getenv("8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("8007854479")

last_signal = None  # 🚫 duplicate avoid

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def get_signal():
    global last_signal

    try:
        df = yf.download("ETH-USD", period="1d", interval="5m")

        if df.empty:
            return None

        close = df['Close']

        if len(close.shape) > 1:
            close = close.squeeze()

        # Indicators
        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()

        # Last values
        price = float(close.iloc[-1])
        rsi_val = float(rsi.iloc[-1])
        macd_val = float(macd.iloc[-1])
        macd_sig = float(macd_signal.iloc[-1])

        signal = None

        # 🎯 SIGNAL LOGIC
        if rsi_val < 30 and macd_val > macd_sig:
            signal = "BUY"

        elif rsi_val > 70 and macd_val < macd_sig:
            signal = "SELL"

        # 🚫 Duplicate avoid
        if signal == last_signal or signal is None:
            return None

        last_signal = signal

        # 🎯 TARGET + SL CALCULATION
        if signal == "BUY":
            tp1 = price + 10
            tp2 = price + 20
            sl = price - 10

            msg = f"""
🟢 BUY SIGNAL — ETH

Entry : {price:.2f}
TP1   : {tp1:.2f}
TP2   : {tp2:.2f}
SL    : {sl:.2f}

RSI   : {rsi_val:.2f}
"""

        elif signal == "SELL":
            tp1 = price - 10
            tp2 = price - 20
            sl = price + 10

            msg = f"""
🔴 SELL SIGNAL — ETH

Entry : {price:.2f}
TP1   : {tp1:.2f}
TP2   : {tp2:.2f}
SL    : {sl:.2f}

RSI   : {rsi_val:.2f}
"""

        return msg

    except Exception as e:
        return f"❌ Error: {e}"


# 🔥 LOOP
while True:
    try:
        msg = get_signal()

        if msg:
            send_telegram(msg)
            print("Sent:", msg)

        time.sleep(300)

    except Exception as e:
        print("Loop Error:", e)
        time.sleep(60)
