import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 💰 ACCOUNT SETTINGS
account_balance = 10000
risk_per_trade = 0.02

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
last_signal = {}

# TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except Exception as e:
        print("Telegram Error:", e)

# SIGNAL
def get_signal(symbol, name):

    global account_balance

    try:
        df = yf.download(
            symbol,
            period="1d",
            interval="5m",
            progress=False
        )

        if df.empty:
            return

        close = df["Close"].squeeze().dropna()

        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd = ta.trend.MACD(close)

        rsi_val = rsi.iloc[-1]
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]
        price = close.iloc[-1]

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

            # 💰 Risk Calculation
            risk_amount = account_balance * risk_per_trade

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            sl_distance = abs(price - sl)

            lot_size = risk_amount / sl_distance if sl_distance != 0 else 0

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price,2),
                "sl": sl,
                "target": target,
                "lot": round(lot_size,2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"""
{name} SIGNAL

Type: {signal}
Entry: {price:.2f}
Target: {target}
SL: {sl}
Lot: {round(lot_size,2)}
"""

            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# RESULT UPDATE
def update_results():

    global account_balance

    for trade in trade_history:

        if trade["result"] != "OPEN":
            continue

        price = latest_data[trade["coin"]]["price"]

        entry = trade["price"]
        lot = trade["lot"]

        # 💰 PnL Calculation
        if trade["type"] == "BUY":
            pnl = (price - entry) * lot
        else:
            pnl = (entry - price) * lot

        trade["pnl"] = round(pnl,2)

        if trade["type"] == "BUY":

            if price >= trade["target"]:
                trade["result"] = "WIN ✅"
                account_balance += pnl

            elif price <= trade["sl"]:
                trade["result"] = "LOSS ❌"
                account_balance += pnl

        if trade["type"] == "SELL":

            if price <= trade["target"]:
                trade["result"] = "WIN ✅"
                account_balance += pnl

            elif price >= trade["sl"]:
                trade["result"] = "LOSS ❌"
                account_balance += pnl

# BOT LOOP
def run_bot():

    while True:

        get_signal("ETH-USD","ETH")
        get_signal("BTC-USD","BTC")

        update_results()

        time.sleep(300)

# DASHBOARD
@app.route("/")
def home():

    cards=""

    for coin,data in latest_data.items():

        color="#FFD700"

        if data["signal"]=="BUY":
            color="#22c55e"

        if data["signal"]=="SELL":
            color="#ef4444"

        cards+=f"""
        <a href="/coin/{coin}">
        <div class="box">
        <h3>{coin}</h3>
        <p>{data['price']}</p>
        <p style="color:{color}">
        {data['signal']}
        </p>
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

    a {{
        text-decoration:none;
        color:#FFD700;
    }}

    </style>

    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>

    <h3>Balance: ₹{round(account_balance,2)}</h3>

    {cards}

    </body>

    </html>
    """

# COIN PAGE
@app.route("/coin/<name>")
def coin_page(name):

    history=""

    for t in trade_history:

        if t["coin"]==name:

            history+=f"""
            <p>
            {t['time']} |
            {t['type']} @ {t['price']}
            → {t['result']}
            | Lot: {t['lot']}
            | PnL: {t.get('pnl',0)}
            </p>
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

    </style>

    <body>

    <h2>{name}</h2>

    {history if history else "<p>No Trades</p>"}

    <br>

    <a href="/">⬅ Back</a>

    </body>

    </html>
    """

# MAIN
if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=8080
    )
