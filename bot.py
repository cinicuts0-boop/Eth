
import requests
import time

TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"

URL1 = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=1"
URL2 = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        print("Telegram error")

def get_prices():
    try:
        res = requests.get(URL1, timeout=10).json()
        if 'prices' in res:
            return [p[1] for p in res['prices']]
    except:
        pass

    # 🔥 Backup API
    try:
        res = requests.get(URL2, timeout=10).json()
        if 'ethereum' in res:
            price = res['ethereum']['usd']
            return [price] * 50  # fake history for RSI
    except:
        pass

    return None

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

def calculate_ema(prices, period):
    if len(prices) == 0:
        return 0

    ema = prices[0]
    k = 2 / (period + 1)

    for price in prices:
        ema = price * k + ema * (1 - k)

    return ema

last_signal = ""
last_rsi = None

while True:
    try:
        prices = get_prices()

        if prices is None:
            print("API failed, retry later...")
            time.sleep(300)
            continue

        current_price = prices[-1]

        rsi = calculate_rsi(prices)
        ema20 = calculate_ema(prices, 20)
        ema50 = calculate_ema(prices, 50)

        print(f"Price: {current_price} | RSI: {rsi} | EMA20: {ema20} | EMA50: {ema50}")

        # 🟢 REVERSAL BUY
        if (last_rsi is not None and
            last_rsi < rsi and
            rsi < 35 and
            current_price > ema20 and
            ema20 > ema50 and
            last_signal != "BUY"):

            send_message(f"REVERSAL BUY 🚀\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}")
            last_signal = "BUY"

        # 🔴 REVERSAL SELL
        elif (last_rsi is not None and
              last_rsi > rsi and
              rsi > 65 and
              current_price < ema20 and
              ema20 < ema50 and
              last_signal != "SELL"):

            send_message(f"REVERSAL SELL 🔻\nPrice: {current_price:.2f}\nRSI: {rsi:.2f}")
            last_signal = "SELL"

        last_rsi = rsi

        # 🔥 smart delay (avoid rate limit)
        time.sleep(300)

    except Exception as e:
        print("Error:", e)
        time.sleep(300)
