from flask import Flask
from bot.signals import latest_data
from bot.stats import calculate_stats, trade_history
from bot.telegram import telegram_messages

app = Flask(__name__)

def style():
    return """
    <style>
    body {background:#0f172a;color:#FFD700;text-align:center;}
    .card {background:#1e293b;margin:10px;padding:10px;border-radius:10px;}
    </style>
    """

@app.route("/")
def home():
    cards = ""

    for coin, d in latest_data.items():
        color = "white"
        if d.get("signal") == "BUY":
            color = "green"
        elif d.get("signal") == "SELL":
            color = "red"

        cards += f"""
        <div class="card">
        <h3>{coin}</h3>
        <p>{d.get('price')}</p>
        <p style="color:{color}">{d.get('signal')}</p>
        </div>
        """

    return f"<html>{style()}<body><h2>Dashboard</h2>{cards}</body></html>"
