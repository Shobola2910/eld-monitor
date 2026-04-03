"""
ELD Telegram Monitor — Main Entry Point

Usage:
    1. Install dependencies:
       pip install -r requirements.txt

    2. Edit config.json with your ELD tokens and Telegram credentials.

    3. Run:
       python main.py

    On first run, Telegram will ask for a verification code
    sent to your phone number. Enter it in the terminal.
    After that, the session is saved and the code is not needed again.
"""

import asyncio
import logging
import json
import sys
import signal
from pathlib import Path

from eld_client import create_eld_client
from telegram_bot import TelebotManager
from monitor import ELDMonitor

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("eld_monitor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        logger.error(f"Config file not found: {path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def main():
    config = load_config()
    settings = config.get("settings", {})

    # ── Initialize ELD clients ─────────────────────────────────────────────
    eld_clients = []
    for acc in config.get("eld_accounts", []):
        if not acc.get("enabled", True):
            logger.info(f"Skipping disabled ELD account: {acc.get('name')}")
            continue
        try:
            client = create_eld_client(acc)
            eld_clients.append(client)
            logger.info(f"ELD account ready: {acc['name']}")
        except Exception as e:
            logger.error(f"Failed to create ELD client '{acc.get('name')}': {e}")

    if not eld_clients:
        logger.error("No ELD accounts configured or all failed. Exiting.")
        sys.exit(1)

    # ── Initialize Telegram accounts ──────────────────────────────────────
    telegram_manager = TelebotManager()

    for tg in config.get("telegram_accounts", []):
        if not tg.get("enabled", True):
            logger.info(f"Skipping disabled Telegram account: {tg.get('name')}")
            continue
        try:
            await telegram_manager.add_account(
                api_id=tg["api_id"],
                api_hash=tg["api_hash"],
                phone=tg["phone"],
                session_name=tg.get("session_name", f"session_{tg['phone']}")
            )
        except Exception as e:
            logger.error(f"Failed to connect Telegram account '{tg.get('name')}': {e}")

    if not telegram_manager.accounts:
        logger.error("No Telegram accounts connected. Exiting.")
        sys.exit(1)

    # ── Start monitor ──────────────────────────────────────────────────────
    monitor = ELDMonitor(
        eld_clients=eld_clients,
        telegram_manager=telegram_manager,
        settings=settings
    )

    # Handle Ctrl+C gracefully
    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("Shutting down...")
        asyncio.ensure_future(monitor.stop())
        asyncio.ensure_future(telegram_manager.stop_all())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    logger.info("=" * 50)
    logger.info("  ELD Telegram Monitor v1.0")
    logger.info(f"  ELD accounts: {len(eld_clients)}")
    logger.info(f"  Telegram accounts: {len(telegram_manager.accounts)}")
    logger.info(f"  Poll interval: {settings.get('poll_interval_seconds', 60)}s")
    logger.info(f"  Alert repeat: every {settings.get('alert_repeat_interval_minutes', 30)} min")
    logger.info("=" * 50)

    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
