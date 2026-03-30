import requests
import pandas as pd
import time
import ta
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_data():
    url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=5m&limit=100"

    try:
        res = requests.get(url)
        data = res.json()

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "ct","qav","nt","tbv","tqv","ignore"
        ])

        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        return df

    except Exception as e:
        print("Data Error:", e)
        return None

def strategy():
    df = get_data()

    if df is None or df.empty:
        return None

    # Keltner Channel
    kc = ta.volatility.KeltnerChannel(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=20
    )

    df['upper'] = kc.keltner_channel_hband()
    df['lower'] = kc.keltner_channel_lband()

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    last = df.iloc[-1]

    print("Price:", last['close'], "RSI:", last['rsi'])

    # BUY
    if last['close'] < last['lower'] and last['rsi'] < 50:
        return f"📈 BUY ETH\nPrice: {last['close']}"

    # SELL
    elif last['close'] > last['upper'] and last['rsi'] > 50:
        return f"📉 SELL ETH\nPrice: {last['close']}"

    return None

last_signal = None

print("Keltner Bot Started...")

while True:
    try:
        signal = strategy()

        if signal and signal != last_signal:
            send_telegram(f"🚨 ETH Keltner Signal:\n{signal}")
            last_signal = signal
        else:
            print("No signal")

    except Exception as e:
        print("Error:", e)

    time.sleep(300)
