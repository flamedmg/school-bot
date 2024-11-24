from typing import AsyncGenerator
from fast_depends import Depends, inject
from telethon import TelegramClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db as get_db_session

class Dependencies:
    _bot_instance: TelegramClient | None = None

    @classmethod
    def set_bot(cls, bot: TelegramClient) -> None:
        """Set the global bot instance."""
        cls._bot_instance = bot

    @classmethod
    @inject
    async def get_bot(cls) -> TelegramClient:
        """
        Dependency provider for the Telegram bot instance.
        This can be used in FastAPI/FastStream route handlers with Depends.
        """
        if cls._bot_instance is None:
            raise RuntimeError("Bot instance not initialized")
        return cls._bot_instance

    @staticmethod
    @inject
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """Database session dependency."""
        async for session in get_db_session():
            yield session

# Create singleton dependencies
get_bot = Dependencies.get_bot
get_db = Dependencies.get_db
