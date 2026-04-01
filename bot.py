
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

# ✅ EMA calculation
def calculate_ema(prices, period=20):
    ema = prices[0]
    k = 2 / (period + 1)

    for price in prices:
        ema = price * k + ema * (1 - k)

    return ema

# ✅ RSI (improved)
def calculate_rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

last_signal = ""
last_signal_time = 0

while True:
    try:
        res = requests.get(URL, timeout=10).json()

        if 'prices' not in res:
            print("API error:", res)
            time.sleep(60)
            continue

        prices = [p[1] for p in res['prices']]
        current_price = prices[-1]

        # 🔥 breakout levels (corrected)
        recent_prices = prices[-21:-1]
        resistance = max(recent_prices)
        support = min(recent_prices)

        # 🔥 indicators
        rsi = calculate_rsi(prices)
        ema = calculate_ema(prices)

        print(f"Price: {current_price} | RSI: {rsi} | EMA: {ema}")

        # ⏳ cooldown
        if time.time() - last_signal_time < 1800:
            time.sleep(60)
            continue

        # 🟢 BUY
        if (current_price > resistance * 1.001 and rsi > 55 and current_price > ema and last_signal != "BUY"):
            target = current_price * 1.02
            stoploss = current_price * 0.99

            send_message(
                f"BUY 🚀\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nEMA: {ema:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "BUY"
            last_signal_time = time.time()

        # 🔴 SELL
        elif (current_price < support * 0.999 and rsi < 45 and current_price < ema and last_signal != "SELL"):
            target = current_price * 0.98
            stoploss = current_price * 1.01

            send_message(
                f"SELL 🔻\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}\nEMA: {ema:.2f}\nTarget: {target:.2f}\nSL: {stoploss:.2f}"
            )
            last_signal = "SELL"
            last_signal_time = time.time()

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
