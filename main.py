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
    pnl = (wins * 10) - (loss * 10)
    acc = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(acc, 2)

# 🔹 SIGNAL LOGIC (IMPROVED)
def get_signal_for(symbol, name):
    global last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df.empty:
            return

        df = df.dropna()

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        if len(close.shape) > 1:
            close = close.squeeze()

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        price = close.iloc[-1]

        # ATR for SL/Target
        atr = ta.volatility.AverageTrueRange(high, low, close).average_true_range().iloc[-1]

        signal = "WAITING"

        if rsi < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 65 and macd_val < macd_sig:
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
                target = round(price + atr * 2, 2)
            else:
                sl = round(price + atr, 2)
                target = round(price - atr * 2, 2)

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
            price = latest_data[trade["coin"]]["price"]

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

# 🔹 BOT LOOP
def run_bot():
    while True:
        get_signal_for("ETH-USD", "ETH")
        get_signal_for("BTC-USD", "BTC")
        get_signal_for("^NSEI", "NIFTY")
        get_signal_for("^NSEBANK", "BANKNIFTY")
        get_signal_for("CL=F", "CRUDE")

        update_results()
        time.sleep(300)

# 🔹 UI STYLE
def style():
    return """
    <style>
    body {background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}
    .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;}
    .card {background:#1e293b;padding:15px;border-radius:10px;}
    a {color:#FFD700;text-decoration:none;}
    </style>
    """

# 🔹 HEADER
def header():
    return """
    <h1>🚀 Mani Trading Dashboard</h1>
    <a href="/">Home</a> |
    <a href="/signals">Signals</a>
    <hr>
    """

# 🔹 HOME
@app.route("/")
def home():
    cards = ""
    for c, d in latest_data.items():
        cards += f"""
        <a href="/coin/{c}">
        <div class="card">
        <h3>{c}</h3>
        <p>{d['price']}</p>
        <p>{d['signal']}</p>
        </div></a>
        """
    return f"<html>{style()}<body>{header()}<div class='grid'>{cards}</div></body></html>"

# 🔹 SIGNAL PAGE
@app.route("/signals")
def signals():
    msgs = "".join([f"<p>{m['time']} → {m['msg']}</p>" for m in telegram_messages[::-1]])
    return f"<html>{style()}<body>{header()}<h3>Signals</h3>{msgs}</body></html>"

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    history = "".join([
        f"<p>{t['time']} | {t['type']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    return f"""
    <html>{style()}
    <body>{header()}
    <h2>{name}</h2>
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>

    <h3>📊 Performance</h3>
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>

    <h3>📈 Chart</h3>
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={chart_map.get(name)}&interval=5&theme=dark"
    width="100%" height="300"></iframe>

    <h3>📜 Trade History</h3>
    {history if history else "No trades"}

    </body></html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
