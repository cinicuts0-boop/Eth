import os
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def _get_bool(key, default):
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

def _get_float(key, default):
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def _get_int(key, default):
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

_raw = os.getenv("SYMBOLS", "ETH-USD")
SYMBOLS = [s.strip() for s in _raw.split(",") if s.strip()]

CHECK_INTERVAL_MINUTES = _get_int("CHECK_INTERVAL_MINUTES", 5)
DATA_INTERVAL          = os.getenv("DATA_INTERVAL", "5m")
DATA_PERIOD            = os.getenv("DATA_PERIOD", "5d")

RSI_OVERSOLD           = _get_float("RSI_OVERSOLD", 35.0)
RSI_OVERBOUGHT         = _get_float("RSI_OVERBOUGHT", 65.0)

ALERT_ON_BUY           = _get_bool("ALERT_ON_BUY", True)
ALERT_ON_SELL          = _get_bool("ALERT_ON_SELL", True)
MIN_SIGNAL_STRENGTH    = _get_float("MIN_SIGNAL_STRENGTH", 0.5)

DB_PATH   = os.getenv("DB_PATH", "bot/signals.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trading_bot")


def validate_credentials():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        logger.warning("TELEGRAM_BOT_TOKEN not set — running in dry-run mode")
        return False
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "your_chat_id_here":
        logger.warning("TELEGRAM_CHAT_ID not set — running in dry-run mode")
        return False
    return True
