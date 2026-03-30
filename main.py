
import requests
import pandas as pd
import time
import ta

TELEGRAM_TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_data():
    url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=5m&limit=100"

    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "ct","qav","nt","tbv","tqv","ignore"
    ])

    df['close'] = df['close'].astype(float)
    return df

def strategy():
    df = get_data()

    # Indicators
    df['ema'] = df['close'].ewm(span=20).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    last = df.iloc[-1]

    print("Price:", last['close'], "EMA:", last['ema'], "RSI:", last['rsi'])

    # BUY
    if last['close'] > last['ema'] and last['rsi'] > 55:
        return f"📈 BUY ETH\nPrice: {last['close']}"

    # SELL
    elif last['close'] < last['ema'] and last['rsi'] < 45:
        return f"📉 SELL ETH\nPrice: {last['close']}"

    return None

last_signal = None

print("🚀 ETH BOT STARTED")

while True:
    try:
        signal = strategy()

        if signal and signal != last_signal:
            send_telegram(f"🚨 ETH SIGNAL\n{signal}")
            last_signal = signal
        else:
            print("No signal")

    except Exception as e:
        print("Error:", e)

    time.sleep(180)
