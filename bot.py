
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
        ema_fast = calculate_ema(prices, 20)
        ema_slow = calculate_ema(prices, 50)

        print(f"Price: {current_price} | RSI: {rsi} | EMA20: {ema_fast} | EMA50: {ema_slow}")

        # 🟢 BUY CONDITION
        if (rsi < 30 and current_price > ema_fast and ema_fast > ema_slow and last_signal != "BUY"):
            target = current_price * 1.02
            stoploss = current_price * 0.99

            send_message(
                f"BUY 🚀\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "BUY"

        # 🔴 SELL CONDITION
        elif (rsi > 70 and current_price < ema_fast and ema_fast < ema_slow and last_signal != "SELL"):
            target = current_price * 0.98
            stoploss = current_price * 1.01

            send_message(
                f"SELL 🔻\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "SELL"

        time.sleep(180)

    except Exception as e:
        print("Error:", e)
        time.sleep(180)
