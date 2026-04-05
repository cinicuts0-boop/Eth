
import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

# 🔐 பாதுகாப்புக்கு ENV use பண்ணலாம் (recommended)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("CHAT_ID", "8007854479")


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

# 💰 ACCOUNT SETTINGS
account_balance = 10000   # starting balance
risk_per_trade = 0.02     # 2% risk

# 🔊 NEW
last_alert_time = ""
last_alert_type = ""

@app.route("/data")
def live_data():
    return {
        "data": latest_data,
        "last_alert_time": last_alert_time,
        "last_alert_type": last_alert_type
    }

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

    total_pnl = sum(t.get("pnl", 0) for t in trade_history)

    accuracy = (wins / total * 100) if total > 0 else 0

    # 📊 % RETURN
    initial_balance = 10000
    percent_return = ((account_balance - initial_balance) / initial_balance) * 100

    return total, wins, loss, round(total_pnl, 2), round(accuracy, 2), round(percent_return, 2)

# 🔹 SIGNAL
# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time, last_alert_type

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        close = df['Close']
        if len(close.shape) > 1:
            close = close.squeeze()

        close = close.dropna()
        if len(close) < 30:
            return

        rsi_series = ta.momentum.RSIIndicator(close).rsi()
        macd_obj = ta.trend.MACD(close)

        if rsi_series.isna().iloc[-1]:
            return

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

        # ❗ FIX: indentation correct
        if signal == last_signal.get(name):
            return

        if signal != "WAITING":

            last_signal[name] = signal

            # 🔊 ALERT
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal

            # 💼 LOT SIZE
            risk_amount = account_balance * risk_per_trade

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            sl_distance = abs(price - sl)
            lot_size = risk_amount / sl_distance if sl_distance != 0 else 0

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": sl,
                "target": target,
                "lot": round(lot_size, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE
def update_results():
    global account_balance

    for trade in trade_history:
        if trade["result"] == "OPEN":

            current_price = latest_data.get(trade["coin"], {}).get("price", 0)
            if current_price == 0:
                continue

            entry = trade["price"]
            lot = trade.get("lot", 1)

            # 💰 LIVE PnL
            if trade["type"] == "BUY":
                pnl = (current_price - entry) * lot
            else:
                pnl = (entry - current_price) * lot

            trade["live_pnl"] = round(pnl, 2)

            # 🎯 CLOSE TRADE
            if trade["type"] == "BUY":
                if current_price >= trade["target"]:
                    trade["result"] = "WIN ✅"
                    account_balance += pnl
                elif current_price <= trade["sl"]:
                    trade["result"] = "LOSS ❌"
                    account_balance += pnl

            elif trade["type"] == "SELL":
                if current_price <= trade["target"]:
                    trade["result"] = "WIN ✅"
                    account_balance += pnl
                elif current_price >= trade["sl"]:
                    trade["result"] = "LOSS ❌"
                    account_balance += pnl

# 🔹 BOT LOOP
def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD", "ETH")
            get_signal_for("BTC-USD", "BTC")
            get_signal_for("^NSEI", "NIFTY")
            get_signal_for("^NSEBANK", "BANKNIFTY")
            # get_signal_for("CL=F", "CRUDE")

            update_results()   # ✅ same level

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

# 🔹 HOME (SOUND ADDED)
@app.route("/")
def dashboard():
    cards = ""

    for coin, data in latest_data.items():
        color = "#FFD700"

        if data["signal"] == "BUY":
            color = "#22c55e"
        elif data["signal"] == "SELL":
            color = "#ef4444"

        blink_class = ""
        if data["signal"] == "BUY":
            blink_class = "blink-buy"
        elif data["signal"] == "SELL":
            blink_class = "blink-sell"

        cards += f"""
        <a href="/coin/{coin}">
        <div class="box {blink_class}">
        <h3>{coin}</h3>
        <p id="{coin}_price">{data['price']}</p>
        <p id="{coin}_signal" style="color:{color}">{data['signal']}</p>
        </div>
        </a>
        """

    return f"""
    <html>
    <head>

    <script>
    let lastAlert = "{last_alert_time}";
    let lastType = "{last_alert_type}";
    let prevAlert = localStorage.getItem("lastAlert");

    if (lastAlert !== prevAlert && lastAlert !== "") {{

        let soundFile = "";

        if (lastType === "BUY") {{
            soundFile = "/static/buy.mp3";
        }} else if (lastType === "SELL") {{
            soundFile = "/static/sell.mp3";
        }}

        if (soundFile !== "") {{
            let audio = new Audio(soundFile);
            audio.play();
        }}

        localStorage.setItem("lastAlert", lastAlert);
    }}

    // 🔥 LIVE UPDATE (NO REFRESH)
    function updateData() {{
        fetch('/data')
        .then(res => res.json())
        .then(data => {{

            .then(data => {

    for (let coin in data.data) {

        let price = data.data[coin].price;
        let signal = data.data[coin].signal;

        document.getElementById(coin + "_price").innerText = price;
        document.getElementById(coin + "_signal").innerText = signal;

        let color = "#FFD700";
        if (signal === "BUY") color = "#22c55e";
        if (signal === "SELL") color = "#ef4444";

        document.getElementById(coin + "_signal").style.color = color;
    }

});
    }}

    setInterval(updateData, 5000);
    </script>

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

@keyframes blinkGreen {{
    0% {{ background-color: #1e293b; }}
    50% {{ background-color: #22c55e; }}
    100% {{ background-color: #1e293b; }}
}}

@keyframes blinkRed {{
    0% {{ background-color: #1e293b; }}
    50% {{ background-color: #ef4444; }}
    100% {{ background-color: #1e293b; }}
}}

.blink-buy {{
    animation: blinkGreen 1s infinite;
}}

.blink-sell {{
    animation: blinkRed 1s infinite;
}}
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
    percent = ((account_balance - 10000) / 10000) * 100

    history = "".join([
    f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']} | PnL: {t.get('live_pnl',0)}</p>"
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
        background:#0f172a;
        color:#FFD700;
        font-family: Arial;
        margin:0;
        text-align:center;
    }}

    h1 {{ font-size:20px; }}
    h2 {{ font-size:18px; }}
    p {{ font-size:14px; }}

    .nav {{
        margin:10px;
        font-size:14px;
    }}

    .nav a {{
        padding:6px;
        color:#FFD700;
        text-decoration:none;
    }}

    .box {{
        background:#1e293b;
        margin:10px;
        padding:15px;
        border-radius:15px;
        border:1px solid #FFD700;
    }}

    iframe {{
        width:100%;
        height:250px;
        border:none;
    }}

    a {{
        color:#FFD700;
        text-decoration:none;
        font-size:14px;
    }}

    @media (max-width:600px) {{
        h1 {{ font-size:18px; }}
        h2 {{ font-size:16px; }}
        p {{ font-size:13px; }}
        iframe {{ height:220px; }}
    }}
    </style>
    </head>

    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>
    <p>💚 எண்ணம் போல் வாழ்க்கை ❤️</p>

    <div class="nav">
        <a href="/">Home</a> |
        <a href="/signals">Signals</a> |
        <a href="/rules">Rules</a> |
        <a href="/tricks">Tricks</a>
    </div>

    <div class="box">
        <h2>{name}</h2>
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>Signal: {data.get('signal')}</p>
    </div>

    <div class="box">
    <h3>📊 Performance</h3>
    <p>Balance: ₹{round(account_balance,2)}</p>
    <p>Accuracy: {accuracy}%</p>
    <p>Total PnL: {pnl}</p>
    <p>Return: {round(percent,2)}%</p>
</div>

    <div class="box">
        <h3>📈 Chart</h3>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"></iframe>
    </div>

    <div class="box">
        <h3>📜 History</h3>
        {history if history else "<p>No trades</p>"}
    </div>

    <br>
    <a href="/">⬅ Back</a>

    </body>
    </html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
