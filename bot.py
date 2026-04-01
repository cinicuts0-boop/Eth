
import requests
import time

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

def send_msg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
    data = requests.get(url).json()
    return float(data["price"])

while True:
    price = get_price()

    if price > 2100:
        send_msg(f"🚀 ETH BUY SIGNAL\nPrice: {price}")

    elif price < 2000:
        send_msg(f"🔻 ETH SELL SIGNAL\nPrice: {price}")

    print("Running...", price)
    time.sleep(60)
