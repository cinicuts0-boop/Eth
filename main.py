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

# 🔹 SIGNAL (PRO VERSION)
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

        # ✅ FIX 1D
        if len(close.shape) > 1:
            close = close.squeeze()
        if len(high.shape) > 1:
            high = high.squeeze()
        if len(low.shape) > 1:
            low = low.squeeze()
        if len(volume.shape) > 1:
            volume = volume.squeeze()

        # 🔹 INDICATORS
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        price = close.iloc[-1]

        # 🔹 VOLUME CONFIRM
        vol_avg = volume.rolling(20).mean().iloc[-1]
        volume_ok = volume.iloc[-1] > vol_avg

        # 🔹 ATR (SMART SL)
        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close
        ).average_true_range().iloc[-1]

        # 🔥 SIGNAL LOGIC
        signal = "WAITING"

        # ❌ SIDEWAYS FILTER
        if 45 < rsi < 55:
            signal = "WAITING"

        # ✅ BUY
        elif (
            rsi < 35 and
            macd_val > macd_sig and
            price > ema20 > ema50 and
            volume_ok
        ):
            signal = "BUY"

        # ✅ SELL
        elif (
            rsi > 65 and
            macd_val < macd_sig and
            price < ema20 < ema50 and
            volume_ok
        ):
            signal = "SELL"

        # 🔹 SAVE
        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "signal": signal
        }

        # 🔁 Duplicate avoid
        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            # 🔥 SL / TARGET
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
RSI: {round(rsi,2)}
"""
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE
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

# 🔹 SIMPLE DASHBOARD
@app.route("/")
def home():
    cards = ""
    for coin, d in latest_data.items():
        color = "#FFD700"
        if d["signal"] == "BUY":
            color = "#22c55e"
        elif d["signal"] == "SELL":
            color = "#ef4444"

        cards += f"""
        <div style='background:#1e293b;padding:15px;margin:10px;border-radius:10px'>
        <h2>{coin}</h2>
        <p>{d['price']}</p>
        <p style='color:{color}'>{d['signal']}</p>
        </div>
        """

    return f"""
    <body style="background:#0f172a;color:#FFD700;text-align:center">
    <h1>🚀 Mani Money Mindset</h1>
    {cards}
    </body>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
