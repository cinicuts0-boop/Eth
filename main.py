import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
from datetime import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
telegram_messages = []
last_signal = {}

last_alert_time = ""
last_alert_type = ""

# 🔹 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

        telegram_messages.append({
            "msg": msg,
            "time": datetime.now().strftime("%H:%M:%S")
        })
    except:
        print("Telegram Failed")

# 🔹 STATS
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# 🔹 SIGNAL
def get_signal(symbol, name):
    global last_alert_time, last_alert_type

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df.empty:
            return

        close = df["Close"].squeeze().dropna()

        if len(close) < 30:
            return

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        macd = ta.trend.MACD(close)

        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        price = float(close.iloc[-1])

        signal = "WAITING"

        if rsi < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 60 and macd_val < macd_sig:
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

            last_alert_time = datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "time": datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            send_telegram(f"{name} {signal} @ {price}")

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT
def update_results():
    for t in trade_history:
        if t["result"] == "OPEN":

            price = latest_data.get(t["coin"], {}).get("price", 0)
            entry = t["price"]

            if t["type"] == "BUY":
                if price >= entry + 10:
                    t["result"] = "WIN ✅"
                elif price <= entry - 10:
                    t["result"] = "LOSS ❌"

            elif t["type"] == "SELL":
                if price <= entry - 10:
                    t["result"] = "WIN ✅"
                elif price >= entry + 10:
                    t["result"] = "LOSS ❌"

# 🔹 LOOP
def run_bot():
    while True:
        get_signal("ETH-USD", "ETH")
        get_signal("BTC-USD", "BTC")
        update_results()
        time.sleep(300)

# 🔹 UI
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
        <div style="border:1px solid gold;margin:10px;padding:10px">
        <h2>{coin}</h2>
        <p>{d['price']}</p>
        <p style='color:{color}'>{d['signal']}</p>
        </div>
        """

    return f"""
    <html>
    <body style="background:black;color:gold;text-align:center">

    <h1>🚀 Mani Bot</h1>

    {cards}

    <script>
    setTimeout(()=>location.reload(),10000)
    </script>

    </body>
    </html>
    """

# 🔹 START
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
