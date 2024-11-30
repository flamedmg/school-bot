from faststream import Depends, Logger
from telethon import TelegramClient

from src.config import settings
from src.events.broker import broker, get_telegram
from src.events.event_types import EventTopics
from src.events.types import AnnouncementEvent, MarkEvent

# Create module-level singleton
telegram_client = Depends(get_telegram)


@broker.subscriber(EventTopics.NEW_MARK)
async def handle_new_mark(
    event: MarkEvent, logger: Logger, telegram: TelegramClient = telegram_client
):
    """Handle new mark events and send Telegram notifications."""
    try:
        logger.info(f"Handling new mark event for student: {event.student_nickname}")

        # Get student's emoji from settings
        student = next(
            (s for s in settings.students if s.nickname == event.student_nickname), None
        )
        emoji = student.emoji if student else "👤"

        # Format mark notification
        message = f"{emoji} New mark in *{event.subject}*:\n" f"📝 *{event.new}*"

        await telegram.send_message(
            settings.telegram_chat_id, message, parse_mode="Markdown"
        )
        logger.info("Mark notification sent successfully")

    except Exception as e:
        logger.error(f"Error handling mark event: {str(e)}")


@broker.subscriber(EventTopics.NEW_ANNOUNCEMENT)
async def handle_new_announcement(
    event: AnnouncementEvent,
    logger: Logger,
    telegram: TelegramClient = telegram_client,
):
    """Handle new announcement events and send Telegram notifications."""
    try:
        logger.info(f"Handling new announcement for student: {event.student_nickname}")

        # Get student's emoji from settings
        student = next(
            (s for s in settings.students if s.nickname == event.student_nickname), None
        )
        emoji = student.emoji if student else "👤"

        # Format announcement notification
        message = f"{emoji} New announcement:\n📢 {event.text}"

        # Add additional details if available
        if event.subject:
            message += f"\nSubject: {event.subject}"
        if event.behavior_type:
            message += f"\nBehavior: {event.behavior_type}"
        if event.rating:
            message += f"\nRating: {event.rating}"
        if event.description:
            message += f"\nDescription: {event.description}"

        await telegram.send_message(settings.telegram_chat_id, message)
        logger.info("Announcement notification sent successfully")

    except Exception as e:
        logger.error(f"Error handling announcement event: {str(e)}")
