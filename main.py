
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask

app = Flask(__name__)

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

last_signal = None
latest_data = {
    "price": 0,
    "rsi": 0,
    "signal": "WAITING"
}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)


def get_signal():
    global last_signal, latest_data
    latest_data["price"] = 1234
    latest_data["rsi"] = 50
    latest_data["signal"] = "TEST"

    try:
        df = yf.download("ETH-USD", period="1d", interval="5m")

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

        latest_data = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal == last_signal or signal == "WAITING":
            return None

        last_signal = signal

        msg = f"""
🚨 ETH SIGNAL

Price : {price:.2f}
RSI   : {rsi_val:.2f}

Signal: {signal}
"""

        return msg

    except Exception as e:
        return f"❌ Error: {e}"


# 🌐 DASHBOARD ROUTE
@app.route("/")
def dashboard():
    return f"""
    <html>
    <head>
        <title>ETH Dashboard</title>

        <!-- 📱 Mobile Responsive -->
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: white;
                margin: 0;
                padding: 0;
                text-align: center;
            }}

            h1 {{
                padding: 15px;
                font-size: 20px;
            }}

            .container {{
                padding: 10px;
            }}

            .box {{
                background: #1e293b;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 12px;
            }}

            .price {{
                font-size: 22px;
                font-weight: bold;
            }}

            .buy {{
                color: #22c55e;
                font-weight: bold;
            }}

            .sell {{
                color: #ef4444;
                font-weight: bold;
            }}

            iframe {{
                width: 100%;
                height: 300px;
                border-radius: 10px;
            }}
        </style>
    </head>

    <body>

        <h1>🚀 ETH DASHBOARD</h1>

        <div class="container">

            <div class="box">
                <div class="price">💰 {latest_data['price']}</div>
                <p>RSI: {latest_data['rsi']}</p>
                <p>Signal: 
                    <span class="{latest_data['signal'].lower()}">
                        {latest_data['signal']}
                    </span>
                </p>
                <p>🟢 Status: RUNNING</p>
            </div>

            <div class="box">
                <h3>📈 Live Chart</h3>
                <iframe 
                    src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:ETHUSDT&interval=5&theme=dark">
                </iframe>
            </div>

        </div>

    </body>
    </html>
    """


# 🤖 BOT LOOP
def run_bot():
    while True:
        try:
            msg = get_signal()
            if msg:
                send_telegram(msg)
                print("Sent:", msg)
            else:
                print("No signal...")

            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)


# 🚀 RUN BOTH
if __name__ == "__main__":
    import threading

    # 🤖 Bot backgroundல run ஆகும்
    threading.Thread(target=run_bot).start()

    # 🌐 Flask dashboard run ஆகும்
    import os
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
