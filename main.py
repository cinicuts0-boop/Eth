
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
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
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

        # 🔥 SMART OPTION LOGIC
        option = ""
        if name in ["NIFTY", "BANKNIFTY"]:
            if signal == "BUY":
                option = "CE 📈"
            elif signal == "SELL":
                option = "PE 📉"
        elif name == "CRUDE":
            if signal == "BUY":
                option = "CALL 📈"
            elif signal == "SELL":
                option = "PUT 📉"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi_val, 2),
            "signal": signal
        }

        if signal != "WAITING":
            trade = {
                "coin": name,
                "type": signal,
                "price": round(price, 2),
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            }
            trade_history.append(trade)

            return f"{name} → {signal} ({option}) @ {price:.2f}"

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
            eth_msg = get_signal_for("ETH-USD", "ETH")
            btc_msg = get_signal_for("BTC-USD", "BTC")
            nifty_msg = get_signal_for("^NSEI", "NIFTY")
            bank_msg = get_signal_for("^NSEBANK", "BANKNIFTY")
            crude_msg = get_signal_for("CL=F", "CRUDE")  # 🛢️

            update_results()

            if eth_msg:
                send_telegram("🟢 " + eth_msg)

            if btc_msg:
                send_telegram("🟡 " + btc_msg)

            if nifty_msg:
                send_telegram("🇮🇳 " + nifty_msg)

            if bank_msg:
                send_telegram("🏦 " + bank_msg)

            if crude_msg:
                send_telegram("🛢️ " + crude_msg)

            print("Updated...")

            time.sleep(300)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)


@app.route("/")
def dashboard():
    total, wins, loss, pnl, accuracy = calculate_stats()

    history_html = "".join([
        f"<p>{t['time']} | {t['coin']} {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history[-10:]
    ])

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: white;
                text-align: center;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                padding: 10px;
            }}
            .box {{
                background: #1e293b;
                padding: 15px;
                border-radius: 10px;
            }}
            .buy {{ color: #22c55e; }}
            .sell {{ color: #ef4444; }}
        </style>
    </head>

    <body>

    <h1>🚀 Mani Money Mindset DASHBOARD</h1>

    <div style="padding:10px;">
        <h2>📊 Performance</h2>
        <p>Total Trades: {total}</p>
        <p>Wins: {wins} | Loss: {loss}</p>
        <p>Accuracy: {accuracy}%</p>
        <p>💰 PnL: {pnl}</p>
    </div>

    <div class="grid">
        {"".join([f'''
        <div class="box">
            <h2>{coin}</h2>
            <p>{data['price']}</p>
            <p>RSI: {data['rsi']}</p>
            <p class="{data['signal'].lower()}">{data['signal']}</p>
        </div>
        ''' for coin, data in latest_data.items()])}
    </div>

    <div style="padding:10px;">
        <h3>📈 Charts</h3>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:ETHUSDT&interval=5&theme=dark" width="100%" height="200"></iframe>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:BTCUSDT&interval=5&theme=dark" width="100%" height="200"></iframe>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=NSE:NIFTY&interval=5&theme=dark" width="100%" height="200"></iframe>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=NSE:BANKNIFTY&interval=5&theme=dark" width="100%" height="200"></iframe>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol=NYMEX:CL1!&interval=5&theme=dark" width="100%" height="200"></iframe>
    </div>

    <h2>📊 Trade History</h2>
    <div style="padding:10px;">
        {history_html}
    </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()

    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
