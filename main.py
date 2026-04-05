import yfinance as yf
import ta
import time
import threading
from flask import Flask

app = Flask(__name__)

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

last_signal = {}

# 🔹 SIGNAL FUNCTION
def get_signal(symbol, name):

    global latest_data, last_signal

    try:
        df = yf.download(
            symbol,
            period="1d",
            interval="5m",
            progress=False
        )

        if df is None or df.empty:
            print(name, "No Data")
            return

        close = df["Close"]

        # Fix multi-dimension issue
        if len(close.shape) > 1:
            close = close.squeeze()

        close = close.dropna()

        if len(close) < 30:
            return

        # RSI
        rsi_series = ta.momentum.RSIIndicator(close).rsi()

        # MACD
        macd_obj = ta.trend.MACD(close)

        rsi_val = float(rsi_series.iloc[-1])
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])

        price = float(close.iloc[-1])

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

        if signal != last_signal.get(name):

            last_signal[name] = signal

            print(
                name,
                "| Price:",
                round(price, 2),
                "| RSI:",
                round(rsi_val, 2),
                "| Signal:",
                signal
            )

    except Exception as e:

        print(name, "ERROR:", e)

# 🔹 BOT LOOP
def run_bot():

    while True:

        get_signal("ETH-USD", "ETH")

        get_signal("BTC-USD", "BTC")

        time.sleep(300)

# 🔹 DASHBOARD UI
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
        <div class="box">
        <h2>{coin}</h2>
        <p>Price: {data['price']}</p>
        <p>RSI: {data['rsi']}</p>
        <p style="color:{color}">
        Signal: {data['signal']}
        </p>
        </div>
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

    </style>

    </head>

    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>

    {cards}

    <script>

    setTimeout(() => {{
        location.reload();
    }}, 60000);

    </script>

    </body>

    </html>
    """

# 🔹 START
if __name__ == "__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=8080
    )
