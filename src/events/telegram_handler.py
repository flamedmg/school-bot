import logging
from telethon import TelegramClient
from faststream import Depends

from src.events.types import TelegramMessageEvent, TelegramCommandEvent, EventTopics
from src.events.broker import broker, get_telegram

logger = logging.getLogger(__name__)

@broker.subscriber(EventTopics.TELEGRAM_MESSAGE)
async def handle_message(
    event: TelegramMessageEvent,
    telegram: TelegramClient = Depends(get_telegram)
):
    """Handle incoming Telegram messages."""
    try:
        logger.info(f"Handling Telegram message: {event.message_id}")
        
        # Here you would implement message handling logic
        # For example, processing natural language queries
        # or handling specific message patterns
        
        # For now, we'll just acknowledge the message
        await telegram.send_message(
            event.chat_id,
            "Message received! I'm still learning how to process natural language queries."
        )
        
    except Exception as e:
        logger.error(f"Error handling Telegram message: {str(e)}")

@broker.subscriber(EventTopics.TELEGRAM_COMMAND)
async def handle_command(
    event: TelegramCommandEvent,
    telegram: TelegramClient = Depends(get_telegram)
):
    """Handle Telegram bot commands."""
    try:
        logger.info(f"Handling Telegram command: {event.command}")
        
        # Process different commands
        if event.command == "start":
            await _handle_start_command(event, telegram)
        elif event.command == "help":
            await _handle_help_command(event, telegram)
        else:
            await _handle_unknown_command(event, telegram)
            
    except Exception as e:
        logger.error(f"Error handling Telegram command: {str(e)}")
        await telegram.send_message(
            event.chat_id,
            f"❌ Error processing command: {str(e)}"
        )

async def _handle_start_command(event: TelegramCommandEvent, telegram: TelegramClient):
    """Handle the /start command."""
    welcome_message = (
        "🚀 Welcome to School Bot!\n\n"
        "Available commands:\n"
        "/schedule - View today's schedule\n"
        "/homework - Check homework assignments\n"
        "/grades - View recent grades\n"
        "/notifications - Manage notification settings\n"
        "/help - Show this help message"
    )
    await telegram.send_message(event.chat_id, welcome_message)

async def _handle_help_command(event: TelegramCommandEvent, telegram: TelegramClient):
    """Handle the /help command."""
    help_message = (
        "📚 School Bot Help\n\n"
        "Commands:\n"
        "• /schedule - Shows your schedule for today\n"
        "• /homework - Lists pending homework assignments\n"
        "• /grades - Shows your recent grades\n"
        "• /notifications - Manage your notification preferences\n"
        "\nThe bot will automatically notify you about:\n"
        "• New grades\n"
        "• New announcements\n"
        "• Schedule changes"
    )
    await telegram.send_message(event.chat_id, help_message)

async def _handle_unknown_command(event: TelegramCommandEvent, telegram: TelegramClient):
    """Handle unknown commands."""
    unknown_command_message = (
        "❓ Unknown command. Use /help to see available commands."
    )
    await telegram.send_message(event.chat_id, unknown_command_message)
