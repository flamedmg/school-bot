from faststream import FastStream, Depends
from faststream.redis import RedisBroker
from telethon import TelegramClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.dependencies import get_bot, get_db
from src.database.repository import ScheduleRepository

# Global broker instance
broker = RedisBroker(
    str(settings.redis_url),
    apply_types=True  # Enable type casting and dependency injection
)

# Global FastStream app instance
app = FastStream(broker)

# Dependencies
async def get_telegram() -> TelegramClient:
    """Dependency for telegram client."""
    return await get_bot()

async def get_session() -> AsyncSession:
    """Dependency for database session."""
    return await anext(get_db())

async def get_repository(session: AsyncSession = Depends(get_session)) -> ScheduleRepository:
    """Dependency for repository with session injection."""
    return ScheduleRepository(session)

__all__ = [
    'broker',
    'app',
    'get_telegram',
    'get_session',
    'get_repository'
]
