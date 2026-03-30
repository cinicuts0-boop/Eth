import logging
from typing import Optional
import pandas as pd
import yfinance as yf
from config import DATA_INTERVAL, DATA_PERIOD

logger = logging.getLogger("trading_bot.data")


def fetch_ohlcv(symbol: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(symbol).history(period=DATA_PERIOD, interval=DATA_INTERVAL)
        if df.empty:
            logger.warning(f"No data for {symbol}")
            return None
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        logger.debug(f"Fetched {len(df)} rows for {symbol}")
        return df
    except Exception as e:
        logger.error(f"Fetch failed for {symbol}: {e}")
        return None
