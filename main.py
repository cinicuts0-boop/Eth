
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
last_signal = ""

# 🔹 COMMON HEADER
def common_header():
    return """
    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>꧁༺ 💚 எண்ணம் போல் வாழ்க்கை ❤️ ༻꧂</h4>
    <div class="nav">
        <a href="/">Home</a> | 
        <a href="/Rules">Contact</a> | 
        <a href="/Tricks">DMCA</a>
    </div>
    <style>
        .nav a {color:#FFD700;margin:0 10px;text-decoration:none;font-weight:bold;}
        .nav a:hover {color:#22c55e;}
    </style>
    """

# 🔔 TELEGRAM
def send_telegram(msg):
    global last_signal
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg,
            "disable_notification": False
        })
        last_signal = msg
    except Exception as e:
        print(e)

# 📊 SIGNAL
def get_signal(symbol, name):
    global latest_data, trade_history
    try:
        df = yf.download(symbol, period="1d", interval="5m")
        close = df['Close'].squeeze()

        rsi = float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd = ta.trend.MACD(close)
        macd_val = float(macd.macd().iloc[-1])
        macd_sig = float(macd.macd_signal().iloc[-1])
        price = float(close.iloc[-1])

        signal = "WAITING"
        if rsi < 40 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 60 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {"price": round(price,2), "rsi": round(rsi,2), "signal": signal}

        if signal != "WAITING":
            msg = f"{name} → {signal} @ {price:.2f}"
            send_telegram(msg)

    except Exception as e:
        print(e)

# 🔄 LOOP
def run_bot():
    while True:
        get_signal("ETH-USD","ETH")
        get_signal("BTC-USD","BTC")
        get_signal("^NSEI","NIFTY")
        get_signal("^NSEBANK","BANKNIFTY")
        get_signal("CL=F","CRUDE")
        time.sleep(300)

# 🔹 API
@app.route("/latest_signal")
def latest_signal_api():
    return {"msg": last_signal}

# 🏠 HOME
@app.route("/")
def home():
    cards = ""
    for c,d in latest_data.items():
        cards += f"""
        <div class="box">
            <h2>{c}</h2>
            <p>{d['price']}</p>
            <p class="{d['signal'].lower()}">{d['signal']}</p>
        </div>
        """

    return f"""
    <html>
    <body style="background:#0f172a;color:#FFD700;text-align:center;font-family:Arial;">

    {common_header()}

    <!-- SIGNAL BOX -->
    <div id="signalBox" style="margin:20px;padding:15px;border-radius:10px;background:#1e293b;">
        Waiting for signals...
    </div>

    <!-- SOUND -->
    <audio id="sound" src="https://www.soundjay.com/buttons/sounds/beep-01a.mp3"></audio>

    <div>{cards}</div>

    <script>
    let lastMsg="";

    setInterval(()=>{
        fetch("/latest_signal")
        .then(r=>r.json())
        .then(d=>{
            if(d.msg && d.msg!==lastMsg){
                lastMsg=d.msg;

                let box=document.getElementById("signalBox");

                if(d.msg.includes("BUY")) box.style.color="#22c55e";
                else if(d.msg.includes("SELL")) box.style.color="#ef4444";

                box.innerText=d.msg;

                document.getElementById("sound").play();
                alert("New Signal 🚀\\n"+d.msg);
            }
        })
    },5000);
    </script>

    </body>
    </html>
    """

# 📄 CONTACT
@app.route("/Rules")
def contact():
    return f"""
    <html><body style="background:#0f172a;color:#FFD700;text-align:center;">
    {common_header()}
    <h2>Contact</h2>
    <p>Email: mani@example.com</p>
    </body></html>
    """

# 📄 DMCA
@app.route("/Tricks")
def dmca():
    return f"""
    <html><body style="background:#0f172a;color:#FFD700;text-align:center;">
    {common_header()}
    <h2>DMCA</h2>
    <p>All rights reserved</p>
    </body></html>
    """

# ▶️ RUN
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8080)
