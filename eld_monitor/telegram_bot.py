"""
Telegram Userbot
Uses Telethon to log in as a real Telegram account (not a bot).

On first run it will ask for the verification code sent to your phone.
After that, the session is saved and reused automatically.
"""

import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserDeactivatedBanError
from telethon.tl.types import Chat, Channel
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramUserbot:
    """
    A Telegram userbot that can find groups by driver name and send messages.
    """

    def __init__(self, api_id: int, api_hash: str, phone: str, session_name: str = "eld_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self._dialog_cache: dict = {}  # name → entity cache

    async def start(self):
        """Start the Telegram client (prompts for code on first run)."""
        self.client = TelegramClient(
            session=self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash
        )
        await self.client.start(phone=self.phone)
        me = await self.client.get_me()
        logger.info(f"Telegram account logged in as: {me.first_name} (@{me.username})")
        await self._refresh_dialog_cache()
        return self

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def _refresh_dialog_cache(self):
        """Load all group/channel names into cache for quick lookup."""
        self._dialog_cache.clear()
        async for dialog in self.client.iter_dialogs():
            if hasattr(dialog.entity, "title"):
                name = dialog.entity.title.lower()
                self._dialog_cache[name] = dialog.entity
        logger.info(f"Dialog cache refreshed: {len(self._dialog_cache)} groups/channels loaded")

    async def find_group_for_driver(self, driver_name: str) -> Optional[object]:
        """
        Find a Telegram group where the driver's name appears in the group title.
        
        Example: driver name "John Smith" will match groups like:
          - "John Smith - Dispatch"
          - "John Smith Trucker"
          - "John Smith"
        """
        name_parts = driver_name.lower().split()
        
        # Try exact full name first
        if driver_name.lower() in self._dialog_cache:
            return self._dialog_cache[driver_name.lower()]
        
        # Try partial match
        for group_name, entity in self._dialog_cache.items():
            # Check if all name parts appear in the group name
            if all(part in group_name for part in name_parts):
                return entity
        
        # Refresh cache and try again (in case new groups were added)
        await self._refresh_dialog_cache()
        for group_name, entity in self._dialog_cache.items():
            if all(part in group_name for part in name_parts):
                return entity
        
        logger.warning(f"No Telegram group found for driver: {driver_name}")
        return None

    async def send_message(self, driver_name: str, message: str) -> bool:
        """
        Send a message to the group matching the driver's name.
        Returns True if sent successfully.
        """
        try:
            entity = await self.find_group_for_driver(driver_name)
            if not entity:
                logger.warning(f"Skipping message for {driver_name} — no group found")
                return False

            await self.client.send_message(entity, message)
            logger.info(f"✓ Message sent to group for {driver_name}")
            return True

        except FloodWaitError as e:
            logger.warning(f"Telegram flood wait: {e.seconds}s — will retry later")
            await asyncio.sleep(e.seconds)
            return False

        except UserDeactivatedBanError:
            logger.error("Telegram account has been banned or deactivated!")
            return False

        except Exception as e:
            logger.error(f"Failed to send message to {driver_name}: {e}")
            return False

    async def send_message_to_group(self, group_name: str, message: str) -> bool:
        """Send a message directly to a group by name."""
        entity = self._dialog_cache.get(group_name.lower())
        if not entity:
            return False
        try:
            await self.client.send_message(entity, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to group '{group_name}': {e}")
            return False

    async def list_groups(self) -> list[str]:
        """Returns a list of all group/channel names in the account."""
        await self._refresh_dialog_cache()
        return list(self._dialog_cache.keys())


class TelebotManager:
    """
    Manages multiple Telegram accounts.
    Routes alerts through available accounts.
    """

    def __init__(self):
        self.accounts: list[TelegramUserbot] = []
        self._current_account_index = 0

    async def add_account(self, api_id: int, api_hash: str, phone: str, session_name: str) -> TelegramUserbot:
        bot = TelegramUserbot(api_id, api_hash, phone, session_name)
        await bot.start()
        self.accounts.append(bot)
        logger.info(f"Added Telegram account: {phone}")
        return bot

    async def stop_all(self):
        for acc in self.accounts:
            await acc.stop()

    async def send_alert(self, driver_name: str, message: str) -> bool:
        """
        Send an alert using the next available account (round-robin).
        Falls back to other accounts if one fails.
        """
        if not self.accounts:
            logger.error("No Telegram accounts configured!")
            return False

        start_index = self._current_account_index
        attempts = 0

        while attempts < len(self.accounts):
            account = self.accounts[self._current_account_index]
            self._current_account_index = (self._current_account_index + 1) % len(self.accounts)

            success = await account.send_message(driver_name, message)
            if success:
                return True

            attempts += 1

        logger.error(f"All Telegram accounts failed to send message to {driver_name}")
        return False
