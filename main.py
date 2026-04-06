import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask, render_template_string, send_from_directory, request
import threading
import datetime

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN_HERE")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID_HERE")

latest_data = {"ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
               "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
               "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
               "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
               "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}}

trade_history = []
telegram_messages = []
last_signal = {}
last_alert_time = ""
last_alert_type = ""

# 🔹 Dynamic Thresholds
thresholds = {"RSI_BUY": 35, "RSI_SELL": 65, "MACD_DIFF": 0.5}

# Telegram Notification
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        telegram_messages.append({"msg": msg, "time": datetime.datetime.now().strftime("%H:%M:%S")})
    except Exception as e:
        print("Telegram Error:", e)

# Stats
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# Signal Calculation
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time, last_alert_type
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty:
            return
        close = df['Close'].squeeze().dropna()
        if len(close) < 30:
            return

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        rsi_buy = thresholds["RSI_BUY"]
        rsi_sell = thresholds["RSI_SELL"]
        macd_diff_threshold = thresholds["MACD_DIFF"]
        macd_diff = macd_val - macd_sig

        if rsi_val < rsi_buy and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        latest_data[name] = {"price": round(price, 2), "rsi": round(rsi_val, 2), "signal": signal}

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            trade_history.append({"coin": name, "type": signal, "price": round(price, 2),
                                  "sl": sl, "target": target, "time": last_alert_time, "result": "OPEN"})

            msg = f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)
    except Exception as e:
        print(name, "ERROR:", e)

# Update Trade Results
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

# Bot Loop
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

# Common Header
def common_header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">
        <a href="/">Home</a> | <a href="/signals">Signals</a> | 
        <a href="/rules">Rules</a> | <a href="/tricks">Tricks</a> |
        <a href="/settings">Settings</a>
    </div>
    """

# Settings Page
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            thresholds["RSI_BUY"] = float(request.form.get("rsi_buy", thresholds["RSI_BUY"]))
            thresholds["RSI_SELL"] = float(request.form.get("rsi_sell", thresholds["RSI_SELL"]))
            thresholds["MACD_DIFF"] = float(request.form.get("macd_diff", thresholds["MACD_DIFF"]))
        except:
            pass
    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;">
    {common_header()}
    <h2>⚙️ Signal Settings</h2>
    <form method="POST">
        <p>RSI Buy Threshold: <input type="number" step="0.1" name="rsi_buy" value="{thresholds['RSI_BUY']}"></p>
        <p>RSI Sell Threshold: <input type="number" step="0.1" name="rsi_sell" value="{thresholds['RSI_SELL']}"></p>
        <p>MACD Diff Threshold: <input type="number" step="0.1" name="macd_diff" value="{thresholds['MACD_DIFF']}"></p>
        <button type="submit">Update</button>
    </form>
    </body>
    </html>
    """

# Start Bot & Flask
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
