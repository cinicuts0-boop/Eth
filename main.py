
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

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
            print(name, "No data")
            return

        close = df['Close']

        # 🔥 FIX (1D conversion)
        if len(close.shape) > 1:
            close = close.squeeze()

        close = close.dropna()

        if len(close) < 30:
            return

        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        if rsi_series.isna().iloc[-1]:
            return

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"

        if rsi_val < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 60 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        # 🔥 duplicate avoid
        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"{name} → {signal} @ {price:.2f}"
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 UPDATE RESULTS
def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":
            current_price = latest_data.get(trade["coin"], {}).get("price", 0)

            if current_price == 0:
                continue

            if trade["type"] == "BUY":
                if current_price > trade["price"] + 10:
                    trade["result"] = "WIN ✅"
                elif current_price < trade["price"] - 10:
                    trade["result"] = "LOSS ❌"

            elif trade["type"] == "SELL":
                if current_price < trade["price"] - 10:
                    trade["result"] = "WIN ✅"
                elif current_price > trade["price"] + 10:
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
        for m in telegram_messages[::-1]
    ])

    return f"""
    <html><body style="background:black;color:lime;text-align:center;">
    {common_header()}
    <h3>📩 Telegram Signals</h3>
    {msgs if msgs else "<p>No signals</p>"}
    </body></html>
    """
     # 🔹 RULES PAGE
@app.route("/Rules")
def rules_page():
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}
            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                margin: 10px auto;
                width: 90%;
                border: 1px solid #FFD700;
            }}
            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        {common_header()}
        <div class="box">
            <h3>📜 Contact / Rules</h3>
            <p>For any queries, contact Mani via Telegram or email.</p>
            <p>All trading signals are educational; trade at your own risk.</p>
        </div>
        <br>
        <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 TRICKS / DMCA PAGE
@app.route("/Tricks")
def tricks_page():
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}
            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                margin: 10px auto;
                width: 90%;
                border: 1px solid #FFD700;
            }}
            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>{common_header()}
        <div class="box">
            <h3>🛡️ DMCA / Tricks</h3>
            <p>All content on this website is protected. Please respect copyrights.</p>
            <p>Do not copy or redistribute without permission.</p>
        </div>
        <br>
        <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 HOME
@app.route("/")
def dashboard():
    cards = ""
    for coin, data in latest_data.items():
        cards += f"""
        <a href="/coin/{coin}">
        <div style="margin:10px;padding:10px;border:1px solid white;">
        <h3>{coin}</h3>
        <p>Price: {data['price']}</p>
        <p>Signal: {data['signal']}</p>
        </div>
        </a>
        """
    return f"<html><body style='background:black;color:white;text-align:center;'>{common_header()}{cards}</body></html>"

# 🔹 COIN PAGE (FIXED)
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})

    return f"""
    <html>
    <body style="background:black;color:white;text-align:center;">
        {common_header()}
        <h2>{name}</h2>
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>Signal: {data.get('signal')}</p>
        <br><a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT, debug=False)
