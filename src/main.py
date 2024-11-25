import asyncio
import uvicorn
from loguru import logger

from src.utils import setup_logging, is_port_in_use, find_free_port

# Configure logging first, before any other imports
logger = setup_logging()

from telethon import TelegramClient
from src.config import settings
from src.database import init_db
from src.api.app import app as fastapi_app
from src.telegram.bot import setup_handlers, send_welcome_message
from src.events.broker import app as stream_app
from src.dependencies import Dependencies
# Import handlers to ensure they're registered
from src.events import crawl_handler, schedule_handler, telegram_handler

# Initialize Telegram client
bot = TelegramClient("school_bot", settings.telegram_api_id, settings.telegram_api_hash)

async def startup():
    """Startup events for the application."""
    try:
        logger.info("Starting application...")
        
        # Initialize database
        db_initialized = await init_db()
        if not db_initialized:
            raise RuntimeError("Database initialization failed")
        logger.info("Database initialized")

        # Start Telegram client
        await bot.start(bot_token=settings.telegram_bot_token)
        logger.info("Telegram client started")

        # Register bot in dependency system
        Dependencies.set_bot(bot)

        # Setup Telegram bot handlers
        setup_handlers(bot)
        logger.info("Telegram handlers set up")

        # Send welcome message
        await send_welcome_message(bot, settings.telegram_chat_id)

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

async def shutdown():
    """Shutdown events for the application."""
    try:
        logger.info("Starting shutdown sequence...")
        await bot.disconnect()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")
        raise

async def run_fastapi():
    """Run the FastAPI server"""
    port = settings.api_port
    
    # Check if port is in use and find a free one if needed
    if is_port_in_use(port):
        try:
            port = find_free_port(port + 1)
            logger.warning(f"Original port {settings.api_port} was in use, using port {port} instead")
        except RuntimeError as e:
            logger.error(str(e))
            return
    
    config = uvicorn.Config(
        fastapi_app,
        host=settings.api_host,
        port=port,
        workers=settings.api_workers,
        reload=True,
        loop="asyncio",
        log_level="info",
        log_config=None,  # Disable uvicorn's default logging config
        access_log=False  # Disable access logging as it will be handled by our interceptor
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except Exception as e:
        logger.error(f"FastAPI server error: {str(e)}")

async def run_all():
    """Run all services concurrently"""
    try:
        # Start application
        await startup()
        
        # Run FastAPI server and FastStream worker
        await asyncio.gather(
            run_fastapi(),
            stream_app.run(),
            return_exceptions=True
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
