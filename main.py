import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask, send_from_directory, request
import threading
import datetime
import pytz  # For India timezone

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("CHAT_ID", "8007854479")

# ===== Global Variables =====
latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}
trade_history = []
last_signal = {}
last_alert_time = ""
last_alert_type = ""

# ===== Thresholds =====
rsi_buy_threshold = 35
rsi_sell_threshold = 65
macd_diff_threshold = 0.5

# ===== Telegram Alert =====
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# ===== India Time =====
def india_time():
    return datetime.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M:%S")

# ===== Common Header =====
def common_header(active=None):
    nav_items = [
        ("Home", "/"),
        ("Alerts", "/alerts"),
        ("Rules", "/rules"),
        ("Tricks", "/tricks"),
        ("All Charts", "/signals"), 
        ("Admin", "/thresholds")
    ]
    nav_html = " | ".join([
        f'<a href="{url}" style="color:{"#3b82f6" if name==active else "#FFD700"}">{name}</a>'
        for name, url in nav_items
    ])
    return f"""
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">{nav_html}</div>
    """

# ===== Bot Signal Calculation =====
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
        macd_diff = macd_val - macd_sig

        if rsi_val < rsi_buy_threshold and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell_threshold and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        latest_data[name] = {"price": round(price, 2), "rsi": round(rsi_val, 2), "signal": signal}

        if signal != "WAITING" and signal != last_signal.get(name):
            last_signal[name] = signal
            last_alert_time = india_time()
            last_alert_type = signal

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            trade_history.append({
                "coin": name, "type": signal, "price": round(price, 2),
                "sl": sl, "target": target, "time": last_alert_time, "result": "OPEN"
            })

            msg = f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)
    except Exception as e:
        print(name, "ERROR:", e)

# ===== Update Trade Results =====
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

# ===== Stats =====
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# ===== Bot Loop =====
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

# ===== Blink Script =====
def blink_script():
    return f"""
    <script>
    let lastAlert = "{last_alert_time}";
    let lastType = "{last_alert_type}";
    let prevAlert = localStorage.getItem("lastAlert");
    if(lastAlert !== prevAlert && lastAlert !== "") {{
        localStorage.setItem("lastAlert", lastAlert);
        let boxes = document.querySelectorAll(".box");
        if(boxes.length>0){{
            let box = boxes[0];
            if(lastType==="BUY"){{box.classList.add("blink-buy");document.getElementById("buySound").play();}}
            if(lastType==="SELL"){{box.classList.add("blink-sell");document.getElementById("sellSound").play();}}
            setTimeout(()=>{{box.classList.remove("blink-buy","blink-sell");}},1000);
        }}
    }}
    setInterval(()=>{{location.reload();}},60000);
    </script>
    """

# ===== Flask Pages =====

# Home, Alerts, Rules, Tricks, Thresholds, Signals, Coin pages
# (Integrate blink, India time, sound for alerts, as in previous code)

# === Start Bot & Flask ===
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
