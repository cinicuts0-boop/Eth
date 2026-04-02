
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
    <h1>🚀 ETH SIGNAL DASHBOARD</h1>
    <p>Price: {latest_data['price']}</p>
    <p>RSI: {latest_data['rsi']}</p>
    <p>Signal: {latest_data['signal']}</p>
    <p>Status: RUNNING ✅</p>
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
    import os

PORT = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=PORT)
