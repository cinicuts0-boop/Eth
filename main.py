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
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
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

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        df = df.dropna()

        close = df['Close']
        high = df['High']
        low = df['Low']

        if len(close.shape) > 1:
            close = close.squeeze()
        if len(high.shape) > 1:
            high = high.squeeze()
        if len(low.shape) > 1:
            low = low.squeeze()

        if len(close) < 50:
            return

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        ema = close.ewm(span=50).mean().iloc[-1]
        price = float(close.iloc[-1])

        signal = "WAITING"

        if 45 < rsi < 55:
            signal = "WAITING"
        elif rsi < 35 and macd_val > macd_sig and price > ema:
            signal = "BUY"
        elif rsi > 65 and macd_val < macd_sig and price < ema:
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

            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 20 if signal == "BUY" else price - 20

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"{name} {signal} @ {price:.2f}"
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
            elif trade["type"] == "SELL":
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

# 🔹 STYLE
def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {background:#0f172a;color:#FFD700;font-family:Arial;margin:0;text-align:center;}
    .nav {display:flex;justify-content:center;gap:10px;margin:10px;}
    .nav a {padding:8px;background:#1e293b;border-radius:8px;color:#FFD700;text-decoration:none;}
    .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;padding:10px;}
    .card {background:#1e293b;padding:15px;border-radius:10px;}
    .green {color:#22c55e;}
    .red {color:#ef4444;}
    .box {background:#1e293b;margin:10px;padding:10px;border-radius:10px;}
    </style>
    """

# 🔹 HEADER
def header():
    return """
    <h2>🚀 Trading Dashboard</h2>
    <div class="nav">
    <a href="/">Home</a>
    <a href="/signals">Signals</a>
    <a href="/rules">Rules</a>
    </div><hr>
    """

# 🔹 HOME
@app.route("/")
def home():
    cards = ""
    for coin, d in latest_data.items():
        color = "green" if d["signal"]=="BUY" else "red" if d["signal"]=="SELL" else ""

        cards += f"""
        <a href="/coin/{coin}">
        <div class="card">
        <h3>{coin}</h3>
        <p>{d['price']}</p>
        <p class="{color}">{d['signal']}</p>
        </div></a>
        """

    return f"<html>{style()}<body>{header()}<div class='grid'>{cards}</div></body></html>"

# 🔹 SIGNALS
@app.route("/signals")
def signals():
    msgs = "".join([f"<div class='box'>{m['time']} → {m['msg']}</div>" for m in telegram_messages[::-1][:50]])
    return f"<html>{style()}<body>{header()}<h3>Signals</h3>{msgs}</body></html>"

# 🔹 RULES
@app.route("/rules")
def rules():
    return f"<html>{style()}<body>{header()}<div class='box'>Trade at your own risk</div></body></html>"

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    history = "".join([
        f"<div class='box'>{t['time']} | {t['type']} → {t['result']}</div>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    return f"""
    <html>{style()}
    <body>{header()}
    <h2>{name}</h2>
    <div class="box">
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>
    </div>

    <div class="box">
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>
    </div>

    <h3>History</h3>
    {history if history else "No trades"}
    </body></html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
