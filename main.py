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
last_signal_time = {}

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

# 🔹 SIGNAL LOGIC
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_signal_time

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

        try:
            price = float(close.iloc[-1])
        except:
            return

        signal = "WAITING"

        if rsi < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 65 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "signal": signal
        }

        now = time.time()

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            if name in last_signal_time and now - last_signal_time[name] < 600:
                return

            last_signal[name] = signal
            last_signal_time[name] = now

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE
def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":
            price = latest_data.get(trade["coin"], {}).get("price", 0)
            if price == 0:
                continue

            if trade["type"] == "BUY":
                if price >= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price <= trade["sl"]:
                    trade["result"] = "LOSS ❌"
            else:
                if price <= trade["target"]:
                    trade["result"] = "WIN ✅"
                elif price >= trade["sl"]:
                    trade["result"] = "LOSS ❌"

# 🔹 BOT LOOP
def run_bot():
    while True:
        get_signal_for("ETH-USD", "ETH")
        get_signal_for("BTC-USD", "BTC")
        get_signal_for("^NSEI", "NIFTY")
        get_signal_for("^NSEBANK", "BANKNIFTY")
        get_signal_for("CL=F", "CRUDE")

        update_results()
        time.sleep(300)

# 🔹 HOME PAGE
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">

    <style>
    body {{background:#0f172a;color:#FFD700;text-align:center;font-family:Arial;margin:0;}}
    .grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;padding:10px;}}
    .box {{background:#1e293b;padding:15px;border-radius:15px;border:1px solid #FFD700;}}
    a {{color:#FFD700;text-decoration:none;}}
    </style>
    </head>

    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>
    <p>💚 எண்ணம் போல் வாழ்க்கை ❤️</p>

    <div>
        <a href="/signals">Signals</a>
    </div>

    <div class="grid">
    {cards}
    </div>

    <!-- SOUND -->
    <audio id="sound" src="https://www.soundjay.com/buttons/sounds/beep-01a.mp3"></audio>
    <script>
let lastData="";
setInterval(()=>{{
    fetch("/").then(r=>r.text()).then(d=>{{
        if(d!==lastData && (d.includes("BUY")||d.includes("SELL"))){{
            document.getElementById("sound").play();
            lastData=d;
        }}
    }});
}},10000);
</script>

    </body>
    </html>
    """

# 🔹 SIGNAL PAGE
@app.route("/signals")
def signals_page():
    msgs = "".join([
        f"<div class='msg'>{m['msg']}<br><small>{m['time']}</small></div>"
        for m in telegram_messages[::-1][:50]
    ])

    return f"""
    <html>
    <style>
    body {{background:#0f172a;color:white;font-family:Arial;padding:10px;}}
    .msg {{background:#1e293b;margin:8px;padding:10px;border-radius:10px;}}
    </style>
    <body>
    <h2>📩 Signals</h2>
    {msgs}
    <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    chart = {
        "ETH":"BINANCE:ETHUSDT",
        "BTC":"BINANCE:BTCUSDT",
        "NIFTY":"NSE:NIFTY",
        "BANKNIFTY":"NSE:BANKNIFTY",
        "CRUDE":"NYMEX:CL1!"
    }

    return f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="background:#0f172a;color:#FFD700;text-align:center;">
    <h2>{name}</h2>
    <p>Price: {data.get('price')}</p>
    <p>RSI: {data.get('rsi')}</p>
    <p>Signal: {data.get('signal')}</p>

    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>

    <iframe src="https://s.tradingview.com/widgetembed/?symbol={chart.get(name)}&interval=5&theme=dark"
    width="100%" height="250"></iframe>

    <br><a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 RUN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
