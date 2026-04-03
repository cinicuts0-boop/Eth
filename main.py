
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])

    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0

    return total, wins, loss, pnl, round(accuracy, 2)


def get_signal_for(symbol, name):
    global latest_data, trade_history

    try:
        df = yf.download(symbol, period="1d", interval="5m")

        if df.empty:
            return None

        close = df['Close']
        if len(close.shape) > 1:
            close = close.squeeze()

        rsi = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()

        price = float(close.iloc[-1])
        rsi_val = float(rsi.iloc[-1])
        macd_val = float(macd.iloc[-1])
        macd_sig = float(macd_signal.iloc[-1])

        signal = "WAITING"

        if rsi_val < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 65 and macd_val < macd_sig:
            signal = "SELL"

        # OPTION TEXT
        option = ""
        if name in ["NIFTY", "BANKNIFTY"]:
            option = "CE 📈" if signal == "BUY" else "PE 📉" if signal == "SELL" else ""
        elif name == "CRUDE":
            option = "CALL 📈" if signal == "BUY" else "PUT 📉" if signal == "SELL" else ""

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal != "WAITING":
            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            return f"{name} → {signal} ({option}) @ {price:.2f}"

    except Exception as e:
        print(name, "error:", e)

    return None


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
            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)


# 🔥 HOME PAGE
@app.route("/")
def dashboard():
    cards = ""
    for coin, data in latest_data.items():
        cards += f"""
        <a href="/coin/{coin}">
            <div class="box">
                <h2>{coin}</h2>
                <p>{data['price']}</p>
                <p class="{data['signal'].lower()}">{data['signal']}</p>
            </div>
        </a>
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

            h1 {{
                color: #FFD700;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 12px;
                padding: 12px;
            }}

            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                border: 1px solid #FFD700;
                box-shadow: 0 0 10px rgba(255,215,0,0.2);
                transition: 0.3s;
            }}

            .box:hover {{
                transform: scale(1.05);
            }}

            p {{
                color: #FFD700;
            }}

            .buy {{ color: #22c55e; }}
            .sell {{ color: #ef4444; }}

            a {{
                text-decoration: none;
            }}
        </style>
    </head>

    <body>

    <h1>🎁 Mani Money Mindset 💸</h1>
    <h4>  ꧁༺ 💚 எண்ணம் போல் வாழ்க்கை ❤️ ༻꧂ </h4>

    <div class="grid">
        {cards}
    </div>

    </body>
    </html>
    """


# 🔥 DETAIL PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})

    total, wins, loss, pnl, accuracy = calculate_stats()

    history_html = "".join([
        f"<p>{t['time']} | {t['coin']} {t['type']} @ {t['price']} → {t['result']}</p>"
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
        <p>Signal: {data.get('signal')}</p>
    </div>

    <div class="box">
        <h3>📊 Performance</h3>
        <p>Accuracy: {accuracy}%</p>
        <p>PnL: {pnl}</p>
    </div>

    <div class="box">
        <h3>📈 Chart</h3>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"
        width="100%" height="300"></iframe>
    </div>

    <div class="box">
        <h3>📜 Trade History</h3>
        {history_html}
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
