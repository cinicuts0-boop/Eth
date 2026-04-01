
from binance.client import Client
import time


TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

client = Client(API_KEY, API_SECRET)

SYMBOL = "ETHUSDT"
INTERVAL = "1m"   # Binance doesn't have 2m, so use 1m and combine logic

def get_prices():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=50)
    return [float(k[4]) for k in klines]  # closing prices

def calculate_ema(prices, period=20):
    ema = prices[0]
    k = 2 / (period + 1)
    for price in prices:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_rsi(prices, period=14):
    gains, losses = [], []
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

while True:
    try:
        prices = get_prices()
        current_price = prices[-1]

        recent = prices[-21:-1]
        resistance = max(recent)
        support = min(recent)

        ema = calculate_ema(prices)
        rsi = calculate_rsi(prices)

        print(f"Price: {current_price} | RSI: {rsi} | EMA: {ema}")

        # 🟢 BUY
        if current_price > resistance and rsi > 55 and current_price > ema and last_signal != "BUY":
            print("🚀 BUY SIGNAL")
            last_signal = "BUY"

        # 🔴 SELL
        elif current_price < support and rsi < 45 and current_price < ema and last_signal != "SELL":
            print("🔻 SELL SIGNAL")
            last_signal = "SELL"

        time.sleep(120)  # ⏱ 2 minutes

    except Exception as e:
        print("Error:", e)
        time.sleep(120)
