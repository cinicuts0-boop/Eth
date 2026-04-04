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

@app.route("/")
def home():
    cards = ""

    for coin, data in latest_data.items():

        # 🔥 signal color
        color = "white"
        if data.get("signal") == "BUY":
            color = "green"
        elif data.get("signal") == "SELL":
            color = "red"

        cards += f"""
        <div style="border:1px solid white; margin:10px; padding:10px;">
            <h3>{coin}</h3>
            <p>Price: {data.get('price')}</p>
            <p style="color:{color}">Signal: {data.get('signal')}</p>
            <p>{data.get('prediction')}</p>

            <!-- 📈 LIVE CHART -->
            <iframe src="https://s.tradingview.com/widgetembed/?symbol=BINANCE:{coin}USDT&interval=5&theme=dark"
            width="100%" height="200"></iframe>
        </div>
        """

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
