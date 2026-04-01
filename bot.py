
import requests
import time

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

URL = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        print("Telegram error")

def calculate_rsi(prices, period=14):
    gains, losses = [], []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    if len(gains) < period:
        return 50

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

last_signal = ""

while True:
    try:
        res = requests.get(URL, timeout=10).json()

        if 'prices' not in res:
            print("API error:", res)
            time.sleep(300)
            continue

        prices = [p[1] for p in res['prices']]
        current_price = prices[-1]

        # 🔥 breakout levels
        recent_prices = prices[-20:]
        resistance = max(recent_prices)
        support = min(recent_prices)

        rsi = calculate_rsi(prices)

        print(f"Price: {current_price} | RSI: {rsi} | High: {resistance} | Low: {support}")

        # 🟢 BUY BREAKOUT
        if (current_price > resistance and rsi > 50 and last_signal != "BUY"):
            target = current_price * 1.02
            stoploss = current_price * 0.99

            send_message(
                f"BREAKOUT BUY 🚀\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "BUY"

        # 🔴 SELL BREAKDOWN
        elif (current_price < support and rsi < 50 and last_signal != "SELL"):
            target = current_price * 0.98
            stoploss = current_price * 1.01

            send_message(
                f"BREAKDOWN SELL 🔻\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "SELL"

        time.sleep(300)

    except Exception as e:
        print("Error:", e)
        time.sleep(300)
