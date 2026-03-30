import logging
from datetime import datetime, timezone
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, validate_credentials
from signals import TradingSignal

logger = logging.getLogger("trading_bot.telegram")
_API = "https://api.telegram.org/bot{token}/sendMessage"


def _fmt_price(p):
    return f"{p:,.2f}" if p >= 1000 else (f"{p:.4f}" if p >= 1 else f"{p:.8f}")


def build_message(sig: TradingSignal) -> str:
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    price = _fmt_price(sig.price) if sig.price else "N/A"
    chg   = f"{sig.price_change_pct:+.2f}%" if sig.price_change_pct is not None else "N/A"
    rsi   = f"{sig.rsi:.1f}" if sig.rsi else "N/A"
    lines = [
        f"{sig.emoji} *{sig.action} Signal — {sig.symbol}*",
        f"Strength: *{sig.strength_label}* ({sig.strength:.0%})",
        "",
        f"Price : `${price}`",
        f"Change: `{chg}`",
        f"RSI   : `{rsi}`",
        "",
        "*Reasons:*",
    ] + [f"  - {r}" for r in sig.reasons] + ["", f"_{now}_"]
    return "\n".join(lines)


def _post(text: str) -> bool:
    url     = _API.format(token=TELEGRAM_BOT_TOKEN)
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text,
               "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10).raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_signal(sig: TradingSignal) -> bool:
    msg = build_message(sig)
    if not validate_credentials():
        logger.info(f"[DRY RUN]\n{msg}")
        return False
    logger.info(f"Sending {sig.action} alert for {sig.symbol}")
    return _post(msg)


def send_startup_message(symbols: list) -> None:
    if not validate_credentials():
        logger.info("[DRY RUN] Bot started — Telegram not configured")
        return
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = "🤖 *Trading Signal Bot Started*\n\n" + \
           "\n".join(f"  - {s}" for s in symbols) + f"\n\n_{now}_"
    _post(text)


def send_error_alert(symbol: str, error: str) -> None:
    if validate_credentials():
        _post(f"*Error — {symbol}*\n`{error}`")
