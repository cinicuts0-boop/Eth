import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask, send_from_directory
import threading
import datetime

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID_HERE")

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
last_alert_time = ""
last_alert_type = ""

# ===== Global Thresholds =====
rsi_buy_threshold = 35
rsi_sell_threshold = 65
macd_diff_threshold = 0.5

# ===== Telegram Alert =====
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# ===== Signal Calculation =====
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time, last_alert_type
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty:
            return
        close = df['Close'].squeeze().dropna()
        if len(close) < 30:
            return

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        rsi_buy = 35
        rsi_sell = 65
        macd_diff_threshold = 0.5
        macd_diff = macd_val - macd_sig

                # Use user-set thresholds
        if rsi_val < rsi_buy_threshold and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell_threshold and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        latest_data[name] = {"price": round(price, 2), "rsi": round(rsi_val, 2), "signal": signal}

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal

            sl = round(price - 10, 2) if signal == "BUY" else round(price + 10, 2)
            target = round(price + 10, 2) if signal == "BUY" else round(price - 10, 2)

            trade_history.append({"coin": name, "type": signal, "price": round(price, 2),
                                  "sl": sl, "target": target, "time": last_alert_time, "result": "OPEN"})

            msg = f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)
    except Exception as e:
        print(name, "ERROR:", e)

# ===== Update Results =====
def update_results():
    for trade in trade_history:
        if trade["result"] != "OPEN":
            continue
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

# ===== Bot Loop =====
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

# ===== Stats =====
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# ===== Common Header =====
def common_header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">
        <a href="/">Home</a> | <a href="/signals">Signals</a> | 
        <a href="/rules">Rules</a> | <a href="/tricks">Tricks</a>
    </div>
    """

# ===== Home Page =====
@app.route("/", methods=["GET", "POST"])
def home():
    global rsi_buy_threshold, rsi_sell_threshold, macd_diff_threshold

    from flask import request

    # Update thresholds if form submitted
    if request.method == "POST":
        try:
            rsi_buy_threshold = float(request.form.get("rsi_buy", rsi_buy_threshold))
            rsi_sell_threshold = float(request.form.get("rsi_sell", rsi_sell_threshold))
            macd_diff_threshold = float(request.form.get("macd_diff", macd_diff_threshold))
        except:
            pass  # ignore invalid input

    cards = ""
    for coin, data in latest_data.items():
        color = "#FFD700"
        if data["signal"] == "BUY": color = "#22c55e"
        elif data["signal"] == "SELL": color = "#ef4444"
        cards += f"""
        <div class="box">
            <h3>{coin}</h3>
            <p>Price: {data['price']}</p>
            <p style="color:{color}">Signal: {data['signal']}</p>
            <a href="/coin/{coin}">View Details</a>
        </div>
        """

    return f"""
    <html>
    <head>
    <style>
        body {{background:#0f172a;color:#FFD700;text-align:center;font-family:Arial;}}
        .box {{background:#1e293b;padding:20px;margin:10px;border-radius:15px;border:1px solid #FFD700;}}
        a {{color:#FFD700;text-decoration:none;}}
        input {{width:60px;text-align:center;}}
        button {{padding:5px 10px;margin-left:10px;}}
    </style>
    </head>
    <body>
        {common_header()}
        <div class="box">
            <h3>⚙️ Adjust Thresholds</h3>
            <form method="POST">
                RSI Buy: <input name="rsi_buy" value="{rsi_buy_threshold}"/>
                RSI Sell: <input name="rsi_sell" value="{rsi_sell_threshold}"/>
                MACD Diff: <input name="macd_diff" value="{macd_diff_threshold}"/>
                <button type="submit">Update</button>
            </form>
        </div>
        {cards}
        <audio id="buySound" src="/static/buy.mp3"></audio>
        <audio id="sellSound" src="/static/sell.mp3"></audio>
        <script>
            let lastAlert = "{last_alert_time}";
            let lastType = "{last_alert_type}";
            let prevAlert = localStorage.getItem("lastAlert");
            if(lastAlert !== prevAlert && lastAlert !== "") {{
                if(lastType === "BUY") {{ document.getElementById("buySound").play(); }}
                else if(lastType === "SELL") {{ document.getElementById("sellSound").play(); }}
                localStorage.setItem("lastAlert", lastAlert);
            }}
            setInterval(()=>{{ location.reload(); }}, 60000);
        </script>
    </body>
    </html>
    """

# ===== Coin Page =====
@app.route("/coin/<name>")
def coin_page(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, accuracy = calculate_stats()
    chart_map = {"ETH":"BINANCE:ETHUSDT","BTC":"BINANCE:BTCUSDT","NIFTY":"NSE:NIFTY",
                 "BANKNIFTY":"NSE:BANKNIFTY","CRUDE":"NYMEX:CL1!"}
    symbol = chart_map.get(name,"")
    history_html = "".join([f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>"
                            for t in trade_history if t["coin"]==name][-10:])
    html = f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <style>
        body {{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}
        .box {{background:#1e293b;margin:10px;padding:15px;border-radius:15px;border:1px solid #FFD700;}}
        iframe {{width:100%;height:300px;border:none;}}
        a {{color:#FFD700;text-decoration:none;}}
    </style>
    </head>
    <body>
    {common_header()}
    <div class="box">
        <h2>{name}</h2>
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>Signal: {data.get('signal')}</p>
    </div>
    <div class="box">
        <h3>📊 Performance</h3>
        <p>Accuracy: {accuracy}% | PnL: {pnl}</p>
    </div>
    <div class="box">
        <h3>📈 Chart with Signals</h3>
        <iframe id="tv_chart" src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"></iframe>
    </div>
    <div class="box">
        <h3>📜 Trade History</h3>
        {history_html if history_html else "<p>No trades</p>"}
    </div>
    <audio id="buySound" src="/static/buy.mp3"></audio>
    <audio id="sellSound" src="/static/sell.mp3"></audio>
    <script>
        let lastAlert = "{last_alert_time}";
        let lastType = "{last_alert_type}";
        let prevAlert = localStorage.getItem("lastAlert");
        if(lastAlert !== prevAlert && lastAlert !== "") {{
            if(lastType === "BUY") {{ document.getElementById("buySound").play(); }}
            else if(lastType === "SELL") {{ document.getElementById("sellSound").play(); }}
            localStorage.setItem("lastAlert", lastAlert);
        }}
        setInterval(()=>{{ location.reload(); }},60000);
    </script>
    </body>
    </html>
    """
    return html

# ===== Static Files =====
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# ===== Start Bot & Flask =====
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
