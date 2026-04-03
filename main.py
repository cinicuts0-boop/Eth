
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

# 🔐 Telegram credentials
TOKEN = "abcd"
CHAT_ID = "abcd"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []

# 🔔 Telegram send function
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("Telegram response:", res.json())
    except Exception as e:
        print("Telegram Error:", e)

# 📊 Performance stats
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# 🔥 Signal calculation
def get_signal_for(symbol, name):
    global latest_data, trade_history
    try:
        df = yf.download(symbol, period="1d", interval="5m")
        if df.empty:
            print(name, "data empty")
            return None

        close = df['Close']
        if len(close.shape) > 1:
            close = close.squeeze()

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"
        if rsi_val < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 65 and macd_val < macd_sig:
            signal = "SELL"

        option = ""
        if name in ["NIFTY", "BANKNIFTY"]:
            option = "CE 📈" if signal == "BUY" else "PE 📉" if signal == "SELL" else ""
        elif name == "CRUDE":
            option = "CALL 📈" if signal == "BUY" else "PUT 📉" if signal == "SELL" else ""

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi_val,2), "signal": signal}

        # ✅ Telegram msg auto-send
        if signal != "WAITING":
            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price,2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })
            msg = f"{name} → {signal} ({option}) @ {price:.2f}"
            send_telegram(msg)
            return msg
    except Exception as e:
        print(name, "error:", e)
    return None

# 🔄 Update open trades
def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":
            current_price = latest_data[trade["coin"]]["price"]
            if trade["type"] == "BUY":
                if current_price > trade["price"] + 10:
                    trade["result"] = "WIN ✅"
                elif current_price < trade["price"] - 10:
                    trade["result"] = "LOSS ❌"
            elif trade["type"] == "SELL":
                if current_price < trade["price"] - 10:
                    trade["result"] = "WIN ✅"
                elif current_price > trade["price"] + 10:
                    trade["result"] = "LOSS ❌"

# 🟢 Bot runner
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD", "ETH")
            get_signal_for("BTC-USD", "BTC")
            get_signal_for("^NSEI", "NIFTY")
            get_signal_for("^NSEBANK", "BANKNIFTY")
            get_signal_for("CL=F", "CRUDE")
            update_results()
            print("Updated...")
            time.sleep(300)  # 5 min
        except Exception as e:
            print("Bot Error:", e)
            time.sleep(60)

# 🔥 HOME PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})

    # 🔹 Performance stats
    total, wins, loss, pnl, accuracy = calculate_stats()

    # 🔹 Last 10 trades for this coin
    history_html = "".join([
        f"<p>{t['time']} | {t['coin']} {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    # 🔹 Chart symbol map
    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    symbol = chart_map.get(name)
    timezone = "Asia/Kolkata"  # 🕒 India time zone

    iframe = f"""
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark&timezone={timezone}"
    width="100%" height="300"></iframe>
    """

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
                padding: 15px;
                border-radius: 15px;
                margin: 10px;
                border: 1px solid #FFD700;
            }}
            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>

    <body>

    <h1>{name} DETAILS</h1>

    <div class="box">
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>MACD: {data.get('macd')}</p>
        <p>Signal: {data.get('signal')}</p>
    </div>

    <div class="box">
        <h3>📊 Performance</h3>
        <p>Accuracy: {accuracy}%</p>
        <p>PnL: {pnl}</p>
    </div>

    <div class="box">
        <h3>📈 Chart</h3>
        {iframe}
    </div>

    <div class="box">
        <h3>📜 Last 10 Trades</h3>
        {history_html if history_html else "<p>No trades yet.</p>"}
    </div>

    <br>
    <a href="/">⬅ Back</a>

    </body>
    </html>
    """


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
