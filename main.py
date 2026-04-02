
import requests
import time
import yfinance as yf
import ta
import os

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

last_signal = None

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def get_signal():
    global last_signal
    return "✅ Bot Working Fine 🚀"

    try:
        df = yf.download("ETH-USD", period="1d", interval="5m")

        if df.empty:
            return None

        close = df['Close']

        # 🔥 Fix 1D issue
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

        # 🔥 Fast signal logic (test mode)
        if rsi_val < 50 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 50 and macd_val < macd_sig:
            signal = "SELL"

        # 🚫 Duplicate avoid
        if signal == last_signal or signal is None:
            return None

        last_signal = signal

        # 🎯 MESSAGE FORMAT (FIXED)
        if signal == "BUY":
            msg = f"""
🟢 BUY SIGNAL — ETH

Entry : {price:.2f}
TP1   : {price+10:.2f}
TP2   : {price+20:.2f}
SL    : {price-10:.2f}

RSI   : {rsi_val:.2f}
"""
        else:
            msg = f"""
🔴 SELL SIGNAL — ETH

Entry : {price:.2f}
TP1   : {price-10:.2f}
TP2   : {price-20:.2f}
SL    : {price+10:.2f}

RSI   : {rsi_val:.2f}
"""

        return msg

    except Exception as e:
        return f"❌ Error: {e}"


# 🔥 MAIN LOOP
while True:
    try:
        msg = get_signal()

        if msg:
            send_telegram(msg)
            print("Sent:", msg)
        else:
            print("No signal...")

        time.sleep(300)

    except Exception as e:
        print("Loop Error:", e)
        time.sleep(60)
