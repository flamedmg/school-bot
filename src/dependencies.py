from collections.abc import AsyncGenerator

from fast_depends import inject
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient

from src.config import settings
from src.database import get_db as get_db_session
from src.database.kvstore import KeyValueStore


class Dependencies:
    _bot_instance: TelegramClient | None = None
    _kvstore_instance: KeyValueStore | None = None
    _redis_instance: Redis | None = None

    @classmethod
    def set_bot(cls, bot: TelegramClient) -> None:
        """Set the global bot instance."""
        cls._bot_instance = bot

    @classmethod
    async def initialize_redis(cls) -> None:
        """Initialize Redis connection."""
        if cls._redis_instance is None:
            cls._redis_instance = Redis.from_url(str(settings.redis_url))
            cls._kvstore_instance = KeyValueStore(cls._redis_instance)

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

    @classmethod
    @inject
    async def get_kvstore(cls) -> KeyValueStore:
        """
        Dependency provider for the KVStore instance.
        This can be used in FastAPI/FastStream route handlers with Depends.
        """
        if cls._kvstore_instance is None:
            raise RuntimeError("KVStore instance not initialized")
        return cls._kvstore_instance

    @staticmethod
    @inject
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """Database session dependency."""
        async for session in get_db_session():
            yield session

    @classmethod
    async def cleanup(cls) -> None:
        """Cleanup resources."""
        if cls._redis_instance:
            await cls._redis_instance.close()
            cls._redis_instance = None
            cls._kvstore_instance = None


# Create singleton dependencies
get_bot = Dependencies.get_bot
get_db = Dependencies.get_db
get_kvstore = Dependencies.get_kvstore
