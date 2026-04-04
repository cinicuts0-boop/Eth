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
    pnl = (wins * 20) - (loss * 10)
    acc = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(acc, 2)

# 🔹 SIGNAL (PRO)
def get_signal_for(symbol, name):
    global last_signal

    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        df = df.dropna()

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # FIX
        close = close.squeeze()
        high = high.squeeze()
        low = low.squeeze()
        volume = volume.squeeze()

        if len(close) < 100:
            return

        # INDICATORS
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        ema50 = close.ewm(span=50).mean().iloc[-1]
        ema200 = close.ewm(span=200).mean().iloc[-1]

        vol_avg = volume.rolling(20).mean().iloc[-1]
        volume_ok = volume.iloc[-1] > vol_avg

        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close
        ).average_true_range().iloc[-1]

        price = float(close.iloc[-1])

        signal = "WAITING"

        # 🔥 PRO LOGIC
        if 45 < rsi < 55:
            signal = "WAITING"

        elif (
            rsi < 35 and
            macd_val > macd_sig and
            price > ema50 and
            ema50 > ema200 and
            volume_ok
        ):
            signal = "BUY 🔥"

        elif (
            rsi > 65 and
            macd_val < macd_sig and
            price < ema50 and
            ema50 < ema200 and
            volume_ok
        ):
            signal = "SELL 🔥"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "signal": signal
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            # ATR SL/Target
            if "BUY" in signal:
                sl = price - atr
                target = price + (atr * 2)
            else:
                sl = price + atr
                target = price - (atr * 2)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"""
🚀 {name} PRO SIGNAL
Type: {signal}
Entry: {price:.2f}
Target: {target:.2f}
SL: {sl:.2f}
RSI: {round(rsi,2)}
"""
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE
def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":

            price = latest_data.get(trade["coin"], {}).get("price", 0)

            if "BUY" in trade["type"]:
                if price >= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price <= trade["sl"]:
                    trade["result"] = "LOSS ❌"

            elif "SELL" in trade["type"]:
                if price <= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price >= trade["sl"]:
                    trade["result"] = "LOSS ❌"

# 🔹 LOOP
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD", "ETH")
            get_signal_for("BTC-USD", "BTC")
            get_signal_for("^NSEI", "NIFTY")
            get_signal_for("^NSEBANK", "BANKNIFTY")
            get_signal_for("CL=F", "CRUDE")

            update_results()
            print("Updated PRO...")
            time.sleep(300)

        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 UI
def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;margin:0;}
    .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;padding:10px;}
    .card {background:#1e293b;padding:15px;border-radius:12px;}
    </style>
    """

def header():
    return "<h2>🚀 PRO Trading Dashboard</h2><hr>"

@app.route("/")
def home():
    cards = ""
    for coin, d in latest_data.items():
        cards += f"""
        <div class="card">
        <h3>{coin}</h3>
        <p>{d['price']}</p>
        <p>{d['signal']}</p>
        </div>
        """
    return f"<html>{style()}<body>{header()}<div class='grid'>{cards}</div></body></html>"

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
