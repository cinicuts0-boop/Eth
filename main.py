import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import logger, SYMBOLS, CHECK_INTERVAL_MINUTES, validate_credentials
from database import init_db
from scheduler import start_scheduler
from telegram_alerts import send_startup_message


def main():
    logger.info("=" * 50)
    logger.info("  Trading Signal Bot")
    logger.info("=" * 50)
    logger.info(f"Symbols : {', '.join(SYMBOLS)}")
    logger.info(f"Interval: every {CHECK_INTERVAL_MINUTES} min")
    logger.info(f"Telegram: {'configured' if validate_credentials() else 'NOT configured (dry-run)'}")
    logger.info("=" * 50)

    init_db()
    send_startup_message(SYMBOLS)
    start_scheduler()


if __name__ == "__main__":
    main()
