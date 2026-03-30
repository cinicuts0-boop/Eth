import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from config import DB_PATH
from signals import TradingSignal

logger = logging.getLogger("trading_bot.db")


def _conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, action TEXT, strength REAL,
            price REAL, rsi REAL, macd REAL, price_change_pct REAL,
            reasons TEXT, created_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS i1 ON signals(symbol)")
        c.commit()
    logger.debug("DB ready")


def save_signal(sig: TradingSignal):
    with _conn() as c:
        c.execute(
            "INSERT INTO signals VALUES (NULL,?,?,?,?,?,?,?,?,?)",
            (sig.symbol, sig.action, sig.strength, sig.price, sig.rsi,
             sig.macd, sig.price_change_pct, json.dumps(sig.reasons),
             datetime.now(timezone.utc).isoformat())
        )
        c.commit()


def get_recent(symbol=None, limit=20):
    with _conn() as c:
        q  = "SELECT * FROM signals"
        q += (" WHERE symbol=?" if symbol else "") + " ORDER BY created_at DESC LIMIT ?"
        rows = c.execute(q, ((symbol, limit) if symbol else (limit,))).fetchall()
    return [dict(r) for r in rows]
