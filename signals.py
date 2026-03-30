import logging
from dataclasses import dataclass, field
from typing import Optional
from config import RSI_OVERBOUGHT, RSI_OVERSOLD
from indicators import IndicatorValues

logger = logging.getLogger("trading_bot.signals")

BUY  = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass
class TradingSignal:
    symbol: str
    action: str
    strength: float
    reasons: list[str] = field(default_factory=list)
    price: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    price_change_pct: Optional[float] = None

    @property
    def emoji(self):
        return {"BUY": "🟢", "SELL": "🔴"}.get(self.action, "🟡")

    @property
    def strength_label(self):
        return "STRONG" if self.strength >= 0.8 else ("MODERATE" if self.strength >= 0.5 else "WEAK")


def generate_signal(symbol: str, iv: IndicatorValues) -> TradingSignal:
    bull = bear = 0
    max_c = 6
    reasons = []
    price = iv.current_price or 0.0

    if iv.rsi is not None:
        if iv.rsi < RSI_OVERSOLD:
            bull += 1; reasons.append(f"RSI oversold ({iv.rsi:.1f} < {RSI_OVERSOLD})")
        elif iv.rsi > RSI_OVERBOUGHT:
            bear += 1; reasons.append(f"RSI overbought ({iv.rsi:.1f} > {RSI_OVERBOUGHT})")
        else:
            reasons.append(f"RSI neutral ({iv.rsi:.1f})")

    if iv.macd is not None and iv.macd_signal is not None:
        if iv.macd > iv.macd_signal and (iv.macd_histogram or 0) > 0:
            bull += 1; reasons.append(f"MACD bullish ({iv.macd:.4f} > {iv.macd_signal:.4f})")
        elif iv.macd < iv.macd_signal and (iv.macd_histogram or 0) < 0:
            bear += 1; reasons.append(f"MACD bearish ({iv.macd:.4f} < {iv.macd_signal:.4f})")
        else:
            reasons.append("MACD neutral")

    if iv.ema_50 is not None:
        if price > iv.ema_50:
            bull += 1; reasons.append(f"Above EMA50 ({iv.ema_50:.2f})")
        else:
            bear += 1; reasons.append(f"Below EMA50 ({iv.ema_50:.2f})")

    if iv.ema_200 is not None:
        if price > iv.ema_200:
            bull += 1; reasons.append(f"Above EMA200 ({iv.ema_200:.2f})")
        else:
            bear += 1; reasons.append(f"Below EMA200 ({iv.ema_200:.2f})")
    else:
        max_c -= 1

    if iv.bb_percent is not None:
        if iv.bb_percent < 0.2:
            bull += 1; reasons.append(f"Near BB lower band ({iv.bb_percent:.0%})")
        elif iv.bb_percent > 0.8:
            bear += 1; reasons.append(f"Near BB upper band ({iv.bb_percent:.0%})")
        else:
            reasons.append(f"Mid Bollinger band ({iv.bb_percent:.0%})")

    if iv.volume_sma and iv.current_volume:
        if iv.current_volume > iv.volume_sma * 1.5:
            reasons.append("High volume (>=1.5x avg)")
            if bull > bear:   bull += 1
            elif bear > bull: bear += 1
        else:
            max_c -= 1

    if bull > bear:
        action = BUY;  strength = bull / max_c if max_c else 0
    elif bear > bull:
        action = SELL; strength = bear / max_c if max_c else 0
    else:
        action = HOLD; strength = 0.3

    strength = min(1.0, max(0.0, strength))
    logger.info(f"{symbol}: {action} strength={strength:.2f} bull={bull} bear={bear}")
    return TradingSignal(symbol=symbol, action=action, strength=strength, reasons=reasons,
                         price=iv.current_price, rsi=iv.rsi, macd=iv.macd,
                         price_change_pct=iv.price_change_pct)
