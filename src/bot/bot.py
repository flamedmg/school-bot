import logging

from telethon import TelegramClient, events
from telethon.tl.types import Message, Chat, Channel

logger = logging.getLogger(__name__)


async def start_handler(event: Message):
    """Handle /start command."""
    chat = await event.get_chat()
    logger.info(f"Received /start command from chat ID: {chat.id}")
    
    await event.respond(
        "👋 Welcome to School Parent Assistant Bot!\n\n"
        "I'll help you stay updated with:\n"
        "📚 School schedules\n"
        "📧 Important notifications\n"
        "📊 Academic performance\n\n"
        "Use /help to see available commands."
    )


async def help_handler(event: Message):
    """Handle /help command."""
    chat = await event.get_chat()
    logger.info(f"Received /help command from chat ID: {chat.id}")
    
    await event.respond(
        "Available commands:\n\n"
        "/schedule - View today's schedule\n"
        "/homework - Check homework assignments\n"
        "/grades - View recent grades\n"
        "/notifications - Manage notification settings\n"
        "/help - Show this help message"
    )


async def message_handler(event: Message):
    """Handle all messages to log chat IDs."""
    chat = await event.get_chat()
    if isinstance(chat, (Chat, Channel)):
        logger.info(f"Message received in chat/channel - Title: {chat.title}, ID: {chat.id}")
    else:
        logger.info(f"Message received from chat ID: {chat.id}")


def setup_handlers(bot: TelegramClient):
    """Register all message handlers."""
    # Command handlers
    bot.add_event_handler(
        start_handler,
        events.NewMessage(pattern='/start')
    )
    bot.add_event_handler(
        help_handler,
        events.NewMessage(pattern='/help')
    )
    # General message handler to log chat IDs
    bot.add_event_handler(
        message_handler,
        events.NewMessage()
    )
    logger.info("Bot handlers registered")
