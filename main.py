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

# 🔹 SIGNAL LOGIC
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        close = df['Close']

        if len(close.shape) > 1:
            close = close.squeeze()

        close = close.dropna()

        if len(close) < 30:
            return

        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close)

        if rsi.isna().iloc[-1]:
            return

        rsi_val = float(rsi.iloc[-1])
        macd_val = float(macd.macd().iloc[-1])
        macd_sig = float(macd.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"

        # 🔥 Improved logic
        if rsi_val < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 60 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": sl,
                "target": target,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"{name} → {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
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

            print("Updated...")
            time.sleep(300)

        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 HEADER
def common_header():
    return """
    <h2>🚀 Trading Dashboard</h2>
    <a href="/">Home</a> |
    <a href="/signals">Signals</a> |
    <a href="/rules">Rules</a> |
    <a href="/tricks">Tricks</a>
    <hr>
    """

# 🔹 SIGNAL PAGE
@app.route("/signals")
def signals_page():
    msgs = "".join([
        f"<p>{m['time']} → {m['msg']}</p>"
        for m in telegram_messages[::-1][:50]
    ])

    return f"""
    <html><body style="background:black;color:lime;text-align:center;">
    {common_header()}
    <h3>📩 Telegram Signals</h3>
    {msgs if msgs else "<p>No signals</p>"}
    </body></html>
    """

# 🔹 RULES PAGE
@app.route("/rules")
def rules_page():
    return f"""
    <html><body style="background:#0f172a;color:#FFD700;text-align:center;">
    {common_header()}
    <h3>📜 Rules</h3>
    <p>Trade at your own risk</p>
    <a href="/">⬅ Back</a>
    </body></html>
    """

# 🔹 TRICKS PAGE
@app.route("/tricks")
def tricks_page():
    return f"""
    <html><body style="background:#0f172a;color:#FFD700;text-align:center;">
    {common_header()}
    <h3>🛡️ DMCA</h3>
    <p>Do not copy content</p>
    <a href="/">⬅ Back</a>
    </body></html>
    """

# 🔹 HOME
@app.route("/")
def dashboard():
    cards = ""
    for coin, data in latest_data.items():

        color = "white"
        if data["signal"] == "BUY":
            color = "lime"
        elif data["signal"] == "SELL":
            color = "red"

        cards += f"""
        <a href="/coin/{coin}">
        <div style="margin:10px;padding:10px;border:1px solid {color};">
        <h3>{coin}</h3>
        <p>Price: {data['price']}</p>
        <p style="color:{color}">{data['signal']}</p>
        </div>
        </a>
        """

    return f"<html><body style='background:black;color:white;text-align:center;'>{common_header()}{cards}</body></html>"

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})

    history = "".join([
        f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    return f"""
    <html><body style="background:black;color:white;text-align:center;">
    {common_header()}
    <h2>{name}</h2>
    <p>Price: {data.get('price')}</p>
    <p>RSI: {data.get('rsi')}</p>
    <p>Signal: {data.get('signal')}</p>

    <h3>📜 History</h3>
    {history if history else "<p>No trades</p>"}

    <a href="/">⬅ Back</a>
    </body></html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
