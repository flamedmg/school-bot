import asyncio
import sys

from faststream import ContextRepo, Depends, FastStream
from faststream.redis import RedisBroker
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq_faststream import BrokerWrapper
from telethon import TelegramClient

from src.config import settings
from src.database.repository import ScheduleRepository
from src.dependencies import get_bot, get_db
from src.events.initial_crawl import trigger_initial_crawls

# Global broker instance
broker = RedisBroker(url=str(settings.redis_url), logger=logger)

# Global FastStream app instance
app = FastStream(broker, logger=logger)

# Create taskiq broker wrapper for scheduling
taskiq_broker = BrokerWrapper(broker)


# Dependencies
async def get_telegram() -> TelegramClient:
    """Dependency for telegram client."""
    return await get_bot()


async def get_session() -> AsyncSession:
    """Dependency for database session."""
    return await anext(get_db())


# Create module-level singleton for session
session_singleton = Depends(get_session)


async def get_repository(
    session: AsyncSession = session_singleton,
) -> ScheduleRepository:
    """Dependency for repository with session injection."""
    return ScheduleRepository(session)


@app.on_startup
async def setup(context: ContextRepo):
    """Initialize broker and set up global context."""
    try:
        await broker.connect()
    except Exception as e:
        logger.error(f"Failed to connect to the broker: {str(e)}")
        sys.exit(1)  # Terminate the application if the broker connection fails

    context.set_global("settings", settings)
    logger.info("Message broker connected and context initialized")
    # Add a small delay to ensure broker is fully ready
    await asyncio.sleep(1)


@app.after_startup
async def trigger_crawls():
    """Trigger initial crawls after broker is connected and handlers are set up."""
    logger.info("Starting initial crawls...")
    await trigger_initial_crawls(broker)


__all__ = [
    "broker",
    "app",
    "taskiq_broker",
    "get_telegram",
    "get_session",
    "get_repository",
]
