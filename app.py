import threading
import time

from web.routes import app
from bot.signals import get_signal_for

def run_bot():
    while True:
        get_signal_for("ETH-USD", "ETH")
        get_signal_for("BTC-USD", "BTC")
        get_signal_for("^NSEI", "NIFTY")
        get_signal_for("^NSEBANK", "BANKNIFTY")
        get_signal_for("CL=F", "CRUDE")

        time.sleep(300)

# 🔥 Railway fix
threading.Thread(target=run_bot, daemon=True).start()
