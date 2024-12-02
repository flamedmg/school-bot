"""Message handling functionality for the Telegram bot."""

from datetime import datetime

from loguru import logger
from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.errors import PeerIdInvalidError

from src.telegram.constants import MessagePattern
from src.telegram.handlers.menu import display_menu
from src.database.kvstore import should_show_greeting
from src.dependencies import get_kvstore


async def handle_hi_message(event: NewMessage.Event) -> None:
    """Handle 'hi' messages (case insensitive)."""
    logger.info("Handling 'hi' message")
    await display_menu(event)


async def handle_menu_command(event: NewMessage.Event) -> None:
    """Handle /menu command."""
    logger.info("Handling menu command")
    await display_menu(event)


async def handle_start_command(event: NewMessage.Event) -> None:
    """Handle /start command."""
    logger.info("Handling start command")
    await display_menu(event)


async def handle_text_message(event: NewMessage.Event) -> None:
    """Handle general text messages."""
    if not event.message or not event.message.text:
        return

    text = event.message.text.strip()
    logger.info(f"Processing text message: {text}")

    if text.lower() == "hi":
        await handle_hi_message(event)


async def send_welcome_message(bot: TelegramClient, chat_id: int) -> None:
    """Send welcome message to the specified chat.

    Args:
        bot: The Telegram client instance
        chat_id: The chat ID to send the message to
    """
    try:
        # Get KVStore instance
        kvstore = await get_kvstore()

        # Check if we should show the greeting
        if not await should_show_greeting(kvstore):
            logger.info("Skipping welcome message (already shown today)")
            return

        logger.info(f"Sending welcome message to chat {chat_id}...")
        await bot.send_message(
            chat_id,
            "👋 Hello! I'm School Bot!\n\n"
            "I can help you check:\n"
            "• Class schedules\n"
            "• Homework assignments\n"
            "• Grades\n\n"
            "Say 'hi' or use /menu to see available options!",
        )

        # Store current timestamp
        await kvstore.set_last_greeting_time(datetime.now().timestamp())
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
