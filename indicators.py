import logging
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger("trading_bot.indicators")


@dataclass
class IndicatorValues:
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_percent: Optional[float] = None
    volume_sma: Optional[float] = None
    current_volume: Optional[float] = None
    current_price: Optional[float] = None
    prev_close: Optional[float] = None
    price_change_pct: Optional[float] = None


def _last(s):
    if s is None or s.empty:
        return None
    v = s.dropna()
    return float(v.iloc[-1]) if not v.empty else None


def compute_indicators(df: pd.DataFrame) -> Optional[IndicatorValues]:
    if df is None or len(df) < 26:
        return None

    close, volume = df["close"], df["volume"]
    v = IndicatorValues()

    v.current_price = float(close.iloc[-1])
    if len(close) >= 2:
        v.prev_close = float(close.iloc[-2])
        v.price_change_pct = (v.current_price - v.prev_close) / v.prev_close * 100

    v.rsi = _last(ta.rsi(close, length=14))

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        v.macd          = _last(macd_df.iloc[:, 0])
        v.macd_signal   = _last(macd_df.iloc[:, 2])
        v.macd_histogram= _last(macd_df.iloc[:, 1])

    if len(close) >= 50:
        v.ema_50  = _last(ta.ema(close, length=50))
    if len(close) >= 200:
        v.ema_200 = _last(ta.ema(close, length=200))

    if len(close) >= 20:
        bb = ta.bbands(close, length=20, std=2)
        if bb is not None and not bb.empty:
            v.bb_upper = _last(bb.iloc[:, 0])
            v.bb_lower = _last(bb.iloc[:, 2])
            if v.bb_upper and v.bb_lower and v.bb_upper != v.bb_lower:
                v.bb_percent = (v.current_price - v.bb_lower) / (v.bb_upper - v.bb_lower)

    v.volume_sma    = _last(ta.sma(volume, length=20))
    v.current_volume= float(volume.iloc[-1])
    return v
