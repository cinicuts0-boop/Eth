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

# 🔊 NEW (sound alert tracking)
last_alert_time = ""

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

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time

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

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            # 🔊 update alert time
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")

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

            msg = f"""
🚀 {name} SIGNAL
Type: {signal}
Entry: {price:.2f}
Target: {target}
SL: {sl}
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

# 🔹 GOLD HEADER
def common_header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">
        <a href="/">Home</a> | 
        <a href="/signals">Signals</a> | 
        <a href="/rules">Rules</a> | 
        <a href="/tricks">Tricks</a>
    </div>
    """

# 🔹 SIGNAL PAGE
@app.route("/signals")
def signals_page():
    msgs = "".join([
        f"<p>{m['time']} → {m['msg']}</p>"
        for m in telegram_messages[::-1][:50]
    ])

    return f"""
    <html>
    <style>
    body {{background:#0f172a;color:#FFD700;text-align:center;}}
    </style>
    <body>
    {common_header()}
    <h3>📩 Signals</h3>
    {msgs if msgs else "<p>No signals</p>"}
    </body></html>
    """

# 🔹 HOME (UPDATED WITH SOUND)
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
        <a href="/coin/{coin}">
        <div class="box">
        <h3>{coin}</h3>
        <p>{data['price']}</p>
        <p style="color:{color}">{data['signal']}</p>
        </div>
        </a>
        """

    return f"""
    <html>
    <head>

    <script>
    let lastAlert = "{last_alert_time}";
    let prevAlert = localStorage.getItem("lastAlert");

    if (lastAlert !== prevAlert && lastAlert !== "") {{
        let audio = new Audio('/static/alert.mp3');
        audio.play();
        localStorage.setItem("lastAlert", lastAlert);
    }}

    setInterval(() => {{
        location.reload();
    }}, 60000);
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
    a {{text-decoration:none;color:#FFD700;}}
    </style>
    </head>
    <body>
    {common_header()}
    {cards}
    </body>
    </html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
