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

# 🔹 SIGNAL (PRO)
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

        # FIX 1D
        if len(close.shape) > 1: close = close.squeeze()
        if len(high.shape) > 1: high = high.squeeze()
        if len(low.shape) > 1: low = low.squeeze()
        if len(volume.shape) > 1: volume = volume.squeeze()

        # INDICATORS
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        price = close.iloc[-1]

        vol_avg = volume.rolling(20).mean().iloc[-1]
        volume_ok = volume.iloc[-1] > vol_avg

        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close
        ).average_true_range().iloc[-1]

        signal = "WAITING"

        if 45 < rsi < 55:
            signal = "WAITING"

        elif rsi < 35 and macd_val > macd_sig and price > ema20 > ema50 and volume_ok:
            signal = "BUY"

        elif rsi > 65 and macd_val < macd_sig and price < ema20 < ema50 and volume_ok:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
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

            if trade["type"] == "BUY":
                if price >= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price <= trade["sl"]:
                    trade["result"] = "LOSS ❌"

            if trade["type"] == "SELL":
                if price <= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price >= trade["sl"]:
                    trade["result"] = "LOSS ❌"

# 🔹 LOOP
def run_bot():
    while True:
        get_signal_for("ETH-USD", "ETH")
        get_signal_for("BTC-USD", "BTC")
        get_signal_for("^NSEI", "NIFTY")
        get_signal_for("^NSEBANK", "BANKNIFTY")
        get_signal_for("CL=F", "CRUDE")

        update_results()
        time.sleep(300)

# 🔹 HEADER
def header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/signals">Signals</a>
        <a href="/rules">Rules</a>
        <a href="/tricks">Tricks</a>
    </div>
    """

# 🔹 STYLE (MOBILE FRIENDLY)
def style():
    return """
    <style>
    body {
        background:#0f172a;
        color:#FFD700;
        font-family:Arial;
        text-align:center;
        margin:0;
    }
    .nav a {
        margin:5px;
        color:#FFD700;
        text-decoration:none;
        font-size:14px;
    }
    .grid {
        display:grid;
        grid-template-columns: repeat(auto-fit, minmax(150px,1fr));
        gap:10px;
        padding:10px;
    }
    .card {
        background:#1e293b;
        padding:15px;
        border-radius:12px;
    }
    </style>
    """

# 🔹 HOME
@app.route("/")
def home():
    cards = ""
    for coin, d in latest_data.items():
        color = "#FFD700"
        if d["signal"] == "BUY": color = "green"
        elif d["signal"] == "SELL": color = "red"

        cards += f"""
        <div class="card">
        <h3>{coin}</h3>
        <p>{d['price']}</p>
        <p style="color:{color}">{d['signal']}</p>
        </div>
        """

    return f"<html>{style()}<body>{header()}<div class='grid'>{cards}</div></body></html>"

# 🔹 SIGNALS
@app.route("/signals")
def signals():
    msgs = "".join([f"<p>{m['time']} → {m['msg']}</p>" for m in telegram_messages[::-1][:50]])
    return f"<html>{style()}<body>{header()}<h3>Signals</h3>{msgs}</body></html>"

# 🔹 RULES
@app.route("/rules")
def rules():
    return f"<html>{style()}<body>{header()}<p>Trade at your own risk</p></body></html>"

# 🔹 TRICKS
@app.route("/tricks")
def tricks():
    return f"<html>{style()}<body>{header()}<p>Protected content</p></body></html>"

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    return f"""
    <html>{style()}
    <body>{header()}
    <h2>{name}</h2>
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>
    </body></html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
