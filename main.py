
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading

app = Flask(__name__)

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"}
}


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def get_signal_for(symbol, name):
    global latest_data

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

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal != "WAITING":
            return f"{name} → {signal} @ {price:.2f}"

    except Exception as e:
        print(name, "error:", e)

    return None


def run_bot():
    while True:
        try:
            eth_msg = get_signal_for("ETH-USD", "ETH")
            btc_msg = get_signal_for("BTC-USD", "BTC")

            if eth_msg:
                send_telegram("🟢 " + eth_msg)

            if btc_msg:
                send_telegram("🟡 " + btc_msg)

            print("Updated...")

            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)


@app.route("/")
def dashboard():
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: white;
                text-align: center;
            }}
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                padding: 10px;
            }}
            .box {{
                background: #1e293b;
                padding: 15px;
                border-radius: 10px;
            }}
            .buy {{ color: #22c55e; }}
            .sell {{ color: #ef4444; }}
        </style>
    </head>

    <body>

    <h1>🚀 MULTI COIN DASHBOARD</h1>

    <div class="grid">
        <div class="box">
            <h2>ETH</h2>
            <p>{latest_data['ETH']['price']}</p>
            <p>RSI: {latest_data['ETH']['rsi']}</p>
            <p class="{latest_data['ETH']['signal'].lower()}">{latest_data['ETH']['signal']}</p>
        </div>

        <div class="box">
            <h2>BTC</h2>
            <p>{latest_data['BTC']['price']}</p>
            <p>RSI: {latest_data['BTC']['rsi']}</p>
            <p class="{latest_data['BTC']['signal'].lower()}">{latest_data['BTC']['signal']}</p>
        </div>
        <div style="padding:10px;">

    <h3>📈 ETH Chart</h3>
    <iframe 
        src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:ETHUSDT&interval=5&theme=dark" 
        width="100%" 
        height="300">
    </iframe>

    <h3>📈 BTC Chart</h3>
    <iframe 
        src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:BTCUSDT&interval=5&theme=dark" 
        width="100%" 
        height="300">
    </iframe>

</div>
    </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()

    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
