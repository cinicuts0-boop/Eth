import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
from datetime import datetime
import pytz

app = Flask(__name__)

# 🔐 TELEGRAM
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

# 📊 DATA
latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
}

trade_history = []
last_signal = {}

# 🔊 ALERT
last_alert_time = ""
last_alert_type = ""

# 💰 ACCOUNT
account_balance = 10000
risk_per_trade = 0.02

# ⏰ IST TIME
def get_ist_time():
    return datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")

# 📡 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        print("Telegram Error")

# 📊 STATS
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = sum(t.get("pnl", 0) for t in trade_history)
    acc = (wins / total * 100) if total else 0
    return total, wins, loss, round(pnl, 2), round(acc, 2)

# 📈 SIGNAL
def get_signal(symbol, name):
    global last_alert_time, last_alert_type

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df.empty:
            return

        close = df["Close"].squeeze().dropna()

        if len(close) < 30:
            return

        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close)

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd.macd().iloc[-1])
        macd_sig = float(macd.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"

        if rsi_val < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 65 and macd_val < macd_sig:
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

            last_alert_time = get_ist_time()
            last_alert_type = signal

            msg = f"{name} {signal} @ {price}"
            send_telegram(msg)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "time": get_ist_time(),
                "result": "OPEN"
            })

    except Exception as e:
        print(name, "ERROR:", e)

# 🔁 BOT LOOP
def run_bot():
    while True:
        get_signal("ETH-USD", "ETH")
        get_signal("BTC-USD", "BTC")
        time.sleep(300)

# 🌐 API
@app.route("/data")
def data():
    return {
        "data": latest_data,
        "last_alert_time": last_alert_time,
        "last_alert_type": last_alert_type
    }

# 🏠 DASHBOARD
@app.route("/")
def home():
    cards = ""

    for coin, d in latest_data.items():
        color = "#FFD700"
        if d["signal"] == "BUY":
            color = "green"
        elif d["signal"] == "SELL":
            color = "red"

        cards += f"""
        <div>
        <h2>{coin}</h2>
        <p id="{coin}_price">{d['price']}</p>
        <p id="{coin}_signal" style="color:{color}">{d['signal']}</p>
        </div>
        """

    return f"""
    <html>
    <body style="background:black;color:gold;text-align:center">

    <h1>🚀 Trading Dashboard</h1>

    {cards}

    <script>
    function update() {{
        fetch('/data')
        .then(r=>r.json())
        .then(data=>{{
            for (let coin in data.data) {{
                document.getElementById(coin+"_price").innerText = data.data[coin].price;
                document.getElementById(coin+"_signal").innerText = data.data[coin].signal;
            }}
        }});
    }}

    setInterval(update, 5000);
    </script>

    </body>
    </html>
    """

# 🚀 START
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
    
