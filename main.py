
import requests
import pandas as pd
import time
import ta

TELEGRAM_TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)

def get_data():
    url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=5m&limit=100"

    try:
        res = requests.get(url)
        data = res.json()

        # ✅ API empty check
        if not isinstance(data, list) or len(data) == 0:
            print("No API data")
            return None

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "ct","qav","nt","tbv","tqv","ignore"
        ])

        # ✅ conversion safe
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna()

        return df

    except Exception as e:
        print("Data Error:", e)
        return None

def strategy():
    df = get_data()

    # ✅ FULL safety checks
    if df is None:
        print("DF None")
        return None

    if df.empty:
        print("DF Empty")
        return None

    if len(df) < 20:
        print("Not enough candles")
        return None

    try:
        df['ema'] = df['close'].ewm(span=20).mean()
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

        df = df.dropna()

        if df.empty:
            print("After indicator empty")
            return None

        last = df.iloc[-1]

        print("Price:", last['close'], "EMA:", last['ema'], "RSI:", last['rsi'])

        # BUY
if last['close'] > last['ema'] and last['rsi'] > 50:
    return f"📈 BUY ETH\nPrice: {last['close']}"

# SELL
elif last['close'] < last['ema'] and last['rsi'] < 50:
    return f"📉 SELL ETH\nPrice: {last['close']}"

        return None

    except Exception as e:
        print("Strategy Error:", e)
        return None

last_signal = None

print("🚀 BOT STARTED")

while True:
    try:
        signal = strategy()

        if signal and signal != last_signal:
            send_telegram(f"🚨 ETH SIGNAL\n{signal}")
            last_signal = signal
        else:
            print("No signal")

    except Exception as e:
        print("Main Loop Error:", e)

    time.sleep(180)
