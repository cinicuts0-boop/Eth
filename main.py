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

# ⏰ IST
def get_ist_time():
    return datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")

def get_trade_duration(start):
    try:
        fmt = "%H:%M:%S"
        now = datetime.strptime(get_ist_time(), fmt)
        st = datetime.strptime(start, fmt)
        return str(now - st)
    except:
        return "0:00:00"

# 📊 DATA
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

last_alert_time = ""
last_alert_type = ""

account_balance = 10000

# 📡 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        telegram_messages.append({"msg": msg, "time": get_ist_time()})
    except:
        print("Telegram Error")

# 📊 STATS
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = sum(t.get("pnl", 0) for t in trade_history)
    acc = (wins/total*100) if total else 0
    return total, wins, loss, round(pnl,2), round(acc,2)

def today_pnl():
    pnl = sum(t.get("pnl",0) for t in trade_history if t["result"]!="OPEN")
    return round(pnl,2)

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
            "price": round(price,2),
            "rsi": round(float(rsi),2),
            "signal": signal
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = get_ist_time()
            last_alert_type = signal

            sl = price - 10 if signal=="BUY" else price + 10
            target = price + 10 if signal=="BUY" else price - 10

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "time": get_ist_time(),
                "result": "OPEN",
                "pnl": 0
            })

            send_telegram(f"{name} {signal} @ {price}")

    except Exception as e:
        print(name, "ERROR:", e)

# 🔄 UPDATE RESULT
def update_results():
    global account_balance

    for t in trade_history:
        if t["result"]=="OPEN":
            price = latest_data[t["coin"]]["price"]
            entry = t["price"]

            pnl = price-entry if t["type"]=="BUY" else entry-price
            t["pnl"] = round(pnl,2)

            if t["type"]=="BUY":
                if price>=t["target"]:
                    t["result"]="WIN ✅"
                    account_balance+=pnl
                elif price<=t["sl"]:
                    t["result"]="LOSS ❌"
                    account_balance+=pnl

            else:
                if price<=t["target"]:
                    t["result"]="WIN ✅"
                    account_balance+=pnl
                elif price>=t["sl"]:
                    t["result"]="LOSS ❌"
                    account_balance+=pnl

# 🔁 BOT
def run_bot():
    while True:
        get_signal("ETH-USD","ETH")
        get_signal("BTC-USD","BTC")
        get_signal("^NSEI","NIFTY")
        get_signal("^NSEBANK","BANKNIFTY")
        get_signal("CL=F","CRUDE")

        update_results()
        time.sleep(300)

@app.route("/data")
def data():
    return {"data":latest_data}

# 🏠 DASHBOARD
@app.route("/")
def home():
    cards=""
    for c,d in latest_data.items():
        color="#FFD700"
        if d["signal"]=="BUY": color="green"
        elif d["signal"]=="SELL": color="red"

        cards+=f"""
        <a href="/coin/{c}">
        <div class="box">
        <h3>{c}</h3>
        <p>{d['price']}</p>
        <p style="color:{color}">{d['signal']}</p>
        </div></a>
        """

    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;text-align:center">
    <h1>🚀 Dashboard</h1>
    {cards}
    </body>
    </html>
    """

# 📄 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name,{})
    total,wins,loss,pnl,acc = calculate_stats()

    history = "".join([
        f"<p>{t['time']} | {t['type']} → {t['result']} | ⏱ {get_trade_duration(t['time'])} | ₹{t['pnl']}</p>"
        for t in trade_history if t["coin"]==name
    ][-10:])

    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;text-align:center">
    <h2>{name}</h2>
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>

    <h3>📊 Performance</h3>
    <p>Accuracy: {acc}%</p>
    <p>Total PnL: {pnl}</p>
    <p>Today PnL: {today_pnl()}</p>

    <h3>📜 History</h3>
    {history}
    <br><a href="/">Back</a>
    </body>
    </html>
    """

# 🚀 RUN
if __name__=="__main__":
    threading.Thread(target=run_bot,daemon=True).start()
    app.run(host="0.0.0.0",port=8080)
    
