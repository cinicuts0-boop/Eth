import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime
import pytz

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
}

trade_history = []
telegram_messages = []
last_signal = {}

account_balance = 10000
risk_per_trade = 0.02

last_alert_time = ""
last_alert_type = ""
last_report_date = ""

@app.route("/data")
def live_data():
    return {
        "data": latest_data,
        "last_alert_time": last_alert_time,
        "last_alert_type": last_alert_type
    }

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    total_pnl = sum(t.get("live_pnl", 0) for t in trade_history)
    accuracy = (wins / total * 100) if total > 0 else 0
    percent_return = ((account_balance - 10000) / 10000) * 100
    return total, wins, loss, round(total_pnl, 2), round(accuracy, 2), round(percent_return, 2)

def get_signal_for(symbol, name):
    global last_alert_time, last_alert_type

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
        price = float(close.iloc[-1])

        signal = "WAITING"
        if rsi < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 60 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi,2), "signal": signal}

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal

            risk_amount = account_balance * risk_per_trade
            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 10 if signal == "BUY" else price - 10

            lot = risk_amount / abs(price - sl) if price != sl else 0

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "lot": round(lot,2),
                "time": datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            send_telegram(f"{name} {signal} @ {price}")

    except Exception as e:
        print(name, "ERROR:", e)

def update_results():
    global account_balance

    for t in trade_history:
        if t["result"] == "OPEN":
            price = latest_data[t["coin"]]["price"]
            pnl = (price - t["price"]) * t["lot"] if t["type"]=="BUY" else (t["price"] - price) * t["lot"]
            t["live_pnl"] = round(pnl,2)

            if (t["type"]=="BUY" and price>=t["target"]) or (t["type"]=="SELL" and price<=t["target"]):
                t["result"]="WIN ✅"; account_balance += pnl
            elif (t["type"]=="BUY" and price<=t["sl"]) or (t["type"]=="SELL" and price>=t["sl"]):
                t["result"]="LOSS ❌"; account_balance += pnl

def send_daily_report():
    global last_report_date
    now = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
    today = now.strftime("%Y-%m-%d")

    if last_report_date == today:
        return

    if now.hour == 23 and now.minute >= 59:
        total, wins, loss, pnl, acc, percent = calculate_stats()

        msg = f"""
📅 DAILY REPORT
💰 Balance: ₹{round(account_balance,2)}
📊 Trades: {total}
✅ Wins: {wins}
❌ Loss: {loss}
📈 Accuracy: {acc}%
💸 PnL: {pnl}
📊 Return: {percent}%
"""
        send_telegram(msg)
        last_report_date = today

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

@app.route("/")
def dashboard():
    cards = ""
    for coin,data in latest_data.items():
        cards += f"""
        <div class="box">
        <h3>{coin}</h3>
        <p id="{coin}_price">{data['price']}</p>
        <p id="{coin}_signal">{data['signal']}</p>
        </div>
        """

    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;text-align:center;">

    <button onclick="enableSound()">🔊 Enable Sound</button>

    {cards}

    <script>
    let soundEnabled=false;
    function enableSound(){{soundEnabled=true;}}

    function updateData(){{
        fetch('/data').then(r=>r.json()).then(res=>{{
            let data=res.data;

            for (let coin in data){{
                document.getElementById(coin+"_price").innerText=data[coin].price;
                document.getElementById(coin+"_signal").innerText=data[coin].signal;
            }}

            if(soundEnabled && res.last_alert_time){{
                let audio=new Audio("/static/buy.mp3");
                audio.play();
            }}
        }});
    }}

    setInterval(updateData,5000);
    </script>

    </body>
    </html>
    """

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
