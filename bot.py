import requests
import time
import os

TOKEN = os.getenv("8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng")
CHAT_ID = os.getenv("8007854479")

URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

last_signal = ""

while True:
    try:
        res = requests.get(URL).json()

        # ✅ correct extraction
        price = res['ethereum']['usd']
        print("ETH Price:", price)

        # 🔥 signal logic
        if price < 3000 and last_signal != "BUY":
    send_message(f"BUY SIGNAL 🚀\nPrice: {price}")
    last_signal = "BUY"

        elif price > 2500 and last_signal != "SELL":
            send_message(f"SELL SIGNAL 🔻\nPrice: {price}")
            last_signal = "SELL"

        # ✅ VERY IMPORTANT (rate limit fix)
        time.sleep(120)  # 2 minutes

    except Exception as e:
        print("Error:", e)
        time.sleep(120)
        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
