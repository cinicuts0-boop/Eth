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

# 🔐 ENV
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

# ⏱ TIME
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%H:%M:%S")

# 📊 DATA
latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
last_signal = {}

# 🔊 ALERT
last_alert_time = ""
last_alert_type = ""

# 💰 ACCOUNT
account_balance = 10000
risk_per_trade = 0.02

# 🔹 API
@app.route("/data")
def live_data():
    return {"data": latest_data}

# 🔹 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        print("Telegram error")

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global last_alert_time, last_alert_type

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

        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close)

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd.macd().iloc[-1])
        macd_sig = float(macd.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"

        if rsi_val < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 60 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price,2),
            "rsi": round(rsi_val,2),
            "signal": signal
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = get_ist_time()
            last_alert_type = signal

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "time": get_ist_time()
            })

            send_telegram(f"{name} {signal} @ {price}")

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 BOT LOOP
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD","ETH")
            get_signal_for("BTC-USD","BTC")
            get_signal_for("^NSEI","NIFTY")
            get_signal_for("^NSEBANK","BANKNIFTY")

            time.sleep(300)

        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 DASHBOARD (OLD STYLE GOLD)
@app.route("/")
def dashboard():
    cards = ""

    for coin, data in latest_data.items():
        color = "#FFD700"

        if data["signal"] == "BUY":
            color = "#22c55e"
        elif data["signal"] == "SELL":
            color = "#ef4444"

        cards += f"""
        <div class="box">
        <h3>{coin}</h3>
        <p id="{coin}_price">{data['price']}</p>
        <p id="{coin}_signal" style="color:{color}">{data['signal']}</p>
        </div>
        """

    return f"""
    <html>
    <head>

    <script>
    function updateData() {{
        fetch('/data')
        .then(res => res.json())
        .then(data => {{

            for (let coin in data.data) {{

                let price = data.data[coin].price;
                let signal = data.data[coin].signal;

                document.getElementById(coin + "_price").innerText = price;
                document.getElementById(coin + "_signal").innerText = signal;

                let color = "#FFD700";
                if (signal === "BUY") color = "#22c55e";
                if (signal === "SELL") color = "#ef4444";

                document.getElementById(coin + "_signal").style.color = color;
            }}
        }});
    }}

    setInterval(updateData, 5000);
    </script>

    <style>
    body {{
        background:#0f172a;
        color:#FFD700;
        text-align:center;
        font-family:Arial;
    }}

    .box {{
        background:#1e293b;
        padding:20px;
        margin:10px;
        border-radius:15px;
        border:1px solid #FFD700;
    }}
    </style>

    </head>
    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>

    {cards}

    </body>
    </html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
