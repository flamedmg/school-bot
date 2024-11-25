import asyncio
import logging
import uvicorn

from telethon import TelegramClient
from telethon.errors import PeerIdInvalidError
from telethon.tl.types import PeerChannel
from fast_depends import Depends, inject

from src.config import settings
from src.database import init_db
from src.api.app import app as fastapi_app
from src.telegram.bot import setup_handlers
from src.events.manager import event_manager
from src.events.broker import app as stream_app
from src.dependencies import Dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Telegram client
bot = TelegramClient("school_bot", settings.telegram_api_id, settings.telegram_api_hash)

@inject
async def send_welcome_message(
    chat_id: int, bot: TelegramClient = Depends(Dependencies.get_bot)
):
    """Send welcome message to the specified chat."""
    try:
        await bot.send_message(
            chat_id,
            "🚀 Bot has started and is ready to assist you!\n\n"
            "Available commands:\n"
            "/schedule - View today's schedule\n"
            "/homework - Check homework assignments\n"
            "/grades - View recent grades\n"
            "/notifications - Manage notification settings\n"
            "/help - Show help message",
        )
        logger.info(f"Welcome message sent to chat ID: {chat_id}")
    except PeerIdInvalidError:
        logger.error(
            f"Failed to send welcome message: Invalid chat ID format. "
            f"Current chat_id: {chat_id}. "
            f"Please make sure:\n"
            f"1. The bot is added to the group/channel\n"
            f"2. The bot has admin privileges in the group/channel\n"
            f"3. Send a message in the group/channel to get the correct ID\n"
            f"4. Update TELEGRAM_CHAT_ID in .env with the ID shown in logs"
        )
    except Exception as e:
        logger.error(f"Failed to send welcome message: {str(e)}")

async def startup():
    """Startup events for the application."""
    try:
        # Initialize database
        db_initialized = await init_db()
        if not db_initialized:
            raise RuntimeError("Database initialization failed")

        # Start Telegram client
        await bot.start(bot_token=settings.telegram_bot_token)

        # Register bot in dependency system
        Dependencies.set_bot(bot)

        # Setup bot handlers
        setup_handlers(bot)

        # Send welcome message or instructions for chat ID
        await send_welcome_message(settings.telegram_chat_id)

        # Initialize and start event manager
        event_manager.initialize()
        await event_manager.start()

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

async def shutdown():
    """Shutdown events for the application."""
    try:
        # Cleanup
        await event_manager.stop()
        await bot.disconnect()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")
        raise

async def run_fastapi():
    """Run the FastAPI server"""
    config = uvicorn.Config(
        fastapi_app,
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    await server.serve()

async def run_all():
    """Run all services concurrently"""
    try:
        # Start application
        await startup()
        
        # Run FastAPI server and FastStream app
        await asyncio.gather(
            run_fastapi(),
            stream_app.run()
        )
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
