from flask import Flask
from bot.signals import latest_data
from bot.stats import calculate_stats, trade_history
from bot.telegram import telegram_messages

app = Flask(__name__)

def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <style>
    body {background:black;color:white;text-align:center;}
    </style>
    """

@app.route("/")
def home():
    return f"<html>{style()}<body><h2>Dashboard</h2>{latest_data}</body></html>"

@app.route("/signals")
def signals():
    msgs = "".join([f"<p>{m['time']} → {m['msg']}</p>" for m in telegram_messages[::-1]])
    return f"<html>{style()}<body>{msgs}</body></html>"
