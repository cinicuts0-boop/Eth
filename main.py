import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
telegram_messages = []
last_signal = {}

# 🔹 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)

        telegram_messages.append({
            "msg": msg,
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        })
    except Exception as e:
        print("Telegram Error:", e)

# 🔹 STATS
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        df = df.dropna()

        if len(df) < 50:
            return

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # ✅ FIX (1D conversion)
        if len(close.shape) > 1:
            close = close.squeeze()
        if len(high.shape) > 1:
            high = high.squeeze()
        if len(low.shape) > 1:
            low = low.squeeze()
        if len(volume.shape) > 1:
            volume = volume.squeeze()

        # 🔹 INDICATORS
        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        ema_50 = close.ewm(span=50).mean().iloc[-1]

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        # 🔹 VOLUME
        vol_avg = volume.rolling(20).mean().iloc[-1]
        volume_ok = volume.iloc[-1] > vol_avg

        # 🔹 ATR
        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close
        ).average_true_range().iloc[-1]

        # 🔹 SIGNAL LOGIC
        signal = "WAITING"

        if 45 < rsi_val < 55:
            signal = "WAITING"

        elif rsi_val < 35 and macd_val > macd_sig and price > ema_50 and volume_ok:
            signal = "BUY"

        elif rsi_val > 65 and macd_val < macd_sig and price < ema_50 and volume_ok:
            signal = "SELL"

        # 🔹 SAVE DATA
        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            if signal == "BUY":
                sl = round(price - atr, 2)
                target = round(price + (atr * 2), 2)
            else:
                sl = round(price + atr, 2)
                target = round(price - (atr * 2), 2)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": sl,
                "target": target,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"""
🚀 {name} SIGNAL
Type: {signal}
Entry: {price:.2f}
Target: {target}
SL: {sl}
RSI: {round(rsi_val,2)}
"""
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE (same)
def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":

            current_price = latest_data.get(trade["coin"], {}).get("price", 0)
            if current_price == 0:
                continue

            if trade["type"] == "BUY":
                if current_price >= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif current_price <= trade["sl"]:
                    trade["result"] = "LOSS ❌"

            elif trade["type"] == "SELL":
                if current_price <= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif current_price >= trade["sl"]:
                    trade["result"] = "LOSS ❌"

# 🔹 BOT LOOP
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD", "ETH")
            get_signal_for("BTC-USD", "BTC")
            get_signal_for("^NSEI", "NIFTY")
            get_signal_for("^NSEBANK", "BANKNIFTY")
            get_signal_for("CL=F", "CRUDE")

            update_results()
            time.sleep(300)

        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
