import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask
import threading
import datetime

app = Flask(__name__)

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

latest_data = {
    "ETH": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BTC": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "NIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "BANKNIFTY": {"price": 0, "rsi": 0, "signal": "WAITING"},
    "CRUDE": {"price": 0, "rsi": 0, "signal": "WAITING"}
}

trade_history = []

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("Telegram response:", res.json())
    except Exception as e:
        print("Telegram Error:", e)

def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins * 10) - (loss * 10)
    accuracy = (wins / total * 100) if total > 0 else 0
    return total, wins, loss, pnl, round(accuracy, 2)

def get_signal_for(symbol, name):
    global latest_data, trade_history
    try:
        df = yf.download(symbol, period="1d", interval="5m")
        if df.empty:
            print(name, "data empty")
            return None

        close = df['Close']
        if len(close.shape) > 1:
            close = close.squeeze()

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        # 🔹 Adjusted thresholds for more signals
        signal = "WAITING"
        if rsi_val < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi_val > 60 and macd_val < macd_sig:
            signal = "SELL"

        # 🔹 Debug print for signals
        print(f"{name}: Price={price}, RSI={rsi_val:.2f}, MACD={macd_val:.2f}, MACD_SIG={macd_sig:.2f}, Signal={signal}")

        option = ""
        if name in ["NIFTY", "BANKNIFTY"]:
            option = "CE 📈" if signal == "BUY" else "PE 📉" if signal == "SELL" else ""
        elif name == "CRUDE":
            option = "CALL 📈" if signal == "BUY" else "PUT 📉" if signal == "SELL" else ""

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi_val,2), "signal": signal}

        if signal != "WAITING":
            trade_history.append({
                "coin": name,
                "type": signal,
                "price": round(price,2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })
            msg = f"{name} → {signal} ({option}) @ {price:.2f}"
            send_telegram(msg)
            return msg
    except Exception as e:
        print(name, "error:", e)
    return None

def update_results():
    for trade in trade_history:
        if trade["result"] == "OPEN":
            current_price = latest_data[trade["coin"]]["price"]
            if trade["type"] == "BUY":
                if current_price > trade["price"] + 10:
                    trade["result"] = "WIN ✅"
                elif current_price < trade["price"] - 10:
                    trade["result"] = "LOSS ❌"
            elif trade["type"] == "SELL":
                if current_price < trade["price"] - 10:
                    trade["result"] = "WIN ✅"
                elif current_price > trade["price"] + 10:
                    trade["result"] = "LOSS ❌"

def run_bot():
    while True:
        try:
            get_signal_for("ETH-USD", "ETH")
            get_signal_for("BTC-USD", "BTC")
            get_signal_for("^NSEI", "NIFTY")
            get_signal_for("^NSEBANK", "BANKNIFTY")
            get_signal_for("CL=F", "CRUDE")
            update_results()
            print("Updated...")
            time.sleep(300)
        except Exception as e:
            print("Bot Error:", e)
            time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
