import requests
import time

TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"


URL = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def calculate_rsi(prices, period=14):
    gains, losses = [], []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
    ema = prices[0]
    k = 2 / (period + 1)

    for price in prices:
        ema = price * k + ema * (1 - k)

    return ema

last_signal = ""
last_rsi = None

while True:
    try:
        res = requests.get(URL).json()

        if 'prices' not in res:
            print("API error:", res)
            time.sleep(180)
            continue

        prices = [p[1] for p in res['prices']]
        current_price = prices[-1]

        rsi = calculate_rsi(prices)
        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)

        print(f"Price: {current_price} | RSI: {rsi} | EMA20: {ema20} | EMA50: {ema50}")

        # 🟢 BUY REVERSAL
        if (last_rsi is not None and
            last_rsi < rsi and  # RSI rising
            rsi < 35 and
            current_price > ema20 and
            ema20 > ema50 and
            last_signal != "BUY"):

            send_message(f"REVERSAL BUY 🚀\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}")
            last_signal = "BUY"

        # 🔴 SELL REVERSAL
        elif (last_rsi is not None and
              last_rsi > rsi and  # RSI falling
              rsi > 65 and
              current_price < ema20 and
              ema20 < ema50 and
              last_signal != "SELL"):

            send_message(f"REVERSAL SELL 🔻\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}")
            last_signal = "SELL"

        last_rsi = rsi

        time.sleep(180)

    except Exception as e:
        print("Error:", e)
        time.sleep(180)
