
import requests
import time
import os

TOKEN = os.getenv("8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng")
CHAT_ID = os.getenv("8007854479")

URL = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def calculate_rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

last_signal = ""

while True:
    try:
        res = requests.get(URL).json()

        prices = [p[1] for p in res['prices']]

        rsi = calculate_rsi(prices)

        print("RSI:", rsi)

        if rsi < 30 and last_signal != "BUY":
            send_message(f"BUY SIGNAL 🚀\nRSI: {rsi:.2f}")
            last_signal = "BUY"

        elif rsi > 70 and last_signal != "SELL":
            send_message(f"SELL SIGNAL 🔻\nRSI: {rsi:.2f}")
            last_signal = "SELL"

        time.sleep(180)

    except Exception as e:
        print("Error:", e)
        time.sleep(180)
