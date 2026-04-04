def get_ai_prediction(close):
    try:
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]

        if ema20 > ema50:
            return "📈 UP TREND"
        elif ema20 < ema50:
            return "📉 DOWN TREND"
        else:
            return "⚖️ SIDEWAYS"

    except:
        return "N/A"
