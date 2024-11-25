from loguru import logger
from telethon import TelegramClient, events
from telethon.errors import PeerIdInvalidError

from src.config import settings

async def send_welcome_message(bot: TelegramClient, chat_id: int):
    """Send welcome message to the specified chat."""
    try:
        logger.info(f"Sending welcome message to chat {chat_id}...")
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
        logger.info("Welcome message sent successfully")
    except PeerIdInvalidError:
        logger.error(
            "Failed to send welcome message: Invalid chat ID format. "
            f"Current chat_id: {chat_id}. "
            "Please make sure:\n"
            "1. The bot is added to the group/channel\n"
            "2. The bot has admin privileges in the group/channel\n"
            "3. Send a message in the group/channel to get the correct ID\n"
            "4. Update TELEGRAM_CHAT_ID in .env with the ID shown in logs"
        )
    except Exception as e:
        logger.error(f"Failed to send welcome message: {str(e)}")

def setup_handlers(bot: TelegramClient):
    """Setup Telegram bot handlers."""
    logger.info("Setting up Telegram bot handlers...")
    # Here you would set up any direct Telegram event handlers
    # that aren't handled through FastStream
    logger.info("Telegram bot handlers registered successfully")
