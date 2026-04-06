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

# 🔹 Telegram message sender
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

# 🔹 Stats calculator
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
        # 5-min data
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

        rsi_buy = 35
        rsi_sell = 65
        macd_diff_threshold = 0.5

        if rsi_val < rsi_buy and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        # 15-min multi-timeframe confirmation
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

        # Update latest_data
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
            msg=f"""
🚀 {name} SIGNAL
Type: {signal}
Entry: {price:.2f}
Target: {target}
SL: {sl}
"""
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
    return "<h1>🚀 Mani Money Mindset 💸</h1><h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4> \
            <nav><a href='/'>Home</a> | <a href='/signals'>Signals</a> | <a href='/rules'>Rules</a> | <a href='/tricks'>Tricks</a></nav><hr>"

# 🔹 Dashboard
@app.route("/")
def dashboard():
    cards=""
    for coin,data in latest_data.items():
        color="#FFD700"
        if data["signal"]=="BUY": color="#22c55e"
        elif data["signal"]=="SELL": color="#ef4444"
        cards+=f"<div style='border:1px solid #FFD700;padding:10px;margin:5px;border-radius:10px;'>\
        <h3>{coin}</h3><p>Price: {data['price']}</p><p style='color:{color}'>{data['signal']}</p></div>"
    return common_header()+cards

# 🔹 Signals page
@app.route("/signals")
def signals_page():
    msgs="".join([f"<p>{m['time']} → {m['msg']}</p>" for m in telegram_messages[::-1][:50]])
    return common_header()+"<h2>📩 Signals</h2>"+(msgs if msgs else "<p>No signals</p>")

# 🔹 Rules page
@app.route("/rules")
def rules_page():
    return common_header()+"<h2>📜 Rules</h2><p>All signals are educational. Trade at your own risk.</p>"

# 🔹 Tricks / DMCA page
@app.route("/tricks")
def tricks_page():
    return common_header()+"<h2>🛡️ DMCA / Tricks</h2><p>Content protected. Do not copy.</p>"

# 🔹 Coin detail page
@app.route("/coin/<name>")
def coin_page(name):
    data = latest_data.get(name,{})
    total,wins,loss,pnl,accuracy=calculate_stats()
    history="".join([f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>" for t in trade_history if t["coin"]==name][-10:])
    return common_header()+f"<h2>{name}</h2><p>Price: {data.get('price')}</p><p>RSI: {data.get('rsi')}</p><p>Signal: {data.get('signal')}</p>\
            <h3>Performance</h3><p>Accuracy: {accuracy}% | PnL: {pnl}</p>\
            <h3>Trade History</h3>{history if history else '<p>No trades</p>'}"

# 🔹 Main
if __name__=="__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    PORT=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=PORT)
