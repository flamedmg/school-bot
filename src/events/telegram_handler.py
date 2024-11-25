from telethon import TelegramClient
from faststream import Depends, Logger

from src.config import settings
from src.events.types import TelegramMessageEvent, TelegramCommandEvent, CrawlErrorEvent, EventTopics
from src.events.broker import broker, get_telegram

@broker.subscriber(EventTopics.TELEGRAM_MESSAGE)
async def handle_message(
    event: TelegramMessageEvent,
    logger: Logger,
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
        logger.info("Message acknowledgment sent")
        
    except Exception as e:
        logger.error(f"Error handling Telegram message: {str(e)}")

@broker.subscriber(EventTopics.TELEGRAM_COMMAND)
async def handle_command(
    event: TelegramCommandEvent,
    logger: Logger,
    telegram: TelegramClient = Depends(get_telegram)
):
    """Handle Telegram bot commands."""
    try:
        logger.info(f"Handling Telegram command: {event.command}")
        
        # Process different commands
        if event.command == "start":
            await _handle_start_command(event, telegram, logger)
        elif event.command == "help":
            await _handle_help_command(event, telegram, logger)
        else:
            await _handle_unknown_command(event, telegram, logger)
            
    except Exception as e:
        logger.error(f"Error handling Telegram command: {str(e)}")
        await telegram.send_message(
            event.chat_id,
            f"❌ Error processing command: {str(e)}"
        )

@broker.subscriber(EventTopics.CRAWL_ERROR)
async def handle_crawl_error(
    event: CrawlErrorEvent,
    logger: Logger,
    telegram: TelegramClient = Depends(get_telegram)
):
    """Handle crawling and parsing errors."""
    try:
        logger.error(f"Crawl error occurred: {event.error_message}")
        
        # Format error message for Telegram
        error_message = (
            f"⚠️ Error for student {event.student_nickname}\n"
            f"Type: {event.error_type}\n"
            f"Message: {event.error_message}\n"
            f"Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # If there's a screenshot, send it
        if event.screenshot_path:
            await telegram.send_file(
                settings.admin_chat_id,  # Send to admin chat
                event.screenshot_path,
                caption=error_message
            )
        else:
            await telegram.send_message(
                settings.admin_chat_id,  # Send to admin chat
                error_message
            )
            
        logger.info("Crawl error notification sent to admin")
        
    except Exception as e:
        logger.error(f"Error handling crawl error notification: {str(e)}")

async def _handle_start_command(
    event: TelegramCommandEvent,
    telegram: TelegramClient,
    logger: Logger
):
    """Handle the /start command."""
    logger.info("Processing /start command")
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
    logger.info("Welcome message sent")

async def _handle_help_command(
    event: TelegramCommandEvent,
    telegram: TelegramClient,
    logger: Logger
):
    """Handle the /help command."""
    logger.info("Processing /help command")
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
        "• Schedule changes\n"
        "• System errors and issues"
    )
    await telegram.send_message(event.chat_id, help_message)
    logger.info("Help message sent")

async def _handle_unknown_command(
    event: TelegramCommandEvent,
    telegram: TelegramClient,
    logger: Logger
):
    """Handle unknown commands."""
    logger.warning(f"Unknown command received: {event.command}")
    unknown_command_message = (
        "❓ Unknown command. Use /help to see available commands."
    )
    await telegram.send_message(event.chat_id, unknown_command_message)
    logger.info("Unknown command message sent")
