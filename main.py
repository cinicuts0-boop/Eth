
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

# 🔐 பாதுகாப்புக்கு ENV use பண்ணலாம் (recommended)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("CHAT_ID", "8007854479")

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
    wins = sum(1 for t in trade_history if t["result"] == "WIN ✅")
    loss = sum(1 for t in trade_history if t["result"] == "LOSS ❌")

    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0

    return total, wins, loss, pnl, round(accuracy, 2)


# 🔹 SIGNAL ENGINE
def get_signal_for(symbol, name):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        close = df['Close'].dropna()

        if len(close) < 30:
            return

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        macd = ta.trend.MACD(close)

        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        # 🔥 safety check
        if any(map(lambda x: x is None or str(x) == "nan", [rsi, macd_val, macd_sig])):
            return

        price = float(close.iloc[-1])
        rsi_val = float(rsi)

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

        # ❌ Duplicate signal block
        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 10 if signal == "BUY" else price - 10

            trade = {
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            }

            trade_history.append(trade)

            msg = (
                f"🚀 {name} SIGNAL\n"
                f"Type: {signal}\n"
                f"Entry: {price:.2f}\n"
                f"Target: {target:.2f}\n"
                f"SL: {sl:.2f}"
            )

            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)


# 🔹 RESULT CHECK
def update_results():
    for trade in trade_history:
        if trade["result"] != "OPEN":
            continue

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


# 🔹 COMMON HEADER
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


# 🔹 HOME
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
    a {{color:#FFD700;text-decoration:none;}}
    </style>

    <body>
    {common_header()}
    {cards}
    </body>
    </html>
    """


# 🔹 START
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()

    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
