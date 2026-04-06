import requests
import time
import yfinance as yf
import ta
import os
from flask import Flask, send_from_directory, request
import threading
from datetime import datetime, timedelta

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M")
CHAT_ID = os.getenv("CHAT_ID", "8007854479")

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

# ===== India Time =====
def india_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

# ===== Common Header =====
def common_header(active=None):
    nav_items = [
        ("Home", "/"),
        ("Alerts", "/alerts"),
        ("Rules", "/rules"),
        ("Tricks", "/tricks"),
        ("All Charts", "/signals"), 
        ("Admin", "/thresholds")
    ]
    nav_html = " | ".join([
        f'<a href="{url}" style="color:{"#3b82f6" if name==active else "#FFD700"}">{name}</a>'
        for name, url in nav_items
    ])
    return f"""
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>💚 எண்ணம் போல் வாழ்க்கை ❤️</h4>
    <div class="nav">{nav_html}</div>
    """

# ===== Bot Signal Calculation =====
def get_signal_for(symbol, name):
    global latest_data, trade_history, last_signal, last_alert_time, last_alert_type
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty:
            return
        close = df['Close'].dropna()
        if len(close) < 30:
            return

        rsi_val = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_val = float(macd_obj.macd().iloc[-1])
        macd_sig = float(macd_obj.macd_signal().iloc[-1])
        price = float(close.iloc[-1])
        macd_diff = macd_val - macd_sig

        if rsi_val < rsi_buy_threshold and macd_diff > macd_diff_threshold:
            signal = "BUY"
        elif rsi_val > rsi_sell_threshold and macd_diff < -macd_diff_threshold:
            signal = "SELL"
        else:
            signal = "WAITING"

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi_val,2), "signal": signal}

        if signal != "WAITING" and signal != last_signal.get(name):
            last_signal[name] = signal
            last_alert_time[name] = india_time().strftime("%H:%M:%S")
            last_alert_type[name] = signal

            sl = round(price - 10,2) if signal=="BUY" else round(price+10,2)
            target = round(price +10,2) if signal=="BUY" else round(price-10,2)

            trade_history.append({
                "coin": name, "type": signal, "price": round(price,2),
                "sl": sl, "target": target, "time": last_alert_time[name], "result": "OPEN"
            })

            msg = f"🚀 {name} SIGNAL\nType: {signal}\nEntry: {price:.2f}\nTarget: {target}\nSL: {sl}"
            send_telegram(msg)

    except Exception as e:
        print(name, "ERROR:", e)

# ===== Update Trade Results =====
def update_results():
    for trade in trade_history:
        if trade["result"] != "OPEN":
            continue
        current_price = latest_data.get(trade["coin"], {}).get("price",0)
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

# ===== Stats =====
def calculate_stats():
    total = len(trade_history)
    wins = sum(1 for t in trade_history if "WIN" in t["result"])
    loss = sum(1 for t in trade_history if "LOSS" in t["result"])
    pnl = (wins*10) - (loss*10)
    accuracy = (wins/total*100) if total>0 else 0
    return total, wins, loss, pnl, round(accuracy,2)

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
            print("BOT ERROR:", e)
            time.sleep(60)

# ===== Static Files =====
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# ===== Home Page =====
@app.route("/")
def home():
    cards=""
    for coin,data in latest_data.items():
        color="#FFD700"
        if data["signal"]=="BUY": color="#22c55e"
        elif data["signal"]=="SELL": color="#ef4444"
        cards+=f"""
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}
        .container{{display:flex;flex-wrap:wrap;justify-content:center;}}
        .box{{background:#1e293b;padding:20px;margin:10px;border-radius:15px;border:1px solid #FFD700;min-width:200px;flex:1 1 200px;}}
        a{{color:#FFD700;text-decoration:none;}}
    </style>
    </head>
    <body>
        {common_header(active="Home")}
        <div class="container">{cards}</div>
    </body>
    </html>
    """

# ===== Alerts Page with Sounds =====
@app.route("/alerts")
def alerts_page():
    history_html=""
    for t in trade_history[-20:]:
        history_html+=f"<p>{t['time']} | {t['coin']} | {t['type']} @ {t['price']} → {t['result']}</p>"

    scripts=""
    audios=""
    for coin in latest_data.keys():
        audios+=f'<audio id="{coin}_buy" src="/static/{coin}_buy.mp3"></audio>'
        audios+=f'<audio id="{coin}_sell" src="/static/{coin}_sell.mp3"></audio>'
        scripts+=f"""
        let last_{coin}= "{last_alert_time.get(coin,'')}";
        let type_{coin}= "{last_alert_type.get(coin,'')}";
        let prev_{coin}= localStorage.getItem("last_{coin}");
        if(last_{coin}!==prev_{coin} && last_{coin}!==""){{
            if(type_{coin}==="BUY"){{ document.getElementById("{coin}_buy").play(); }}
            else if(type_{coin}==="SELL"){{ document.getElementById("{coin}_sell").play(); }}
            localStorage.setItem("last_{coin}",last_{coin});
        }}
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <style>body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}</style>
    </head>
    <body>
        {common_header(active="Alerts")}
        <h2>📢 Live Alerts</h2>
        {history_html if history_html else "<p>No alerts yet</p>"}
        {audios}
        <script>{scripts}</script>
    </body>
    </html>
    """

# ===== Coin Details Page =====
@app.route("/coin/<name>")
def coin_page(name):
    name = name.upper()
    data = latest_data.get(name)
    if not data:
        return "Coin not found", 404
    total,wins,loss,pnl,accuracy = calculate_stats()
    chart_map = {"ETH":"BINANCE:ETHUSDT","BTC":"BINANCE:BTCUSDT","NIFTY":"NSE:NIFTY",
                 "BANKNIFTY":"NSE:BANKNIFTY","CRUDE":"NYMEX:CL1!"}
    symbol = chart_map.get(name,"")
    history_html="".join([f"<p>{t['time']} | {t['type']} @ {t['price']} → {t['result']}</p>"
                          for t in trade_history if t["coin"]==name][-10:])
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <style>
        body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;margin:0;padding:0;}}
        .box{{background:#1e293b;margin:10px;padding:15px;border-radius:15px;border:1px solid #FFD700;}}
        iframe{{width:100%;height:350px;border:none;}}
        a{{color:#FFD700;text-decoration:none;}}
        .history{{max-height:200px;overflow-y:auto;text-align:left;}}
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
            <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"></iframe>
        </div>
        <div class="box history">
            <h3>📜 Trade History</h3>
            {history_html if history_html else "<p>No trades</p>"}
        </div>
    </body>
    </html>
    """

# ===== Rules Page =====
@app.route("/rules")
def rules_page():
    rules_html="""
    <ul style="text-align:left; max-width:600px; margin:auto;">
        <li>✅ Always set stop-loss before entering a trade.</li>
        <li>✅ Do not risk more than 2% of capital per trade.</li>
        <li>✅ Follow RSI & MACD signals for entry/exit.</li>
        <li>✅ Avoid trading during high volatility news.</li>
        <li>✅ Keep a trade journal to track performance.</li>
    </ul>
    """
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}</style>
    </head>
    <body>
        {common_header(active="Rules")}
        <h2>📜 Trading Rules</h2>
        {rules_html}
    </body>
    </html>
    """

# ===== Tricks Page =====
@app.route("/tricks")
def tricks_page():
    tricks_html="""
    <ul style="text-align:left; max-width:600px; margin:auto;">
        <li>💡 Use multiple timeframes for confirmation.</li>
        <li>💡 Avoid overtrading; wait for high-probability setups.</li>
        <li>💡 Take partial profits to lock gains.</li>
        <li>💡 Monitor correlation between assets.</li>
        <li>💡 Review losing trades to improve strategy.</li>
    </ul>
    """
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}</style>
    </head>
    <body>
        {common_header(active="Tricks")}
        <h2>💡 Trading Tricks</h2>
        {tricks_html}
    </body>
    </html>
    """

# ===== Thresholds Page =====
@app.route("/thresholds", methods=["GET","POST"])
def thresholds_page():
    global rsi_buy_threshold, rsi_sell_threshold, macd_diff_threshold
    if request.method=="POST":
        try:
            rsi_buy_threshold=float(request.form.get("rsi_buy",rsi_buy_threshold))
            rsi_sell_threshold=float(request.form.get("rsi_sell",rsi_sell_threshold))
            macd_diff_threshold=float(request.form.get("macd_diff",macd_diff_threshold))
        except: pass
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}
    .box{{background:#1e293b;padding:20px;margin:10px;border-radius:15px;border:1px solid #FFD700;}}
    input{{width:60px;text-align:center;}}
    button{{padding:5px 10px; margin-left:10px;}}
    </style>
    </head>
    <body>
        {common_header(active="Admin")}
        <div class="box">
            <h3>⚙️ Adjust Thresholds</h3>
            <form method="POST">
                RSI Buy: <input name="rsi_buy" value="{rsi_buy_threshold}"/>
                RSI Sell: <input name="rsi_sell" value="{rsi_sell_threshold}"/>
                MACD Diff: <input name="macd_diff" value="{macd_diff_threshold}"/>
                <button type="submit">Update</button>
            </form>
        </div>
    </body>
    </html>
    """

# ===== Signals Page =====
@app.route("/signals")
def signals_page():
    cards=""
    chart_map = {"ETH":"BINANCE:ETHUSDT","BTC":"BINANCE:BTCUSDT","NIFTY":"NSE:NIFTY",
                 "BANKNIFTY":"NSE:BANKNIFTY","CRUDE":"NYMEX:CL1!"}
    for coin,data in latest_data.items():
        color="#FFD700"
        if data["signal"]=="BUY": color="#22c55e"
        elif data["signal"]=="SELL": color="#ef4444"
        symbol=chart_map.get(coin,"")
        cards+=f"""
        <div class="box">
            <h3>{coin}</h3>
            <p>Price: {data['price']}</p>
            <p style="color:{color}">Signal: {data['signal']}</p>
            <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"></iframe>
        </div>
        """
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body{{background:#0f172a;color:#FFD700;font-family:Arial;text-align:center;}}
        .box{{background:#1e293b;padding:15px;margin:10px;border-radius:15px;border:1px solid #FFD700;}}
        iframe{{width:100%;height:300px;border:none;margin-top:10px;}}
    </style>
    </head>
    <body>
        {common_header(active="All Charts")}
        <h2>📈 Live Signals</h2>
        {cards}
    </body>
    </html>
    """

# ===== Start Bot & Flask =====
if __name__=="__main__":
    threading.Thread(target=run_bot,daemon=True).start()
    PORT=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=PORT)
