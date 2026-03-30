
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

    if df is None or df.empty:
        print("No data available")
        return None

    if len(df) < 20:
        print("Not enough data")
        return None

    df['ema'] = df['close'].ewm(span=20).mean()
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

    last = df.iloc[-1]

    print("Price:", last['close'], "EMA:", last['ema'], "RSI:", last['rsi'])

    if last['close'] > last['ema'] and last['rsi'] > 55:
        return f"📈 BUY ETH\nPrice: {last['close']}"

    elif last['close'] < last['ema'] and last['rsi'] < 45:
        return f"📉 SELL ETH\nPrice: {last['close']}"

    return None
