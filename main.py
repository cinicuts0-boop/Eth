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
    global latest_data, trade_history, last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

if df is None or df.empty:
    return

df = df.dropna()

if len(df) < 50:
    return

close = df['Close']
high = df['High']
low = df['Low']
volume = df['Volume']

# 🔥 FIX
if len(close.shape) > 1:
    close = close.squeeze()
if len(high.shape) > 1:
    high = high.squeeze()
if len(low.shape) > 1:
    low = low.squeeze()
if len(volume.shape) > 1:
    volume = volume.squeeze()
        # 🔹 INDICATORS
        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        ema_50 = close.ewm(span=50).mean().iloc[-1]

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        # 🔹 VOLUME CHECK
        vol_avg = volume.rolling(20).mean().iloc[-1]
        volume_ok = volume.iloc[-1] > vol_avg

        # 🔹 ATR (Dynamic SL/Target)
        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close
        ).average_true_range().iloc[-1]

        # 🔹 SIGNAL LOGIC
        signal = "WAITING"

        # ❌ Sideways avoid
        if 45 < rsi_val < 55:
            signal = "WAITING"

        elif (
            rsi_val < 35 and
            macd_val > macd_sig and
            price > ema_50 and
            volume_ok
        ):
            signal = "BUY"

        elif (
            rsi_val > 65 and
            macd_val < macd_sig and
            price < ema_50 and
            volume_ok
        ):
            signal = "SELL"

        # 🔹 SAVE DATA
        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        # 🔁 Duplicate avoid
        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            # 🔹 ATR SL/Target
            if signal == "BUY":
                sl = round(price - atr, 2)
                target = round(price + (atr * 2), 2)
            else:
                sl = round(price + atr, 2)
                target = round(price - (atr * 2), 2)

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
RSI: {round(rsi_val,2)}
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

# 🔹 HOME (GOLD UI)
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

  # 🔹 RULES PAGE
@app.route("/rules")
def rules_page():
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}
            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                margin: 10px auto;
                width: 90%;
                border: 1px solid #FFD700;
            }}
            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        {common_header()}
        <div class="box">
            <h3>📜 Contact / Rules</h3>
            <p>For any queries, contact Mani via Telegram or email.</p>
            <p>All trading signals are educational; trade at your own risk.</p>
        </div>
        <br>
        <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 TRICKS / DMCA PAGE
@app.route("/tricks")
def tricks_page():
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}
            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                margin: 10px auto;
                width: 90%;
                border: 1px solid #FFD700;
            }}
            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>{common_header()}
        <div class="box">
            <h3>🛡️ DMCA / Tricks</h3>
            <p>All content on this website is protected. Please respect copyrights.</p>
            <p>Do not copy or redistribute without permission.</p>
        </div>
        <br>
        <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, accuracy = calculate_stats()

    history = "".join([
        f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    symbol = chart_map.get(name)

    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;text-align:center;">
    {common_header()}

    <h2>{name}</h2>
    <p>Price: {data.get('price')}</p>
    <p>RSI: {data.get('rsi')}</p>
    <p>Signal: {data.get('signal')}</p>

    <h3>📊 Performance</h3>
    <p>Accuracy: {accuracy}%</p>
    <p>PnL: {pnl}</p>

    <h3>📈 Chart</h3>
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"
    width="100%" height="300"></iframe>

    <h3>📜 History</h3>
    {history if history else "<p>No trades</p>"}

    <a href="/">⬅ Back</a>
    </body>
    </html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
