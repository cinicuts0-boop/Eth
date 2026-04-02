
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
        res = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })

        print("Telegram Response:", res.text)

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

        # 🔥 INDICATORS
        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)
        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()
        ema = ta.trend.EMAIndicator(close, window=200).ema_indicator()

        # LAST VALUES
        price = float(close.iloc[-1])
        rsi_val = float(rsi.iloc[-1])
        macd_val = float(macd.iloc[-1])
        macd_sig = float(macd_signal.iloc[-1])
        ema_val = float(ema.iloc[-1])

        signal = None

        # 🟢 BUY (STRONG)
        if price > ema_val and rsi_val < 35 and macd_val > macd_sig:
            signal = "BUY"

        # 🔴 SELL (STRONG)
        elif price < ema_val and rsi_val > 65 and macd_val < macd_sig:
            signal = "SELL"

        # 🚫 Duplicate avoid
        if signal == last_signal or signal is None:
            return None

        last_signal = signal

        # 🎯 SMART TP / SL
        if signal == "BUY":
            tp1 = price + 15
            tp2 = price + 30
            sl = price - 12

            msg = f"""
🟢 STRONG BUY — ETH

Entry : {price:.2f}
TP1   : {tp1:.2f}
TP2   : {tp2:.2f}
SL    : {sl:.2f}

RSI   : {rsi_val:.2f}
Trend : UP 📈
"""

        else:
            tp1 = price - 15
            tp2 = price - 30
            sl = price + 12

            msg = f"""
🔴 STRONG SELL — ETH

Entry : {price:.2f}
TP1   : {tp1:.2f}
TP2   : {tp2:.2f}
SL    : {sl:.2f}

RSI   : {rsi_val:.2f}
Trend : DOWN 📉
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
