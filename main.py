import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask, send_from_directory, request
import threading
from datetime import datetime
import pytz

app = Flask(__name__)

# ===== Telegram =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ===== India Time =====
IST = pytz.timezone("Asia/Kolkata")

def india_time():
    return datetime.now(IST)

# ===== Global Variables =====
latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []
last_signal = {}
last_alert_time = {}
last_alert_type = {}

# ===== Thresholds =====
rsi_buy_threshold = 35
rsi_sell_threshold = 65
macd_diff_threshold = 0.5

# ===== Telegram =====
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# ===== Header =====
def common_header(active=None):

    nav_items = [
        ("Home", "/"),
        ("Alerts", "/alerts"),
        ("Rules", "/rules"),
        ("Tricks", "/tricks"),
        ("All Charts", "/signals"),
        ("Stats", "/stats"),
        ("Daily PnL", "/daily_pnl"),
        ("Admin", "/thresholds")
    ]

    nav_html = " | ".join([
        f'<a href="{url}" '
        f'style="color:{"#3b82f6" if name==active else "#FFD700"}">{name}</a>'
        for name, url in nav_items
    ])

    return f"""
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">{nav_html}</div>
    """

# ===== Footer =====
def common_footer(active=None):

    nav_items = [
        ("Home", "/"),
        ("Alerts", "/alerts"),
        ("Charts", "/signals"),
        ("Admin", "/thresholds")
    ]

    nav_html = " | ".join([
        f'<a href="{url}" '
        f'style="color:{"#3b82f6" if name==active else "#FFD700"}">{name}</a>'
        for name, url in nav_items
    ])

    return f"""
    <div class="footer">
        {nav_html}
    </div>
    """

# ===== Signal Engine =====
def get_signal_for(symbol, name):

    global latest_data
    global trade_history
    global last_signal
    global last_alert_time
    global last_alert_type

    try:

        df = yf.download(
            symbol,
            period="1d",
            interval="5m",
            progress=False
        )

        if df is None or df.empty:
            return

        close = df["Close"].squeeze().dropna()

        if len(close) < 30:
            return

        rsi_val = float(
            ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        )

        macd_obj = ta.trend.MACD(close)

        macd_val = float(
            macd_obj.macd().iloc[-1]
        )

        macd_sig = float(
            macd_obj.macd_signal().iloc[-1]
        )

        price = float(close.iloc[-1])

        macd_diff = macd_val - macd_sig

        if rsi_val < rsi_buy_threshold and macd_diff > macd_diff_threshold:
            signal = "BUY"

        elif rsi_val > rsi_sell_threshold and macd_diff < -macd_diff_threshold:
            signal = "SELL"

        else:
            signal = "WAITING"

        latest_data[name] = {
            "price": round(price,2),
            "rsi": round(rsi_val,2),
            "signal": signal
        }

        if signal != "WAITING" and signal != last_signal.get(name):

            last_signal[name] = signal

            ist_time = india_time().strftime("%Y-%m-%d %H:%M:%S")

            last_alert_time[name] = ist_time
            last_alert_type[name] = signal

            sl = round(price-10,2) if signal=="BUY" else round(price+10,2)
            target = round(price+10,2) if signal=="BUY" else round(price-10,2)

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "time": ist_time,
                "result": "OPEN"
            })

            msg=f"""
🚀 {name} SIGNAL
Type: {signal}
Entry: {price}
Target: {target}
SL: {sl}
"""

            send_telegram(msg)

    except Exception as e:
        print(name,"ERROR:",e)

# ===== Update Results =====
def update_results():

    for trade in trade_history:

        if trade["result"]!="OPEN":
            continue

        current_price = latest_data.get(
            trade["coin"],{}
        ).get("price",0)

        if current_price==0:
            continue

        if trade["type"]=="BUY":

            if current_price >= trade["target"]:
                trade["result"]="WIN ✅"

            elif current_price <= trade["sl"]:
                trade["result"]="LOSS ❌"

        elif trade["type"]=="SELL":

            if current_price <= trade["target"]:
                trade["result"]="WIN ✅"

            elif current_price >= trade["sl"]:
                trade["result"]="LOSS ❌"

# ===== Bot Loop =====
def run_bot():

    while True:

        try:

            get_signal_for("ETH-USD","ETH")
            get_signal_for("BTC-USD","BTC")
            get_signal_for("^NSEI","NIFTY")
            get_signal_for("^NSEBANK","BANKNIFTY")
            get_signal_for("CL=F","CRUDE")

            update_results()

            time.sleep(300)

        except Exception as e:

            print("BOT ERROR:",e)

            time.sleep(60)

# ===== Home =====
@app.route("/")
def home():

    cards=""

    for coin,data in latest_data.items():

        color="#FFD700"

        if data["signal"]=="BUY":
            color="#22c55e"

        elif data["signal"]=="SELL":
            color="#ef4444"

        cards+=f"""
        <div class="box">
            <h3>{coin}</h3>
            <p>Price: {data['price']}</p>
            <p style="color:{color}">
            Signal: {data['signal']}
            </p>
            <a href="/coin/{coin}">
            View Details
            </a>
        </div>
        """

    return f"""
    <html>

    <head>

    <meta name="viewport"
    content="width=device-width, initial-scale=1.0">

    <style>

    body{{
    background:#0f172a;
    color:#FFD700;
    font-family:Arial;
    text-align:center;
    }}

    .container{{
    display:flex;
    flex-wrap:wrap;
    justify-content:center;
    }}

    .box{{
    background:#1e293b;
    padding:20px;
    margin:10px;
    border-radius:15px;
    border:1px solid #FFD700;
    min-width:200px;
    }}

    .footer{{
    position: fixed;
    bottom: 0;
    width: 100%;
    background:#020617;
    padding:10px;
    border-top:1px solid #FFD700;
    }}

    a{{
    color:#FFD700;
    text-decoration:none;
    }}

    </style>

    </head>

    <body>

    {common_header("Home")}

    <div class="container">

    {cards}

    </div>

    {common_footer("Home")}

    </body>

    </html>
    """

# ===== Start =====
if __name__=="__main__":

    threading.Thread(
        target=run_bot,
        daemon=True
    ).start()

    PORT=int(os.environ.get("PORT",8080))

    app.run(
        host="0.0.0.0",
        port=PORT
    )
