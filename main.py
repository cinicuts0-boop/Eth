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

# 🔐 பாதுகாப்புக்கு ENV use பண்ணலாம் (recommended)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("CHAT_ID", "8007854479")


# ⏱ TIME
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%H:%M:%S")

def get_trade_duration(start_time):
    try:
        fmt = "%H:%M:%S"
        now = datetime.strptime(get_ist_time(), fmt)
        start = datetime.strptime(start_time, fmt)
        return str(now - start)
    except:
        return "0:00:00"

# 📊 DATA
latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
telegram_messages = []
last_signal = {}

# 🔊 ALERT
last_alert_time = ""
last_alert_type = ""
last_report_date = ""

# 💰 ACCOUNT
account_balance = 10000
risk_per_trade = 0.02

# 🔹 API
@app.route("/data")
def live_data():
    return {
        "data": latest_data,
        "last_alert_time": last_alert_time,
        "last_alert_type": last_alert_type
    }

# 🔹 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        telegram_messages.append({"msg": msg, "time": get_ist_time()})
    except:
        print("Telegram Error")

# 🔹 STATS
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])

    total_pnl = sum(t.get("live_pnl", 0) for t in trade_history)

    accuracy = (wins / total * 100) if total > 0 else 0
    percent = ((account_balance - 10000) / 10000) * 100

    return total, wins, loss, round(total_pnl,2), round(accuracy,2), round(percent,2)

def today_pnl():
    pnl = 0
    for t in trade_history:
        if t["result"] != "OPEN":
            pnl += t.get("live_pnl", 0)
    return round(pnl, 2)

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global last_alert_time, last_alert_type

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        close = df['Close']
        if hasattr(close, "values") and len(close.shape) > 1:
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

            risk_amount = account_balance * risk_per_trade
            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 10 if signal == "BUY" else price - 10

            lot = risk_amount / abs(price - sl)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "lot": round(lot,2),
                "time": get_ist_time(),
                "result": "OPEN"
            })

            send_telegram(f"{name} {signal} @ {price}")

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 UPDATE
def update_results():
    global account_balance

    for t in trade_history:
        if t["result"] == "OPEN":

            current = latest_data.get(t["coin"], {}).get("price",0)
            if current == 0:
                continue

            entry = t["price"]
            lot = t["lot"]

            pnl = (current - entry)*lot if t["type"]=="BUY" else (entry-current)*lot
            t["live_pnl"] = round(pnl,2)

            if t["type"]=="BUY":
                if current >= t["target"] or current <= t["sl"]:
                    t["result"] = "WIN ✅" if current>=t["target"] else "LOSS ❌"
                    account_balance += pnl

            if t["type"]=="SELL":
                if current <= t["target"] or current >= t["sl"]:
                    t["result"] = "WIN ✅" if current<=t["target"] else "LOSS ❌"
                    account_balance += pnl

# 🔹 DAILY REPORT
def send_daily_report():
    global last_report_date

    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    today = now.strftime("%Y-%m-%d")

    if last_report_date == today:
        return

    if now.hour == 23 and now.minute >= 59:
        total, wins, loss, pnl, acc, percent = calculate_stats()

        msg = f"""
📅 DAILY REPORT
💰 Balance: ₹{account_balance}
📊 Trades: {total}
✅ Wins: {wins}
❌ Loss: {loss}
📈 Accuracy: {acc}%
💸 PnL: {pnl}
📊 Return: {percent}%
"""
        send_telegram(msg)
        last_report_date = today

# 🔹 LOOP
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD","ETH")
            get_signal_for("BTC-USD","BTC")
            get_signal_for("^NSEI","NIFTY")
            get_signal_for("^NSEBANK","BANKNIFTY")

            update_results()
            send_daily_report()

            time.sleep(300)

        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 UI
@app.route("/")
def home():
    cards = ""
    for c,d in latest_data.items():
        cards += f"<p>{c} | {d['price']} | {d['signal']}</p>"

    return f"""
    <h2>🚀 Dashboard</h2>
    {cards}
    """

@app.route("/coin/<name>")
def coin(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, acc, percent = calculate_stats()

    history = "".join([
        f"<p>{t['time']} | {t['type']} | {t.get('live_pnl',0)}</p>"
        for t in trade_history if t["coin"]==name
    ])

    return f"""
    <h2>{name}</h2>
    <p>Price: {data.get('price')}</p>
    <p>Signal: {data.get('signal')}</p>

    <h3>Performance</h3>
    <p>Balance: {account_balance}</p>
    <p>Today PnL: {today_pnl()}</p>

    <h3>History</h3>
    {history}
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
