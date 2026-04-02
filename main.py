
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
        # 🔥 5 MIN DATA (ENTRY)
        df_5m = yf.download("ETH-USD", period="1d", interval="5m")

        # 🔥 15 MIN DATA (TREND)
        df_15m = yf.download("ETH-USD", period="1d", interval="15m")

        if df_5m.empty or df_15m.empty:
            return None

        close_5m = df_5m['Close']
        close_15m = df_15m['Close']

        if len(close_5m.shape) > 1:
            close_5m = close_5m.squeeze()

        if len(close_15m.shape) > 1:
            close_15m = close_15m.squeeze()

        # 🔥 INDICATORS (5m)
        rsi = ta.momentum.RSIIndicator(close_5m).rsi()
        macd_obj = ta.trend.MACD(close_5m)

        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()

        # 🔥 TREND (15m EMA)
        ema_15m = ta.trend.EMAIndicator(close_15m, window=200).ema_indicator()

        # LAST VALUES
        price = float(close_5m.iloc[-1])
        rsi_val = float(rsi.iloc[-1])
        macd_val = float(macd.iloc[-1])
        macd_sig = float(macd_signal.iloc[-1])
        ema_trend = float(ema_15m.iloc[-1])
        trend_price = float(close_15m.iloc[-1])

        signal = None

        # 🟢 BUY
        if trend_price > ema_trend and rsi_val < 35 and macd_val > macd_sig:
            signal = "BUY"

        # 🔴 SELL
        elif trend_price < ema_trend and rsi_val > 65 and macd_val < macd_sig:
            signal = "SELL"

        # 🚫 Duplicate avoid
        if signal == last_signal or signal is None:
            return None

        last_signal = signal

        # 🎯 TP / SL
        if signal == "BUY":
            msg = f"""
🟢 MULTI-TF BUY — ETH

Entry : {price:.2f}
TP1   : {price+20:.2f}
TP2   : {price+40:.2f}
SL    : {price-15:.2f}

RSI   : {rsi_val:.2f}
Trend : 15m UP 📈
"""

        else:
            msg = f"""
🔴 MULTI-TF SELL — ETH

Entry : {price:.2f}
TP1   : {price-20:.2f}
TP2   : {price-40:.2f}
SL    : {price+15:.2f}

RSI   : {rsi_val:.2f}
Trend : 15m DOWN 📉
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
