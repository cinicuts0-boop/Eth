import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING", "prediction": ""},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING", "prediction": ""},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING", "prediction": ""},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING", "prediction": ""},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING", "prediction": ""}
}

trade_history = []
telegram_messages = []
last_signal = {}

# 🔹 TELEGRAM
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
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
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# 🔹 AI TREND
def get_ai_prediction(close):
    try:
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        if ema20 > ema50:
            return "📈 UP TREND"
        elif ema20 < ema50:
            return "📉 DOWN TREND"
        else:
            return "⚖️ SIDEWAYS"
    except:
        return "N/A"

# 🔹 SIGNAL
def get_signal_for(symbol, name):
    global last_signal

    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        df = df.dropna()
        close = df['Close']

        if len(close.shape) > 1:
            close = close.squeeze()

        if len(close) < 30:
            return

        price = float(close.iloc[-1])

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        prediction = get_ai_prediction(close)

        signal = "WAITING"

        if 45 < rsi < 55:
            signal = "WAITING"
        elif rsi < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 65 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "signal": signal,
            "prediction": prediction
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 20 if signal == "BUY" else price - 20

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            msg = f"{name} → {signal} @ {price:.2f}"
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# 🔹 RESULT UPDATE
def update_results():
    for t in trade_history:
        if t["result"] == "OPEN":

            price = latest_data.get(t["coin"], {}).get("price", 0)

            if t["type"] == "BUY":
                if price >= t["target"]:
                    t["result"] = "WIN ✅"
                elif price <= t["sl"]:
                    t["result"] = "LOSS ❌"

            elif t["type"] == "SELL":
                if price <= t["target"]:
                    t["result"] = "WIN ✅"
                elif price >= t["sl"]:
                    t["result"] = "LOSS ❌"

# 🔹 LOOP
def run_bot():
    while True:
        get_signal_for("ETH-USD", "ETH")
        get_signal_for("BTC-USD", "BTC")
        get_signal_for("^NSEI", "NIFTY")
        get_signal_for("^NSEBANK", "BANKNIFTY")
        get_signal_for("CL=F", "CRUDE")

        update_results()
        time.sleep(300)

# 🔹 STYLE (MOBILE + AUTO REFRESH)
def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <style>
    body {background:black;color:white;text-align:center;font-family:Arial;}
    a {text-decoration:none;color:white;}
    iframe {border:none;border-radius:10px;}
    </style>
    """

# 🔹 HEADER
def common_header():
    return """
    <h2>🚀 Trading Dashboard</h2>
    <a href="/">Home</a> |
    <a href="/signals">Signals</a> |
    <a href="/rules">Rules</a> |
    <a href="/tricks">Tricks</a>
    <hr>
    """

# 🔹 HOME
@app.route("/")
def dashboard():
    cards = ""
    for coin, data in latest_data.items():
        cards += f"""
        <a href="/coin/{coin}">
        <div style="margin:10px;padding:10px;border:1px solid white;">
        <h3>{coin}</h3>
        <p>Price: {data['price']}</p>
        <p>Signal: {data['signal']}</p>
        <p>{data.get('prediction','')}</p>
        </div>
        </a>
        """

    return f"<html>{style()}<body>{common_header()}{cards}</body></html>"

# 🔹 SIGNALS
@app.route("/signals")
def signals_page():
    msgs = "".join([
        f"<p>{m['time']} → {m['msg']}</p>"
        for m in telegram_messages[::-1]
    ])

    return f"<html>{style()}<body>{common_header()}<h3>Signals</h3>{msgs}</body></html>"

# 🔹 RULES
@app.route("/rules")
def rules():
    return f"<html>{style()}<body>{common_header()}<p>Trade at your own risk</p></body></html>"

# 🔹 TRICKS
@app.route("/tricks")
def tricks():
    return f"<html>{style()}<body>{common_header()}<p>Protected content</p></body></html>"

# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    history = "".join([
        f"<p>{t['time']} | {t['type']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    return f"""
    <html>{style()}
    <body>{common_header()}

    <h2>{name}</h2>
    <p>Price: {data.get('price')}</p>
    <p>RSI: {data.get('rsi')}</p>
    <p>Signal: {data.get('signal')}</p>
    <p>{data.get('prediction')}</p>

    <h3>📊 Performance</h3>
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>

    <h3>📈 Live Chart</h3>
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={chart_map.get(name)}&interval=5&theme=dark"
    width="100%" height="300"></iframe>

    <h3>📜 History</h3>
    {history if history else "No trades"}

    </body></html>
    """

# 🔹 MAIN
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
    
