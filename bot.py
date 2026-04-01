

import requests
import pandas as pd
import time
from ta.volatility import AverageTrueRange

TOKEN = "8682502193:AAGCtZGXiI-5v9x62W54PuhelYihBmE5t4M"
CHAT_ID = "8007854479"

def send_msg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_data():
    url = "https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=5m&limit=100"
    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "ct","qav","trades","tb","tq","ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df

def keltner_signal():
    df = get_data()

    # EMA
    df["ema"] = df["close"].ewm(span=20).mean()

    # ATR
    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=10
    )
    df["atr"] = atr.average_true_range()

    # Keltner Channel
    df["upper"] = df["ema"] + (df["atr"] * 2)
    df["lower"] = df["ema"] - (df["atr"] * 2)

    last = df.iloc[-1]

    price = last["close"]

    if price > last["upper"]:
        return f"🚀 BUY SIGNAL\nPrice: {price}"

    elif price < last["lower"]:
        return f"🔻 SELL SIGNAL\nPrice: {price}"

    else:
        return None

while True:
    try:
        signal = keltner_signal()

        if signal:
            send_msg(signal)
            print(signal)
        else:
            print("No trade")

    except Exception as e:
        print("Error:", e)

    time.sleep(300)
