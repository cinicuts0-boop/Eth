from flask import Flask
from bot.signals import latest_data
from bot.stats import calculate_stats
from bot.telegram import telegram_messages

app = Flask(__name__)

def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <style>
    body {background:black;color:white;text-align:center;}
    </style>
    """
# 🔹 COIN PAGE
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name, {})
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
    <body>{header()}
    <h2>{name}</h2>
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>

    <h3>📊 Performance</h3>
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>

    <h3>📈 Chart</h3>
    <iframe src="https://s.tradingview.com/widgetembed/?symbol={chart_map.get(name)}&interval=5&theme=dark"
    width="100%" height="300"></iframe>

    <h3>📜 History</h3>
    {history if history else "No trades"}

    </body></html>
    """
