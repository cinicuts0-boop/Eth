
# 🚀 AUTO STRIKE PRO DASHBOARD + LIVE SIGNAL
import yfinance as yf
import pandas as pd
import ta
import time
import requests
from flask import Flask, render_template_string
from threading import Thread

# ==============================
# 🔧 User Config
TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

CRUDE_CE_STRIKE = 9900
CRUDE_PE_STRIKE = 7500
NIFTY_CE_STRIKE = 22900
NIFTY_PE_STRIKE = 23000
# ==============================

# Telegram alert
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("📤 Telegram Sent")
    except Exception as e:
        print("❌ Telegram Error:", e)

# Fetch live price
def get_price(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty:
            return None
        # If multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        price = float(df["Close"].iloc[-1])
        return price
    except Exception as e:
        print("❌ Price Error:", e)
        return None

# Strategy
def strategy(price_history, ce_strike, pe_strike):
    df = pd.DataFrame(price_history, columns=["close"])
    if len(df) < 14:
        return None, None, None, None, None
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["ema20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    last = df.iloc[-1]
    price = float(last["close"])
    rsi = float(last["rsi"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])

    signal = None
    option = None
    entry = None

    # CE Signal
    if rsi < 45 and ema20 > ema50:
        signal = "BUY"
        option = f"CE {ce_strike}"
        intrinsic = max(0, price - ce_strike)
        entry = max(50, intrinsic + price*0.02)
    # PE Signal
    elif rsi > 55 and ema20 < ema50:
        signal = "BUY"
        option = f"PE {pe_strike}"
        intrinsic = max(0, pe_strike - price)
        entry = max(50, intrinsic + price*0.02)

    return signal, option, price, rsi, entry

# Flask dashboard
app = Flask(__name__)
signal_log = []

@app.route("/")
def dashboard():
    html = """
    <html>
    <head><title>AUTO STRIKE PRO DASHBOARD</title></head>
    <body>
    <h2>🚀 AUTO STRIKE PRO DASHBOARD</h2>
    <table border="1" cellpadding="5">
    <tr><th>Symbol</th><th>Price</th><th>RSI</th><th>Signal</th><th>Option</th><th>Entry</th></tr>
    {% for s in signals %}
    <tr>
        <td>{{ s['symbol'] }}</td>
        <td>{{ s['price'] }}</td>
        <td>{{ s['rsi'] }}</td>
        <td>{{ s['signal'] }}</td>
        <td>{{ s['option'] }}</td>
        <td>{{ s['entry'] }}</td>
    </tr>
    {% endfor %}
    </table>
    </body>
    </html>
    """
    return render_template_string(html, signals=signal_log[-10:])

# Bot loop
def run_bot():
    symbols = [("CL=F", CRUDE_CE_STRIKE, CRUDE_PE_STRIKE),
               ("^NSEI", NIFTY_CE_STRIKE, NIFTY_PE_STRIKE)]
    last_signal_record = {}
    price_histories = {sym[0]: [] for sym in symbols}

    while True:
        for symbol, ce_strike, pe_strike in symbols:
            price = get_price(symbol)
            if price is None:
                continue

            price_histories[symbol].append(price)
            if len(price_histories[symbol]) > 100:
                price_histories[symbol].pop(0)

            signal, option, p, rsi, entry = strategy(price_histories[symbol], ce_strike, pe_strike)

            signal_info = {
                "symbol": symbol,
                "price": round(p,2) if p else "-",
                "rsi": round(rsi,2) if rsi else "-",
                "signal": signal or "No Trade",
                "option": option or "-",
                "entry": round(entry,2) if entry else "-"
            }
            signal_log.append(signal_info)

            if signal and last_signal_record.get(symbol) != signal:
                msg = f"""
🚀 AUTO STRIKE PRO SIGNAL

Symbol: {symbol}
🔔 {signal}
🎯 {option}
💰 Price: {round(p,2)}
💸 Entry: ₹{round(entry,2)}
📈 RSI: {round(rsi,2)}
"""
                send_telegram(msg)
                last_signal_record[symbol] = signal

            print(signal_info)

        time.sleep(60)

if __name__ == "__main__":
    # Run dashboard
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)).start()
    # Run bot
    run_bot()
