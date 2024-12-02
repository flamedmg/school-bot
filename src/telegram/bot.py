"""Main Telegram bot module."""

from typing import List

from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import PeerIdInvalidError
from datetime import datetime

from src.telegram.handlers.base import (
    BaseHandler,
    MessageHandler,
    CommandHandler,
    CallbackHandler,
)
from src.dependencies import get_kvstore
from src.database.kvstore import should_show_greeting
from src.telegram.handlers.messages import send_welcome_message


class Bot:
    """Telegram bot class."""

    def __init__(self, client: TelegramClient):
        """Initialize the bot.

        Args:
            client: The Telegram client instance
        """
        self.client = client
        self.handlers: List[BaseHandler] = [
            MessageHandler(),
            CommandHandler(),
            CallbackHandler(),
        ]
        self.logger = logger

    def setup_handlers(self) -> None:
        """Register all message and callback handlers."""
        # Register greeting handler with expanded patterns
        greeting_pattern = "(?i)^(hi|hey|bot|бот)$"

        @self.client.on(events.NewMessage(pattern=greeting_pattern))
        async def handle_greeting(event):
            await self.handlers[0].handle(event)

        # Register command handler
        @self.client.on(events.NewMessage(pattern="^/[a-zA-Z]+"))
        async def handle_command(event):
            await self.handlers[1].handle(event)

        # Register callback handler
        @self.client.on(events.CallbackQuery())
        async def handle_callback(event):
            await self.handlers[2].handle(event)

        self.logger.info("All handlers registered successfully")


def setup_handlers(bot: TelegramClient) -> None:
    """Set up the bot handlers.

    Args:
        bot: The Telegram client instance
    """
    Bot(bot).setup_handlers()


__all__ = ["setup_handlers", "send_welcome_message"]
