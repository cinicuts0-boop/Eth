import yfinance as yf
import ta
import datetime

from bot.strategy import get_ai_prediction
from bot.telegram import send_telegram
from bot.stats import trade_history

latest_data = {
    "ETH": {}, "BTC": {}, "NIFTY": {}, "BANKNIFTY": {}, "CRUDE": {}
}

last_signal = {}

def get_signal_for(symbol, name):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)

        if df is None or df.empty:
            return

        df = df.dropna()
        close = df['Close']

# ✅ FIX (IMPORTANT)
if hasattr(close, "shape") and len(close.shape) > 1:
    close = close.squeeze()

close = close.astype(float)

        if len(close) < 30:
            return

        price = float(close.iloc[-1].item())

        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

        macd = ta.trend.MACD(close)
        macd_val = macd.macd().iloc[-1]
        macd_sig = macd.macd_signal().iloc[-1]

        prediction = get_ai_prediction(close)

        signal = "WAITING"

        if rsi < 35 and macd_val > macd_sig:
            signal = "BUY"
        elif rsi > 65 and macd_val < macd_sig:
            signal = "SELL"

        latest_data[name] = {
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "signal": signal,
            "prediction": prediction
        }

        if signal == last_signal.get(name):
            return

        if signal != "WAITING":
            last_signal[name] = signal

            sl = price - 10 if signal == "BUY" else price + 10
            target = price + 20 if signal == "BUY" else price - 20

            trade_history.append({
                "coin": name,
                "type": signal,
                "price": price,
                "sl": sl,
                "target": target,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "result": "OPEN"
            })

            send_telegram(f"{name} → {signal} @ {price}")
    except Exception as e:
        print(name, "ERROR:", e)
