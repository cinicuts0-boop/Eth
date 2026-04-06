import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

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
last_alert_time = ""
last_alert_type = ""

# 🔹 Telegram
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

# 🔹 Stats
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

# 🔹 Signal generator
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time, last_alert_type
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty:
            return
        close = df['Close'].dropna()
        if len(close.shape) > 1:
            close = close.iloc[:, 0]
        close = close.values.flatten()
        if len(close) < 30:
            return

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        macd_diff = macd_val - macd_sig
        price = float(close[-1])

        rsi_buy, rsi_sell = 35, 65
        macd_diff_threshold = 0.5

        if rsi_val < rsi_buy and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        df_15 = yf.download(symbol, period="1d", interval="15m", progress=False)
        if df_15 is not None and not df_15.empty:
            close_15 = df_15['Close'].dropna()
            if len(close_15.shape) > 1:
                close_15 = close_15.iloc[:, 0]
            close_15 = close_15.values.flatten()
            if len(close_15) >= 30:
                rsi_15 = float(ta.momentum.RSIIndicator(close_15).rsi().iloc[-1])
                macd_obj_15 = ta.trend.MACD(close_15)
                macd_15 = float(macd_obj_15.macd().iloc[-1])
                macd_sig_15 = float(macd_obj_15.macd_signal().iloc[-1])
                macd_diff_15 = macd_15 - macd_sig_15

                if signal == "BUY" and not (rsi_15 < rsi_buy and macd_diff_15 > macd_diff_threshold):
                    signal = "WAITING"
                elif signal == "SELL" and not (rsi_15 > rsi_sell and macd_diff_15 < -macd_diff_threshold):
                    signal = "WAITING"

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi_val,2), "signal": signal}

        if signal == last_signal.get(name):
            return
        if signal != "WAITING":
            last_signal[name] = signal
            last_alert_time = datetime.datetime.now().strftime("%H:%M:%S")
            last_alert_type = signal
            sl = round(price-10,2) if signal=="BUY" else round(price+10,2)
            target = round(price+10,2) if signal=="BUY" else round(price-10,2)
            trade_history.append({"coin":name,"type":signal,"price":round(price,2),"sl":sl,"target":target,"time":datetime.datetime.now().strftime("%H:%M:%S"),"result":"OPEN"})
            msg=f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)

    except Exception as e:
        print(name,"ERROR:", e)

# 🔹 Update open trades
def update_results():
    for trade in trade_history:
        if trade["result"]=="OPEN":
            current_price = latest_data.get(trade["coin"],{}).get("price",0)
            if current_price==0:
                continue
            if trade["type"]=="BUY":
                if current_price>=trade["target"]:
                    trade["result"]="WIN ✅"
                elif current_price<=trade["sl"]:
                    trade["result"]="LOSS ❌"
            elif trade["type"]=="SELL":
                if current_price<=trade["target"]:
                    trade["result"]="WIN ✅"
                elif current_price>=trade["sl"]:
                    trade["result"]="LOSS ❌"

# 🔹 Bot loop
def run_bot():
    symbols_map={"ETH":"ETH-USD","BTC":"BTC-USD","NIFTY":"^NSEI","BANKNIFTY":"^NSEBANK","CRUDE":"CL=F"}
    while True:
        try:
            for name,symbol in symbols_map.items():
                get_signal_for(symbol,name)
            update_results()
            time.sleep(300)
        except Exception as e:
            print("BOT ERROR:", e)
            time.sleep(60)

# 🔹 Common header
def common_header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <nav>
        <a href='/'>Home</a> | 
        <a href='/signals'>Signals</a> | 
        <a href='/rules'>Rules</a> | 
        <a href='/tricks'>Tricks</a>
    </nav><hr>
    """

# 🔹 Dashboard
@app.route("/")
def dashboard():
    cards=""
    for coin,data in latest_data.items():
        color="#FFD700"
        if data["signal"]=="BUY": color="#22c55e"
        elif data["signal"]=="SELL": color="#ef4444"
        cards+=f"<div style='border:1px solid #FFD700;padding:15px;margin:10px;border-radius:15px;background:#1e293b;'>\
        <h3>{coin}</h3><p>Price: {data['price']}</p><p style='color:{color}'>{data['signal']}</p></div>"
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script>
    let lastAlert="{last_alert_time}";let lastType="{last_alert_type}";
    let prevAlert=localStorage.getItem("lastAlert");
    if(lastAlert!==prevAlert && lastAlert!==""){{
        let soundFile="";
        if(lastType==="BUY") soundFile="/static/buy.mp3";
        else if(lastType==="SELL") soundFile="/static/sell.mp3";
        if(soundFile!==""){{let audio=new Audio(soundFile);audio.play();}}
        localStorage.setItem("lastAlert",lastAlert);
    }}
    setInterval(()=>{{location.reload();}},60000);
    </script>
    <style>
    body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}
    a{{color:#FFD700;text-decoration:none;}}
    </style>
    </head>
    <body>{common_header()}{cards}</body></html>
    """

# 🔹 Signals page
@app.route("/signals")
def signals_page():
    msgs="".join([f"<p>{m['time']} → {m['msg']}</p>" for m in telegram_messages[::-1][:50]])
    return f"<html><body>{common_header()}<h3>📩 Signals</h3>{msgs if msgs else '<p>No signals</p>'}</body></html>"

# 🔹 Rules page
@app.route("/rules")
def rules_page():
    return f"<html><body>{common_header()}<h3>📜 Rules</h3><p>All signals are educational; trade at your own risk.</p></body></html>"

# 🔹 Tricks / DMCA page
@app.route("/tricks")
def tricks_page():
    return f"<html><body>{common_header()}<h3>🛡️ DMCA / Tricks</h3><p>Content is protected. Do not copy.</p></body></html>"

# 🔹 ONLY ONE coin_page FUNCTION
@app.route("/coin/<name>")
def coin_page(name):
    data = latest_data.get(name, {})
    total, wins, loss, pnl, accuracy = calculate_stats()

    history = "".join([
        f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    symbol = chart_map.get(name, "")

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="60">
    </head>
    <body>
        <h1>{name}</h1>
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>Signal: {data.get('signal')}</p>

        <!-- TradingView Chart -->
        <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark" 
                style="width:100%; height:300px; border:none;"></iframe>

        <h3>Trade History</h3>
        {history if history else "<p>No trades</p>"}
    </body>
    </html>
    """
# 🔹 Main
if __name__=="__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=PORT)
